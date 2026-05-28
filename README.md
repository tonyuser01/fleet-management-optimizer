# 🚚 Fleet Management Optimizer

**Scientific Research — Fleet Management for a General Merchandise Distributor**  
MSc Transport Management · Faculty of Transport · National University of Science and Technology POLITEHNICA Bucharest · 2024-2026

---

## Overview

An interactive web application for optimizing the fleet management of a general merchandise distributor, implementing mathematical vehicle routing models:

- **MDVRP** — Multi-Depot Vehicle Routing Problem
- **FSMVRP** — Fleet Size and Mix Vehicle Routing Problem
- **Real-map visualization** via Folium (OpenStreetMap) with animated routes

---

## Project structure

```
fleet_management/
├── app.py                          # Streamlit entry point — home page
├── requirements.txt
├── README.md
├── pages/
│   ├── 1_Map_and_Data.py           # Interactive map, depot/store config, fleet allocation
│   ├── 2_MDVRP_Solver.py           # MDVRP solver with route map visualization
│   ├── 3_FSMVRP_Optimizer.py       # Fleet optimizer & sensitivity analysis
│   ├── 4_Mathematical_Models.py    # Full mathematical documentation
│   ├── 5_Route_Timeline.py         # Delivery schedule and pallet tracking
│   └── 6_Conclusions_and_Results.py # Research questions answered from simulation
└── utils/
    ├── __init__.py
    ├── data_models.py              # Data classes + Bucharest sample data
    ├── mdvrp_algorithms.py         # NN, Clarke-Wright Savings, 2-opt, refrigeration validation
    ├── fsmvrp_optimizer.py         # Combined Savings, fleet enumeration optimizer
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

**Constraints:**
- Customer coverage: each customer visited exactly once
- Vehicle capacity: `Σ d_i · y_ik ≤ Q_k`
- Flow conservation: vehicle enters and exits each node
- Depot assignment: vehicle departs from and returns to its assigned depot
- Load balancing: vehicle availability constraint per depot (M_d)

### FSMVRP — Objective function

$$\min \sum_{t \in T} f_t \cdot n_t + \sum_{k \in K} \sum_{(i,j) \in A} c_{ij} \cdot x_{ijk}$$

### Combined Savings (CS) — FSMVRP heuristic

$$CS(i,j) = s_{ij} + F(Z_i) + F(Z_j) - F(Z_i + Z_j)$$

where $F(Z)$ is the fixed cost of the smallest vehicle capable of serving demand $Z$.

### Customer-Depot Assignment

$$\text{depot}(i) = \arg\min_{d \in D} \; \text{Haversine}(d, i)$$

---

## Implemented algorithms

| Algorithm | Complexity | Description |
|---|---|---|
| Nearest Neighbor | O(n²) | Greedy: always visit the nearest unserved customer |
| Clarke-Wright Savings | O(n² log n) | Merge routes using `s(i,j) = c(d,i) + c(d,j) - c(i,j)` |
| 2-opt Local Search | O(n²) per iteration | Reverse route segments for local improvement |
| Combined Savings (CS) | O(n²) per iteration | FSMVRP-aware merging with vehicle cost integration |
| FSMVRP Enumeration | O(Π N_t^max) | Exact enumeration for small instances |

---

## Application modules

### Module 1 — Map & Data
- Depot and customer visualization on OpenStreetMap
- Interactive fleet allocation per depot (vehicles by type)
- Add new customers via address geocoding or manual coordinates
- Europallet specifications and vehicle technical details
- Origin-Destination distance matrix with color coding

### Module 2 — MDVRP Solver
- Configurable algorithm and vehicle type selection (including Mixed Fleet)
- Animated routes on map (AntPath) with numbered stops and direction arrows
- Detailed route sequences with depot → customer → depot format
- Side-by-side algorithm comparison with Clarke-Wright Efficiency Index
- Load Balancing (M_d constraint) and refrigeration assignment validation

### Module 3 — FSMVRP Optimizer
- Automatic demand and distance calculation from network data
- Fleet composition optimization (4 vehicle types, 3 objectives)
- Cost breakdown chart (fixed vs variable)
- Top 10 feasible solutions with best solution highlighted
- Sensitivity analysis with automatic conclusions (50%–150% demand range)
- Combined Savings operational routing with multi-depot support

### Module 4 — Mathematical Models
- Full MDVRP and FSMVRP formulations with LaTeX
- Academic context: what each model solves and why it is useful
- Algorithm comparison table (NN vs Clarke-Wright)
- Performance metrics with formulas

### Module 5 — Route Timeline
- Step-by-step delivery schedule with arrival/departure times
- Dynamic service time based on pallets to unload
- Realistic travel time model with urban overhead
- Individual movement cyclograms (distance vs time) per route
- Multi-trip reload logic for routes exceeding vehicle capacity

### Module 6 — Conclusions & Results
- Automatic simulation of all algorithms on current network
- Explicit answers to all 5 Research Questions with real data
- Algorithm performance comparison with Clarke-Wright Efficiency Index
- The three core distribution decisions answered quantitatively

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
| `requests` | ≥2.31 | Address geocoding via Nominatim |

---

## Reference scenario

The implemented scenario simulates a general merchandise distributor in **Bucharest, Romania**:

- **3 depots**: D1 — Bucharest North, D2 — Bucharest South, D3 — Ilfov-Otopeni
- **20 customers**: stores across all districts and peri-urban areas (expandable)
- **4 vehicle types**: Small (3.5t), Medium (7t), Heavy Duty (24t), Refrigerated (5t)
- **Real GPS coordinates** based on Bucharest geography
- **Fleet allocation per depot**: configurable in Map & Data → Depot directory

---

## Academic context

This application was developed as part of the **dissertation research**:

> *"Scientific Research: Fleet Management for a General Merchandise Distributor"*  
> MSc Transport Management  
> Faculty of Transport — National University of Science and Technology POLITEHNICA Bucharest  
> Academic year 2024-2026

---

## License

Free for academic and educational use. No license granted.

---

*Built with Python · Streamlit · Folium · OpenStreetMap · Plotly*
