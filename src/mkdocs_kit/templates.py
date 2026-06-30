MKDOCS_YML = """site_name: My Documentation Kit
theme:
  name: material
  palette:
    scheme: slate
    primary: indigo
    accent: indigo
  features:
    - navigation.tabs
    - navigation.sections
    - toc.integrate

plugins:
  - search

nav:
  - Home: index.md
  - Diagrams Showcase: diagrams.md
"""

INDEX_MD = """# Welcome to MkDocs Kit!

This is a highly integrated documentation environment wrapped in a single binary.

## Features

* **HTML Documentation**: Standard responsive HTML5 site (built with Material for MkDocs).
* **PDF Reference Manual**: Automatically generated from your pages.
* **UNIX Man Pages**: Compiled from Markdown files in your `man/` folder.
* **Integrated Diagrams**:
    * **PlantUML** (UML diagrams)
    * **WireViz** (Wiring & cabling diagrams)
    * **RackDiag** (Server rack layouts)
    * **PacketDiag** (Network packet layouts)
    * **ByteField** (Binary bit/byte field diagrams)

## Getting Started

1. Edit the Markdown files in `docs/`.
2. Run `mkdocs-kit build` to compile everything (HTML, PDF, and Man pages).
3. Run `mkdocs-kit serve` to preview your HTML site locally.
"""

DIAGRAMS_MD = """# Diagram Showcase

This page showcases the diagram engines integrated into this kit. All diagrams are rendered locally to SVG and embedded directly in the HTML and PDF outputs.

## PlantUML

```plantuml
@startuml
skinparam handwritten true
skinparam backgroundColor #2e303f
skinparam ActivityBorderColor #ffffff
skinparam ActivityStartColor #ffffff
skinparam ActivityEndColor #ffffff
skinparam ActivityFontColor #ffffff
skinparam ArrowColor #ffffff

start
:Initialize MkDocs Kit;
:Parse Markdown;
if (Diagram found?) then (yes)
  :Render locally to SVG;
  :Embed SVG in HTML;
else (no)
endif
:Generate PDF and Man Pages;
stop
@enduml
```

## WireViz

```wireviz
connectors:
  A:
    type: DB9
    pinlabels: [TX, RX, GND]
  B:
    type: RJ45
    pinlabels: [RX, TX, GND]

cables:
  W1:
    wirecount: 3

connections:
  -
    - A: [1, 2, 3]
    - W1: [1, 2, 3]
    - B: [2, 1, 3]
```

## RackDiag

```rackdiag
rackdiag {
  rack {
    16U;
    1: UPS [color = "red"];
    2: DB Server [2U];
    4: Web Server [2U];
    6: Switch;
  }
}
```


## PacketDiag

```packetdiag
packetdiag {
  colwidth = 32;
  0-15: Source Port;
  16-31: Destination Port;
  32-63: Sequence Number;
  64-95: Acknowledgment Number;
}
```

## ByteField

You can write ByteField diagrams using Clojure-like Lisp DSL, JSON, or YAML.

### Lisp-like DSL
```bytefield
(bytefield
  (draw-column-headers)
  (draw-box "Type" 8)
  (draw-box "Length" 16)
  (draw-box "Value" 8)
)
```

### YAML Format
```bytefield
- name: Type
  bits: 8
- name: Length
  bits: 16
- name: Value
  bits: 8
```
"""

MAN_MD_TEMPLATE = """---
title: mytool
section: 1
date: June 2026
version: 1.0.0
manual: MyTool Utility Manual
description: A tool to demonstrate MkDocs Kit man page generation
---

# MYTOOL(1) - A tool to demonstrate MkDocs Kit man page generation

## SYNOPSIS
**mytool** [*options*] *command* [*args*]

## DESCRIPTION
**mytool** is a utility designed to showcase how Markdown files in the `docs/man/` directory are automatically compiled into standard UNIX troff man pages.

## OPTIONS
- **-h**, **--help**
  Show help message and exit.
  
- **-v**, **--version**
  Show version information and exit.

## COMMANDS
- **build**
  Build the documentation.
  
- **serve**
  Serve the documentation locally.

## AUTHOR
Written by Antigravity.
"""
