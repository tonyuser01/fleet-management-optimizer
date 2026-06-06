"""
Page 1 — Map & Data
Interactive map, depot/store directory, europallet specs, OD distance matrix.
"""
import streamlit as st
import pandas as pd
import math
import requests
from typing import Any, cast
from streamlit.components.v1 import html as st_html

from utils.data_models import (
    DEPOTS_BUCHAREST, CUSTOMERS_BUCHAREST, VEHICLE_FLEET,
    EUROPALLET, Europallet, build_od_matrix, haversine
)
from utils.map_utils import build_map, map_to_html

@st.cache_data(hash_funcs={list: lambda x: str([(i.lat, i.lon) for i in x])})
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
if "active_customer_ids" not in st.session_state:
    st.session_state.active_customer_ids = {c.id for c in st.session_state.all_customers}

# Sincronizează num_vehicles per depot bazat pe flota totală disponibilă
# Sugestie: Rulează această logică doar dacă nu a fost deja configurată manual
if "fleet_initialized" not in st.session_state:
    total_vehicles = sum(vt.max_available for vt in st.session_state.vehicle_types)
    num_depots = len(st.session_state.depots)
    if num_depots > 0:
        vehicles_per_depot = total_vehicles // num_depots
        remainder = total_vehicles % num_depots
        for i, depot in enumerate(st.session_state.depots):
            depot.num_vehicles = vehicles_per_depot + (1 if i < remainder else 0)
    st.session_state.fleet_initialized = True

# ── Callbacks ────────────────────────────────────────────────────────────────
def on_store_edit():
    """Callback to sync data_editor changes back to Customer objects before the script reruns."""
    state = st.session_state.stores_editor
    # Sync edited rows back to the session_state objects
    for idx_str, changes in state.get("edited_rows", {}).items():
        idx = int(idx_str)
        if idx < len(st.session_state.all_customers):
            c = st.session_state.all_customers[idx]
            if "Ambient (kg)" in changes:    c.demand_ambient = changes["Ambient (kg)"] / 1000.0
            if "Fridge (kg)" in changes:     c.demand_refrigerated = changes["Fridge (kg)"] / 1000.0
            if "Needs Fridge" in changes:    c.needs_refrigeration = changes["Needs Fridge"]

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuration")
    max_demand = st.slider("Max demand per customer (t)", 1.0, 10.0, 8.0, 0.5)

    st.markdown("---")
    st.subheader("🪵 Europallet parameters")
    pallet_payload = st.slider("Net payload per pallet (kg)", 200, 1200, 800, 50)

# Asigură că clienții noi adăugați sunt incluși în active_customer_ids
for c in st.session_state.all_customers:
    if c.id not in st.session_state.active_customer_ids:
        st.session_state.active_customer_ids.add(c.id)

