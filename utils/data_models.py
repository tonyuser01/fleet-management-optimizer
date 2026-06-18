"""
Data models, europallet specifications, and sample Bucharest data
for the fleet management application.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict
import math
import re


# ── Europallet specification ──────────────────────────────────────────────────

@dataclass
class Europallet:
    """Standard EUR/EPAL pallet dimensions and weight."""
    length_cm: float = 120.0
    width_cm:  float = 80.0
    height_cm: float = 14.4
    weight_kg: float = 20.0

    @property
    def length_m(self): return self.length_cm / 100
    @property
    def width_m(self):  return self.width_cm  / 100
    @property
    def height_m(self): return self.height_cm / 100
    @property
    def footprint_m2(self): return self.length_m * self.width_m
    @property
    def volume_m3(self): return self.footprint_m2 * self.height_m

EUROPALLET = Europallet()


# ── Core data classes ─────────────────────────────────────────────────────────

@dataclass
class Depot:
    id: int
    name: str
    lat: float
    lon: float
    address: str
    capacity: int = 1000
    num_vehicles: int = 5
    daily_stock_tonnes: float = 0.0
    fleet_allocation: Dict[int, int] = field(default_factory=dict)


@dataclass
class Customer:
    id: int
    name: str
    lat: float
    lon: float
    address: str
    demand_ambient: float = 0.0
    demand_refrigerated: float = 0.0
    needs_refrigeration: bool = False
    time_window_open: int  = 6
    time_window_close: int = 18
    service_time: int = 30

    @property
    def demand(self): return self.demand_ambient + self.demand_refrigerated
    @property
    def demand_kg(self): return self.demand * 1000

    def pallets_needed(self, pallet: Europallet = EUROPALLET,
                       payload_per_pallet_kg: float = 800.0) -> int:
        return math.ceil(self.demand_kg / (payload_per_pallet_kg + pallet.weight_kg))


@dataclass
class VehicleType:
    id: int
    name: str
    capacity_tonnes: float
    fixed_cost: float
    cost_per_km: float
    max_available: int
    is_refrigerated: bool = False
    speed_kmh: float  = 70.0
    cargo_length_m: float = 7.2
    cargo_width_m:  float = 2.4
    cargo_height_m: float = 2.7
    description: str = ""
    tech_specs: Dict[str, str] = field(default_factory=dict)

    @property
    def capacity(self): return self.capacity_tonnes

    def max_pallets_by_floor(self, pallet: Europallet = EUROPALLET) -> int:
        cols = int(self.cargo_width_m  / pallet.width_m)
        rows = int(self.cargo_length_m / pallet.length_m)
        return cols * rows

    def max_pallets_by_weight(self, pallet: Europallet = EUROPALLET,
                               payload_per_pallet_kg: float = 800.0) -> int:
        total_kg = self.capacity_tonnes * 1000
        return int(total_kg / (payload_per_pallet_kg + pallet.weight_kg))

    def max_pallets(self, pallet: Europallet = EUROPALLET,
                    payload_per_pallet_kg: float = 800.0) -> int:
        return min(self.max_pallets_by_floor(pallet),
                   self.max_pallets_by_weight(pallet, payload_per_pallet_kg))


@dataclass
class Route:
    depot: Depot
    vehicle_type: VehicleType
    customers: List[Customer]
    total_distance: float = 0.0
    total_demand: float   = 0.0
    total_cost: float     = 0.0

    def total_pallets(self, pallet: Europallet = EUROPALLET,
                      payload_per_pallet_kg: float = 800.0) -> int:
        kg = self.total_demand * 1000
        return math.ceil(kg / (payload_per_pallet_kg + pallet.weight_kg))

    def pallet_utilization(self, pallet: Europallet = EUROPALLET,
                            payload_per_pallet_kg: float = 800.0) -> float:
        used = self.total_pallets(pallet, payload_per_pallet_kg)
        cap  = self.vehicle_type.max_pallets(pallet, payload_per_pallet_kg)
        return (used / cap * 100) if cap > 0 else 0.0

def clean_name(name: str) -> str:
    """Removes virtual suffixes like (📦 P1) or (❄️ P2)."""
    # Replace (❄️ P1) with (❄️) and (📦 P1) with (📦)
    name = re.sub(r'\((❄️)\s*P\d+\)', r'(\1)', name)
    name = re.sub(r'\((📦)\s*P\d+\)', r'(📦)', name)
    # Remove any other remaining (P1), (P2) suffix
    name = re.sub(r'\s*\([^)]*P\d+\)\s*$', '', name)
    return name.strip()


# ── Sample data: Bucharest distribution network ───────────────────────────────
# All coordinates verified on OpenStreetMap / Google Maps

DEPOTS_BUCHAREST = [
    Depot(0, "D1 — Depot Bucharest North",
          lat=44.4812230000, lon=26.1155450000,
          address="Șoseaua Pipera 42, Voluntari, Ilfov",
          capacity=800, num_vehicles=6, daily_stock_tonnes=85.0,
          fleet_allocation={0: 2, 1: 2, 2: 1, 3: 1}),

    Depot(1, "D2 — Depot Bucharest South",
          lat=44.4068450000, lon=26.1182210000,
          address="Calea Văcărești 391, Sector 4, București",
          capacity=600, num_vehicles=5, daily_stock_tonnes=65.0,
          fleet_allocation={0: 2, 1: 2, 2: 1, 3: 1}),

    Depot(2, "D3 — Depot Chiajna",
          lat=44.4424745543, lon=25.9419712582,
          address="Calea București 1, Chiajna, Ilfov",
          capacity=500, num_vehicles=3, daily_stock_tonnes=50.0,
          fleet_allocation={0: 2, 1: 1, 2: 1, 3: 0}),

]

CUSTOMERS_BUCHAREST = [
    Customer(0,  "Store District 1",
             lat=44.4325410000, lon=26.0984120000,
             address="Calea Victoriei 12, Sector 1",
             demand_ambient=3.5),

    Customer(1,  "Store District 2",
             lat=44.4442120000, lon=26.1264310000,
             address="Bulevardul Ferdinand 80, Sector 2",
             demand_ambient=2.0),

    Customer(2,  "Store District 3",
             lat=44.4308120000, lon=26.1385410000,
             address="Șoseaua Mihai Bravu 220, Sector 3",
             demand_ambient=4.5),

    Customer(3,  "Store District 4",
             lat=44.3781210000, lon=26.1287120000,
             address="Bulevardul Metalurgiei 67, Sector 4",
             demand_ambient=3.0),

    Customer(4,  "Store District 5",
             lat=44.4251210000, lon=26.0842120000,
             address="Calea 13 Septembrie 90, Sector 5",
             demand_ambient=2.5),

    Customer(5,  "Store District 6",
             lat=44.4355410000, lon=25.9772120000,
             address="Bulevardul Iuliu Maniu 541, Sector 6",
             demand_ambient=3.0),

    Customer(6,  "Store Pipera",
             lat=44.4831210000, lon=26.1181210000,
             address="Strada Pipera 46, Voluntari, Ilfov",
             demand_ambient=4.0),

    Customer(7,  "Store Baneasa",
             lat=44.4942120000, lon=26.0805120000,
             address="Șoseaua București-Ploiești 42, Sector 1",
             demand_ambient=2.0),

    Customer(8,  "Store Drumul Taberei",
             lat=44.4215000000, lon=26.0235000000,
             address="Bulevardul Drumul Taberei 44, Sector 6",
             demand_ambient=4.0),

    Customer(9,  "Store Militari",
             lat=44.4352000000, lon=26.0305000000,
             address="Bulevardul Iuliu Maniu 19, Sector 6",
             demand_ambient=3.5),

    Customer(10, "Store Colentina",
             lat=44.4875120000, lon=26.1661210000,
             address="Șoseaua Colentina 426, Sector 2",
             demand_ambient=2.5),

    Customer(11, "Store Pantelimon",
             lat=44.4441210000, lon=26.1662120000,
             address="Șoseaua Pantelimon 302, Sector 2",
             demand_ambient=3.0),

    Customer(12, "Store Titan",
             lat=44.4172120000, lon=26.1731210000,
             address="Bulevardul 1 Decembrie 1918 12, Sector 3",
             demand_ambient=4.0),

    Customer(13, "Store Rahova",
             lat=44.4192120000, lon=26.0845120000,
             address="Calea Rahovei 198, Sector 5",
             demand_ambient=2.0),

    Customer(14, "Store Ferentari",
             lat=44.4011120000, lon=26.0852120000,
             address="Bulevardul Ferentari 62, Sector 5",
             demand_ambient=2.5),

    Customer(15, "Store Giulesti",
             lat=44.4550000000, lon=26.0450000000,
             address="Calea Giulești 125, Sector 6",
             demand_ambient=3.5),

    Customer(16, "Store Floreasca",
             lat=44.4665410000, lon=26.1012120000,
             address="Calea Floreasca 167, Sector 1",
             demand_ambient=3.8, demand_refrigerated=0.7),

    Customer(17, "Store Dorobanti",
             lat=44.4471210000, lon=26.0972120000,
             address="Calea Dorobanților 5, Sector 1",
             demand_ambient=3.0),

    Customer(18, "Store Obor",
             lat=44.4492120000, lon=26.1271210000,
             address="Piața Obor 1, Sector 2",
             demand_ambient=3.5, demand_refrigerated=1.5),

    Customer(19, "Store Berceni",
             lat=44.3721210000, lon=26.1291120000,
             address="Șoseaua Berceni 187, Sector 4",
             demand_ambient=2.5),

]

VEHICLE_FLEET = [
    VehicleType(0, "Small truck (3.5t)",     capacity_tonnes=3.5,  fixed_cost=80,
                cost_per_km=0.25, max_available=6,
                cargo_length_m=4.2, cargo_width_m=2.0, cargo_height_m=2.2,
                description="Ideal for fast urban deliveries and areas with weight restrictions.",
                tech_specs={
                    "Model": "Iveco Daily 35C15",
                    "Configuration": "4x2, Single axle",
                    "Engine": "2.3L Diesel, 150 HP",
                    "GVWR": "3,500 kg",
                    "Net Payload": "~1,200 kg (volumetric 3.5t)",
                    "Transmission": "Manual, 6-speed"
                }),

    VehicleType(1, "Medium truck (7t)",      capacity_tonnes=7.0,  fixed_cost=130,
                cost_per_km=0.35, max_available=5,
                cargo_length_m=6.0, cargo_width_m=2.4, cargo_height_m=2.5,
                description="Optimal balance between capacity and peri-urban maneuverability.",
                tech_specs={
                    "Model": "Mercedes-Benz Atego 818",
                    "Configuration": "4x2, Rigid",
                    "Engine Power": "177 HP",
                    "GVWR": "7,490 kg",
                    "Fuel Source": "Diesel AdBlue Euro VI",
                    "Braking System": "Pneumatic, ABS/ASR"
                }),

    VehicleType(2, "Heavy Duty (Volvo FH)",  capacity_tonnes=24.0, fixed_cost=200,
                cost_per_km=0.45, max_available=3,
                cargo_length_m=13.6, cargo_width_m=2.48, cargo_height_m=2.7,
                description="Tractor-trailer combination for high-capacity transport (FTL).",
                tech_specs={
                    "Tractor": "Volvo FH D13 42 XA (4x2)",
                    "Trailer": "Schmitz Cargobull S.PR BAU",
                    "GVWR (Tractor)": "18,200 kg",
                    "GCWR (Combination)": "44,000 kg",
                    "Net Payload": "24,000 kg",
                    "Pallet Capacity": "34 EUR",
                    "Internal Length": "13,620 mm",
                    "Internal Width": "2,480 mm",
                    "Fifth Wheel Load": "12 t",
                    "Axle Config": "3 axles (trailer)"
                }),

    VehicleType(3, "Refrigerated truck (5t)", capacity_tonnes=5.0, fixed_cost=160,
                cost_per_km=0.50, max_available=2,
                cargo_length_m=5.5, cargo_width_m=2.2, cargo_height_m=2.4, is_refrigerated=True,
                description="Designed for perishable goods requiring temperature control.",
                tech_specs={
                    "Model": "Scania P250 XT",
                    "Cooling Unit": "Thermo King T-1200R",
                    "Temp Range": "-20°C to +20°C",
                    "Insulation": "Reinforced sandwich panels",
                    "Power Unit": "Diesel/Electric standby",
                    "GVWR": "12,000 kg"
                }),
]


# ── Distance utilities ────────────────────────────────────────────────────────

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km (Haversine formula)."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def build_od_matrix(depots: List[Depot], customers: List[Customer]) -> dict:
    """OD distance matrix (km) for all node pairs."""
    nodes = [(d.name, d.lat, d.lon) for d in depots] + \
            [(c.name, c.lat, c.lon) for c in customers]
    matrix = {}
    for i, (ni, lati, loni) in enumerate(nodes):
        for j, (nj, latj, lonj) in enumerate(nodes):
            if i != j:
                matrix[(ni, nj)] = round(haversine(lati, loni, latj, lonj), 2)
    return matrix