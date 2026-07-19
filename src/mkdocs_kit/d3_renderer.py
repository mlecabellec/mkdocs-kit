import json
import os
import re
import textwrap
import yaml

def parse_d3_spec(src, page_dir="."):
    """
    Parses D3 chart specification from JSON, YAML or external file reference.
    Robustly handles loose list items (e.g., `- label: "API", value: 90`).
    """
    src_stripped = textwrap.dedent(src).strip()
    
    if src_stripped.startswith('file:'):
        file_path = src_stripped.split('file:', 1)[1].strip().strip('"\'')
        target_path = os.path.normpath(os.path.join(page_dir, file_path))
        if os.path.exists(target_path):
            with open(target_path, 'r', encoding='utf-8') as f:
                src_stripped = f.read().strip()
        else:
            raise FileNotFoundError(f"D3 file not found: {file_path}")
            
    # Normalize loose key-value pairs inside list items: "- label: X, value: Y" -> "- {label: X, value: Y}"
    normalized_lines = []
    for line in src_stripped.splitlines():
        match = re.match(r'^\s*-\s+([a-zA-Z0-9_]+:\s*[^,]+,\s*[a-zA-Z0-9_]+:.*)$', line)
        if match:
            indent = line[:line.find('-')]
            kv_pairs = match.group(1)
            normalized_lines.append(f"{indent}- {{{kv_pairs}}}")
        else:
            normalized_lines.append(line)
            
    normalized_src = "\n".join(normalized_lines)
    
    try:
        data = json.loads(normalized_src)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
        
    try:
        data = yaml.safe_load(normalized_src)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
        
    raise ValueError("Invalid D3 chart specification. Must be JSON or YAML dictionary.")

def render_d3_svg_static(spec):
    """
    Build-time static vector SVG generator for D3 declarative charts.
    Guarantees crisp SVG pre-rendering for WeasyPrint PDF compilation.
    """
    chart_type = spec.get('type', 'bar')
    data = spec.get('data', [])
    options = spec.get('options', {})
    
    width = int(options.get('width', 600))
    height = int(options.get('height', 350))
    title = options.get('title', '')
    color = options.get('color', '#9b59b6')
    
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" style="background-color: #ffffff; font-family: system-ui, sans-serif;">']
    
    if title:
        svg.append(f'<text x="{width/2}" y="30" text-anchor="middle" font-size="16" font-weight="bold" fill="#333333">{title}</text>')
        
    margin_top = 50 if title else 30
    margin_bottom = 50
    margin_left = 60
    margin_right = 30
    
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    
    if chart_type in ('bar', 'column', 'line') and data:
        labels = [str(item.get('label', item.get('x', ''))) for item in data]
        values = [float(item.get('value', item.get('y', 0))) for item in data]
        max_v = max(values) if values else 1.0
        if max_v == 0: max_v = 1.0
        
        n = len(data)
        step = plot_w / max(n, 1)
        
        # Axes
        svg.append(f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_h}" stroke="#ccc" stroke-width="1"/>')
        svg.append(f'<line x1="{margin_left}" y1="{margin_top + plot_h}" x2="{margin_left + plot_w}" y2="{margin_top + plot_h}" stroke="#ccc" stroke-width="1"/>')
        
        for i in range(n):
            cx = margin_left + (i + 0.5) * step
            val = values[i]
            bh = (val / max_v) * plot_h
            by = margin_top + plot_h - bh
            
            # Label
            svg.append(f'<text x="{cx}" y="{margin_top + plot_h + 18}" text-anchor="middle" font-size="11" fill="#555">{labels[i]}</text>')
            
            if chart_type in ('bar', 'column'):
                bw = step * 0.6
                bx = cx - bw / 2
                svg.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="{color}" rx="3"/>')
                svg.append(f'<text x="{cx}" y="{by - 6}" text-anchor="middle" font-size="10" font-weight="bold" fill="#333">{val:g}</text>')
                
    svg.append('</svg>')
    return "".join(svg)

def render_d3(src, page_dir="."):
    """
    Main renderer for D3 chart codeblocks.
    Returns unindented HTML container with client D3.js v7 loader and SVG static fallback.
    """
    spec = parse_d3_spec(src, page_dir)
    d3_id = f"d3-chart-{abs(hash(src)) % 1000000}"
    
    spec_json = json.dumps(spec)
    svg_static = render_d3_svg_static(spec)
    
    raw_html = f'''<div class="mkdocs-kit-d3-wrapper" id="{d3_id}">
<div class="mkdocs-kit-d3-container" style="width: 100%; min-height: 350px;">{svg_static}</div>
<script>
(function() {{
const container = document.getElementById("{d3_id}").querySelector(".mkdocs-kit-d3-container");
const spec = {spec_json};
if (typeof d3 !== "undefined") {{
// Interactivity hook
}} else if (!window.d3ScriptLoading) {{
window.d3ScriptLoading = true;
const script = document.createElement("script");
script.src = "https://cdn.jsdelivr.net/npm/d3@7";
document.head.appendChild(script);
}}
}})();
</script>
</div>'''
    lines = [line.strip() for line in raw_html.splitlines() if line.strip()]
    return "\n".join(lines)
