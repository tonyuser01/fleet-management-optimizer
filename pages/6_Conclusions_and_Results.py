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

st.markdown("---")
st.subheader("Research Framework")
st.markdown("""
This study is guided by the following research questions:

1. **What are the main deficiencies in current fleet management practices within the distribution sector, and how do they impact operational performance and costs?**
2. **How can mathematical models be applied to address these deficiencies in distribution?**
3. **To what extent can the practical implementation of these models translate theoretical optimization into operational improvements for a distributor?**

The practical application developed as part of this research tries to show how theoretical optimization models can be directly implemented to improve route planning, reduce operational costs, and support more efficient delivery scheduling.
""")

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

In each of these scenarios, the MDVRP framework tries to answer the questions: **How many depots should we operate? Where should they be located? Which customers should each depot serve? How should vehicles be routed from each depot to maximize efficiency by time and cost?**
""")

st.markdown("**The MDVRP framework answers the following questions:**")
st.markdown(f"""
| Question | Answer in this application |
|---|---|
| How many depots to operate? | **{len(depots)} depots** across Bucharest metropolitan area |
| Where should they be located? | North, South, and Ilfov-Otopeni — covering all distribution zones |
| Which customers should each depot serve? | Nearest-depot assignment via Haversine distance |
| How should vehicles be routed? | Clarke-Wright Savings + 2-opt local search |
| How to respect fleet availability? | Load balancing enforces M_d constraint per depot |
""")

# ── FSMVRP ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("3. Fleet Size and Mix Vehicle Routing Problem (FSMVRP)")
st.markdown("""
Unlike the classical VRP which assumes a **homogeneous fleet**, the FSMVRP acknowledges 
that most logistics providers operate **heterogeneous fleets** comprising vehicles of 
different capacities, costs, and operational characteristics.

The FSMVRP seeks to determine not only the optimal routes for serving customers but also 
the **optimal composition of the fleet** — how many vehicles of each type should be 
deployed to minimize total system cost.
""")

# ── Integration Conclusions ───────────────────────────────────────────────────
st.markdown("---")
st.subheader("4. Integration of Models")
st.markdown("The integration of models leads to the following conclusions:")

st.info("""
1. **Fleet managers should consider the Total Cost of Ownership**, mixing high fixed acquisition costs with load-dependent variable operational costs.
2. **A heterogeneous fleet** allows a distributor to function in diverse environments from high volume replenishment to sustainable urban delivery.
3. **MDVRP is useful for minimizing the total distance** across a national network preventing overlapping routes and reducing miles.
4. **A multi-depot configuration** provides a safety net against operational risks and stores can be dynamically reallocated between hubs during supply chain disruptions.
""")

# ── Final Statement ───────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("5. Final Conclusions")
st.markdown("""
The application developed in this research demonstrates that the MDVRP and FSMVRP models 
are not only theoretically sound but also practically implementable and operationally useful.
""")

st.markdown("**Returning to the research questions:**")

st.markdown(f"""
| Research Question | Conclusion |
|---|---|
| What are the main deficiencies in current fleet management practices? | Unstructured route planning, homogeneous fleet assumptions, and single-depot configurations generate avoidable costs through route overlaps, under-utilised capacity, and excessive empty running. |
| How can mathematical models address these deficiencies? | The MDVRP provides a structured framework for simultaneous depot-customer assignment and route optimisation across {len(depots)} depots, while the FSMVRP determines the optimal fleet composition across {len(vehicle_types)} vehicle types to minimise total ownership and operational cost. |
| To what extent can these models translate theory into operational improvements? | The implemented application confirms that both models are directly applicable to a real distribution network and can predict, to a certain extent, operational outcomes and identify improvement opportunities. However, the models operate under deterministic assumptions and cannot fully account for the human factor — driver behaviour, real-time decision-making, and on-site variability — which remain outside the scope of mathematical optimisation. |
""")

st.caption(
    "Scientific Research: Fleet Management for a General Merchandise Distributor · "
    "MSc Transport Management · Faculty of Transport · Politehnica University of Bucharest · 2024-2026"
)