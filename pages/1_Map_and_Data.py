"""
Page 1 — Map & Data
Interactive map, depot/store directory, europallet specs, OD distance matrix.
"""
import streamlit as st
import pandas as pd
import math
from typing import Any, cast
from streamlit.components.v1 import html as st_html

from utils.data_models import (
    ROMANIAN_DEPOTS, ROMANIAN_CUSTOMERS, VEHICLE_FLEET,
    EUROPALLET, Europallet, build_od_matrix, haversine
)
from utils.map_utils import build_map, map_to_html

st.title("🗺️ Map, Data & Network Overview")
st.markdown("Depot and customer directory, europallet specifications, vehicle fleet, and OD distance matrix.")

# ── Session state ─────────────────────────────────────────────────────────────
if "depots"        not in st.session_state: st.session_state.depots        = ROMANIAN_DEPOTS.copy()
if "customers"     not in st.session_state: st.session_state.customers     = ROMANIAN_CUSTOMERS.copy()
if "vehicle_types" not in st.session_state: st.session_state.vehicle_types = VEHICLE_FLEET.copy()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuration")
    max_demand = st.slider("Max demand per customer (t)", 1.0, 10.0, 8.0, 0.5)
    st.session_state.customers = [c for c in ROMANIAN_CUSTOMERS if c.demand <= max_demand]
    st.info(f"Active customers: **{len(st.session_state.customers)}**")

    st.markdown("---")
    st.subheader("🪵 Europallet parameters")
    pallet_payload = st.slider("Net payload per pallet (kg)", 200, 1200, 800, 50)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "🗺️ Map",
    "🏭 Depots",
    "🏪 Stores",
    "🚛 Fleet & Pallets",
    "📊 OD Matrix"
])

# ─── TAB 1: MAP ───────────────────────────────────────────────────────────────
with tabs[0]:
    st.subheader("Network map — depots and customers")
    st.caption("Click any marker for details. Use layer control (top right) to toggle layers.")
    m = build_map(
        depots=st.session_state.depots,
        customers=st.session_state.customers,
        routes=st.session_state.get("routes"),
    )
    st_html(map_to_html(m), height=520, scrolling=False)

    total_demand = sum(c.demand for c in st.session_state.customers)
    total_stock  = sum(d.daily_stock_tonnes for d in st.session_state.depots)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Depots",              len(st.session_state.depots))
    c2.metric("Active customers",    len(st.session_state.customers))
    c3.metric("Total daily demand",  f"{total_demand:.1f} t")
    c4.metric("Total depot stock",   f"{total_stock:.1f} t/day")

