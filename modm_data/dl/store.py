# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

import os
import shutil
import logging
import tempfile
from pathlib import Path
from urllib.request import urlopen, Request

LOGGER = logging.getLogger(__name__)
_hdr = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
    'Accept-Encoding': 'none',
    'Accept-Language': 'en-US,en;q=0.8',
    'Connection': 'keep-alive'
}


def download_data(url: str, decode: bool = None) -> str:
    LOGGER.debug(f"Downloading data from {url}")
    with urlopen(Request(url, headers=_hdr)) as data:
        return data.read().decode(decode or "utf-8")


def download_file(url: str, path: Path, overwrite: bool = False) -> bool:
    if not overwrite and path.exists():
        LOGGER.error(f"File {path} already exists!")
        return False
    if isinstance(path, Path):
        path.parent.mkdir(parents=True, exist_ok=True)
    LOGGER.debug(f"Downloading file from {url} to {path}")
    with tempfile.NamedTemporaryFile() as outfile:
        os.system(f'wget -q --user-agent="{_hdr["User-Agent"]}" "{url}" -O {outfile.name}')
        shutil.copy(outfile.name, str(path))
    # This doesn't work with all PDFs, redirects maybe?
    # with urlopen(Request(url, headers=_hdr)) as infile, \
    #      tempfile.NamedTemporaryFile() as outfile:
    #     shutil.copyfileobj(infile, outfile)
    #     shutil.copy(outfile.name, str(path))
    return True
