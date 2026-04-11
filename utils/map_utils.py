"""
Map visualization utilities using Folium (OpenStreetMap).
Renders depots, customers, and optimized routes on an interactive map.
"""
import folium
from folium import plugins
from typing import List, Optional
from utils.data_models import Depot, Customer, Route

DEPOT_COLORS  = ["darkblue", "darkred", "darkgreen", "purple", "orange"]
ROUTE_COLORS  = [
    "#E94560", "#3B8BD4", "#1D9E75", "#BA7517", "#9c42c9",
    "#D4537E", "#185FA5", "#0F6E56", "#634802", "#6b2fa0",
]


def build_map(
    depots: List[Depot],
    customers: List[Customer],
    routes: Optional[List[Route]] = None,
    zoom: int = 11
) -> folium.Map:
    """
    Build a Folium map with:
      - Depot markers with influence radius
      - Customer circle markers colored by assigned depot
      - Animated route polylines (AntPath)
      - Toggleable layer control
      - Fullscreen and measure tools
    """
    all_lats = [d.lat for d in depots] + [c.lat for c in customers]
    all_lons = [d.lon for d in depots] + [c.lon for c in customers]
    center = (sum(all_lats) / len(all_lats), sum(all_lons) / len(all_lons))

    m = folium.Map(location=center, zoom_start=zoom,
                   tiles="OpenStreetMap", control_scale=True)

    folium.TileLayer("CartoDB positron",     name="CartoDB Light").add_to(m)
    folium.TileLayer("CartoDB dark_matter",  name="CartoDB Dark").add_to(m)

    fg_depots    = folium.FeatureGroup(name="🏭 Depots",    show=True)
    fg_customers = folium.FeatureGroup(name="📦 Customers", show=True)
    fg_routes    = folium.FeatureGroup(name="🛣️ Routes",   show=True)

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
                    <b>{c.name}</b><br>
                    <hr style='margin:4px 0'>
                    📦 Demand: <b>{c.demand} t</b><br>
                    🕐 Time window: {c.time_window_open}:00 – {c.time_window_close}:00<br>
                    ⏱️ Service time: {c.service_time} min
                </div>""",
                max_width=200
            ),
            tooltip=f"📦 {c.name} ({c.demand}t)"
        ).add_to(fg_customers)

    # ── Route polylines ───────────────────────────────────────────────────────
    if routes:
        for i, route in enumerate(routes):
            if not route.customers:
                continue
            color = ROUTE_COLORS[i % len(ROUTE_COLORS)]
            coords = ([[route.depot.lat, route.depot.lon]]
                      + [[c.lat, c.lon] for c in route.customers]
                      + [[route.depot.lat, route.depot.lon]])

            folium.PolyLine(
                locations=coords, color=color, weight=3, opacity=0.8,
                tooltip=(f"Route {i+1} — {route.depot.name} | "
                         f"{len(route.customers)} customers | "
                         f"{route.total_distance:.1f} km | {route.total_demand:.1f}t"),
                popup=folium.Popup(
                    f"""<div style='font-family:sans-serif;min-width:200px'>
                        <b style='color:{color}'>Route {i+1}</b><br>
                        <hr style='margin:4px 0'>
                        🏭 Depot: {route.depot.name}<br>
                        🚛 Vehicle: {route.vehicle_type.name}<br>
                        📦 Total demand: {route.total_demand} t<br>
                        📏 Distance: {route.total_distance} km<br>
                        💰 Estimated cost: {route.total_cost:.0f} €<br>
                        <b>Sequence:</b><br>
                        {'<br>'.join(f'  {j+1}. {c.name}' for j, c in enumerate(route.customers))}
                    </div>""",
                    max_width=240
                )
            ).add_to(fg_routes)

            plugins.AntPath(
                locations=coords, color=color,
                weight=2, opacity=0.5,
                delay=1200, dash_array=[10, 20],
                pulse_color="#fff"
            ).add_to(fg_routes)

        # Legend
        legend_items = "".join(
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">'
            f'<div style="width:24px;height:4px;background:{ROUTE_COLORS[i % len(ROUTE_COLORS)]};border-radius:2px"></div>'
            f'<span style="font-size:11px">Route {i+1} ({r.depot.name.split()[-1]}) — {r.total_distance:.1f} km</span></div>'
            for i, r in enumerate(routes)
        )
        m.get_root().html.add_child(folium.Element(
            f"""<div style='position:fixed;bottom:30px;right:10px;z-index:1000;
                 background:white;padding:10px 14px;border-radius:8px;
                 box-shadow:0 2px 8px rgba(0,0,0,0.2);font-family:sans-serif;
                 max-height:200px;overflow-y:auto'>
              <b style="font-size:12px">🗺️ Generated routes</b><br><br>
              {legend_items}
            </div>"""
        ))

    fg_depots.add_to(m)
    fg_customers.add_to(m)
    fg_routes.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    plugins.Fullscreen().add_to(m)
    plugins.MeasureControl(position="topleft", primary_length_unit="kilometers").add_to(m)

    return m


def map_to_html(m: folium.Map) -> str:
    return m._repr_html_()
