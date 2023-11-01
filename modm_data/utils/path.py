# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

from pathlib import Path

def root_path(path) -> Path:
    return Path(__file__).parents[2] / path

def cache_path(path) -> Path:
    return root_path(Path("ext/cache") / path)

def patch_path(path) -> Path:
    return root_path(Path("patches") / path)
