import os
import re
import yaml
import datetime
import logging
from weasyprint import HTML

# Custom logging handler to intercept WeasyPrint warnings and errors for reporter
class WeasyPrintLogHandler(logging.Handler):
    def __init__(self, reporter=None):
        super().__init__()
        self.reporter = reporter

    def emit(self, record):
        msg = self.format(record)
        if self.reporter:
            if record.levelno >= logging.ERROR:
                self.reporter.error(f"WeasyPrint PDF Engine: {msg}", category="PDF_ENGINE")
                self.reporter.record_pdf_issue("WEASYPRINT_ERROR", "Global", msg)
            elif record.levelno >= logging.WARNING:
                self.reporter.warn(f"WeasyPrint PDF Engine: {msg}", category="PDF_ENGINE")
                self.reporter.record_pdf_issue("WEASYPRINT_WARNING", "Global", msg)

def flatten_nav(nav):
    pages = []
    if isinstance(nav, list):
        for item in nav:
            pages.extend(flatten_nav(item))
    elif isinstance(nav, dict):
        for key, value in nav.items():
            pages.extend(flatten_nav(value))
    elif isinstance(nav, str):
        pages.append(nav)
    return pages

def extract_main_content(html_content):
    match = re.search(r'<article\b[^>]*>(.*?)</article>', html_content, re.DOTALL)
    if match:
        return match.group(1)
    match = re.search(r'<div\b[^>]*role="main"[^>]*>(.*?)</div>', html_content, re.DOTALL)
    if match:
        return match.group(1)
    match = re.search(r'<body\b[^>]*>(.*?)</body>', html_content, re.DOTALL)
    if match:
        return match.group(1)
    return html_content

def adjust_paths(html_content, page_dir):
    if not page_dir or page_dir == '.':
        return html_content
    
    def replace_path(match):
        attr = match.group(1)
        path = match.group(2)
        if path.startswith(('http://', 'https://', '/', '#', 'mailto:', 'tel:')):
            return match.group(0)
        new_path = os.path.normpath(os.path.join(page_dir, path))
        return f'{attr}="{new_path}"'
        
    pattern = r'\b(src|href)="([^"]*)"'
    return re.sub(pattern, replace_path, html_content)

def inspect_missing_files_in_html(html_content, site_dir, page_name, reporter=None):
    """
    Scans HTML content for embedded image, media, or stylesheet assets and checks if they exist on disk.
    Logs warnings if required rendering assets are missing.
    """
    # Match <img src="...">, <object data="...">, <embed src="...">, <source src="...">, <link rel="stylesheet" href="...">
    patterns = [
        r'<img\b[^>]*\bsrc=["\']([^"\']+)["\']',
        r'<object\b[^>]*\bdata=["\']([^"\']+)["\']',
        r'<embed\b[^>]*\bsrc=["\']([^"\']+)["\']',
        r'<source\b[^>]*\bsrc=["\']([^"\']+)["\']',
        r'<image\b[^>]*\b(?:href|xlink:href)=["\']([^"\']+)["\']',
        r'<link\b[^>]*\brel=["\']stylesheet["\'][^>]*\bhref=["\']([^"\']+)["\']',
    ]

    for pat in patterns:
        for match in re.finditer(pat, html_content, re.IGNORECASE):
            path = match.group(1).strip()
            if path.startswith(('http://', 'https://', '#', 'mailto:', 'tel:', 'data:')):
                continue

            target_path = os.path.normpath(os.path.join(site_dir, path))
            if not os.path.exists(target_path):
                msg = f"Asset file '{path}' referenced in page '{page_name}' does not exist at '{target_path}' for PDF rendering."
                if reporter:
                    reporter.warn(msg, category="PDF_MISSING_FILE")
                    reporter.record_pdf_issue("MISSING_FILE", page_name, msg)

