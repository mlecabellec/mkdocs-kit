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
