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
import multiprocessing
from pathlib import Path
sys.path.append(".")

import modm_data.pdf
import modm_data.pdf2html
from modm_data.pdf2html.stmicro import convert as convert_st, patch as patch_st


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--document", type=str)
    parser.add_argument("--output", type=str, default="")
    parser.add_argument("--page", type=int, action="append")
    parser.add_argument("--range", action="append")
    parser.add_argument("--png", action="store_true")
    parser.add_argument("--pdf", action="store_true")
    parser.add_argument("--ast", action="store_true")
    parser.add_argument("--tree", action="store_true")
    parser.add_argument("--ascii", action="store_true")
    parser.add_argument("--html", action="store_true")
    parser.add_argument("--parallel", action="store_true")
    parser.add_argument("--chapters", action="store_true")
    parser.add_argument("--tags", action="store_true")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    doc = modm_data.pdf.Document(args.document)
    print(doc.page_count, doc.metadata, doc.is_tagged)
    if doc.page_count == 0 or not doc.page(1).width:
        print("Corrupt PDF!")
        exit(1)

    if args.page or args.range:
        page_range = list(map(lambda p: p - 1, args.page or []))
        if args.range:
            for arange in args.range:
                start, stop = arange.split(":")
                arange = range(int(start or 0), int(stop or doc.page_count - 1) + 1)
                page_range.extend([p - 1 for p in arange])
        page_range.sort()
    else:
        page_range = range(doc.page_count)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    document = None
    # FIXME detection is flawed
    if modm_data.pdf2html.stmicro.is_compatible(doc) or True:
        if args.parallel:
            output_dir = (output_path.parent / output_path.stem)
            output_dir.mkdir(parents=True, exist_ok=True)
            dests = [(0, "introduction")]
            for toc in doc.toc:
                if toc.level == 0 and not toc.title.startswith("Table"):
                    title = toc.title.lower().strip("0123456789").strip()
                    title = re.sub(r"[\(\)/®&\n\r,;:™]", "", title)
                    title = re.sub(r"[ -]", "_", title)
                    title = re.sub(r"_+", "_", title)
                    title = title.replace("²", "2")
                    if not any(c in toc.title for c in {"Contents", "List of ", "Index"}):
                        dests.append((toc.page, title))
                    print(toc.page, toc.title)
            dests.append((doc.page_count, None))
            ranges = [(p0, p1, t0) for (p0, t0), (p1, t1) in zip(dests, dests[1:]) if p0 != p1]
            calls = []
            for ii, (p0, p1, title) in enumerate(ranges):
                call = f"python3 {__file__} --document {args.document} --html " \
                       f"--output {output_dir}/chapter_{ii}_{title}.html --range {p0 + 1}:{p1}"
                calls.append(call)
                print(call)
            with multiprocessing.Pool() as pool:
                retvals = pool.map(os.system, calls)
            if all(os.WEXITSTATUS(r) == 0 for r in retvals):
                return patch_st(doc, output_dir)
            return False
        else:
            return convert_st(doc, page_range, output_path,
                              format_chapters=args.chapters,
                              render_html=args.html, render_png=args.png,
                              render_pdf=args.pdf, render_all=args.all,
                              show_ascii=args.ascii, show_ast=args.ast,
                              show_tree=args.tree, show_tags=args.tags)
    else:
        print("Unknown document template!")
        return False


if __name__ == "__main__":
    exit(0 if main() else 1)