def inspect_svg_bounding_boxes(html_content, page_name, reporter=None):
    """
    Inspects embedded inline SVGs for bounding dimensions (width, height, viewBox).
    A4 printable width is approx 170mm (~643px at 96dpi), height approx 257mm (~971px).
    Warns if diagram bounding box dimensions exceed printable page bounds without max-width constraint.
    """
    svg_blocks = re.findall(r'<svg\b[^>]*>(.*?)</svg>', html_content, re.DOTALL | re.IGNORECASE)
    MAX_A4_WIDTH_PX = 643   # 170mm at 96dpi
    MAX_A4_HEIGHT_PX = 971  # 257mm at 96dpi

    for idx, svg_block in enumerate(svg_blocks, 1):
        width_match = re.search(r'\bwidth=["\']([0-9.]+)(px|pt|mm|cm)?["\']', svg_block, re.IGNORECASE)
        height_match = re.search(r'\bheight=["\']([0-9.]+)(px|pt|mm|cm)?["\']', svg_block, re.IGNORECASE)
        viewbox_match = re.search(r'\bviewBox=["\']([0-9.\s,-]+)["\']', svg_block, re.IGNORECASE)

        width_val = None
        height_val = None

        if width_match:
            try:
                width_val = float(width_match.group(1))
                unit = width_match.group(2)
                if unit == 'pt': width_val *= 1.333
                elif unit == 'mm': width_val *= 3.779
                elif unit == 'cm': width_val *= 37.79
            except ValueError:
                pass

        if height_match:
            try:
                height_val = float(height_match.group(1))
                unit = height_match.group(2)
                if unit == 'pt': height_val *= 1.333
                elif unit == 'mm': height_val *= 3.779
                elif unit == 'cm': height_val *= 37.79
            except ValueError:
                pass

        if (width_val is None or height_val is None) and viewbox_match:
            try:
                parts = [float(p) for p in re.split(r'[\s,]+', viewbox_match.group(1).strip()) if p]
                if len(parts) >= 4:
                    if width_val is None: width_val = parts[2]
                    if height_val is None: height_val = parts[3]
            except ValueError:
                pass

        if width_val and width_val > MAX_A4_WIDTH_PX:
            msg = f"SVG diagram #{idx} in page '{page_name}' bounding box width ({width_val:.0f}px) exceeds A4 printable page width ({MAX_A4_WIDTH_PX}px)."
            if reporter:
                reporter.warn(msg, category="PDF_BOUNDING_BOX")
                reporter.record_pdf_issue("BOUNDING_BOX_OVERFLOW", page_name, msg)

        if height_val and height_val > MAX_A4_HEIGHT_PX:
            msg = f"SVG diagram #{idx} in page '{page_name}' bounding box height ({height_val:.0f}px) exceeds A4 printable page height ({MAX_A4_HEIGHT_PX}px)."
            if reporter:
                reporter.warn(msg, category="PDF_BOUNDING_BOX")
                reporter.record_pdf_issue("BOUNDING_BOX_OVERFLOW", page_name, msg)

