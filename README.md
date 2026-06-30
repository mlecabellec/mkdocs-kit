# MkDocs Kit: Single-Binary Documentation Environment

MkDocs Kit is a wrapped, highly integrated documentation generation environment compiled into a **single standalone binary**. It allows you to write documentation using Markdown and various diagram formats, and compile them locally into **HTML5, PDF, and UNIX Man Pages** without any external Python dependencies.

## Key Features

* **Single-Binary Execution**: All Python resources, themes, and libraries (including `mkdocs`, the `material` theme, `weasyprint`, `wireviz`, `nwdiag`, and `bit_field`) are bundled into a single executable (`dist/mkdocs-kit`).
* **Integrated Diagram Engines**:
  * **PlantUML**: Renders UML diagrams (class, sequence, activity, etc.) locally using the system's `plantuml` command.
  * **WireViz**: Renders wiring and cabling diagrams from YAML.
  * **RackDiag**: Renders server rack layouts from `rackdiag` syntax.
  * **PacketDiag**: Renders network packet layouts from `packetdiag` syntax.
  * **ByteField**: Renders binary bit/byte field diagrams using Lisp-like DSL, JSON, or YAML.
* **Multi-Format Output**:
  * **HTML**: Standard, highly aesthetic responsive site utilizing the premium `material` theme.
  * **PDF**: A beautifully styled single-file PDF reference manual compiled with WeasyPrint.
  * **Man Pages**: Standard UNIX troff man pages compiled from Markdown files in the `docs/man/` directory.

---

## Installation & Setup

If you want to run or develop from source, set up the environment:

```bash
# Create virtual environment and install dependencies
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install "setuptools<82.0.0"
.venv/bin/pip install mkdocs mkdocs-material weasyprint wireviz nwdiag bit_field pyinstaller

# Install in editable mode
.venv/bin/pip install -e .
```

To compile the standalone binary:
```bash
.venv/bin/pyinstaller --onefile --name mkdocs-kit \
  --collect-all mkdocs \
  --collect-all material \
  --collect-all weasyprint \
  --collect-all wireviz \
  --collect-all blockdiag \
  --collect-all rackdiag \
  --collect-all packetdiag \
  --collect-all nwdiag \
  --collect-all bit_field \
  src/mkdocs_kit/cli.py
```

---

## Usage Instructions

### 1. Initialize a New Project
Create a new documentation workspace:
```bash
./dist/mkdocs-kit init my_docs
cd my_docs
```

### 2. Build Documentation
Build the HTML site, PDF reference manual, and UNIX man pages:
```bash
../dist/mkdocs-kit build
```
Outputs generated:
* `site/`: The responsive HTML site.
* `documentation.pdf` and `site/documentation.pdf`: The single-file PDF manual.
* `man/man1/mytool.1` and `site/man/man1/mytool.1`: The UNIX troff man page.

### 3. Serve the Site Locally
Preview the HTML site with live-reloading:
```bash
../dist/mkdocs-kit serve
```
Open your browser and navigate to `http://127.0.0.1:8000`.

---

## Testing

A comprehensive test suite is located in `tests/test_all.py`. To run the tests:
```bash
.venv/bin/python -m unittest tests/test_all.py
```
