"""
Page 5 — Route Timeline
Step-by-step delivery schedule with estimated arrival times,
reload stops at depot, and pallet/weight tracking per stop.
"""
import streamlit as st
import pandas as pd
import math
from datetime import datetime, timedelta
import plotly.express as px

from utils.data_models import (
    DEPOTS_BUCHAREST, CUSTOMERS_BUCHAREST, VEHICLE_FLEET,
    EUROPALLET, haversine
)
from utils.mdvrp_algorithms import solve_mdvrp, get_transport_stats

st.title("🕐 Route Timeline & Delivery Schedule")
st.markdown(
    "Step-by-step delivery schedule for each vehicle: departure time, "
    "estimated arrival at each stop, reload events at depot, and pallet tracking."
)

# ── Session state ─────────────────────────────────────────────────────────────
if "depots"        not in st.session_state: st.session_state.depots        = DEPOTS_BUCHAREST.copy()
if "customers"     not in st.session_state: st.session_state.customers     = CUSTOMERS_BUCHAREST.copy()
if "vehicle_types" not in st.session_state: st.session_state.vehicle_types = VEHICLE_FLEET.copy()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Schedule parameters")

    departure_hour = st.slider("Depot departure time", 4, 10, 6)
    departure_min  = st.slider("Departure minute",     0, 59,  0, 5)
    avg_speed      = st.slider("Average speed (km/h)", 20, 90, 40)
    reload_time    = st.slider("Reload time at depot (min)", 10, 60, 20)
    pallet_payload = st.slider("Net payload per pallet (kg)", 200, 1200, 800, 50)

    st.markdown("---")
    vt_names = [vt.name for vt in st.session_state.vehicle_types]
    vt_sel   = st.selectbox("Vehicle type", vt_names, index=1)
    selected_vt = next(vt for vt in st.session_state.vehicle_types if vt.name == vt_sel)

    algo = st.selectbox("Routing algorithm", [
        "Clarke-Wright Savings", "Nearest Neighbor"
    ])
    apply_2opt = st.checkbox("Apply 2-opt improvement", value=True)

    run_btn = st.button("▶ Generate schedule", type="primary", width='stretch')

# ── Helper: build timeline for one route ─────────────────────────────────────

def build_timeline(route, departure_dt: datetime,
                   speed_kmh: float, reload_min: int,
                   pallet_payload_kg: float) -> list:
    """
    Build a list of timeline events for a single route.
    Each event: {stop, type, arrival, departure, distance_leg, load_kg, pallets, cumulative_km}
    Reload events are inserted when the vehicle returns to depot mid-route
    (here we model each route as one trip; reload logic shown for multi-trip extension).
    """
    pallet = EUROPALLET
    events = []
    current_time = departure_dt
    current_lat, current_lon = route.depot.lat, route.depot.lon
    cumulative_km = 0.0

    # Departure from depot
    load_kg     = route.total_demand * 1000
    pallets_loaded = math.ceil(load_kg / (pallet_payload_kg + pallet.weight_kg))

    events.append({
        "Stop #":          "0",
        "Location":        f"🏭 {route.depot.name}",
        "Address":         route.depot.address,
        "Event":           "Departure (loaded)",
        "Arrival":         "—",
        "Departure":       current_time.strftime("%H:%M"),
        "Leg dist (km)":   0.0,
        "Cumulative km":   "0.0",
        "Load on board (kg)": int(load_kg),
        "Pallets on board":   pallets_loaded,
        "Delivered (kg)":  0,
    })

    remaining_load = load_kg

    for idx, customer in enumerate(route.customers):
        # Travel leg
        leg_km = haversine(current_lat, current_lon, customer.lat, customer.lon)
        travel_min = (leg_km / speed_kmh) * 60
        arrival_time = current_time + timedelta(minutes=travel_min)
        cumulative_km += leg_km

        delivered_kg     = customer.demand * 1000
        remaining_load  -= delivered_kg
        pallets_delivered = math.ceil(delivered_kg / (pallet_payload_kg + pallet.weight_kg))
        pallets_remaining = math.ceil(max(remaining_load, 0) / (pallet_payload_kg + pallet.weight_kg))

        departure_time = arrival_time + timedelta(minutes=customer.service_time)

        events.append({
            "Stop #":             str(idx + 1),
            "Location":           f"🏪 {customer.name}",
            "Address":            customer.address,
            "Event":              "Delivery",
            "Arrival":            arrival_time.strftime("%H:%M"),
            "Departure":          departure_time.strftime("%H:%M"),
            "Leg dist (km)":      round(leg_km, 2),
            "Cumulative km":      str(round(cumulative_km, 2)),
            "Load on board (kg)": int(max(remaining_load, 0)),
            "Pallets on board":   pallets_remaining,
            "Delivered (kg)":     int(delivered_kg),
        })

        current_time = departure_time
        current_lat, current_lon = customer.lat, customer.lon

    # Return to depot
    return_km = haversine(current_lat, current_lon, route.depot.lat, route.depot.lon)
    cumulative_km += return_km
    return_arrival = current_time + timedelta(minutes=(return_km / speed_kmh) * 60)

    events.append({
        "Stop #":             str(len(route.customers) + 1),
        "Location":           f"🏭 {route.depot.name}",
        "Address":            route.depot.address,
        "Event":              "Return to depot",
        "Arrival":            return_arrival.strftime("%H:%M"),
        "Departure":          "—",
        "Leg dist (km)":      round(return_km, 2),
        "Cumulative km":      str(round(cumulative_km, 2)),
        "Load on board (kg)": 0,
        "Pallets on board":   0,
        "Delivered (kg)":     0,
    })

    return events


