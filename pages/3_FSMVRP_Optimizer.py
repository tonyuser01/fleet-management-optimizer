"""
Page 3 — FSMVRP Fleet Optimizer
Optimize fleet composition for minimum cost, minimum vehicles, or balanced utilization.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Union, Optional

from utils.data_models import VEHICLE_FLEET, DEPOTS_BUCHAREST, CUSTOMERS_BUCHAREST
from utils.mdvrp_algorithms import get_transport_stats
from utils.fsmvrp_optimizer import optimize_fleet, sensitivity_analysis, solve_fsmvrp_multi_depot, FleetSolution
from utils.map_utils import build_map, map_to_html
from streamlit.components.v1 import html as st_html

st.title("🚛 FSMVRP — Fleet Size and Mix Optimizer")
st.markdown("Determine the optimal fleet composition to minimize total distribution cost.")

with st.expander("📖 Theoretical Framework: Fleet Size and Mix VRP"):
    st.markdown(r"""
    ### 1. Introduction
    The Fleet Size and Mix Vehicle Routing Problem (FSMVRP) represents a decision layer in
    distribution network optimization. Unlike the classical VRP which assumes a homogeneous
    fleet, the FSMVRP acknowledges that most logistics providers operate heterogeneous fleets
    comprising vehicles of different capacities, costs, and operational characteristics.
    
    The FSMVRP seeks to determine not only the optimal routes for serving customers but also the optimal composition of the fleet, how many vehicles of each type should be deployed to minimize total system cost.

    ### 2. Mathematical Formulation
    $$\min Z = \sum_{k=1}^{T}{F_k\left(\sum_{j=1}^{n}x_{0jk}\right)}+\sum_{k=1}^{T}\sum_{i=0}^{n}\sum_{j=0}^{n}c_{ijk}\, x_{ijk}$$

    **Cost Structure:**
    - **Fixed costs ($F_k$):** Acquisition costs for each vehicle type $k$ that leaves the depot.
    - **Variable costs ($c_{ijk}$):** Operational cost of traversing arc $(i,j)$ with vehicle $k$.

    ### 3. Combined Savings (CS) Approach
    $$S_{ij}=s_{ij}+F(Z_i)+F(Z_j)-F(Z_i+Z_j)$$
    Where $F(Z)$ is the fixed cost of the smallest vehicle capable of serving demand $Z$.

    ### 4. Optimization Objectives
    - **Minimize Total Cost**: Lowest aggregate cost (Fixed + Variable).
    - **Minimize Vehicles**: Absolute lowest vehicle count — useful when driver availability is the constraint.
    - **Balanced Utilization**: Targets ~85% load factor — operational safety buffer.
    """)

# ── Session state ─────────────────────────────────────────────────────────────
if "vehicle_types" not in st.session_state:
    st.session_state.vehicle_types = VEHICLE_FLEET.copy()
if "depots" not in st.session_state:
    st.session_state.depots = DEPOTS_BUCHAREST.copy()
if "customers" not in st.session_state:
    st.session_state.customers = CUSTOMERS_BUCHAREST.copy()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ FSMVRP Parameters")
    if "customers" in st.session_state and st.session_state.customers:
        auto_demand = round(sum(c.demand for c in st.session_state.customers), 1)
    else:
        auto_demand = 45.0

    total_demand = st.number_input(
        "Total demand to deliver (t)",
        value=float(auto_demand),
        step=0.5,
        help=f"Auto-calculated from active customers: {auto_demand} t. You can override manually."
    )

    # Automatically calculate estimated distance from network data
    if "customers" in st.session_state and "depots" in st.session_state and st.session_state.customers:
        from utils.data_models import haversine
        auto_km = sum(
            min(haversine(c.lat, c.lon, d.lat, d.lon) for d in st.session_state.depots) * 2
            for c in st.session_state.customers
        )
        auto_km = round(auto_km, 0)
    else:
        auto_km = 320.0

    total_km = st.number_input(
        "Estimated total distance (km)",
        value=float(auto_km),
        step=10.0,
        help=f"Auto-calculated from network data: {auto_km:.0f} km (depot→customer×2 for all active customers). You can override manually."
    )
    objective = st.selectbox(
        "Optimization objective",
        ["min_cost", "min_vehicles", "balanced"],
        format_func=lambda x: {
            "min_cost":     "Minimize total cost",
            "min_vehicles": "Minimize number of vehicles",
            "balanced":     "Balanced fleet utilization"
        }[x],
        help="Strategic priority. Note: In this dataset, 'min_cost' and 'min_vehicles' often overlap because larger vehicles are more efficient per tonne."
    )
    max_veh = st.slider("Maximum vehicles allowed", 3, 20, 12)

    # Inventory warning for FSMVRP
    if "customers" in st.session_state and st.session_state.customers:
        has_fridge_demand = any(c.demand_refrigerated > 0 for c in st.session_state.customers)
        has_ambient_demand = any(c.demand_ambient > 0 for c in st.session_state.customers)
        
        available_fridge = any(vt.is_refrigerated and vt.max_available > 0 for vt in st.session_state.vehicle_types)
        available_ambient = any(not vt.is_refrigerated and vt.max_available > 0 for vt in st.session_state.vehicle_types)
        
        if has_fridge_demand and not available_fridge:
            st.warning(
                "⚠️ **Inventory Gap:** You have Refrigerated demand, but **no Refrigerated vehicles** are available "
                "in your fleet (Max Available = 0). Please update fleet allocation in **Map & Data**."
            )
        if has_ambient_demand and not available_ambient:
            st.warning(
                "⚠️ **Inventory Gap:** You have Ambient demand, but **no Ambient vehicles** are available "
                "in your fleet (Max Available = 0). Please update fleet allocation in **Map & Data**."
            )

    run_btn  = st.button("▶ Optimize fleet", type="primary", width='stretch')

# ── Run optimization ──────────────────────────────────────────────────────────
if run_btn:
    with st.spinner("Computing optimal fleet configuration..."):
        best, top20 = optimize_fleet(
            st.session_state.vehicle_types, total_demand, total_km,
            objective=objective, max_vehicles=max_veh
        )
        sens = sensitivity_analysis(st.session_state.vehicle_types, total_demand, total_km)

        if "customers" in st.session_state and st.session_state.customers:
            st.session_state.cs_routes = solve_fsmvrp_multi_depot(
                st.session_state.depots, st.session_state.customers, st.session_state.vehicle_types
            )

    st.session_state.fsm_best  = best
    st.session_state.fsm_top20 = top20
    st.session_state.fsm_sens  = sens

# ── Results ───────────────────────────────────────────────────────────────────
best: Optional[FleetSolution] = st.session_state.get("fsm_best")

if best is not None:
    top20 = st.session_state.fsm_top20
    sens  = st.session_state.fsm_sens

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("💰 Total cost",        f"{best.total_cost:.0f} EUR")
    c2.metric("💶 Fixed cost",        f"{best.fixed_cost:.0f} EUR")
    c3.metric("🛣️ Variable cost",    f"{best.variable_cost:.0f} EUR")
    c4.metric("🚛 Vehicles used",     best.total_vehicles)
    c5.metric("📊 Fleet utilization", f"{best.utilization:.1f}%")

    c1b, c2b, c3b = st.columns(3)
    c1b.metric("📦 Capacity covered", f"{best.total_capacity:.1f} t")
    c2b.metric(
        "💸 Cost per tonne", 
        f"{best.cost_per_ton:.2f} EUR/t",
        help="Derived from the Total System Cost (Fixed + Variable) divided by the Total Demand. It represents the average unit cost to deliver one tonne of merchandise."
    )
    c3b.metric("💡 Surplus capacity", f"{best.total_capacity - total_demand:.1f} t")

    st.markdown("---")
    t_summary, t1, t2, t3, t4, t5 = st.tabs([
        "📋 Executive Summary",
        "🚛 Optimal configuration",
        "📊 Solution comparison",
        "📈 Analysis",
        " Mathematical model",
        "🗺️ CS Routing Results"
    ])

    # ── Executive Summary ─────────────────────────────────────────────────────
    with t_summary:
        st.subheader("Key Performance Indicators (KPIs)")

        cs_routes = st.session_state.get("cs_routes")
        cs_total_cost = sum(r.total_cost for r in cs_routes) if cs_routes else None

        k1, k2, k3 = st.columns(3)
        with k1:
            st.markdown("### 💰 Economic Efficiency")
            st.write(f"**Total Estimated Cost:** {best.total_cost:.0f} EUR")
            st.write(f"**Transport Cost / Ton:** {best.cost_per_ton:.2f} EUR/t")
            if cs_total_cost:
                gap = ((cs_total_cost - best.total_cost) / best.total_cost) * 100
                st.write(f"**Operational Gap:** :red[{gap:+.1f}%]" if gap > 0 else f"**Operational Gap:** :green[{gap:+.1f}%]")
                st.info(f"""
                **What is Operational Gap?**  
                This represents the variance between the **Theoretical Fleet Cost** (calculated using estimated distances) and the **Actual Routing Cost** (calculated by the Combined Savings algorithm). A negative value (e.g., {gap:+.1f}%) means the routing engine found higher efficiencies via consolidation than the initial estimate predicted.
                """)
        with k2:
            st.markdown("### 🚛 Fleet Utilization")
            st.write(f"**Capacity Fill Rate:** {best.utilization:.1f}%")
            st.write(f"**Total Capacity:** {best.total_capacity:.1f} t")
            st.progress(min(best.utilization / 100, 1.0))
        with k3:
            st.markdown("### ⚙️ Resource Allocation")
            st.write(f"**Total Vehicles:** {best.total_vehicles}")
            fixed_ratio = (best.fixed_cost / best.total_cost) * 100
            st.write(f"**Fixed Cost Ratio:** {fixed_ratio:.1f}%")

        st.markdown("---")
        st.markdown("#### 📦 Fleet Inventory Status")
        inventory_data = []
        for vt in st.session_state.vehicle_types:
            used = best.allocation.get(vt.id, 0)
            inventory_data.append({
                "Vehicle Type": vt.name,
                "Used": used,
                "Available": vt.max_available,
                "Remaining": vt.max_available - used,
                "Utilization": f"{(used/vt.max_available*100):.0f}%" if vt.max_available > 0 else "0%"
            })
        st.table(pd.DataFrame(inventory_data))

        st.markdown("---")
        st.markdown("#### Recommendation")
        if best.utilization > 90:
            st.warning("⚠️ **High Utilization:** Fleet near maximum capacity. Any demand increase requires additional vehicles.")
        elif best.utilization < 70:
            st.info("ℹ️ **Underutilized Fleet:** Significant spare capacity. Consider smaller vehicle types or consolidated deliveries.")
        else:
            st.success("✅ **Balanced Fleet:** Good safety margin while maintaining cost-efficiency.")

        if cs_routes:
            st.markdown("---")
            st.markdown("#### 📊 Transport & Traffic Parameters (Operational)")
            t_stats = get_transport_stats(cs_routes)
            st.markdown("""
