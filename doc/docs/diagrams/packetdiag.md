# PacketDiag — Protocol Header Diagrams

PacketDiag generates byte-accurate network protocol header diagrams. Fields are defined by bit position ranges and can carry color, rotation, and spanning attributes.

!!! tip "Syntax"
    Use `start-end: Label;` to define a field. `[rotate = 270]` rotates short labels vertically. `[colheight = N]` makes a field span multiple rows.

---

## UDP Header

The complete 64-bit User Datagram Protocol header with color-highlighted fields.

```packetdiag
packetdiag {
  colwidth = 32;

  0-15: Source Port [color = lightblue];
  16-31: Destination Port [color = lightgreen];
  32-47: Length [color = lightyellow];
  48-63: Checksum [color = lightpink];
}
```

---

## TCP Header

The full 224-bit TCP header including flags with rotated labels, window, checksum, and options.

```packetdiag
packetdiag {
  colwidth = 32;
  node_height = 72;

  0-15: Source Port;
  16-31: Destination Port;
  32-63: Sequence Number;
  64-95: Acknowledgment Number;
  96-99: Data Offset;
  100-103: Reserved;
  104: CWR [rotate = 270];
  105: ECE [rotate = 270];
  106: URG [rotate = 270];
  107: ACK [rotate = 270];
  108: PSH [rotate = 270];
  109: RST [rotate = 270];
  110: SYN [rotate = 270];
  111: FIN [rotate = 270];
  112-127: Window;
  128-143: Checksum;
  144-159: Urgent Pointer;
  160-191: (Options and Padding);
  192-223: data [colheight = 3];
}
```

---

## EtherCAT Frame Header

An industrial EtherCAT Ethernet frame header layout — an example of field-bus protocol documentation.

```packetdiag
packetdiag {
  colwidth = 32;

  0-47: Destination MAC;
  48-95: Source MAC;
  96-111: EtherType (0x88A4);
  112-121: Length;
  122: Reserved;
  123-127: Type;
  128-255: EtherCAT Datagram [colheight = 2];
}
```