def build_multi_trip_timeline(route, departure_dt, speed_kmh,
                               reload_min, pallet_payload_kg,
                               max_pallets_per_trip) -> list:
    """
    If route demand exceeds one truck load, split into multiple trips with
    reload stops at the depot between trips.
    """
    pallet = EUROPALLET
    all_events = []
    customers_remaining = list(route.customers)
    current_time = departure_dt
    trip_num = 1

    while customers_remaining:
        # Fill this trip up to capacity
        trip_customers = []
        trip_pallets   = 0
        trip_load_kg   = 0.0

        for c in customers_remaining:
            c_pallets = math.ceil((c.demand * 1000) / (pallet_payload_kg + pallet.weight_kg))
            if trip_pallets + c_pallets <= max_pallets_per_trip:
                trip_customers.append(c)
                trip_pallets  += c_pallets
                trip_load_kg  += c.demand * 1000

        if not trip_customers:
            # Edge case: single customer exceeds capacity — take it anyway
            trip_customers = [customers_remaining[0]]
            trip_load_kg   = trip_customers[0].demand * 1000
            trip_pallets   = math.ceil(trip_load_kg / (pallet_payload_kg + pallet.weight_kg))

        for c in trip_customers:
            customers_remaining.remove(c)

        # Departure from depot
        all_events.append({
            "Stop #":             f"T{trip_num}-0",
            "Location":           f"🏭 {route.depot.name}",
            "Address":            route.depot.address,
            "Event":              f"Trip {trip_num} departure (loaded)",
            "Arrival":            "—",
            "Departure":          current_time.strftime("%H:%M"),
            "Leg dist (km)":      0.0,
            "Cumulative km":      "—",
            "Load on board (kg)": int(trip_load_kg),
            "Pallets on board":   trip_pallets,
            "Delivered (kg)":     0,
        })

        cur_lat, cur_lon = route.depot.lat, route.depot.lon
        remaining = trip_load_kg

        for idx, customer in enumerate(trip_customers):
            leg_km     = haversine(cur_lat, cur_lon, customer.lat, customer.lon)
            travel_min = (leg_km / speed_kmh) * 60
            arrival    = current_time + timedelta(minutes=travel_min)
            delivered  = customer.demand * 1000
            remaining -= delivered
            dep_time   = arrival + timedelta(minutes=customer.service_time)
            p_rem      = math.ceil(max(remaining, 0) / (pallet_payload_kg + pallet.weight_kg))

            all_events.append({
                "Stop #":             f"T{trip_num}-{idx+1}",
                "Location":           f"🏪 {customer.name}",
                "Address":            customer.address,
                "Event":              "Delivery",
                "Arrival":            arrival.strftime("%H:%M"),
                "Departure":          dep_time.strftime("%H:%M"),
                "Leg dist (km)":      round(leg_km, 2),
                "Cumulative km":      "—",
                "Load on board (kg)": int(max(remaining, 0)),
                "Pallets on board":   p_rem,
                "Delivered (kg)":     int(delivered),
            })
            current_time = dep_time
            cur_lat, cur_lon = customer.lat, customer.lon

        # Return to depot
        ret_km  = haversine(cur_lat, cur_lon, route.depot.lat, route.depot.lon)
        ret_arr = current_time + timedelta(minutes=(ret_km / speed_kmh) * 60)

        if customers_remaining:
            # More trips needed → reload
            reload_done = ret_arr + timedelta(minutes=reload_min)
            all_events.append({
                "Stop #":             f"T{trip_num}-R",
                "Location":           f"🏭 {route.depot.name}",
                "Address":            route.depot.address,
                "Event":              f"⟳ Return & RELOAD (trip {trip_num} → {trip_num+1})",
                "Arrival":            ret_arr.strftime("%H:%M"),
                "Departure":          reload_done.strftime("%H:%M"),
                "Leg dist (km)":      round(ret_km, 2),
                "Cumulative km":      "—",
                "Load on board (kg)": 0,
                "Pallets on board":   0,
                "Delivered (kg)":     0,
            })
            current_time = reload_done
        else:
            all_events.append({
                "Stop #":             f"T{trip_num}-R",
                "Location":           f"🏭 {route.depot.name}",
                "Address":            route.depot.address,
                "Event":              "Final return to depot",
                "Arrival":            ret_arr.strftime("%H:%M"),
                "Departure":          "—",
                "Leg dist (km)":      round(ret_km, 2),
                "Cumulative km":      "—",
                "Load on board (kg)": 0,
                "Pallets on board":   0,
                "Delivered (kg)":     0,
            })

        trip_num += 1

    return all_events


