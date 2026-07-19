# 📈 Plotly Charts

This page demonstrates Plotly chart integration supporting interactive Plotly.js visuals in HTML output and pre-rendered vector SVG graphics in PDF output.

---

## 📊 Quarterly Revenue Bar Chart

```plotly
data:
  - x: ["Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025", "Q1 2026"]
    y: [120, 180, 240, 310, 390]
    type: "bar"
    marker:
      color: "#3498db"
layout:
  title: "Annual Revenue Growth ($k)"
  xaxis: { title: "Quarter" }
  yaxis: { title: "Revenue ($k)" }
  width: 650
  height: 380
```

---

## 📉 System Performance Line Chart

```plotly
data:
  - x: ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"]
    y: [15, 12, 45, 88, 72, 30]
    type: "scatter"
    mode: "lines+markers"
    marker:
      color: "#e74c3c"
layout:
  title: "Server CPU Utilization (%)"
  xaxis: { title: "Time of Day" }
  yaxis: { title: "CPU Usage (%)" }
  width: 650
  height: 380
```
