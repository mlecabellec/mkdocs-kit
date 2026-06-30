import unittest
import os
import shutil
import tempfile
import sys

# Ensure src/ is in python path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from mkdocs_kit.renderers import (
    render_plantuml,
    render_wireviz,
    render_rackdiag,
    render_packetdiag,
    render_bytefield,
)
from mkdocs_kit.man import convert_md_to_man
from mkdocs_kit.cli import main as cli_main

class TestDiagrams(unittest.TestCase):
    def test_plantuml(self):
        src = """
        @startuml
        Alice -> Bob: Hello
        @enduml
        """
        try:
            svg = render_plantuml(src)
            self.assertIn("<svg", svg)
            self.assertIn("Alice", svg)
            self.assertIn("Bob", svg)
        except Exception as e:
            self.fail(f"PlantUML rendering failed: {e}")

    def test_wireviz(self):
        src = """
        connectors:
          A:
            type: DB9
        """
        try:
            svg = render_wireviz(src)
            self.assertIn("<svg", svg)
        except Exception as e:
            self.fail(f"WireViz rendering failed: {e}")

    def test_rackdiag(self):
        src = """
        rackdiag {
          rack {
            1: Server;
          }
        }
        """
        try:
            svg = render_rackdiag(src)
            self.assertIn("<svg", svg)
            self.assertIn("Server", svg)
        except Exception as e:
            self.fail(f"RackDiag rendering failed: {e}")

    def test_packetdiag(self):
        src = """
        packetdiag {
          colwidth = 32;
          0-15: Source Port;
        }
        """
        try:
            svg = render_packetdiag(src)
            self.assertIn("<svg", svg)
            self.assertIn("Source Port", svg)
        except Exception as e:
            self.fail(f"PacketDiag rendering failed: {e}")

    def test_bytefield_lisp(self):
        src = """
        (bytefield
          (draw-box "Type" 8)
        )
        """
        try:
            svg = render_bytefield(src)
            self.assertIn("<svg", svg)
            self.assertIn("Type", svg)
        except Exception as e:
            self.fail(f"ByteField Lisp rendering failed: {e}")

    def test_bytefield_yaml(self):
        src = """
        - name: Type
          bits: 8
        """
        try:
            svg = render_bytefield(src)
            self.assertIn("<svg", svg)
            self.assertIn("Type", svg)
        except Exception as e:
            self.fail(f"ByteField YAML rendering failed: {e}")

class TestManPage(unittest.TestCase):
    def test_convert_md_to_man(self):
        md = """---
title: testtool
section: 1
description: A test tool
---
# TESTTOOL(1) - A test tool
## DESCRIPTION
This is a **bold** and *italic* test with `code`.
"""
        man, name, section = convert_md_to_man(md, "testtool")
        self.assertEqual(name, "testtool")
        self.assertEqual(section, "1")
        self.assertIn(".TH TESTTOOL 1", man)
        self.assertIn("testtool \\- A test tool", man)
        self.assertIn("\\fBbold\\fR", man)
        self.assertIn("\\fIitalic\\fR", man)
        self.assertIn("\\fBcode\\fR", man)

class TestCliAndPipeline(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_init_and_build(self):
        orig_argv = sys.argv
        try:
            # Test init
            sys.argv = ["mkdocs-kit", "init", self.tmpdir]
            cli_main()
            self.assertTrue(os.path.exists(os.path.join(self.tmpdir, "mkdocs.yml")))
            self.assertTrue(os.path.exists(os.path.join(self.tmpdir, "docs", "index.md")))
            self.assertTrue(os.path.exists(os.path.join(self.tmpdir, "docs", "diagrams.md")))
            
            # Test build
            sys.argv = ["mkdocs-kit", "build", "-c", os.path.join(self.tmpdir, "mkdocs.yml")]
            cli_main()
            self.assertTrue(os.path.exists(os.path.join(self.tmpdir, "site", "index.html")))
            self.assertTrue(os.path.exists(os.path.join(self.tmpdir, "documentation.pdf")))
            self.assertTrue(os.path.exists(os.path.join(self.tmpdir, "man", "man1", "mytool.1")))
        finally:
            sys.argv = orig_argv

if __name__ == "__main__":
    unittest.main()
