# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []
tmp_ret = collect_all('mkdocs')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('material')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('weasyprint')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('wireviz')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('blockdiag')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('rackdiag')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('packetdiag')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('nwdiag')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('bit_field')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

hiddenimports += ['mkdocs_kit.csv_renderer', 'mkdocs_kit.plotly_renderer', 'mkdocs_kit.d3_renderer', 'mkdocs_kit.reporter', 'mkdocs_kit.link_checker']

import os

def collect_dir(src_dir, target_prefix):
    ret = []
    for root, dirs, files in os.walk(src_dir):
        for f in files:
            full_path = os.path.join(root, f)
            rel_dir = os.path.relpath(root, src_dir)
            if rel_dir == '.':
                dest = target_prefix
            else:
                dest = os.path.join(target_prefix, rel_dir)
            ret.append((full_path, dest))
    return ret

bundled_dir = os.path.join(SPECPATH, 'src', 'mkdocs_kit', 'bundled')
jre_dir = os.path.join(bundled_dir, 'jre')
plantuml_jar = os.path.join(bundled_dir, 'plantuml', 'plantuml.jar')

if os.path.isdir(jre_dir):
    datas += collect_dir(jre_dir, 'jre')

if os.path.isfile(plantuml_jar):
    datas.append((plantuml_jar, 'plantuml'))

a = Analysis(
    ['src/mkdocs_kit/cli.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='mkdocs-kit',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=['libjvm.so', 'java', 'libjli.so', 'libawt*.so', 'libfontmanager.so', 'liblcms.so', 'libjavajpeg.so'],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

