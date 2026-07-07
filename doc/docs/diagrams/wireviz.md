# WireViz — Cable & Wiring Harness Diagrams

WireViz documents physical cable assemblies, connectors, and pinouts using a clean YAML syntax. It renders professional wiring diagrams with color-coded wire representations.

!!! tip "Color codes"
    WireViz uses standard color abbreviations: `RD` (red), `BK` (black), `GN` (green), `YE` (yellow), `BU` (blue), `WH` (white), `GY` (grey), `OG` (orange), `PK` (pink), `VT` (violet).

---

## Simple 3-Wire Serial Cable

A minimal RS-232 serial cable connecting TX, RX, and GND between two DB9 connectors.

```wireviz
connectors:
  J1:
    type: DB9
    subtype: male
    pinlabels: [DCD, RX, TX, DTR, GND, DSR, RTS, CTS, RI]
  J2:
    type: DB9
    subtype: female
    pinlabels: [DCD, RX, TX, DTR, GND, DSR, RTS, CTS, RI]

cables:
  W1:
    wirecount: 3
    colors: [RD, BK, GN]

connections:
  -
    - J1: [3, 2, 5]
    - W1: [1, 2, 3]
    - J2: [2, 3, 5]
```

---

## Shielded Industrial Sensor Cable

A 3-wire shielded cable used for industrial field-bus connections — includes a shield drain wire tied to chassis ground.

```wireviz
connectors:
  X1:
    type: D-Sub
    subtype: female
    pinlabels: [DCD, RX, TX, DTR, GND, DSR, RTS, CTS, RI]
  X2:
    type: Molex KK 254
    subtype: female
    pinlabels: [GND, RX, TX]

cables:
  W1:
    gauge: "0.25 mm2"
    length: 0.2
    color_code: DIN
    wirecount: 3
    shield: true

connections:
  -
    - X1: [5, 2, 3]
    - W1: [1, 2, 3]
    - X2: [1, 3, 2]
  -
    - X1: 5
    - W1: s
```

---

## Power Y-Splitter Harness

A power distribution harness splitting one Molex input connector into two SATA power outputs.

```wireviz
connectors:
  Power_In:
    type: Molex 4pin
    pinlabels: [12V, GND, GND, 5V]
  Device_A:
    type: SATA power
    pinlabels: [3.3V, GND, 5V, GND, 12V]
  Device_B:
    type: SATA power
    pinlabels: [3.3V, GND, 5V, GND, 12V]

cables:
  W1:
    wirecount: 4
    colors: [YE, BK, BK, RD]
  W2:
    wirecount: 4
    colors: [OG, BK, RD, BK]

connections:
  -
    - Power_In: [1, 2, 3, 4]
    - W1: [1, 2, 3, 4]
    - Device_A: [5, 2, 3, 4]
  -
    - Power_In: [1, 2, 3, 4]
    - W2: [1, 2, 3, 4]
    - Device_B: [5, 2, 3, 4]
```
