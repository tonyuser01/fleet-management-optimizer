"""
Page 4 — Mathematical Models
Mathematical documentation for MDVRP and FSMVRP.
"""
import streamlit as st
import pandas as pd

st.title("📖 Mathematical Models")
st.markdown("Complete mathematical documentation for the models implemented in this application.")

tab1, tab2, tab3, tab4 = st.tabs([
    "📐 MDVRP",
    "🚛 FSMVRP",
    "🔁 Algorithms",
    "📏 Performance Metrics"
])

# ── TAB 1: MDVRP ─────────────────────────────────────────────────────────────
with tab1:
    st.header("Multi-Depot Vehicle Routing Problem (MDVRP)")

    st.markdown(r"""
The MDVRP is formally defined on a complete graph $G = (V, E)$, where $V$ is the set of nodes
representing depots and customers, and $E$ is the set of arcs representing feasible routes
connecting each pair of nodes.

The node set $V$ is partitioned into two distinct subsets:
- $C = \{1, 2, \ldots, n\}$ — the set of **customers**, each with a specific demand $d_i$
- $D = \{n+1, \ldots, n+m\}$ — the set of **depots**
- $A$ — the set of arcs, where each arc $(i, j)$ represents a possible route from node $i$ to node $j$
    """)

    st.markdown("---")
    st.subheader("Sets, Parameters and Constraints")

    st.markdown(r"""
| Symbol | Description |
|---|---|
| $c_{i,j}$ | Weight of arc $(i,j)$: transportation cost (distance or travel time) from node $i$ to $j$ |
| $c_{i,j} = c_{j,i}$ | Symmetric VRP — standard road network distributions |
| $c_{i,j} \neq c_{j,i}$ | Asymmetric VRP — one-way streets or time-dependent travel costs |
| $d_i$ | Demand of customer $i$. For depots: $d_i = 0$ for all $i \in D$ |
| $Q_k$ | Maximum load capacity of vehicle $k$. Homogeneous fleet: $Q_k = Q$ for all $k$ |
| $m_d$ | Maximum number of vehicles available at depot $d$ (hard resource constraint) |
| $T_{\max}$ | Maximum allowable travel cost/time per route (driver shift or fuel range limit) |
| $u_i$ | Auxiliary MTZ variable: cumulative load/position along route at node $i$ |
""")

    st.markdown("---")
    st.subheader("Decision Variables")
    st.markdown(r"""
$$x_{i,j,k} = \begin{cases} 1 & \text{if vehicle } k \text{ traverses arc } (i,j) \\ 0 & \text{otherwise} \end{cases}$$

Auxiliary variables $u_i$ are used in the MTZ sub-tour elimination constraints to track the
cumulative load or position along a route, ensuring every route is connected to a depot.
    """)

    st.markdown("---")
    st.subheader("Objective Function")
    st.markdown(r"""
Minimize total routing cost across all vehicles and arcs:

$$\min \quad Z = \sum_{k \in K} \sum_{(i,j) \in A} c_{i,j} \cdot x_{i,j,k} \tag{1}$$
    """)

    st.markdown("---")
    st.subheader("Constraints")

    st.markdown("**C1 — Unique Customer Visit** (each customer visited exactly once):")
    st.markdown(r"""
$$\sum_{k \in K} \sum_{j \in V} x_{i,j,k} = 1 \quad \forall i \in C \tag{2}$$
    """)

    st.markdown("**C2 — Flow Conservation** (vehicle entering a node must also depart from it):")
    st.markdown(r"""
$$\sum_{j \in V} x_{i,j,k} = \sum_{j \in V} x_{j,i,k} \quad \forall i \in V,\; \forall k \in K \tag{3}$$
    """)

    st.markdown("**C3 — Capacity Constraint** (total demand on a route cannot exceed vehicle capacity):")
    st.markdown(r"""
$$\sum_{i \in C} d_i \cdot \sum_{j \in V} x_{i,j,k} \leq Q_k \quad \forall k \in K \tag{4}$$
    """)

    st.markdown(r"""
**C4 — Total Route Cost/Length Constraint** (total travel cost of a route cannot exceed $T_{\max}$,
representing operational limits such as driver shift durations or maximum fuel range):

$$\sum_{(i,j) \in A} c_{i,j} \cdot x_{i,j,k} \leq T_{\max} \quad \forall k \in K \tag{5}$$
    """)

    st.markdown("**C5 — Depot Integrity and Vehicle Availability** (each route originates from and returns to the same depot):")
    st.markdown(r"""
$$\sum_{j \in C} x_{d(k),j,k} = 1 \quad \forall k \in K \tag{6}$$

$$\sum_{i \in C} x_{i,d(k),k} = 1 \quad \forall k \in K \tag{7}$$

$$\sum_{k \in K_d} \sum_{j \in C} x_{d,j,k} \leq m_d \quad \forall d \in D \tag{8}$$
    """)

    st.markdown("**C6 — Sub-tour Elimination — MTZ Constraints** (prevents isolated cycles not connected to a depot):")
    st.markdown(r"""
$$u_i - u_j + Q_k \cdot x_{i,j,k} \leq Q_k - d_j \quad \forall i,j \in C,\; i \neq j,\; \forall k \in K \tag{9}$$

$$d_i \leq u_i \leq Q_k \quad \forall i \in C,\; \forall k \in K \tag{10}$$

In compact form, where $N$ represents the total number of vehicles:

$$u_i - u_j + N \cdot x_{i,j,k} \leq N - 1 \quad \forall i,j \in C,\; i \neq j \tag{11}$$
    """)

    st.markdown("**C7 — Integrality:**")
    st.markdown(r"""
$$x_{i,j,k} \in \{0, 1\} \quad \forall i,j \in V,\; \forall k \in K \tag{12}$$
    """)

    st.markdown("---")
    st.subheader("Customer-Depot Assignment")
    st.markdown(r"""
Each customer is assigned to the nearest depot using the Haversine great-circle distance:

$$\text{depot}(i) = \arg\min_{d \in D} \;\text{dist}(d, i) \quad \forall i \in C$$

$$\text{dist}(d, i) = 2R \arcsin\sqrt{\sin^2\frac{\Delta\phi}{2} + \cos\phi_d\cos\phi_i\sin^2\frac{\Delta\lambda}{2}}$$

where $R = 6{,}371$ km is the mean Earth radius.
    """)

