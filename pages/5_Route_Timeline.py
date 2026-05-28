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
import plotly.graph_objects as go

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
    shift_end      = st.slider("Shift end hour", 16, 24, 22)
    reload_time    = st.slider("Reload time at depot (min)", 10, 60, 20)
    unload_per_pallet = st.slider("Unloading time per pallet (min)", 1, 10, 2)
    pallet_payload = st.slider("Net payload per pallet (kg)", 200, 1200, 800, 50)

    st.markdown("---")
    vt_options = ["Mixed Fleet (Auto-select)"] + [vt.name for vt in st.session_state.vehicle_types]
    vt_sel     = st.selectbox("Vehicle type", vt_options, index=0)

    if vt_sel == "Mixed Fleet (Auto-select)":
        selected_vt = st.session_state.vehicle_types
    else:
        selected_vt = next(vt for vt in st.session_state.vehicle_types if vt.name == vt_sel)

    algo = st.selectbox("Routing algorithm", [
        "Clarke-Wright Savings", "Nearest Neighbor"
    ])
    apply_2opt = st.checkbox("Apply 2-opt improvement", value=True)

    run_btn = st.button("▶ Generate schedule", type="primary", width='stretch')

# ── Helper: build timeline for one route ─────────────────────────────────────

def clean_name(name: str) -> str:
    import re
    return re.sub(r'\s*\([^)]*P\d+\)\s*$', '', name).strip()


def travel_time_minutes(dist_km: float, speed_kmh: float) -> float:
    """
    Realistic travel time including acceleration and deceleration phases.
    For short distances, a vehicle never reaches cruising speed.
    
    Model: assumes 2 min fixed overhead per stop (traffic lights, 
    parking, maneuvering) + distance/speed travel time.
    Minimum travel time = 1 min regardless of distance.
    """
    if dist_km <= 0:
        return 0.0
    
    # Timp de bază la viteza de croazieră
    base_min = (dist_km / speed_kmh) * 60.0
    # Overhead fix per deplasare urbană (semafoare, manevre, parcare)
    overhead_min = 2.0
    total = base_min + overhead_min
    return max(total, 1.0)  # Minim 1 minut

