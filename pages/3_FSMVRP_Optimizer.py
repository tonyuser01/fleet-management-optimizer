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

if "vehicle_types" not in st.session_state:
    st.session_state.vehicle_types = VEHICLE_FLEET.copy()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ FSMVRP Parameters")
    total_demand = st.slider("Total demand to deliver (t)", 10.0, 120.0, 45.0, 2.5)
    total_km     = st.slider("Estimated total distance (km)", 50, 800, 320, 10)
    objective = st.selectbox("Optimization objective", [
        "min_cost", "min_vehicles", "balanced"
    ], format_func=lambda x: {
        "min_cost":     "Minimize total cost",
        "min_vehicles": "Minimize number of vehicles",
        "balanced":     "Balanced fleet utilization"
    }[x])
    max_veh  = st.slider("Maximum vehicles allowed", 3, 20, 12)
    run_btn  = st.button("▶ Optimize fleet", type="primary", width='stretch')

if run_btn:
    with st.spinner("Computing optimal fleet configuration..."):
        best, top20 = optimize_fleet(
            st.session_state.vehicle_types, total_demand, total_km,
            objective=objective, max_vehicles=max_veh
        )
        sens = sensitivity_analysis(st.session_state.vehicle_types, total_demand, total_km)
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
        " Sensitivity analysis",
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
        st.markdown("#### 📑 Strategic Recommendation")
        
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
        fig_bar.update_layout(title="Vehicles used by type", yaxis_title="Count",
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

    with t5: # Tab-ul nou
        st.subheader("Combined Savings Operational Routes")
        if cs_routes:
            st.write(f"The algorithm generated **{len(cs_routes)} routes** using an optimal vehicle mix.")
            
            # Vizualizare hartă
            m_cs = build_map(DEPOTS_BUCHAREST[:1], CUSTOMERS_BUCHAREST, cs_routes)
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