# ── TAB 2: FSMVRP ────────────────────────────────────────────────────────────
with tab2:
    st.header("Fleet Size and Mix Vehicle Routing Problem (FSMVRP)")

    st.markdown("""
The FSMVRP extends the classical VRP by introducing **vehicle heterogeneity as a decision variable**.
The objective is to minimize total costs consisting of fixed acquisition/leasing costs and
vehicle-dependent operational costs.

The key distinction from the classical VRP lies in the cost structure:
- **Fixed costs $F_k$** — acquisition or leasing costs for each vehicle type $k$ that leaves the depot (node 0) to start a route
- **Variable costs $c_{ijk}$** — operational cost of traversing arc $(i,j)$ with vehicle type $k$,
  typically proportional to distance and vehicle-specific consumption rates
    """)

    st.markdown("---")
    st.subheader("Objective Function")
    st.markdown(r"""
$$\min \quad Z = \sum_{k \in K} \left( F_k \cdot \sum_{j \in C} x_{0,j,k} \right) + \sum_{k \in K} \sum_{(i,j) \in A} c_{i,j,k} \cdot x_{i,j,k} \tag{1}$$

The first term sums the **fixed cost** $F_k$ for every vehicle $k$ that departs from the depot (node 0).
The second term captures the **variable routing costs** across all arcs.
    """)

    st.markdown("---")
    st.subheader("Constraints")

    st.markdown("**C1 — Customer Service** (each customer visited exactly once by any vehicle type):")
    st.markdown(r"""
$$\sum_{k \in K} \sum_{j \in V} x_{i,j,k} = 1 \quad \forall i \in C \tag{2}$$
    """)

    st.markdown("**C2 — Flow Conservation** (vehicle $k$ entering customer $i$ must also depart from it):")
    st.markdown(r"""
$$\sum_{j \in V} x_{i,j,k} = \sum_{j \in V} x_{j,i,k} \quad \forall i \in C,\; \forall k \in K \tag{3}$$
    """)

    st.markdown("**C3 — Vehicle Capacity Constraint** (total demand on a route must not exceed vehicle capacity):")
    st.markdown(r"""
$$\sum_{i \in C} d_i \cdot y_{i,k} \leq Q_k \quad \forall k \in K \tag{4}$$

where $y_{i,k}$ is the cumulative demand serviced after reaching customer $i$ on vehicle $k$'s route.
    """)

    st.markdown("**C4 — Sub-tour Elimination** (prevents isolated loops using commodity flow variables $f_{ijk}$):")
    st.markdown(r"""
$$\sum_{j \in V} f_{i,j,k} - \sum_{j \in V} f_{j,i,k} = d_i \cdot \sum_{j \in V} x_{i,j,k} \quad \forall i \in C,\; \forall k \in K \tag{5}$$

$$0 \leq f_{i,j,k} \leq Q_k \cdot x_{i,j,k} \quad \forall (i,j) \in A,\; \forall k \in K \tag{6}$$
    """)

    st.markdown("**C5 — Integrity and Fleet Availability:**")
    st.markdown(r"""
$$x_{i,j,k} \in \{0, 1\} \quad \forall i,j \in V,\; \forall k \in K \tag{7}$$

$$\sum_{j \in V} x_{0,j,k} \leq 1 \quad \forall k \in K \tag{8}$$

$$\sum_{k \in K_t} \sum_{j \in C} x_{0,j,k} \leq M_t \quad \forall t \in T \tag{9}$$

where $M_t$ is the maximum number of vehicles of type $t$ available.
    """)

    st.markdown("---")
    st.subheader("Cost Structure: VRP vs FSMVRP")
    st.markdown(r"""
| Model | Cost type | Objective | Key difference |
|---|---|---|---|
| Classical VRP | Variable only | $\sum c_{i,j} \cdot x_{i,j,k}$ | Homogeneous fleet — cost = distance |
| FSMVRP | Fixed + Variable | $\sum F_k \cdot x_{0,j,k} + \sum c_{i,j,k} \cdot x_{i,j,k}$ | Heterogeneous fleet — vehicle type is a decision variable |
""")

    st.warning("""
**Key trade-off:** A solution that minimizes total distance may **not** minimize total cost
if it requires deploying many small vehicles instead of fewer large vehicles.
    """)

    st.markdown("---")
    st.subheader("Combined Savings (CS) Approach for FSMVRP")
    st.markdown(r"""
Traditional Clarke-Wright Savings is **insufficient** for FSMVRP because it focuses solely on
distance and ignores fixed vehicle costs. Standard CW tends to merge routes until the capacity
of the largest vehicle is reached, even when this is not cost-effective.

The **Combined Savings (CS)** approach integrates vehicle costs directly into the savings formula:

$$CS(i,j) = c(d,i) + c(d,j) - c(i,j) + \left[ F_{k^*(i)} + F_{k^*(j)} - F_{k^*(i \cup j)} \right]$$

where $F_{k^*(\cdot)}$ is the fixed cost of the **smallest vehicle type capable of serving**
the cumulative demand of the route.

This ensures that merging two routes is only beneficial when the combined routing saving
**and** the fleet-cost saving together justify the operation.

> Research also shows that energy consumption is load-dependent, adding further incentive
> to optimize vehicle–load combinations beyond simple distance minimization.
    """)

    st.markdown("---")
    st.subheader("Fleet Optimization KPIs")
    st.markdown(r"""
$$\text{Fleet utilization} = \frac{D_{\text{total}}}{\sum_{t \in T} n_t \cdot Q_t} \times 100\%$$

$$\text{Cost per tonne} = \frac{C_{\text{total}}}{D_{\text{total}}}$$

$$C_{\text{total}} = \underbrace{\sum_{t \in T} F_t \cdot n_t}_{\text{fixed cost}} + \underbrace{\sum_{t \in T} n_t \cdot c_t^{km} \cdot L_t}_{\text{variable cost}}$$
    """)