def build_timeline(route, departure_dt: datetime,
                   speed_kmh: float, reload_min: int,
                   pallet_payload_kg: float, unload_per_pallet: int = 2) -> list:
    """
    Build a list of timeline events for a single route.
    Each event: {stop, type, arrival, departure, distance_leg, load_kg, pallets, cumulative_km, dist_from_depot}
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
        "DepartureDT":     current_time,
        "Leg dist (km)":   0.0,
        "Cumulative km":   f"{0.0:.2f}",
        "Dist from Depot": 0.0,
        "Load on board (kg)": int(load_kg),
        "Pallets on board":   pallets_loaded,
        "Delivered (kg)":  0,
    })

    remaining_load = load_kg

    for idx, customer in enumerate(route.customers):
        # Travel leg
        leg_km = haversine(current_lat, current_lon, customer.lat, customer.lon)
        travel_min = travel_time_minutes(leg_km, speed_kmh)
        arrival_time = current_time + timedelta(minutes=travel_min)
        cumulative_km += leg_km
        dist_from_depot = haversine(route.depot.lat, route.depot.lon, customer.lat, customer.lon)

        delivered_kg     = customer.demand * 1000
        remaining_load  -= delivered_kg
        pallets_delivered = math.ceil(delivered_kg / (pallet_payload_kg + pallet.weight_kg))
        pallets_remaining = math.ceil(max(remaining_load, 0) / (pallet_payload_kg + pallet.weight_kg))

        service_min = pallets_delivered * unload_per_pallet
        departure_time = arrival_time + timedelta(minutes=service_min)

        events.append({
            "Stop #":             str(idx + 1),
            "Location":           f"🏪 {clean_name(customer.name)}",
            "Address":            customer.address,
            "Event":              "Delivery",
            "Arrival":            arrival_time.strftime("%H:%M"),
            "ArrivalDT":          arrival_time,
            "Departure":          departure_time.strftime("%H:%M"),
            "DepartureDT":        departure_time,
            "Leg dist (km)":      round(leg_km, 2),
            "Cumulative km":      f"{cumulative_km:.2f}",
            "Dist from Depot":    round(dist_from_depot, 2),
            "Load on board (kg)": int(max(remaining_load, 0)),
            "Pallets on board":   pallets_remaining,
            "Delivered (kg)":     int(delivered_kg),
        })

        current_time = departure_time
        current_lat, current_lon = customer.lat, customer.lon

    # Return to depot
    return_km = haversine(current_lat, current_lon, route.depot.lat, route.depot.lon)
    cumulative_km += return_km
    return_arrival = current_time + timedelta(minutes=travel_time_minutes(return_km, speed_kmh))

    events.append({
        "Stop #":             str(len(route.customers) + 1),
        "Location":           f"🏭 {route.depot.name}",
        "Address":            route.depot.address,
        "Event":              "Return to depot",
        "Arrival":            return_arrival.strftime("%H:%M"),
        "ArrivalDT":          return_arrival,
        "Departure":          "—",
        "Leg dist (km)":      round(return_km, 2),
        "Cumulative km":      f"{cumulative_km:.2f}",
        "Dist from Depot":    0.0,
        "Load on board (kg)": 0,
        "Pallets on board":   0,
        "Delivered (kg)":     0,
    })

    return events


def build_multi_trip_timeline(route, departure_dt, speed_kmh,
                               reload_min, pallet_payload_kg,
                               max_pallets_per_trip, unload_per_pallet: int = 2) -> list:
    """
    If route demand exceeds one truck load, split into multiple trips with
    reload stops at the depot between trips.
    """
    pallet = EUROPALLET
    all_events = []
    customers_remaining = list(route.customers)
    current_time = departure_dt
    trip_num = 1
    cumulative_km = 0.0

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
            "DepartureDT":        current_time,
            "Leg dist (km)":      0.0,
            "Cumulative km":      f"{cumulative_km:.2f}",
            "Dist from Depot":    0.0,
            "Load on board (kg)": int(trip_load_kg),
            "Pallets on board":   trip_pallets,
            "Delivered (kg)":     0,
        })

        cur_lat, cur_lon = route.depot.lat, route.depot.lon
        remaining = trip_load_kg

        for idx, customer in enumerate(trip_customers):
            leg_km     = haversine(cur_lat, cur_lon, customer.lat, customer.lon)
            cumulative_km += leg_km
            travel_min = travel_time_minutes(leg_km, speed_kmh)
            arrival    = current_time + timedelta(minutes=travel_min)
            delivered  = customer.demand * 1000
            remaining -= delivered
            pallets_to_deliver = math.ceil(delivered / (pallet_payload_kg + pallet.weight_kg))
            service_min = pallets_to_deliver * unload_per_pallet
            dep_time   = arrival + timedelta(minutes=service_min)
            p_rem      = math.ceil(max(remaining, 0) / (pallet_payload_kg + pallet.weight_kg))
            dist_dep   = haversine(route.depot.lat, route.depot.lon, customer.lat, customer.lon)

            all_events.append({
                "Stop #":             f"T{trip_num}-{idx+1}",
                "Location":           f"🏪 {clean_name(customer.name)}",
                "Address":            customer.address,
                "Event":              "Delivery",
                "Arrival":            arrival.strftime("%H:%M"),
                "ArrivalDT":          arrival,
                "Departure":          dep_time.strftime("%H:%M"),
                "DepartureDT":        dep_time,
                "Leg dist (km)":      round(leg_km, 2),
                "Cumulative km":      f"{cumulative_km:.2f}",
                "Dist from Depot":    round(dist_dep, 2),
                "Load on board (kg)": int(max(remaining, 0)),
                "Pallets on board":   p_rem,
                "Delivered (kg)":     int(delivered),
            })
            current_time = dep_time
            cur_lat, cur_lon = customer.lat, customer.lon

        # Return to depot
        ret_km  = haversine(cur_lat, cur_lon, route.depot.lat, route.depot.lon)
        cumulative_km += ret_km
        ret_arr = current_time + timedelta(minutes=travel_time_minutes(ret_km, speed_kmh))

        if customers_remaining:
            # More trips needed → reload
            reload_done = ret_arr + timedelta(minutes=reload_min)
            all_events.append({
                "Stop #":             f"T{trip_num}-R",
                "Location":           f"🏭 {route.depot.name}",
                "Address":            route.depot.address,
                "Event":              f"⟳ Return & RELOAD (trip {trip_num} → {trip_num+1})",
                "Arrival":            ret_arr.strftime("%H:%M"),
                "ArrivalDT":          ret_arr,
                "Departure":          reload_done.strftime("%H:%M"),
                "DepartureDT":        reload_done,
                "Leg dist (km)":      round(ret_km, 2),
                "Cumulative km":      f"{cumulative_km:.2f}",
                "Dist from Depot":    0.0,
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
                "ArrivalDT":          ret_arr,
                "Departure":          "—",
                "Leg dist (km)":      round(ret_km, 2),
                "Cumulative km":      f"{cumulative_km:.2f}",
                "Dist from Depot":    0.0,
                "Load on board (kg)": 0,
                "Pallets on board":   0,
                "Delivered (kg)":     0,
            })

        trip_num += 1

    return all_events


# ── Solve / use cached routes ─────────────────────────────────────────────────
if run_btn:
    algo_key = "clarke_wright" if "Clarke" in algo else "nearest_neighbor"
    routes, _, ref_warnings = solve_mdvrp(
        st.session_state.depots, st.session_state.customers,
        selected_vt, algo_key, apply_2opt, load_balance=True,
        start_hour=departure_hour, speed_kmh=avg_speed, shift_end_hour=shift_end
    )

    if ref_warnings:
        st.warning("⚠️ Refrigeration assignment issues detected:")
        for w in ref_warnings:
            st.write(f"- {w}")

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

ROUTE_COLORS = ["#E94560", "#3B8BD4", "#1D9E75", "#BA7517", "#9c42c9", "#D4537E"]

st.markdown(f"**Departure:** {departure_dt.strftime('%H:%M')} | **Speed:** {avg_speed} km/h | **Algorithm:** {st.session_state.get('tl_algo', algo)}")

# ── Pre-calculate all data in one pass ────────────────────────────────────────
summary_rows = []
route_events = {} # Cache for expanders
base_date = datetime.now().date()
if isinstance(selected_vt, list):
    max_p = max(vt.max_pallets(EUROPALLET, pallet_payload) for vt in selected_vt)
else:
    max_p = selected_vt.max_pallets(EUROPALLET, pallet_payload)

for i, route in enumerate(routes):
    used_p = route.total_pallets(EUROPALLET, pallet_payload)
    util_pct = round(min(used_p / max_p * 100, 100.0), 2) if max_p else 0.0
    
    # 1. Build Timeline Events
    if used_p > max_p:
        evs = build_multi_trip_timeline(route, departure_dt, avg_speed, reload_time, pallet_payload, max_p, unload_per_pallet)
    else:
        evs = build_timeline(route, departure_dt, avg_speed, reload_time, pallet_payload, unload_per_pallet)
    
    route_events[i] = evs

    # 2. Build Summary Data
    summary_rows.append({
        "Route": f"Route {i+1}",
        "Depot": route.depot.name,
        "Pallets": used_p,
        "Pallet util (%)": round(min(used_p / max_p * 100, 100.0), 2) if max_p else 0.0,
        "Distance (km)": round(route.total_distance, 2),
        "Cost (€)": round(route.total_cost, 2)
    })

# ── Display Sumar ─────────────────────────────────────────────────────────────
st.subheader("📋 Route Summary")
df_sum = pd.DataFrame(summary_rows)
def color_putil(val):
    if val >= 80: return "background-color: #2e7d32; color: white; font-weight: 600"
    if val >= 50: return "background-color: #f57f17; color: white; font-weight: 600"
    return "background-color: #c62828; color: white; font-weight: 600"
st.dataframe(df_sum.style.map(color_putil, subset=["Pallet util (%)"]), width='stretch', hide_index=True)

st.markdown("#### 📈 Operating Parameters (Total Fleet)")
t_stats = get_transport_stats(routes)

# Calculează gradul de utilizare al flotei
total_demand_served = sum(r.total_demand for r in routes)
total_capacity      = sum(r.vehicle_type.capacity for r in routes)
fleet_util          = (total_demand_served / total_capacity * 100) if total_capacity > 0 else 0.0

st.markdown("""
| Parameter | Formula | Value | Description |
|---|---|---|---|
| 🛣️ Traffic Flow | $F_{{trafic}} = \\sum n_i \\cdot d_i$ | **{:.2f} km/day** | Total km driven by all vehicles |
| 🚛 Transport Flow | $F_{{transport}} = \\sum n_i \\cdot (d_i - d_i')$ | **{:.2f} veh·km/day** | Km driven while carrying goods |
| 🔄 Empty Run % | $P_{{gol}} = \\frac{{P_{{dg}}}}{{P_{{total}}}} \\cdot 100$ | **{:.2f} %** | Share of distance driven empty |
| 📦 Daily Performance | $P_{{perf}} = \\sum q_i \\cdot d_i$ | **{:.2f} t·km/day** | Total transport work done |
| 📊 Fleet Utilization | $U = \\frac{{P_z}}{{q_{{veh}} \\cdot P_{{total}}}} \\cdot 100$ | **{:.2f} %** | Load vs total fleet capacity |
""".format(
    t_stats['traffic_flow'],
    t_stats['transport_flow'],
    t_stats['empty_pct'],
    t_stats['performance'],
    fleet_util
))

# ── Display Details ───────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📝 Step-by-Step Details")
for i, route in enumerate(routes):
    with st.expander(f"🚛 Route {i+1} — {route.depot.name} | {route.total_distance:.1f} km", expanded=(i == 0)):
        events = route_events[i]
        if len(events) > len(route.customers) + 2: # Multi-trip detection
            st.warning("⚠️ This route requires reloading at the depot (Multi-trip).")
        
        df_tl = pd.DataFrame(events)

        # Selectăm doar coloanele esențiale pentru vizualizarea în tabel
        visible_cols = [
            "Stop #", "Location", "Address", "Event", "Arrival", 
            "Departure", "Leg dist (km)", "Cumulative km"
        ]

        def style_event(val):
            if "Departure" in str(val) and "loaded" in str(val):
                return "background-color: #1e3a8a; color: white; font-weight: bold"
            if "RELOAD" in str(val):
                return "background-color: #f59e0b; color: black; font-weight: bold"
            if "Return" in str(val) and "RELOAD" not in str(val):
                return "background-color: #065f46; color: white; font-weight: bold"
            if "Delivery" in str(val):
                return "background-color: #f3f4f6; color: black"
            return ""

        st.dataframe(
            df_tl[visible_cols].style.map(style_event, subset=["Event"]),
            width='stretch',
            hide_index=True,
            height=min(38 * len(events) + 50, 520)
        )

        # ── Individual Cyclogram for this route ──
        df_local = []
        for ev in events:
            dist = ev["Dist from Depot"]
            if "DepartureDT" in ev:
                df_local.append({"Time": ev["DepartureDT"], "Distance": dist, "Location": ev["Location"]})
            if "ArrivalDT" in ev:
                df_local.append({"Time": ev["ArrivalDT"], "Distance": dist, "Location": ev["Location"]})
        
        if df_local:
            df_plot = pd.DataFrame(df_local).sort_values("Time")
            fig_r = go.Figure()
            color = ROUTE_COLORS[i % len(ROUTE_COLORS)]

            fig_r.add_trace(go.Scatter(
                x=df_plot["Time"], y=df_plot["Distance"],
                mode='lines+markers',
                line=dict(color=color, width=3),
                marker=dict(size=6),
                hovertemplate="<b>%{text}</b><br>Ora: %{x|%H:%M}<br>Dist: %{y} km<extra></extra>",
                text=df_plot["Location"]
            ))

            # Linii punctate orizontale pentru repere clienți
            for _, row in df_plot[df_plot["Distance"] > 0].iterrows():
                fig_r.add_shape(type="line", x0=df_plot["Time"].min(), x1=row["Time"],
                                y0=row["Distance"], y1=row["Distance"],
                                line=dict(color=color, width=1, dash="dot"), opacity=0.2)

            fig_r.update_layout(
                title=f"Movement Profile — Route {i+1}",
                xaxis_title="Timeline",
                yaxis_title="Km from Depot",
                height=300,
                margin=dict(t=40, b=40, l=40, r=20),
                hovermode="x unified",
                showlegend=False,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0.02)"
            )
            st.plotly_chart(fig_r, use_container_width=True)

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
