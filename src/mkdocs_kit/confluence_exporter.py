import os
import re
import io
import json
import yaml
import zipfile
import datetime
import html
import lxml.html
import xml.etree.ElementTree as ET
from mkdocs_kit.pdf import flatten_nav, extract_main_content, adjust_paths


def _clean_csf_xml_string(xml_str):
    """
    Cleans and standardizes Confluence Storage Format XML snippet.
    """
    # Fix any unclosed void tags in HTML to be valid XML
    void_tags = ['br', 'hr', 'img', 'input', 'meta', 'link']
    for vt in void_tags:
        xml_str = re.sub(rf'<{vt}(\b[^>]*?)>', lambda m: f'<{vt}{m.group(1)}/>' if not m.group(1).rstrip().endswith('/') else m.group(0), xml_str, flags=re.IGNORECASE)
    # Self-close empty ri: tags like <ri:page ...></ri:page>
    xml_str = re.sub(r'<(ri:[a-zA-Z0-9_-]+)([^>]*)></\1>', r'<\1\2/>', xml_str)
    return xml_str


def _html_to_confluence_storage_format(html_content, page_id, site_dir, attachments_dict, page_title_map, reporter=None):
    """
    Converts standard HTML content into Atlassian Confluence Storage Format (CSF XHTML).
    
    Transforms:
    - Code blocks ➔ <ac:structured-macro ac:name="code">
    - Admonition callouts ➔ <ac:structured-macro ac:name="info|warning|tip|note">
    - Details / expand blocks ➔ <ac:structured-macro ac:name="expand">
    - Inline & linked diagrams (SVG) ➔ Extracted attachments + <ac:image>
    - Image tags ➔ Extracted attachments + <ac:image>
    - Page links ➔ <ac:link><ri:page ri:content-title="..."/></ac:link>
    """
    try:
        root = lxml.html.fromstring(html_content)
    except Exception:
        # Fallback if empty
        return f"<p>{html.escape(html_content)}</p>", []

    extracted_attachments = []
    diagram_counter = 0

    # 1. Transform Code Blocks (<div class="highlight"><pre><code> or <pre><code>)
    for pre in root.xpath('//pre'):
        code_el = pre.find('code')
        code_text = (code_el.text_content() if code_el is not None else pre.text_content()) or ''
        
        # Detect language
        classes = (code_el.get('class', '') if code_el is not None else '') + ' ' + pre.get('class', '')
        lang_match = re.search(r'\blanguage-([a-zA-Z0-9_-]+)', classes)
        lang = lang_match.group(1) if lang_match else 'none'

        macro_xml = (
            f'<ac:structured-macro ac:name="code">\n'
            f'  <ac:parameter ac:name="language">{html.escape(lang)}</ac:parameter>\n'
            f'  <ac:parameter ac:name="theme">Confluence</ac:parameter>\n'
            f'  <ac:parameter ac:name="linenumbers">false</ac:parameter>\n'
            f'  <ac:plain-text-body><![CDATA[{code_text.rstrip()}]]></ac:plain-text-body>\n'
            f'</ac:structured-macro>'
        )
        parent = pre.getparent()
        if parent is not None:
            # Replace <pre> or parent highlight div with macro placeholder
            macro_elem = lxml.html.fromstring(f'<div class="__confluence_macro__">{macro_xml}</div>')
            if 'highlight' in parent.get('class', ''):
                grandparent = parent.getparent()
                if grandparent is not None:
                    grandparent.replace(parent, macro_elem)
                else:
                    parent.replace(pre, macro_elem)
            else:
                parent.replace(pre, macro_elem)

    # 2. Transform Admonition Callouts (<div class="admonition ...">)
    for adm in root.xpath('//div[contains(@class, "admonition")]'):
        classes = adm.get('class', '')
        macro_name = "info"
        if 'warning' in classes or 'caution' in classes:
            macro_name = "warning"
        elif 'danger' in classes or 'error' in classes:
            macro_name = "note"
        elif 'tip' in classes or 'success' in classes:
            macro_name = "tip"
        elif 'note' in classes:
            macro_name = "info"

        title_el = adm.find('.//p[@class="admonition-title"]')
        title_text = title_el.text_content().strip() if title_el is not None else ''
        if title_el is not None:
            adm.remove(title_el)

        body_html = "".join(lxml.html.tostring(child, encoding='utf-8').decode('utf-8') for child in adm)
        title_param = f'<ac:parameter ac:name="title">{html.escape(title_text)}</ac:parameter>\n' if title_text else ''

        macro_xml = (
            f'<ac:structured-macro ac:name="{macro_name}">\n'
            f'  {title_param}'
            f'  <ac:rich-text-body>\n'
            f'    {body_html}\n'
            f'  </ac:rich-text-body>\n'
            f'</ac:structured-macro>'
        )
        parent = adm.getparent()
        if parent is not None:
            macro_elem = lxml.html.fromstring(f'<div class="__confluence_macro__">{macro_xml}</div>')
            parent.replace(adm, macro_elem)

    # 3. Transform Expand / Details Blocks (<details><summary>...</summary>...</details>)
    for det in root.xpath('//details'):
        summary_el = det.find('summary')
        title_text = summary_el.text_content().strip() if summary_el is not None else 'Details'
        if summary_el is not None:
            det.remove(summary_el)

        body_html = "".join(lxml.html.tostring(child, encoding='utf-8').decode('utf-8') for child in det)
        macro_xml = (
            f'<ac:structured-macro ac:name="expand">\n'
            f'  <ac:parameter ac:name="title">{html.escape(title_text)}</ac:parameter>\n'
            f'  <ac:rich-text-body>\n'
            f'    {body_html}\n'
            f'  </ac:rich-text-body>\n'
            f'</ac:structured-macro>'
        )
        parent = det.getparent()
        if parent is not None:
            macro_elem = lxml.html.fromstring(f'<div class="__confluence_macro__">{macro_xml}</div>')
            parent.replace(det, macro_elem)

    # 4. Extract and Transform Inline SVGs (<svg>)
    for svg in root.xpath('//svg'):
        diagram_counter += 1
        att_filename = f"diagram_{page_id}_{diagram_counter}.svg"
        svg_content = lxml.html.tostring(svg, encoding='utf-8').decode('utf-8')
        
        extracted_attachments.append({
            'filename': att_filename,
            'content': svg_content.encode('utf-8'),
            'content_type': 'image/svg+xml'
        })

        image_xml = (
            f'<ac:image ac:align="center">\n'
            f'  <ri:attachment ri:filename="{att_filename}"/>\n'
            f'</ac:image>'
        )
        parent = svg.getparent()
        if parent is not None:
            macro_elem = lxml.html.fromstring(f'<div class="__confluence_macro__">{image_xml}</div>')
            parent.replace(svg, macro_elem)

    # 5. Extract and Transform Standalone Images (<img>)
    for img in root.xpath('//img'):
        src = img.get('src', '').strip()
        if src and not src.startswith(('http://', 'https://', 'data:')):
            img_path = os.path.normpath(os.path.join(site_dir, src))
            if os.path.isfile(img_path):
                filename = os.path.basename(img_path)
                with open(img_path, 'rb') as f:
                    data = f.read()

                # Determine content type
                ext = os.path.splitext(filename)[1].lower()
                mime = {
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.gif': 'image/gif',
                    '.svg': 'image/svg+xml',
                    '.webp': 'image/webp',
                }.get(ext, 'application/octet-stream')

                extracted_attachments.append({
                    'filename': filename,
                    'content': data,
                    'content_type': mime
                })

                image_xml = (
                    f'<ac:image>\n'
                    f'  <ri:attachment ri:filename="{html.escape(filename)}"/>\n'
                    f'</ac:image>'
                )
                parent = img.getparent()
                if parent is not None:
                    macro_elem = lxml.html.fromstring(f'<div class="__confluence_macro__">{image_xml}</div>')
                    parent.replace(img, macro_elem)

    # 6. Transform Links (<a>)
    for a in root.xpath('//a'):
        href = a.get('href', '')
        link_text = a.text_content().strip() or href
        
        # Internal link resolution
        if href and not href.startswith(('http://', 'https://', 'mailto:', '#', 'tel:')):
            # Normalize target page path
            clean_href = href.split('#')[0]
            if clean_href in page_title_map:
                target_title = page_title_map[clean_href]
                link_xml = (
                    f'<ac:link>\n'
                    f'  <ri:page ri:content-title="{html.escape(target_title)}"/>\n'
                    f'  <ac:plain-text-link-body><![CDATA[{link_text}]]></ac:plain-text-link-body>\n'
                    f'</ac:link>'
                )
                parent = a.getparent()
                if parent is not None:
                    macro_elem = lxml.html.fromstring(f'<span class="__confluence_macro__">{link_xml}</span>')
                    parent.replace(a, macro_elem)

    # Serialize to XHTML string
    raw_res = lxml.html.tostring(root, encoding='utf-8').decode('utf-8')

    # Unwrap __confluence_macro__ wrappers
    raw_res = re.sub(r'<div class="__confluence_macro__">(.*?)</div>', r'\1', raw_res, flags=re.DOTALL)
    raw_res = re.sub(r'<span class="__confluence_macro__">(.*?)</span>', r'\1', raw_res, flags=re.DOTALL)

    # Restore CDATA blocks converted to comments by lxml.html
    raw_res = re.sub(r'<!--\[CDATA\[(.*?)\]\]-->', r'<![CDATA[\1]]>', raw_res, flags=re.DOTALL)

    cleaned_csf = _clean_csf_xml_string(raw_res)
    return cleaned_csf, extracted_attachments