# Recalculează lista activă
st.session_state.customers = [
    c for c in st.session_state.all_customers
    if c.id in st.session_state.active_customer_ids
    and c.demand <= max_demand
]
st.sidebar.info(f"Active customers: **{len(st.session_state.customers)}**")

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
        "Daily capacity (pallets)": d.capacity,
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
            "Daily capacity (pallets)": st.column_config.NumberColumn(
                "Daily capacity (pallets)",
                min_value=1,
                help="Maximum number of europallets the depot can process and dispatch per day."
            )
        }
    )
    # Sync changes back to session state objects
    for i, row in enumerate(edited_depots):
        st.session_state.depots[i].num_vehicles = row["Vehicles available"]
        st.session_state.depots[i].capacity = row["Daily capacity (pallets)"]
        st.session_state.depots[i].daily_stock_tonnes = row["Daily stock (t)"]

    st.markdown("---")
    st.subheader("Daily incoming stock per depot")
    stock_df = pd.DataFrame({
        "Depot": [d.name for d in st.session_state.depots],
        "Stock (t/day)": [d.daily_stock_tonnes for d in st.session_state.depots],
    })
    st.bar_chart(stock_df.set_index("Depot"))

    st.markdown("---")
    st.subheader("Fleet allocation per depot")
    st.markdown("Specify how many vehicles of each type are stationed at each depot.")

    # Construiește tabelul de alocare
    alloc_data = []
    for depot in st.session_state.depots:
        row = {"Depot": depot.name}
        for vt in st.session_state.vehicle_types:
            row[vt.name] = depot.fleet_allocation.get(vt.id, 0)
        alloc_data.append(row)

    # Verificare: totalul per tip să nu depășească max_available
    st.caption("⚠️ Total per vehicle type across all depots cannot exceed **Max available** defined in Fleet & Pallets.")

    col_config = {"Depot": st.column_config.TextColumn(disabled=True)}
    for vt in st.session_state.vehicle_types:
        col_config[vt.name] = st.column_config.NumberColumn(
            vt.name,
            min_value=0,
            max_value=vt.max_available,
            step=1,
            help=f"Max available: {vt.max_available} | Refrigerated: {'Yes' if vt.is_refrigerated else 'No'}"
        )

    edited_alloc = st.data_editor(
        alloc_data,
        width='stretch',
        hide_index=True,
        column_config=col_config
    )

    # Validare și sincronizare
    alloc_valid = True
    for vt in st.session_state.vehicle_types:
        total_allocated = sum(row[vt.name] for row in edited_alloc)
        if total_allocated > vt.max_available:
            st.error(
                f"⚠️ **{vt.name}**: {total_allocated} allocated across depots "
                f"but only {vt.max_available} available. Please reduce."
            )
            alloc_valid = False

    if alloc_valid:
        for i, depot in enumerate(st.session_state.depots):
            for vt in st.session_state.vehicle_types:
                depot.fleet_allocation[vt.id] = edited_alloc[i][vt.name]
            # Actualizează și num_vehicles ca suma totală per depozit
            depot.num_vehicles = sum(depot.fleet_allocation.values())
        st.success("✅ Fleet allocation valid and saved.")

