import os
import sys
import time

class BuildReporter:
    def __init__(self, log_file_path="mkdocs-kit.log", verbose=True):
        self.log_file_path = log_file_path
        self.verbose = verbose
        self.pages = []        # dict: {file, status, warnings, errors, duration}
        self.diagrams = []     # dict: {type, page, status, detail, duration}
        self.links = []        # dict: {page, target, text, status, detail}
        self.pdf_issues = []   # dict: {type, page, detail}
        self.start_time = time.time()
        self._log_fp = None
        self._init_log_file()

    def _init_log_file(self):
        try:
            log_dir = os.path.dirname(self.log_file_path)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            self._log_fp = open(self.log_file_path, "w", encoding="utf-8")
            self.log(f"=== MkDocs Kit Build Session Started: {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
        except Exception as e:
            sys.stderr.write(f"Warning: Could not initialize log file '{self.log_file_path}': {e}\n")

    def log(self, message="", to_console=True):
        timestamp = time.strftime("[%H:%M:%S]")
        formatted = f"{timestamp} {message}" if message else ""
        if to_console and self.verbose:
            print(formatted)
        if self._log_fp:
            try:
                self._log_fp.write(formatted + "\n")
                self._log_fp.flush()
            except Exception:
                pass

    def warn(self, message, category="GENERAL"):
        msg = f"[WARNING][{category}] {message}"
        self.log(msg)

    def error(self, message, category="GENERAL"):
        msg = f"[ERROR][{category}] {message}"
        self.log(msg)

    def progress(self, current_step, total_steps, title, done_tasks=None, ongoing_task=None, upcoming_tasks=None):
        self.log("")
        self.log(f"==================================================")
        self.log(f" Progress [{current_step}/{total_steps}]: {title}")
        self.log(f"==================================================")
        if done_tasks:
            for task in done_tasks:
                self.log(f"  [DONE]     {task}")
        if ongoing_task:
            self.log(f"  [ONGOING]  {ongoing_task}")
        if upcoming_tasks:
            for task in upcoming_tasks:
                self.log(f"  [UPCOMING] {task}")
        self.log(f"--------------------------------------------------")

    def record_page(self, file_path, status="SUCCESS", warnings=None, errors=None, duration=0.0):
        self.pages.append({
            "file": file_path,
            "status": status,
            "warnings": warnings or [],
            "errors": errors or [],
            "duration": duration
        })

    def record_diagram(self, diag_type, page, status="SUCCESS", detail="", duration=0.0):
        self.diagrams.append({
            "type": diag_type,
            "page": page,
            "status": status,
            "detail": detail,
            "duration": duration
        })

    def record_link(self, page, target, text, status, detail=""):
        self.links.append({
            "page": page,
            "target": target,
            "text": text,
            "status": status,
            "detail": detail
        })

    def record_pdf_issue(self, issue_type, page, detail):
        self.pdf_issues.append({
            "type": issue_type,
            "page": page,
            "detail": detail
        })

    def print_summary_reports(self):
        total_duration = time.time() - self.start_time
        
        self.log("")
        self.log("================================================================================")
        self.log("                        MKDOCS KIT BUILD SUMMARY REPORT                         ")
        self.log("================================================================================")

        # 1. Page Status Report
        self.log("")
        self.log("--- 📄 PAGE PROCESSING REPORT ---")
        if not self.pages:
            self.log("  No pages processed.")
        else:
            self.log(f"  {'STATUS':<10} | {'DURATION':<8} | {'PAGE FILE':<40} | {'NOTES'}")
            self.log(f"  {'-'*10}-+-{'-'*8}-+-{'-'*40}-+-{'-'*15}")
            for p in self.pages:
                notes = ""
                if p["errors"]:
                    notes = f"ERRORS: {len(p['errors'])}"
                elif p["warnings"]:
                    notes = f"WARNINGS: {len(p['warnings'])}"
                self.log(f"  {p['status']:<10} | {p['duration']:>6.2f}s | {p['file']:<40} | {notes}")

        # 2. Diagram Processing Report
        self.log("")
        self.log("--- 📊 DIAGRAM RENDERING REPORT ---")
        if not self.diagrams:
            self.log("  No diagrams processed.")
        else:
            self.log(f"  {'STATUS':<10} | {'TYPE':<12} | {'PAGE':<35} | {'DETAIL/ERROR'}")
            self.log(f"  {'-'*10}-+-{'-'*12}-+-{'-'*35}-+-{'-'*20}")
            for d in self.diagrams:
                detail_str = d["detail"] if d["detail"] else "Rendered successfully"
                self.log(f"  {d['status']:<10} | {d['type']:<12} | {d['page']:<35} | {detail_str}")

        # 3. Link Inspection Report
        self.log("")
        self.log("--- 🔗 LINK VALIDATION & DIRECTORY REPORT ---")
        if not self.links:
            self.log("  No links analyzed.")
        else:
            self.log(f"  {'STATUS':<18} | {'PAGE':<30} | {'TARGET LINK':<30} | {'DETAIL'}")
            self.log(f"  {'-'*18}-+-{'-'*30}-+-{'-'*30}-+-{'-'*20}")
            for l in self.links:
                self.log(f"  {l['status']:<18} | {l['page']:<30} | {l['target']:<30} | {l['detail']}")

        # 4. PDF Issues Report
        if self.pdf_issues:
            self.log("")
            self.log("--- 🖨️ PDF GENERATION WARNINGS & ISSUES ---")
            self.log(f"  {'ISSUE TYPE':<22} | {'PAGE':<30} | {'DETAILS'}")
            self.log(f"  {'-'*22}-+-{'-'*30}-+-{'-'*30}")
            for item in self.pdf_issues:
                self.log(f"  {item['type']:<22} | {item['page']:<30} | {item['detail']}")

        self.log("")
        self.log(f"Total build time: {total_duration:.2f} seconds.")
        self.log(f"Log written to: {os.path.abspath(self.log_file_path)}")
        self.log("================================================================================")

    def close(self):
        if self._log_fp:
            try:
                self._log_fp.close()
            except Exception:
                pass
            self._log_fp = None