def export_confluence_package(site_dir, config_file, output_zip_path, space_key=None, space_name=None, package_format="dual", reporter=None):
    """
    Exports the documentation into a complete, import-ready Confluence Package (.zip).
    
    Supported package formats:
    - 'dual' (default): Includes both Space Backup format (entities.xml + exportDescriptor.properties + attachments/)
      and Confluence Storage Format REST Bundle (manifest.json + pages/*.xhtml + attachments/).
    - 'space-backup': Native Confluence Space Backup XML for direct Space Import via UI.
    - 'rest-bundle': Confluence Storage Format XHTML bundle with manifest.json for REST API / CI/CD scripts.
    """
    if reporter:
        reporter.log(f"[CONFLUENCE] Initializing Confluence export package: '{output_zip_path}' (Format: {package_format})...")

    # Read configuration
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    site_name_cfg = config.get('site_name', 'Documentation')
    space_name = space_name or site_name_cfg
    if not space_key:
        # Generate alphanumeric uppercase space key
        clean_key = re.sub(r'[^a-zA-Z0-9]', '', space_name).upper()[:10]
        space_key = clean_key if clean_key else 'DOCS'

    nav = config.get('nav', [])
    pages = flatten_nav(nav)
    if not pages:
        for root, _, files in os.walk(site_dir):
            for f in files:
                if f.endswith('.html') and not f.startswith('.'):
                    rel = os.path.relpath(os.path.join(root, f), site_dir)
                    pages.append(rel)

    # Build page title mapping & hierarchy
    page_records = []
    page_title_map = {}
    base_page_id = 100000
    base_body_id = 200000
    base_att_id = 300000
    total_att_count = 0

    now_dt = datetime.datetime.now()
    now_iso = now_dt.strftime("%Y-%m-%d %H:%M:%S")

    # First pass: map titles
    for idx, page in enumerate(pages, 1):
        html_file = os.path.splitext(page)[0] + '.html'
        html_path = os.path.join(site_dir, html_file)
        if not os.path.exists(html_path):
            dir_index = os.path.join(site_dir, os.path.splitext(page)[0], 'index.html')
            if os.path.exists(dir_index):
                html_path = dir_index

        title = os.path.splitext(os.path.basename(page))[0].replace('_', ' ').replace('-', ' ').title()
        if os.path.exists(html_path):
            with open(html_path, 'r', encoding='utf-8') as f:
                content = f.read()
            title_m = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
            if title_m:
                t = title_m.group(1).split('-')[0].split('–')[0].split('|')[0].strip()
                if t:
                    title = t

        page_title_map[page] = title
        page_title_map[html_file] = title
        page_title_map[f"{os.path.splitext(page)[0]}/"] = title

    # Second pass: convert pages to Confluence Storage Format
    all_attachments = []
    for idx, page in enumerate(pages, 1):
        page_id = base_page_id + idx
        body_id = base_body_id + idx
        html_file = os.path.splitext(page)[0] + '.html'
        html_path = os.path.join(site_dir, html_file)
        if not os.path.exists(html_path):
            dir_index = os.path.join(site_dir, os.path.splitext(page)[0], 'index.html')
            if os.path.exists(dir_index):
                html_path = dir_index

        raw_html = ""
        if os.path.exists(html_path):
            with open(html_path, 'r', encoding='utf-8') as f:
                raw_html = f.read()

        main_html = extract_main_content(raw_html)
        page_dir = os.path.dirname(html_file)
        main_html = adjust_paths(main_html, page_dir)

        title = page_title_map.get(page, f"Page {idx}")
        csf_body, atts = _html_to_confluence_storage_format(main_html, page_id, site_dir, all_attachments, page_title_map, reporter=reporter)

        page_attachments = []
        for att in atts:
            total_att_count += 1
            att_id = base_att_id + total_att_count
            att['id'] = att_id
            att['page_id'] = page_id
            page_attachments.append(att)
            all_attachments.append(att)

        page_records.append({
            'page_id': page_id,
            'body_id': body_id,
            'title': title,
            'page_rel': page,
            'body_csf': csf_body,
            'parent_id': (base_page_id + 1) if idx > 1 else None, # Root page is page 1
            'attachments': page_attachments
        })
        if reporter:
            reporter.log(f"  [CONFLUENCE] Converted page [{idx}/{len(pages)}]: '{title}' ({len(page_attachments)} attachments)")

    # Create ZIP bundle
    os.makedirs(os.path.dirname(os.path.abspath(output_zip_path)), exist_ok=True)

    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # ==================== FORMAT: REST BUNDLE ====================
        if package_format in ('dual', 'rest-bundle'):
            manifest = {
                "spaceKey": space_key,
                "spaceName": space_name,
                "version": "1.0.0",
                "generatedAt": now_iso,
                "totalPages": len(page_records),
                "totalAttachments": len(all_attachments),
                "pages": [
                    {
                        "id": p['page_id'],
                        "title": p['title'],
                        "file": f"pages/{p['page_id']}.xhtml",
                        "parent": p['parent_id'],
                        "attachments": [a['filename'] for a in p['attachments']]
                    }
                    for p in page_records
                ]
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

            for p in page_records:
                xhtml_doc = (
                    f'<?xml version="1.0" encoding="UTF-8"?>\n'
                    f'<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n'
                    f'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:ac="http://www.atlassian.com/schema/confluence/4/ac/" xmlns:ri="http://www.atlassian.com/schema/confluence/4/ri/">\n'
                    f'<head><title>{html.escape(p["title"])}</title></head>\n'
                    f'<body>\n{p["body_csf"]}\n</body>\n</html>'
                )
                zf.writestr(f"pages/{p['page_id']}.xhtml", xhtml_doc)

            for att in all_attachments:
                zf.writestr(f"attachments/{att['filename']}", att['content'])

        # ==================== FORMAT: SPACE BACKUP ====================
        if package_format in ('dual', 'space-backup'):
            # 1. exportDescriptor.properties
            desc_props = (
                f"exportType=space\n"
                f"spaceKey={space_key}\n"
                f"spaceName={space_name}\n"
                f"buildNumber=9000\n"
                f"confluence.version=9.0.0\n"
                f"createdDate={now_iso}\n"
            )
            zf.writestr("exportDescriptor.properties", desc_props)

            # 2. entities.xml
            xml_lines = []
            xml_lines.append('<?xml version="1.0" encoding="UTF-8"?>')
            xml_lines.append(f'<hibernate-generic datetime="{now_iso}">')
            
            def _cdata(val):
                return f"<![CDATA[{str(val).replace(']]>', ']]]]><![CDATA[>')}]]>"

            # Space object
            xml_lines.append(f'  <object class="Space" package="com.atlassian.confluence.spaces">')
            xml_lines.append(f'    <id name="id">1</id>')
            xml_lines.append(f'    <property name="key">{_cdata(space_key)}</property>')
            xml_lines.append(f'    <property name="name">{_cdata(space_name)}</property>')
            xml_lines.append(f'    <property name="description">{_cdata("Auto-generated Space by MkDocs Kit")}</property>')
            xml_lines.append(f'  </object>')

            # BodyContent & Page objects
            for p in page_records:
                # BodyContent
                xml_lines.append(f'  <object class="BodyContent" package="com.atlassian.confluence.core">')
                xml_lines.append(f'    <id name="id">{p["body_id"]}</id>')
                xml_lines.append(f'    <property name="body">{_cdata(p["body_csf"])}</property>')
                xml_lines.append(f'    <property name="bodyType">2</property>') # 2 = Confluence Storage XHTML
                xml_lines.append(f'  </object>')

                # Page
                xml_lines.append(f'  <object class="Page" package="com.atlassian.confluence.pages">')
                xml_lines.append(f'    <id name="id">{p["page_id"]}</id>')
                xml_lines.append(f'    <property name="title">{_cdata(p["title"])}</property>')
                xml_lines.append(f'    <property name="space" class="Space"><id name="id">1</id></property>')
                xml_lines.append(f'    <property name="creationDate">{now_iso}</property>')
                xml_lines.append(f'    <property name="lastModificationDate">{now_iso}</property>')
                xml_lines.append(f'    <property name="version">1</property>')
                if p['parent_id']:
                    xml_lines.append(f'    <property name="parent" class="Page"><id name="id">{p["parent_id"]}</id></property>')

                # BodyContents collection
                xml_lines.append(f'    <collection name="bodyContents">')
                xml_lines.append(f'      <element class="BodyContent"><id name="id">{p["body_id"]}</id></element>')
                xml_lines.append(f'    </collection>')

                # Attachments collection
                if p['attachments']:
                    xml_lines.append(f'    <collection name="attachments">')
                    for att in p['attachments']:
                        xml_lines.append(f'      <element class="Attachment"><id name="id">{att["id"]}</id></element>')
                    xml_lines.append(f'    </collection>')

                xml_lines.append(f'  </object>')

                # Attachment entities
                for att in p['attachments']:
                    xml_lines.append(f'  <object class="Attachment" package="com.atlassian.confluence.pages">')
                    xml_lines.append(f'    <id name="id">{att["id"]}</id>')
                    xml_lines.append(f'    <property name="title">{_cdata(att["filename"])}</property>')
                    xml_lines.append(f'    <property name="fileName">{_cdata(att["filename"])}</property>')
                    xml_lines.append(f'    <property name="fileSize">{len(att["content"])}</property>')
                    xml_lines.append(f'    <property name="contentType">{_cdata(att["content_type"])}</property>')
                    xml_lines.append(f'    <property name="version">1</property>')
                    xml_lines.append(f'    <property name="container" class="Page"><id name="id">{p["page_id"]}</id></property>')
                    xml_lines.append(f'  </object>')

                    # Store attachment binary in space-backup location: attachments/{page_id}/{att_id}/1
                    zf.writestr(f"attachments/{p['page_id']}/{att['id']}/1", att['content'])

            xml_lines.append('</hibernate-generic>')
            zf.writestr("entities.xml", "\n".join(xml_lines))

    file_size_kb = os.path.getsize(output_zip_path) / 1024.0
    if reporter:
        reporter.log(f"[CONFLUENCE] Successfully packaged Confluence Space archive: '{output_zip_path}' ({len(page_records)} pages, {len(all_attachments)} attachments, {file_size_kb:.1f} KB).")

    return output_zip_path
