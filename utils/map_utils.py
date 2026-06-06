"""
Map visualization utilities using Folium (OpenStreetMap).
Renders depots, customers, and optimized routes on an interactive map.
"""
import folium
from folium import plugins
from typing import List, Optional
import re
from utils.data_models import Depot, Customer, Route

DEPOT_COLORS = ["darkblue", "darkred", "darkgreen", "purple", "orange"]
ROUTE_COLORS = [
    "#E94560",  # roșu aprins
    "#2196F3",  # albastru
    "#FF9800",  # portocaliu
    "#9C27B0",  # violet
    "#00BCD4",  # cyan
    "#F44336",  # roșu închis
    "#4CAF50",  # verde
    "#FF5722",  # portocaliu închis
    "#673AB7",  # indigo
    "#009688",  # teal
]


def clean_name(name: str) -> str:
    """Removes virtual suffixes like (📦 P1) or (❄️ P2)."""
    # Înlocuiește (❄️ P1) cu (❄️) și (📦 P1) cu (📦)
    name = re.sub(r'\((❄️)\s*P\d+\)', r'(\1)', name)
    name = re.sub(r'\((📦)\s*P\d+\)', r'(📦)', name)
    # Scoate orice alt sufix (P1), (P2) rămas
    name = re.sub(r'\s*\([^)]*P\d+\)\s*$', '', name)
    return name.strip()