| Parameter | Value | Description |
|---|---|---|
| 🛣️ Traffic Flow | **{:.1f} km/day** | Total km driven by all vehicles (loaded + empty) |
| 🚛 Transport Flow | **{:.1f} veh·km/day** | Km driven while carrying goods (excludes empty returns) |
| 🔄 Empty Run % | **{:.1f} %** | Share of total distance driven empty (return trips) |
| 📦 Daily Performance | **{:.1f} t·km/day** | Σ(load × distance) — measures total transport work |
""".format(
                t_stats['traffic_flow'],
                t_stats['transport_flow'],
                t_stats['empty_pct'],
                t_stats['performance']
            ))
            st.caption("Parameters calculated from Combined Savings operational routes.")
            st.markdown(f"Operational routing confirmed **{len(cs_routes)} routes** needed with current fleet mix.")

    # ── Optimal configuration ─────────────────────────────────────────────────
    with t1:
        st.subheader("Optimal fleet configuration")
        rows = best.to_dict()
        if rows:
            st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)

        st.markdown("""
**Cost breakdown** shows the proportion of total daily cost attributed to fixed costs 
(vehicle leasing/amortization — paid regardless of distance driven) versus variable costs 
(fuel and maintenance — proportional to km driven). A high fixed cost ratio suggests 
the fleet is underutilized; a high variable cost ratio suggests high operational intensity.
""")
        fig_pie = go.Figure(data=[go.Pie(
            labels=["Fixed cost", "Variable cost"],
            values=[round(best.fixed_cost), round(best.variable_cost)],
            hole=0.45, marker_colors=["#E94560", "#3B8BD4"]
        )])
        fig_pie.update_layout(title="Total cost breakdown", height=280,
                               margin=dict(t=40, b=20, l=20, r=20))
        st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown("""
