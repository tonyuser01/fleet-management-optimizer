# 🚚 Fleet Management Optimizer

**Scientific Research — Fleet Management for a General Merchandise Distributor**  
MSc Transport Management · Faculty of Transport · National University of Science and Technology POLITEHNICA Bucharest · 2024–2026

---

## Overview

An interactive web application for the optimisation of fleet management operations for a general merchandise distributor. The application implements and compares two mathematical vehicle routing models:

- **MDVRP** — Multi-Depot Vehicle Routing Problem
- **FSMVRP** — Fleet Size and Mix Vehicle Routing Problem


---

## Project Structure

```
fleet_management/
├── app.py                            # Streamlit entry point — home page
├── requirements.txt
├── README.md
├── pages/
│   ├── 1_Map_and_Data.py             # Interactive map, depot/store configuration, fleet allocation
│   ├── 2_MDVRP_Solver.py             # MDVRP solver with animated route visualisation
│   ├── 3_FSMVRP_Optimizer.py         # Fleet optimiser and sensitivity analysis
│   ├── 4_Mathematical_Models.py      # Full mathematical formulations and algorithm documentation
│   ├── 5_Route_Timeline.py           # Step-by-step delivery schedule and pallet tracking
│   └── 6_Conclusions_and_Results.py  # Research conclusions drawn from simulation results
└── utils/
    ├── __init__.py
    ├── data_models.py                # Data classes and Bucharest reference dataset
    ├── mdvrp_algorithms.py           # Nearest Neighbour, Clarke-Wright Savings, 2-opt, refrigeration validation
    ├── fsmvrp_optimizer.py           # Combined Savings heuristic and fleet enumeration optimiser
    └── map_utils.py                  # Folium map builder
```

---

## Installation and Setup

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

The application opens automatically at `http://localhost:8501`.

---

## Mathematical Models

### MDVRP — Objective Function

$$\min \sum_{k \in K} \sum_{(i,j) \in A} c_{ij} \cdot x_{ijk}$$

**Constraints:**
- Each customer is visited exactly once
- Vehicle capacity: `Σ d_i · y_ik ≤ Q_k`
- Flow conservation at each node
- Vehicles depart from and return to their assigned depot
- Vehicle availability per depot: `M_d` constraint (load balancing)

### FSMVRP — Objective Function

$$\min \sum_{t \in T} f_t \cdot n_t + \sum_{k \in K} \sum_{(i,j) \in A} c_{ij} \cdot x_{ijk}$$

### Combined Savings (CS) — FSMVRP Heuristic

$$CS(i,j) = s_{ij} + F(Z_i) + F(Z_j) - F(Z_i + Z_j)$$

where $F(Z)$ is the fixed cost of the smallest vehicle capable of serving demand $Z$.

### Customer–Depot Assignment

$$\text{depot}(i) = \arg\min_{d \in D} \; \text{Haversine}(d, i)$$

---

## Implemented Algorithms

| Algorithm | Complexity | Description |
|---|---|---|
| Nearest Neighbour | O(n²) | Greedy construction: visit the nearest unserved customer at each step |
| Clarke-Wright Savings | O(n² log n) | Merge routes based on `s(i,j) = c(d,i) + c(d,j) - c(i,j)` |
| 2-opt Local Search | O(n²) per iteration | Reverse route sub-sequences to eliminate crossings |
| Combined Savings (CS) | O(n²) per iteration | FSMVRP-aware merging with vehicle fixed-cost integration |
| FSMVRP Enumeration | O(Π N_t^max) | Exact enumeration of fleet compositions for small instances |

---

## Application Modules

### Module 1 — Map & Data
- Depot and customer visualisation on OpenStreetMap
- Interactive fleet allocation per depot, by vehicle type
- Addition of new customers via address geocoding (Nominatim) or manual GPS coordinates
- Europallet specifications and vehicle technical parameters
- Origin–destination distance matrix with colour coding
- Fleet mismatch validation: alerts the user when the selected vehicle type cannot serve all demand categories (ambient/refrigerated)

### Module 2 — MDVRP Solver
- Configurable routing algorithm and vehicle type selection, including Mixed Fleet mode
- Animated routes on map (AntPath) with numbered stops and direction arrows
- Detailed route sequences in depot → customer → depot format
- Side-by-side algorithm comparison with Clarke-Wright Efficiency Index
- Load balancing (`M_d` constraint) and refrigeration assignment validation

### Module 3 — FSMVRP Optimizer
- Automatic demand and distance aggregation from the active network
- Fleet composition optimisation across four vehicle types and three strategic objectives
- Cost breakdown chart (fixed vs. variable costs)
- Top 10 feasible fleet configurations with the optimal solution highlighted
- Sensitivity analysis over the 50%–150% demand range with automatic conclusions
- Combined Savings operational routing with multi-depot support

### Module 4 — Mathematical Models
- Complete MDVRP and FSMVRP formulations with LaTeX notation
- Academic context: problem definitions and practical relevance
- Algorithm comparison (Nearest Neighbour vs. Clarke-Wright Savings)
- Transport performance metrics with formulas

### Module 5 — Route Timeline
- Step-by-step delivery schedule with estimated arrival and departure times per stop
- Dynamic service time calculation based on pallets to be unloaded
- Realistic urban travel time model with peak-hour overhead (signal delay doubling, 30% speed reduction)
- Individual movement cyclograms (distance vs. time) per route
- Multi-trip reload logic for routes that exceed vehicle capacity

### Module 6 — Conclusions & Results
- Research questions answered from simulation output
- Comparison of practical vs. theoretical optimisation benefits across models

---

## Dependencies

| Library | Version | Purpose |
|---|---|---|
| `streamlit` | ≥ 1.32 | Web application framework |
| `folium` | ≥ 0.16 | Interactive map rendering (OpenStreetMap) |
| `streamlit-folium` | ≥ 0.20 | Folium integration within Streamlit |
| `plotly` | ≥ 5.20 | Interactive charts and graphs |
| `pandas` | ≥ 2.0 | Data processing and tabular display |
| `numpy` | ≥ 1.26 | Numerical computations |
| `requests` | ≥ 2.31 | Address geocoding via Nominatim API |

---

## Reference Scenario

The implemented scenario simulates a general merchandise distributor operating in **Bucharest, Romania**:

- **3 depots**: D1 — Bucharest North, D2 — Bucharest South, D3 — Chiajna (Logistics Hub West)
- **20 customers**: stores distributed across all districts and peri-urban areas
- **4 vehicle types**: Small (3.5 t), Medium (7 t), Heavy Duty (24 t), Refrigerated (5 t)
- **Real GPS coordinates** based on Bucharest geography
- **Fleet allocation per depot**: configurable in Map & Data → Depot Directory

---

## Academic Context

This application was developed as part of the following dissertation research:

> *"Scientific Research: Fleet Management for a General Merchandise Distributor"*  
> MSc Transport Management  
> Faculty of Transport — National University of Science and Technology POLITEHNICA Bucharest  
> Academic year 2024–2026

---

## License

This project is provided for academic and educational purposes. All rights reserved. No licence is granted for commercial use, redistribution, or modification without the explicit written consent of the author.

---

*Built with Python · Streamlit · Folium · OpenStreetMap · Plotly*