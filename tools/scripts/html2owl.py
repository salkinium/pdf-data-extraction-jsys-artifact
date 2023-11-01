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

from modm_data.html2py.stmicro import DatasheetMicro, ReferenceManual, load_documents
from modm_data.owl.stmicro import store
from modm_data.py2owl.stmicro import owl_from


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--document", type=str, default="")
    parser.add_argument("--all", action="store_true", default=False)
    args = parser.parse_args()

    if args.all:
        docs = []
        for name, versions in load_documents().items():
            # always use latest version for now
            doc = list(versions.values())[-1]
            if isinstance(doc, DatasheetMicro):
                docs.append(doc)
            elif isinstance(doc, ReferenceManual):
                docs.append(doc)

        calls = [f"python3 {__file__} --document {doc.path}" for doc in docs]
        # for call in calls: os.system(call)
        # return False
        with multiprocessing.Pool() as pool:
            retvals = pool.map(os.system, calls)
        return all(os.WEXITSTATUS(r) == 0 for r in retvals)

    else:
        path = Path(args.document).absolute()
        if path.stem.startswith("DS"):
            doc = DatasheetMicro(path)
        elif path.stem.startswith("RM"):
            doc = ReferenceManual(path)

        print(doc.path_pdf.relative_to(Path().cwd()),
              doc.path.relative_to(Path().cwd()),
              f"ext/cache/stmicro-owl/{doc.fullname}.owl")

        owl_from(doc)
        store.save(doc.fullname)
        return True


if __name__ == "__main__":
    exit(0 if main() else 1)