**Vehicles used by type** shows how many units of each vehicle type are deployed 
in the optimal configuration. The mix reflects the trade-off between capacity 
(fewer large vehicles) and flexibility (more small vehicles) for the current demand level.
""")
        alloc = {vt.name: best.allocation.get(vt.id, 0)
                 for vt in st.session_state.vehicle_types if best.allocation.get(vt.id, 0) > 0}
        fig_bar = go.Figure(data=[go.Bar(
            x=list(alloc.keys()), y=list(alloc.values()),
            marker_color=["#E94560", "#3B8BD4", "#1D9E75", "#BA7517"],
            text=list(alloc.values()), textposition="outside"
        )])
        fig_bar.update_layout(title="Vehicles Used by Type", yaxis_title="Count",
                               height=260, margin=dict(t=40, b=20, l=20, r=20))
        st.plotly_chart(fig_bar, use_container_width=True)

    # ── Solution comparison ───────────────────────────────────────────────────
    with t2:
        st.subheader("Top 10 feasible solutions")
        st.markdown("""
The optimizer evaluates **all feasible combinations** of vehicle types within the 
available fleet inventory. A configuration is feasible if:
- Total fleet capacity ≥ total demand
- Number of vehicles ≤ maximum allowed

Solutions are **ranked by total cost** (fixed + variable). The highlighted row (rank 1) 
is the optimal solution for the selected objective:
- **Minimize total cost** — lowest EUR/day regardless of vehicle count
- **Minimize vehicles** — fewest vehicles, then lowest cost as tiebreaker  
- **Balanced utilization** — closest to 85% load factor, then lowest cost

