#!/usr/bin/env python3
"""Reformat side-by-side gamebook PDFs to portrait Statement pages (5.5 x 8.5 in)."""

from __future__ import annotations

import argparse
import copy
import re
from enum import Enum
from pathlib import Path

from pypdf import PageObject, PdfReader, PdfWriter, Transformation
from pypdf.generic import RectangleObject

# Portrait Statement: 5.5" wide x 8.5" tall.
OUTPUT_WIDTH_PT = 5.5 * 72
OUTPUT_HEIGHT_PT = 8.5 * 72
# Frame border line width in the inner coordinate space used by /Div rects (/LW 1).
FRAME_LINE_WIDTH = 1.0

Matrix = tuple[float, float, float, float, float, float]
BBox = tuple[float, float, float, float]


class ExportMode(str, Enum):
    COVER = "cover"
    SPLIT = "split"
    COLORED_SPLIT = "colored_split"


def multiply_matrix(m1: Matrix, m2: Matrix) -> Matrix:
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (
        a1 * a2 + b1 * c2,
        a1 * b2 + b1 * d2,
        c1 * a2 + d1 * c2,
        c1 * b2 + d1 * d2,
        e1 * a2 + f1 * c2 + e2,
        e1 * b2 + f1 * d2 + f2,
    )


def transform_point(matrix: Matrix, x: float, y: float) -> tuple[float, float]:
    a, b, c, d, e, f = matrix
    return a * x + c * y + e, b * x + d * y + f


def get_page_content(page: PageObject) -> str:
    content = page.get_contents()
    if content is None:
        return ""
    if hasattr(content, "get_data"):
        data = content.get_data()
    else:
        data = b"".join(part.get_data() for part in content)
    return data.decode("latin-1", errors="replace")


