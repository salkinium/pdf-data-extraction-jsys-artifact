# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

from anytree import RenderTree

from .page import Page
from .ast import merge_area, normalize_document
from .ast import format_document, write_html
from ..render import render_page_png, render_page_pdf
from ...utils import patch_path
import pypdfium2 as pp
# import subprocess
import patch_ng


def convert(doc, page_range, output_path, format_chapters=False, pretty=True,
            render_html=True, render_png=False, render_pdf=False, render_all=False,
            show_ascii=False, show_ast=False, show_tree=False, show_tags=False) -> bool:

    document = None
    debug_doc = None
    debug_index = 0
    for dpage in doc.pages(page_range):
        page = Page(dpage)
        if not render_all and any(c in page.top for c in {"Contents", "List of ", "Index"}):
            continue
        print(f"\n\n=== {page.top} #{dpage.number} ===\n")

        if show_ascii:
            print(page.format_ascii())

        if show_tags:
            for struct in dpage.structures:
                print(struct.descr())

        if show_tree or render_html or show_ast:
            areas = page.content_ast
            if show_ast:
                print()
                for area in areas:
                    print(RenderTree(area))
            if show_tree or render_html:
                for area in areas:
                    document = merge_area(document, area)

        if render_png:
            img = render_page(page, scale=3, frames=True, spacing=True)
            img.save(f"debug_{output_path.stem}_{dpage.number}.png")
        if render_pdf:
            debug_doc = render_page_pdf(doc, page, debug_doc, debug_index)
            debug_index += 1

    if render_pdf:
        with open(f"debug_{output_path.stem}.pdf", 'wb') as file_handle:
            pp.save_pdf(debug_doc, file_handle)

    if show_tree or render_html:
        if document is None:
            print("No pages parsed, empty document!")
            return True

        document = normalize_document(document)
        if show_tree:
            print(RenderTree(document))

        if render_html:
            if format_chapters:
                for chapter in document.children:
                    if chapter.name == "chapter":
                        print(f"\nFormatting HTML for '{chapter.title}'")
                        html = format_document(chapter)
                        output_file = f"{output_path}/chapter_{chapter._filename}.html"
                        print(f"\nWriting HTML '{output_file}'")
                        write_html(html, output_file, pretty=pretty)
            else:
                print("\nFormatting HTML")
                html = format_document(document)
                print(f"\nWriting HTML '{str(output_path)}'")
                write_html(html, str(output_path), pretty=pretty)

    return True


def patch(doc, output_path, patch_file=None) -> bool:
    if patch_file is None:
        # First try the patch file for the specific version
        patch_file = patch_path("stmicro") / f"{doc.name}.patch"
        if not patch_file.exists():
            # Then try the patch file shared between versions
            patch_file = patch_path("stmicro") / f"{doc.name.split('-')[0]}.patch"
            if not patch_file.exists():
                return True
    print(f"Patching {doc.name} with {patch_file}...")
    patch_ng.setdebug()
    patchset = patch_ng.fromfile(patch_file)
    if patchset and patchset.apply(root=output_path, fuzz=True):
        return True
    print(f"Failed to apply patch {patch_file}!")
    return False
    # return not subprocess.run(f"(cd {output_path}; patch -p1 -l -i {patch_file})", shell=True).returncode
    # return not subprocess.run(f"(cd {output_path}; git apply -v --ignore-whitespace {patch_file})", shell=True).returncode
