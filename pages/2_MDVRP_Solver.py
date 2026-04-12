"""
Page 2 — MDVRP Solver
Run routing algorithms and visualize generated routes on the real map.
"""
import streamlit as st
import pandas as pd
import time
from streamlit.components.v1 import html as st_html

from utils.data_models import ROMANIAN_DEPOTS, ROMANIAN_CUSTOMERS, VEHICLE_FLEET
from utils.mdvrp_algorithms import solve_mdvrp
from utils.map_utils import build_map, map_to_html

st.title("📐 MDVRP Solver")
st.markdown("Run vehicle routing algorithms on a real map and compare algorithm performance.")

if "depots"        not in st.session_state: st.session_state.depots        = ROMANIAN_DEPOTS.copy()
if "customers"     not in st.session_state: st.session_state.customers     = ROMANIAN_CUSTOMERS.copy()
if "vehicle_types" not in st.session_state: st.session_state.vehicle_types = VEHICLE_FLEET.copy()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ MDVRP Parameters")

    algo = st.selectbox("Routing algorithm", [
        "Clarke-Wright Savings",
        "Nearest Neighbor",
        "Both (comparison)"
    ])

    vt_sel = st.selectbox("Vehicle type", [vt.name for vt in st.session_state.vehicle_types], index=1)
    selected_vt = next(vt for vt in st.session_state.vehicle_types if vt.name == vt_sel)
    apply_2opt = st.checkbox("Apply 2-opt improvement", value=True)

    st.markdown("---")
    st.info(f"""
    **Current configuration:**
    - {len(st.session_state.depots)} depots
    - {len(st.session_state.customers)} customers
    - Vehicle capacity: {selected_vt.capacity} t
    - Fixed cost: {selected_vt.fixed_cost} €/day
    - Cost per km: {selected_vt.cost_per_km} €
    """)

    run_btn = st.button("▶ Run MDVRP", type="primary", width='stretch')

# ── Solve ─────────────────────────────────────────────────────────────────────
if run_btn:
    with st.spinner("Computing optimal routes..."):
        t0 = time.time()
        if algo == "Both (comparison)":
            routes_cw, _ = solve_mdvrp(st.session_state.depots, st.session_state.customers,
                                        selected_vt, "clarke_wright", apply_2opt)
            routes_nn, _ = solve_mdvrp(st.session_state.depots, st.session_state.customers,
                                        selected_vt, "nearest_neighbor", apply_2opt)
            st.session_state.routes       = routes_cw
            st.session_state.routes_nn    = routes_nn
            st.session_state.compare_mode = True
        elif algo == "Clarke-Wright Savings":
            routes, _ = solve_mdvrp(st.session_state.depots, st.session_state.customers,
                                    selected_vt, "clarke_wright", apply_2opt)
            st.session_state.routes       = routes
            st.session_state.compare_mode = False
        else:
            routes, _ = solve_mdvrp(st.session_state.depots, st.session_state.customers,
                                    selected_vt, "nearest_neighbor", apply_2opt)
            st.session_state.routes       = routes
            st.session_state.compare_mode = False

        st.session_state.solve_time = time.time() - t0

    st.success(f"✅ Optimization completed in {st.session_state.solve_time:.3f}s")

