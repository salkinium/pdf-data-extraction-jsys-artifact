# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

import math
from ..utils import Rectangle


class Figure:
    def __init__(self, page, bbox: Rectangle, cbbox: Rectangle = None, paths: list = None):
        self._page = page
        self.bbox = bbox
        self.cbbox = cbbox
        self._type = "figure"
        self._paths = paths or []

    def format_ascii(self, with_ansi: bool = True) -> str:
        width = max(12, math.floor(self.bbox.width / self._spacing["x_em"]))
        hline = "\n+" + "-" * (width - 2) + "+"
        figure = hline
        figure += "\n|" + "[Figure]".center(width - 2) + "|"
        figure += hline
        return figure

    def __repr__(self) -> str:
        return f"Figure({int(self.bbox.width)}x{int(self.bbox.height)})"
