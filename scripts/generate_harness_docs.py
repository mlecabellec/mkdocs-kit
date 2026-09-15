#!/usr/bin/env python3
import os
import sys
import csv
import re
import shutil
import wireviz.wireviz as wv

def generate_harness_docs(signals_path, faisceaux_path, embases_path, output_dir):
    """
    Deterministically transforms CBREP CSV data into individual harness markdown pages
    containing strictly verified WireViz diagrams constructed directly from CSV fields,
    with clean connector formatting, deduplicated physical pins, and explicit signal wirelabels.
    """
    with open(faisceaux_path, 'r', encoding='utf-8', errors='replace') as f:
        faisceaux_rows = list(csv.DictReader(f))

    faisceaux_dict = {r['ID'].strip(): r for r in faisceaux_rows if r['ID'].strip()}

    with open(embases_path, 'r', encoding='utf-8', errors='replace') as f:
        embases_rows = list(csv.DictReader(f))

    embases_dict = {r['Interface'].strip(): r for r in embases_rows if r['Interface'].strip()}

    with open(signals_path, 'r', encoding='utf-8', errors='replace') as f:
        signal_rows = list(csv.DictReader(f))

    def clean(val):
        if not val or val.strip() in ('-', '.', '=', 'nan', 'No', 'SO'):
            return ''
        return val.strip()

    def sanitize_id(name):
        cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        cleaned = re.sub(r'_+', '_', cleaned).strip('_')
        return cleaned if cleaned else 'CONN'

    def format_disp_name(val):
        lines = [line.strip() for line in val.split('\n') if line.strip() and line.strip() not in ('-', '.', '=')]
        if not lines:
            return 'Equipment'
        if len(lines) > 2:
            return f"{lines[0]}..{lines[-1]}"
        return ' / '.join(lines)

    def harness_to_filename(h_id):
        fn = re.sub(r'[^a-zA-Z0-9_\-]', '_', h_id)
        fn = re.sub(r'_+', '_', fn).strip('_')
        return f"{fn}.md"

    def parse_pins(pin_str):
        if not pin_str:
            return []
        pins = []
        for line in pin_str.split('\n'):
            for part in line.split(','):
                p = part.strip()
                if p and p not in ('-', '.', '='):
                    pins.append(p)
        return pins

    def parse_multiline_list(cell_str):
        if not cell_str:
            return []
        return [line.strip() for line in cell_str.split('\n') if line.strip() and line.strip() not in ('-', '.', '=')]

    # Group signals by harness ID
    harness_signals = {}
    for s in signal_rows:
        h_set = set()
        for col in ['harness', 'harness.1', 'cabling cabinet']:
            val = s.get(col, '')
            if val:
                for item in val.split('\n'):
                    item = item.strip()
                    if item and item not in ('-', '.', '=', 'nan', 'WGxxxx', 'Pas cablé'):
                        h_set.add(item)
        for h_id in h_set:
            if h_id not in harness_signals:
                harness_signals[h_id] = []
            harness_signals[h_id].append(s)

    all_harness_ids = sorted(list((set(faisceaux_dict.keys()) | set(harness_signals.keys())) - {'-', '.', '=', 'nan', 'WGxxxx', 'Pas cablé'}))

    # Clean and create output directory
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    def build_strict_wireviz_diagrams(h_id, signals, chunk_size=12):
        if not signals:
            return [], 0

        cable_id = sanitize_id(h_id)
        all_wire_entries = []

        for s_idx, sig in enumerate(signals):
            s_name = clean(sig.get('Signal name')) or f"SIG_{s_idx+1}"

            raw_src_cab = clean(sig.get('Source cabinet')) or clean(sig.get('bornier')) or "Source"
            src_name = format_disp_name(raw_src_cab)
            src_conn_id = sanitize_id(src_name)

            raw_dst_cab = clean(sig.get('destination')) or clean(sig.get('embase')) or clean(sig.get('cabling cabinet')) or clean(sig.get('bornier.3')) or "Destination"
            dst_name = format_disp_name(raw_dst_cab)
            dst_conn_id = sanitize_id(dst_name)

            if src_conn_id == dst_conn_id or src_conn_id == cable_id:
                src_conn_id = f"{src_conn_id}_SRC"
            if dst_conn_id == src_conn_id or dst_conn_id == cable_id:
                dst_conn_id = f"{dst_conn_id}_DEST"

            src_cabs = parse_multiline_list(sig.get('Source cabinet'))
            src_pos_pins = parse_pins(sig.get('+')) or parse_pins(sig.get('+.1')) or parse_pins(sig.get('+.2'))
            src_neg_pins = parse_pins(sig.get('-')) or parse_pins(sig.get('-.1')) or parse_pins(sig.get('-.2'))

            dst_pos_pins = parse_pins(sig.get('+.3')) or parse_pins(sig.get('+.4')) or parse_pins(sig.get('+.5')) or parse_pins(sig.get('+.6'))
            dst_neg_pins = parse_pins(sig.get('-.3')) or parse_pins(sig.get('-.4')) or parse_pins(sig.get('-.5')) or parse_pins(sig.get('-.6'))

            n_pos = max(len(src_pos_pins), len(dst_pos_pins), 1 if (src_pos_pins or dst_pos_pins) else 0)
            for i in range(n_pos):
                sp = src_pos_pins[i] if i < len(src_pos_pins) else f"Pin_{i+1}"
                dp = dst_pos_pins[i] if i < len(dst_pos_pins) else (dst_pos_pins[-1] if dst_pos_pins else "NC")

                sub_cab = src_cabs[i] if i < len(src_cabs) else ""
                lbl_suffix = f" ({sub_cab}) (+)" if sub_cab else (" (+)" if n_pos > 1 or src_neg_pins else "")
                lbl = f"{s_name}{lbl_suffix}"
                all_wire_entries.append((src_conn_id, src_name, sp, dst_conn_id, dst_name, dp, lbl))

            n_neg = max(len(src_neg_pins), len(dst_neg_pins), 1 if src_neg_pins or dst_neg_pins else 0)
            for i in range(n_neg):
                sp = src_neg_pins[i] if i < len(src_neg_pins) else f"Pin_{i+1}"
                dp = dst_neg_pins[i] if i < len(dst_neg_pins) else (dst_neg_pins[-1] if dst_neg_pins else "NC")

                sub_cab = src_cabs[i] if i < len(src_cabs) else ""
                lbl_suffix = f" ({sub_cab}) (-)" if sub_cab else " (-)"
                lbl = f"{s_name}{lbl_suffix}"
                all_wire_entries.append((src_conn_id, src_name, sp, dst_conn_id, dst_name, dp, lbl))

            if not n_pos and not n_neg:
                sp = f"Pin_{s_idx+1}"
                dp = f"Pin_{s_idx+1}"
                all_wire_entries.append((src_conn_id, src_name, sp, dst_conn_id, dst_name, dp, s_name))

        if not all_wire_entries:
            return [], 0

        diagram_specs = []
        total_parts = (len(all_wire_entries) + chunk_size - 1) // chunk_size

        for chunk_idx in range(0, len(all_wire_entries), chunk_size):
            chunk = all_wire_entries[chunk_idx:chunk_idx+chunk_size]
            part_num = (chunk_idx // chunk_size) + 1

            conn_pin_map = {}
            conn_type_map = {}
            wire_src_pinlabels = []
            wire_dst_pinlabels = []

            for src_id, src_disp, sp, dst_id, dst_disp, dp, lbl in chunk:
                if src_id not in conn_pin_map:
                    conn_pin_map[src_id] = []
                    conn_type_map[src_id] = src_disp
                if dst_id not in conn_pin_map:
                    conn_pin_map[dst_id] = []
                    conn_type_map[dst_id] = dst_disp

                sp_clean = f"P_{re.sub(r'[^a-zA-Z0-9_]', '_', sp).strip('_')}"
                if sp_clean not in conn_pin_map[src_id]:
                    conn_pin_map[src_id].append(sp_clean)
                wire_src_pinlabels.append(sp_clean)

                dp_clean = f"P_{re.sub(r'[^a-zA-Z0-9_]', '_', dp).strip('_')}"
                if dp_clean not in conn_pin_map[dst_id]:
                    conn_pin_map[dst_id].append(dp_clean)
                wire_dst_pinlabels.append(dp_clean)

            yaml_lines = ['connectors:']
            for conn_id, pins in conn_pin_map.items():
                disp = conn_type_map[conn_id]
                p_str = ', '.join(f'"{p}"' for p in pins)
                yaml_lines.append(f"  {conn_id}:")
                yaml_lines.append(f"    type: \"{disp}\"")
                yaml_lines.append(f"    pinlabels: [{p_str}]")

            yaml_lines.append('\ncables:')
            sub_cable_id = f"{cable_id}_p{part_num}" if total_parts > 1 else cable_id
            yaml_lines.append(f"  {sub_cable_id}:")
            yaml_lines.append(f"    wirecount: {len(chunk)}")

            clean_labels = []
            for w in chunk:
                lbl_text = re.sub(r'[^\w\s\(\)\+\-\.]', '_', w[6])
                clean_labels.append(f'"{lbl_text}"')
            w_str = ', '.join(clean_labels)
            yaml_lines.append(f"    wirelabels: [{w_str}]")

            yaml_lines.append('\nconnections:')
            for idx, (src_id, _, _, dst_id, _, _, _) in enumerate(chunk):
                sp_lbl = wire_src_pinlabels[idx]
                dp_lbl = wire_dst_pinlabels[idx]
                yaml_lines.append('  -')
                yaml_lines.append(f'    - {src_id}: ["{sp_lbl}"]')
                yaml_lines.append(f'    - {sub_cable_id}: [{idx+1}]')
                yaml_lines.append(f'    - {dst_id}: ["{dp_lbl}"]')

            spec = '\n'.join(yaml_lines)
            wv.parse(spec, return_types='svg')
            title = f"Section {part_num} of {total_parts} (Wires {chunk_idx+1} to {chunk_idx+len(chunk)} of {len(all_wire_entries)})" if total_parts > 1 else ""
            diagram_specs.append((title, spec))

        return diagram_specs, len(all_wire_entries)

    # Generate each harness markdown file
    generated_files = []

    for h_id in all_harness_ids:
        sigs = harness_signals.get(h_id, [])
        f_info = faisceaux_dict.get(h_id, {})

        fname = harness_to_filename(h_id)
        fpath = os.path.join(output_dir, fname)

        diagram_specs, total_wires = build_strict_wireviz_diagrams(h_id, sigs)

        md = []
        md.append(f"# 🔌 Harness Documentation: `{h_id}`\n")

        # Properties Table
        md.append("## 📋 Harness Specifications & Metadata\n")
        md.append("| Property | Value |")
        md.append("| :--- | :--- |")
        md.append(f"| **Harness Identifier** | `{h_id}` |")
        md.append(f"| **Resistance per Signal** | {f_info.get('R/signal\\n(mOhm)', f_info.get('R/signal', '-')) or '-'} mOhm |")
        md.append(f"| **Available Signals** | {f_info.get('Nombre de signaux disponibles', '-') or '-'} |")
        md.append(f"| **Present Signals** | {f_info.get('Nombre de signaux présents', '-') or '-'} |")
        md.append(f"| **Spare Signals** | {f_info.get('Spare de signaux', '-') or '-'} |")
        md.append(f"| **Cabled Spare** | {f_info.get('Spare cablés', '-') or '-'} |")
        md.append(f"| **Real Spare** | {f_info.get('spare réelle', '-') or '-'} |")
        md.append(f"| **Total Route Signals in CSV** | {len(sigs)} |")
        md.append(f"| **Total Conductors / Wires** | {total_wires} |")
        md.append(f"| **WireViz Diagram Sections** | {len(diagram_specs)} |")
        md.append("\n---\n")

        # WireViz Diagram Section
        md.append("## 📐 Wiring Harness Diagrams\n")

        if diagram_specs:
            if len(diagram_specs) > 1:
                md.append(f"> [!NOTE]\n> **Multi-Section Harness Diagram**: Harness `{h_id}` contains **{len(sigs)} signal routes** ({total_wires} total conductors). To ensure 100% complete visual representation without exceeding Graphviz layout limits, the wiring schematic below is split into **{len(diagram_specs)} readable diagram sections**.\n")

            for title, spec in diagram_specs:
                if title:
                    md.append(f"### 🔗 {title}\n")
                md.append("```wireviz")
                md.append(spec.strip())
                md.append("```\n")
        else:
            md.append(f"> [!NOTE]\n> **Unassigned / Spare Harness**: Harness `{h_id}` is listed in the harness capacity inventory (`Faisceaux.csv`), but has no active signal routes assigned in `signals.csv`.\n")

        md.append("\n---\n")

        # Signals List Table
        md.append("## ⚡ Associated Signals Routing Table\n")
        if sigs:
            md.append("| Signal Name | Signal Type | Source Cabinet & Terminal | Intermediate / Cabling | Destination / Embase | Resistance (mOhm) |")
            md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
            for s in sigs:
                s_name = clean(s.get('Signal name')) or '-'
                s_type = clean(s.get('Signal type')) or '-'

                src_cab = clean(s.get('Source cabinet')) or '-'
                src_born = clean(s.get('bornier'))
                src_p_plus = clean(s.get('+'))
                src_p_minus = clean(s.get('-'))
                src_str = f"{src_cab}"
                if src_born: src_str += f" ({src_born})"
                if src_p_plus or src_p_minus: src_str += f" [+: {src_p_plus or '-'}, -: {src_p_minus or '-'}]"

                cabling_cab = clean(s.get('cabling cabinet')) or '-'
                cabling_born1 = clean(s.get('bornier.1'))
                cabling_born2 = clean(s.get('bornier.2'))
                cabling_str = f"{cabling_cab}"
                if cabling_born1 or cabling_born2: cabling_str += f" ({cabling_born1 or cabling_born2})"

                dest_cab = clean(s.get('destination'))
                dest_emb = clean(s.get('embase'))
                dest_born = clean(s.get('bornier.3')) or clean(s.get('bornier.4'))
                dest_p_plus = clean(s.get('+.3')) or clean(s.get('+.4')) or clean(s.get('+.5')) or clean(s.get('+.6'))
                dest_p_minus = clean(s.get('-.3')) or clean(s.get('-.4')) or clean(s.get('-.5')) or clean(s.get('-.6'))

                dest_str = dest_cab or dest_emb or '-'
                if dest_born: dest_str += f" ({dest_born})"
                if dest_p_plus or dest_p_minus: dest_str += f" [+: {dest_p_plus or '-'}, -: {dest_p_minus or '-'}]"

                res = clean(s.get('Resistance')) or '-'

                src_str = src_str.replace('\n', '<br>')
                cabling_str = cabling_str.replace('\n', '<br>')
                dest_str = dest_str.replace('\n', '<br>')

                md.append(f"| {s_name} | {s_type} | {src_str} | {cabling_str} | {dest_str} | {res} |")
        else:
            md.append("*No individual signal routes explicit for this harness identifier in signal dataset.*\n")

        with open(fpath, 'w', encoding='utf-8') as out:
            out.write('\n'.join(md))

        # Extract source and dest cabinets for summary table
        src_cabs = sorted(list({clean(s.get('Source cabinet')).replace('\n', ' / ') for s in sigs if clean(s.get('Source cabinet'))}))
        dst_cabs = sorted(list({(clean(s.get('destination')) or clean(s.get('embase')) or clean(s.get('cabling cabinet'))).replace('\n', ' / ') for s in sigs if (clean(s.get('destination')) or clean(s.get('embase')) or clean(s.get('cabling cabinet')))}))

        src_summary = ', '.join(src_cabs) if src_cabs else '-'
        dst_summary = ', '.join(dst_cabs) if dst_cabs else '-'

        generated_files.append((h_id, fname, len(sigs), f_info, src_summary, dst_summary))

    # Create Index Overview Page
    index_path = os.path.join(output_dir, 'index.md')
    idx_md = []
    idx_md.append("# 🗂️ Wiring Harnesses Index & Overview\n")
    idx_md.append("This page provides a complete, interactive inventory of all wiring harnesses defined in the **CBREP** signal database, featuring source/destination routing and interactive data filtering.\n")

    idx_md.append("## 📊 Interactive Harness Inventory Data\n")
    idx_md.append("```csv")
    idx_md.append("file: ../signal-data/SignalEndToEnd__CBREP_D_Faisceaux.csv")
    idx_md.append("page_size: 10")
    idx_md.append("sort: \"ID asc\"")
    idx_md.append("search: true")
    idx_md.append("caption: Global Harness Inventory & Capacity Data")
    idx_md.append("```\n")

    idx_md.append("\n---\n")

    # Master Table with Source and Destination Cabinets
    idx_md.append("## 📑 Harnesses & Wires Master Summary Table\n")
    idx_md.append(f"Total harnesses documented: **{len(generated_files)}**\n")

    idx_md.append("| Harness ID | Source Cabinet(s) | Destination Cabinet(s) / Embase | Resistance (mOhm) | Active Signals | Spare Signals | Link |")
    idx_md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

    for h_id, fname, sig_cnt, f_info, src_summary, dst_summary in generated_files:
        res = f_info.get('R/signal\n(mOhm)', f_info.get('R/signal', '-')) or '-'
        spare = f_info.get('Spare de signaux', '-') or '-'
        idx_md.append(f"| **`{h_id}`** | {src_summary} | {dst_summary} | {res} | {sig_cnt} | {spare} | [{h_id}]({fname}) |")

    with open(index_path, 'w', encoding='utf-8') as out:
        out.write('\n'.join(idx_md))

    print(f"Successfully generated {len(generated_files)} harness markdown files and index.md in {output_dir}")

if __name__ == '__main__':
    signals_csv = '/media/vortigern/mlc2023b/tmp/cbrep-mkdocs-v1/docs/signal-data/SignalEndToEnd__CBREP_D_signals.csv'
    faisceaux_csv = '/media/vortigern/mlc2023b/tmp/cbrep-mkdocs-v1/docs/signal-data/SignalEndToEnd__CBREP_D_Faisceaux.csv'
    embases_csv = '/media/vortigern/mlc2023b/tmp/cbrep-mkdocs-v1/docs/signal-data/SignalEndToEnd__CBREP_D_Embases.csv'
    out_dir = '/media/vortigern/mlc2023b/tmp/cbrep-mkdocs-v1/docs/harnesses'

    generate_harness_docs(signals_csv, faisceaux_csv, embases_csv, out_dir)
