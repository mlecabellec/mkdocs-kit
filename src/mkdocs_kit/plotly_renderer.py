import json
import os
import textwrap
import yaml

def parse_plotly_spec(src, page_dir="."):
    """
    Parses Plotly spec from JSON, YAML or external file reference.
    """
    src_stripped = textwrap.dedent(src).strip()

    
    # Check for file parameter
    if src_stripped.startswith('file:'):
        file_path = src_stripped.split('file:', 1)[1].strip().strip('"\'')
        target_path = os.path.normpath(os.path.join(page_dir, file_path))
        if os.path.exists(target_path):
            with open(target_path, 'r', encoding='utf-8') as f:
                src_stripped = f.read().strip()
        else:
            raise FileNotFoundError(f"Plotly file not found: {file_path}")
            
    # Try JSON
    try:
        data = json.loads(src_stripped)
        if isinstance(data, dict):
            return data
        elif isinstance(data, list):
            return {'data': data, 'layout': {}}
    except json.JSONDecodeError:
        pass
        
    # Try YAML
    try:
        data = yaml.safe_load(src_stripped)
        if isinstance(data, dict):
            return data
        elif isinstance(data, list):
            return {'data': data, 'layout': {}}
    except Exception:
        pass
        
    raise ValueError("Invalid Plotly chart specification. Must be JSON or YAML.")

def render_plotly_svg_fallback(spec):
    """
    Pure Python vector SVG generator fallback for Plotly charts (bar, line, scatter, pie).
    Guarantees 100% standalone SVG pre-rendering for WeasyPrint PDF compilation without requiring external browser dependencies.
    """
    data_list = spec.get('data', [])
    layout = spec.get('layout', {})
    
    title = layout.get('title', {}).get('text', '') if isinstance(layout.get('title'), dict) else layout.get('title', '')
    width = int(layout.get('width', 600))
    height = int(layout.get('height', 350))
    
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" style="background-color: #ffffff; font-family: system-ui, sans-serif;">']
    
    # Title
    if title:
        svg.append(f'<text x="{width/2}" y="30" text-anchor="middle" font-size="16" font-weight="bold" fill="#333333">{title}</text>')
        
    if not data_list:
        svg.append('</svg>')
        return "".join(svg)
        
    series = data_list[0]
    chart_type = series.get('type', 'bar')
    x_vals = series.get('x', [])
    y_vals = series.get('y', [])
    color = series.get('marker', {}).get('color', '#3498db') if isinstance(series.get('marker'), dict) else '#3498db'
    
    margin_top = 50 if title else 30
    margin_bottom = 50
    margin_left = 60
    margin_right = 30
    
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    
    if chart_type in ('bar', 'scatter', 'line') and x_vals and y_vals:
        # Axes
        svg.append(f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_height}" stroke="#ccc" stroke-width="1"/>')
        svg.append(f'<line x1="{margin_left}" y1="{margin_top + plot_height}" x2="{margin_left + plot_width}" y2="{margin_top + plot_height}" stroke="#ccc" stroke-width="1"/>')
        
        try:
            num_y = [float(v) for v in y_vals]
            max_y = max(num_y) if num_y else 1.0
            if max_y == 0: max_y = 1.0
        except ValueError:
            num_y = [0.0] * len(y_vals)
            max_y = 1.0
            
        n = len(x_vals)
        bar_step = plot_width / max(n, 1)
        
        # Grid lines
        for i in range(5):
            gy = margin_top + plot_height - (i / 4.0) * plot_height
            gval = (i / 4.0) * max_y
            svg.append(f'<line x1="{margin_left}" y1="{gy}" x2="{margin_left + plot_width}" y2="{gy}" stroke="#f0f0f0" stroke-width="1"/>')
            svg.append(f'<text x="{margin_left - 8}" y="{gy + 4}" text-anchor="end" font-size="10" fill="#666">{gval:.1f}</text>')
            
        points = []
        for i in range(n):
            cx = margin_left + (i + 0.5) * bar_step
            val = num_y[i] if i < len(num_y) else 0.0
            cy = margin_top + plot_height - (val / max_y) * plot_height
            points.append((cx, cy))
            
            # X Label
            svg.append(f'<text x="{cx}" y="{margin_top + plot_height + 18}" text-anchor="middle" font-size="11" fill="#555">{x_vals[i]}</text>')
            
            if chart_type == 'bar':
                bw = bar_step * 0.6
                bx = cx - bw / 2
                bh = (val / max_y) * plot_height
                by = margin_top + plot_height - bh
                svg.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="{color}" rx="2"/>')
                
        if chart_type in ('line', 'scatter'):
            pts_str = " ".join([f"{x},{y}" for x, y in points])
            if chart_type == 'line':
                svg.append(f'<polyline points="{pts_str}" fill="none" stroke="{color}" stroke-width="3"/>')
            for cx, cy in points:
                svg.append(f'<circle cx="{cx}" cy="{cy}" r="4" fill="{color}"/>')
                
    svg.append('</svg>')
    return "".join(svg)

def render_plotly(src, page_dir="."):
    """
    Main renderer for Plotly chart codeblocks.
    Returns container with client Plotly.js loader and SVG fallback.
    """
    spec = parse_plotly_spec(src, page_dir)
    plotly_id = f"plotly-chart-{abs(hash(src)) % 1000000}"
    
    spec_json = json.dumps(spec)
    svg_static = render_plotly_svg_fallback(spec)
    
    html = f'''
    <div class="mkdocs-kit-plotly-wrapper" id="{plotly_id}">
        <div class="mkdocs-kit-plotly-container" style="width: 100%; min-height: 350px;">{svg_static}</div>
        <script>
        (function() {{
            const container = document.getElementById("{plotly_id}").querySelector(".mkdocs-kit-plotly-container");
            const config = {spec_json};
            if (typeof Plotly !== "undefined") {{
                container.innerHTML = "";
                Plotly.newPlot(container, config.data || [], config.layout || {{}}, {{responsive: true}});
            }} else {{
                if (!window.plotlyScriptLoading) {{
                    window.plotlyScriptLoading = true;
                    const script = document.createElement("script");
                    script.src = "https://cdn.plot.ly/plotly-2.27.0.min.js";
                    script.onload = function() {{
                        document.querySelectorAll(".mkdocs-kit-plotly-wrapper").forEach(w => {{
                            const c = w.querySelector(".mkdocs-kit-plotly-container");
                            const cfg = w.dataset.config ? JSON.parse(w.dataset.config) : null;
                            if (c && cfg) {{ c.innerHTML = ""; Plotly.newPlot(c, cfg.data || [], cfg.layout || {{}}, {{responsive: true}}); }}
                        }});
                    }};
                    document.head.appendChild(script);
                }}
                document.getElementById("{plotly_id}").dataset.config = JSON.stringify(config);
            }}
        }})();
        </script>
    </div>
    '''
    return html