# ─── TAB 3: STORES ────────────────────────────────────────────────────────────
with tabs[2]:
    st.subheader("Store directory")
    st.markdown("All customer locations with addresses, daily demand, and time windows.")

    store_data = [{
        "Active":             c.id in st.session_state.active_customer_ids,
        "ID":                 c.id,
        "Store name":         c.name,
        "Ambient (kg)":       int(c.demand_ambient * 1000),
        "Fridge (kg)":        int(c.demand_refrigerated * 1000),
        "Needs Fridge":       c.needs_refrigeration,
        "Total Demand (t)":   round(c.demand, 2),
        "Pallets needed":     c.pallets_needed(EUROPALLET, pallet_payload),
        "Address":            c.address,
        "Latitude":           c.lat,
        "Longitude":          c.lon,
    } for c in st.session_state.all_customers]

    edited_store_data = st.data_editor(
        store_data, 
        width='stretch', 
        hide_index=True,
        key="stores_editor",
        on_change=on_store_edit,
        column_config={
            "Active": st.column_config.CheckboxColumn(
                "Active",
                help="Uncheck to exclude this store from routing",
                default=True
            ),
            "ID": st.column_config.NumberColumn(disabled=True),
            "Store name": st.column_config.TextColumn(disabled=True),
            "Ambient (kg)": st.column_config.NumberColumn(min_value=0, step=50),
            "Fridge (kg)": st.column_config.NumberColumn(min_value=0, step=50),
            "Needs Fridge": st.column_config.CheckboxColumn(),
            "Total Demand (t)": st.column_config.NumberColumn(disabled=True),
            "Pallets needed": st.column_config.NumberColumn(disabled=True),
            "Address": st.column_config.TextColumn(disabled=True),
            "Latitude":  st.column_config.NumberColumn("Latitude",  format="%.4f", disabled=True),
            "Longitude": st.column_config.NumberColumn("Longitude", format="%.4f", disabled=True),
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
            
        total_pallets = sum(c.pallets_needed(EUROPALLET, pallet_payload) for c in st.session_state.customers)
        st.metric("Total pallets needed", total_pallets)

    st.markdown("---")
    st.subheader("➕ Add new store")

    def geocode_address(address: str) -> tuple:
        """Returns (lat, lon) for a given address using Nominatim."""
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {"q": address, "format": "json", "limit": 1}
            headers = {"User-Agent": "FleetManagementApp/1.0"}
            with requests.get(url, params=params, headers=headers, timeout=5) as resp:
                resp.raise_for_status()
                data = resp.json()
                if data:
                    return float(data[0]["lat"]), float(data[0]["lon"])
        except Exception:
            pass
        return None, None

    st.markdown("**Input method:**")
    input_method = st.radio(
        "How to specify location:",
        ["📍 Enter address (auto geocode)", "🔢 Enter coordinates manually"],
        horizontal=True,
        label_visibility="collapsed"
    )

    with st.form("add_customer_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_name    = st.text_input("Store name", placeholder="Store Aviației")
            new_address = st.text_input("Address", placeholder="Strada Aviației 1, București")
            new_ambient = st.number_input("Ambient demand (kg)", min_value=0, max_value=10000, step=50, value=2000)
            new_fridge  = st.number_input("Refrigerated demand (kg)", min_value=0, max_value=10000, step=50, value=0)
        with col2:
            if input_method == "🔢 Enter coordinates manually":
                new_lat = st.number_input("Latitude",  min_value=44.0, max_value=45.0, value=44.46, format="%.4f")
                new_lon = st.number_input("Longitude", min_value=25.0, max_value=27.0, value=26.10, format="%.4f")
            else:
                st.info("📍 Coordinates will be auto-detected from the address using OpenStreetMap.")
                new_lat = None
                new_lon = None
            new_tw_open  = st.slider("Time window open",  0,  12,  6)
            new_tw_close = st.slider("Time window close", 12, 23, 18)

        submitted = st.form_submit_button("Add store", type="primary")

        if submitted:
            if not new_name.strip():
                st.error("Store name is required.")
            else:
                # Geocoding dacă e nevoie
                if input_method == "📍 Enter address (auto geocode)":
                    if not new_address.strip():
                        st.error("Address is required for geocoding.")
                        st.stop()
                    with st.spinner("Looking up coordinates..."):
                        new_lat, new_lon = geocode_address(new_address)
                    if new_lat is None:
                        st.error("Could not find coordinates for this address. Try a more specific address or use manual coordinates.")
                        st.stop()
                    st.success(f"📍 Found: {new_lat:.4f}, {new_lon:.4f}")

                existing_ids = {c.id for c in st.session_state.all_customers}
                new_id = max(existing_ids) + 1 if existing_ids else 100

                if new_lat is None or new_lon is None:
                    st.error("Coordinates are missing. Please try again.")
                    st.stop()

                from utils.data_models import Customer
                new_customer = Customer(
                    id=new_id,
                    name=new_name.strip(),
                    lat=float(new_lat),
                    lon=float(new_lon),
                    address=new_address.strip() or f"{float(new_lat):.4f}, {float(new_lon):.4f}",
                    demand_ambient=new_ambient / 1000.0,
                    demand_refrigerated=new_fridge / 1000.0,
                    needs_refrigeration=new_fridge > 0,
                    time_window_open=new_tw_open,
                    time_window_close=new_tw_close,
                    service_time=30
                )
                st.session_state.all_customers.append(new_customer)
                st.session_state.active_customer_ids.add(new_id)
                st.success(f"✅ **{new_name}** added at ({new_lat:.4f}, {new_lon:.4f})!")
                st.rerun()

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
        - Total daily pallets needed: **{sum(c.pallets_needed(EUROPALLET, pallet_payload) for c in st.session_state.customers)}**
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
    st.subheader("📑 Technical Fleet Details")
    st.info("Technical details and specifications for each vehicle type used in the model.")

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
    
    max_val = float(od_df.values.max())
    min_nonzero = float(od_df[od_df > 0].min().min())
    avg_val = float(od_df.values[od_df.values > 0].mean())

    st.caption(
        f"🟢 Green = short (min: {min_nonzero:.1f} km) · "
        f"🟡 Yellow = average ({avg_val:.1f} km) · "
        f"🔴 Red = long (max: {max_val:.1f} km) · "
        f"⬜ Diagonal = 0 (same node). "
        f"Colors are relative to the maximum distance in this network."
    )

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
