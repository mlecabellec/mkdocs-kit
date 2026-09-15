import unittest
import tempfile
import os
import shutil
import zipfile
import xml.etree.ElementTree as ET
import docx
from mkdocs_kit.docx_generator import generate_docx, _rasterize_svg, _format_inline_html
from mkdocs_kit.reporter import BuildReporter


class TestDocxGenerator(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.site_dir = os.path.join(self.tmpdir, 'site')
        os.makedirs(self.site_dir, exist_ok=True)
        self.config_path = os.path.join(self.tmpdir, 'mkdocs.yml')

        # Create a sample mkdocs.yml
        with open(self.config_path, 'w', encoding='utf-8') as f:
            f.write(
                "site_name: Test DOCX Project\n"
                "site_description: Comprehensive testing for Word document generator\n"
                "site_author: Test Author\n"
                "nav:\n"
                "  - Home: index.md\n"
                "  - Features: features.md\n"
            )

        # Create sample HTML pages in site_dir
        index_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Home - Test DOCX Project</title></head>
        <body>
            <div role="main">
                <h1>Welcome to Test Project</h1>
                <p>This is a <b>bold</b>, <i>italic</i>, and <code>inline code</code> paragraph with a <a href="https://example.com">hyperlink</a>.</p>
                
                <h2>Section 1: Lists & Code</h2>
                <ul>
                    <li>First bullet item with <b>bold</b></li>
                    <li>Second bullet item</li>
                </ul>
                <ol>
                    <li>First numbered step</li>
                    <li>Second numbered step</li>
                </ol>
                
                <pre><code class="language-python">def hello_world():
    print("Hello, DOCX!")</code></pre>
            </div>
        </body>
        </html>
        """
        with open(os.path.join(self.site_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(index_html)

        features_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Features - Test DOCX Project</title></head>
        <body>
            <article>
                <h1>Detailed Features</h1>
                <p>Overview of all system capabilities.</p>
                
                <div class="admonition note">
                    <p class="admonition-title">Important Note</p>
                    <p>Admonition note body text explaining key details.</p>
                </div>

                <div class="admonition warning">
                    <p class="admonition-title">Security Warning</p>
                    <p>Please exercise caution when configuring credentials.</p>
                </div>

                <h2>Data Table</h2>
                <table>
                    <thead>
                        <tr><th>ID</th><th>Component</th><th>Status</th></tr>
                    </thead>
                    <tbody>
                        <tr><td>1</td><td>Gateway</td><td>Online</td></tr>
                        <tr><td>2</td><td>Database</td><td>Standby</td></tr>
                    </tbody>
                </table>

                <h2>Vector Diagram</h2>
                <svg width="200" height="100" viewBox="0 0 200 100" xmlns="http://www.w3.org/2000/svg">
                    <rect x="10" y="10" width="180" height="80" fill="#E2E8F0" stroke="#004B87" stroke-width="2"/>
                    <text x="50" y="55" fill="#000000" font-family="sans-serif" font-size="14">Sample Box</text>
                </svg>

                <hr/>
                <details>
                    <summary>More Info</summary>
                    <p>Expanded detail paragraph.</p>
                </details>
            </article>
        </body>
        </html>
        """
        with open(os.path.join(self.site_dir, 'features.html'), 'w', encoding='utf-8') as f:
            f.write(features_html)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_generate_docx_basic(self):
        out_docx = os.path.join(self.tmpdir, 'output.docx')
        reporter = BuildReporter(log_file_path=os.path.join(self.tmpdir, 'build.log'), verbose=False)
        
        result_path = generate_docx(self.site_dir, self.config_path, out_docx, reporter=reporter)
        reporter.close()

        self.assertTrue(os.path.exists(result_path))
        self.assertGreater(os.path.getsize(result_path), 5000)

        # Inspect generated docx
        doc = docx.Document(result_path)
        
        # Verify headings
        headings = [p.text for p in doc.paragraphs if p.style.name.startswith('Heading')]
        self.assertIn("Table of Contents", headings)
        self.assertIn("Welcome to Test Project", headings)
        self.assertIn("Section 1: Lists & Code", headings)
        self.assertIn("Detailed Features", headings)

        # Verify tables (TOC / Callouts / Data Tables)
        self.assertGreaterEqual(len(doc.tables), 3)

        # Verify cover page text
        full_text = "\n".join(p.text for p in doc.paragraphs)
        self.assertIn("Test DOCX Project", full_text)
        self.assertIn("Comprehensive testing for Word document generator", full_text)
        self.assertIn("Author: Test Author", full_text)

    def test_docx_diagram_rasterization(self):
        svg = '<svg width="100" height="50" xmlns="http://www.w3.org/2000/svg"><rect width="100" height="50" fill="blue"/></svg>'
        res = _rasterize_svg(svg, dpi=150)
        self.assertIsNotNone(res)
        png_bytes, width_in = res
        self.assertGreater(len(png_bytes), 50)
        # Check PNG magic bytes \x89PNG
        self.assertEqual(png_bytes[:4], b'\x89PNG')

    def test_docx_table_content_and_styles(self):
        out_docx = os.path.join(self.tmpdir, 'table_test.docx')
        generate_docx(self.site_dir, self.config_path, out_docx)

        doc = docx.Document(out_docx)
        # Find the 3-column data table
        data_table = None
        for tbl in doc.tables:
            if len(tbl.columns) == 3:
                data_table = tbl
                break

        self.assertIsNotNone(data_table)
        headers = [c.text.strip() for c in data_table.rows[0].cells]
        self.assertEqual(headers, ["ID", "Component", "Status"])

        row1 = [c.text.strip() for c in data_table.rows[1].cells]
        self.assertEqual(row1, ["1", "Gateway", "Online"])


if __name__ == '__main__':
    unittest.main()
