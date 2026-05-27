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
python3 reformat_pdf.py velvet-labyrinth.pdf
python3 reformat_pdf.py /home/user/Downloads/crimson-atlas.pdf -o crimson-atlas-modified.pdf
```

### Windows

Use `reformat_pdf_windows.py` (or the included batch launcher). Paths may use backslashes or forward slashes; quotes are needed when a path contains spaces.

```powershell
py -3 reformat_pdf_windows.py C:\Books\velvet-labyrinth.pdf
py -3 reformat_pdf_windows.py velvet-labyrinth.pdf -o C:\Books\velvet-labyrinth_statement.pdf
```

From Command Prompt, you can also run the batch file in the project folder (it calls `py -3` when available, otherwise `python`):

```cmd
reformat_pdf.bat "C:\Books\Silver Compass.pdf"
reformat_pdf.bat obsidian-vault.pdf -o C:\Books\obsidian-vault_statement.pdf
```

Examples:

```powershell
py -3 reformat_pdf_windows.py marble-oracle.pdf
py -3 reformat_pdf_windows.py C:\Users\you\Downloads\crimson-atlas.pdf -o crimson-atlas-modified.pdf
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
