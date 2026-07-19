import os
import re
from mkdocs.plugins import BasePlugin
from mkdocs_kit.renderers import (
    render_plantuml, render_wireviz, render_rackdiag, render_packetdiag,
    render_bytefield, render_blockdiag, render_nwdiag
)
from mkdocs_kit.csv_renderer import render_csv
from mkdocs_kit.plotly_renderer import render_plotly
from mkdocs_kit.d3_renderer import render_d3

class DiagramsPlugin(BasePlugin):
    def on_page_markdown(self, markdown, page, config, files):
        pattern = r'```(plantuml|wireviz|rackdiag|packetdiag|bytefield|blockdiag|nwdiag|csv|plotly|d3)\n(.*?)\n```'
        
        page_dir = os.path.dirname(page.file.abs_src_path) if page and hasattr(page, 'file') and page.file else "."

        def replace_block(match):
            diag_type = match.group(1)
            content = match.group(2)
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
                    return render_csv(content, page_dir=page_dir)
                elif diag_type == 'plotly':
                    return render_plotly(content, page_dir=page_dir)
                elif diag_type == 'd3':
                    return render_d3(content, page_dir=page_dir)
                else:
                    return match.group(0)
                
                svg_clean = svg.strip()
                if svg_clean.startswith('<?xml'):
                    svg_clean = svg_clean[svg_clean.find('?>')+2:].strip()
                
                return f'<div class="diagram-{diag_type}">{svg_clean}</div>'
            except Exception as e:
                return f'<div class="diagram-error" style="color: #ff3333; border: 1px solid #ff3333; padding: 10px; margin: 10px 0; background-color: #ffe6e6; border-radius: 4px; font-family: monospace;"><strong>Error rendering {diag_type}:</strong><pre style="margin: 5px 0 0 0; white-space: pre-wrap;">{str(e)}</pre></div>'

        return re.sub(pattern, replace_block, markdown, flags=re.DOTALL)

