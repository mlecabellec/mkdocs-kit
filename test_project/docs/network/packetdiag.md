# PacketDiag Protocol Headers

This page demonstrates the rendering of network packet headers and byte-level protocol layouts using the **PacketDiag** engine.

## Complete TCP Header Layout
This diagram shows the complete TCP header layout (first 224 bits), including flags with rotated text, window size, checksum, options, and data.

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

## Simple UDP Header Layout
A simple User Datagram Protocol (UDP) header using color styling.

```packetdiag
packetdiag {
  colwidth = 32;
  
  0-15: Source Port [color = "lightblue"];
  16-31: Destination Port [color = "lightgreen"];
  32-47: Length [color = "lightyellow"];
  48-63: Checksum [color = "lightpink"];
}
```
