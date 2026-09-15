import os
import re
import io
import yaml
import datetime
import logging
from io import BytesIO

try:
    import docx
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml import parse_xml, OxmlElement
    from docx.oxml.ns import nsdecls, qn
except ImportError:
    docx = None

try:
    import cairosvg
except ImportError:
    cairosvg = None

import lxml.html
from mkdocs_kit.pdf import flatten_nav, extract_main_content, adjust_paths


def _add_page_number_to_footer(footer_paragraph):
    """
    Adds a dynamic 'Page X of Y' field into the Word document footer using OpenXML fields.
    """
    footer_paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = footer_paragraph.add_run("Page ")
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(128, 128, 128)

    # PAGE field
    fldSimple1 = OxmlElement('w:fldSimple')
    fldSimple1.set(qn('w:instr'), 'PAGE')
    footer_paragraph._p.append(fldSimple1)

    run2 = footer_paragraph.add_run(" of ")
    run2.font.size = Pt(9)
    run2.font.color.rgb = RGBColor(128, 128, 128)

    # NUMPAGES field
    fldSimple2 = OxmlElement('w:fldSimple')
    fldSimple2.set(qn('w:instr'), 'NUMPAGES')
    footer_paragraph._p.append(fldSimple2)


def _add_toc_field(paragraph):
    """
    Inserts a native Word Table of Contents field into the given paragraph.
    """
    fldSimple = OxmlElement('w:fldSimple')
    fldSimple.set(qn('w:instr'), r'TOC \o "1-3" \h \z \u')
    paragraph._p.append(fldSimple)


def _set_cell_background(cell, fill_hex):
    """
    Sets the background fill color of a table cell.
    """
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)


def _set_cell_borders(cell, top=None, bottom=None, left=None, right=None, color="CCCCCC", sz="4"):
    """
    Applies custom borders to a Word table cell.
    """
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>\n'
        f'  <w:top w:val="{"single" if top else "none"}" w:sz="{sz}" w:space="0" w:color="{color}"/>\n'
        f'  <w:left w:val="{"single" if left else "none"}" w:sz="{sz}" w:space="0" w:color="{color}"/>\n'
        f'  <w:bottom w:val="{"single" if bottom else "none"}" w:sz="{sz}" w:space="0" w:color="{color}"/>\n'
        f'  <w:right w:val="{"single" if right else "none"}" w:sz="{sz}" w:space="0" w:color="{color}"/>\n'
        f'</w:tcBorders>'
    )
    tcPr.append(tcBorders)


def _add_hyperlink(paragraph, url, text, color="004B87", underline=True):
    """
    Adds a clickable hyperlink into a Word paragraph.
    """
    part = paragraph.part
    r_id = part.relate_to(url, docx.opc.constants.RELATIONSHIP_TYPE.HYPERLINK, is_external=True)

    hyperlink = parse_xml(
        f'<w:hyperlink {nsdecls("w", "r")} r:id="{r_id}" w:history="1">\n'
        f'  <w:r>\n'
        f'    <w:rPr>\n'
        f'      <w:color w:val="{color}"/>\n'
        f'      {"<w:u w:val=\"single\"/>" if underline else ""}\n'
        f'    </w:rPr>\n'
        f'    <w:t xml:space="preserve">{text}</w:t>\n'
        f'  </w:r>\n'
        f'</w:hyperlink>'
    )
    paragraph._p.append(hyperlink)


def _setup_docx_styles(doc):
    """
    Configures default professional styles and color palettes on a fresh Word Document.
    """
    # Configure Normal Style
    style_normal = doc.styles['Normal']
    style_normal.font.name = 'Segoe UI'
    style_normal.font.size = Pt(10.5)
    style_normal.font.color.rgb = RGBColor(34, 34, 34)
    style_normal.paragraph_format.line_spacing = 1.15
    style_normal.paragraph_format.space_after = Pt(6)

    # Heading colors
    primary_color = RGBColor(0, 75, 135)     # #004B87
    secondary_color = RGBColor(30, 80, 120)  # #1E5078
    accent_color = RGBColor(70, 70, 70)

    for level, (pt_size, color) in enumerate([
        (22, primary_color),
        (16, primary_color),
        (13.5, secondary_color),
        (12, secondary_color),
        (11, accent_color),
        (10.5, accent_color),
    ], 1):
        style_name = f'Heading {level}'
        if style_name in doc.styles:
            h_style = doc.styles[style_name]
            h_style.font.name = 'Segoe UI Semibold'
            h_style.font.size = Pt(pt_size)
            h_style.font.color.rgb = color
            h_style.font.bold = True
            h_style.paragraph_format.space_before = Pt(12)
            h_style.paragraph_format.space_after = Pt(4)
            h_style.paragraph_format.keep_with_next = True