def build_map(
    depots: List[Depot],
    customers: List[Customer],
    routes: Optional[List[Route]] = None,
    zoom: int = 11
) -> folium.Map:
    all_lats = [d.lat for d in depots] + [c.lat for c in customers]
    all_lons = [d.lon for d in depots] + [c.lon for c in customers]
    center = (sum(all_lats) / len(all_lats), sum(all_lons) / len(all_lons))

    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles="OpenStreetMap",
        control_scale=True
    )

    # Feature groups — liniile se adaugă direct pe m, markerii în feature groups
    fg_routes    = folium.FeatureGroup(name="🛣️ Routes",    show=True)
    fg_customers = folium.FeatureGroup(name="📦 Customers",  show=True)
    fg_depots    = folium.FeatureGroup(name="🏭 Depots",     show=True)

    # ── Depot markers ─────────────────────────────────────────────────────────
    for i, depot in enumerate(depots):
        color = DEPOT_COLORS[i % len(DEPOT_COLORS)]
        folium.Marker(
            location=[depot.lat, depot.lon],
            popup=folium.Popup(
                f"""<div style='font-family:sans-serif;min-width:180px'>
                    <b style='color:{color}'>{depot.name}</b><br>
                    <hr style='margin:4px 0'>
                    📍 {depot.lat:.4f}, {depot.lon:.4f}<br>
                    🚛 Vehicles available: {depot.num_vehicles}<br>
                    📦 Daily capacity: {depot.capacity} units
                </div>""",
                max_width=220
            ),
            tooltip=f"🏭 {depot.name}",
            icon=folium.Icon(color=color, icon="home", prefix="fa")
        ).add_to(fg_depots)

        folium.Circle(
            location=[depot.lat, depot.lon],
            radius=1500, color=color,
            fill=True, fill_opacity=0.05,
            weight=1, dash_array="5"
        ).add_to(fg_depots)

    # ── Customer-to-depot mapping ─────────────────────────────────────────────
    depot_color_map = {d.id: DEPOT_COLORS[i % len(DEPOT_COLORS)] for i, d in enumerate(depots)}
    cust_depot_map = {}
    if routes:
        for route in routes:
            for c in route.customers:
                cust_depot_map[c.id] = route.depot.id

    # ── Customer markers ──────────────────────────────────────────────────────
    for c in customers:
        depot_id = cust_depot_map.get(c.id, depots[0].id)
        color = depot_color_map.get(depot_id, "blue")
        folium.CircleMarker(
            location=[c.lat, c.lon],
            radius=8, color="white", weight=2,
            fill=True, fill_color=color, fill_opacity=0.85,
            popup=folium.Popup(
                f"""<div style='font-family:sans-serif;min-width:160px'>
                    <b>{clean_name(c.name)}</b><br>
                    <hr style='margin:4px 0'>
                    📦 Demand: <b>{c.demand} t</b><br>
                    🕐 Time window: {c.time_window_open}:00 – {c.time_window_close}:00<br>
                    ⏱️ Service time: {c.service_time} min
                </div>""",
                max_width=200
            ),
            tooltip=f"📦 {clean_name(c.name)} ({c.demand}t)"
        ).add_to(fg_customers)

    # ── Route polylines ───────────────────────────────────────────────────────
    if routes:
        for i, route in enumerate(routes):
            if not route.customers:
                continue

            color = ROUTE_COLORS[i % len(ROUTE_COLORS)]
            coords = (
                [[route.depot.lat, route.depot.lon]]
                + [[c.lat, c.lon] for c in route.customers]
                + [[route.depot.lat, route.depot.lon]]
            )

            sequence_html = (
                f"<b>{route.depot.name}</b> (start)<br>"
                + "".join(
                    f"&nbsp;&nbsp;{j+1}. {clean_name(c.name)}<br>"
                    for j, c in enumerate(route.customers)
                )
                + f"<b>{route.depot.name}</b> (return)"
            )

            # Grosimi alternante: 6, 4, 6, 4... ca rutele suprapuse să fie vizibile
            weight = 6 if i % 2 == 0 else 4

            # Linie principală — adăugată DIRECT pe hartă (nu în fg_routes)
            # Garantează că liniile sunt randate primele, sub orice marker
            folium.PolyLine(
                locations=coords,
                color=color,
                weight=weight,
                opacity=0.85,
                tooltip=(
                    f"Route {i+1} — {route.depot.name} | "
                    f"{len(route.customers)} stops | "
                    f"{route.total_distance:.1f} km"
                ),
                popup=folium.Popup(
                    f"""<div style='font-family:sans-serif;min-width:220px'>
                        <b style='color:{color}'>Route {i+1}</b><br>
                        <hr style='margin:4px 0'>
                        🏭 Depot: {route.depot.name}<br>
                        🚛 Vehicle: {route.vehicle_type.name}<br>
                        📦 Demand: {route.total_demand} t<br>
                        📏 Distance: {route.total_distance} km<br>
                        💰 Cost: {route.total_cost:.0f} €<br>
                        <hr style='margin:4px 0'>
                        <b>Sequence:</b><br>{sequence_html}
                    </div>""",
                    max_width=280
                )
            ).add_to(m)

            # AntPath animat — direct pe hartă
            plugins.AntPath(
                locations=coords,
                color=color,
                weight=3,
                opacity=0.5,
                delay=1200,
                dash_array=[10, 20],
                pulse_color="#ffffff"
            ).add_to(m)

            # Număr rută la mijlocul traseului — în fg_routes
            mid_idx = len(coords) // 2
            mid_lat, mid_lon = coords[mid_idx]
            folium.Marker(
                location=[mid_lat, mid_lon],
                icon=folium.DivIcon(
                    html=f"""<div style="
                        background:{color};
                        color:white;
                        border-radius:50%;
                        width:26px;height:26px;
                        display:flex;align-items:center;justify-content:center;
                        font-size:13px;font-weight:bold;
                        border:2px solid white;
                        box-shadow:0 2px 5px rgba(0,0,0,0.5);
                        font-family:sans-serif;">{i+1}</div>""",
                    icon_size=(26, 26),
                    icon_anchor=(13, 13)
                ),
                tooltip=f"Route {i+1}"
            ).add_to(fg_routes)

            # Număr stop pe fiecare client — în fg_routes
            for j, c in enumerate(route.customers):
                folium.Marker(
                    location=[c.lat, c.lon],
                    icon=folium.DivIcon(
                        html=f"""<div style="
                            background:white;
                            color:{color};
                            border-radius:50%;
                            width:16px;height:16px;
                            display:flex;align-items:center;justify-content:center;
                            font-size:9px;font-weight:bold;
                            border:1.5px solid {color};
                            box-shadow:0 1px 3px rgba(0,0,0,0.3);
                            font-family:sans-serif;
                            margin-left:10px;margin-top:-22px;">{j+1}</div>""",
                        icon_size=(16, 16),
                        icon_anchor=(8, 8)
                    ),
                    tooltip=f"R{i+1} — Stop {j+1}: {clean_name(c.name)}"
                ).add_to(fg_routes)

        # Legendă
        legend_items = "".join(
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:5px">'
            f'<div style="width:14px;height:14px;border-radius:50%;'
            f'background:{ROUTE_COLORS[i % len(ROUTE_COLORS)]};'
            f'color:white;font-size:9px;font-weight:bold;'
            f'display:flex;align-items:center;justify-content:center;">{i+1}</div>'
            f'<span style="font-size:11px">'
            f'Route {i+1} — {r.depot.name.split()[-1]} — '
            f'{r.total_distance:.1f} km — {len(r.customers)} stops'
            f'</span></div>'
            for i, r in enumerate(routes)
        )
        m.get_root().add_child(folium.Element(
            f"""<div style='position:fixed;bottom:30px;right:10px;z-index:1000;
                 background:white;padding:10px 14px;border-radius:8px;
                 box-shadow:0 2px 8px rgba(0,0,0,0.2);font-family:sans-serif;
                 max-height:220px;overflow-y:auto'>
              <b style="font-size:12px">🗺️ Generated routes</b><br><br>
              {legend_items}
            </div>"""
        ))

    # Feature groups — routes (jos) → customers → depots (sus)
    fg_routes.add_to(m)
    fg_customers.add_to(m)
    fg_depots.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    plugins.Fullscreen().add_to(m)
    plugins.MeasureControl(position="topleft", primary_length_unit="kilometers").add_to(m)

    return m


def map_to_html(m: folium.Map) -> str:
    return m._repr_html_()