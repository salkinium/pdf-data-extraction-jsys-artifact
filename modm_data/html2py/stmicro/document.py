# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

from collections import defaultdict
from ...html import Document
from ...utils import cache_path
from .datasheet import DatasheetMicro, DatasheetSensor
from .reference import ReferenceManual
from .identifier import DeviceIdentifier


def load_documents() -> list:
    documents = defaultdict(dict)
    for path in sorted(cache_path("stmicro-html").glob("*-v*")):
        # This doc is parsed wrongly since it has a DRAFT background
        if path.stem in ["DS12960-v5"]: continue
        # This doc has a preliminary ordering information STM32WBA52CGU6TR
        if "DS14127" in path.stem: continue
        doc = Document(path)
        if "DS" in doc.name and (chap := doc.chapters("chapter 0")):
            # FIXME: Better detection that DS13252 is a STM32WB55 module, not a chip!
            if any("STM32" in h.html for h in chap[0].headings()) and \
                "DS13252" not in doc.name and "DS14096" not in doc.name:
                documents[doc.name][doc.version] = DatasheetMicro(path)
            else:
                documents[doc.name][doc.version] = DatasheetSensor(path)
        elif "RM" in doc.name:
            documents[doc.name][doc.version] = ReferenceManual(path)
    return documents


def load_document_devices() -> \
                        tuple[dict[DatasheetMicro, list[DeviceIdentifier]],
                              dict[ReferenceManual, list[DeviceIdentifier]]]:
    dss = defaultdict(set)
    rms = defaultdict(set)
    for name, versions in load_documents().items():
        # Always choose the latest version
        doc = list(versions.values())[-1]
        # print(doc.path_pdf.relative_to(Path().cwd()), doc.path.relative_to(Path().cwd()))
        # print(doc.devices)
        if isinstance(doc, DatasheetMicro):
            if not doc.devices:
                raise ValueError(f"{doc} has no associated devices!")
            for dev in doc.devices:
                dss[dev].add(doc)
        elif isinstance(doc, ReferenceManual):
            if not doc.devices:
                raise ValueError(f"{doc} has no associated devices!")
            for dev in doc.devices:
                rms[dev].add(doc)

    for dev, docs in dss.items():
        if len(docs) != 1:
            raise ValueError(f"One device points to multiple datasheets! {dev} -> {docs}")
    datasheets = {did:list(ds)[0] for did, ds in dss.items()}
    # print(len(datasheets.keys()), sorted(list(d.string for d in datasheets.keys())))

    manuals = defaultdict(set)
    for dev, docs in rms.items():
        if len(docs) != 1:
            raise ValueError(f"One device points to multiple reference manuals! {dev} -> {docs}")
        for dev in list(docs)[0].filter_devices(datasheets.keys()):
            manuals[dev].add(list(docs)[0])

    for dev, docs in manuals.items():
        if len(docs) != 1:
            raise ValueError(f"One device points to multiple reference manuals! {dev} -> {docs}")

    reference_manuals = {did:list(rm)[0] for did, rm in manuals.items()}

    return datasheets, reference_manuals
