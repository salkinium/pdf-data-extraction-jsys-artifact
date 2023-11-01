# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

import math
from PIL import Image, ImageDraw, ImageColor, ImageColor
import pypdfium2 as pp
from ..utils import VLine, HLine
from ..pdf.render import render_page_png as pdf_render_page_png
from ..pdf.render import render_page_pdf as pdf_render_page_pdf


def render_page_png(page, scale: float = 1, frames: bool = False, grid: bool = False, spacing: bool = False) -> Image:
    img = pdf_render_page_png(page._page, scale=scale, frames=frames)
    draw = ImageDraw.Draw(img)
    s = scale

    def _vline(x, y0, y1, **kw):
        draw.line([x * s, (page._page.height - y0) * s,
                   x * s, (page._page.height - y1) * s], **kw)

    def _hline(y, x0, x1, **kw):
        draw.line([x0 * s, (page._page.height - y) * s,
                   x1 * s, (page._page.height - y) * s], **kw)

    def _line(line, **kw):
        draw.line([line.p0.x * s, (page._page.height - line.p0.y) * s,
                   line.p1.x * s, (page._page.height - line.p1.y) * s], **kw)

    def _rect(rect, **kw):
        draw.rectangle([rect.p0.x * s, (page._page.height - rect.p0.y) * s,
                        rect.p1.x * s, (page._page.height - rect.p1.y) * s], **kw)

    if grid:
        for ii in range(20):
            _vline(page._page.width * ii / 20, 0, page._page.height, width=1, fill="black")
            _hline(page._page.height * ii / 20, 0, page._page.width, width=1, fill="black")

    if spacing:
        for name, distance in page._spacing.items():
            if name.startswith("x_"):
                _vline(distance, 0, page._page.height, width=1, fill="yellow")
            else:
                _hline(distance, 0, page._page.width, width=1, fill="yellow")

    if frames:
        for name, area in page._areas.items():
            if isinstance(area, list):
                for rect in area:
                    _rect(rect, width=1, outline="yellow")
            else:
                _rect(area, width=1, outline="yellow")

        for obj in page.content_graphics:
            if obj.cbbox is not None:
                _rect(obj.cbbox, width=3, outline="yellowgreen")
            if obj.bbox is not None:
                _rect(obj.bbox, width=3, outline="green")

        for table in page.content_tables:
            _rect(table.bbox, width=2, outline="blue")

            for lines in table._xgrid.values():
                for line in lines:
                    _line(line, width=1, fill="white")
            for lines in table._ygrid.values():
                for line in lines:
                    _line(line, width=1, fill="white")

            for cell in table.cells:
                for line in cell.lines:
                    for cluster in line.clusters():
                        _rect(cluster.bbox, width=1, outline="white")
                if cell.b.l:
                    _vline(cell.bbox.left, cell.bbox.bottom, cell.bbox.top,
                           width=math.ceil(s * cell.b.l), fill="red")
                if cell.b.r:
                    _vline(cell.bbox.right, cell.bbox.bottom, cell.bbox.top,
                           width=math.ceil(s * cell.b.r), fill="blue")
                if cell.b.b:
                    _hline(cell.bbox.bottom, cell.bbox.left, cell.bbox.right,
                           width=math.ceil(s * cell.b.b), fill="green")
                if cell.b.t:
                    _hline(cell.bbox.top, cell.bbox.left, cell.bbox.right,
                           width=math.ceil(s * cell.b.t), fill="white")

    return img


