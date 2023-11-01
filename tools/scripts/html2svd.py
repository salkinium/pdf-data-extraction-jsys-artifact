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
from pathlib import Path
import multiprocessing
sys.path.extend([".", "ext/modm-devices"])

from modm_data.html2py.stmicro import ReferenceManual, load_documents
from modm_data.html2svd.stmicro import memory_map_from_reference_manual
from modm_data.svd import format_svd, write_svd
from modm_data.utils import cache_path
from anytree import RenderTree


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
            if isinstance(doc, ReferenceManual):
                docs.append(doc)

        Path("log/stmicro/svd-docs").mkdir(exist_ok=True, parents=True)
        calls = [f"python3 {__file__} --document {doc.path} "
                 f"> log/stmicro/svd-docs/{doc.name}.txt 2>&1" for doc in docs]
        # for call in calls: os.system(call)
        # return False
        with multiprocessing.Pool() as pool:
            retvals = pool.map(os.system, calls)
        return all(os.WEXITSTATUS(r) == 0 for r in retvals)

    else:
        path = Path(args.document).absolute()
        doc = ReferenceManual(path)
        print(doc.path_pdf.relative_to(Path().cwd()),
              doc.path.relative_to(Path().cwd()),
              f"ext/cache/stmicro-svd/rm_{doc.fullname}.svd")

        mmaptrees = memory_map_from_reference_manual(doc)
        for mmaptree in mmaptrees:
            print(RenderTree(mmaptree, maxlevel=2))
            svd = format_svd(mmaptree)
            output_path = cache_path(f"stmicro-svd/rm_{doc.name.lower()}_{mmaptree.name}.svd")
            write_svd(svd, str(output_path))
        return True


if __name__ == "__main__":
    exit(0 if main() else 1)
