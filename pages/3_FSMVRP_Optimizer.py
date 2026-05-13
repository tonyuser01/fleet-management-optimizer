"""
Page 3 — FSMVRP Fleet Optimizer
Optimize fleet composition for minimum cost, minimum vehicles, or balanced utilization.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from utils.data_models import VEHICLE_FLEET, DEPOTS_BUCHAREST, CUSTOMERS_BUCHAREST
from utils.mdvrp_algorithms import get_transport_stats
from utils.fsmvrp_optimizer import optimize_fleet, sensitivity_analysis, solve_fsmvrp_combined_savings
from utils.map_utils import build_map, map_to_html
from streamlit.components.v1 import html as st_html

st.title("🚛 FSMVRP — Fleet Size and Mix Optimizer")
st.markdown("Determine the optimal fleet composition to minimize total distribution cost.")

with st.expander("📖 Theoretical Framework: Fleet Size and Mix VRP"):
    st.markdown(r"""
    ### 1. Introduction
    The Fleet Size and Mix Vehicle Routing Problem (FSMVRP) represents a decision layer in distribution network optimization. Unlike the classical VRP which assumes a homogeneous fleet, the FSMVRP acknowledges that most logistics providers operate heterogeneous fleets comprising vehicles of different capacities, costs, and operational characteristics.
    
    The FSMVRP seeks to determine not only the optimal routes for serving customers but also the optimal composition of the fleet: how many vehicles of each type should be deployed to minimize total system cost. Determining the optimal fleet composition is a long-term decision, as distribution costs driven by fuel and asset maintenance constitute a significant portion of a firm's total expenditure.

    ### 2. Mathematical Formulation
    The objective is to minimize total costs, consisting of fixed acquisition/leasing costs and vehicle-dependent operational costs:
    $$\min Z = \sum_{k=1}^{T}{F_k\left(\sum_{j=1}^{n}x_{0jk}\right)}+\sum_{k=1}^{T}\sum_{i=0}^{n}\sum_{j=0}^{n}c_{ijk}\, x_{ijk}$$

    **Cost Structure:**
    - **Fixed costs ($F_k$):** Sum of acquisition costs for each vehicle type $k$ that leaves the depot (node 0).
    - **Variable costs ($c_{ijk}$):** Operational cost of traversing arc $(i,j)$ with vehicle type $k$, proportional to distance and consumption rates.

    **Constraints:**
    - **Customer Service:** Each customer $j$ must be visited exactly once:
      $$\sum_{k=1}^{T}\sum_{i=0}^{n}x_{ijk}=1, \quad \forall j=1,\ldots,n$$
    - **Flow Conservation:** Vehicle $k$ entering location $p$ must also depart:
      $$\sum_{i=0}^{n}x_{ipk}-\sum_{j=0}^{n}x_{pjk}=0, \quad \forall k=1,\ldots,T; \ \forall p=1,\ldots,n$$
    - **Vehicle Capacity:** Total demand served on a route must not exceed vehicle capacity $a_k$:
      $$r_j \le \sum_{k=1}^{T}\sum_{i=0}^{n}a_k\, x_{ijk}, \quad \forall j=1,\ldots,n$$
    - **Subtour Elimination:** Ensures all routes are linked to the central depot using commodity flow variables:
      $$r_j-r_i \geq (d_j+a_T)\sum_{k=1}^{T}x_{ijk}-a_T, \quad \forall i=0,\ldots,n; \ \forall j=1,\ldots,n$$
    - **Fleet Availability:**
      $$x_{ij}^k \in \{0, 1\}, \quad \sum_{j=1}^{n}x_{0jk} \le m_k, \quad \forall k \in K$$

    ### 3. Solution Methodology: Combined Savings (CS)
    Traditional routing algorithms, such as the Clarke and Wright (CW) savings technique, are often deficient for the FSMVRP because they focus solely on distance. Standard CW tends to merge routes until the capacity of the largest vehicle is reached, even if it is not cost-effective.

    To solve this, the **Combined Savings (CS)** approach integrates vehicle costs into the logic:
    $$S_{ij}=s_{ij}+F(Z_i)+F(Z_j)-F(Z_i+Z_j)$$
    Where $F(Z)$ is the cost of the smallest vehicle type capable of serving demand $Z$.

    ### 4. Optimization Objectives Explained
    - **Minimize Total Cost**: The model searches for the fleet composition that achieves the lowest aggregate cost (Fixed Costs + Variable Costs). This is the standard "profit-maximization" strategy.
    - **Minimize Vehicles**: Focuses on asset reduction. It aims for the absolute lowest vehicle count required to cover demand. This is vital when driver availability or physical terminal space is the primary constraint.
    - **Balanced Utilization (Mixed Fleet)**: Targets an ideal load factor of approximately 85%. This strategy provides an operational safety buffer for demand fluctuations while avoiding the inefficiencies of under-utilization.
    
    ---
    *Note: Research also indicates that energy consumption in these models is highly load-dependent.*
    """)

if "vehicle_types" not in st.session_state:
    st.session_state.vehicle_types = VEHICLE_FLEET.copy()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ FSMVRP Parameters")
    total_demand = st.slider("Total demand to deliver (t)", 10.0, 120.0, 45.0, 2.5)
    total_km     = st.slider("Estimated total distance (km)", 50, 800, 320, 10)
    objective = st.selectbox(
        "Optimization objective", 
        ["min_cost", "min_vehicles", "balanced"], 
        format_func=lambda x: {
            "min_cost":     "Minimize total cost",
            "min_vehicles": "Minimize number of vehicles",
            "balanced":     "Balanced fleet utilization"
        }[x],
        help="Choose the strategic priority for fleet composition. 'Balanced' targets ~85% average utilization."
    )
    max_veh  = st.slider("Maximum vehicles allowed", 3, 20, 12)
    run_btn  = st.button("▶ Optimize fleet", type="primary", width='stretch')

if run_btn:
    with st.spinner("Computing optimal fleet configuration..."):
        best, top20 = optimize_fleet(
            st.session_state.vehicle_types, total_demand, total_km,
            objective=objective, max_vehicles=max_veh
        )
        sens = sensitivity_analysis(st.session_state.vehicle_types, total_demand, total_km)

        # Generate operational routes using Combined Savings if data is available
        if "customers" in st.session_state and st.session_state.customers:
            st.session_state.cs_routes = solve_fsmvrp_combined_savings(
                st.session_state.depots, st.session_state.customers, st.session_state.vehicle_types
            )

    st.session_state.fsm_best  = best
    st.session_state.fsm_top20 = top20
    st.session_state.fsm_sens  = sens

best = st.session_state.get("fsm_best")
if best is not None:
    top20 = st.session_state.fsm_top20
    sens  = st.session_state.fsm_sens

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("💰 Total cost",       f"{best.total_cost:.0f} €")
    c2.metric("💶 Fixed cost",       f"{best.fixed_cost:.0f} €")
    c3.metric("🛣️ Variable cost",   f"{best.variable_cost:.0f} €")
    c4.metric("🚛 Vehicles used",    best.total_vehicles)
    c5.metric("📊 Fleet utilization", f"{best.utilization:.1f}%")

    c1b, c2b, c3b = st.columns(3)
    c1b.metric("📦 Capacity covered",  f"{best.total_capacity:.1f} t")
    c2b.metric("💸 Cost per tonne",    f"{best.cost_per_ton:.2f} €/t")
    c3b.metric("💡 Surplus capacity",  f"{best.total_capacity - total_demand:.1f} t")

    st.markdown("---")
    t_summary, t1, t2, t3, t4, t5 = st.tabs([
        "📋 Executive Summary",
        "🚛 Optimal configuration",
        "📊 Solution comparison",
        "📈 Sensitivity analysis",
        "🔢 Mathematical model",
        "🗺️ CS Routing Results"
    ])

    with t_summary:
        st.subheader("Key Performance Indicators (KPIs)")
        
        # Calculăm metrici comparative dacă avem rutele CS
        cs_routes = st.session_state.get("cs_routes")
        cs_total_cost = sum(r.total_cost for r in cs_routes) if cs_routes else None
        
        k1, k2, k3 = st.columns(3)
        
        with k1:
            st.markdown("### 💰 Economic Efficiency")
            st.write(f"**Total Estimated Cost:** {best.total_cost:.0f} €")
            st.write(f"**Transport Cost / Ton:** {best.cost_per_ton:.2f} €/t")
            if cs_total_cost:
                gap = ((cs_total_cost - best.total_cost) / best.total_cost) * 100
                st.write(f"**Operational Gap:** {gap:+.1f}%")
                st.caption("Difference between theoretical fleet cost and actual routing.")

        with k2:
            st.markdown("### 🚛 Fleet Utilization")
            st.write(f"**Capacity Fill Rate:** {best.utilization:.1f}%")
            st.write(f"**Total Capacity:** {best.total_capacity:.1f} t")
            st.progress(best.utilization / 100)
            
        with k3:
            st.markdown("### ⚙️ Resource Allocation")
            st.write(f"**Total Vehicles:** {best.total_vehicles}")
            fixed_ratio = (best.fixed_cost / best.total_cost) * 100
            st.write(f"**Fixed Cost Ratio:** {fixed_ratio:.1f}%")
            
        st.markdown("---")
        st.markdown("#### 📦 Fleet Inventory Status")
        st.caption("Usage vs. Availability defined in Map & Data configuration.")
        
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
        st.markdown("#### Strategic Recommendation")
        
        if best.utilization > 90:
            st.warning("⚠️ **High Utilization:** Your fleet is operating near maximum capacity. Any increase in demand will require additional vehicles or outsourced transport.")
        elif best.utilization < 70:
            st.info("ℹ️ **Underutilized Fleet:** You have significant spare capacity. Consider using smaller vehicle types or increasing consolidate deliveries.")
        else:
            st.success("✅ **Balanced Fleet:** Current configuration provides a good safety margin while maintaining cost-efficiency.")
            
        if cs_routes:
            st.markdown("---")
            st.markdown("#### 📊 Transport & Traffic Parameters (Operational)")
            t_stats = get_transport_stats(cs_routes)
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Traffic Flow", f"{t_stats['traffic_flow']:.1f} km/day", help="Ftrafic = Σ (ni * di)")
            m2.metric("Transport Flow", f"{t_stats['transport_flow']:.1f} veh-inc*km", help="Ftransport = Σ (ni * (di - di'))")
            m3.metric("Empty Run %", f"{t_stats['empty_pct']:.1f} %", help="Pgol = (Pdg / Ptotal) * 100")
            m4.metric("Daily Performance", f"{t_stats['performance']:.1f} t*km", help="Pperformance = Σ (qi * di)")
            st.caption("Parameters are calculated based on operational routes generated via Combined Savings.")

        if cs_routes:
            st.markdown(f"Operational routing has confirmed that **{len(cs_routes)} routes** are needed to serve the demand with the current fleet mix.")

    with t1:
        st.subheader("Optimal fleet configuration")
        rows = best.to_dict()
        if rows:
            st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)

        fig_pie = go.Figure(data=[go.Pie(
                labels=["Fixed cost", "Variable cost"],
                values=[round(best.fixed_cost), round(best.variable_cost)],
                hole=0.45, marker_colors=["#E94560", "#3B8BD4"]
        )])
        fig_pie.update_layout(title="Total cost breakdown", height=280,
                               margin=dict(t=40, b=20, l=20, r=20))
        st.plotly_chart(fig_pie, use_container_width=True)

        alloc = {vt.name: best.allocation.get(vt.id, 0)
                 for vt in st.session_state.vehicle_types if best.allocation.get(vt.id, 0) > 0}
        fig_bar = go.Figure(data=[go.Bar(
            x=list(alloc.keys()), y=list(alloc.values()),
            marker_color=["#E94560","#3B8BD4","#1D9E75","#BA7517"],
            text=list(alloc.values()), textposition="outside"
        )])
        fig_bar.update_layout(title="Vehicles Used by Type", yaxis_title="Count",
                               height=260, margin=dict(t=40, b=20, l=20, r=20))
        st.plotly_chart(fig_bar, use_container_width=True)

    with t2:
        st.subheader("Top 10 feasible solutions")
        if top20:
            rows_top = []
            for i, sol in enumerate(top20[:10]):
                alloc_str = ", ".join(
                    f"{sol.allocation[vt.id]}×{vt.name.split('(')[0].strip()}"
                    for vt in st.session_state.vehicle_types if sol.allocation.get(vt.id, 0) > 0
                )
                rows_top.append({
                    "Rank": i+1, "Configuration": alloc_str,
                    "Vehicles": sol.total_vehicles,
                    "Capacity (t)": round(sol.total_capacity, 1),
                    "Utilization (%)": round(sol.utilization, 1),
                    "Fixed cost (€)": round(sol.fixed_cost, 0),
                    "Variable cost (€)": round(sol.variable_cost, 0),
                    "Total cost (€)": round(sol.total_cost, 0),
                })
            df_top = pd.DataFrame(rows_top)
            st.dataframe(df_top, width='stretch', hide_index=True)

            fig_sc = px.scatter(
                df_top, x="Vehicles", y="Total cost (€)",
                size="Utilization (%)", color="Utilization (%)",
                hover_data=["Configuration"],
                color_continuous_scale="RdYlGn",
                title="Trade-off: Number of vehicles vs. Total cost (size = utilization)",
                height=320
            )
            st.plotly_chart(fig_sc, use_container_width=True)

    with t3:
        st.subheader("Sensitivity analysis — demand variation")
        st.caption("Optimal fleet cost at different demand levels (50% – 150% of base demand).")
        if sens:
            df_s = pd.DataFrame(sens)
            fig_s = go.Figure()
            fig_s.add_trace(go.Scatter(x=df_s["demand_t"], y=df_s["total_cost"],
                mode="lines+markers", name="Total cost (€)",
                line=dict(color="#E94560", width=2), marker=dict(size=7)))
            fig_s.add_trace(go.Scatter(x=df_s["demand_t"], y=df_s["cost_per_ton"],
                mode="lines+markers", name="Cost/tonne (€/t)", yaxis="y2",
                line=dict(color="#3B8BD4", width=2, dash="dash"), marker=dict(size=7)))
            fig_s.update_layout(
                xaxis_title="Total demand (t)", yaxis_title="Total cost (€)",
                yaxis2=dict(title="Cost per tonne (€/t)", overlaying="y", side="right"),
                height=320, margin=dict(t=30, b=40, l=60, r=60))
            st.plotly_chart(fig_s, use_container_width=True)

            fig_v = px.line(df_s, x="demand_t", y="total_vehicles", markers=True,
                title="Optimal vehicle count vs demand",
                labels={"demand_t": "Demand (t)", "total_vehicles": "Vehicles"}, height=260)
            st.plotly_chart(fig_v, use_container_width=True)

    with t4:
        st.subheader("FSMVRP mathematical formulation")
        st.markdown(r"""
