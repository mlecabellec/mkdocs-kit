# NwDiag — Network Topology Diagrams

NwDiag generates network topology diagrams from text descriptions. Networks are defined as named groups with optional subnet addresses. Nodes can participate in multiple networks.

!!! tip "Syntax"
    Define networks with `network name { address = "..."; }`. Place nodes inside the networks where they reside. A node can appear in multiple networks to show multi-homed hosts.

---

## Simple DMZ Layout

A two-tier network showing a DMZ hosting web servers and an internal network hosting back-end services.

```nwdiag
{
  network dmz {
    address = "192.168.1.0/24";

    web-01 [address = "192.168.1.10"];
    web-02 [address = "192.168.1.11"];
    lb [label = "Load Balancer", address = "192.168.1.1"];
  }
  network internal {
    address = "10.0.0.0/24";

    web-01 [address = "10.0.0.10"];
    web-02 [address = "10.0.0.11"];
    db-01 [label = "DB Primary", address = "10.0.0.100"];
    db-02 [label = "DB Replica", address = "10.0.0.101"];
  }
}
```

---

## Industrial Network Segments

An industrial automation network with a management VLAN, a supervisory (SCADA) network, and a field-bus segment.

```nwdiag
{
  network management {
    address = "172.16.0.0/24";

    workstation [address = "172.16.0.10"];
    historian [address = "172.16.0.20"];
  }
  network scada {
    address = "172.16.1.0/24";

    historian [address = "172.16.1.20"];
    hmi-01 [label = "HMI Station 1", address = "172.16.1.30"];
    hmi-02 [label = "HMI Station 2", address = "172.16.1.31"];
    plc-gw [label = "PLC Gateway", address = "172.16.1.50"];
  }
  network fieldbus {
    address = "10.10.0.0/24";

    plc-gw [address = "10.10.0.1"];
    plc-01 [label = "PLC Rack A", address = "10.10.0.10"];
    plc-02 [label = "PLC Rack B", address = "10.10.0.11"];
  }
}
```