# ── Solve / use cached routes ─────────────────────────────────────────────────
if run_btn:
    algo_key = "clarke_wright" if "Clarke" in algo else "nearest_neighbor"
    routes, _ = solve_mdvrp(
        st.session_state.depots, st.session_state.customers,
        selected_vt, algo_key, apply_2opt, load_balance=True,
        start_hour=departure_hour, speed_kmh=avg_speed
    )
    st.session_state.routes      = routes
    st.session_state.tl_vt       = selected_vt
    st.session_state.tl_algo     = algo
    st.success(f"✅ {len(routes)} routes generated.")

routes = st.session_state.get("routes")

if not routes:
    st.info("👈 Click **'Generate schedule'** in the sidebar to compute routes and build the timeline.")
    st.markdown("""
    **This page shows:**
    - Departure time from depot
    - Estimated arrival and departure at each customer stop
    - Load on board (kg) and pallets after each delivery
    - Reload stops when a vehicle needs to return to depot for more goods
    - Total route duration and distance
    """)
    st.stop()

# ── Display timelines ─────────────────────────────────────────────────────────
departure_dt = datetime.now().replace(
    hour=departure_hour, minute=departure_min, second=0, microsecond=0
)

st.markdown(f"**Departure:** {departure_dt.strftime('%H:%M')} | **Speed:** {avg_speed} km/h | **Algorithm:** {st.session_state.get('tl_algo', algo)}")

# ── Pre-calculate all data in one pass ────────────────────────────────────────
summary_rows = []
gantt_data = []
route_events = {} # Cache for expanders
base_date = datetime.now().date()
max_p = selected_vt.max_pallets(EUROPALLET, pallet_payload)

for i, route in enumerate(routes):
    used_p = math.ceil((route.total_demand * 1000) / (pallet_payload + EUROPALLET.weight_kg))
    
    # 1. Build Timeline Events
    if used_p > max_p:
        evs = build_multi_trip_timeline(route, departure_dt, avg_speed, reload_time, pallet_payload, max_p)
    else:
        evs = build_timeline(route, departure_dt, avg_speed, reload_time, pallet_payload)
    
    route_events[i] = evs

    # 2. Build Summary Data
    summary_rows.append({
        "Route": f"Route {i+1}", "Depot": route.depot.name,
        "Pallets": used_p, "Pallet util (%)": round(used_p / max_p * 100, 1) if max_p else 0,
        "Distance (km)": route.total_distance, "Cost (€)": route.total_cost
    })

    # 3. Build Gantt Data
    for j in range(len(evs) - 1):
        start_str = evs[j]["Departure"] if evs[j]["Departure"] != "—" else evs[j]["Arrival"]
        end_str = evs[j+1]["Arrival"]
        if start_str != "—" and end_str != "—":
            st_t = datetime.combine(base_date, datetime.strptime(start_str, "%H:%M").time())
            en_t = datetime.combine(base_date, datetime.strptime(end_str, "%H:%M").time())
            activity = "Transit (Driving)"
            if "Delivery" in evs[j+1]["Event"]: activity = "Unloading (Service)"
            if "RELOAD" in evs[j+1]["Event"] or "Trip" in evs[j]["Event"]: activity = "Loading/Wait (Depot)"
            gantt_data.append({
                "Vehicul": f"R{i+1} ({route.vehicle_type.name})",
                "Start": st_t, "End": en_t, "Activity": activity, "Location": evs[j+1]["Location"]
            })