The scatter plot shows the trade-off between number of vehicles and total cost — 
larger bubbles indicate higher fleet utilization.
""")
        if top20 and not isinstance(top20[0], str):
            rows_top = []
            for i, sol in enumerate(top20[:10]):
                if isinstance(sol, str):
                    continue
                alloc_str = ", ".join(
                    f"{sol.allocation.get(vt.id, 0)}×{vt.name.split('(')[0].strip()}"
                    for vt in st.session_state.vehicle_types if sol.allocation and sol.allocation.get(vt.id, 0) > 0
                )
                rows_top.append({
                    "Rank": i+1, "Configuration": alloc_str,
                    "Vehicles": sol.total_vehicles,
                    "Capacity (t)": round(sol.total_capacity, 1),
                    "Utilization (%)": round(sol.utilization, 1),
                    "Fixed cost (EUR)": round(sol.fixed_cost, 0),
                    "Variable cost (EUR)": round(sol.variable_cost, 0),
                    "Total cost (EUR)": round(sol.total_cost, 0),
                })
            df_top = pd.DataFrame(rows_top)

            def highlight_best(row):
                if row["Rank"] == 1:
                    return ["background-color: #1b5e20; color: white; font-weight: bold"] * len(row)
                return [""] * len(row)

            st.dataframe(
                 df_top.style.apply(highlight_best, axis=1).format({
                    "Capacity (t)": "{:.2f}",
                    "Utilization (%)": "{:.1f}",
                    "Fixed cost (EUR)": "{:.2f}",
                    "Variable cost (EUR)": "{:.2f}",
                    "Total cost (EUR)": "{:.2f}"
                }),
                width='stretch',
                hide_index=True
            )
            st.caption("🥇 Row 1 (green) = optimal solution for the selected objective. Remaining rows are alternative feasible configurations ranked by total cost.")
            fig_sc = px.scatter(
                df_top, x="Vehicles", y="Total cost (EUR)",
                size="Utilization (%)", color="Utilization (%)",
                hover_data=["Configuration"],
                color_continuous_scale="RdYlGn",
                title="Trade-off: Number of vehicles vs. Total cost (size = utilization)",
                height=320
            )
            st.plotly_chart(fig_sc, use_container_width=True)

    # ── Sensitivity analysis ──────────────────────────────────────────────────
    with t3:
        st.subheader("Analysis — demand variation")
        st.markdown("""
