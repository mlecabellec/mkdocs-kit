#!/usr/bin/env python3
import os
import glob
import re
import json
import pypdf
import pdfplumber

def parse_config_registers(registers_dir, output_dir):
    """
    Parses all Configuration Register PDFs, extracts metadata, document tables,
    software release compositions, change requests, and hardware component trees,
    and formats them into structured Markdown pages per bench.
    """
    os.makedirs(output_dir, exist_ok=True)
    pdf_files = sorted(glob.glob(os.path.join(registers_dir, "*.pdf")))

    benches = {}

    for pdf_path in pdf_files:
        fname = os.path.basename(pdf_path)

        # Classify bench name
        if 'CBREP' in fname: bench = 'CBREP'
        elif 'CBSR2' in fname: bench = 'CBSR2'
        elif 'CBLL1' in fname: bench = 'CBLL1'
        elif 'CBUL' in fname: bench = 'CBUL'
        elif 'TKCBLP' in fname: bench = 'TKCBLP'
        elif 'CBLP' in fname: bench = 'CBLP'
        elif 'VADOR_CNES' in fname: bench = 'VADOR_CNES'
        elif 'VADOR_AG' in fname: bench = 'VADOR_AG'
        else: bench = 'OTHER'

        if bench not in benches:
            benches[bench] = []
        benches[bench].append((fname, pdf_path))

    print(f"Found {len(pdf_files)} PDF register files across {len(benches)} benches: {list(benches.keys())}")

    # For each bench, process all its PDF files
    bench_data = {}

    for bench_name, file_list in benches.items():
        print(f"\n==================== Processing Bench: {bench_name} ({len(file_list)} files) ====================")
        bench_versions = []

        for fname, pdf_path in file_list:
            print(f"  Parsing: {fname}")

            # Extract basic text and metadata
            reader = pypdf.PdfReader(pdf_path)
            num_pages = len(reader.pages)

            title = fname
            date_str = "-"
            issue_ver = "-"
            doc_ref = fname.replace('.pdf', '')

            # Extract text from first 5 pages for metadata
            meta_text = ""
            for p in range(min(5, num_pages)):
                meta_text += reader.pages[p].extract_text() + "\n"

            # Match Document Ref
            ref_m = re.search(r'(A6-[A-Z0-9]+-[0-9X]+-[A-Z0-9]+-[0-9]+-[A-Z]+)', meta_text)
            if ref_m:
                doc_ref = ref_m.group(1)

            # Match Date
            date_m = re.search(r'Date\s*:\s*([0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{2}/[0-9]{2}/[0-9]{4})', meta_text)
            if date_m:
                date_str = date_m.group(1)

            # Match Version from filename or text
            ver_m = re.search(r'(GTD_|EVAO_)?([0-9]+\.[0-9]+(_[0-9]+)?)', fname)
            version = ver_m.group(2) if ver_m else "1.0"

            # Parse tables using pdfplumber
            tables_data = []
            with pdfplumber.open(pdf_path) as pdf:
                for p_idx, page in enumerate(pdf.pages):
                    tbls = page.extract_tables()
                    if tbls:
                        for t in tbls:
                            # Clean table rows
                            clean_tbl = []
                            for row in t:
                                if not row: continue
                                clean_row = [cell.replace('\n', ' ').strip() if cell else '' for cell in row]
                                if any(clean_row):
                                    clean_tbl.append(clean_row)
                            if len(clean_tbl) > 1:
                                tables_data.append((p_idx + 1, clean_tbl))

            bench_versions.append({
                'filename': fname,
                'path': pdf_path,
                'doc_ref': doc_ref,
                'version': version,
                'date': date_str,
                'num_pages': num_pages,
                'tables': tables_data
            })

        bench_data[bench_name] = bench_versions

    return bench_data

if __name__ == '__main__':
    reg_dir = '/media/vortigern/mlc2023b/tmp/cbrep-mkdocs-v1/docs/config_registers'
    out_dir = '/media/vortigern/mlc2023b/tmp/cbrep-mkdocs-v1/docs/configurations'
    bench_data = parse_config_registers(reg_dir, out_dir)
    print("PDF parsing completed successfully.")
