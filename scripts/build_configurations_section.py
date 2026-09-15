#!/usr/bin/env python3
"""
Bench Configurations Processing Helper Script
==============================================
Parses Ariane 6 bench PDF configuration registers, extracts hardware component
breakdown structures (HBS), software/firmware release compositions, reference
documentation tables, and PMD anomaly records, generating:
1. Structured Markdown documentation pages under docs/configurations/
2. Structured CSV data exports under docs/configurations/csv/ (per-bench, per-register, and global master datasets).

Usage:
    python helpers/build_configurations_section.py [--registers REGISTERS_DIR] [--output OUTPUT_DIR]
"""

import os
import sys
import glob
import re
import csv
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import pypdf
import pdfplumber

def parse_single_pdf(pdf_path):
    fname = os.path.basename(pdf_path)

    # Determine Bench Name
    if 'CBREP' in fname: bench = 'CBREP'
    elif 'CBSR2' in fname: bench = 'CBSR2'
    elif 'CBLL1' in fname: bench = 'CBLL1'
    elif 'CBUL' in fname: bench = 'CBUL'
    elif 'TKCBLP' in fname: bench = 'TKCBLP'
    elif 'CBLP' in fname: bench = 'CBLP'
    elif 'VADOR_CNES' in fname: bench = 'VADOR_CNES'
    elif 'VADOR_AG' in fname: bench = 'VADOR_AG'
    else: bench = 'OTHER'

    # Extract Version
    ver_m = re.search(r'(GTD_|EVAO_)?([0-9]+\.[0-9]+(_[0-9]+)?)', fname)
    version = ver_m.group(2) if ver_m else "1.0"

    reader = pypdf.PdfReader(pdf_path)
    num_pages = len(reader.pages)

    # Extract text metadata from first 5 pages
    meta_text = ""
    for p in range(min(5, num_pages)):
        meta_text += reader.pages[p].extract_text() + "\n"

    # Match Document Ref
    ref_m = re.search(r'(A6-[A-Z0-9]+-[0-9X]+-[A-Z0-9]+-[0-9]+-[A-Z]+)', meta_text)
    doc_ref = ref_m.group(1) if ref_m else fname.replace('.pdf', '')

    # Match Date
    date_m = re.search(r'Date\s*:\s*([0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{2}/[0-9]{2}/[0-9]{4})', meta_text)
    date_str = date_m.group(1) if date_m else "-"

    hw_rows = []
    sw_rows = []
    doc_rows = []
    pmd_rows = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tbls = page.extract_tables()
            if not tbls: continue
            for tbl in tbls:
                if not tbl or len(tbl) < 2: continue

                header_text = ''
                for r in tbl[:2]:
                    if not r: continue
                    clean_r = [str(c).replace('\n', ' ').strip() for c in r if c is not None and str(c).strip()]
                    header_text += ' '.join(clean_r).lower() + ' '

                is_hbs = ('level' in header_text and ('name' in header_text or 'cots' in header_text or 'manufacturer' in header_text or 'cabinet' in header_text or 'desk' in header_text))
                is_sw = ('internal release' in header_text or ('tags' in header_text and 'component' in header_text))
                is_doc = ('document title' in header_text or ('reference' in header_text and ('dp' in header_text or 'da' in header_text or 'dr' in header_text)))
                is_pmd = ('pmd' in header_text or 'pmi' in header_text)

                if not (is_hbs or is_sw or is_doc or is_pmd):
                    continue

                for r in tbl[1:]:
                    if not r: continue
                    vals = [str(c).replace('\n', ' ').replace('', '-').strip() for c in r if c is not None and str(c).strip()]
                    if not vals: continue
                    val_str = ' '.join(vals).lower()
                    if any(kw in val_str for kw in ['document title', 'internal release', 'manufacturer', 'limited distribution', 'iss. :']):
                        continue

                    if is_hbs and len(vals) >= 2:
                        level = ''
                        if vals[0].isdigit():
                            level = vals[0]
                            vals = vals[1:]
                        elif len(vals) > 1 and vals[1].isdigit():
                            level = vals[1]
                            vals = [vals[0]] + vals[2:]

                        if vals:
                            name = vals[0]
                            cots = vals[1] if len(vals) > 1 else '-'
                            mfr = vals[2] if len(vals) > 2 else '-'
                            lic_type = vals[3] if len(vals) > 3 else '-'
                            family = vals[4] if len(vals) > 4 else '-'
                            pn_sn = vals[5] if len(vals) > 5 else '-'
                            loc = ' / '.join(vals[6:]) if len(vals) > 6 else '-'
                            hw_rows.append([level, name, cots, mfr, lic_type, family, pn_sn, loc])

                    elif is_sw and len(vals) >= 2:
                        comp = vals[0]
                        rel = vals[1] if len(vals) > 1 else '-'
                        tags = ' / '.join(vals[2:]) if len(vals) > 2 else '-'
                        sw_rows.append([comp, rel, tags])

                    elif is_doc and len(vals) >= 2:
                        dp = vals[0]
                        ref = vals[1] if len(vals) > 1 else '-'
                        title = vals[2] if len(vals) > 2 else '-'
                        ver = vals[3] if len(vals) > 3 else '-'
                        status = vals[4] if len(vals) > 4 else '-'
                        doc_rows.append([dp, ref, title, ver, status])

                    elif is_pmd and len(vals) >= 2:
                        ref = vals[0]
                        desc = vals[1] if len(vals) > 1 else '-'
                        status = ' / '.join(vals[2:]) if len(vals) > 2 else '-'
                        pmd_rows.append([ref, desc, status])

    return {
        'bench': bench,
        'filename': fname,
        'path': pdf_path,
        'doc_ref': doc_ref,
        'version': version,
        'date': date_str,
        'num_pages': num_pages,
        'hw_components_count': len(hw_rows),
        'hw_components': hw_rows,
        'sw_components_count': len(sw_rows),
        'sw_components': sw_rows,
        'doc_tables_count': len(doc_rows),
        'doc_tables': doc_rows,
        'pmd_tables_count': len(pmd_rows),
        'pmd_tables': pmd_rows
    }

