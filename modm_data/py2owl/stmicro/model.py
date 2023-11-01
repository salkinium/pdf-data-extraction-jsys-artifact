# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

import modm_data.owl.stmicro as owl


def owl_from_datasheet(ds):
    with owl.store.namespace(ds.devices[0].string[:9].lower()):
        # Add device identifiers
        for dev in ds.devices:
            owl.Device(dev.string.lower())

        # Add package, pinouts, pins, signals
        data_packages, data_pins = ds.packages_pins
        # Add package and pinouts
        for package_name, data in data_packages.items():
            opackage = owl.Package(package_name)
            for pin_name, positions in data:
                opin = owl.Pin(pin_name)
                opackage.hasPin.append(opin)
                for pos in positions:
                    owl.pinPosition[opackage, owl.hasPin, opin].append(pos)

        # Add pins and additional functions
        for name, data in data_pins.items():
            opin = owl.Pin(name)
            if ios := data.get("structure"): opin.hasPinStructure = ios
            if ptype := data.get("type"): opin.hasPinType = ptype
            for signal in data.get("additional", []):
                opin.hasSignal.append(owl.AdditionalFunction(signal))
            for af, signals in data.get("alternate", {}).items():
                for signal in signals:
                    osig = owl.AlternateFunction(signal)
                    opin.hasSignal.append(osig)
                    owl.alternateFunction[opin, owl.hasSignal, osig].append(af)


def owl_from_reference_manual(rm):
    for dev in rm.device_filters:
        owl.DeviceFilter(dev.lower())

    with owl.store.namespace(rm.devices[0][:9].lower()):
        # Convert interrupt vector table to OWL
        for name, vtable in rm.vector_tables.items():
            otable = owl.InterruptTable(name)
            for pos, vectors in vtable.items():
                for vector in vectors:
                    ovector = owl.InterruptVector(vector)
                    otable.hasInterruptVector.append(ovector)
                    owl.vectorPosition[otable, owl.hasInterruptVector, ovector] = pos


def owl_from(doc):
    if doc.name.startswith("DS"):
        owl_from_datasheet(doc)
    elif doc.name.startswith("RM"):
        owl_from_reference_manual(doc)
