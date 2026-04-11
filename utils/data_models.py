"""
Data models and sample Bucharest coordinates for the fleet management app.
"""
from dataclasses import dataclass, field
from typing import List
import math


@dataclass
class Depot:
    id: int
    name: str
    lat: float
    lon: float
    capacity: int = 1000
    num_vehicles: int = 5


@dataclass
class Customer:
    id: int
    name: str
    lat: float
    lon: float
    demand: float              # tonnes
    time_window_open: int = 6  # hour
    time_window_close: int = 18
    service_time: int = 30     # minutes


@dataclass
class VehicleType:
    id: int
    name: str
    capacity: float            # tonnes
    fixed_cost: float          # EUR/day
    cost_per_km: float         # EUR/km
    max_available: int
    speed_kmh: float = 70.0


@dataclass
class Route:
    depot: Depot
    vehicle_type: VehicleType
    customers: List[Customer]
    total_distance: float = 0.0
    total_demand: float = 0.0
    total_cost: float = 0.0


# ── Sample data: Bucharest distribution network ──────────────────────────────

ROMANIAN_DEPOTS = [
    Depot(0, "Depot Bucharest North", 44.5500, 26.0800, capacity=800, num_vehicles=6),
    Depot(1, "Depot Bucharest South", 44.3200, 26.1200, capacity=600, num_vehicles=5),
    Depot(2, "Depot Ilfov-Otopeni",   44.5800, 26.0500, capacity=500, num_vehicles=4),
]

ROMANIAN_CUSTOMERS = [
    Customer(0,  "Store District 1",       44.4600, 26.0700,  3.5),
    Customer(1,  "Store District 2",       44.4500, 26.1400,  2.0),
    Customer(2,  "Store District 3",       44.4300, 26.1600,  4.5),
    Customer(3,  "Store District 4",       44.4100, 26.1100,  3.0),
    Customer(4,  "Store District 5",       44.3900, 26.0700,  2.5),
    Customer(5,  "Store District 6",       44.4400, 26.0300,  3.0),
    Customer(6,  "Store Pipera",           44.5000, 26.1000,  5.0),
    Customer(7,  "Store Baneasa",          44.5200, 26.0800,  2.0),
    Customer(8,  "Store Drumul Taberei",   44.4200, 25.9900,  4.0),
    Customer(9,  "Store Militari",         44.4300, 25.9600,  3.5),
    Customer(10, "Store Colentina",        44.4700, 26.1700,  2.5),
    Customer(11, "Store Pantelimon",       44.4300, 26.2100,  3.0),
    Customer(12, "Store Titan",            44.4200, 26.1800,  4.0),
    Customer(13, "Store Rahova",           44.3900, 26.0600,  2.0),
    Customer(14, "Store Ferentari",        44.3800, 26.0900,  2.5),
    Customer(15, "Store Giulesti",         44.4600, 25.9900,  3.5),
    Customer(16, "Store Floreasca",        44.4800, 26.1000,  4.5),
    Customer(17, "Store Dorobanti",        44.4700, 26.0900,  3.0),
    Customer(18, "Store Obor",             44.4500, 26.1200,  5.0),
    Customer(19, "Store Berceni",          44.3700, 26.1200,  2.5),
]

VEHICLE_FLEET = [
    VehicleType(0, "Small truck (3.5t)",        capacity=3.5,  fixed_cost=80,  cost_per_km=0.25, max_available=6),
    VehicleType(1, "Medium truck (7t)",          capacity=7.0,  fixed_cost=130, cost_per_km=0.35, max_available=5),
    VehicleType(2, "Large truck (14t)",          capacity=14.0, fixed_cost=200, cost_per_km=0.45, max_available=3),
    VehicleType(3, "Refrigerated truck (5t)",    capacity=5.0,  fixed_cost=160, cost_per_km=0.50, max_available=2),
]


# ── Distance utilities ────────────────────────────────────────────────────────

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in km between two lat/lon points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))
