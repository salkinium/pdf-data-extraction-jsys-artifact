# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

import math
import ctypes
from ..utils import VLine, HLine
from PIL import Image, ImageDraw, ImageColor
import pypdfium2 as pp

def render_page_png(page, scale: float = 1, frames: bool = False) -> Image:
    s = scale
    width = math.ceil(page.width * s)
    height = math.ceil(page.height * s)
    bitmap = pp.FPDFBitmap_Create(width, height, 0)
    pp.FPDFBitmap_FillRect(bitmap, 0, 0, width, height, 0x008F8F8F)

    render_args = [bitmap, page._page, 0, 0, width, height, 0, pp.FPDF_LCD_TEXT | pp.FPDF_ANNOT]
    pp.FPDF_RenderPageBitmap(*render_args)
    cbuffer = pp.FPDFBitmap_GetBuffer(bitmap)
    buffer = ctypes.cast(cbuffer, ctypes.POINTER(ctypes.c_ubyte * (width * height * 4)))
    img = Image.frombuffer("RGBA", (width, height), buffer.contents, "raw", "BGRA", 0, 1)
    pp.FPDFBitmap_Destroy(bitmap)

    if frames:
        draw = ImageDraw.Draw(img)

        def _vline(x, y0, y1, **kw):
            _line(VLine(x, y0, y1), **kw)

        def _hline(y, x0, x1, **kw):
            _line(HLine(y, x0, x1), **kw)

        def _line(line, **kw):
            draw.line([line.p0.x * s, (page.height - line.p0.y) * s,
                       line.p1.x * s, (page.height - line.p1.y) * s], **kw)

        def _rect(rect, **kw):
            draw.rectangle([rect.p0.x * s, (page.height - rect.p0.y) * s,
                            rect.p1.x * s, (page.height - rect.p1.y) * s], **kw)

        for path in page.paths:
            for line in path.lines:
                _line(line, width=1, fill="blue")
                if path.stroke == 0xffffffff and path.fill == 0x2052ff and 0.14 < path.width < 0.16:
                    _line(line, width=3, fill="green")

        for bbox, _ in page.graphic_clusters():
            _rect(bbox, width=3, outline="cyan")

        for char in page.chars:
            _rect(char.bbox, width=math.ceil(0.25 * s), outline="red")
            _vline(char.origin.x, char.origin.y - 1, char.origin.y + 1, width=1, fill="gray")
            _hline(char.origin.y, char.origin.x - 1, char.origin.x + 1, width=1, fill="gray")
            color = "blue" if char.unicode in {0xa, 0xd} else "white"
            _vline(char.bbox.midpoint.x, char.bbox.midpoint.y - 1, char.bbox.midpoint.y + 1, width=1, fill=color)
            _hline(char.bbox.midpoint.y, char.bbox.midpoint.x - 1, char.bbox.midpoint.x + 1, width=1, fill=color)

        for link in page.objlinks:
            _rect(link.bbox, width=1 * s, outline="yellowgreen")

        for link in page.weblinks:
            for bbox in link.bboxes:
                _rect(bbox, width=1 * s, outline="green")

    return img


def render_page_pdf(doc, page, new_doc = None, index = 0) -> Image:
    width, height = page.width, page.height

    if new_doc is None:
        new_doc = pp.FPDF_CreateNewDocument()
    # copy page over to new doc
    assert pp.FPDF_ImportPages(new_doc, doc._doc, str(page.number), index)
    new_page = pp.FPDF_LoadPage(new_doc, index)
    rotation = page.rotation

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
            assert pp.FPDFPageObj_SetFillColor(obj, *ImageColor.getcolor(fill, "RGB"), 0xC0)
        if stroke := kw.get("stroke"):
            assert pp.FPDFPageObj_SetStrokeColor(obj, *ImageColor.getcolor(stroke, "RGB"), 0xC0)
        if width := kw.get("width"):
            assert pp.FPDFPageObj_SetStrokeWidth(obj, width)
        assert pp.FPDFPath_SetDrawMode(obj, 1 if kw.get("fill") else 0,
                                       kw.get("width") is not None)
        pp.FPDFPage_InsertObject(new_page, obj)

    def _rect(rect, **kw):
        if rotation:
            obj = pp.FPDFPageObj_CreateNewRect(
                    height - rect.bottom - rect.height, rect.left, rect.height, rect.width)
        else:
            obj = pp.FPDFPageObj_CreateNewRect(rect.left, rect.bottom, rect.width, rect.height)
        if fill := kw.get("fill"):
            assert pp.FPDFPageObj_SetFillColor(obj, *ImageColor.getcolor(fill, "RGB"), 0xC0)
        if stroke := kw.get("stroke"):
            assert pp.FPDFPageObj_SetStrokeColor(obj, *ImageColor.getcolor(stroke, "RGB"), 0xC0)
        if width := kw.get("width"):
            assert pp.FPDFPageObj_SetStrokeWidth(obj, width)
        assert pp.FPDFPath_SetDrawMode(obj, 1 if kw.get("fill") else 0,
                                       kw.get("width") is not None)
        pp.FPDFPage_InsertObject(new_page, obj)

    for path in page.paths:
        p0 = path.points[0]
        if rotation: obj = pp.FPDFPageObj_CreateNewPath(height - p0.y, p0.x)
        else: obj = pp.FPDFPageObj_CreateNewPath(p0.x, p0.y)
        assert pp.FPDFPageObj_SetStrokeColor(obj, *ImageColor.getcolor("blue", "RGB"), 0xC0)
        assert pp.FPDFPageObj_SetStrokeWidth(obj, 0.25)
        assert pp.FPDFPageObj_SetLineJoin(obj, pp.FPDF_LINEJOIN_ROUND)
        assert pp.FPDFPageObj_SetLineCap(obj, pp.FPDF_LINECAP_ROUND)
        assert pp.FPDFPath_SetDrawMode(obj, 0, True)
        for point in path.points[1:]:
            if point.type == path.Type.MOVE:
                if rotation: assert pp.FPDFPath_MoveTo(obj, height - point.y, point.x)
                else: assert pp.FPDFPath_MoveTo(obj, point.x, point.y)
            else:
                if rotation: assert pp.FPDFPath_LineTo(obj, height - point.y, point.x)
                else: assert pp.FPDFPath_LineTo(obj, point.x, point.y)
        pp.FPDFPage_InsertObject(new_page, obj)

    for bbox, _ in page.graphic_clusters():
        _rect(bbox, width=2, stroke="cyan")

    for link in page.objlinks:
        _rect(link.bbox, width=0.75, stroke="yellowgreen")

    for link in page.weblinks:
        for bbox in link.bboxes:
            _rect(bbox, width=0.75, stroke="green")

    for char in page.chars:
        color = "blue"
        if char.bbox.width:
            _rect(char.bbox, width=0.5, stroke="red")
            _vline(char.bbox.midpoint.x, char.bbox.midpoint.y - 1, char.bbox.midpoint.y + 1, width=0.25, stroke="red")
            _hline(char.bbox.midpoint.y, char.bbox.midpoint.x - 1, char.bbox.midpoint.x + 1, width=0.25, stroke="red")
            color = "black"
        _vline(char.origin.x, char.origin.y - 1, char.origin.y + 1, width=0.25, stroke=color)
        _hline(char.origin.y, char.origin.x - 1, char.origin.x + 1, width=0.25, stroke=color)

    assert pp.FPDFPage_GenerateContent(new_page)
    pp.FPDF_ClosePage(new_page)
    return new_doc
