# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

import re
import CppHeaderParser
from ..utils import root_path
from collections import defaultdict


class Header:
    CMSIS_PATH =  root_path("ext/cmsis/header/CMSIS/Core/Include")
    CACHE_HEADER = defaultdict(dict)

    def __init__(self, filename, substitutions=None):
        self.filename = filename
        self.substitutions = {r"__(IO|IM|I|O)": ""}
        if substitutions is not None:
            self.substitutions.update(substitutions)

    @property
    def _cache(self):
        return Header.CACHE_HEADER[self.filename]

    @property
    def header(self):
        if "header" not in self._cache:
            content = self.filename.read_text(encoding="utf-8-sig", errors="replace")
            for pattern, subs in self.substitutions.items():
                content = re.sub(pattern, subs, content, flags=(re.DOTALL | re.MULTILINE))
            header = CppHeaderParser.CppHeader(content, "string")
            self._cache["header"] = header
        return self._cache["header"]

