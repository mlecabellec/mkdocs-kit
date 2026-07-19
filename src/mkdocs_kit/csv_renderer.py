import csv
import io
import os
import re

def parse_csv_spec(src, page_dir="."):
    """
    Parses CSV codeblock content. Supports options:
    file: relative/path/to/file.csv
    page_size: 10
    sort: "ColumnName asc/desc"
    filter: "ColumnName >= 30"
    delimiter: ","
    search: true
    caption: Table Caption
    Or raw inline CSV content.
    """
    lines = src.strip().splitlines()
    spec = {
        'file': None,
        'page_size': 10,
        'sort': None,
        'filter': None,
        'delimiter': ',',
        'search': True,
        'caption': None,
        'inline_data': []
    }
    
    config_lines = []
    data_lines = []
    in_config = True
    
    for line in lines:
        stripped = line.strip()
        if in_config and (':' in stripped and not stripped.startswith('"') and not stripped.startswith("'")):
            key, val = stripped.split(':', 1)
            key = key.strip().lower()
            val = val.strip().strip('"\'')
            if key == 'file':
                spec['file'] = val
            elif key == 'page_size':
                try:
                    spec['page_size'] = int(val)
                except ValueError:
                    spec['page_size'] = 10
            elif key == 'sort':
                spec['sort'] = val
            elif key == 'filter':
                spec['filter'] = val
            elif key == 'delimiter':
                spec['delimiter'] = val if val else ','
            elif key == 'search':
                spec['search'] = val.lower() in ('true', '1', 'yes')
            elif key == 'caption':
                spec['caption'] = val
            else:
                data_lines.append(line)
                in_config = False
        else:
            in_config = False
            data_lines.append(line)
            
    csv_text = ""
    if spec['file']:
        target_path = os.path.normpath(os.path.join(page_dir, spec['file']))
        if os.path.exists(target_path):
            with open(target_path, 'r', encoding='utf-8', errors='replace') as f:
                csv_text = f.read()
        else:
            raise FileNotFoundError(f"CSV file not found: {spec['file']} (resolved: {target_path})")
    else:
        csv_text = "\n".join(data_lines)
        
    if not csv_text.strip():
        return [], [], spec
        
    reader = csv.reader(io.StringIO(csv_text.strip()), delimiter=spec['delimiter'])
    rows = list(reader)
    if not rows:
        return [], [], spec
        
    headers = rows[0]
    data = rows[1:]
    return headers, data, spec

def apply_filter(headers, data, filter_expr):
    """
    Applies build-time filtering to data rows.
    Supports syntax: "ColName >= 30", "ColName == 'Engineering'", "ColName contains 'Tech'"
    """
    if not filter_expr or not headers:
        return data
        
    match = re.match(r'^(.+?)\s*(>=|<=|>|<|==|!=|=~|contains)\s*(.+)$', filter_expr.strip())
    if not match:
        return data
        
    col_name, op, target_val = match.groups()
    col_name = col_name.strip().strip('"\'')
    target_val = target_val.strip().strip('"\'')
    
    col_idx = -1
    for i, h in enumerate(headers):
        if h.strip().lower() == col_name.lower():
            col_idx = i
            break
            
    if col_idx == -1:
        return data
        
    filtered = []
    for row in data:
        if col_idx >= len(row):
            continue
        val = row[col_idx].strip()
        
        # Try numeric comparison
        try:
            num_val = float(val.replace('$', '').replace(',', ''))
            num_target = float(target_val.replace('$', '').replace(',', ''))
            
            if op == '>' and num_val > num_target: filtered.append(row)
            elif op == '>=' and num_val >= num_target: filtered.append(row)
            elif op == '<' and num_val < num_target: filtered.append(row)
            elif op == '<=' and num_val <= num_target: filtered.append(row)
            elif op in ('==', '=') and num_val == num_target: filtered.append(row)
            elif op == '!=' and num_val != num_target: filtered.append(row)
            continue
        except ValueError:
            pass
            
        # String comparison
        val_lower = val.lower()
        target_lower = target_val.lower()
        
        if op in ('==', '=') and val_lower == target_lower: filtered.append(row)
        elif op == '!=' and val_lower != target_lower: filtered.append(row)
        elif op in ('contains', '=~') and target_lower in val_lower: filtered.append(row)
        
    return filtered

def apply_sort(headers, data, sort_expr):
    """
    Applies build-time sorting to data rows.
    Syntax: "ColName asc" or "ColName desc"
    """
    if not sort_expr or not headers or not data:
        return data
        
    parts = sort_expr.strip().split()
    col_name = parts[0].strip('"\'')
    reverse = len(parts) > 1 and parts[1].lower() == 'desc'
    
    col_idx = -1
    for i, h in enumerate(headers):
        if h.strip().lower() == col_name.lower():
            col_idx = i
            break
            
    if col_idx == -1:
        return data
        
    def get_sort_key(row):
        if col_idx >= len(row):
            return ""
        val = row[col_idx].strip()
        try:
            return (0, float(val.replace('$', '').replace(',', '')))
        except ValueError:
            return (1, val.lower())
            
    return sorted(data, key=get_sort_key, reverse=reverse)