def _rasterize_svg(svg_content, dpi=300, max_width_in=6.0):
    """
    Converts SVG markup string to PNG byte data using cairosvg with 300 DPI.
    Returns (png_bytes, width_in, height_in) or None if rasterization fails.
    """
    if not cairosvg:
        return None

    try:
        # Extract intrinsic dimensions if available
        w_match = re.search(r'\bwidth=["\']([0-9.]+)(px|pt|mm|cm)?["\']', svg_content, re.IGNORECASE)
        h_match = re.search(r'\bheight=["\']([0-9.]+)(px|pt|mm|cm)?["\']', svg_content, re.IGNORECASE)
        vb_match = re.search(r'\bviewBox=["\']([0-9.\s,-]+)["\']', svg_content, re.IGNORECASE)

        orig_w_pt = None
        orig_h_pt = None

        if w_match and h_match:
            try:
                w_val = float(w_match.group(1))
                h_val = float(h_match.group(1))
                u = w_match.group(2)
                if u == 'px' or not u:
                    orig_w_pt = w_val * 0.75
                    orig_h_pt = h_val * 0.75
                elif u == 'mm':
                    orig_w_pt = w_val * 2.834
                    orig_h_pt = h_val * 2.834
                elif u == 'cm':
                    orig_w_pt = w_val * 28.34
                    orig_h_pt = h_val * 28.34
                elif u == 'pt':
                    orig_w_pt = w_val
                    orig_h_pt = h_val
            except Exception:
                pass

        if not orig_w_pt and vb_match:
            try:
                parts = [float(p) for p in re.split(r'[\s,]+', vb_match.group(1).strip()) if p]
                if len(parts) >= 4:
                    orig_w_pt = parts[2] * 0.75
                    orig_h_pt = parts[3] * 0.75
            except Exception:
                pass

        png_bytes = cairosvg.svg2png(bytestring=svg_content.encode('utf-8'), dpi=dpi)

        # Calculate display width in inches
        target_width = max_width_in
        if orig_w_pt:
            w_in = orig_w_pt / 72.0
            target_width = min(max_width_in, max(1.5, w_in))

        return png_bytes, target_width
    except Exception as e:
        return None


