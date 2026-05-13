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
    DEPOTS_BUCHAREST, CUSTOMERS_BUCHAREST, VEHICLE_FLEET,
    EUROPALLET, Europallet, build_od_matrix, haversine
)
from utils.map_utils import build_map, map_to_html

@st.cache_data
def compute_od_matrix(depots: list, customers: list) -> pd.DataFrame:
    """Computes the Origin-Destination distance matrix between all nodes."""
    all_nodes = depots + customers
    names = [n.name for n in all_nodes]
    n = len(all_nodes)

    matrix = [[
        0.0 if i == j else round(haversine(all_nodes[i].lat, all_nodes[i].lon, all_nodes[j].lat, all_nodes[j].lon), 2)
        for j in range(n)
    ] for i in range(n)]

    return pd.DataFrame(matrix, index=names, columns=names)

st.title("🗺️ Map, Data & Network Overview")
st.markdown("Depot and customer directory, europallet specifications, vehicle fleet, and OD distance matrix.")

# ── Session state ─────────────────────────────────────────────────────────────
if "depots"        not in st.session_state: st.session_state.depots        = DEPOTS_BUCHAREST.copy()
if "all_customers" not in st.session_state: st.session_state.all_customers = CUSTOMERS_BUCHAREST.copy()
if "vehicle_types" not in st.session_state: st.session_state.vehicle_types = VEHICLE_FLEET.copy()

# ── Callbacks ────────────────────────────────────────────────────────────────
def on_store_edit():
    """Callback to sync data_editor changes back to Customer objects before the script reruns."""
    state = st.session_state.stores_editor
    # Sync edited rows back to the session_state objects
    for idx_str, changes in state.get("edited_rows", {}).items():
        idx = int(idx_str)
        if "customers" in st.session_state and idx < len(st.session_state.customers):
            c = st.session_state.customers[idx]
            if "Ambient (kg)" in changes:    c.demand_ambient = changes["Ambient (kg)"] / 1000.0
            if "Fridge (kg)" in changes:     c.demand_refrigerated = changes["Fridge (kg)"] / 1000.0
            if "Needs Fridge" in changes:    c.needs_refrigeration = changes["Needs Fridge"]

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuration")
    max_demand = st.slider("Max demand per customer (t)", 1.0, 10.0, 8.0, 0.5)
    st.session_state.customers = [c for c in st.session_state.all_customers if c.demand <= max_demand]
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
    total_ambient = sum(c.demand_ambient for c in st.session_state.customers)
    total_fridge  = sum(c.demand_refrigerated for c in st.session_state.customers)
    total_stock  = sum(d.daily_stock_tonnes for d in st.session_state.depots)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Depots",              len(st.session_state.depots))
    c2.metric("Active customers",    len(st.session_state.customers))
    c3.metric("Total Demand",        f"{total_demand:.1f} t")
    c4.metric("📦 Ambient",          f"{total_ambient:.1f} t")
    c5.metric("❄️ Refrigerated",      f"{total_fridge:.1f} t")

