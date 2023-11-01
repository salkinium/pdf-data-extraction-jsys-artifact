# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

import os
import re
import sys
import argparse
from collections import defaultdict
from pathlib import Path
import multiprocessing
sys.path.extend([".", "ext/modm-devices"])

import modm_data.cubemx
from modm_data.header2svd.stmicro import Header, normalize_memory_map
from modm_data.svd import format_svd, write_svd
from modm_data.html2py.stmicro import did_from_string
from modm_data.utils import cache_path
from anytree import RenderTree


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", type=str, default=[], action="append")
    parser.add_argument("--all", type=str, default=[], action="append")
    args = parser.parse_args()

    if args.all:
        devices = modm_data.cubemx.devices()
        filtered_devices = [d for d in devices if any(re.match(pat, d.string) for pat in args.all)]

        headers = defaultdict(list)
        for device in reversed(filtered_devices):
            header = Header(device)
            headers[header.filename].append(device.string)
        header_devices = list(headers.values())
        Path("log/stmicro/svd-header").mkdir(exist_ok=True, parents=True)

        calls = [f"python3 {__file__} --device {' --device '.join(devices)} "
                 f" > log/stmicro/svd-header/{list(sorted(devices))[0]}.txt 2>&1"
                 for devices in header_devices]

        with multiprocessing.Pool() as pool:
            retvals = pool.map(os.system, calls)
        for ii, retval in enumerate(retvals):
            if os.WEXITSTATUS(retval) != 0: print(calls[ii])
        return all(os.WEXITSTATUS(r) == 0 for r in retvals)
    else:
        mmaps = defaultdict(list)
        headers = {}
        # create one or multiple mmaps from device set
        for device in args.device:
            device = did_from_string(device)
            header = Header(device)
            print(device.string, header.filename)
            mmaptree = header.memory_map_tree # create cache entry
            mmaps[header._memory_map_key].append(device)
            headers[header._memory_map_key] = header

        # Create one SVD file for each memory map
        for key, devices in mmaps.items():
            header = headers[key]
            mmaptree = header._cache[key]
            mmaptree.compatible = list(sorted(devices, key=lambda d: d.string))
            mmaptree = normalize_memory_map(mmaptree)
            print(RenderTree(mmaptree, maxlevel=2))
            svd = format_svd(mmaptree)
            output_path = cache_path(f"stmicro-svd/header_{mmaptree.compatible[0].string}.svd")
            write_svd(svd, str(output_path))
        return True


if __name__ == "__main__":
    exit(0 if main() else 1)
