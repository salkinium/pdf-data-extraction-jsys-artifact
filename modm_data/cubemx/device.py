# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

import logging
from ..utils import root_path, cache_path
from ..html2py.stmicro import did_from_string, DeviceIdentifier
import modm_devices.parser
import json

LOGGER = logging.getLogger(__name__)
_DEVICE_MAPPING = None
_DEVICE_PARTIAL_MAPPING = {}
_DEVICE_NAMES_FILE = cache_path("modm_devices.json")
_DEVICE_MAP_FILE = cache_path("modm_device_files.json")


def device_files() -> dict[DeviceIdentifier]:
    global _DEVICE_MAPPING, _DEVICE_NAMES_FILE, _DEVICE_MAP_FILE
    if _DEVICE_MAPPING is None:
        _DEVICE_MAPPING = {}
        device_file_map = {}

        device_files = root_path("ext/modm-devices/devices/").glob("*/stm32*.xml")
        parser = modm_devices.parser.DeviceParser()
        for device_file_name in device_files:
            device_file = parser.parse(str(device_file_name))
            for device in device_file.get_devices():
                _DEVICE_MAPPING[device.identifier] = device
                device_file_map[device.identifier.string] = str(device_file_name)

        names = sorted(device_file_map.keys())
        _DEVICE_NAMES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with _DEVICE_NAMES_FILE.open('w', encoding='utf-8') as fh:
            json.dump(names, fh, indent=4)

        _DEVICE_MAP_FILE.parent.mkdir(parents=True, exist_ok=True)
        with _DEVICE_MAP_FILE.open('w', encoding='utf-8') as fh:
            json.dump(device_file_map, fh, indent=4)

    return _DEVICE_MAPPING


def devices() -> list[DeviceIdentifier]:
    global _DEVICE_NAMES_FILE
    if not _DEVICE_NAMES_FILE.exists():
        return list(sorted(device_files().keys(), key=lambda d: d.string))

    with _DEVICE_NAMES_FILE.open('r', encoding='utf-8') as fh:
        names = json.load(fh)
    return [did_from_string(n) for n in names]


def device_file(device):
    global _DEVICE_PARTIAL_MAPPING, _DEVICE_MAP_FILE
    if (dfile := _DEVICE_PARTIAL_MAPPING.get(device)) is not None:
        return dfile
    if not _DEVICE_MAP_FILE.exists():
        return device_files().get(device)

    with _DEVICE_MAP_FILE.open('r', encoding='utf-8') as fh:
        did_file_map = json.load(fh)
    dfile = did_file_map.get(device.string)
    if dfile is None:
        LOGGER.error(f"Cannot find device file for {device}!")
        return None

    parser = modm_devices.parser.DeviceParser()
    device_file = parser.parse(dfile)
    for ddev in device_file.get_devices():
        _DEVICE_PARTIAL_MAPPING[ddev.identifier] = ddev

    return _DEVICE_PARTIAL_MAPPING.get(device)
