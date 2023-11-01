# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

import ctypes
from functools import cached_property
import pypdfium2 as pp
from ..utils import Point, Rectangle, Line, Transform


class Image:
    def __init__(self, page, image):
        self._page = page
        self._image = image

    @cached_property
    def bbox(self) -> Rectangle:
        l, b = ctypes.c_float(), ctypes.c_float()
        r, t = ctypes.c_float(), ctypes.c_float()
        assert pp.FPDFPageObj_GetBounds(self._image, l, b, r, t)
        bbox = Rectangle(l.value, b.value, r.value, t.value)
        if self._page.rotation:
            bbox = Rectangle(bbox.p0.y, self._page.height - bbox.p1.x,
                             bbox.p1.y, self._page.height - bbox.p0.x)
        return bbox

    @cached_property
    def matrix(self) -> Transform:
        mm = pp.FS_MATRIX()
        assert pp.FPDFPageObj_GetMatrix(self._image, mm)
        return Transform(mm)

    @property
    def count(self) -> int:
        return 4

    @property
    def stroke(self) -> int:
        return 0

    @property
    def fill(self) -> int:
        return 0

    @property
    def width(self) -> float:
        return 0

    @cached_property
    def points(self) -> list[Point]:
        points = self.bbox.points
        if self._page.rotation:
            points = [Point(p.y, self._page.height - p.x, p.type) for p in points]
        return points

    @cached_property
    def lines(self) -> list[Line]:
        p = self.points
        return [Line(p[0], p[1], p[1].type, 0),
                Line(p[1], p[2], p[2].type, 0),
                Line(p[2], p[3], p[3].type, 0),
                Line(p[3], p[0], p[0].type, 0)]

    def __repr__(self) -> str:
        return f"I{self.bbox}"
