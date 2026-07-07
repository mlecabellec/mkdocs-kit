# RackDiag — Server Rack Layouts

RackDiag generates visual server rack diagrams from concise textual descriptions. It uses a simple `slot: label [options]` syntax inside a `rackdiag { }` block.

!!! tip "Height & Colors"
    Specify rack units with `[2U]` inside brackets. Color names like `red`, `lightgreen`, `orange`, `lightblue` are supported.

---

## Simple 16U Rack

A compact rack configuration suitable for a small server room or network closet.

```rackdiag
rackdiag {
  16U;
  1: UPS [2U, color = red];
  3: Core Switch [1U, color = lightblue];
  4: Firewall [1U];
  5: Web Server 1 [2U, color = lightgreen];
  7: Web Server 2 [2U, color = lightgreen];
  9: Database Server [2U, color = orange];
  11: NAS Storage [2U];
  13: Patch Panel [1U];
}
```

---

## Full 42U Corporate Rack

A fully populated enterprise rack including redundant power, storage, application, and network layers.

```rackdiag
rackdiag {
  42U;
  1: Redundant UPS [2U, color = red];
  3: PDU;
  4: NetApp SAN [2U, color = orange];
  6: DB Server 1 [2U];
  8: DB Server 2 [2U];
  10: App Server 1 [2U, color = lightgreen];
  12: App Server 2 [2U, color = lightgreen];
  14: App Server 3 [2U, color = lightgreen];
  16: Load Balancer [1U];
  17: Cisco Catalyst 1 [1U, color = lightblue];
  18: Cisco Catalyst 2 [1U, color = lightblue];
  19: Fiber Patch Panel [1U];
  20: KVM Console [2U];
}
```

---

## Multi-Rack Data Center Row

Multiple racks side-by-side using the `rack { }` grouping syntax to represent a data center row.

```rackdiag
rackdiag {
  rack "Production" {
    12U;
    1: App Server [2U, color = lightgreen];
    3: App Server [2U, color = lightgreen];
    5: DB Server [2U, color = orange];
    7: Switch [1U, color = lightblue];
  }
  rack "DMZ" {
    12U;
    1: Web Proxy [1U];
    2: WAF [1U, color = red];
    3: Mail Relay [1U];
    4: DNS [1U];
  }
}
```
