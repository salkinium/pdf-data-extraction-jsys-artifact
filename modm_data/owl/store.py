# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

from ..utils import cache_path
import owlready2 as owl

class Store:
    def __init__(self, vendor):
        self.base_url = "https://data.modm.io"
        self.vendor = vendor
        self._path = cache_path(f"{vendor}-owl")
        # Add the directory to the search path
        owl.onto_path.append(self._path)
        self.ontology = owl.get_ontology(f"{self.base_url}/{vendor}")

    def namespace(self, name):
        return self.ontology.get_namespace(f"{self.vendor}/{name}")

    def load(self, name=None):
        if name is None: name = "ontology"
        fileobj = open(self._path / f"{name}.owl", "rb")
        self.ontology.load(only_local=True, fileobj=fileobj, reload=True)

    def save(self, name=None):
        self._path.mkdir(exist_ok=True, parents=True)
        if name is None: name = "ontology"
        self.ontology.save(file=str(self._path / f"{name}.owl"))

    def clear(self):
        self.ontology._destroy_cached_entities()

    def __repr__(self) -> str:
        return f"Store({self._vendor})"