def parse_leading_cm(content: str) -> Matrix:
    match = re.search(
        r"^([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+cm",
        content,
    )
    if not match:
        return (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    return tuple(float(value) for value in match.groups())  # type: ignore[return-value]


def _inner_cm_before(content: str, match_start: int) -> Matrix | None:
    window = content[max(0, match_start - 500) : match_start]
    cm_matches = re.findall(
        r"([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+cm",
        window,
    )
    if not cm_matches:
        return None
    return tuple(float(value) for value in cm_matches[-1])  # type: ignore[return-value]


def parse_interior_frame(content: str) -> tuple[Matrix, float, float, float, float] | None:
    """Return inner cm and the interior content rect (x, y, width, height) for a /Div panel."""
    stroke_match = re.search(
        r"/Div\s*<</MCID\s+\d+\s*>>BDC\s*"
        r"[\d.\-]+\s+[\d.\-]+\s+902\s+677\s+re\s+"
        r"f\s+"
        r".*?"
        r"([\d.\-]+)\s+([\d.\-]+)\s+901\s+676\s+re\s+"
        r"S",
        content,
        re.DOTALL,
    )
    if stroke_match:
        inner = _inner_cm_before(content, stroke_match.start())
        if inner is None:
            return None
        stroke_x = float(stroke_match.group(1))
        stroke_y = float(stroke_match.group(2))
        half_line = FRAME_LINE_WIDTH / 2.0
        return (
            inner,
            stroke_x + half_line,
            stroke_y + half_line,
            901.0 - FRAME_LINE_WIDTH,
            676.0 - FRAME_LINE_WIDTH,
        )

    colored_match = re.search(
        r"/Div\s*<</MCID\s+\d+\s*>>BDC\s*"
        r"([\d.\-]+)\s+([\d.\-]+)\s+900\s+675\s+re\s+"
        r"f",
        content,
    )
    if colored_match:
        inner = _inner_cm_before(content, colored_match.start())
        if inner is None:
            return None
        return (
            inner,
            float(colored_match.group(1)),
            float(colored_match.group(2)),
            900.0,
            675.0,
        )

    return None


def is_colored_panel_page(content: str) -> bool:
    """True when the page uses a solid-fill /Div panel instead of a stroked frame."""
    if re.search(
        r"/Div\s*<</MCID\s+\d+\s*>>BDC\s*"
        r"[\d.\-]+\s+[\d.\-]+\s+902\s+677\s+re\s+"
        r"f\s+"
        r".*?"
        r"[\d.\-]+\s+[\d.\-]+\s+901\s+676\s+re\s+"
        r"S",
        content,
        re.DOTALL,
    ):
        return False
    return bool(
        re.search(
            r"/Div\s*<</MCID\s+\d+\s*>>BDC\s*"
            r"[\d.\-]+\s+[\d.\-]+\s+900\s+675\s+re\s+"
            r"f",
            content,
        )
    )


def parse_cover_panels(content: str) -> list[tuple[Matrix, float, float, float, float]]:
    """Return cover artwork panels found in the page content stream."""
    panels: list[tuple[Matrix, float, float, float, float]] = []

    for panel_match in re.finditer(r"0\s+0\s+450\s+675\s+re", content):
        inner = _inner_cm_before(content, panel_match.start())
        if inner is not None:
            panels.append((inner, 0.0, 0.0, 450.0, 675.0))

    framed_match = re.search(
        r"/Div\s*<</MCID\s+\d+\s*>>BDC\s*"
        r"0\s+0\s+452\s+677\s+re\s+"
        r"f\s+"
        r".*?"
        r"[\d.\-]+\s+[\d.\-]+\s+451\s+676\s+re\s+"
        r"S",
        content,
        re.DOTALL,
    )
    if framed_match:
        inner = _inner_cm_before(content, framed_match.start())
        if inner is not None:
            half_line = FRAME_LINE_WIDTH / 2.0
            panels.append(
                (
                    inner,
                    half_line,
                    half_line,
                    451.0 - FRAME_LINE_WIDTH,
                    676.0 - FRAME_LINE_WIDTH,
                )
            )

    return panels


def intersect_bbox(a: BBox, b: BBox) -> BBox | None:
    left = max(a[0], b[0])
    bottom = max(a[1], b[1])
    right = min(a[2], b[2])
    top = min(a[3], b[3])
    if right <= left or top <= bottom:
        return None
    return left, bottom, right, top


def right_half_bbox(page_width: float, page_height: float) -> BBox:
    mid_x = page_width / 2.0
    return mid_x, 0.0, page_width, page_height


def rect_to_bbox(outer: Matrix, inner: Matrix, x: float, y: float, w: float, h: float) -> BBox:
    full = multiply_matrix(inner, outer)
    corners = (
        transform_point(full, x, y),
        transform_point(full, x + w, y),
        transform_point(full, x, y + h),
        transform_point(full, x + w, y + h),
    )
    xs = [point[0] for point in corners]
    ys = [point[1] for point in corners]
    return min(xs), min(ys), max(xs), max(ys)


def detect_cover_bbox(page: PageObject) -> BBox:
    """Isolate cover artwork from the right-hand half of the source cover sheet."""
    page_width = float(page.mediabox.width)
    page_height = float(page.mediabox.height)
    content = get_page_content(page)
    outer = parse_leading_cm(content)
    right_half = right_half_bbox(page_width, page_height)

    best: BBox | None = None
    best_left = -1.0

    for inner, rect_x, rect_y, rect_width, rect_height in parse_cover_panels(content):
        panel_bbox = rect_to_bbox(outer, inner, rect_x, rect_y, rect_width, rect_height)
        clipped = clip_bbox(panel_bbox, page_width, page_height)
        region = intersect_bbox(clipped, right_half)
        if region is not None and region[0] > best_left:
            best_left = region[0]
            best = region

    if best is not None:
        return best

    return right_half


def clip_bbox(bbox: BBox, page_width: float, page_height: float) -> BBox:
    left, bottom, right, top = bbox
    left = max(0.0, min(left, page_width))
    right = max(0.0, min(right, page_width))
    bottom = max(0.0, min(bottom, page_height))
    top = max(0.0, min(top, page_height))
    if right <= left or top <= bottom:
        return 0.0, 0.0, page_width, page_height
    return left, bottom, right, top


def strip_outer_frame_bbox(content: str, page_width: float, page_height: float) -> BBox | None:
    """Detect a /Div panel (line-art frame or solid fill) and return its interior area."""
    frame = parse_interior_frame(content)
    if frame is None:
        return None
    inner, rect_x, rect_y, rect_width, rect_height = frame
    outer = parse_leading_cm(content)
    interior = rect_to_bbox(outer, inner, rect_x, rect_y, rect_width, rect_height)
    clipped = clip_bbox(interior, page_width, page_height)
    if clipped[2] <= clipped[0] or clipped[3] <= clipped[1]:
        return None
    return clipped


def detect_interior_bbox(page: PageObject) -> BBox:
    """Crop to the area inside the outer frame, excluding margins and border."""
    page_width = float(page.mediabox.width)
    page_height = float(page.mediabox.height)
    content = get_page_content(page)

    interior = strip_outer_frame_bbox(content, page_width, page_height)
    if interior is not None:
        return interior

    return 0.0, 0.0, page_width, page_height


def set_page_box(page: PageObject, bbox: BBox) -> None:
    rect = RectangleObject(bbox)
    page.mediabox = rect
    page.cropbox = rect
    if "/TrimBox" in page:
        page.trimbox = rect
    if "/BleedBox" in page:
        page.bleedbox = rect
    if "/ArtBox" in page:
        page.artbox = rect


def fit_region_to_output(source_page: PageObject, region: BBox) -> PageObject:
    left, bottom, right, top = region
    region_width = right - left
    region_height = top - bottom

    output_page = PageObject.create_blank_page(
        width=OUTPUT_WIDTH_PT,
        height=OUTPUT_HEIGHT_PT,
    )

    scale = min(
        OUTPUT_WIDTH_PT / region_width,
        OUTPUT_HEIGHT_PT / region_height,
    )
    scaled_width = region_width * scale
    scaled_height = region_height * scale
    translate_x = (OUTPUT_WIDTH_PT - scaled_width) / 2.0
    translate_y = (OUTPUT_HEIGHT_PT - scaled_height) / 2.0

    working_page = copy.deepcopy(source_page)
    set_page_box(working_page, region)

    transform = (
        Transformation()
        .translate(-left, -bottom)
        .scale(scale, scale)
        .translate(translate_x, translate_y)
    )
    output_page.merge_transformed_page(working_page, transform, expand=False)
    return output_page


def fit_cover_to_output(source_page: PageObject, region: BBox) -> PageObject:
    """Scale the cover proportionally to fill the output page, cropping any overflow."""
    left, bottom, right, top = region
    region_width = right - left
    region_height = top - bottom

    output_page = PageObject.create_blank_page(
        width=OUTPUT_WIDTH_PT,
        height=OUTPUT_HEIGHT_PT,
    )

    scale = max(
        OUTPUT_WIDTH_PT / region_width,
        OUTPUT_HEIGHT_PT / region_height,
    )
    scaled_width = region_width * scale
    scaled_height = region_height * scale
    translate_x = (OUTPUT_WIDTH_PT - scaled_width) / 2.0
    translate_y = (OUTPUT_HEIGHT_PT - scaled_height) / 2.0

    working_page = copy.deepcopy(source_page)
    set_page_box(working_page, region)

    transform = (
        Transformation()
        .translate(-left, -bottom)
        .scale(scale, scale)
        .translate(translate_x, translate_y)
    )
    output_page.merge_transformed_page(working_page, transform, expand=False)
    return output_page


def fit_stretch_to_output(source_page: PageObject, region: BBox) -> PageObject:
    """Stretch the cropped region to exactly fill the output page with no padding."""
    left, bottom, right, top = region
    region_width = right - left
    region_height = top - bottom

    output_page = PageObject.create_blank_page(
        width=OUTPUT_WIDTH_PT,
        height=OUTPUT_HEIGHT_PT,
    )

    scale_x = OUTPUT_WIDTH_PT / region_width
    scale_y = OUTPUT_HEIGHT_PT / region_height

    working_page = copy.deepcopy(source_page)
    set_page_box(working_page, region)

    transform = (
        Transformation()
        .translate(-left, -bottom)
        .scale(scale_x, scale_y)
    )
    output_page.merge_transformed_page(working_page, transform, expand=False)
    return output_page


def split_bbox(bbox: BBox) -> tuple[BBox, BBox]:
    left, bottom, right, top = bbox
    mid_x = left + (right - left) / 2.0
    return (left, bottom, mid_x, top), (mid_x, bottom, right, top)


def regions_for_page(source_page_number: int, page: PageObject) -> tuple[ExportMode, list[BBox]]:
    if source_page_number == 1:
        return ExportMode.COVER, [detect_cover_bbox(page)]

    content = get_page_content(page)
    interior_bbox = detect_interior_bbox(page)
    left_region, right_region = split_bbox(interior_bbox)
    if is_colored_panel_page(content):
        return ExportMode.COLORED_SPLIT, [left_region, right_region]
    return ExportMode.SPLIT, [left_region, right_region]


def default_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_statement.pdf")


def process_pdf(input_path: Path, output_path: Path) -> tuple[int, int]:
    reader = PdfReader(str(input_path))
    writer = PdfWriter()
    output_page_count = 0

    for source_page_number, page in enumerate(reader.pages, start=1):
        mode, regions = regions_for_page(source_page_number, page)

        for region in regions:
            if mode == ExportMode.COVER:
                writer.add_page(fit_cover_to_output(page, region))
            elif mode == ExportMode.COLORED_SPLIT:
                writer.add_page(fit_stretch_to_output(page, region))
            else:
                writer.add_page(fit_region_to_output(page, region))
            output_page_count += 1

        if mode == ExportMode.COVER:
            bbox = regions[0]
            print(
                f"Page {source_page_number} (cover): right-half full-bleed from "
                f"{bbox[2] - bbox[0]:.1f}x{bbox[3] - bbox[1]:.1f} pt, no split"
            )
        elif mode == ExportMode.COLORED_SPLIT:
            interior = (
                regions[0][0],
                regions[0][1],
                regions[1][2],
                regions[0][3],
            )
            mid_x = regions[0][2]
            print(
                f"Page {source_page_number} (colored): cropped to "
                f"{interior[2] - interior[0]:.1f}x{interior[3] - interior[1]:.1f} pt, "
                f"split at x={mid_x:.1f}, stretch fill"
            )
        else:
            interior = (
                regions[0][0],
                regions[0][1],
                regions[1][2],
                regions[0][3],
            )
            mid_x = regions[0][2]
            print(
                f"Page {source_page_number}: stripped frame to "
                f"{interior[2] - interior[0]:.1f}x{interior[3] - interior[1]:.1f} pt, "
                f"split at x={mid_x:.1f}"
            )

    with output_path.open("wb") as output_file:
        writer.write(output_file)

    return len(reader.pages), output_page_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert a side-by-side gamebook PDF into portrait Statement pages "
            "(5.5 x 8.5 in). Page 1 uses the right-hand cover artwork as a "
            "full-bleed cover; pages 2 onward strip the outer frame, split the "
            "interior vertically, and resize each half."
        )
    )
    parser.add_argument("input_pdf", type=Path, help="Path to the source PDF")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output PDF path (default: <input>_statement.pdf)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.input_pdf.is_file():
        raise FileNotFoundError(f"Input PDF not found: {args.input_pdf}")

    output_path = args.output or default_output_path(args.input_pdf)
    source_pages, output_pages = process_pdf(args.input_pdf, output_path)
    print(
        f"Wrote {output_pages} portrait pages ({OUTPUT_WIDTH_PT:.0f}x{OUTPUT_HEIGHT_PT:.0f} pt) "
        f"from {source_pages} source pages to {output_path}"
    )


if __name__ == "__main__":
    main()
