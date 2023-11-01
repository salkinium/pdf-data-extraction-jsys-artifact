# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------


def list_lstrip(input_values: list, strip_fn) -> list:
    ii = 0
    for value in input_values:
        if strip_fn(value):
            ii += 1
        else:
            break
    return input_values[ii:]


def list_rstrip(input_values: list, strip_fn) -> list:
    ii = 0
    for value in reversed(input_values):
        if strip_fn(value):
            ii += 1
        else:
            break
    return input_values[:len(input_values) - ii]


def list_strip(input_values: list, strip_fn) -> list:
    return list_rstrip(list_lstrip(input_values, strip_fn), strip_fn)
