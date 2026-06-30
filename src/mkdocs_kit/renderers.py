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

import rackdiag.parser
import rackdiag.builder
import rackdiag.drawer
import packetdiag.parser
import packetdiag.builder
import packetdiag.drawer

def render_plantuml(src):
    with tempfile.TemporaryDirectory() as tmpdir:
        puml_path = os.path.join(tmpdir, 'diagram.puml')
        with open(puml_path, 'w', encoding='utf-8') as f:
            f.write(src)
        
        try:
            # Use system plantuml command (which is version 1.2020.02 on this system)
            subprocess.run(['plantuml', '-tsvg', puml_path], capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"PlantUML rendering failed: {e.stderr or e.stdout}")
        
        svg_path = os.path.join(tmpdir, 'diagram.svg')
        if not os.path.exists(svg_path):
            raise RuntimeError("PlantUML did not generate an SVG file.")
        
        with open(svg_path, 'r', encoding='utf-8') as f:
            return f.read()

def render_wireviz(src):
    try:
        svg_data = wv.parse(src, return_types='svg')
        if isinstance(svg_data, bytes):
            return svg_data.decode('utf-8')
        return svg_data
    except Exception as e:
        raise RuntimeError(f"WireViz rendering failed: {e}")

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

def parse_lisp(src):
    tokens = re.findall(r'\(|\)|"[^"]*"|:[^\s)]+|[^\s()]+', src)
    
    def helper(index):
        result = []
        while index < len(tokens):
            token = tokens[index]
            if token == '(':
                sublist, index = helper(index + 1)
                result.append(sublist)
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
