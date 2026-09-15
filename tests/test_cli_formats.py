import unittest
import os
import shutil
import tempfile
import sys
import zipfile
import docx

# Ensure src/ is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from mkdocs_kit.cli import main as cli_main


class TestCliFormats(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        orig_argv = sys.argv
        try:
            sys.argv = ["mkdocs-kit", "init", self.tmpdir]
            cli_main()
        finally:
            sys.argv = orig_argv

        self.config_path = os.path.join(self.tmpdir, "mkdocs.yml")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_cli_docx_output(self):
        docx_path = os.path.join(self.tmpdir, "output.docx")
        orig_argv = sys.argv
        try:
            sys.argv = [
                "mkdocs-kit", "build",
                "-c", self.config_path,
                "--docx-output", docx_path,
                "-v"
            ]
            cli_main()
        finally:
            sys.argv = orig_argv

        self.assertTrue(os.path.exists(docx_path))
        doc = docx.Document(docx_path)
        # Verify paragraphs exist and site title is present
        text_content = "\n".join(p.text for p in doc.paragraphs)
        self.assertIn("My Documentation Kit", text_content)

    def test_cli_confluence_output_dual(self):
        conf_zip = os.path.join(self.tmpdir, "confluence-export.zip")
        orig_argv = sys.argv
        try:
            sys.argv = [
                "mkdocs-kit", "build",
                "-c", self.config_path,
                "--confluence-output", conf_zip,
                "--confluence-space-key", "TESTCLI",
                "--confluence-space-name", "Test CLI Space",
                "--confluence-format", "dual",
                "-v"
            ]
            cli_main()
        finally:
            sys.argv = orig_argv

        self.assertTrue(os.path.exists(conf_zip))
        self.assertTrue(zipfile.is_zipfile(conf_zip))
        with zipfile.ZipFile(conf_zip, 'r') as zf:
            namelist = zf.namelist()
            self.assertIn("entities.xml", namelist)
            self.assertIn("exportDescriptor.properties", namelist)
            self.assertIn("manifest.json", namelist)

    def test_cli_confluence_output_rest_bundle(self):
        conf_zip = os.path.join(self.tmpdir, "confluence-rest.zip")
        orig_argv = sys.argv
        try:
            sys.argv = [
                "mkdocs-kit", "build",
                "-c", self.config_path,
                "--confluence-output", conf_zip,
                "--confluence-format", "rest-bundle",
                "-v"
            ]
            cli_main()
        finally:
            sys.argv = orig_argv

        self.assertTrue(os.path.exists(conf_zip))
        with zipfile.ZipFile(conf_zip, 'r') as zf:
            namelist = zf.namelist()
            self.assertIn("manifest.json", namelist)
            self.assertNotIn("entities.xml", namelist)

    def test_cli_all_formats_simultaneously(self):
        docx_path = os.path.join(self.tmpdir, "multi.docx")
        conf_zip = os.path.join(self.tmpdir, "multi.zip")
        pdf_path = os.path.join(self.tmpdir, "multi.pdf")
        orig_argv = sys.argv
        try:
            sys.argv = [
                "mkdocs-kit", "build",
                "-c", self.config_path,
                "--pdf-output", pdf_path,
                "--docx-output", docx_path,
                "--confluence-output", conf_zip,
                "-v"
            ]
            cli_main()
        finally:
            sys.argv = orig_argv

        self.assertTrue(os.path.exists(pdf_path))
        self.assertTrue(os.path.exists(docx_path))
        self.assertTrue(os.path.exists(conf_zip))


if __name__ == "__main__":
    unittest.main()
