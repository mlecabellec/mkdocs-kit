import unittest
import os
import shutil
import tempfile
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from mkdocs_kit.reporter import BuildReporter
from mkdocs_kit.link_checker import check_links_in_markdown
from mkdocs_kit.pdf import inspect_missing_files_in_html, inspect_svg_bounding_boxes
from mkdocs_kit.cli import main as cli_main

class TestReporterAndDiagnostics(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.tmpdir, "test_build.log")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_build_reporter_logging_and_summary(self):
        reporter = BuildReporter(log_file_path=self.log_file, verbose=False)
        reporter.progress(1, 4, "Testing Progress", done_tasks=["Task 1"], ongoing_task="Task 2", upcoming_tasks=["Task 3"])
        reporter.record_page("index.md", status="SUCCESS", duration=0.15)
        reporter.record_diagram("plantuml", "index.md", status="SUCCESS", detail="Rendered SVG", duration=0.25)
        reporter.record_link("index.md", "subfolder/", "Folder Link", status="WARNING_DIRECTORY", detail="Points to directory")
        reporter.record_pdf_issue("BOUNDING_BOX_OVERFLOW", "diagrams.md", "Diagram width exceeds page width")
        reporter.print_summary_reports()
        reporter.close()

        self.assertTrue(os.path.exists(self.log_file))
        with open(self.log_file, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("MKDOCS KIT BUILD SUMMARY REPORT", content)
        self.assertIn("PAGE PROCESSING REPORT", content)
        self.assertIn("DIAGRAM RENDERING REPORT", content)
        self.assertIn("LINK VALIDATION & DIRECTORY REPORT", content)
        self.assertIn("PDF GENERATION WARNINGS & ISSUES", content)
        self.assertIn("index.md", content)
        self.assertIn("plantuml", content)
        self.assertIn("WARNING_DIRECTORY", content)
        self.assertIn("BOUNDING_BOX_OVERFLOW", content)

    def test_link_checker_directory_warning(self):
        docs_dir = os.path.join(self.tmpdir, "docs")
        sub_dir = os.path.join(docs_dir, "subfolder")
        os.makedirs(sub_dir, exist_ok=True)
        page_file = os.path.join(docs_dir, "test.md")

        reporter = BuildReporter(log_file_path=self.log_file, verbose=False)

        # Markdown containing explicit directory link (trailing slash) and disk directory target
        md_content = """
        [Directory Slash Link](subfolder/)
        [Directory Disk Link](subfolder)
        [Valid File Link](test.md)
        """
        has_dir_warn = check_links_in_markdown(md_content, page_file, docs_dir, reporter)
        reporter.close()

        self.assertTrue(has_dir_warn)
        self.assertEqual(len(reporter.links), 3)

        dir_links = [l for l in reporter.links if l["status"] == "WARNING_DIRECTORY"]
        self.assertEqual(len(dir_links), 2)
        self.assertEqual(dir_links[0]["target"], "subfolder/")
        self.assertEqual(dir_links[1]["target"], "subfolder")

    def test_pdf_diagnostics_missing_files_and_bounding_box(self):
        reporter = BuildReporter(log_file_path=self.log_file, verbose=False)

        # HTML with missing image asset and oversized SVG
        html_content = """
        <html>
        <body>
            <img src="images/missing_photo.png">
            <div class="diagram-plantuml">
                <svg width="1200px" height="600px" viewBox="0 0 1200 600">
                    <rect width="1200" height="600"/>
                </svg>
            </div>
        </body>
        </html>
        """
        inspect_missing_files_in_html(html_content, self.tmpdir, "test_page.html", reporter)
        inspect_svg_bounding_boxes(html_content, "test_page.html", reporter)
        reporter.close()

        missing_issues = [i for i in reporter.pdf_issues if i["type"] == "MISSING_FILE"]
        bbox_issues = [i for i in reporter.pdf_issues if i["type"] == "BOUNDING_BOX_OVERFLOW"]

        self.assertTrue(len(missing_issues) >= 1)
        self.assertIn("missing_photo.png", missing_issues[0]["detail"])

        self.assertTrue(len(bbox_issues) >= 1)
        self.assertIn("1200px", bbox_issues[0]["detail"])

    def test_cli_full_build_execution_with_log_file(self):
        orig_argv = sys.argv
        try:
            # Init project
            sys.argv = ["mkdocs-kit", "init", self.tmpdir]
            cli_main()

            log_path = os.path.join(self.tmpdir, "mkdocs-kit.log")

            # Build project with --log-file
            sys.argv = ["mkdocs-kit", "build", "-c", os.path.join(self.tmpdir, "mkdocs.yml"), "-l", log_path]
            cli_main()

            self.assertTrue(os.path.exists(log_path))
            with open(log_path, "r", encoding="utf-8") as f:
                log_text = f.read()

            self.assertIn("Progress [1/4]", log_text)
            self.assertIn("Progress [4/4]", log_text)
            self.assertIn("MKDOCS KIT BUILD SUMMARY REPORT", log_text)
            self.assertIn("PAGE PROCESSING REPORT", log_text)
            self.assertIn("DIAGRAM RENDERING REPORT", log_text)
        finally:
            sys.argv = orig_argv

if __name__ == "__main__":
    unittest.main()