This analysis shows how the **optimal fleet cost and composition** change when total demand 
varies between **50% and 150%** of the current base demand. It answers the question:
*"What happens to our distribution costs if demand increases or decreases?"*

**How to read the charts:**
- **Cost curve (red)** — total daily cost (fixed + variable) at each demand level. 
  A steep increase signals a point where a new vehicle must be added to the fleet.
- **Cost/tonne curve (dashed blue)** — economic efficiency. Lower = more cost-efficient. 
  Drops when a larger vehicle replaces multiple smaller ones.
- **Vehicle count chart** — step increases show exactly when an additional vehicle becomes necessary.

**Insight:** The cost curve is not linear — it increases in **steps** each time a new 
vehicle type threshold is crossed. This is the fixed cost effect ($F_k$) from the FSMVRP formulation.
""")
        if sens:
            df_s = pd.DataFrame(sens)
            # Add column for percentage relative to base demand for clear 50%-150% visualization
            df_s["demand_pct"] = (df_s["demand_t"] / total_demand) * 100

            fig_s = go.Figure()
            fig_s.add_trace(go.Scatter(x=df_s["demand_pct"], y=df_s["total_cost"],
                mode="lines+markers", name="Total cost (EUR)",
                line=dict(color="#E94560", width=2), marker=dict(size=7)))
            fig_s.add_trace(go.Scatter(x=df_s["demand_pct"], y=df_s["cost_per_ton"],
                mode="lines+markers", name="Cost/tonne (EUR/t)", yaxis="y2",
                line=dict(color="#3B8BD4", width=2, dash="dash"), marker=dict(size=7)))
            fig_s.update_layout(
                xaxis_title="Demand Level (% of base)", yaxis_title="Total cost (EUR)",
                yaxis2=dict(title="Cost per tonne (EUR/t)", overlaying="y", side="right"),
                height=320, margin=dict(t=30, b=40, l=60, r=60))
            st.plotly_chart(fig_s, use_container_width=True)

            fig_v = px.line(df_s, x="demand_pct", y="total_vehicles", markers=True,
                title="Optimal vehicle count vs demand level",
                labels={"demand_pct": "Demand Level (%)", "total_vehicles": "Vehicles"}, height=260)
            st.plotly_chart(fig_v, use_container_width=True)

            min_cost_row = df_s.loc[df_s["total_cost"].idxmin()]
            max_cost_row = df_s.loc[df_s["total_cost"].idxmax()]
            min_cpt_row  = df_s.loc[df_s["cost_per_ton"].idxmin()]

            st.markdown("---")
            st.markdown("#### 📌 Automatic Conclusions")
            st.markdown(f"""
> All costs represent **total daily fleet operating costs** = fixed vehicle costs 
> (leasing/amortization per day) + variable routing costs (fuel × distance).

- **Lowest cost scenario:** {min_cost_row['demand_t']:.1f} t demand → **{min_cost_row['total_cost']:.0f} EUR/day** 
  *(total daily cost for the optimal fleet at this demand level)*
- **Highest cost scenario:** {max_cost_row['demand_t']:.1f} t demand → **{max_cost_row['total_cost']:.0f} EUR/day**
- **Most cost-efficient point:** {min_cpt_row['demand_t']:.1f} t demand → **{min_cpt_row['cost_per_ton']:.2f} EUR/t** 
  *(lowest cost per tonne delivered — fleet is best utilized at this demand level)*