def render_page_pdf(doc, page, new_doc = None, index = 0):
    new_doc = pdf_render_page_pdf(doc, page._page, new_doc, index)
    # return new_doc
    new_page = pp.FPDF_LoadPage(new_doc, index)
    rotation = page._page.rotation
    width, height = page._page.width, page._page.height

    def _vline(x, y0, y1, **kw):
        _line(VLine(x, y0, y1), **kw)

    def _hline(y, x0, x1, **kw):
        _line(HLine(y, x0, x1), **kw)

    def _line(line, **kw):
        if rotation:
            obj = pp.FPDFPageObj_CreateNewPath(height - line.p0.y, line.p0.x)
            assert pp.FPDFPath_LineTo(obj, height - line.p1.y, line.p1.x)
        else:
            obj = pp.FPDFPageObj_CreateNewPath(line.p0.x, line.p0.y)
            assert pp.FPDFPath_LineTo(obj, line.p1.x, line.p1.y)
        if fill := kw.get("fill"):
            assert pp.FPDFPageObj_SetFillColor(obj, *ImageColor.getcolor(fill, "RGB"), 0xA0)
        if stroke := kw.get("stroke"):
            assert pp.FPDFPageObj_SetStrokeColor(obj, *ImageColor.getcolor(stroke, "RGB"), 0xA0)
        if width := kw.get("width"):
            assert pp.FPDFPageObj_SetStrokeWidth(obj, width)
        assert pp.FPDFPath_SetDrawMode(obj, 1 if kw.get("fill") else 0,
                                       kw.get("width") is not None)
        pp.FPDFPage_InsertObject(new_page, obj)

    def _rect(rect, **kw):
        if rotation:
            obj = pp.FPDFPageObj_CreateNewRect(height - rect.bottom - rect.height,
                                               rect.left, rect.height, rect.width)
        else:
            obj = pp.FPDFPageObj_CreateNewRect(rect.left, rect.bottom, rect.width, rect.height)
        if fill := kw.get("fill"):
            assert pp.FPDFPageObj_SetFillColor(obj, *ImageColor.getcolor(fill, "RGB"), 0xA0)
        if stroke := kw.get("stroke"):
            assert pp.FPDFPageObj_SetStrokeColor(obj, *ImageColor.getcolor(stroke, "RGB"), 0xA0)
        if width := kw.get("width"):
            assert pp.FPDFPageObj_SetStrokeWidth(obj, width)
        assert pp.FPDFPath_SetDrawMode(obj, 1 if kw.get("fill") else 0,
                                       kw.get("stroke") is not None)
        pp.FPDFPage_InsertObject(new_page, obj)

    if False:
        for ii in range(20):
            _vline(page._page.width * ii / 20, 0, page._page.height, width=1, stroke="black")
            _hline(page._page.height * ii / 20, 0, page._page.width, width=1, stroke="black")

    # for name, distance in page._spacing.items():
    #     if name.startswith("x_"):
    #         _vline(distance, 0, page._page.height, width=0.5, stroke="orange")
    #     else:
    #         _hline(distance, 0, page._page.width, width=0.5, stroke="orange")

    for name, area in page._areas.items():
        if isinstance(area, list):
            for rect in area:
                _rect(rect, width=0.5, stroke="orange")
        else:
            _rect(area, width=0.5, stroke="orange")

    for obj in page.content_graphics:
        if obj.cbbox is not None:
            _rect(obj.cbbox, width=2, stroke="yellowgreen")
        if obj.bbox is not None:
            _rect(obj.bbox, width=2, stroke="green")

    for table in page.content_tables:
        _rect(table.bbox, width=1.5, stroke="blue")

        for lines in table._xgrid.values():
            for line in lines:
                _line(line, width=0.75, stroke="blue")
        for lines in table._ygrid.values():
            for line in lines:
                _line(line, width=0.75, stroke="blue")

        for cell in table.cells:
            for line in cell.lines:
                for cluster in line.clusters():
                    _rect(cluster.bbox, width=0.33, stroke="gray")
            if cell.b.l:
                _vline(cell.bbox.left, cell.bbox.bottom, cell.bbox.top,
                       width=cell.b.l, stroke="red")
            if cell.b.r:
                _vline(cell.bbox.right, cell.bbox.bottom, cell.bbox.top,
                       width=cell.b.r, stroke="blue")
            if cell.b.b:
                _hline(cell.bbox.bottom, cell.bbox.left, cell.bbox.right,
                       width=cell.b.b, stroke="green")
            if cell.b.t:
                _hline(cell.bbox.top, cell.bbox.left, cell.bbox.right,
                       width=cell.b.t, stroke="gray")

    assert pp.FPDFPage_GenerateContent(new_page)
    pp.FPDF_ClosePage(new_page)
    return new_doc
