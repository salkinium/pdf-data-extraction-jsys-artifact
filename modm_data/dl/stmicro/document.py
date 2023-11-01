# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

import logging
from functools import cached_property
from ..store import download_file
from ...utils import cache_path

LOGGER = logging.getLogger(__name__)


class Document:
    def __init__(self, data):
        # Primary information from JSON data
        self._title = data["title"]
        self._description = data["localizedDescriptions"]["en"]
        self._url = data["localizedLinks"]["en"]
        self._version = data["version"]
        self._update = data["latestUpdate"]
        self._type = data.get("resourceType", "Unknown")

        # Derived information
        self._short_type = self._title[:2]
        self.filename = self._title + "-v" + \
                self._version.replace(".0", "").replace(".", "_") + ".pdf"
        self.url = "https://www.st.com" + self._url
        self.location = cache_path("stmicro-pdf/" + self.filename)

    @property
    def data(self) -> dict:
        return {
            "title": self._title,
            "localizedDescriptions": {"en": self._description},
            "localizedLinks": {"en": self._url},
            "version": self._version,
            "latestUpdate": self._update,
            "resourceType": self._type,
        }

    def store_pdf(self, overwrite: bool = False, path: str = None) -> bool:
        return download_file(self.url, path or self.location, overwrite=overwrite)

    def __repr__(self) -> str:
        return f"Doc({self._title} v{self._version.replace('.0', '')})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, type(self)):
            return False
        return self.filename == other.filename

    def __hash__(self) -> int:
        return hash(self.filename)