def generate_pdf(site_dir, mkdocs_yml_path, pdf_output_path, reporter=None):
    # Attach WeasyPrint logger handler
    weasy_logger = logging.getLogger('weasyprint')
    log_handler = WeasyPrintLogHandler(reporter)
    weasy_logger.addHandler(log_handler)

    try:
        site_name = "Documentation"
        pages = []
        if os.path.exists(mkdocs_yml_path):
            try:
                with open(mkdocs_yml_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                    site_name = config.get('site_name', site_name)
                    nav = config.get('nav')
                    if nav:
                        pages = flatten_nav(nav)
            except Exception as e:
                msg = f"Could not parse {mkdocs_yml_path} for PDF generation: {e}"
                if reporter:
                    reporter.warn(msg, category="PDF_CONFIG")

        if not pages:
            for root, dirs, files in os.walk(site_dir):
                for file in files:
                    if file.endswith('.html') and file != '404.html':
                        rel_path = os.path.relpath(os.path.join(root, file), site_dir)
                        pages.append(rel_path)
            pages.sort()

        combined_body_parts = []
        for page in pages:
            if page.endswith('.html'):
                found_path = os.path.join(site_dir, page)
                page_rel_dir = os.path.dirname(page)
            else:
                if page == "index.md":
                    html_paths_to_try = ["index.html"]
                else:
                    name_no_ext = os.path.splitext(page)[0]
                    html_paths_to_try = [
                        os.path.join(name_no_ext, "index.html"),
                        name_no_ext + ".html"
                    ]
                    
                found_path = None
                page_rel_dir = ""
                for rel_try in html_paths_to_try:
                    full_try = os.path.normpath(os.path.join(site_dir, rel_try))
                    if os.path.exists(full_try):
                        found_path = full_try
                        page_rel_dir = os.path.dirname(rel_try)
                        break
                        
            if not found_path or not os.path.exists(found_path):
                msg = f"Page target '{page}' missing in built HTML site directory '{site_dir}'."
                if reporter:
                    reporter.warn(msg, category="PDF_MISSING_PAGE")
                    reporter.record_pdf_issue("MISSING_PAGE", page, msg)
                continue
                
            try:
                with open(found_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
            except Exception as e:
                msg = f"Failed to read page HTML file '{found_path}': {e}"
                if reporter:
                    reporter.error(msg, category="PDF_READ_ERROR")
                continue
                
            # Perform diagnostic checks for missing files and SVG bounding boxes
            inspect_missing_files_in_html(html_content, site_dir, page, reporter)
            inspect_svg_bounding_boxes(html_content, page, reporter)

            content = extract_main_content(html_content)
            content = adjust_paths(content, page_rel_dir)
            
            if combined_body_parts:
                combined_body_parts.append('<div class="page-break"></div>')
                
            combined_body_parts.append(f'<section class="pdf-page" data-source="{page}">{content}</section>')

        master_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{site_name}</title>
<style>
@page {{
    size: A4;
    margin: 2cm;
    @bottom-right {{
        content: counter(page);
        font-family: 'Roboto', 'Helvetica', 'Arial', sans-serif;
        font-size: 9pt;
        color: #666;
    }}
    @top-left {{
        content: "{site_name}";
        font-family: 'Roboto', 'Helvetica', 'Arial', sans-serif;
        font-size: 9pt;
        color: #666;
        border-bottom: 0.5px solid #ddd;
        padding-bottom: 3px;
        width: 100%;
    }}
}}
body {{
    font-family: 'Roboto', 'Helvetica', 'Arial', sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #333;
}}
h1, h2, h3, h4, h5, h6 {{
    font-family: 'Outfit', 'Inter', sans-serif;
    color: #111;
    page-break-after: avoid;
}}
h1 {{
    font-size: 24pt;
    margin-top: 0;
    border-bottom: 1px solid #eee;
    padding-bottom: 10px;
}}
h2 {{
    font-size: 18pt;
    margin-top: 1.5em;
}}
h3 {{
    font-size: 14pt;
    margin-top: 1.2em;
}}
pre, code {{
    font-family: 'Courier New', Courier, monospace;
    background-color: #f5f5f5;
    border-radius: 3px;
}}
pre {{
    padding: 10px;
    border: 1px solid #ccc;
    white-space: pre-wrap;
    page-break-inside: avoid;
}}
code {{
    padding: 2px 4px;
    background-color: #f5f5f5;
    font-size: 9.5pt;
}}
img {{
    max-width: 100%;
    height: auto;
    page-break-inside: avoid;
}}
.page-break {{
    page-break-before: always;
}}
.diagram-plantuml, .diagram-wireviz, .diagram-rackdiag, .diagram-packetdiag, .diagram-bytefield, .diagram-blockdiag, .diagram-nwdiag, .mkdocs-kit-plotly-wrapper, .mkdocs-kit-d3-wrapper {{
    text-align: center;
    margin: 20px 0;
    page-break-inside: avoid;
}}
.diagram-plantuml svg, .diagram-wireviz svg, .diagram-rackdiag svg, .diagram-packetdiag svg, .diagram-bytefield svg, .diagram-blockdiag svg, .diagram-nwdiag svg, .mkdocs-kit-plotly-wrapper svg, .mkdocs-kit-d3-wrapper svg {{
    max-width: 100% !important;
    max-height: 20cm !important;
    width: auto !important;
    height: auto !important;
    object-fit: contain !important;
}}
.mkdocs-kit-csv-controls, .mkdocs-kit-csv-pagination {{
    display: none !important;
}}
table.mkdocs-kit-csv-table {{
    width: 100% !important;
    border-collapse: collapse !important;
    margin: 15px 0 !important;
    font-size: 9pt !important;
}}
table.mkdocs-kit-csv-table thead {{
    display: table-header-group !important;
}}
table.mkdocs-kit-csv-table tr {{
    page-break-inside: avoid !important;
}}
table.mkdocs-kit-csv-table th, table.mkdocs-kit-csv-table td {{
    border: 1px solid #d2d2d7 !important;
    padding: 6px 8px !important;
}}
table.mkdocs-kit-csv-table th {{
    background-color: #f5f5f7 !important;
    color: #1d1d1f !important;
    font-weight: 600 !important;
}}
</style>
</head>
<body>
<div class="cover-page" style="page-break-after: always; text-align: center; padding-top: 5cm;">
    <h1 style="font-size: 36pt; border: none; margin-bottom: 20px;">{site_name}</h1>
    <p style="font-size: 14pt; color: #666;">Generated Documentation Reference</p>
    <p style="font-size: 11pt; color: #999; margin-top: 5cm;">Date: {datetime.date.today().strftime("%B %d, %Y")}</p>
</div>
{"".join(combined_body_parts)}
</body>
</html>
"""

        html_obj = HTML(string=master_html, base_url=site_dir)
        html_obj.write_pdf(pdf_output_path)
    finally:
        weasy_logger.removeHandler(log_handler)
