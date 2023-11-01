# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

import math
import ctypes
from functools import cached_property
from enum import Enum
import pypdfium2 as pp
from ..utils import Rectangle, Point


class Character:
    class RenderMode(Enum):
        UNKNOWN = -1
        FILL = 0
        STROKE = 1
        FILL_STROKE = 2
        INVISIBLE = 3
        FILL_CLIP = 4
        STROKE_CLIP = 5
        FILL_STROKE_CLIP = 6
        CLIP = 7

    def __init__(self, page, index: int):
        self._page = page
        self._text = page._text
        self._index = index
        self._font = None
        self.unicode = pp.FPDFText_GetUnicode(self._text, self._index)
        self._rotation = int(math.degrees(pp.FPDFText_GetCharAngle(self._text, self._index)))
        self.objlink = None
        self.weblink = None

        crect = pp.FS_RECTF()
        assert pp.FPDFText_GetLooseCharBox(self._text, self._index, crect)
        bbox = Rectangle(crect)
        if self._page.rotation:
            bbox = Rectangle(bbox.p0.y, self._page.height - bbox.p1.x,
                             bbox.p1.y, self._page.height - bbox.p0.x)
        self._bbox = bbox

    def _font_flags(self) -> tuple[str, int]:
        if self._font is None:
            font = ctypes.create_string_buffer(255)
            flags = ctypes.c_int()
            pp.FPDFText_GetFontInfo(self._text, self._index, font, 255, flags)
            self._font = (font.value.decode("utf-8"), flags.value)
        return self._font

    @property
    def char(self) -> str:
        char = chr(self.unicode)
        return char if char.isprintable() else ""

    @cached_property
    def origin(self) -> Point:
        x, y = ctypes.c_double(), ctypes.c_double()
        assert pp.FPDFText_GetCharOrigin(self._text, self._index, x, y)
        if self._page.rotation:
            return Point(y.value, self._page.height - x.value)
        return Point(x.value, y.value)

    @cached_property
    def width(self) -> float:
        if self.rotation:
            return self.bbox.height
        return self.bbox.width

    @cached_property
    def height(self) -> float:
        if self.rotation:
            return self.bbox.width
        return self.bbox.height

    @cached_property
    def tbbox(self) -> Rectangle:
        x0, y0 = ctypes.c_double(), ctypes.c_double()
        x1, y1 = ctypes.c_double(), ctypes.c_double()
        assert pp.FPDFText_GetCharBox(self._text, self._index, x0, x1, y0, y1)
        tbbox = Rectangle(x0.value, y0.value, x1.value, y1.value)
        if self._page.rotation:
            tbbox = Rectangle(tbbox.p0.y, self._page.height - tbbox.p1.x,
                              tbbox.p1.y, self._page.height - tbbox.p0.x)
        return tbbox

    @property
    def bbox(self) -> Rectangle:
        if not self._bbox.width or not self._bbox.height:
            return self.tbbox
        return self._bbox

    @cached_property
    def twidth(self) -> float:
        return self.tbbox.twidth

    @cached_property
    def theight(self) -> float:
        return self.tbbox.theight

    @cached_property
    def render_mode(self) -> RenderMode:
        return Character.RenderMode(pp.FPDFText_GetTextRenderMode(self._text, self._index))

    @cached_property
    def rotation(self) -> int:
        # Special case for vertical text in rotated pages
        if self._page.rotation == 90 and self._rotation == 0 and self.unicode not in {0x20, 0xa, 0xd}:
            return 90
        if self._page.rotation and self._rotation:
            return (self._page.rotation + self._rotation) % 360
        return self._rotation

    @cached_property
    def size(self) -> float:
        return pp.FPDFText_GetFontSize(self._text, self._index)

    @cached_property
    def weight(self) -> int:
        return pp.FPDFText_GetFontWeight(self._text, self._index)

    @cached_property
    def fill(self) -> tuple[int, int, int, int]:
        r, g, b, a = ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint()
        pp.FPDFText_GetFillColor(self._text, self._index, r, g, b, a)
        return r.value << 24 | g.value << 16 | b.value << 8 | a.value

    @cached_property
    def stroke(self) -> int:
        r, g, b, a = ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint()
        pp.FPDFText_GetStrokeColor(self._text, self._index, r, g, b, a)
        return r.value << 24 | g.value << 16 | b.value << 8 | a.value

    @cached_property
    def font(self) -> str:
        return self._font_flags()[0]

    @cached_property
    def flags(self) -> int:
        return self._font_flags()[1]

    def descr(self) -> str:
        char = chr(self.unicode)
        if not char.isprintable():
            char = hex(self.unicode)
        return f"Chr({char}, {self.size}, {self.weight}, {self.rotation}, " \
               f"{self.render_mode}, {self.font}, {hex(self.flags)}, " \
               f"{self.fill}, {self.stroke}, {repr(self.bbox)})"

    def __str__(self) -> str:
        return self.char

    def __repr__(self) -> str:
        char = chr(self.unicode)
        escape = {0xa: "\\n", 0xd: "\\r", 0x9: "\\t", 0x20: "␣"}
        char = escape.get(self.unicode, char if char.isprintable() else hex(self.unicode))
        return char
