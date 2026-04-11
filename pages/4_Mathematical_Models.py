"""
Page 4 — Mathematical Models
Full mathematical documentation for MDVRP and FSMVRP.
"""
import streamlit as st
import pandas as pd

st.title("📖 Mathematical Models")
st.markdown("Complete mathematical documentation for the models implemented in this application.")

tab1, tab2, tab3, tab4 = st.tabs(["📐 MDVRP", "🚛 FSMVRP", "🔁 Algorithms", "📏 Performance metrics"])

with tab1:
    st.header("Multi-Depot Vehicle Routing Problem (MDVRP)")
    st.markdown("""
### Definition

The MDVRP is a generalisation of the classical VRP in which **multiple depots** exist.
Each vehicle departs from and returns to the same depot.

### Sets and parameters
    """)
    st.dataframe(pd.DataFrame([
        ["$G = (V, A)$",         "Directed graph of the transport network"],
        ["$V = D \\cup C$",      "Nodes: D = depots, C = customers"],
        ["$D = \\{d_1,...,d_m\\}$", "Set of depots"],
        ["$C = \\{c_1,...,c_n\\}$", "Set of customers"],
        ["$K$",                  "Set of available vehicles"],
        ["$c_{ij}$",             "Cost / distance of arc (i, j) ∈ A"],
        ["$d_i$",                "Demand of customer i (tonnes)"],
        ["$Q_k$",                "Capacity of vehicle k (tonnes)"],
        ["$[a_i, b_i]$",         "Time window for customer i"],
        ["$s_i$",                "Service time at customer i"],
    ], columns=["Symbol", "Description"]), use_container_width=True, hide_index=True)

    st.markdown(r"""
### Decision variables

$$x_{ijk} = \begin{cases} 1 & \text{if vehicle } k \text{ traverses arc } (i,j) \\ 0 & \text{otherwise} \end{cases}$$

$$y_{ik} = \begin{cases} 1 & \text{if vehicle } k \text{ visits customer } i \\ 0 & \text{otherwise} \end{cases}$$

### Objective function

$$\min \sum_{k \in K} \sum_{(i,j) \in A} c_{ij} \cdot x_{ijk}$$

### Constraints

**C1 — Customer coverage** (each customer visited exactly once):
$$\sum_{k \in K} y_{ik} = 1 \quad \forall i \in C$$

**C2 — Vehicle capacity:**
$$\sum_{i \in C} d_i \cdot y_{ik} \leq Q_k \quad \forall k \in K$$

**C3 — Flow conservation** (route continuity):
$$\sum_{j \in V} x_{ijk} = \sum_{j \in V} x_{jik} = y_{ik} \quad \forall i \in C, \forall k \in K$$

**C4 — Depot departure and return:**
$$\sum_{j \in C} x_{d(k)jk} = \sum_{j \in C} x_{jd(k)k} = 1 \quad \forall k \in K$$

**C5 — Sub-tour elimination (MTZ):**
$$u_{ik} - u_{jk} + Q_k \cdot x_{ijk} \leq Q_k - d_j \quad \forall i,j \in C, i \neq j, \forall k \in K$$

**C6 — Integrality:**
$$x_{ijk} \in \{0,1\}, \quad y_{ik} \in \{0,1\}$$

### Customer-Depot Assignment

$$\text{depot}(i) = \arg\min_{d \in D} \; \text{dist}(d, i) \quad \forall i \in C$$

where $\text{dist}(d,i)$ is the Haversine distance:
$$\text{dist} = 2R \arcsin\!\sqrt{\sin^2\!\frac{\Delta\phi}{2} + \cos\phi_1\cos\phi_2\sin^2\!\frac{\Delta\lambda}{2}}$$
    """)

