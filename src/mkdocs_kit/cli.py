import argparse
import sys
import os
import shutil
import time
import mkdocs.config
import mkdocs.utils
from mkdocs.commands.build import build as mkdocs_build
from mkdocs.commands.serve import serve as mkdocs_serve
from mkdocs_kit.pdf import generate_pdf
from mkdocs_kit.man import generate_man_pages
from mkdocs_kit.templates import MKDOCS_YML, INDEX_MD, DIAGRAMS_MD, MAN_MD_TEMPLATE
from mkdocs_kit.reporter import BuildReporter

# Monkey-patch mkdocs.config.load_config to automatically inject our diagrams plugin
original_load_config = mkdocs.config.load_config

active_reporter = None

def patched_load_config(*args, **kwargs):
    config = original_load_config(*args, **kwargs)
    from mkdocs_kit.plugin import DiagramsPlugin
    
    if active_reporter:
        config['reporter'] = active_reporter

    if 'mkdocs_kit_diagrams' not in config['plugins']:
        plugin = DiagramsPlugin(reporter=active_reporter)
        plugin.load_config({})
        config['plugins']['mkdocs_kit_diagrams'] = plugin
    else:
        # Update reporter on existing plugin instance
        plugin = config['plugins']['mkdocs_kit_diagrams']
        if hasattr(plugin, 'reporter'):
            plugin.reporter = active_reporter

    # Ensure theme palette includes light/dark mode switch if not explicitly defined as list
    if 'theme' in config and hasattr(config['theme'], 'palette'):
        palette = config['theme'].palette
        if not palette or not isinstance(palette, list):
            config['theme']['palette'] = [
                {
                    'scheme': 'slate',
                    'primary': 'indigo',
                    'accent': 'indigo',
                    'toggle': {
                        'icon': 'material/brightness-4',
                        'name': 'Switch to light mode'
                    }
                },
                {
                    'scheme': 'default',
                    'primary': 'indigo',
                    'accent': 'indigo',
                    'toggle': {
                        'icon': 'material/brightness-7',
                        'name': 'Switch to dark mode'
                    }
                }
            ]
    return config


mkdocs.config.load_config = patched_load_config

# Monkey-patch mkdocs.utils.get_themes to support the bundled 'material' theme under PyInstaller
original_get_themes = mkdocs.utils.get_themes

class MockMaterialEntryPoint:
    def __init__(self):
        self.name = 'material'
        self.value = 'material'
        self.group = 'mkdocs.themes'
    
    @property
    def dist(self):
        class MockDist:
            name = 'mkdocs-material'
        return MockDist()
        
    def load(self):
        import sys
        import os
        class MockModule:
            pass
        m = MockModule()
        if hasattr(sys, '_MEIPASS'):
            m.__file__ = os.path.join(sys._MEIPASS, 'material', 'templates', '__init__.py')
        else:
            import material.templates
            m.__file__ = material.templates.__file__
        return m

def patched_get_themes():
    themes = original_get_themes()
    themes_dict = dict(themes)
    if 'material' not in themes_dict:
        themes_dict['material'] = MockMaterialEntryPoint()
    return themes_dict

patched_get_themes.cache_clear = lambda: None

mkdocs.utils.get_themes = patched_get_themes


def cmd_init(args):
    target_dir = args.directory or '.'
    print(f"Initializing MkDocs Kit in '{target_dir}'...")
    
    os.makedirs(target_dir, exist_ok=True)
    docs_dir = os.path.join(target_dir, 'docs')
    man_dir = os.path.join(docs_dir, 'man')
    
    os.makedirs(docs_dir, exist_ok=True)
    os.makedirs(man_dir, exist_ok=True)
    
    def write_file(path, content):
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  Created {path}")
        else:
            print(f"  Skipped {path} (already exists)")

    write_file(os.path.join(target_dir, 'mkdocs.yml'), MKDOCS_YML)
    write_file(os.path.join(docs_dir, 'index.md'), INDEX_MD)
    write_file(os.path.join(docs_dir, 'diagrams.md'), DIAGRAMS_MD)
    write_file(os.path.join(man_dir, 'mytool.1.md'), MAN_MD_TEMPLATE)
    
    print("Initialization complete! Run 'mkdocs-kit build' to generate documentation.")

