# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

import os.path
import logging
import weakref
import ctypes
from functools import cached_property
from collections import defaultdict
import pypdfium2 as pp
from .page import Page

LOGGER = logging.getLogger(__name__)


class OutlineItem:
    def __init__(self, level: int, title: str, page: int):
        self.level = level
        self.title = title
        self.page = page

    def __hash__(self) -> int:
        return hash(f"{self.page}+{self.title}")

    def __eq__(self, other) -> bool:
        if not isinstance(other, type(self)): return NotImplemented
        return self.page == other.page and self.title == other.title

    def __repr__(self) -> str:
        return f"O({self.page}, {self.level}, {self.title})"


class Document:
    def __init__(self, path: str):
        self._path = str(path)
        self._name = os.path.basename(str(path))
        self._bbox_cache = defaultdict(dict)

        # open the PDF document
        self._doc = pp.FPDF_LoadDocument(str(path), None)
        LOGGER.debug(f"Loading: {path}")
        # defer closing the PDF document
        weakref.finalize(self, pp.FPDF_CloseDocument, self._doc)

    @property
    def name(self) -> str:
        return self._name.replace(".pdf", "")

    @cached_property
    def metadata(self) -> dict[str, str]:
        data = {}
        # Refer to PDF Reference 1.7, section 10.2.1: Document Information Dictionary
        tags = ["Title", "Author", "Subject", "Keywords", "Creator",
                "Producer", "CreationDate", "ModDate", "Trapped"]
        for tag in tags:
            clength = ctypes.c_ulong(250)
            cbuffer = ctypes.create_string_buffer(clength.value)
            ctag = ctypes.c_char_p(tag.encode("ascii"))
            if pp.FPDF_GetMetaText(self._doc, ctag, cbuffer, clength):
                value = cbuffer.raw.decode("utf-16-le").rstrip("\x00")
                if value:
                    data[tag] = value
        return data

    @property
    def destinations(self) -> list[tuple[int, str]]:
        for ii in range(pp.FPDF_CountNamedDests(self._doc)):
            clength = ctypes.c_long(500)
            cbuffer = ctypes.create_string_buffer(1000)
            dest = pp.FPDF_GetNamedDest(self._doc, ii, cbuffer, clength)
            name = cbuffer.raw[:clength.value*2].decode("utf-16-le").rstrip("\x00")
            page = pp.FPDFDest_GetDestPageIndex(self._doc, dest)
            yield (page, name)

    @property
    def toc(self) -> list[OutlineItem]:
        tocs = set()
        # Sometimes the TOC contains duplicates so we must use a set
        for toc in pp.get_toc(self._doc):
            tocs.add(OutlineItem(toc.level, toc.title, toc.page_index))
        return list(sorted(list(tocs), key=lambda o: (o.page, o.level, o.title)))

    @cached_property
    def is_tagged(self) -> bool:
        return bool(pp.FPDFCatalog_IsTagged(self._doc))

    def _identifier(self, typ: int) -> str:
        clength = ctypes.c_ulong(250)
        cbuffer = ctypes.create_string_buffer(clength.value)
        length = pp.FPDF_GetFileIdentifier(self._doc, typ, cbuffer, clength)
        return cbuffer.raw[:length - 1]

    @cached_property
    def identifier_permanent(self) -> str:
        return self._identifier(0)

    @cached_property
    def identifier_changing(self) -> str:
        return self._identifier(1)

    @cached_property
    def page_count(self) -> str:
        return pp.FPDF_GetPageCount(self._doc)

    def page(self, index: int) -> Page:
        assert index < self.page_count
        return Page(self, index)

    def pages(self, numbers=None) -> list[Page]:
        if numbers is None:
            numbers = range(self.page_count)
        for ii in numbers:
            if 0 <= ii < self.page_count:
                yield self.page(ii)

    def __repr__(self) -> str:
        return f"Doc({self._name})"
