# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

import ctypes
import logging
import weakref
from functools import cached_property, cache
from collections import defaultdict, OrderedDict
import pypdfium2 as pp

from ..utils import Rectangle, Region
from .character import Character
from .link import ObjLink, WebLink
from .path import Path
from .image import Image
from .structure import Structure

LOGGER = logging.getLogger(__name__)


class Page:
    def __init__(self, document, index: int):
        self._doc = document
        self._paths = None
        self._images = None
        self._links = None
        self._weblinks = None
        self._charlines = defaultdict(list)
        self._linked = False

        self.index = index
        self.number = index + 1
        LOGGER.debug(f"Loading: {index}")

        self._page = pp.FPDF_LoadPage(document._doc, index)
        self._text = pp.FPDFText_LoadPage(self._page)
        self._linkpage = pp.FPDFLink_LoadWebLinks(self._text)
        self._structtree = pp.FPDF_StructTree_GetForPage(self._page)
        # close them in reverse order
        weakref.finalize(self, pp.FPDF_StructTree_Close, self._structtree)
        weakref.finalize(self, pp.FPDFLink_CloseWebLinks, self._linkpage)
        weakref.finalize(self, pp.FPDFText_ClosePage, self._text)
        weakref.finalize(self, pp.FPDF_ClosePage, self._page)

        self._fix_bboxes()

    def text_in_area(self, area: Rectangle, max_length: int = 100) -> str:
        clength = ctypes.c_int(max_length)
        cbuffer = (ctypes.c_ushort * max_length)()
        length = pp.FPDFText_GetBoundedText(self._text, area.left, area.top, area.right,
                                            area.bottom, cbuffer, clength)
        return bytes(cbuffer).decode("utf-16-le", errors="ignore")[:length - 1]

    def chars_in_area(self, area: Rectangle) -> list[Character]:
        found = []
        # lines are ordered by ypos
        for ypos, chars in self.charlines.items():
            # We can stop the search if the ypos is above the area
            if ypos > area.top:
                break
            # otherwise we check if it's inside the area
            if area.bottom <= ypos:
                # chars are ordered by xpos
                for char in chars:
                    # we can stop looking into this line
                    if char.bbox.midpoint.x > area.right:
                        break
                    # otherwise we check if it's inside the area
                    if area.left <= char.bbox.midpoint.x:
                        found.append(char)
        return found

    @property
    def structures(self) -> list:
        count = pp.FPDF_StructTree_CountChildren(self._structtree)
        for ii in range(count):
            child = pp.FPDF_StructTree_GetChildAtIndex(self._structtree, ii)
            yield Structure(self, child)

    @cached_property
    def label(self) -> str:
        clength = ctypes.c_ulong(500)
        cbuffer = (ctypes.c_ushort * 500)()
        length = pp.FPDF_GetPageLabel(self._doc._doc, self.index, cbuffer, clength)
        return bytes(cbuffer).decode("utf-16-le", errors="ignore")[:length - 1]

    @cached_property
    def width(self) -> float:
        return pp.FPDF_GetPageWidthF(self._page)

    @cached_property
    def height(self) -> float:
        return pp.FPDF_GetPageHeightF(self._page)

    @cached_property
    def rotation(self) -> int:
        return pp.FPDFPage_GetRotation(self._page) * 90

    @cached_property
    def bbox(self) -> Rectangle:
        bbox = pp.FS_RECTF()
        assert pp.FPDF_GetPageBoundingBox(self._page, bbox)
        return Rectangle(bbox)

    @cached_property
    def char_count(self) -> int:
        return pp.FPDFText_CountChars(self._text)

    @cache
    def char(self, index) -> Character:
        return Character(self, index)

    @property
    def chars(self) -> list[Character]:
        for ii in range(self.char_count):
            yield self.char(ii)

    @cached_property
    def objlinks(self) -> list[ObjLink]:
        links = []
        pos = ctypes.c_int(0)
        link = pp.FPDF_LINK()
        while pp.FPDFLink_Enumerate(self._page, pos, link):
            links.append(ObjLink(self, link))
        return links

    @cached_property
    def weblinks(self) -> list[WebLink]:
        links = []
        for ii in range(pp.FPDFLink_CountWebLinks(self._linkpage)):
            links.append(WebLink(self, ii))
        return links

    def find(self, string, case_sensitive=True) -> list[Character]:
        flags = pp.FPDF_MATCHWHOLEWORD | pp.FPDF_CONSECUTIVE
        if case_sensitive:
            flags |= pp.FPDF_MATCHCASE

        wstring = (ctypes.c_ushort * (len(string) + 1))()
        for ii in range(len(string)):
            wstring[ii] = ord(string[ii])
        wstring[-1] = 0
        handle = pp.FPDFText_FindStart(self._text, wstring, flags, 0)

        while pp.FPDFText_FindNext(handle):
            start = pp.FPDFText_GetSchResultIndex(handle)
            count = pp.FPDFText_GetSchCount(handle)
            chars = [self.char(ii) for ii in range(start, start + count)]
            yield chars

        pp.FPDFText_FindClose(handle)

    def link_characters(self):
        if self._linked:
            return
        # The in-document links only gives us rectangles and we must find the
        # linked chars ourselves
        for link in self.objlinks:
            for char in self.chars_in_area(link.bbox):
                char.objlink = link
        # The weblinks give you an explicit char range, very convenient
        for link in self.weblinks:
            for ii in range(*link.range):
                self.char(ii).weblink = link
        self._linked = True

    def _fix_bboxes(self):
        def _key(char):
            height = round(char.tbbox.height, 1)
            width = round(char.tbbox.width, 1)
            return f"{char.font} {char.unicode} {height} {width}"
        fix_chars = []
        for char in self.chars:
            if not char._bbox.width or not char._bbox.height:
                if char._rotation:
                    fix_chars.append(char)
                elif char.unicode not in {0xa, 0xd}:
                    fix_chars.append(char)
            elif (char.unicode not in {0xa, 0xd} and not char._rotation and
                  _key(char) not in self._doc._bbox_cache):
                bbox = char._bbox.translated(-char.origin).rotated(self.rotation + char._rotation)
                self._doc._bbox_cache[_key(char)] = (char, bbox)
                # print("->", _key(char), char.descr(), char.height, char.rotation, char._rotation, self.rotation)
        for char in fix_chars:
            bbox = self._doc._bbox_cache.get(_key(char))
            if bbox is not None:
                # print("<-", char.descr(), char._rotation, char.rotation, char.height)
                _, bbox = bbox
                bbox = bbox.rotated(-self.rotation - char._rotation).translated(char.origin)
                char._bbox = bbox
            elif char.unicode not in {0x20, 0xa, 0xd}:
                LOGGER.debug(f"Unable to fix bbox for {char.descr()}!")

    @cached_property
    def charlines(self):
        charlines = defaultdict(list)
        for char in self.chars:
            charlines[round(char.bbox.midpoint.y, 1)].append(char)

        orderedchars = OrderedDict.fromkeys(sorted(charlines))
        for ypos, chars in charlines.items():
            orderedchars[ypos] = sorted(chars, key=lambda c: c.bbox.midpoint.x)

        return orderedchars

    def _objects(self, ftyp: int) -> list:
        count = pp.FPDFPage_CountObjects(self._page)
        objs = []
        for ii in range(count):
            obj = pp.FPDFPage_GetObject(self._page, ii)
            typ = pp.FPDFPageObj_GetType(obj)
            if typ == ftyp:
                if typ == pp.FPDF_PAGEOBJ_PATH:
                    objs.append(Path(self, obj))
                elif typ == pp.FPDF_PAGEOBJ_IMAGE:
                    objs.append(Image(self, obj))
        return objs

    @property
    def paths(self) -> list[Path]:
        if self._paths is None:
            self._paths = self._objects(pp.FPDF_PAGEOBJ_PATH)
        return self._paths

    @property
    def images(self):
        if self._images is None:
            self._images = self._objects(pp.FPDF_PAGEOBJ_IMAGE)
        return self._images

    def graphic_clusters(self, predicate=None, atol=None) -> list:
        if atol is None:
            atol = min(self.width, self.height) * 0.01

        # First collect all vertical regions
        filtered_paths = []
        for path in self.paths:
            if predicate is None or predicate(path):
                filtered_paths.append(path)
        for image in self.images:
            if predicate is None or predicate(image):
                filtered_paths.append(image)

        regions = []
        for path in sorted(filtered_paths, key=lambda l: l.bbox.y):
            for reg in regions:
                if reg.overlaps(path.bbox.bottom, path.bbox.top, atol):
                    # They overlap, so merge them
                    reg.v0 = min(reg.v0, path.bbox.bottom)
                    reg.v1 = max(reg.v1, path.bbox.top)
                    reg.objs.append(path)
                    break
            else:
                regions.append(Region(path.bbox.bottom, path.bbox.top, path))

        # Now collect horizontal region inside each vertical region
        for yreg in regions:
            for path in sorted(filtered_paths, key=lambda l: l.bbox.x):
                # check if horizontal line is contained in vregion
                if yreg.contains(path.bbox.y, atol):
                    for xreg in yreg.subregions:
                        if xreg.overlaps(path.bbox.left, path.bbox.right, atol):
                            # They overlap so merge them
                            xreg.v0 = min(xreg.v0, path.bbox.left)
                            xreg.v1 = max(xreg.v1, path.bbox.right)
                            xreg.objs.append(path)
                            break
                    else:
                        yreg.subregions.append(Region(path.bbox.left, path.bbox.right, path))

        clusters = []
        for yreg in regions:
            for xreg in yreg.subregions:
                if len(yreg.subregions) > 1:
                    # Strip down the height again for subregions
                    y0, y1 = 1e9, 0
                    for path in xreg.objs:
                        y0 = min(y0, path.bbox.bottom)
                        y1 = max(y1, path.bbox.top)
                else:
                    y0, y1 = yreg.v0, yreg.v1
                bbox = Rectangle(xreg.v0, y0, xreg.v1, y1)
                clusters.append((bbox, xreg.objs))

        return sorted(clusters, key=lambda c: (-c[0].y, c[0].x))
