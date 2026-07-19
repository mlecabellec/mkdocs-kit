# 📊 CSV Data Tables

This page demonstrates CSV data table inclusion with interactive sorting, multi-column search filtering, and pagination in HTML, alongside build-time filtered and sorted PDF rendering.

---

## 🏢 Employee Roster (File Inclusion with Build-Time Filter & Sort)

```csv
file: ../data/employees.csv
page_size: 5
sort: "Salary desc"
filter: "Age >= 30"
search: true
caption: High Seniority Staff (Age >= 30, Sorted by Salary Descending)
```

---

## 📈 Financial Data (Inline CSV Sample)

```csv
page_size: 4
sort: "Revenue desc"
search: true
caption: Quarterly Financial Report

Quarter, Region, Revenue, Growth
Q1 2026, North America, $145000, +12%
Q1 2026, Europe, $112000, +8%
Q2 2026, North America, $168000, +15%
Q2 2026, Asia Pacific, $98000, +22%
Q3 2026, Europe, $130000, +10%
Q3 2026, North America, $182000, +18%
```