def cmd_build(args):
    global active_reporter
    config_file = args.config or 'mkdocs.yml'
    if not os.path.exists(config_file):
        print(f"Error: Config file '{config_file}' not found. Run 'mkdocs-kit init' first.")
        sys.exit(1)

    log_file = getattr(args, 'log_file', None) or 'mkdocs-kit.log'
    reporter = BuildReporter(log_file_path=log_file, verbose=True)
    active_reporter = reporter

    try:
        # Step 1: HTML, Markdown & Diagram Processing
        reporter.progress(
            current_step=1,
            total_steps=4,
            title="Processing Markdown Pages, Render Diagrams & Validate Links",
            done_tasks=[],
            ongoing_task=f"Parsing config '{config_file}', compiling Markdown files and inline diagrams",
            upcoming_tasks=["Compiling PDF Manual with WeasyPrint", "Generating UNIX Man Pages", "Publishing Summary Reports"]
        )

        config = mkdocs.config.load_config(config_file=config_file)
        site_dir = config.get('site_dir', 'site')
        docs_dir = config.get('docs_dir', 'docs')

        mkdocs_build(config)
        reporter.log(f"HTML build complete! Output directory: '{site_dir}'")

        # Step 2: Link & Directory Target Validation Summary
        reporter.progress(
            current_step=2,
            total_steps=4,
            title="Link & Directory Target Validation",
            done_tasks=["Compiled Markdown pages & diagrams"],
            ongoing_task="Validating internal/external links and directory reference targets",
            upcoming_tasks=["Compiling PDF Manual with WeasyPrint", "Generating UNIX Man Pages", "Publishing Summary Reports"]
        )
        reporter.log(f"Analyzed {len(reporter.links)} links across documentation pages.")

        # Step 3: PDF Generation
        pdf_path = args.pdf_output or os.path.join(os.path.dirname(config_file) or '.', 'documentation.pdf')
        reporter.progress(
            current_step=3,
            total_steps=4,
            title="Compiling PDF Manual & Asset Inspection",
            done_tasks=["Compiled Markdown pages & diagrams", "Validated internal/external links"],
            ongoing_task=f"Generating PDF manual at '{pdf_path}' with WeasyPrint",
            upcoming_tasks=["Generating UNIX Man Pages", "Publishing Summary Reports"]
        )

        try:
            generate_pdf(site_dir, config_file, pdf_path, reporter=reporter)
            site_pdf_path = os.path.join(site_dir, 'documentation.pdf')
            shutil.copy2(pdf_path, site_pdf_path)
            reporter.log(f"PDF generated successfully at '{pdf_path}'.")
        except Exception as e:
            reporter.error(f"Error generating PDF: {e}", category="PDF_BUILD")

        # Step 4: Man Page Generation
        man_output_dir = os.path.join(site_dir, 'man')
        reporter.progress(
            current_step=4,
            total_steps=4,
            title="Generating UNIX Man Pages",
            done_tasks=["Compiled Markdown pages & diagrams", "Validated internal/external links", "Generated PDF manual"],
            ongoing_task=f"Scanning '{docs_dir}' and building troff man pages in '{man_output_dir}'",
            upcoming_tasks=["Publishing Summary Reports"]
        )

        try:
            count = generate_man_pages(docs_dir, man_output_dir)
            workspace_man_dir = os.path.join(os.path.dirname(config_file) or '.', 'man')
            if os.path.exists(workspace_man_dir):
                shutil.rmtree(workspace_man_dir)
            shutil.copytree(man_output_dir, workspace_man_dir)
            reporter.log(f"Generated {count} man pages successfully.")
        except Exception as e:
            reporter.error(f"Error generating man pages: {e}", category="MAN_BUILD")

        # Print all structured summary reports
        reporter.print_summary_reports()
    finally:
        reporter.close()
        active_reporter = None

def cmd_serve(args):
    config_file = args.config or 'mkdocs.yml'
    if not os.path.exists(config_file):
        print(f"Error: Config file '{config_file}' not found. Run 'mkdocs-kit init' first.")
        sys.exit(1)
        
    print(f"Serving HTML documentation from '{config_file}'...")
    try:
        mkdocs_serve(config_file=config_file, dev_addr=args.dev_addr)
    except KeyboardInterrupt:
        print("\nStopping server.")

def main():
    parser = argparse.ArgumentParser(
        description="MkDocs Kit - A wrapped, highly integrated documentation generation environment."
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Init command
    parser_init = subparsers.add_parser("init", help="Initialize a new documentation project")
    parser_init.add_argument("directory", nargs="?", help="Directory to initialize (default: current directory)")
    
    # Build command
    parser_build = subparsers.add_parser("build", help="Build HTML, PDF, and Man pages documentation")
    parser_build.add_argument("-c", "--config", help="Path to mkdocs.yml config file")
    parser_build.add_argument("-o", "--pdf-output", help="Path to output PDF file")
    parser_build.add_argument("-l", "--log-file", default="mkdocs-kit.log", help="Path to log file (default: mkdocs-kit.log)")
    
    # Serve command
    parser_serve = subparsers.add_parser("serve", help="Serve HTML documentation locally")
    parser_serve.add_argument("-c", "--config", help="Path to mkdocs.yml config file")
    parser_serve.add_argument("-a", "--dev-addr", default="127.0.0.1:8000", help="IP address and port to serve on (default: 127.0.0.1:8000)")
    
    args = parser.parse_args()
    
    if args.command == "init":
        cmd_init(args)
    elif args.command == "build":
        cmd_build(args)
    elif args.command == "serve":
        cmd_serve(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
