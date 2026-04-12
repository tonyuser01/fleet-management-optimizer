# 🚚 Fleet Management Optimizer

**Scientific Research — Fleet Management for a General Merchandise Distributor**  
MSc Transport Management · Faculty of Transport · Politehnica University of Bucharest · 2024-2026

---

## Overview

An interactive web application for optimizing the fleet management of a general merchandise distributor, implementing mathematical vehicle routing models:

- **MDVRP** — Multi-Depot Vehicle Routing Problem
- **FSMVRP** — Fleet Size and Mix Vehicle Routing Problem
- **Real-map visualization** via Folium (OpenStreetMap) with animated routes
- **Algorithm comparison**: Nearest Neighbor, Clarke-Wright Savings, 2-opt

---

## Project structure

```
fleet_management/
├── app.py                          # Streamlit entry point — home page
├── requirements.txt
├── README.md
├── pages/
│   ├── 1_Map_and_Data.py           # Interactive map & data configuration
│   ├── 2_MDVRP_Solver.py           # MDVRP solver with route map visualization
│   ├── 3_FSMVRP_Optimizer.py       # Fleet optimizer & sensitivity analysis
│   ├── 4_Mathematical_Models.py    # Full mathematical documentation
│   └── 5_Route_Timeline.py         # Delivery schedule and pallet tracking
└── utils/
    ├── __init__.py
    ├── data_models.py              # Data classes + Bucharest sample data
    ├── mdvrp_algorithms.py         # NN, Clarke-Wright Savings, 2-opt
    ├── fsmvrp_optimizer.py         # Fleet enumeration optimizer
    └── map_utils.py                # Folium map builder
```

---

## Installation & running

### 1. Clone the repository

```bash
git clone https://github.com/tonyuser01/fleet-management-optimizer.git
cd fleet-management-optimizer
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# macOS / Linux:
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

```bash
streamlit run app.py
```

The app opens automatically at `http://localhost:8501`

---

## Mathematical models

### MDVRP — Objective function

$$\min \sum_{k \in K} \sum_{(i,j) \in A} c_{ij} \cdot x_{ijk}$$

**constraints:**
- Customer coverage: each customer visited exactly once
- Vehicle capacity: `Σ d_i · y_ik ≤ Q_k`
- Flow conservation: vehicle enters and exits each node
- Depot assignment: vehicle departs from and returns to its assigned depot

### FSMVRP — Objective function

$$\min \sum_{t \in T} f_t \cdot n_t + \sum_{k \in K} \sum_{(i,j) \in A} c_{ij} \cdot x_{ijk}$$

### Customer-Depot Assignment

$$\text{depot}(i) = \arg\min_{d \in D} \; \text{Haversine}(d, i)$$

---

## Implemented algorithms

| Algorithm | Complexity | Description |
|---|---|---|
| Nearest Neighbor | O(n²) | Greedy: always visit the nearest unserved customer |
| Clarke-Wright Savings | O(n² log n) | Merge routes using `s(i,j) = c(d,i) + c(d,j) - c(i,j)` |
| 2-opt Local Search | O(n²) per iteration | Reverse route segments for local improvement |
| FSMVRP Enumeration | O(Π N_t^max) | Exact enumeration for small instances |

---

## Application modules

### Module 1 — Map & Data
- Depot and customer visualization on OpenStreetMap
- Toggleable layers (depots, customers, routes)
- Depot influence radius visualization
- Demand statistics and distribution charts

### Module 2 — MDVRP Solver
- Configurable algorithm and vehicle type selection
- Animated routes on map (AntPath)
- Detailed popup per route (distance, demand, cost)
- Side-by-side algorithm comparison
- Route table with utilization color coding

### Module 3 — FSMVRP Optimizer
- Fleet composition optimization (4 vehicle types)
- Cost breakdown chart (fixed vs variable)
- Top 10 feasible solutions with trade-off scatter plot
- Sensitivity analysis across demand range (50%–150%)
- Pareto-style vehicles vs cost visualization

### Module 4 — Route Timeline
- Detailed delivery schedule with arrival/departure times
- Pallet tracking per stop
- Reload logic for routes exceeding vehicle capacity
- Route duration and total distance metrics

### Module 5 — Mathematical Models
- Full MDVRP and FSMVRP formulations with LaTeX
- Algorithm pseudocode and complexity analysis
- Performance metrics with formulas
- Haversine distance formula

---

## Dependencies

| Library | Version | Purpose |
|---|---|---|
| `streamlit` | ≥1.32 | Web application framework |
| `folium` | ≥0.16 | Interactive maps (OpenStreetMap) |
| `streamlit-folium` | ≥0.20 | Folium integration in Streamlit |
| `plotly` | ≥5.20 | Interactive charts |
| `pandas` | ≥2.0 | Data processing |
| `numpy` | ≥1.26 | Numerical computations |

---

## Reference scenario

The implemented scenario simulates a general merchandise distributor in **Bucharest, Romania**:

- **3 depots**: Bucharest North, Bucharest South, Ilfov-Otopeni
- **20 customers**: stores across all districts and peri-urban areas
- **4 vehicle types**: small (3.5t), medium (7t), large (14t), refrigerated (5t)
- **Real coordinates** based on Bucharest geography

---

## Typical results

On the Bucharest scenario with 20 customers and 3 depots:

| Algorithm | Total distance | Routes | Total cost |
|---|---|---|---|
| Nearest Neighbor | ~85 km | 5–7 | ~420 € |
| Clarke-Wright Savings | ~72 km | 4–6 | ~365 € |
| Clarke-Wright + 2-opt | ~68 km | 4–6 | ~345 € |
| **CW improvement over NN** | **~15–20%** | — | — |

---

## Academic context

This application was developed as part of the **dissertation research**:

> *"Scientific Research: Fleet Management for a General Merchandise Distributor"*  
> MSc Transport Management  
> Faculty of Transport — Politehnica University of Bucharest  
> Academic year 2024-2025

### Thesis chapters covered

- **Chapter 1** — Mathematical Models: VRP, VRPTW, IRP
- **MDVRP chapter** — Multi-Depot formulation, Customer-Depot Assignment, Solution Methods
- **FSMVRP chapter** — Fleet Size and Mix, Trade-offs, Computational Methods

---

## License

MIT License — free for academic and educational use.

---

*Built with Python · Streamlit · Folium · OpenStreetMap · Plotly*
