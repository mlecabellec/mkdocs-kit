import subprocess
import tempfile
import os
import re
import json
import yaml
import bit_field
import wireviz.wireviz as wv
import PIL.ImageDraw

# Apply monkey-patch to PIL.ImageDraw for blockdiag compatibility with Pillow 10+
if not hasattr(PIL.ImageDraw.ImageDraw, 'textsize'):
    def patched_textsize(self, text, font=None, *args, **kwargs):
        bbox = self.textbbox((0, 0), text, font=font, *args, **kwargs)
        return (bbox[2] - bbox[0], bbox[3] - bbox[1])
    PIL.ImageDraw.ImageDraw.textsize = patched_textsize

# Mock missing distributions for PyInstaller frozen environment
import pkg_resources
orig_resolve = pkg_resources.WorkingSet.resolve
def patched_resolve(self, requirements, *args, **kwargs):
    while True:
        try:
            return orig_resolve(self, requirements, *args, **kwargs)
        except (pkg_resources.DistributionNotFound, pkg_resources.VersionConflict) as e:
            req = e.req
            dist = pkg_resources.Distribution(
                project_name=req.project_name,
                version='99.9.9',
                location=''
            )
            self.add(dist)
pkg_resources.WorkingSet.resolve = patched_resolve


import shutil
import sys
import rackdiag.parser
import rackdiag.builder
import rackdiag.drawer
import packetdiag.parser
import packetdiag.builder
import packetdiag.drawer
import blockdiag.parser
import blockdiag.builder
import blockdiag.drawer
import nwdiag.parser
import nwdiag.builder
import nwdiag.drawer
import nwdiag.elements
import blockdiag.elements

# Support description attribute in nwdiag networks and groups (alias for label)
if not hasattr(nwdiag.elements.Network, 'description'):
    nwdiag.elements.Network.description = property(
        lambda s: s.label,
        lambda s, v: setattr(s, 'label', v)
    )
if not hasattr(blockdiag.elements.NodeGroup, 'description'):
    blockdiag.elements.NodeGroup.description = property(
        lambda s: s.label,
        lambda s, v: setattr(s, 'label', v)
    )


def get_plantuml_cmd(puml_path):
    """
    Locates the PlantUML execution command, prioritizing bundled JRE and PlantUML jar,
    then environment variables, local system installations, and finally system plantuml executable.
    """
    candidate_bases = []
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        candidate_bases.append(sys._MEIPASS)

    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    candidate_bases.append(pkg_dir)
    candidate_bases.append(os.path.join(pkg_dir, 'bundled'))

    for base in candidate_bases:
        java_bin = os.path.join(base, 'jre', 'bin', 'java')
        jar_candidates = [
            os.path.join(base, 'plantuml', 'plantuml.jar'),
            os.path.join(base, 'plantuml.jar'),
        ]
        jar_path = next((j for j in jar_candidates if os.path.isfile(j)), None)
        if os.path.isfile(java_bin) and jar_path:
            try:
                os.chmod(java_bin, 0o755)
            except Exception:
                pass
            return [java_bin, '-Djava.awt.headless=true', '-jar', jar_path, '-tsvg', puml_path]

    # Check environment variable
    env_jar = os.environ.get('PLANTUML_JAR')
    if env_jar and os.path.isfile(env_jar):
        java_home = os.environ.get('JAVA_HOME', '')
        java_bin = os.path.join(java_home, 'bin', 'java') if java_home and os.path.isfile(os.path.join(java_home, 'bin', 'java')) else 'java'
        return [java_bin, '-Djava.awt.headless=true', '-jar', env_jar, '-tsvg', puml_path]

    # Check local modern plantuml.jar if present
    if os.path.isfile('/opt/gitea/plantuml.jar'):
        java_home = os.environ.get('JAVA_HOME', '')
        java_bin = os.path.join(java_home, 'bin', 'java') if java_home and os.path.isfile(os.path.join(java_home, 'bin', 'java')) else 'java'
        return [java_bin, '-Djava.awt.headless=true', '-jar', '/opt/gitea/plantuml.jar', '-tsvg', puml_path]

    # Check system plantuml executable
    plantuml_bin = shutil.which('plantuml')
    if plantuml_bin:
        return [plantuml_bin, '-tsvg', puml_path]

    # Fallback to system plantuml.jar
    if os.path.isfile('/usr/share/plantuml/plantuml.jar'):
        return ['java', '-Djava.awt.headless=true', '-jar', '/usr/share/plantuml/plantuml.jar', '-tsvg', puml_path]

    return ['plantuml', '-tsvg', puml_path]


def render_plantuml(src):
    with tempfile.TemporaryDirectory() as tmpdir:
        puml_path = os.path.join(tmpdir, 'diagram.puml')
        with open(puml_path, 'w', encoding='utf-8') as f:
            f.write(src)

        cmd = get_plantuml_cmd(puml_path)
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            err_msg = (e.stderr or "") + ("\n" + e.stdout if e.stdout else "")
            raise RuntimeError(f"PlantUML rendering failed: {err_msg.strip()}")
        except FileNotFoundError as e:
            raise RuntimeError(f"PlantUML command not found ({cmd[0]}): {e}")

        svg_files = [f for f in os.listdir(tmpdir) if f.endswith('.svg')]
        if not svg_files:
            raise RuntimeError("PlantUML did not generate an SVG file.")

        svg_path = os.path.join(tmpdir, svg_files[0])
        with open(svg_path, 'r', encoding='utf-8') as f:
            svg_content = f.read()

        if '<text fill="#FF0000"' in svg_content and 'Syntax Error?' in svg_content:
            raise RuntimeError("PlantUML generated a Syntax Error diagram")

        return svg_content