# ── TAB 3: ALGORITHMS ─────────────────────────────────────────────────────────
with tab3:
    st.header("Implemented Algorithms")

    st.subheader("1. Clarke-Wright Savings (1964)")
    st.markdown(r"""
**Saving** obtained by merging the individual routes of customers $i$ and $j$:

$$s(i,j) = c(d,i) + c(d,j) - c(i,j)$$

**Steps:**
1. **Initialise** — create one individual route per customer: $r_i = \{d, i, d\}$ for all $i \in C$
2. **Compute** all pairwise savings $s(i,j)$
3. **Sort** descending: $s(i_1,j_1) \geq s(i_2,j_2) \geq \ldots$
4. **Merge** — for each pair $(i,j)$, if:
   - $i$ is the **last** customer in its route, $j$ is the **first** in its route
   - Combined load $\leq Q_k$
   - Then merge: $r_{ij} = r_i \setminus \{d\} \cup r_j$

**Complexity:** $O(n^2 \log n)$

**Limitation for FSMVRP:** ignores fixed vehicle costs → use Combined Savings (CS) instead.
    """)

    st.subheader("2. Nearest Neighbor Heuristic")
    st.markdown(r"""
1. Start at depot $d$
2. Select nearest feasible unvisited customer:
$$j^* = \arg\min_{j \in \text{unvisited}} c(i,j) \quad \text{s.t.} \quad \text{load} + d_j \leq Q_k$$
3. No feasible customer → close route, open new route from depot
4. Repeat until all customers are served

**Complexity:** $O(n^2)$
    """)

    st.subheader("3. 2-opt Local Search")
    st.markdown(r"""
Reverses segment $[i{+}1 \ldots j]$ if the swap reduces total distance:

$$c(r_i, r_{i+1}) + c(r_j, r_{j+1}) > c(r_i, r_j) + c(r_{i+1}, r_{j+1})$$

Repeat until no improving move exists. **Complexity per iteration:** $O(n^2)$
    """)

    st.subheader("4. Customer-Depot Assignment (MDVRP)")
    st.markdown(r"""
Before routing, each customer is assigned to its nearest depot:

$$\text{depot}(i) = \arg\min_{d \in D} \;\text{Haversine}(d, i) \quad \forall i \in C$$

Clarke-Wright and Nearest Neighbor are then applied independently per depot.
    """)