def _render_html_nodes_to_docx(element, doc, site_dir, page_name, reporter=None):
    """
    Recursively converts HTML element tree nodes into formatted Word document blocks.
    """
    for child in element:
        tag = child.tag.lower() if isinstance(child.tag, str) else ''

        # Headings (h1 to h6)
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            level = int(tag[1])
            text = (child.text_content() or '').strip()
            if text:
                doc.add_heading(text, level=level)

        # Paragraphs (<p>)
        elif tag == 'p':
            p = doc.add_paragraph()
            _format_inline_html(child, p, site_dir, page_name, reporter=reporter)

        # Blockquotes & Admonitions (<div class="admonition ..."> or <blockquote>)
        elif tag in ('blockquote', 'div') and ('admonition' in child.get('class', '') or tag == 'blockquote'):
            classes = child.get('class', '')
            adm_type = "info"
            if 'warning' in classes or 'caution' in classes:
                adm_type = "warning"
            elif 'danger' in classes or 'error' in classes:
                adm_type = "danger"
            elif 'tip' in classes or 'success' in classes:
                adm_type = "tip"
            elif 'note' in classes:
                adm_type = "note"

            border_colors = {
                "info": "004B87",
                "warning": "F59E0B",
                "danger": "EF4444",
                "tip": "10B981",
                "note": "6366F1",
            }
            bg_colors = {
                "info": "F0F7FC",
                "warning": "FFFBEB",
                "danger": "FEF2F2",
                "tip": "ECFDF5",
                "note": "F5F7FF",
            }
            border_color = border_colors.get(adm_type, "004B87")
            bg_color = bg_colors.get(adm_type, "F0F7FC")

            # Create 1x1 callout table
            tbl = doc.add_table(rows=1, cols=1)
            tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
            tbl.autofit = False
            cell = tbl.cell(0, 0)
            cell.width = Inches(6.0)

            _set_cell_background(cell, bg_color)
            _set_cell_borders(cell, left=True, color=border_color, sz="24")  # 3pt thick left border

            # Title
            title_el = child.find('.//p[@class="admonition-title"]')
            cell_p = cell.paragraphs[0]
            cell_p.paragraph_format.space_before = Pt(4)
            cell_p.paragraph_format.space_after = Pt(4)

            if title_el is not None:
                r_title = cell_p.add_run(f"📌 {title_el.text_content().strip()}\n")
                r_title.bold = True
                r_title.font.color.rgb = RGBColor.from_string(border_color)
                # Remove title element to avoid duplicate render
                child.remove(title_el)

            # Format rest of callout content
            body_text = child.text_content().strip()
            if body_text:
                r_body = cell_p.add_run(body_text)
                r_body.font.size = Pt(9.5)

            # Space after table
            sp_p = doc.add_paragraph()
            sp_p.paragraph_format.space_before = Pt(0)
            sp_p.paragraph_format.space_after = Pt(4)

        # Code Blocks (<pre><code>)
        elif tag == 'pre':
            code_el = child.find('code')
            code_text = (code_el.text_content() if code_el is not None else child.text_content()) or ''
            
            tbl = doc.add_table(rows=1, cols=1)
            tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
            tbl.autofit = False
            cell = tbl.cell(0, 0)
            cell.width = Inches(6.0)
            _set_cell_background(cell, "F8F9FA")
            _set_cell_borders(cell, top=True, bottom=True, left=True, right=True, color="E5E7EB", sz="4")

            cp = cell.paragraphs[0]
            cp.paragraph_format.space_before = Pt(4)
            cp.paragraph_format.space_after = Pt(4)
            r = cp.add_run(code_text.rstrip())
            r.font.name = 'Consolas'
            r.font.size = Pt(9.0)
            r.font.color.rgb = RGBColor(40, 40, 40)

            sp_p = doc.add_paragraph()
            sp_p.paragraph_format.space_after = Pt(4)

        # Unordered / Ordered Lists (<ul>, <ol>)
        elif tag in ('ul', 'ol'):
            list_style = 'List Bullet' if tag == 'ul' else 'List Number'
            for li in child.findall('li'):
                lp = doc.add_paragraph(style=list_style)
                _format_inline_html(li, lp, site_dir, page_name, reporter=reporter)

        # Tables (<table>)
        elif tag == 'table':
            rows = child.findall('.//tr')
            if rows:
                num_cols = max(len(r.findall('.//th') + r.findall('.//td')) for r in rows)
                tbl = doc.add_table(rows=len(rows), cols=num_cols)
                tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
                tbl.autofit = True

                for r_idx, r_elem in enumerate(rows):
                    cells = r_elem.findall('.//th') + r_elem.findall('.//td')
                    is_header = bool(r_elem.findall('.//th'))
                    for c_idx, c_elem in enumerate(cells):
                        if c_idx < num_cols:
                            cell = tbl.cell(r_idx, c_idx)
                            cell_p = cell.paragraphs[0]
                            cell_p.paragraph_format.space_before = Pt(3)
                            cell_p.paragraph_format.space_after = Pt(3)

                            _format_inline_html(c_elem, cell_p, site_dir, page_name, reporter=reporter)

                            if is_header:
                                _set_cell_background(cell, "004B87")
                                _set_cell_borders(cell, top=True, bottom=True, left=True, right=True, color="003366", sz="4")
                                for run in cell_p.runs:
                                    run.bold = True
                                    run.font.color.rgb = RGBColor(255, 255, 255)
                            else:
                                bg = "F9FAFB" if r_idx % 2 == 1 else "FFFFFF"
                                _set_cell_background(cell, bg)
                                _set_cell_borders(cell, top=True, bottom=True, left=True, right=True, color="E5E7EB", sz="4")

                sp_p = doc.add_paragraph()
                sp_p.paragraph_format.space_after = Pt(6)

        # Inline SVG Diagrams (<svg>)
        elif tag == 'svg':
            svg_str = lxml.html.tostring(child, encoding='utf-8').decode('utf-8')
            res = _rasterize_svg(svg_str, dpi=300, max_width_in=6.0)
            if res:
                png_bytes, width_in = res
                img_p = doc.add_paragraph()
                img_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                img_p.paragraph_format.space_before = Pt(6)
                img_p.paragraph_format.space_after = Pt(6)
                img_p.add_run().add_picture(BytesIO(png_bytes), width=Inches(width_in))
                if reporter:
                    reporter.log(f"  [DOCX] Embedded rasterized SVG diagram in page '{page_name}' ({len(png_bytes)} bytes)")

        # Standalone Images (<img>)
        elif tag == 'img':
            src = child.get('src', '').strip()
            _insert_image_run(doc, src, site_dir, page_name, reporter=reporter)

        # Horizontal rule (<hr>)
        elif tag == 'hr':
            hr_p = doc.add_paragraph()
            hr_p.paragraph_format.space_before = Pt(6)
            hr_p.paragraph_format.space_after = Pt(6)
            r = hr_p.add_run("―" * 40)
            r.font.color.rgb = RGBColor(200, 200, 200)

        # Recursive traversal for generic containers (<div>, <section>, <article>, <main>)
        elif tag in ('div', 'section', 'article', 'main', 'details'):
            _render_html_nodes_to_docx(child, doc, site_dir, page_name, reporter=reporter)


