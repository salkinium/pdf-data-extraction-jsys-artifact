# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

import copy
import ctypes
from functools import cached_property
import pypdfium2 as pp
from ..utils import Rectangle, Transform


class ObjLink:
    def __init__(self, page, link):
        self._page = page
        self._dest = pp.FPDFLink_GetDest(page._doc._doc, link)

        bbox = pp.FS_RECTF()
        assert pp.FPDFLink_GetAnnotRect(link, bbox)
        bbox = Rectangle(bbox)
        if page.rotation:
            bbox = Rectangle(bbox.p0.y, page.height - bbox.p1.x,
                             bbox.p1.y, page.height - bbox.p0.x)
        self.bbox = bbox

    @cached_property
    def page_index(self) -> int:
        return pp.FPDFDest_GetDestPageIndex(self._page._doc._doc, self._dest)

    def __repr__(self) -> str:
        return f"Obj({self.page_index})"


class WebLink:
    def __init__(self, page, index):
        self._page = page
        self._link = page._linkpage
        self._index = index

    @cached_property
    def bbox_count(self) -> int:
        return pp.FPDFLink_CountRects(self._link, self._index)

    @cached_property
    def bboxes(self) -> list[Rectangle]:
        bboxes = []
        for ii in range(self.bbox_count):
            x0, y0 = ctypes.c_double(), ctypes.c_double()
            x1, y1 = ctypes.c_double(), ctypes.c_double()
            assert pp.FPDFLink_GetRect(self._link, self._index, ii, x0, y1, x1, y0)
            bboxes.append(Rectangle(x0.value, y0.value, x1.value, y1.value))
        if self._page.rotation:
            bboxes = [Rectangle(bbox.p0.y, self._page.height - bbox.p1.x,
                                bbox.p1.y, self._page.height - bbox.p0.x)
                      for bbox in bboxes]
        return bboxes

    @cached_property
    def range(self) -> tuple[int, int]:
        cstart = ctypes.c_int()
        ccount = ctypes.c_int()
        assert pp.FPDFLink_GetTextRange(self._link, self._index, cstart, ccount)
        return (cstart.value, cstart.value + ccount.value)

    @cached_property
    def url(self) -> str:
        length = 1000
        cbuffer = ctypes.c_ushort * length
        cbuffer = cbuffer()
        retlen = pp.FPDFLink_GetURL(self._link, self._index, cbuffer, length)
        assert retlen < length
        return bytes(cbuffer).decode("utf-16-le").strip("\x00")

    def __repr__(self) -> str:
        return f"Url({self.url})"
