"""
Page 6 — Conclusions & Results
Academic conclusions based on the MDVRP and FSMVRP models implemented in this application.
"""
import streamlit as st
from utils.data_models import DEPOTS_BUCHAREST, CUSTOMERS_BUCHAREST, VEHICLE_FLEET

st.title("📊 Conclusions & Results")
st.markdown(
    "This page presents the academic conclusions of the dissertation research on "
    "fleet management optimization for a general merchandise distributor."
)

# ── Session state ─────────────────────────────────────────────────────────────
depots        = st.session_state.get("depots",        DEPOTS_BUCHAREST)
customers     = st.session_state.get("customers",     CUSTOMERS_BUCHAREST)
vehicle_types = st.session_state.get("vehicle_types", VEHICLE_FLEET)
total_demand  = sum(c.demand for c in customers)

# ── Why Mathematical Models in Logistics? ────────────────────────────────────
st.markdown("---")
st.subheader("1. Why Use Mathematical Models in Transportation and Logistics?")
st.markdown("""
Logistics systems involve multiple variables — **time, cost, capacity, and constraints**. 
Mathematical models provide structured tools for solving problems like route planning, 
delivery scheduling, and inventory management more efficiently than manual or intuitive methods.

Three fundamental decisions must be made in every distribution cycle:
""")

c1, c2, c3 = st.columns(3)
with c1:
    st.info("""
**⏰ When to serve?**

Determine the optimal time window for each delivery, respecting store operating hours 
and driver shift constraints.
    """)
with c2:
    st.info("""
**📦 How much to deliver?**

Calculate the exact quantity to deliver at each visit, balancing vehicle capacity 
against customer demand and inventory levels.
    """)
with c3:
    st.info("""
**🗺️ Which routes to use?**

Design delivery sequences that minimize total distance and cost while respecting 
all operational constraints across the network.
    """)

# ── MDVRP ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("2. Multi-Depot Vehicle Routing Problem (MDVRP)")
st.markdown("""
**How to simultaneously assign stores to depots and optimize delivery routes?**

The MDVRP is a generalization of the classical VRP where the vehicle fleet is distributed 
across multiple depots. It represents an optimization framework for retailers operating 
dispersed distribution networks, where a **single centralized depot is neither economically 
viable nor operationally feasible**.

The primary goal is the minimization of total operational costs — total distance, time, 
or travel cost incurred by all vehicles across all routes.
""")

st.markdown("**The model satisfies the following conditions:**")

col1, col2 = st.columns(2)
with col1:
    st.markdown("""
- ✅ **Unique Customer Visit** — each store is served exactly once
- ✅ **Flow Conservation** — vehicles entering a node must also depart
- ✅ **Capacity Constraint** — total load cannot exceed vehicle capacity
    """)
with col2:
    st.markdown("""
- ✅ **Depot Integrity** — routes originate and terminate at the same depot
- ✅ **Vehicle Availability ($M_d$)** — number of routes per depot ≤ available vehicles
- ✅ **Subtour Elimination** — no isolated cycles disconnected from depots
    """)

st.markdown("**The MDVRP framework answers the following strategic questions:**")
st.markdown(f"""
| Question | Answer in this application |
|---|---|
| How many depots to operate? | **{len(depots)} depots** across Bucharest metropolitan area |
| Where should they be located? | North, South, and Ilfov-Otopeni — covering all distribution zones |
| Which customers should each depot serve? | Nearest-depot assignment via Haversine distance |
| How should vehicles be routed? | Clarke-Wright Savings + 2-opt local search |
| How to respect fleet availability? | Load balancing enforces $M_d$ constraint per depot |
""")

# ── FSMVRP ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("3. Fleet Size and Mix Vehicle Routing Problem (FSMVRP)")

vt_names = ", ".join(vt.name for vt in vehicle_types)
st.markdown(f"""
Unlike the classical VRP which assumes a **homogeneous fleet**, the FSMVRP acknowledges 
that most logistics providers operate **heterogeneous fleets** comprising vehicles of 
different capacities, costs, and operational characteristics.

The FSMVRP seeks to determine not only the optimal routes for serving customers but also 
the **optimal composition of the fleet** — how many vehicles of each type should be 
deployed to minimize total system cost.

Current fleet in this application: **{vt_names}**
""")

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Key distinctions from classical VRP:**")
    st.markdown("""
- In VRP, all vehicles are **identical** — one capacity, one cost
- FSMVRP acknowledges that different vehicle types offer **distinct advantages**:
  - **Economies of scale** — larger vehicles cost less per tonne-km
  - **Operational flexibility** — smaller vehicles navigate urban areas better
  - **Environmental compliance** — different emission profiles per vehicle class
    """)
