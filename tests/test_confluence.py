import unittest
import tempfile
import os
import shutil
import zipfile
import json
import xml.etree.ElementTree as ET
from mkdocs_kit.confluence_exporter import export_confluence_package, _html_to_confluence_storage_format
from mkdocs_kit.reporter import BuildReporter


class TestConfluenceExporter(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.site_dir = os.path.join(self.tmpdir, 'site')
        os.makedirs(self.site_dir, exist_ok=True)
        self.config_path = os.path.join(self.tmpdir, 'mkdocs.yml')

        with open(self.config_path, 'w', encoding='utf-8') as f:
            f.write(
                "site_name: Space Mission Docs\n"
                "nav:\n"
                "  - Home: index.md\n"
                "  - Architecture: arch.md\n"
            )

        index_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Home - Space Mission Docs</title></head>
        <body>
            <div role="main">
                <h1>Mission Control Home</h1>
                <p>Welcome to telemetry dashboard documentation. See <a href="arch.md">Architecture Overview</a>.</p>
                <div class="admonition note">
                    <p class="admonition-title">Operational Notice</p>
                    <p>All telemetry streams operate in real-time.</p>
                </div>
            </div>
        </body>
        </html>
        """
        with open(os.path.join(self.site_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(index_html)

        arch_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Architecture Overview - Space Mission Docs</title></head>
        <body>
            <article>
                <h1>Architecture Overview</h1>
                <p>Core server infrastructure.</p>
                
                <div class="admonition warning">
                    <p class="admonition-title">Security Alert</p>
                    <p>Encryption required on port 4840.</p>
                </div>

                <div class="codehilite"><pre><code class="language-yaml">server:
  port: 8080
  name: Nunki</code></pre></div>

                <details>
                    <summary>Hardware Specs</summary>
                    <p>Redundant power supply units configured.</p>
                </details>

                <svg width="150" height="75" viewBox="0 0 150 75" xmlns="http://www.w3.org/2000/svg">
                    <rect width="150" height="75" fill="#3B82F6"/>
                    <text x="30" y="40" fill="#FFFFFF">Telemetry</text>
                </svg>
            </article>
        </body>
        </html>
        """
        with open(os.path.join(self.site_dir, 'arch.html'), 'w', encoding='utf-8') as f:
            f.write(arch_html)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_confluence_export_dual_mode(self):
        out_zip = os.path.join(self.tmpdir, 'confluence-dual.zip')
        reporter = BuildReporter(log_file_path=os.path.join(self.tmpdir, 'conf.log'), verbose=False)

        res_path = export_confluence_package(
            self.site_dir,
            self.config_path,
            out_zip,
            space_key="SPACEMISS",
            space_name="Space Mission",
            package_format="dual",
            reporter=reporter
        )
        reporter.close()

        self.assertTrue(os.path.exists(res_path))
        self.assertTrue(zipfile.is_zipfile(res_path))

        with zipfile.ZipFile(res_path, 'r') as zf:
            namelist = zf.namelist()
            
            # Verify Space Backup members
            self.assertIn("exportDescriptor.properties", namelist)
            self.assertIn("entities.xml", namelist)

            # Verify REST bundle members
            self.assertIn("manifest.json", namelist)
            self.assertTrue(any(name.startswith("pages/") and name.endswith(".xhtml") for name in namelist))
            self.assertTrue(any(name.startswith("attachments/") for name in namelist))

            # Inspect exportDescriptor.properties
            desc = zf.read("exportDescriptor.properties").decode('utf-8')
            self.assertIn("exportType=space", desc)
            self.assertIn("spaceKey=SPACEMISS", desc)
            self.assertIn("spaceName=Space Mission", desc)

            # Inspect entities.xml validity
            entities_xml = zf.read("entities.xml").decode('utf-8')
            self.assertIn('<object class="Space"', entities_xml)
            self.assertIn('<property name="key"><![CDATA[SPACEMISS]]></property>', entities_xml)
            self.assertIn('<object class="BodyContent"', entities_xml)
            self.assertIn('<object class="Page"', entities_xml)
            self.assertIn('<object class="Attachment"', entities_xml)

            # Validate entities.xml well-formedness
            root = ET.fromstring(entities_xml)
            self.assertEqual(root.tag, 'hibernate-generic')

            # Inspect manifest.json
            manifest_str = zf.read("manifest.json").decode('utf-8')
            manifest = json.loads(manifest_str)
            self.assertEqual(manifest["spaceKey"], "SPACEMISS")
            self.assertEqual(len(manifest["pages"]), 2)
            self.assertEqual(manifest["pages"][0]["title"], "Home")

    def test_html_to_confluence_storage_format_macros(self):
        sample_html = """
        <div>
            <h1>Header Title</h1>
            <div class="admonition tip">
                <p class="admonition-title">Pro Tip</p>
                <p>Use keyboard shortcuts for rapid navigation.</p>
            </div>
            <div class="codehilite"><pre><code class="language-python">x = 42</code></pre></div>
            <details>
                <summary>Click to view</summary>
                <p>Hidden body text.</p>
            </details>
            <p>Visit <a href="arch.md">Architecture</a>.</p>
        </div>
        """
        title_map = {"arch.md": "Architecture Overview"}
        csf, atts = _html_to_confluence_storage_format(sample_html, 100001, self.site_dir, [], title_map)

        # Check macro transformations
        self.assertIn('<ac:structured-macro ac:name="tip">', csf)
        self.assertIn('<ac:parameter ac:name="title">Pro Tip</ac:parameter>', csf)
        self.assertIn('<ac:structured-macro ac:name="code">', csf)
        self.assertIn('<ac:parameter ac:name="language">python</ac:parameter>', csf)
        self.assertIn('<![CDATA[x = 42]]>', csf)
        self.assertIn('<ac:structured-macro ac:name="expand">', csf)
        self.assertIn('<ac:link>', csf)
        self.assertIn('<ri:page ri:content-title="Architecture Overview"/>', csf)


if __name__ == '__main__':
    unittest.main()
