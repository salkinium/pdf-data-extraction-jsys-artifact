# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

import os, re, sys, argparse
sys.path.extend([".", "ext/modm-devices"])
from collections import defaultdict
from pathlib import Path

import modm_devices.parser
import modm_data.owl.stmicro as owl
from modm_data.html2py.stmicro import load_document_devices
import modm_data.cubemx
import modm_data.owl2py.stmicro


def compare_device_identifiers():

    modm_devices_ids = set(k.string.split("@")[0] for k in modm_data.cubemx.devices())
    datasheet_owl_ids = set(modm_data.owl2py.stmicro.owl_devices())

    print(f"modm-devices={len(modm_devices_ids)} vs datasheet-owl={len(datasheet_owl_ids)}")

    for length in [9, 10, 11, 12, 13, 14]:
        print("\n\n" + "=" * 70 + "\n\n")
        print(f"Comparing identifiers up to length {length}...")

        mdids = set(d[:length] for d in modm_devices_ids)
        ddids = set(d[:length] for d in datasheet_owl_ids)
        print(f"modm-devices={len(mdids)} vs datasheet-owl={len(ddids)}")

        unknown_modm_devices_ids = mdids - ddids
        unknown_datasheet_owl_ids = ddids - mdids
        print(f"Unknown modm-devices ids: {len(unknown_modm_devices_ids)}")
        print(f"Unknown datasheet-owl ids: {len(unknown_datasheet_owl_ids)}")

        print(sorted(list(unknown_modm_devices_ids)))

        print("Filtering away known unknown devices")
        unknowns = {
            "stm32g071.6",  # No datasheet, not mentioned on website
            "stm32g441",    # DRAFT datasheet
            "stm32g471",    # No datasheet, not mentioned on website
            "stm32l041c4",  # No datasheet, not mentioned on website
            "stm32l485",    # No datasheet, not mentioned on website
        }
        mdids = set(d for d in mdids if not any(re.match(u, d) for u in unknowns))
        ddids = set(d for d in ddids if not any(re.match(u, d) for u in unknowns))
        print(f"modm-devices={len(mdids)} vs datasheet-owl={len(ddids)}")

        unknown_modm_devices_ids = mdids - ddids
        unknown_datasheet_owl_ids = ddids - mdids
        print(f"Unknown modm-devices ids: {len(unknown_modm_devices_ids)}")
        print(f"Unknown datasheet-owl ids: {len(unknown_datasheet_owl_ids)}")

        print(sorted(list(unknown_modm_devices_ids)))


if __name__ == "__main__":
    load_document_devices()
    print("Unambiguous mapping: Identifier -> Datasheet + Reference Manuals")
    compare_device_identifiers()

