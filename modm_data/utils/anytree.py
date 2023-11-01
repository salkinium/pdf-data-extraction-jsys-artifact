# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

from anytree.iterators import AbstractIter


class ReversePreOrderIter(AbstractIter):
    @staticmethod
    def _iter(children, filter_, stop, maxlevel):
        for child_ in reversed(children):
            if not AbstractIter._abort_at_level(2, maxlevel):
                descendantmaxlevel = maxlevel - 1 if maxlevel else None
                yield from ReversePreOrderIter._iter(
                    child_.children, filter_, stop, descendantmaxlevel)
                if stop(child_):
                    continue
                if filter_(child_):
                    yield child_
