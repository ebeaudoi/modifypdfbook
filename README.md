# PDF Gamebook Reformatter

Converts side-by-side gamebook PDFs into portrait Statement pages (5.5 × 8.5 in).

## Requirements

- Python 3.10 or newer
- [pypdf](https://pypi.org/project/pypdf/) 4.0+

## Setup

**Linux / macOS**

```bash
cd /path/to/modifypdf
pip install -r requirements.txt
```

**Windows** (Command Prompt or PowerShell)

```powershell
cd C:\path\to\modifypdf
pip install -r requirements.txt
```

## Usage

Both platforms produce `INPUT_statement.pdf` next to the input file unless you pass `-o`.

### Linux / macOS

```bash
python3 reformat_pdf.py INPUT.pdf
python3 reformat_pdf.py INPUT.pdf -o OUTPUT.pdf
```

Examples:

```bash
python3 reformat_pdf.py bea.pdf
python3 reformat_pdf.py /home/user/Downloads/Quentin-Tello.pdf -o Quentin-Tello-modified.pdf
```

### Windows

Use `reformat_pdf_windows.py` (or the included batch launcher). Paths may use backslashes or forward slashes; quotes are needed when a path contains spaces.

```powershell
py -3 reformat_pdf_windows.py C:\Books\bea.pdf
py -3 reformat_pdf_windows.py bea.pdf -o C:\Books\bea_statement.pdf
```

From Command Prompt, you can also run the batch file in the project folder (it calls `py -3` when available, otherwise `python`):

```cmd
reformat_pdf.bat "C:\Books\My Book.pdf"
reformat_pdf.bat bea.pdf -o C:\Books\bea_statement.pdf
```

Examples:

```powershell
py -3 reformat_pdf_windows.py bea.pdf
py -3 reformat_pdf_windows.py C:\Users\you\Downloads\Quentin-Tello.pdf -o Quentin-Tello-modified.pdf
```

`reformat_pdf_windows.py` must stay in the same folder as `reformat_pdf.py` (it imports the shared processing logic). The Windows script resolves paths with `pathlib`, enables UTF-8 console output, and supports long paths when needed.

## What the script does

| Source page | Output |
|-------------|--------|
| Page 1 (cover) | Right-hand cover art, scaled full-bleed to one portrait page |
| Pages with a line-art frame | Frame removed, interior split into left and right halves, each resized to one portrait page |
| Pages with a solid colored panel | Same crop and split; each half is stretched to fill the page with no white margins |

Interior pages are produced at **396 × 612 pt** (5.5 × 8.5 in portrait).

## Help

**Linux / macOS**

```bash
python3 reformat_pdf.py --help
```

**Windows**

```powershell
py -3 reformat_pdf_windows.py --help
```
