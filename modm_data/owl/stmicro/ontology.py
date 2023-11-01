# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

import re
import owlready2 as owl
from .. import Store


store = Store("stmicro")
ontology = store.ontology


# ================================ ANNOTATIONS ================================
class devices(owl.AnnotationProperty):
    namespace = ontology
    comment = "Contains the list of device identifiers that applies to the entity/relation."

class alternateFunction(owl.AnnotationProperty):
    namespace = ontology
    comment = "The AF number attached to the [Pin, hasSignal, AlternateFunction] relation."

class vectorPosition(owl.AnnotationProperty):
    namespace = ontology
    comment = "The AF number attached to the [InterruptTable, hasInterruptVector, AlternateFunction] relation."

class pinPosition(owl.AnnotationProperty):
    namespace = ontology
    comment = "The pin position attached to the [Package, hasPin, Pin] relation."

# ================================= ENTITIES ==================================
class Device(owl.Thing):
    namespace = ontology
    comment = "The unique identifier (part number) of the device."

class DeviceFilter(owl.Thing):
    namespace = ontology
    comment = "A partial device identifier as a RegEx pattern."

# -------------------------------- INTERRUPTS ---------------------------------
class InterruptTable(owl.Thing):
    namespace = ontology
    comment = "The interrupt table."

class InterruptVector(owl.Thing):
    namespace = ontology
    comment = "Interrupt vector in the table."

# ----------------------------------- PINS ------------------------------------
class GpioPort(owl.Thing):
    namespace = ontology
    comment = "GPIO port of a pin."

class Pin(owl.Thing):
    namespace = ontology
    comment = "A device pin GPIO/electrical/analog/special."
    # def __init__(self, name):
    #     super().__init__(name)
    #     if any(c in name for c in {" ", "(", ")"}):
    #         raise ValueError(f"Invalid pin name '{name}'!")

class Package(owl.Thing):
    namespace = ontology
    comment = "A device package identifier"
    # def __init__(self, name):
    #     super().__init__(name)
    #     if any(c in name for c in {" ", "(", ")"}):
    #         raise ValueError(f"Invalid package name '{name}'!")

# class PinType(owl.Thing):
#     namespace = ontology
#     comment = """
# - S: supply
# - I: input
# - O: output
# - I/O: input/output
# - RST: reset
# - B: boot"""
#     def __init__(self, name):
#         super().__init__(name)
#         if name not in {"S", "I", "O", "I/O", "RST", "B"}:
#             raise ValueError(f"Pin type '{name}' is unknown!")

# class PinStructure(owl.Thing):
#     namespace = ontology
#     comment = """
# - FT: 5V tolerant
# - FTf: 5V tolerant, FM+ capable
# - TC: 3.3V tolerant
# - TTa: 3.3V tolerant, analog
# - RST: reset
# - B: boot"""
#     def __init__(self, name):
#         super().__init__(name)
#         if name not in {"FT", "FTf", "TC", "TTa", "RST", "B"}:
#             raise ValueError(f"Pin structure '{name}' is unknown!")

# ---------------------------------- SIGNALS ----------------------------------
class Signal(owl.Thing):
    namespace = ontology
    comment = "Connects a pin with a peripheral function."
    # def __init__(self, name):
    #     super().__init__(name)
    #     if any(c in name for c in {" ", "(", ")"}):
    #         raise ValueError(f"Invalid signal name '{name}'!")
    #     if not name[0].isalpha():
    #         raise ValueError(f"Signal '{name}' must start with a letter !")

class AlternateFunction(Signal):
    namespace = ontology
    comment = "Connects to a digital peripheral function via multiplexer."

class AdditionalFunction(Signal):
    namespace = ontology
    comment = "Connects to an analog/special peripheral function."

# ================================ PROPERTIES =================================
class hasDescription(owl.DataProperty, owl.FunctionalProperty):
    namespace = ontology
    domain = [InterruptVector]
    range = [str]

# ----------------------------------- PINS ------------------------------------
class hasPin(owl.ObjectProperty):
    namespace = ontology
    domain = [GpioPort, Package]
    range = [Pin]

class hasPackage(owl.ObjectProperty):
    namespace = ontology
    domain = [Device]
    range = [Package]

class hasPinType(owl.DataProperty, owl.FunctionalProperty):
    namespace = ontology
    comment = """
- S: supply
- I: input
- O: output
- I/O: input/output
- RST: reset
- B: boot"""
    domain = [Pin]
    range = [str]

class hasPinStructure(owl.DataProperty, owl.FunctionalProperty):
    namespace = ontology
    comment = """
- FT: 5V tolerant
- FTf: 5V tolerant, FM+ capable
- TC: 3.3V tolerant
- TTa: 3.3V tolerant, analog
- RST: reset
- B: boot"""
    domain = [Pin]
    range = [str]

# ---------------------------------- SIGNALS ----------------------------------
class hasSignal(owl.ObjectProperty):
    namespace = ontology
    domain = [Pin]
    range = [Signal]

# -------------------------------- INTERRUPTS ---------------------------------
class hasInterruptVector(owl.ObjectProperty):
    namespace = ontology
    domain = [InterruptTable]
    range = [InterruptVector]