def render_wireviz(src):
    try:
        svg_data = wv.parse(src, return_types='svg')
        if isinstance(svg_data, bytes):
            return svg_data.decode('utf-8')
        return svg_data
    except Exception as e:
        raise RuntimeError(f"WireViz rendering failed: {e}")

# Monkey-patch PIL.ImageDraw.ImageDraw.textsize for Pillow 10+ compatibility with blockdiag
import PIL.ImageDraw
if not hasattr(PIL.ImageDraw.ImageDraw, 'textsize'):
    def patched_textsize(self, text, font=None, *args, **kwargs):
        bbox = self.textbbox((0, 0), text, font=font, *args, **kwargs)
        return (bbox[2] - bbox[0], bbox[3] - bbox[1])
    PIL.ImageDraw.ImageDraw.textsize = patched_textsize

# Register blockdiag SVG drawer for PyInstaller frozen environments
try:
    from blockdiag.imagedraw import install_imagedrawer
    from blockdiag.imagedraw.svg import SVGImageDraw
    install_imagedrawer('svg', SVGImageDraw)
except Exception:
    pass

def render_rackdiag(src):
    try:
        tree = rackdiag.parser.parse_string(src)
        diagram = rackdiag.builder.ScreenNodeBuilder.build(tree)
        draw = rackdiag.drawer.DiagramDraw('SVG', diagram)
        draw.draw()
        svg = draw.save()
        if isinstance(svg, bytes):
            return svg.decode('utf-8')
        return svg
    except Exception as e:
        raise RuntimeError(f"RackDiag rendering failed: {e}")

def render_packetdiag(src):
    try:
        tree = packetdiag.parser.parse_string(src)
        diagram = packetdiag.builder.ScreenNodeBuilder.build(tree)
        draw = packetdiag.drawer.DiagramDraw('SVG', diagram)
        draw.draw()
        svg = draw.save()
        if isinstance(svg, bytes):
            return svg.decode('utf-8')
        return svg
    except Exception as e:
        raise RuntimeError(f"PacketDiag rendering failed: {e}")

def render_blockdiag(src):
    try:
        tree = blockdiag.parser.parse_string(src)
        diagram = blockdiag.builder.ScreenNodeBuilder.build(tree)
        draw = blockdiag.drawer.DiagramDraw('SVG', diagram)
        draw.draw()
        svg = draw.save()
        if isinstance(svg, bytes):
            return svg.decode('utf-8')
        return svg
    except Exception as e:
        raise RuntimeError(f"BlockDiag rendering failed: {e}")

def render_nwdiag(src):
    try:
        tree = nwdiag.parser.parse_string(src)
        diagram = nwdiag.builder.ScreenNodeBuilder.build(tree)
        draw = nwdiag.drawer.DiagramDraw('SVG', diagram)
        draw.draw()
        svg = draw.save()
        if isinstance(svg, bytes):
            return svg.decode('utf-8')
        return svg
    except Exception as e:
        raise RuntimeError(f"NwDiag rendering failed: {e}")

def parse_lisp(src):
    tokens = re.findall(r'\(|\)|"[^"]*"|:[^\s)]+|[^\s()]+', src)
    
    def helper(index):
        result = []
        while index < len(tokens):
            token = tokens[index]
            if token == '(':
                sublist, index = helper(index + 1)
                result.append(sublist)
                index += 1  # Skip the closing ')'
            elif token == ')':
                return result, index
            else:
                if token.isdigit():
                    val = int(token)
                elif token.startswith('"') and token.endswith('"'):
                    val = token[1:-1]
                else:
                    val = token
                result.append(val)
                index += 1
        return result, index

    parsed, _ = helper(0)
    return parsed[0] if parsed else []


def lisp_to_bitfield(parsed):
    fields = []
    if not parsed:
        return fields
        
    items = parsed[1:] if parsed[0] == 'bytefield' else parsed
        
    for expr in items:
        if not isinstance(expr, list) or not expr:
            continue
        op = expr[0]
        if op == 'draw-box':
            name = expr[1]
            bits = 8
            if len(expr) > 2:
                if expr[2] == ':bytes' and len(expr) > 3:
                    bits = int(expr[3]) * 8
                else:
                    try:
                        bits = int(expr[2])
                    except ValueError:
                        bits = 8
            fields.append({'name': name, 'bits': bits})
        elif op == 'draw-gap':
            name = expr[1] if len(expr) > 1 else ''
            fields.append({'name': name, 'bits': 4, 'type': 0})
        elif op == 'draw-column-headers':
            pass
    return fields

import textwrap

def parse_bytefield(src):
    src_stripped = textwrap.dedent(src).strip()
    if src_stripped.startswith('('):
        parsed = parse_lisp(src_stripped)
        return lisp_to_bitfield(parsed)
    else:
        try:
            return json.loads(src_stripped)
        except json.JSONDecodeError:
            try:
                res = yaml.safe_load(src_stripped)
                if isinstance(res, list):
                    return res
            except Exception:
                pass
    raise ValueError("Invalid bytefield format. Must be Lisp-like DSL, JSON, or YAML.")


def render_bytefield(src):
    try:
        fields = parse_bytefield(src)
        jsonml = bit_field.render(fields)
        svg = bit_field.jsonml_stringify(jsonml)
        if isinstance(svg, bytes):
            return svg.decode('utf-8')
        return svg
    except Exception as e:
        raise RuntimeError(f"ByteField rendering failed: {e}")