# ── Display Sumar ─────────────────────────────────────────────────────────────
st.subheader("📋 Route Summary")
df_sum = pd.DataFrame(summary_rows)
def color_putil(val):
    if val >= 80: return "background-color: #d4edda"
    if val >= 50: return "background-color: #fff3cd"
    return "background-color: #f8d7da"
st.dataframe(df_sum.style.map(color_putil, subset=["Pallet util (%)"]), width='stretch', hide_index=True)

st.markdown("#### 📈 Operating Parameters (Total Fleet)")
t_stats = get_transport_stats(routes)
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Traffic flow", f"{t_stats['traffic_flow']:.1f} km/day")
kpi2.metric("Transport flow", f"{t_stats['transport_flow']:.1f} v-inc*km")
kpi3.metric("Empty run %", f"{t_stats['empty_pct']:.1f} %")
kpi4.metric("Daily performance", f"{t_stats['performance']:.1f} t*km/day")

# ── Display Ciclograma (Gantt) ────────────────────────────────────────────────
st.markdown("---")
st.subheader("📊 Movement Cyclogram")
if gantt_data:
    fig_gantt = px.timeline(pd.DataFrame(gantt_data), x_start="Start", x_end="End", y="Vehicul", 
                            color="Activity", hover_data=["Location"],
                            color_discrete_map={"Transit (Driving)": "#3B8BD4", "Unloading (Service)": "#1D9E75", "Loading/Wait (Depot)": "#E94560"})
    fig_gantt.update_layout(xaxis_title="Timeline", yaxis_title="", height=300 + (len(routes)*30))
    st.plotly_chart(fig_gantt, use_container_width=True)

# ── Display Details ───────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📝 Step-by-Step Details")
for i, route in enumerate(routes):
    with st.expander(f"🚛 Route {i+1} — {route.depot.name} | {route.total_distance:.1f} km", expanded=(i == 0)):
        events = route_events[i]
        if len(events) > len(route.customers) + 2: # Multi-trip detection
            st.warning("⚠️ This route requires reloading at the depot (Multi-trip).")
        
        df_tl = pd.DataFrame(events)

        def style_event(val):
            if "Departure" in str(val) and "loaded" in str(val):
                return "background-color: #d0e8ff; font-weight: 500"
            if "RELOAD" in str(val):
                return "background-color: #fff3cd; font-weight: 600"
            if "Return" in str(val) and "RELOAD" not in str(val):
                return "background-color: #e8f5e9"
            if "Delivery" in str(val):
                return "background-color: #ffffff"
            return ""

        st.dataframe(
            df_tl.style.map(style_event, subset=["Event"]),
            width='stretch',
            hide_index=True,
            height=min(38 * len(events) + 50, 520)
        )

        # Route duration
        first_dep = [e for e in events if e["Departure"] != "—"]
        last_arr  = [e for e in events if e["Arrival"]   != "—"]
        if first_dep and last_arr:
            dep_str = first_dep[0]["Departure"]
            arr_str = last_arr[-1]["Arrival"]
            dep_t   = datetime.strptime(dep_str, "%H:%M")
            arr_t   = datetime.strptime(arr_str, "%H:%M")
            duration = (arr_t - dep_t).seconds // 60
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Departure",        dep_str)
            c2.metric("Final return",     arr_str)
            c3.metric("Total duration",   f"{duration // 60}h {duration % 60}min")
            c4.metric("Total distance",   f"{route.total_distance:.1f} km")