def render_csv(src, page_dir="."):
    """
    Main entrypoint for rendering CSV markdown blocks.
    Returns clean HTML with embedded interactive client-side sorting & pagination scripts.
    """
    headers, data, spec = parse_csv_spec(src, page_dir)
    
    # Apply build-time filter and sort (for PDF & initial HTML view)
    if spec['filter']:
        data = apply_filter(headers, data, spec['filter'])
    if spec['sort']:
        data = apply_sort(headers, data, spec['sort'])
        
    table_id = f"csv-table-{abs(hash(src)) % 1000000}"
    
    html_buf = []
    html_buf.append(f'<div class="mkdocs-kit-csv-wrapper" id="{table_id}" data-page-size="{spec["page-size"] if "page-size" in spec else spec["page_size"]}">')
    
    if spec['caption']:
        html_buf.append(f'<div class="csv-caption"><strong>{spec["caption"]}</strong></div>')
        
    # Controls bar (Search input & Info)
    if spec['search']:
        html_buf.append('''
        <div class="mkdocs-kit-csv-controls">
            <input type="text" class="csv-search-input" placeholder="🔍 Search table..." onkeyup="mkdocsKitCsvSearch(this)">
            <span class="csv-info-span"></span>
        </div>
        ''')
        
    html_buf.append('<div class="csv-table-responsive"><table class="mkdocs-kit-csv-table">')
    
    # Header row with sortable column triggers
    html_buf.append('<thead><tr>')
    for idx, h in enumerate(headers):
        html_buf.append(f'<th data-col="{idx}" onclick="mkdocsKitCsvSort(this)">{h} <span class="sort-icon">↕</span></th>')
    html_buf.append('</tr></thead>')
    
    # Table body
    html_buf.append('<tbody>')
    for row in data:
        html_buf.append('<tr>')
        for cell in row:
            html_buf.append(f'<td>{cell}</td>')
        html_buf.append('</tr>')
    html_buf.append('</tbody></table></div>')
    
    # Pagination controls
    html_buf.append('''
    <div class="mkdocs-kit-csv-pagination">
        <button class="csv-btn csv-prev" onclick="mkdocsKitCsvPage(this, -1)">Previous</button>
        <span class="csv-page-num">Page 1</span>
        <button class="csv-btn csv-next" onclick="mkdocsKitCsvPage(this, 1)">Next</button>
    </div>
    ''')
    
    # Client-side Interactive Script & CSS
    html_buf.append('''
    <style>
    .mkdocs-kit-csv-wrapper { margin: 20px 0; font-family: system-ui, -apple-system, sans-serif; }
    .csv-caption { font-size: 1.1em; margin-bottom: 8px; color: #2c3e50; }
    .mkdocs-kit-csv-controls { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .csv-search-input { padding: 6px 12px; border: 1px solid #ccc; border-radius: 4px; font-size: 0.9em; width: 220px; }
    .csv-info-span { font-size: 0.85em; color: #666; }
    .csv-table-responsive { overflow-x: auto; margin-bottom: 8px; }
    table.mkdocs-kit-csv-table { width: 100%; border-collapse: collapse; font-size: 0.9em; }
    table.mkdocs-kit-csv-table th { background-color: #f8f9fa; color: #333; text-align: left; padding: 10px; border: 1px solid #dee2e6; cursor: pointer; user-select: none; }
    table.mkdocs-kit-csv-table th:hover { background-color: #e9ecef; }
    table.mkdocs-kit-csv-table td { padding: 8px 10px; border: 1px solid #dee2e6; color: #495057; }
    table.mkdocs-kit-csv-table tr:nth-child(even) td { background-color: #f8f9fa; }
    .sort-icon { font-size: 0.8em; color: #999; margin-left: 4px; }
    .mkdocs-kit-csv-pagination { display: flex; align-items: center; justify-content: flex-end; gap: 10px; margin-top: 6px; }
    .csv-btn { padding: 4px 12px; border: 1px solid #0066cc; background: #0066cc; color: white; border-radius: 4px; cursor: pointer; font-size: 0.85em; }
    .csv-btn:disabled { background: #ccc; border-color: #ccc; cursor: not-allowed; }
    .csv-page-num { font-size: 0.85em; color: #555; }
    @media print {
        .mkdocs-kit-csv-controls, .mkdocs-kit-csv-pagination { display: none !important; }
        table.mkdocs-kit-csv-table thead { display: table-header-group !important; }
        table.mkdocs-kit-csv-table tr { page-break-inside: avoid !important; }
    }
    </style>
    <script>
    if (typeof window.mkdocsKitCsvInit !== 'function') {
        window.mkdocsKitCsvInit = function(wrapper) {
            const pageSize = parseInt(wrapper.getAttribute('data-page-size')) || 10;
            wrapper.dataset.currentPage = 1;
            wrapper.dataset.pageSize = pageSize;
            window.mkdocsKitCsvRender(wrapper);
        };
        window.mkdocsKitCsvRender = function(wrapper) {
            const table = wrapper.querySelector('table.mkdocs-kit-csv-table');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const searchInput = wrapper.querySelector('.csv-search-input');
            const query = searchInput ? searchInput.value.toLowerCase().trim() : '';
            
            let visibleRows = rows.filter(row => {
                if (!query) return true;
                return row.textContent.toLowerCase().includes(query);
            });
            
            rows.forEach(r => r.style.display = 'none');
            
            const pageSize = parseInt(wrapper.dataset.pageSize) || 10;
            const totalPages = Math.max(1, Math.ceil(visibleRows.length / pageSize));
            let currentPage = parseInt(wrapper.dataset.currentPage) || 1;
            if (currentPage > totalPages) currentPage = totalPages;
            if (currentPage < 1) currentPage = 1;
            wrapper.dataset.currentPage = currentPage;
            
            const start = (currentPage - 1) * pageSize;
            const end = start + pageSize;
            visibleRows.slice(start, end).forEach(r => r.style.display = '');
            
            const pageNumSpan = wrapper.querySelector('.csv-page-num');
            if (pageNumSpan) pageNumSpan.textContent = 'Page ' + currentPage + ' of ' + totalPages;
            
            const prevBtn = wrapper.querySelector('.csv-prev');
            const nextBtn = wrapper.querySelector('.csv-next');
            if (prevBtn) prevBtn.disabled = (currentPage <= 1);
            if (nextBtn) nextBtn.disabled = (currentPage >= totalPages);
            
            const infoSpan = wrapper.querySelector('.csv-info-span');
            if (infoSpan) infoSpan.textContent = 'Showing ' + (visibleRows.length ? start + 1 : 0) + '-' + Math.min(end, visibleRows.length) + ' of ' + visibleRows.length + ' entries';
        };
        window.mkdocsKitCsvSearch = function(input) {
            const wrapper = input.closest('.mkdocs-kit-csv-wrapper');
            wrapper.dataset.currentPage = 1;
            window.mkdocsKitCsvRender(wrapper);
        };
        window.mkdocsKitCsvPage = function(btn, dir) {
            const wrapper = btn.closest('.mkdocs-kit-csv-wrapper');
            let currentPage = parseInt(wrapper.dataset.currentPage) || 1;
            wrapper.dataset.currentPage = currentPage + dir;
            window.mkdocsKitCsvRender(wrapper);
        };
        window.mkdocsKitCsvSort = function(th) {
            const wrapper = th.closest('.mkdocs-kit-csv-wrapper');
            const table = wrapper.querySelector('table');
            const tbody = table.querySelector('tbody');
            const colIdx = parseInt(th.getAttribute('data-col'));
            const currentDir = th.getAttribute('data-sort-dir') === 'asc' ? 'desc' : 'asc';
            
            table.querySelectorAll('th').forEach(h => {
                h.removeAttribute('data-sort-dir');
                const icon = h.querySelector('.sort-icon');
                if (icon) icon.textContent = '↕';
            });
            
            th.setAttribute('data-sort-dir', currentDir);
            const icon = th.querySelector('.sort-icon');
            if (icon) icon.textContent = currentDir === 'asc' ? '▲' : '▼';
            
            const rows = Array.from(tbody.querySelectorAll('tr'));
            rows.sort((a, b) => {
                const valA = a.children[colIdx] ? a.children[colIdx].textContent.trim() : '';
                const valB = b.children[colIdx] ? b.children[colIdx].textContent.trim() : '';
                const numA = parseFloat(valA.replace(/[$,]/g, ''));
                const numB = parseFloat(valB.replace(/[$,]/g, ''));
                if (!isNaN(numA) && !isNaN(numB)) {
                    return currentDir === 'asc' ? numA - numB : numB - numA;
                }
                return currentDir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
            });
            rows.forEach(r => tbody.appendChild(r));
            window.mkdocsKitCsvRender(wrapper);
        };
        document.addEventListener('DOMContentLoaded', () => {
            document.querySelectorAll('.mkdocs-kit-csv-wrapper').forEach(w => window.mkdocsKitCsvInit(w));
        });
    }
    setTimeout(() => {
        const wrapper = document.getElementById('''' + table_id + '''');
        if (wrapper && window.mkdocsKitCsvInit) window.mkdocsKitCsvInit(wrapper);
    }, 50);
    </script>
    </div>
    ''')
    
    return "".join(html_buf)