- **Cost increase from min to max demand:** **{((max_cost_row['total_cost'] - min_cost_row['total_cost']) / min_cost_row['total_cost'] * 100):.1f}%**
- **Vehicle range:** {df_s['total_vehicles'].min()} – {df_s['total_vehicles'].max()} vehicles across the demand spectrum
            """)

    # ── Mathematical model ────────────────────────────────────────────────────
    with t4:
        st.subheader("FSMVRP mathematical formulation")
        st.markdown(r"""
**Objective function:**
$$\min \sum_{t \in T} f_t \cdot n_t + \sum_{k \in K} \sum_{(i,j) \in A} c_{ij} \cdot x_{ijk}$$

**Constraints:**

1. **Demand coverage:** $\sum_{t \in T} n_t \cdot Q_t \geq D_{\text{total}}$
2. **Vehicle availability:** $n_t \leq N_t^{\max} \quad \forall t \in T$
3. **Maximum fleet size:** $\sum_{t \in T} n_t \leq K^{\max}$
4. **Integrality:** $n_t \in \mathbb{Z}_{\geq 0} \quad \forall t \in T$
        """)
        n_types   = len(st.session_state.vehicle_types)
        opt_cost  = f"{best.total_cost:.0f}"
        opt_veh   = best.total_vehicles

        st.markdown(
            "| Parameter | Value |\n"
            "|---|---|\n"
            f"| |T| — vehicle types | {n_types} |\n"
            f"| D_total — total demand | {total_demand} t |\n"
            f"| K_max — max vehicles | {max_veh} |\n"
            f"| Optimal total cost | {opt_cost} EUR |\n"
            f"| Optimal vehicles used | {opt_veh} |\n"
        )

    # ── CS Routing Results ────────────────────────────────────────────────────
    with t5:
        st.subheader("Combined Savings Operational Routes")
        cs_routes = st.session_state.get("cs_routes")
        if cs_routes:
            st.write(f"Algorithm generated **{len(cs_routes)} routes** using optimal vehicle mix.")
            m_cs = build_map(DEPOTS_BUCHAREST, CUSTOMERS_BUCHAREST, cs_routes)
            st_html(map_to_html(m_cs), height=400)
            cs_data = [{
                "Route": f"R{i+1}",
                "Depot": r.depot.name,
                "Vehicle": r.vehicle_type.name,
                "Capacity (t)": r.vehicle_type.capacity,
                "Load (t)": r.total_demand,
                "Dist (km)": r.total_distance,
                "Cost (EUR)": r.total_cost
            } for i, r in enumerate(cs_routes)]
            st.dataframe(pd.DataFrame(cs_data), width='stretch', hide_index=True)
        else:
            st.info("Run optimization first to generate CS routes.")

# ── No result states ──────────────────────────────────────────────────────────
elif "fsm_best" in st.session_state:
    top20 = st.session_state.get("fsm_top20", [])
    if isinstance(top20, list) and top20 and isinstance(top20[0], str) and top20[0] == "__COMBINATORIAL_EXPLOSION__":
        st.error("⚠️ **Combinatorial explosion detected.**")
        st.warning(
            "The current fleet configuration generates too many combinations (> 50,000). "
            "Reduce **Maximum vehicles allowed** or decrease `max_available` in Map & Data."
        )
        st.info("Current fleet limits (6+5+3+2) generate at most 7×6×4×3 = 504 combinations — well within limits.")
    else:
        st.error("🚫 No feasible fleet configuration found.")
        st.info("Try increasing **Maximum vehicles allowed** or reducing **Total demand**.")
else:
    st.info("👈 Set parameters in the sidebar and click **'Optimize fleet'**.")
    st.markdown("""
    **The FSMVRP model determines:**
    - How many vehicles of each type to deploy
    - Minimizing total cost (fixed + variable)
    - Subject to capacity and availability constraints

    | Small vehicles | Large vehicles |
    |---|---|
    | Low fixed cost | High fixed cost |
    | High flexibility | Better cost per km |
    | More routes needed | Covers high demand |
    """)