def _format_inline_html(element, paragraph, site_dir, page_name, reporter=None):
    """
    Translates inline HTML elements (b, strong, i, em, code, a, img, svg) into Word Run formatting.
    """
    if element.text:
        paragraph.add_run(element.text)

    for child in element:
        tag = child.tag.lower() if isinstance(child.tag, str) else ''

        if tag in ('b', 'strong'):
            r = paragraph.add_run(child.text_content())
            r.bold = True

        elif tag in ('i', 'em'):
            r = paragraph.add_run(child.text_content())
            r.italic = True

        elif tag == 'code':
            r = paragraph.add_run(child.text_content())
            r.font.name = 'Consolas'
            r.font.size = Pt(9.5)
            r.font.color.rgb = RGBColor(180, 40, 70)

        elif tag == 'a':
            href = child.get('href', '')
            text = child.text_content() or href
            if href.startswith(('http://', 'https://', 'mailto:')):
                _add_hyperlink(paragraph, href, text)
            else:
                r = paragraph.add_run(text)
                r.font.color.rgb = RGBColor(0, 75, 135)
                r.underline = True

        elif tag == 'img':
            src = child.get('src', '').strip()
            _insert_image_run(paragraph, src, site_dir, page_name, reporter=reporter, inline=True)

        elif tag == 'svg':
            svg_str = lxml.html.tostring(child, encoding='utf-8').decode('utf-8')
            res = _rasterize_svg(svg_str, dpi=300, max_width_in=5.8)
            if res:
                png_bytes, width_in = res
                paragraph.add_run().add_picture(BytesIO(png_bytes), width=Inches(width_in))

        else:
            paragraph.add_run(child.text_content())

        if child.tail:
            paragraph.add_run(child.tail)


def _insert_image_run(target, src, site_dir, page_name, reporter=None, inline=False):
    """
    Loads and embeds an image file from disk into the target document or paragraph.
    """
    if not src or src.startswith('data:'):
        return

    img_path = os.path.normpath(os.path.join(site_dir, src))
    if not os.path.isfile(img_path):
        if reporter:
            reporter.warn(f"[DOCX] Image asset '{src}' not found at '{img_path}'.", category="DOCX_MISSING_FILE")
        return

    try:
        # If image is SVG, convert to PNG
        if src.lower().endswith('.svg'):
            with open(img_path, 'r', encoding='utf-8') as f:
                svg_data = f.read()
            res = _rasterize_svg(svg_data, dpi=300, max_width_in=6.0)
            if res:
                png_bytes, width_in = res
                if inline:
                    target.add_run().add_picture(BytesIO(png_bytes), width=Inches(width_in))
                else:
                    p = target.add_paragraph()
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p.add_run().add_picture(BytesIO(png_bytes), width=Inches(width_in))
        else:
            if inline:
                target.add_run().add_picture(img_path, width=Inches(min(5.5, 4.0)))
            else:
                p = target.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.add_run().add_picture(img_path, width=Inches(min(5.5, 5.0)))
    except Exception as e:
        if reporter:
            reporter.warn(f"[DOCX] Failed to embed image '{src}': {e}", category="DOCX_IMAGE_ERROR")


