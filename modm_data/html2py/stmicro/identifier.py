# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

from modm_devices.device_identifier import DeviceIdentifier as Did


class DeviceIdentifier(Did):
    def __init__(self, naming_schema=None):
        super().__init__(naming_schema)
        self._descr = {}


def did_from_string(string) -> DeviceIdentifier:
    string = string.lower()

    if string.startswith("stm32"):
        schema = "{platform}{family}{name}{pin}{size}{package}{temperature}{variant}"
        if "@" in string:
            schema += "@{core}"
        i = DeviceIdentifier(schema)
        i.set("platform", "stm32")
        i.set("family", string[5:7])
        i.set("name", string[7:9])
        i.set("pin", string[9])
        i.set("size", string[10])
        i.set("package", string[11])
        i.set("temperature", string[12])
        if "@" in string:
            string, core = string.split("@")
            i.set("core", core)
        if len(string) >= 14:
            i.set("variant", string[13])
        else:
            i.set("variant", "")
        return i

    raise ValueError(f"Unknown identifier '{string}'!")


def split_device_filter(device_filter: str) -> list[str]:
    devices = []
    if len(parts := device_filter.split("/")) >= 2:
        base = parts[0]
        devices.append(base)
        base = base[:-len(parts[1])]
        for part in parts[1:]:
            devices.append(base + part)
    else:
        devices.append(device_filter)
    return devices
