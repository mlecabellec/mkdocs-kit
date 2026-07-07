# ByteField — Bit & Register Field Diagrams

ByteField renders hardware register layouts and bit-field maps as SVG diagrams. It accepts **three input formats** — pick whichever matches your workflow.

---

## Format 1: Lisp-like DSL

The Clojure-inspired DSL is the most expressive format. Use `draw-box` for named fields, `draw-gap` for variable-length regions, and `draw-column-headers` to render the bit position header row.

### Type-Length-Value (TLV) Register

```bytefield
(bytefield
  (draw-column-headers)
  (draw-box "Type" 8)
  (draw-box "Length" 16)
  (draw-box "Value" 8)
)
```

### IPv4 Header (first 64 bits)

```bytefield
(bytefield
  (draw-column-headers)
  (draw-box "Version" 4)
  (draw-box "IHL" 4)
  (draw-box "DSCP" 6)
  (draw-box "ECN" 2)
  (draw-box "Total Length" 16)
  (draw-box "Identification" 16)
  (draw-gap "Payload")
)
```

---

## Format 2: JSON Array

A structured JSON array where each object defines a field with `name`, `bits`, and optional `type` (used for color-coding by the renderer).

### SPI Control Register

```bytefield
[
  {"name": "CPOL", "bits": 1, "type": 1},
  {"name": "CPHA", "bits": 1, "type": 1},
  {"name": "LSBF", "bits": 1, "type": 2},
  {"name": "SPE",  "bits": 1, "type": 3},
  {"name": "MSTR", "bits": 1, "type": 3},
  {"name": "Reserved", "bits": 3},
  {"name": "BAUD[2:0]", "bits": 3, "type": 2},
  {"name": "DFF", "bits": 1, "type": 1},
  {"name": "RXONLY", "bits": 1},
  {"name": "SSM", "bits": 1},
  {"name": "SSI", "bits": 1}
]
```

---

## Format 3: YAML List

The most human-readable format — a YAML list of field definitions. Supports `name`, `bits`, `attr` (displayed annotations), and `type` for coloring.

### Hardware Status Register

```bytefield
- name: IPO
  bits: 8
  attr: RO
- bits: 7
- name: BRK
  bits: 5
  attr: RW
  type: 4
- name: CPK
  bits: 1
- name: Clear
  bits: 3
- bits: 8
```