def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    parser = argparse.ArgumentParser(description="Parse PDF Configuration Registers into Markdown documentation & CSV exports.")
    parser.add_argument('--registers', default=os.path.join(base_dir, 'docs', 'config_registers'), help="Directory containing PDF registers")
    parser.add_argument('--output', default=os.path.join(base_dir, 'docs', 'configurations'), help="Output directory for configurations markdown pages")

    args = parser.parse_args()

    pdf_files = sorted(glob.glob(os.path.join(args.registers, "*.pdf")))
    print(f"Starting parallel processing of {len(pdf_files)} PDF register files from {args.registers}...")

    results = []
    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(parse_single_pdf, f): f for f in pdf_files}
        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            print(f"  Parsed {res['filename']}: {res['num_pages']} pages, HW: {res['hw_components_count']}, SW: {res['sw_components_count']}, Docs: {res['doc_tables_count']}, PMD: {res['pmd_tables_count']}")

    # Output CSV directories
    csv_dir = os.path.join(args.output, 'csv')
    reg_csv_dir = os.path.join(csv_dir, 'registers')
    os.makedirs(csv_dir, exist_ok=True)
    os.makedirs(reg_csv_dir, exist_ok=True)

    # 1. Export Per-Register CSV Files
    for r in results:
        base_name = os.path.splitext(r['filename'])[0]
        # HBS per register
        if r['hw_components']:
            with open(os.path.join(reg_csv_dir, f"{base_name}_hbs.csv"), 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Level", "Component Name / Description", "COTS Status", "Manufacturer / Supplier", "License / Type", "Family / Sub-system", "PN / Serial Number", "Location / Cabinet"])
                writer.writerows(r['hw_components'])
        # SW per register
        if r['sw_components']:
            with open(os.path.join(reg_csv_dir, f"{base_name}_sw.csv"), 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Component Code / Name", "Internal Release / Version", "Configuration Tags / Sub-components"])
                writer.writerows(r['sw_components'])
        # Docs per register
        if r['doc_tables']:
            with open(os.path.join(reg_csv_dir, f"{base_name}_docs.csv"), 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["DP / DA Ref", "Document Reference", "Document Title", "Version", "Delivery Status"])
                writer.writerows(r['doc_tables'])
        # PMD per register
        if r['pmd_tables']:
            with open(os.path.join(reg_csv_dir, f"{base_name}_pmd.csv"), 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["PMD Reference", "Description / Impact", "Status / Closure"])
                writer.writerows(r['pmd_tables'])

    # 2. Export Global Master CSV Files across all benches
    global_hw = []
    global_sw = []
    global_docs = []
    global_pmd = []

    for r in sorted(results, key=lambda x: (x['bench'], x['version'])):
        for row in r['hw_components']:
            global_hw.append([r['bench'], r['filename'], r['doc_ref'], r['version']] + row)
        for row in r['sw_components']:
            global_sw.append([r['bench'], r['filename'], r['doc_ref'], r['version']] + row)
        for row in r['doc_tables']:
            global_docs.append([r['bench'], r['filename'], r['doc_ref'], r['version']] + row)
        for row in r['pmd_tables']:
            global_pmd.append([r['bench'], r['filename'], r['doc_ref'], r['version']] + row)

    with open(os.path.join(csv_dir, "all_benches_hbs.csv"), 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Bench", "PDF Register File", "Document Reference", "Register Version", "Level", "Component Name / Description", "COTS Status", "Manufacturer / Supplier", "License / Type", "Family / Sub-system", "PN / Serial Number", "Location / Cabinet"])
        writer.writerows(global_hw)

    with open(os.path.join(csv_dir, "all_benches_sw.csv"), 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Bench", "PDF Register File", "Document Reference", "Register Version", "Component Code / Name", "Internal Release / Version", "Configuration Tags / Sub-components"])
        writer.writerows(global_sw)

    with open(os.path.join(csv_dir, "all_benches_docs.csv"), 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Bench", "PDF Register File", "Document Reference", "Register Version", "DP / DA Ref", "Document Reference", "Document Title", "Version", "Delivery Status"])
        writer.writerows(global_docs)

    with open(os.path.join(csv_dir, "all_benches_pmd.csv"), 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Bench", "PDF Register File", "Document Reference", "Register Version", "PMD Reference", "Description / Impact", "Status / Closure"])
        writer.writerows(global_pmd)

    with open(os.path.join(csv_dir, "all_registers_summary.csv"), 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Bench", "PDF Register File", "Document Reference", "Version", "Release Date", "Page Count", "Hardware Items Count", "Software Items Count", "Doc References Count", "PMD Items Count"])
        for r in sorted(results, key=lambda x: (x['bench'], x['version'])):
            writer.writerow([r['bench'], r['filename'], r['doc_ref'], r['version'], r['date'], r['num_pages'], r['hw_components_count'], r['sw_components_count'], r['doc_tables_count'], r['pmd_tables_count']])

    # Group by bench
    bench_map = {}
    for r in results:
        b = r['bench']
        if b not in bench_map:
            bench_map[b] = []
        bench_map[b].append(r)

    os.makedirs(args.output, exist_ok=True)

    # Build bench pages
    bench_summaries = []

    for b_name, b_files in sorted(bench_map.items()):
        b_files.sort(key=lambda x: x['version'])
        b_lower = b_name.lower()

        latest_file = b_files[-1]
        page_filename = f"{b_lower}.md"
        page_filepath = os.path.join(args.output, page_filename)

        # Consolidate per-bench CSVs
        b_hw = []
        seen_hw = set()
        for f in b_files:
            for row in f['hw_components']:
                key = ' | '.join(row)
                if key not in seen_hw:
                    seen_hw.add(key)
                    b_hw.append([f['doc_ref'], f['version']] + row)

        b_sw = []
        seen_sw = set()
        for f in b_files:
            for row in f['sw_components']:
                key = ' | '.join(row)
                if key not in seen_sw:
                    seen_sw.add(key)
                    b_sw.append([f['doc_ref'], f['version']] + row)

        b_docs = []
        seen_docs = set()
        for f in b_files:
            for row in f['doc_tables']:
                key = ' | '.join(row)
                if key not in seen_docs:
                    seen_docs.add(key)
                    b_docs.append([f['doc_ref'], f['version']] + row)

        b_pmd = []
        seen_pmd = set()
        for f in b_files:
            for row in f['pmd_tables']:
                key = ' | '.join(row)
                if key not in seen_pmd:
                    seen_pmd.add(key)
                    b_pmd.append([f['doc_ref'], f['version']] + row)

        # Write per-bench CSVs
        bench_hw_csv = f"{b_lower}_hbs.csv"
        bench_sw_csv = f"{b_lower}_sw.csv"
        bench_docs_csv = f"{b_lower}_docs.csv"
        bench_pmd_csv = f"{b_lower}_pmd.csv"

        with open(os.path.join(csv_dir, bench_hw_csv), 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Document Reference", "Register Version", "Level", "Component Name / Description", "COTS Status", "Manufacturer / Supplier", "License / Type", "Family / Sub-system", "PN / Serial Number", "Location / Cabinet"])
            writer.writerows(b_hw)

        with open(os.path.join(csv_dir, bench_sw_csv), 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Document Reference", "Register Version", "Component Code / Name", "Internal Release / Version", "Configuration Tags / Sub-components"])
            writer.writerows(b_sw)

        with open(os.path.join(csv_dir, bench_docs_csv), 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Document Reference", "Register Version", "DP / DA Ref", "Document Reference", "Document Title", "Version", "Delivery Status"])
            writer.writerows(b_docs)

        with open(os.path.join(csv_dir, bench_pmd_csv), 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Document Reference", "Register Version", "PMD Reference", "Description / Impact", "Status / Closure"])
            writer.writerows(b_pmd)

        md = []
        md.append(f"# 🎛️ Bench Configuration: `{b_name}`\n")
        md.append(f"This page presents the consolidated configuration registers, hardware component breakdown structure (HBS), software composition, and reference documentation for **{b_name}** benches across all delivered document revisions.\n")

        # CSV Exports Alert Box
        md.append("> 📊 **Raw CSV Data Exports**: Download structured datasets for this bench:\n"
                  f"> - 📄 [`{bench_hw_csv}`](csv/{bench_hw_csv}) ({len(b_hw)} Hardware Breakdown items)\n"
                  f"> - 💻 [`{bench_sw_csv}`](csv/{bench_sw_csv}) ({len(b_sw)} Software Components)\n"
                  f"> - 📚 [`{bench_docs_csv}`](csv/{bench_docs_csv}) ({len(b_docs)} Technical References)\n"
                  f"> - 🚨 [`{bench_pmd_csv}`](csv/{bench_pmd_csv}) ({len(b_pmd)} PMD Anomalies)\n")

        md.append("## 📋 Configuration Register Document Versions\n")
        md.append("| Document Reference | Bench Version | Date | Pages | Total Hardware Items | PDF Register File |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for f in b_files:
            rel_pdf_path = f"../config_registers/{f['filename']}"
            md.append(f"| `{f['doc_ref']}` | **v{f['version']}** | {f['date']} | {f['num_pages']} | {f['hw_components_count']} | [{f['filename']}]({rel_pdf_path}) |")

        md.append("\n---\n")

        # Hardware Component Tree Structure Table
        md.append("## 🏗️ Hardware Component Breakdown Structure (HBS)\n")

        all_hw = [row[2:] for row in b_hw] # omit doc_ref, version for markdown table clean display

        if all_hw:
            headers = ["Level", "Component Name / Description", "COTS Status", "Manufacturer / Supplier", "License / Type", "Family / Sub-system", "PN / Serial Number", "Location / Cabinet"]
            md.append("| " + " | ".join(headers) + " |")
            md.append("| " + " | ".join([":---"] * len(headers)) + " |")

            for r in all_hw[:250]: # Up to 250 structured rows
                padded = r + ["-"] * (8 - len(r))
                row_cells = padded[:8]

                level_str = row_cells[0]
                if level_str.isdigit():
                    indent = "&nbsp;&nbsp;" * int(level_str)
                    row_cells[1] = f"{indent}↳ {row_cells[1]}"

                row_cells = [c.replace('|', '\\|') for c in row_cells]
                md.append("| " + " | ".join(row_cells) + " |")

            if len(all_hw) > 250:
                md.append(f"\n*\nShowing top 250 components of {len(all_hw)} total recorded items for bench {b_name}. Download full dataset in [`{bench_hw_csv}`](csv/{bench_hw_csv}).*\n")
        else:
            md.append("*No hardware component tree items recorded in parsed configuration registers for this bench.*\n")

        md.append("\n---\n")

        # Software Composition Table
        md.append("## 💻 Software & Firmware Release Composition\n")
        all_sw = [row[2:] for row in b_sw]

        if all_sw:
            sw_headers = ["Component Code / Name", "Internal Release / Version", "Configuration Tags / Sub-components"]
            md.append("| " + " | ".join(sw_headers) + " |")
            md.append("| " + " | ".join([":---"] * len(sw_headers)) + " |")
            for r in all_sw[:150]:
                padded = r + ["-"] * (3 - len(r))
                row_cells = [c.replace('|', '\\|') for c in padded[:3]]
                md.append("| " + " | ".join(row_cells) + " |")
        else:
            md.append("*No specific software components explicit in parsed tables for this bench.*\n")

        md.append("\n---\n")

        # Applicable & Industrial Documents Table
        md.append("## 📚 Reference & Industrial Documentation\n")
        all_docs = [row[2:] for row in b_docs]

        if all_docs:
            doc_headers = ["DP / DA Ref", "Document Reference", "Document Title", "Version", "Delivery Status"]
            md.append("| " + " | ".join(doc_headers) + " |")
            md.append("| " + " | ".join([":---"] * len(doc_headers)) + " |")
            for r in all_docs[:100]:
                padded = r + ["-"] * (5 - len(r))
                row_cells = [c.replace('|', '\\|') for c in padded[:5]]
                md.append("| " + " | ".join(row_cells) + " |")
        else:
            md.append("*No reference document tables recorded for this bench.*\n")

        with open(page_filepath, 'w', encoding='utf-8') as out:
            out.write('\n'.join(md))

        bench_summaries.append((b_name, page_filename, len(b_files), latest_file['version'], latest_file['date'], len(b_hw), len(b_sw)))

    # Build Index Overview Page: docs/configurations/index.md
    index_filepath = os.path.join(args.output, 'index.md')
    idx = []
    idx.append("# ⚙️ Bench Configurations Master Overview\n")
    idx.append("This section documents the official **Configuration Registers** for all Ariane 6 ground segment control benches, detailing hardware breakdown structures (HBS), component trees, software release packages, COTS licenses, and technical specifications.\n")

    # Master CSV Datasets Alert
    idx.append("## 📊 Master CSV Datasets & Raw Downloads\n")
    idx.append("All configuration registers have been transformed into structured CSV files for automated analysis, inventory management, and database ingestion:\n")
    idx.append("| Dataset Name | Total Records | Description | Direct Download Link |")
    idx.append("| :--- | :--- | :--- | :--- |")
    idx.append(f"| **All Benches Hardware Breakdown (HBS)** | {len(global_hw)} rows | Complete hardware component hierarchy across all 29 registers | [📥 `all_benches_hbs.csv`](csv/all_benches_hbs.csv) |")
    idx.append(f"| **All Benches Software Composition** | {len(global_sw)} rows | Full software and firmware release packages | [📥 `all_benches_sw.csv`](csv/all_benches_sw.csv) |")
    idx.append(f"| **All Benches Reference Documentation** | {len(global_docs)} rows | Technical and industrial reference documents | [📥 `all_benches_docs.csv`](csv/all_benches_docs.csv) |")
    idx.append(f"| **All Benches PMD Anomaly Tracking** | {len(global_pmd)} rows | PMI / PMD anomaly tracking records | [📥 `all_benches_pmd.csv`](csv/all_benches_pmd.csv) |")
    idx.append(f"| **Master Configuration Registers Inventory** | {len(results)} registers | Metadata index of all parsed PDF configuration registers | [📥 `all_registers_summary.csv`](csv/all_registers_summary.csv) |\n")

    idx.append("## 📑 Control Bench Families Overview\n")
    idx.append("| Bench Identifier | Description | Total Document Revisions | Latest Register Version | Release Date | Hardware Components | Direct Link | CSV Export |")
    idx.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

    bench_descriptions = {
        'CBREP': 'Control Bench Real-Time Electronic Processing (Primary Test Bench)',
        'CBSR2': 'Control Bench Safety & Range 2 (Secondary Test Bench)',
        'CBLL1': 'Control Bench Lower Liquid 1 (Launcher Fluidic & Propulsion Test Bench)',
        'CBUL': 'Control Bench Upper Liquid (Upper Stage Propulsion Test Bench)',
        'CBLP': 'Control Bench Launch Pad (Ground Integration & Infrastructure Test Bench)',
        'TKCBLP': 'Tanking Control Bench Launch Pad (Propellant Loading System Test Bench)',
        'VADOR_CNES': 'VADOR CNES Acquisition & Optical Data Bench',
        'VADOR_AG': 'VADOR ArianeGroup Acquisition & Guidance Bench'
    }

    for b_name, page_filename, num_revs, latest_ver, latest_date, hw_cnt, sw_cnt in bench_summaries:
        desc = bench_descriptions.get(b_name, 'Ariane 6 Control Bench Subsystem')
        b_lower = b_name.lower()
        idx.append(f"| **`{b_name}`** | {desc} | {num_revs} registers | **v{latest_ver}** | {latest_date} | {hw_cnt} components | [{b_name}]({page_filename}) | [📥 `{b_lower}_hbs.csv`](csv/{b_lower}_hbs.csv) |")

    idx.append("\n---\n")

    idx.append("## 📂 Global Configuration Registers Inventory\n")
    idx.append("Download and inspect the original PDF Configuration Registers below:\n")
    idx.append("| Document Reference | Bench Subsystem | Version | Release Date | Page Count | Download Link | PDF Per-Register CSV |")
    idx.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

    for r in sorted(results, key=lambda x: (x['bench'], x['version'])):
        rel_pdf = f"../config_registers/{r['filename']}"
        base_name = os.path.splitext(r['filename'])[0]
        csv_link = f"[CSV](csv/registers/{base_name}_hbs.csv)" if r['hw_components'] else "-"
        idx.append(f"| `{r['doc_ref']}` | **{r['bench']}** | v{r['version']} | {r['date']} | {r['num_pages']} pages | [{r['filename']}]({rel_pdf}) | {csv_link} |")

    with open(index_filepath, 'w', encoding='utf-8') as out:
        out.write('\n'.join(idx))

    print(f"\nGenerated master configuration overview, {len(bench_summaries)} bench pages, and complete CSV exports in {args.output}/csv")

if __name__ == '__main__':
    main()