# ── TAB 4: METRICS ────────────────────────────────────────────────────────────
with tab4:
    st.header("Performance Metrics")
    st.markdown(r"""
| Metric | Formula | Description |
|---|---|---|
| Total distance | $\sum_k \sum_{(i,j)} c_{i,j} \cdot x_{i,j,k}$ | Total km driven by the fleet |
| Total cost | $\sum_k F_k \cdot x_{0,j,k} + \sum_k \sum_{i,j} c_{i,j,k} \cdot x_{i,j,k}$ | Full cost (fixed + variable) |
| Capacity utilization | $\frac{\sum_i d_i \cdot y_{i,k}}{Q_k} \times 100\%$ | Vehicle load ratio per route |
| Fleet utilization | $\frac{D_{\text{total}}}{\sum_t n_t \cdot Q_t} \times 100\%$ | Overall fleet load ratio |
| Cost per tonne | $\frac{C_{\text{total}}}{D_{\text{total}}}$ | Economic efficiency indicator |
| Routes used | $\lvert K_{\text{used}} \rvert$ | Vehicles actually deployed |

### Clarke-Wright Efficiency Index

$$\text{EI}_{CW} = \frac{d_{\text{NN}} - d_{\text{CW}}}{d_{\text{NN}}} \times 100\%$$

where $d_{\text{NN}}$ = Nearest Neighbor total distance, $d_{\text{CW}}$ = Clarke-Wright total distance.

### Haversine Distance

Used throughout the application for all real-coordinate calculations:

$$\text{dist}(i,j) = 2R \arcsin\sqrt{\sin^2\frac{\varphi_j - \varphi_i}{2} + \cos\varphi_i \cos\varphi_j \sin^2\frac{\lambda_j - \lambda_i}{2}}$$

$R = 6{,}371$ km (mean Earth radius), $\varphi$ = latitude, $\lambda$ = longitude.
    """)
