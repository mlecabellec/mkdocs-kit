import os
import re
import yaml
import datetime
from weasyprint import HTML

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

def generate_pdf(site_dir, mkdocs_yml_path, pdf_output_path):
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
            print(f"Warning: Could not parse {mkdocs_yml_path} for PDF generation: {e}")
            
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
            continue
            
        try:
            with open(found_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
        except Exception:
            continue
            
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
.diagram-plantuml, .diagram-wireviz, .diagram-rackdiag, .diagram-packetdiag, .diagram-bytefield, .diagram-blockdiag, .diagram-nwdiag {{
    text-align: center;
    margin: 20px 0;
    page-break-inside: avoid;
}}
.diagram-plantuml svg, .diagram-wireviz svg, .diagram-rackdiag svg, .diagram-packetdiag svg, .diagram-bytefield svg, .diagram-blockdiag svg, .diagram-nwdiag svg {{
    max-width: 100% !important;
    max-height: 22cm !important;
    width: auto !important;
    height: auto !important;
    object-fit: contain !important;
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
