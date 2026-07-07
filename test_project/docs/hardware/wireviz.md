# WireViz Cabling Diagrams

This page demonstrates the rendering of physical cable wiring harnesses, connectors, and pinouts using the **WireViz** engine.

## Advanced Wiring System with Shield
This example demonstrates a 3-wire shielded cable connecting a D-Sub connector to a Molex connector, including shield grounding.

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

## Y-Splitter Power Cable
A cabling harness with one main power input connector splitting into two output SATA connectors.

```wireviz
connectors:
  Power_In:
    type: Molex 4pin permanent
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
  W2:
    wirecount: 4

connections:
  -
    - Power_In: [1, 2, 3, 4]
    - W1: [1, 2, 3, 4]
    - Device_A: [5, 4, 3, 2]
  -
    - Power_In: [1, 2, 3, 4]
    - W2: [1, 2, 3, 4]
    - Device_B: [5, 4, 3, 2]
```