with col2:
    st.markdown("**Cost structure:**")
    st.markdown("""
By integrating **fixed costs** (leasing/amortization) and **variable costs** (fuel/energy), 
the model justifies the use of a mixed fleet:

$$\\min Z = \\underbrace{\\sum_k F_k \\cdot n_k}_{\\text{fixed}} + \\underbrace{\\sum_k c_k \\cdot d_k}_{\\text{variable}}$$

This balance between vehicle count and total operational cost ensures the network 
can handle **synchronized deliveries** and **sustainable urban replenishment** 
while maintaining profitability.
    """)

# ── Integration Conclusions ───────────────────────────────────────────────────
st.markdown("---")
st.subheader("4. Integration of Models — Key Conclusions")
st.markdown(
    "The integration of MDVRP and FSMVRP models and their constraints leads to the "
    "following conclusions:"
)

c1, c2 = st.columns(2)
with c1:
    st.success("""
**🎯 Strategic Versatility**

The combined MDVRP-FSMVRP framework adapts to different distribution scenarios — 
from dense urban delivery with small vehicles to high-volume inter-depot transfers 
with heavy trucks. The model selects the right vehicle type for each route 
automatically, based on demand and cost structure.
    """)
    st.success("""
**🔄 Coordination**

Multi-depot routing requires coordinated assignment of customers to depots and
vehicles to routes. The load balancing mechanism ($M_d$ constraint) ensures that 
no single depot is overloaded, distributing the delivery workload proportionally 
across all available fleet resources.
    """)

with c2:
    st.success("""
**🗺️ Territorial Efficiency**

By assigning each customer to the nearest depot (Haversine assignment), the model 
minimizes unnecessary cross-city travel. This territorial partitioning reduces 
total fleet distance and improves delivery time windows — directly impacting 
customer satisfaction and fuel consumption.
    """)
    st.success("""
**🛡️ Network Resilience**

The multi-depot structure provides operational resilience — if one depot faces
capacity constraints or disruptions, the load balancing algorithm can redistribute 
customers to alternative depots. The $M_d$ constraint enforcement ensures that the 
routing plan remains executable with the physical fleet available at each location.
    """)

# ── Application Summary ───────────────────────────────────────────────────────
st.markdown("---")
st.subheader("5. Application to the Bucharest Distribution Network")
st.markdown(f"""
This application implements the theoretical MDVRP and FSMVRP frameworks on a realistic 
scenario for a general merchandise distributor operating in **Bucharest, Romania**:
""")

col1, col2, col3 = st.columns(3)
col1.metric("Depots", len(depots), "Bucharest metropolitan area")
col2.metric("Active stores", len(customers), "Across all districts")
col3.metric("Vehicle types", len(vehicle_types), "Heterogeneous fleet")

st.markdown(f"""
The network covers **{total_demand:.1f} tonnes** of daily demand across stores in all 
Bucharest districts and peri-urban areas, served by a mixed fleet of {vt_names}.

The interactive application demonstrates that the mathematical models are not merely 
theoretical constructs — they are **practical decision-support tools** that fleet 
managers can use daily to answer the three fundamental distribution questions: 
*when, how much, and which routes*.
""")

# ── Final Statement ───────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("6. Final Conclusions")
st.markdown("""
The research demonstrates that mathematical optimization of fleet management produces 
structurally sound and operationally feasible distribution plans. The key findings are:

**1. Mathematical models are essential** for managing the combinatorial complexity of 
multi-depot, heterogeneous-fleet distribution — problems that are NP-hard and cannot 
be solved optimally by manual planning at real-world scale.

**2. The MDVRP framework** provides a rigorous method for simultaneously solving 
customer-depot assignment and route optimization, respecting all operational constraints 
(capacity, time windows, depot availability).

**3. The FSMVRP extension** adds strategic value by optimizing fleet composition — 
recognizing that the choice of vehicle types directly impacts both fixed and variable 
costs, and that minimizing distance alone does not minimize total cost.

**4. The integration of both models** delivers Strategic Versatility, Coordination, 
Territorial Efficiency, and Network Resilience — the four pillars of an effective 
urban distribution strategy for general merchandise.

**5. The practical implementation** in an interactive web application confirms that 
these models are accessible, interpretable, and directly applicable to real-world 
fleet management decisions.
""")

st.caption(
    "Scientific Research: Fleet Management for a General Merchandise Distributor · "
    "MSc Transport Management · Faculty of Transport · National University of Science and Technology POLITEHNICA Bucharest · 2024-2026"
)