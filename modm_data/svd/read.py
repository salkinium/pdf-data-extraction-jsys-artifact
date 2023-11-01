# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

from .model import *


def read_svd(path) -> Device:
    from cmsis_svd.parser import SVDParser

    parser = SVDParser.for_xml_file(path)
    pdev = parser.get_device()
    device = Device(pdev.name, compatible=pdev.description.split(","))

    for peripheral in pdev.peripherals:
        ptype = peripheral.get_derived_from()
        if ptype is not None: ptype = ptype.name
        nper = Peripheral(peripheral.name, ptype, peripheral.base_address, parent=device)
        for register in peripheral.registers:
            nreg = Register(register.name, register.address_offset,
                            register.size//8, parent=nper)
            for field in register.fields:
                BitField(field.name, field.bit_offset, field.bit_width, parent=nreg)

    return device
