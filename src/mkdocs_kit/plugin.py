import os
import re
import time
from mkdocs.plugins import BasePlugin
from mkdocs_kit.renderers import (
    render_plantuml, render_wireviz, render_rackdiag, render_packetdiag,
    render_bytefield, render_blockdiag, render_nwdiag
)
from mkdocs_kit.csv_renderer import render_csv
from mkdocs_kit.plotly_renderer import render_plotly
from mkdocs_kit.d3_renderer import render_d3
from mkdocs_kit.link_checker import check_links_in_markdown

class DiagramsPlugin(BasePlugin):
    def __init__(self, reporter=None):
        super().__init__()
        self.reporter = reporter

    def on_page_markdown(self, markdown, page, config, files):
        start_time = time.time()
        reporter = self.reporter or config.get('reporter')
        
        page_src_path = page.file.abs_src_path if page and hasattr(page, 'file') and page.file else "unknown.md"
        docs_dir = config.get('docs_dir', 'docs')
        page_rel = os.path.relpath(page_src_path, docs_dir) if docs_dir and os.path.isabs(page_src_path) else page_src_path

        if reporter:
            reporter.log(f"Processing Markdown page: '{page_rel}'")

        # 1. Link Check & Directory Target Detection
        has_link_dir_warning = check_links_in_markdown(markdown, page_src_path, docs_dir, reporter)

        page_warnings = []
        page_errors = []
        if has_link_dir_warning:
            page_warnings.append("Link points to directory listing instead of target file")

        pattern = r'```(plantuml|wireviz|rackdiag|packetdiag|bytefield|blockdiag|nwdiag|csv|plotly|d3)\n(.*?)\n```'
        page_dir = os.path.dirname(page_src_path)

        def replace_block(match):
            diag_type = match.group(1)
            content = match.group(2)
            diag_start = time.time()
            try:
                if diag_type == 'plantuml':
                    svg = render_plantuml(content)
                elif diag_type == 'wireviz':
                    svg = render_wireviz(content)
                elif diag_type == 'rackdiag':
                    svg = render_rackdiag(content)
                elif diag_type == 'packetdiag':
                    svg = render_packetdiag(content)
                elif diag_type == 'bytefield':
                    svg = render_bytefield(content)
                elif diag_type == 'blockdiag':
                    svg = render_blockdiag(content)
                elif diag_type == 'nwdiag':
                    svg = render_nwdiag(content)
                elif diag_type == 'csv':
                    html_res = render_csv(content, page_dir=page_dir)
                    diag_duration = time.time() - diag_start
                    if reporter:
                        reporter.record_diagram(diag_type, page_rel, "SUCCESS", "Rendered interactive CSV table", diag_duration)
                    return "\n".join(line.strip() for line in html_res.splitlines() if line.strip())
                elif diag_type == 'plotly':
                    html_res = render_plotly(content, page_dir=page_dir)
                    diag_duration = time.time() - diag_start
                    if reporter:
                        reporter.record_diagram(diag_type, page_rel, "SUCCESS", "Rendered Plotly chart", diag_duration)
                    return "\n".join(line.strip() for line in html_res.splitlines() if line.strip())
                elif diag_type == 'd3':
                    html_res = render_d3(content, page_dir=page_dir)
                    diag_duration = time.time() - diag_start
                    if reporter:
                        reporter.record_diagram(diag_type, page_rel, "SUCCESS", "Rendered D3.js chart", diag_duration)
                    return "\n".join(line.strip() for line in html_res.splitlines() if line.strip())
                else:
                    return match.group(0)

                diag_duration = time.time() - diag_start
                if reporter:
                    reporter.record_diagram(diag_type, page_rel, "SUCCESS", f"Rendered SVG ({len(svg)} bytes)", diag_duration)

                svg_clean = svg.strip()
                if svg_clean.startswith('<?xml'):
                    svg_clean = svg_clean[svg_clean.find('?>')+2:].strip()
                
                return f'<div class="diagram-{diag_type}">{svg_clean}</div>'
            except Exception as e:
                diag_duration = time.time() - diag_start
                err_msg = str(e)
                if reporter:
                    reporter.error(f"Page '{page_rel}': Diagram '{diag_type}' rendering failed: {err_msg}", category="DIAGRAM")
                    reporter.record_diagram(diag_type, page_rel, "ERROR", err_msg, diag_duration)
                page_errors.append(f"Diagram '{diag_type}' error: {err_msg}")
                return f'<div class="diagram-error" style="color: #ff3333; border: 1px solid #ff3333; padding: 10px; margin: 10px 0; background-color: #ffe6e6; border-radius: 4px; font-family: monospace;"><strong>Error rendering {diag_type}:</strong><pre style="margin: 5px 0 0 0; white-space: pre-wrap;">{str(e)}</pre></div>'

        processed_markdown = re.sub(pattern, replace_block, markdown, flags=re.DOTALL)
        
        duration = time.time() - start_time
        status = "SUCCESS"
        if page_errors:
            status = "ERROR"
        elif page_warnings:
            status = "WARNING"

        if reporter:
            reporter.record_page(page_rel, status, page_warnings, page_errors, duration)

        return processed_markdown
