import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from mkdocs_kit.cli import main as cli_main
from mkdocs_kit.pdf import build_page_anchor_id, rewrite_internal_pdf_links


class TestPdfInternalLinks(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="mkdocs_kit_pdf_links_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_rewrite_internal_pdf_links_basic_and_fragments(self):
        used_ids = set()
        id_index = build_page_anchor_id("index.html", used_ids)
        id_sub = build_page_anchor_id("sub/target.html", used_ids)
        id_dir = build_page_anchor_id("guide/index.html", used_ids)

        page_map = {
            "index.html": id_index,
            ".": id_index,
            "./": id_index,
            "sub/target.html": id_sub,
            "guide/index.html": id_dir,
            "guide": id_dir,
            "guide/": id_dir,
        }

        html = (
            f'<section id="{id_index}">'
            f'<h2 id="overview">Overview</h2>'
            f'<a href="sub/target.html">Target</a>'
            f'<a href="sub/target.html#unique-sec">Unique</a>'
            f'<a href="sub/target.html#overview">DupHeading</a>'
            f'<a href="guide/">Guide</a>'
            f'<a href="#overview">SelfAnchor</a>'
            f'<a href="https://example.com">External</a>'
            f'<a data-href="sub/target.html" href="index.html">DataAttr</a>'
            f'</section>'
            f'<section id="{id_sub}">'
            f'<h2 id="overview">Overview</h2>'
            f'<h3 id="unique-sec">Unique</h3>'
            f'<a href="index.html">Back</a>'
            f'</section>'
        )

        rewritten = rewrite_internal_pdf_links(html, page_map)

        self.assertIn(f'href="#{id_sub}"', rewritten)
        self.assertIn('href="#unique-sec"', rewritten)
        # Duplicate heading #overview must fall back to target page section ID
        self.assertNotIn('href="#overview">DupHeading', rewritten)
        self.assertIn(f'href="#{id_sub}">DupHeading', rewritten)
        self.assertIn(f'href="#{id_dir}"', rewritten)
        self.assertIn('href="#overview">SelfAnchor', rewritten)
        self.assertIn('href="https://example.com"', rewritten)
        self.assertIn('data-href="sub/target.html"', rewritten)
        self.assertIn(f'href="#{id_index}"', rewritten)

    def test_end_to_end_pdf_has_no_filesystem_uris_and_preserves_html(self):
        docs_dir = os.path.join(self.test_dir, "docs")
        sub_dir = os.path.join(docs_dir, "sub")
        os.makedirs(sub_dir, exist_ok=True)

        with open(os.path.join(self.test_dir, "mkdocs.yml"), "w", encoding="utf-8") as f:
            f.write(
                "site_name: Link Test\n"
                "use_directory_urls: false\n"
                "nav:\n"
                "  - Home: index.md\n"
                "  - SubPage: sub/target.md\n"
            )

        with open(os.path.join(docs_dir, "index.md"), "w", encoding="utf-8") as f:
            f.write(
                "# Home\n\n"
                "Go to [Target Page](sub/target.md) or [External](https://example.com).\n"
            )

        with open(os.path.join(sub_dir, "target.md"), "w", encoding="utf-8") as f:
            f.write(
                "# Target Page\n\n"
                "Back to [Home](../index.md).\n"
            )

        pdf_out = os.path.join(self.test_dir, "documentation.pdf")
        old_cwd = os.getcwd()
        try:
            os.chdir(self.test_dir)
            with patch.object(sys, "argv", ["mkdocs-kit", "build", "--pdf-output", pdf_out]):
                cli_main()
        finally:
            os.chdir(old_cwd)

        self.assertTrue(os.path.exists(pdf_out))

        # Verify HTML on disk still has relative file links (other medium preserved)
        with open(os.path.join(self.test_dir, "site", "index.html"), "r", encoding="utf-8") as f:
            site_index_html = f.read()
        self.assertIn('href="sub/target.html"', site_index_html)

        with open(os.path.join(self.test_dir, "site", "sub", "target.html"), "r", encoding="utf-8") as f:
            site_target_html = f.read()
        self.assertIn('href="../index.html"', site_target_html)

        # Verify PDF annotations via mutool if installed
        if shutil.which("mutool"):
            res = subprocess.run(
                ["mutool", "show", pdf_out, "grep", "URI"],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertNotIn("file://", res.stdout)
            self.assertIn("https://example.com", res.stdout)

            res_dest = subprocess.run(
                ["mutool", "show", pdf_out, "grep", "Dest"],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("/Dest", res_dest.stdout)

    def test_directory_urls_deep_nesting_and_edge_cases(self):
        docs_dir = os.path.join(self.test_dir, "docs")
        deep_dir = os.path.join(docs_dir, "a", "b", "c")
        other_dir = os.path.join(docs_dir, "x")
        os.makedirs(deep_dir, exist_ok=True)
        os.makedirs(other_dir, exist_ok=True)

        with open(os.path.join(self.test_dir, "mkdocs.yml"), "w", encoding="utf-8") as f:
            f.write(
                "site_name: Directory URL Test\n"
                "use_directory_urls: true\n"
                "nav:\n"
                "  - Home: index.md\n"
                "  - Deep: a/b/c/deep.md\n"
                "  - Target: x/y.md\n"
            )

        with open(os.path.join(docs_dir, "index.md"), "w", encoding="utf-8") as f:
            f.write("# Home\n\nSee [Deep](a/b/c/deep.md) and [LocalFile](file:///tmp/demo.txt).\n")

        with open(os.path.join(deep_dir, "deep.md"), "w", encoding="utf-8") as f:
            f.write("# Deep Page\n\nJump to [Target](../../../x/y.md#unique-section) or [Home](../../../index.md).\n")

        with open(os.path.join(other_dir, "y.md"), "w", encoding="utf-8") as f:
            f.write("# Target Y\n\n## Unique Section\n\nBack to [Deep](../a/b/c/deep.md).\n")

        pdf_out = os.path.join(self.test_dir, "documentation.pdf")
        old_cwd = os.getcwd()
        try:
            os.chdir(self.test_dir)
            with patch.object(sys, "argv", ["mkdocs-kit", "build", "--pdf-output", pdf_out]):
                cli_main()
        finally:
            os.chdir(old_cwd)

        self.assertTrue(os.path.exists(pdf_out))
        if shutil.which("mutool"):
            res = subprocess.run(
                ["mutool", "show", pdf_out, "grep", "URI"],
                capture_output=True,
                text=True,
                check=True,
            )
            # Only the explicit file:///tmp/demo.txt should be a file:// URI, never site/ paths
            self.assertNotIn("site/", res.stdout)
            self.assertIn("file:///tmp/demo.txt", res.stdout)

    def test_stress_200_pages_1000_links_and_svg_preservation(self):
        used_ids = set()
        page_map = {}
        sections = []
        num_pages = 200

        for i in range(num_pages):
            rel_path = f"pkg_{i // 20}/page_{i}.html"
            sec_id = build_page_anchor_id(rel_path, used_ids)
            page_map[rel_path] = sec_id

        for i in range(num_pages):
            rel_path = f"pkg_{i // 20}/page_{i}.html"
            sec_id = page_map[rel_path]
            links = []
            for j in range(5):
                target_idx = (i + j + 1) % num_pages
                target_rel = f"pkg_{target_idx // 20}/page_{target_idx}.html"
                links.append(f'<a href="{target_rel}">Link {j}</a>')
            links.append(f'<a HREF="pkg_{((i + 1) % num_pages) // 20}/page_{(i + 1) % num_pages}.html#overview">Dup</a>')
            links.append(f'<a href="pkg_0/page_0.html#unique-0">Unique</a>')
            links.append('<a href="mailto:test@example.com">Mail</a>')
            links.append('<a href="">Empty</a>')
            svg = '<svg><defs><clipPath id="clip0"><rect width="10" height="10"/></clipPath></defs><g clip-path="url(#clip0)"/></svg>'
            sections.append(
                f'<section id="{sec_id}"><h2 id="overview">Overview</h2>'
                f'<h3 id="unique-{i}">U{i}</h3>{"".join(links)}{svg}</section>'
            )

        body = "".join(sections)
        rewritten = rewrite_internal_pdf_links(body, page_map)

        # Verify all 1000 cross-page links were rewritten and no .html hrefs remain
        self.assertNotIn('.html"', rewritten)
        self.assertIn('href="#unique-0"', rewritten)
        self.assertIn('href="mailto:test@example.com"', rewritten)
        self.assertIn('href=""', rewritten)
        self.assertIn('clip-path="url(#clip0)"', rewritten)


if __name__ == "__main__":
    unittest.main()
