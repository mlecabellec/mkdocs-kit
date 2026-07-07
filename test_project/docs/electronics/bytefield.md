# ByteField Register Layouts

This page demonstrates the rendering of hardware registers, bitfields, and memory layouts using the **ByteField** engine.

## Lisp-like DSL Format
The classic Clojure-style Lisp DSL for defining byte field diagrams. It is fully parsed by our custom Lisp engine.

```bytefield
(bytefield
  (draw-column-headers)
  (draw-box "Type" 8)
  (draw-box "Length" 16)
  (draw-box "Value" 8)
)
```

## YAML Format
A clean, human-readable YAML specification mapping a list of register fields.

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

## JSON Format
A structured JSON array representing the register layout.

```bytefield
[
  {"name": "Command", "bits": 4, "type": 1},
  {"name": "Address", "bits": 12, "type": 2},
  {"name": "Data", "bits": 16, "type": 3}
]
```
