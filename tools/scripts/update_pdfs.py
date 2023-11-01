# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

import os
import sys
import shutil
import tempfile
sys.path.append(".")

import modm_data.pdf
from modm_data.dl.stmicro import load_remote_info, store_remote_info
from modm_data.dl.stmicro import load_local_info, store_local_info, Document

import logging
logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger("update")

remote_info = load_remote_info(use_cached=False)
store_remote_info(remote_info)

remote_docs = set(map(Document, remote_info))
# for doc in sorted(remote_docs, key=lambda d: d.filename):
#     LOGGER.debug(f"Raw Remote: {doc}")
# remote_docs = set(filter(lambda d: d._short_type in {"RM", "DS", "ES", "UM", "TN", "PM", "DB"}, remote_docs))
# for doc in sorted(remote_docs, key=lambda d: d.filename):
#     LOGGER.info(f"Remote: {doc}")

local_docs = set(map(Document, load_local_info()))
# for doc in sorted(remote_docs, key=lambda d: d.filename):
#     LOGGER.debug(f"Local: {doc}")

new_remote_docs = sorted(remote_docs - local_docs, key=lambda d: d.filename)
for doc in sorted(new_remote_docs, key=lambda d: d.filename):
    LOGGER.info(f"New documents: {doc}")

new_local_docs = list(local_docs)
invalid_docs = []
for doc in new_remote_docs:
    with tempfile.NamedTemporaryFile() as outfile:
        if doc.store_pdf(overwrite=True, path=outfile.name):
            # Validate the PDF content
            sdoc = modm_data.pdf.Document(outfile.name)
            if sdoc.page_count > 0 and sdoc.page(0).width:
                new_local_docs.append(doc)
                shutil.copy(outfile.name, doc.location)
            else:
                invalid_docs.append(doc)

store_local_info([doc.data for doc in new_local_docs])

if invalid_docs:
    print("=======================================")
    print(f"{len(invalid_docs)} invalid documents!")
    for doc in invalid_docs:
        print(doc, doc.url)
