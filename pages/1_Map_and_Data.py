"""
Page 1 — Map & Data
Configure depots and customers; view them on an interactive OpenStreetMap.
"""
import streamlit as st
import pandas as pd
from streamlit.components.v1 import html as st_html

from utils.data_models import (
    ROMANIAN_DEPOTS, ROMANIAN_CUSTOMERS, VEHICLE_FLEET
)
from utils.map_utils import build_map, map_to_html

st.title("🗺️ Interactive Map & Data Configuration")
st.markdown("View and configure depots, customers, and the vehicle fleet on a real interactive map (OpenStreetMap).")

# ── Session state defaults ────────────────────────────────────────────────────
if "depots"        not in st.session_state: st.session_state.depots        = ROMANIAN_DEPOTS.copy()
if "customers"     not in st.session_state: st.session_state.customers     = ROMANIAN_CUSTOMERS.copy()
if "vehicle_types" not in st.session_state: st.session_state.vehicle_types = VEHICLE_FLEET.copy()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Scenario Configuration")
    scenario = st.selectbox("Predefined scenario",
                            ["Bucharest — 3 depots, 20 customers", "Custom"])
    if scenario == "Bucharest — 3 depots, 20 customers":
        st.session_state.depots    = ROMANIAN_DEPOTS.copy()
        st.session_state.customers = ROMANIAN_CUSTOMERS.copy()

    st.markdown("---")
    st.subheader("Customer filter")
    max_demand = st.slider("Max demand per customer (t)", 1.0, 10.0, 8.0, 0.5)
    st.session_state.customers = [c for c in ROMANIAN_CUSTOMERS if c.demand <= max_demand]
    st.info(f"Active customers: **{len(st.session_state.customers)}**")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_map, tab_depots, tab_customers = st.tabs(["🗺️ Map", "🏭 Depots", "📦 Customers"])

with tab_map:
    st.subheader("Depot and customer locations")
    st.caption("Click on any marker for details. Use the layer control (top right) to toggle depots, customers, and routes.")

    m = build_map(
        depots=st.session_state.depots,
        customers=st.session_state.customers,
        routes=st.session_state.get("routes"),
    )
    st_html(map_to_html(m), height=550, scrolling=False)

    total_demand = sum(c.demand for c in st.session_state.customers)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Depots",            len(st.session_state.depots))
    col2.metric("Customers",         len(st.session_state.customers))
    col3.metric("Total demand",      f"{total_demand:.1f} t")
    col4.metric("Avg demand/customer", f"{total_demand / max(len(st.session_state.customers), 1):.1f} t")

with tab_depots:
    st.subheader("Depot data")
    st.dataframe(pd.DataFrame([{
        "ID": d.id, "Name": d.name,
        "Latitude": d.lat, "Longitude": d.lon,
        "Vehicles available": d.num_vehicles,
        "Daily capacity (units)": d.capacity
    } for d in st.session_state.depots]), use_container_width=True, hide_index=True)

    st.subheader("Vehicle fleet")
    st.dataframe(pd.DataFrame([{
        "Vehicle type": vt.name,
        "Capacity (t)": vt.capacity,
        "Fixed cost (€/day)": vt.fixed_cost,
        "Cost per km (€)": vt.cost_per_km,
        "Max available": vt.max_available,
        "Avg speed (km/h)": vt.speed_kmh
    } for vt in st.session_state.vehicle_types]), use_container_width=True, hide_index=True)

with tab_customers:
    st.subheader(f"Customer data — {len(st.session_state.customers)} active customers")
    st.dataframe(pd.DataFrame([{
        "ID": c.id, "Name": c.name,
        "Latitude": round(c.lat, 4), "Longitude": round(c.lon, 4),
        "Demand (t)": c.demand,
        "Time window": f"{c.time_window_open}:00 – {c.time_window_close}:00",
        "Service time (min)": c.service_time
    } for c in st.session_state.customers]), use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)
    demands = [c.demand for c in st.session_state.customers]
    with col1:
        st.markdown("**Demand distribution**")
        st.bar_chart(pd.DataFrame({"Demand (t)": demands}))
    with col2:
        st.markdown("**Demand statistics**")
        st.metric("Min", f"{min(demands)} t")
        st.metric("Max", f"{max(demands)} t")
        st.metric("Total", f"{sum(demands):.1f} t")