# ─── TAB 2: DEPOTS ────────────────────────────────────────────────────────────
with tabs[1]:
    st.subheader("Depot directory")
    st.markdown("Each depot receives daily stock from the central warehouse and dispatches vehicles to serve assigned customers.")

    depot_df = pd.DataFrame([{
        "ID":                    d.id,
        "Name":                  d.name,
        "Address":               d.address,
        "Latitude":              d.lat,
        "Longitude":             d.lon,
        "Vehicles available":    d.num_vehicles,
        "Daily capacity (units)":d.capacity,
        "Daily stock (t)":       d.daily_stock_tonnes,
    } for d in st.session_state.depots])
    st.dataframe(depot_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Daily incoming stock per depot")
    stock_df = pd.DataFrame({
        "Depot": [d.name for d in st.session_state.depots],
        "Stock (t/day)": [d.daily_stock_tonnes for d in st.session_state.depots],
    })
    st.bar_chart(stock_df.set_index("Depot"))

# ─── TAB 3: STORES ────────────────────────────────────────────────────────────
with tabs[2]:
    st.subheader("Store directory")
    st.markdown("All customer locations with addresses, daily demand, and time windows.")

    store_df = pd.DataFrame([{
        "ID":              c.id,
        "Store name":      c.name,
        "Address":         c.address,
        "Latitude":        round(c.lat, 4),
        "Longitude":       round(c.lon, 4),
        "Daily demand (t)":c.demand,
        "Demand (kg)":     int(c.demand * 1000),
        "Pallets needed":  c.pallets_needed(EUROPALLET),
        "Time window":     f"{c.time_window_open}:00 – {c.time_window_close}:00",
        "Service time (min)": c.service_time,
    } for c in st.session_state.customers])
    st.dataframe(store_df, use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)
    demands = [float(cast(Any, c.demand)) for c in st.session_state.customers]
    with col1:
        st.markdown("**Demand distribution (t)**")
        st.bar_chart(pd.DataFrame({"Demand (t)": demands}))
    with col2:
        st.markdown("**Summary statistics**")
        if demands:
            st.metric("Min demand",   f"{min(demands)} t")
            st.metric("Max demand",   f"{max(demands)} t")
            st.metric("Total demand", f"{sum(demands):.1f} t")
        else:
            st.warning("No customers matching the current filter.")
            st.metric("Total demand", "0.0 t")
            
        total_pallets = sum(c.pallets_needed(EUROPALLET) for c in st.session_state.customers)
        st.metric("Total pallets needed", total_pallets)

# ─── TAB 4: FLEET & PALLETS ───────────────────────────────────────────────────
with tabs[3]:
    st.subheader("Europallet specification")
    col1, col2 = st.columns(2)
    with col1:
        pallet_data = pd.DataFrame([{
            "Parameter": p, "Value": v
        } for p, v in [
            ("Length",       f"{EUROPALLET.length_cm} cm"),
            ("Width",        f"{EUROPALLET.width_cm} cm"),
            ("Height",       f"{EUROPALLET.height_cm} cm"),
            ("Pallet weight",f"{EUROPALLET.weight_kg} kg"),
            ("Footprint",    f"{EUROPALLET.footprint_m2:.2f} m²"),
            ("Volume",       f"{EUROPALLET.volume_m3:.4f} m³"),
            ("Net payload",  f"{pallet_payload} kg (configurable)"),
        ]])
        st.dataframe(pallet_data, use_container_width=True, hide_index=True)
    with col2:
        st.info(f"""
        **Standard EUR/EPAL pallet**

        The europallet is the standard loading unit used
        across European logistics networks.

        At **{pallet_payload} kg** net payload per pallet:
        - Total per pallet (goods + pallet): **{pallet_payload + EUROPALLET.weight_kg} kg**
        - Total daily pallets needed: **{sum(c.pallets_needed(EUROPALLET) for c in st.session_state.customers)}**
        """)

    st.markdown("---")
    st.subheader("Vehicle fleet — capacity and pallet loading")

    fleet_rows = []
    for vt in st.session_state.vehicle_types:
        floor_pallets  = vt.max_pallets_by_floor(EUROPALLET)
        weight_pallets = vt.max_pallets_by_weight(EUROPALLET, pallet_payload)
        effective      = vt.max_pallets(EUROPALLET, pallet_payload)
        fleet_rows.append({
            "Vehicle type":          vt.name,
            "Payload (t)":           vt.capacity_tonnes,
            "Fixed cost (€/day)":    vt.fixed_cost,
            "Cost per km (€)":       vt.cost_per_km,
            "Cargo (L×W×H m)":       f"{vt.cargo_length_m}×{vt.cargo_width_m}×{vt.cargo_height_m}",
            "Pallets by floor":      floor_pallets,
            "Pallets by weight":     weight_pallets,
            "Effective max pallets": effective,
            "Max available":         vt.max_available,
        })
    st.dataframe(pd.DataFrame(fleet_rows), use_container_width=True, hide_index=True)

    st.caption("**Effective max pallets** = min(floor capacity, weight capacity). "
               "Floor capacity = how many pallets fit on the cargo floor in a single layer. "
               "Weight capacity = payload ÷ (net payload per pallet + pallet weight).")

# ─── TAB 5: OD MATRIX ─────────────────────────────────────────────────────────
with tabs[4]:
    st.subheader("Origin-Destination Distance Matrix (km)")
    st.markdown("""
    Haversine great-circle distances (km) between all network nodes.
    Rows = origin, Columns = destination.
    """)

    all_nodes = st.session_state.depots + st.session_state.customers
    names     = [n.name for n in all_nodes]
    lats      = [n.lat  for n in all_nodes]
    lons      = [n.lon  for n in all_nodes]
    n         = len(all_nodes)

    matrix_data = []
    for i in range(n):
        row = {}
        for j in range(n):
            if i == j:
                row[names[j]] = 0.0
            else:
                row[names[j]] = round(haversine(lats[i], lons[i], lats[j], lons[j]), 2)
        matrix_data.append(row)

    od_df = pd.DataFrame(matrix_data, index=names)

    # Color scale: green = short, red = long
    max_dist = od_df.values.max()

    def color_dist(val):
        if val == 0:
            return "background-color: #f0f0f0; color: #999"
        ratio = val / max_dist
        r = int(255 * ratio)
        g = int(200 * (1 - ratio))
        return f"background-color: rgb({r},{g},80); color: #000"

    st.dataframe(
        od_df.style.map(color_dist).format("{:.2f}"),
        use_container_width=True,
        height=500
    )

    st.caption("🟢 Green = short distance · 🔴 Red = long distance · Diagonal = 0 (same node)")

    # Summary stats
    st.markdown("---")
    st.subheader("Distance statistics")
    flat = [float(cast(Any, od_df.iloc[i, j])) for i in range(n) for j in range(n) if i != j]
    nd   = len(st.session_state.depots)
    nc   = len(st.session_state.customers)

    depot_to_cust = [
        round(haversine(lats[i], lons[i], lats[j], lons[j]), 2)
        for i in range(nd) for j in range(nd, nd+nc)
    ]
    cust_to_cust = [
        round(haversine(lats[i], lons[i], lats[j], lons[j]), 2)
        for i in range(nd, nd+nc) for j in range(nd, nd+nc) if i != j
    ]

    c1, c2, c3 = st.columns(3)
    if flat:
        c1.metric("Min distance (any)",      f"{min(flat):.2f} km")
        c2.metric("Max distance (any)",      f"{max(flat):.2f} km")
        c3.metric("Avg distance (any)",      f"{sum(flat)/len(flat):.2f} km")
    else:
        c1.metric("Min distance (any)",      "0.00 km")
        c2.metric("Max distance (any)",      "0.00 km")
        c3.metric("Avg distance (any)",      "0.00 km")

    c4, c5, c6 = st.columns(3)
    c4.metric("Avg depot→customer",      f"{sum(depot_to_cust)/len(depot_to_cust):.2f} km" if depot_to_cust else "0.00 km")
    c5.metric("Avg customer→customer",   f"{sum(cust_to_cust)/len(cust_to_cust):.2f} km" if cust_to_cust else "0.00 km")
    c6.metric("Total nodes in matrix",   n)