with tab2:
    st.header("Fleet Size and Mix VRP (FSMVRP)")
    st.markdown(r"""
### Objective function

$$\min \sum_{t \in T} f_t \cdot n_t + \sum_{k \in K} \sum_{(i,j) \in A} c_{ij} \cdot x_{ijk}$$

### Constraints

**Demand coverage:**
$$\sum_{t \in T} n_t \cdot Q_t \geq D_{\text{total}}$$

**Vehicle availability:**
$$0 \leq n_t \leq N_t^{\max} \quad \forall t \in T$$

**Maximum fleet size:**
$$\sum_{t \in T} n_t \leq K^{\max}$$

**Integrality:**
$$n_t \in \mathbb{Z}_{\geq 0} \quad \forall t \in T$$

### Detailed total cost

$$C_{\text{total}} = \underbrace{\sum_{t} f_t \cdot n_t}_{\text{fixed cost}} + \underbrace{\sum_{t} n_t \cdot c_t^{km} \cdot L_t}_{\text{variable cost}}$$

where $L_t$ = average distance travelled by a vehicle of type $t$.

### Key performance indicators

$$\text{Fleet utilization} = \frac{D_{\text{total}}}{\sum_t n_t \cdot Q_t} \times 100\%$$

$$\text{Cost per tonne} = \frac{C_{\text{total}}}{D_{\text{total}}}$$
    """)

with tab3:
    st.header("Implemented algorithms")

    st.subheader("1. Clarke-Wright Savings (1964)")
    st.markdown(r"""
**Saving** obtained by merging the routes of customers $i$ and $j$:

$$s(i,j) = c(d,i) + c(d,j) - c(i,j)$$

**Algorithm steps:**
1. Initialise: individual routes $r_i = \{d, i, d\}$ for each customer $i$
2. Compute all savings $s(i,j)$
3. Sort savings in descending order: $s(i_1,j_1) \geq s(i_2,j_2) \geq \ldots$
4. For each pair $(i,j)$ with $s > 0$:
   - If $i$ is last in its route and $j$ is first in its route
   - And $\text{load}(r_i) + \text{load}(r_j) \leq Q$
   - Then merge: $r_{ij} = r_i \setminus \{d\} \cup r_j$

**Complexity:** $O(n^2 \log n)$
    """)

    st.subheader("2. Nearest Neighbor Heuristic")
    st.markdown(r"""
**Algorithm steps:**
1. Start from depot $d$
2. At each step, select the nearest unvisited feasible customer $j^*$:
   $$j^* = \arg\min_{j \in \text{unvisited}} c(i, j) \quad \text{s.t. } \text{load} + d_j \leq Q$$
3. If no feasible customer exists → close route, open new route
4. Repeat until all customers are served

**Complexity:** $O(n^2)$
    """)

    st.subheader("3. 2-opt Local Search")
    st.markdown(r"""
**Local improvement:** reversing segment $[i{+}1 \ldots j]$ reduces distance if:

$$c(r_i, r_{i+1}) + c(r_j, r_{j+1}) > c(r_i, r_j) + c(r_{i+1}, r_{j+1})$$

Repeat until no improving move exists.

**Complexity per iteration:** $O(n^2)$
    """)

with tab4:
    st.header("Performance metrics")
    st.markdown(r"""
| Metric | Formula | Description |
|---|---|---|
| Total distance | $\sum_k \sum_{(i,j)} c_{ij} x_{ijk}$ | Total km driven by the fleet |
| Total cost | $\sum_k (f_k + \sum_{ij} c_{ij}^{km} x_{ijk})$ | Full cost (fixed + variable) |
| Capacity utilization | $\frac{\sum_i d_i y_{ik}}{Q_k} \times 100\%$ | Vehicle load ratio |
| Cost per tonne delivered | $\frac{C_{\text{total}}}{D_{\text{total}}}$ | Economic efficiency |
| Number of routes | $|K_{\text{used}}|$ | Vehicles actually deployed |

### Clarke-Wright efficiency index

$$\text{EI}_{CW} = \frac{d_{\text{NN}} - d_{\text{CW}}}{d_{\text{NN}}} \times 100\%$$

where $d_{\text{NN}}$ = Nearest Neighbor total distance, $d_{\text{CW}}$ = Clarke-Wright total distance.

### Haversine distance (used throughout the application)

$$d = 2R \arcsin\sqrt{\sin^2\!\frac{\varphi_2-\varphi_1}{2} + \cos\varphi_1\cos\varphi_2\sin^2\!\frac{\lambda_2-\lambda_1}{2}}$$

with $R = 6{,}371$ km (mean Earth radius).
    """)
