# 📖 User Manual

This manual provides instructions for configuring and building documentation with the MkDocs-Kit toolchain.

---

## ⚙️ Configuration (`mkdocs.yml`)

To unlock all features of MkDocs-Kit, register the custom Diagrams plugin and configure the output options in your `mkdocs.yml`:

```yaml
site_name: Project Documentation
use_directory_urls: false  # REQUIRED: Ensures links point to index.html instead of directories

plugins:
  - search
  - mkdocs_kit.plugin: {}
```

> [!IMPORTANT]
> Setting `use_directory_urls: false` is critical. It ensures that local HTML previews (using `file://` scheme) resolve navigation paths successfully without requiring an active web server.

---

## 🛠️ Command Line Interface

MkDocs-Kit exposes a CLI through `mkdocs_kit.cli`. The basic commands are:

### Build Documentation
Generates static HTML files (inside `site/`), a single unified PDF manual (`documentation.pdf`), and UNIX man pages (inside `site/man/`):
```bash
python3 -m mkdocs_kit.cli build
```

### Serve Site
Starts a local development server with live-reloading:
```bash
python3 -m mkdocs_kit.cli serve
```

### Clean Build Output
Removes generated directories and files:
```bash
python3 -m mkdocs_kit.cli clean
```

---

## 🖨️ PDF Generation (WeasyPrint)

MkDocs-Kit compiles all pages defined in the `nav` section of `mkdocs.yml` into a single, high-fidelity PDF manual using WeasyPrint.

### Scaling & Page-Fit Rules
By default, the PDF stylesheet enforces the following constraints:
* **Aspect Ratio Preservation**: Diagrams and SVGs scale proportionally without distortion.
* **Page Bounds Fitting**: Large SVG diagrams are capped at a maximum height of `22cm` to ensure they fit cleanly inside the A4 printable area.

```css
/* Inside pdf.py custom print stylesheet */
.diagram-plantuml svg, .diagram-wireviz svg, .diagram-rackdiag svg {
    max-width: 100% !important;
    max-height: 22cm !important;
    width: auto !important;
    height: auto !important;
    object-fit: contain !important;
}
```

---

## 🐧 UNIX Man Page Generation

To generate UNIX Man pages, MkDocs-Kit scans the documentation structure for markdown files that contain a specific metadata block (frontmatter) at the very top.

### Frontmatter Structure
Add the following YAML block at the beginning of your markdown page:
```markdown
---
man: true
man_section: 1
man_name: my-utility
man_description: Executes custom configuration sweeps.
---
```

### Build Result
When you run the `build` command, MkDocs-Kit compiles these marked pages and writes them to the `site/man/` output folder (e.g. `site/man/man1/my-utility.1`).

---

## 📊 CSV File Inclusion, Interactive Sorting & Filtering

MkDocs-Kit supports embedding inline or external CSV files in Markdown using ````csv` blocks.

```markdown
```csv
file: data/employees.csv
page_size: 10
sort: "Salary desc"
filter: "Age >= 30"
search: true
caption: Employee Roster
```
```

* **HTML Features**: Interactive column header click-to-sort, instant multi-column search, and paginated navigation.
* **PDF Features**: Build-time dynamic filtering and column sorting, rendered into multi-page tables with repeating headers (`thead { display: table-header-group; }`).

---

## 📈 Plotly & D3.js Integration

### Plotly Charts (`plotly`)
```markdown
```plotly
data:
  - x: ["Q1", "Q2", "Q3", "Q4"]
    y: [120, 240, 180, 310]
    type: "bar"
    marker: { color: "#3498db" }
layout:
  title: "Quarterly Revenue"
```
```

### D3.js Diagrams (`d3`)
```markdown
```d3
type: "bar"
data:
  - label: "Alpha", value: 45
  - label: "Beta", value: 82
options:
  title: "Performance Metrics"
```
```

* **HTML**: Interactive Plotly and D3.js chart components.
* **PDF**: Pre-rendered static vector SVGs compiled into WeasyPrint PDFs.

---

## 📦 Automated Distribution Build Scripts


MkDocs-Kit includes deterministic, multi-distribution build scripts located in `scripts/`:

```bash
# Auto-detect local OS distribution and run full build & test sequence:
./scripts/build-all.sh

# Run explicit distribution build script:
./scripts/build-debian.sh -o ./output   # Builds Debian/Ubuntu .deb package
./scripts/build-fedora.sh -o ./output   # Builds Fedora/RHEL .rpm package
./scripts/build-arch.sh -o ./output     # Builds Arch Linux .pkg.tar.zst package
```