**Objective function:**
$$\min \sum_{t \in T} f_t \cdot n_t + \sum_{k \in K} \sum_{(i,j) \in A} c_{ij} \cdot x_{ijk}$$

**Constraints:**

1. **Demand coverage:**
$$\sum_{t \in T} n_t \cdot Q_t \geq D_{\text{total}}$$

2. **Vehicle availability:**
$$n_t \leq N_t^{\max} \quad \forall t \in T$$

3. **Maximum fleet size:**
$$\sum_{t \in T} n_t \leq K^{\max}$$

4. **Integrality:**
$$n_t \in \mathbb{Z}_{\geq 0} \quad \forall t \in T$$

**Notation:** $f_t$ = daily fixed cost, $n_t$ = vehicles used (decision variable),
$Q_t$ = vehicle capacity, $c_{ij}$ = arc cost, $x_{ijk}$ = binary routing variable.
            """)
        if best is not None:
            st.dataframe(pd.DataFrame([
                {"Parameter": "|T| — vehicle types",   "Value": len(st.session_state.vehicle_types)},
                {"Parameter": "D_total — demand (t)",   "Value": f"{total_demand} t"},
                {"Parameter": "K_max — max vehicles",   "Value": max_veh},
                {"Parameter": "Optimal total cost",     "Value": f"{best.total_cost:.0f} €"},
                {"Parameter": "Optimal vehicles used",  "Value": best.total_vehicles},
            ]), width='stretch', hide_index=True)

    with t5: # New Tab
        st.subheader("Combined Savings Operational Routes")
        if cs_routes:
            st.write(f"The algorithm generated **{len(cs_routes)} routes** using an optimal vehicle mix.")
            
            # Vizualizare hartă
            m_cs = build_map(DEPOTS_BUCHAREST, CUSTOMERS_BUCHAREST, cs_routes)
            st_html(map_to_html(m_cs), height=400)
            
            # Tabel detalii
            cs_data = [{
                "Route": f"R{i+1}",
                "Vehicle": r.vehicle_type.name,
                "Capacity": r.vehicle_type.capacity,
                "Load": r.total_demand,
                "Dist (km)": r.total_distance,
                "Cost (€)": r.total_cost
            } for i, r in enumerate(cs_routes)]
            st.dataframe(pd.DataFrame(cs_data), width='stretch', hide_index=True)
elif "fsm_best" in st.session_state:
    st.error("🚫 No feasible fleet configuration found.")
    st.info("Try increasing the **Maximum vehicles allowed** or reducing the **Total demand** in the sidebar.")
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
