# RackDiag Server Rack Layouts

This page demonstrates the rendering of data center server rack configurations using the **RackDiag** engine.

## 16U Server Rack
A compact 16U server rack containing a UPS, database server, web servers, a load balancer, and an L3 switch.

```rackdiag
rackdiag {
  16U;
  1: UPS [2U, color = "red"];
  3: DB Server;
  4: Web Server;
  5: Web Server;
  6: Web Server;
  7: Load Balancer;
  8: L3 Switch;
}
```

## Corporate 42U Server Rack
A representation of a full-sized corporate rack layout using correct height and color attributes.

```rackdiag
rackdiag {
  rack {
    42U;
    
    1: UPS [2U, color = "red", label = "Redundant UPS"];
    3: PDU [label = "Power Distribution Unit"];
    4: SAN Storage [2U, color = "orange", label = "NetApp SAN (2U)"];
    6: DB Server 1 [2U, label = "Database Server 1 (2U)"];
    8: DB Server 2 [2U, label = "Database Server 2 (2U)"];
    10: App Server 1 [2U, label = "App Server 1 (2U)"];
    12: App Server 2 [2U, label = "App Server 2 (2U)"];
    14: Switch 1 [color = "blue", label = "Cisco Catalyst Switch 1"];
    15: Switch 2 [color = "blue", label = "Cisco Catalyst Switch 2"];
    16: Patch Panel [label = "Fiber Patch Panel"];
    17: KVM Console [2U, label = "1U Drawer + KVM"];
  }
}
```