def generate_docx(site_dir, config_file, output_docx_path, template_path=None, reporter=None):
    """
    Generates a single consolidated MS-Word (.docx) document from the compiled MkDocs HTML site.
    
    Includes:
    - Title / Cover page
    - Table of Contents
    - Formatted Headings (H1-H6), Paragraphs, Lists, Tables
    - Callout / Admonition boxes
    - High-resolution rasterized diagrams (PlantUML, WireViz, etc.)
    - Headers / Footers with dynamic page numbering
    """
    if not docx:
        raise RuntimeError("python-docx is not installed. Please install python-docx to enable DOCX output.")

    if reporter:
        reporter.log(f"[DOCX] Initiating consolidated MS-Word document compilation to '{output_docx_path}'...")

    # Load configuration
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    site_name = config.get('site_name', 'Documentation')
    site_description = config.get('site_description', '')
    site_author = config.get('site_author', '')
    nav = config.get('nav', [])

    # Initialize Document (from template if supplied)
    if template_path and os.path.isfile(template_path):
        if reporter:
            reporter.log(f"[DOCX] Using custom reference template: '{template_path}'")
        doc = docx.Document(template_path)
    else:
        doc = docx.Document()
        _setup_docx_styles(doc)

    # Setup Section & Header/Footer
    section = doc.sections[0]
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)

    # Header
    header = section.header
    header_p = header.paragraphs[0]
    header_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_hdr = header_p.add_run(site_name)
    r_hdr.font.size = Pt(8.5)
    r_hdr.font.color.rgb = RGBColor(140, 140, 140)

    # Footer (Page X of Y)
    footer = section.footer
    _add_page_number_to_footer(footer.paragraphs[0])

    # ==================== COVER PAGE ====================
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(120)
    title_p.paragraph_format.space_after = Pt(12)
    r_title = title_p.add_run(site_name)
    r_title.font.name = 'Segoe UI Semibold'
    r_title.font.size = Pt(32)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(0, 75, 135)

    if site_description:
        desc_p = doc.add_paragraph()
        desc_p.paragraph_format.space_after = Pt(24)
        r_desc = desc_p.add_run(site_description)
        r_desc.font.size = Pt(14)
        r_desc.font.color.rgb = RGBColor(100, 100, 100)

    meta_p = doc.add_paragraph()
    meta_p.paragraph_format.space_before = Pt(80)
    meta_p.paragraph_format.space_after = Pt(4)
    if site_author:
        r_auth = meta_p.add_run(f"Author: {site_author}\n")
        r_auth.font.size = Pt(10)
        r_auth.font.color.rgb = RGBColor(120, 120, 120)

    date_str = datetime.datetime.now().strftime("%B %d, %Y")
    r_date = meta_p.add_run(f"Generated: {date_str}")
    r_date.font.size = Pt(10)
    r_date.font.color.rgb = RGBColor(120, 120, 120)

    doc.add_page_break()

    # ==================== TABLE OF CONTENTS ====================
    toc_h = doc.add_heading("Table of Contents", level=1)
    toc_h.paragraph_format.space_after = Pt(12)
    toc_p = doc.add_paragraph()
    _add_toc_field(toc_p)
    doc.add_page_break()

    # ==================== CONTENT PAGES ====================
    pages = flatten_nav(nav)
    if not pages:
        for root, _, files in os.walk(site_dir):
            for f in files:
                if f.endswith('.html') and not f.startswith('.'):
                    rel = os.path.relpath(os.path.join(root, f), site_dir)
                    pages.append(rel)

    processed_count = 0
    for page_idx, page in enumerate(pages):
        html_file = os.path.splitext(page)[0] + '.html'
        html_path = os.path.join(site_dir, html_file)
        
        # Also try directory index format
        if not os.path.exists(html_path):
            dir_index = os.path.join(site_dir, os.path.splitext(page)[0], 'index.html')
            if os.path.exists(dir_index):
                html_path = dir_index

        if not os.path.exists(html_path):
            if reporter:
                reporter.warn(f"[DOCX] Compiled HTML for page '{page}' not found at '{html_path}'.", category="DOCX_MISSING_PAGE")
            continue

        with open(html_path, 'r', encoding='utf-8') as f:
            raw_html = f.read()

        main_html = extract_main_content(raw_html)
        page_dir = os.path.dirname(html_file)
        main_html = adjust_paths(main_html, page_dir)

        try:
            tree = lxml.html.fromstring(f'<div>{main_html}</div>')
            _render_html_nodes_to_docx(tree, doc, site_dir, page, reporter=reporter)
            processed_count += 1
            if reporter:
                reporter.log(f"  [DOCX] Processed page [{processed_count}/{len(pages)}]: '{page}'")
        except Exception as e:
            if reporter:
                reporter.error(f"[DOCX] Error parsing page '{page}': {e}", category="DOCX_PAGE_PARSE")

        # Add section separation between top-level navigation pages
        if page_idx < len(pages) - 1:
            doc.add_page_break()

    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_docx_path)), exist_ok=True)
    doc.save(output_docx_path)

    file_size_kb = os.path.getsize(output_docx_path) / 1024.0
    if reporter:
        reporter.log(f"[DOCX] Successfully compiled Word document '{output_docx_path}' ({processed_count} pages, {file_size_kb:.1f} KB).")

    return output_docx_path