# ─── TAB 2: DEPOTS ────────────────────────────────────────────────────────────
with tabs[1]:
    st.subheader("Depot directory")
    st.markdown("Each depot receives daily stock from the central warehouse and dispatches vehicles to serve assigned customers.")

    depot_data = [{
        "ID":                    d.id,
        "Name":                  d.name,
        "Address":               d.address,
        "Latitude":              d.lat,
        "Longitude":             d.lon,
        "Vehicles available":    d.num_vehicles,
        "Daily capacity (units)":d.capacity,
        "Daily stock (t)":       d.daily_stock_tonnes,
    } for d in st.session_state.depots]
    
    edited_depots = st.data_editor(
        depot_data, 
        width='stretch', 
        hide_index=True,
        column_config={
            "ID": st.column_config.NumberColumn(disabled=True),
            "Name": st.column_config.TextColumn(disabled=True),
            "Vehicles available": st.column_config.NumberColumn(min_value=1, max_value=50, step=1),
            "Daily capacity (units)": st.column_config.NumberColumn(min_value=100)
        }
    )
    # Sync changes back to session state objects
    for i, row in enumerate(edited_depots):
        st.session_state.depots[i].num_vehicles = row["Vehicles available"]
        st.session_state.depots[i].capacity = row["Daily capacity (units)"]
        st.session_state.depots[i].daily_stock_tonnes = row["Daily stock (t)"]

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

    store_data = [{
        "ID":                 c.id,
        "Store name":         c.name,
        "Ambient (kg)":       int(c.demand_ambient * 1000),
        "Fridge (kg)":        int(c.demand_refrigerated * 1000),
        "Needs Fridge":       c.needs_refrigeration,
        "Total Demand (t)":   round(c.demand, 2),
        "Pallets needed":     c.pallets_needed(EUROPALLET, pallet_payload),
        "Address":            c.address,
    } for c in st.session_state.customers]

    st.data_editor(
        store_data, 
        width='stretch', 
        hide_index=True,
        key="stores_editor",
        on_change=on_store_edit,
        column_config={
            "ID": st.column_config.NumberColumn(disabled=True),
            "Store name": st.column_config.TextColumn(disabled=True),
            "Ambient (kg)": st.column_config.NumberColumn(min_value=0, step=50),
            "Fridge (kg)": st.column_config.NumberColumn(min_value=0, step=50),
            "Needs Fridge": st.column_config.CheckboxColumn(),
            "Total Demand (t)": st.column_config.NumberColumn(disabled=True),
            "Pallets needed": st.column_config.NumberColumn(disabled=True),
            "Address": st.column_config.TextColumn(disabled=True),
        }
    )
    
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
        st.dataframe(pallet_data, width='stretch', hide_index=True)
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

    fleet_data = [{
        "ID":                    vt.id,
        "Vehicle type":          vt.name,
        "Payload (t)":           vt.capacity_tonnes,
        "Fixed cost (€/day)":    vt.fixed_cost,
        "Cost per km (€)":       vt.cost_per_km,
        "Max available":         vt.max_available,
    } for vt in st.session_state.vehicle_types]

    edited_fleet = st.data_editor(
        fleet_data,
        width='stretch',
        hide_index=True,
        column_config={
            "ID": st.column_config.NumberColumn(disabled=True),
            "Vehicle type": st.column_config.TextColumn(disabled=True),
            "Max available": st.column_config.NumberColumn(min_value=0, max_value=100, step=1)
        }
    )
    # Sync fleet changes
    for i, row in enumerate(edited_fleet):
        st.session_state.vehicle_types[i].capacity_tonnes = row["Payload (t)"]
        st.session_state.vehicle_types[i].fixed_cost = row["Fixed cost (€/day)"]
        st.session_state.vehicle_types[i].cost_per_km = row["Cost per km (€)"]
        st.session_state.vehicle_types[i].max_available = row["Max available"]

    st.caption("**Effective max pallets** = min(floor capacity, weight capacity). "
               "Floor capacity = how many pallets fit on the cargo floor in a single layer. "
               "Weight capacity = payload ÷ (net payload per pallet + pallet weight).")

    st.markdown("---")
    st.subheader("📑 Technical Fleet Justification")
    st.info("Technical details and certified specifications for each vehicle type used in the model.")

    for vt in st.session_state.vehicle_types:
        with st.expander(f"🔍 Detailed Specifications: {vt.name}"):
            st.write(f"**Description:** {vt.description}")
            
            if vt.tech_specs:
                # Create a table for technical specifications
                specs_df = pd.DataFrame([
                    {"Parameter": k, "Details": v} for k, v in vt.tech_specs.items()
                ])
                st.table(specs_df)
            else:
                st.write("Technical information unavailable.")

# ─── TAB 5: OD MATRIX ─────────────────────────────────────────────────────────
with tabs[4]:
    st.subheader("Origin-Destination Distance Matrix (km)")
    st.markdown("""
    Haversine great-circle distances (km) between all network nodes.
    Rows = origin, Columns = destination.
    """)
    
    # Optimized with caching to prevent recalculation on every slider change
    od_df = compute_od_matrix(st.session_state.depots, st.session_state.customers)
    names = od_df.columns.tolist()
    n = len(names)

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
        width='stretch',
        height=500
    )

    st.caption("🟢 Green = short distance · 🔴 Red = long distance · Diagonal = 0 (same node)")

    # Summary stats
    st.markdown("---")
    st.subheader("Distance statistics")
    flat = [float(cast(Any, od_df.iloc[i, j])) for i in range(n) for j in range(n) if i != j]
    
    nd   = len(st.session_state.depots)
    # Efficiently extract sub-matrices for stats
    depot_to_cust = od_df.iloc[:nd, nd:].values.flatten()
    cust_to_cust = od_df.iloc[nd:, nd:].values.flatten()
    cust_to_cust = [d for d in cust_to_cust if d > 0] # exclude diagonal

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
    c4.metric("Avg depot→customer",      f"{sum(depot_to_cust)/len(depot_to_cust):.2f} km" if len(depot_to_cust) > 0 else "0.00 km")
    c5.metric("Avg customer→customer",   f"{sum(cust_to_cust)/len(cust_to_cust):.2f} km" if len(cust_to_cust) > 0 else "0.00 km")
    c6.metric("Total nodes in matrix",   n)