# ── Results ───────────────────────────────────────────────────────────────────
if "routes" in st.session_state and st.session_state.routes:
    routes = st.session_state.routes

    total_dist  = sum(r.total_distance for r in routes)
    total_cost  = sum(r.total_cost for r in routes)
    total_dem   = sum(r.total_demand  for r in routes)
    avg_util    = total_dem / (len(routes) * selected_vt.capacity) * 100 if routes else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("🛣️ Total distance",    f"{total_dist:.1f} km")
    c2.metric("💰 Total cost",         f"{total_cost:.0f} €")
    c3.metric("🚛 Routes",             len(routes))
    c4.metric("📦 Demand served",      f"{total_dem:.1f} t")
    c5.metric("📊 Avg utilization",    f"{avg_util:.1f}%")

    st.markdown("---")
    tab_map, tab_table, tab_cmp = st.tabs(["🗺️ Route map", "📋 Route details", "📊 Algorithm comparison"])

    with tab_map:
        st.subheader("Generated routes on map")
        m = build_map(st.session_state.depots, st.session_state.customers, routes)
        st_html(map_to_html(m), height=560, scrolling=False)
        st.caption("💡 Click any route line or customer marker for details. Toggle layers from the top-right corner.")

    with tab_table:
        st.subheader("Route details")
        rows = [{
            "Route":            f"Route {i+1}",
            "Depot":            r.depot.name,
            "Vehicle":          r.vehicle_type.name,
            "Customers":        len(r.customers),
            "Sequence":         " → ".join(c.name.split()[-1] for c in r.customers),
            "Demand (t)":       r.total_demand,
            "Capacity (t)":     selected_vt.capacity,
            "Utilization (%)":  round(r.total_demand / selected_vt.capacity * 100, 1),
            "Distance (km)":    r.total_distance,
            "Cost (€)":         r.total_cost,
        } for i, r in enumerate(routes)]

        df = pd.DataFrame(rows)

        def color_util(val):
            if val >= 80: return "background-color: #d4edda"
            if val >= 50: return "background-color: #fff3cd"
            return "background-color: #f8d7da"

        st.dataframe(df.style.map(color_util, subset=["Utilization (%)"]),
                     use_container_width=True, hide_index=True)

        st.markdown("**Per-depot summary:**")
        summary = df.groupby("Depot").agg(
            Routes=("Route", "count"),
            Customers=("Customers", "sum"),
            Total_demand=("Demand (t)", "sum"),
            Total_distance=("Distance (km)", "sum"),
            Total_cost=("Cost (€)", "sum")
        ).reset_index()
        st.dataframe(summary, use_container_width=True, hide_index=True)

    with tab_cmp:
        if st.session_state.get("compare_mode"):
            routes_nn = st.session_state.routes_nn
            routes_cw = st.session_state.routes

            def summarize(rs, label):
                return {
                    "Algorithm": label,
                    "Routes": len(rs),
                    "Total distance (km)": round(sum(r.total_distance for r in rs), 1),
                    "Total cost (€)": round(sum(r.total_cost for r in rs), 0),
                    "Avg utilization (%)": round(
                        sum(r.total_demand for r in rs) / (len(rs) * selected_vt.capacity) * 100, 1
                    ) if rs else 0,
                }

            st.dataframe(pd.DataFrame([summarize(routes_nn, "Nearest Neighbor"),
                                       summarize(routes_cw, "Clarke-Wright Savings")]),
                         use_container_width=True, hide_index=True)

            nn_dist = sum(r.total_distance for r in routes_nn)
            cw_dist = sum(r.total_distance for r in routes_cw)
            improvement = (nn_dist - cw_dist) / nn_dist * 100 if nn_dist > 0 else 0
            if improvement > 0:
                st.success(f"✅ Clarke-Wright is **{improvement:.1f}%** more efficient than Nearest Neighbor in total distance.")
            else:
                st.info(f"ℹ️ On this instance, Nearest Neighbor achieved {abs(improvement):.1f}% less total distance.")

            st.subheader("Map — Clarke-Wright Savings")
            st_html(map_to_html(build_map(st.session_state.depots, st.session_state.customers, routes_cw)), height=400, scrolling=False)

            st.subheader("Map — Nearest Neighbor")
            st_html(map_to_html(build_map(st.session_state.depots, st.session_state.customers, routes_nn)), height=400, scrolling=False)
        else:
            st.info("Select **'Both (comparison)'** from the sidebar and re-run to see a side-by-side comparison.")

else:
    st.info("👈 Set parameters in the sidebar and click **'Run MDVRP'** to generate routes.")
    st.markdown("""
    **What this module does:**
    - Assigns each customer to the nearest depot (Customer-Depot Assignment)
    - Applies the selected algorithm to build feasible routes
    - Visualizes all routes on the OpenStreetMap with animations

    | Algorithm | Complexity | Solution quality |
    |---|---|---|
    | Nearest Neighbor | O(n²) | Good, very fast |
    | Clarke-Wright Savings | O(n² log n) | High quality |
    | 2-opt improvement | O(n²) per route | Local improvement |
    """)
