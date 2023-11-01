# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

import re
from functools import cached_property
from .text import replace as html_replace, Text


class List(Text):
    def __init__(self, html):
        self._html = html

    def __repr__(self) -> str:
        return f"List({self.text()[:10]})"
