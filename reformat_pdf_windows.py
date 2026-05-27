"""Windows edition: reformat side-by-side gamebook PDFs to portrait Statement pages.

Run with:  py -3 reformat_pdf_windows.py INPUT.pdf
       or:  reformat_pdf.bat INPUT.pdf

Requires reformat_pdf.py in the same directory (shared processing logic).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from reformat_pdf import (
    OUTPUT_HEIGHT_PT,
    OUTPUT_WIDTH_PT,
    default_output_path,
    process_pdf,
)

# Windows extended-length path prefix (MAX_PATH workaround).
_WIN_LONG_PATH_PREFIX = "\\\\?\\"


def configure_windows_runtime() -> None:
    """Prepare the process for typical Windows console and path behavior."""
    if sys.platform != "win32":
        return

    # Python 3.7+ on Windows: UTF-8 console so status lines print reliably.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

def normalize_path(path: Path) -> Path:
    """Expand ~ and resolve to an absolute path using pathlib (works on all drives)."""
    expanded = path.expanduser()
    try:
        return expanded.resolve(strict=True)
    except FileNotFoundError:
        return expanded.resolve(strict=False)


def as_windows_io_path(path: Path) -> Path:
    """Return a path suitable for open() / pypdf on Windows, including long paths."""
    normalized = normalize_path(path)
    if sys.platform != "win32":
        return normalized

    text = str(normalized)
    if text.startswith(_WIN_LONG_PATH_PREFIX):
        return normalized
    if len(text) >= 260:
        return Path(_WIN_LONG_PATH_PREFIX + text)
    return normalized


def strip_long_path_prefix(path: Path) -> Path:
    """Remove the \\\\?\\ prefix so pathlib stem/parent behave normally."""
    text = str(path)
    if text.startswith(_WIN_LONG_PATH_PREFIX):
        return Path(text[len(_WIN_LONG_PATH_PREFIX) :])
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert a side-by-side gamebook PDF into portrait Statement pages "
            "(5.5 x 8.5 in). Page 1 uses the right-hand cover artwork as a "
            "full-bleed cover; pages 2 onward strip the outer frame, split the "
            "interior vertically, and resize each half."
        ),
        epilog=(
            "Examples:\n"
            "  py -3 reformat_pdf_windows.py C:\\Books\\bea.pdf\n"
            "  py -3 reformat_pdf_windows.py bea.pdf -o C:\\Books\\bea_statement.pdf\n"
            "  reformat_pdf.bat \"C:\\Books\\My Book.pdf\""
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input_pdf",
        type=Path,
        help="Path to the source PDF (absolute or relative)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output PDF path (default: <input>_statement.pdf next to the input file)",
    )
    return parser.parse_args()


def main() -> int:
    configure_windows_runtime()
    args = parse_args()

    input_path = as_windows_io_path(args.input_pdf)
    if not input_path.is_file():
        raise FileNotFoundError(f"Input PDF not found: {input_path}")

    logical_input = strip_long_path_prefix(normalize_path(args.input_pdf))
    output_arg = args.output or default_output_path(logical_input)
    output_path = as_windows_io_path(output_arg)

    # Ensure the parent folder exists when -o points to a new directory.
    output_path.parent.mkdir(parents=True, exist_ok=True)

    source_pages, output_pages = process_pdf(input_path, output_path)
    print(
        f"Wrote {output_pages} portrait pages ({OUTPUT_WIDTH_PT:.0f}x{OUTPUT_HEIGHT_PT:.0f} pt) "
        f"from {source_pages} source pages to {output_path}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
