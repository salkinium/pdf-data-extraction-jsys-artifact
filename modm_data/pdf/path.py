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
from enum import Enum
import pypdfium2 as pp
from ..utils import Point as uPoint, Rectangle, Line as uLine, Transform


class Path:
    class Type(Enum):
        LINE = 0
        BEZIER = 1
        MOVE = 2

    class Cap(Enum):
        BUTT = 0
        ROUND = 1
        PROJECTING_SQUARE = 2

    class Join(Enum):
        MITER = 0
        ROUND = 1
        BEVEL = 2

    class Point(uPoint):
        def __init__(self, x: float, y: float, ptype):
            super().__init__(x, y)
            self.type = ptype

        def __repr__(self) -> str:
            fmt = super().__repr__()
            return f"{fmt[:-1]},{self.type.name})"

    class Line(uLine):
        def __init__(self, p0, p1, ltype, width):
            super().__init__(p0, p1, width=width)
            self.type = ltype

        def __repr__(self) -> str:
            fmt = super().__repr__()
            return f"{fmt[:-1]},{self.type.name})>"

    def __init__(self, page, path):
        self._page = page
        self._path = path

    @cached_property
    def count(self) -> int:
        return pp.FPDFPath_CountSegments(self._path)

    @cached_property
    def fill(self) -> int:
        r, g, b, a = ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint()
        assert pp.FPDFPageObj_GetFillColor(self._path, r, g, b, a)
        return r.value << 24 | g.value << 16 | b.value << 8 | a.value

    @cached_property
    def stroke(self) -> int:
        r, g, b, a = ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint()
        assert pp.FPDFPageObj_GetStrokeColor(self._path, r, g, b, a)
        return r.value << 24 | g.value << 16 | b.value << 8 | a.value

    @cached_property
    def width(self) -> float:
        width = ctypes.c_float()
        assert pp.FPDFPageObj_GetStrokeWidth(self._path, width)
        return width.value

    @cached_property
    def cap(self) -> Cap:
        return Path.Cap(pp.FPDFPageObj_GetLineCap(self._path))

    @cached_property
    def join(self) -> Join:
        return Path.Join(pp.FPDFPageObj_GetLineJoin(self._path))

    @cached_property
    def bbox(self) -> Rectangle:
        l, b = ctypes.c_float(), ctypes.c_float()
        r, t = ctypes.c_float(), ctypes.c_float()
        assert pp.FPDFPageObj_GetBounds(self._path, l, b, r, t)
        bbox = Rectangle(l.value, b.value, r.value, t.value)
        if self._page.rotation:
            bbox = Rectangle(bbox.p0.y, self._page.height - bbox.p1.x,
                             bbox.p1.y, self._page.height - bbox.p0.x)
        return bbox

    @cached_property
    def matrix(self) -> Transform:
        mm = pp.FS_MATRIX()
        assert pp.FPDFPageObj_GetMatrix(self._path, mm)
        return Transform(mm)

    @cached_property
    def points(self) -> list[Point]:
        points = []

        for ii in range(self.count):
            seg = pp.FPDFPath_GetPathSegment(self._path, ii)
            ptype = Path.Type(pp.FPDFPathSegment_GetType(seg))
            if ii == 0:
                # The first point should always be MOVETO
                assert ptype == Path.Type.MOVE

            x, y = ctypes.c_float(), ctypes.c_float()
            assert pp.FPDFPathSegment_GetPoint(seg, x, y)
            p = self.matrix.map(uPoint(x.value, y.value))
            points.append(Path.Point(p.x, p.y, ptype))

            if pp.FPDFPathSegment_GetClose(seg):
                points.append(Path.Point(points[0].x, points[0].y, Path.Type.LINE))

        if self._page.rotation:
            points = [Path.Point(p.y, self._page.height - p.x, p.type) for p in points]
        return points

    @cached_property
    def lines(self) -> list[Line]:
        points = self.points
        return [Path.Line(points[ii], points[ii + 1], points[ii + 1].type, self.width)
                for ii in range(len(points) - 1)]

    def __repr__(self) -> str:
        points = ",".join(repr(p) for p in self.points)
        return f"P{self.count}{points}"
