# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

import ctypes
from functools import cached_property, cache
import pypdfium2 as pp


class Structure:
    def __init__(self, page, element, parent=None):
        self._page = page
        self._element = element
        self._parent = None

    def _get_string(self, function, max_length: int = 1000) -> str:
        clength = ctypes.c_ulong(max_length)
        cbuffer = (ctypes.c_ushort * max_length)()
        function(self._element, cbuffer, clength)
        return bytes(cbuffer).decode("utf-16-le", errors="ignore")

    @cached_property
    def title(self) -> str:
        return self._get_string(pp.FPDF_StructElement_GetTitle)

    @cached_property
    def alt_text(self) -> str:
        return self._get_string(pp.FPDF_StructElement_GetAltText)

    @cached_property
    def type(self) -> str:
        return self._get_string(pp.FPDF_StructElement_GetType)

    @cached_property
    def language(self) -> str:
        return self._get_string(pp.FPDF_StructElement_GetLang)

    @cached_property
    def id(self) -> str:
        return self._get_string(pp.FPDF_StructElement_GetID)

    @cached_property
    def marked_id(self) -> int:
        return pp.FPDF_StructElement_GetMarkedContentID(self._element)

    def attribute(self, name, max_length: int = 1000) -> str:
        clength = ctypes.c_ulong(max_length)
        cbuffer = (ctypes.c_ushort * max_length)()
        length = pp.FPDF_StructElement_GetStringAttribute(self._element, name, cbuffer, clength)
        return bytes(cbuffer).decode("utf-16-le", errors="ignore")[:length - 1]
        return pp.FPDF_StructElement_GetMarkedContentID(self._element)

    @cache
    def child(self, index: int):
        child = pp.FPDF_StructElement_GetChildAtIndex(self._element, index)
        return Structure(self._page, child, self)

    @property
    def children(self) -> list:
        count = pp.FPDF_StructElement_CountChildren(self._element)
        for ii in range(count):
            yield self.child(ii)

    def descr(self, indent=0) -> str:
        string = " " * indent + repr(self) + "\n"
        for child in self.children:
            string += child.descr(indent + 2)
        return string

    def __repr__(self) -> str:
        name = self.attribute("name")
        string = self.attribute("string")
        return f"S({self.type}: {self.title or self.alt_text}, {self.id or self.marked_id}, {name}, {string})"
