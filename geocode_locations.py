"""
Geocoding script — run this locally to get precise GPS coordinates
for all depots and customers in the fleet management application.

Usage:
    pip install requests
    python geocode_locations.py
"""
import requests
import time

locations = [
    # Depozite
    ("D1 — Depot Bucharest North",  "Șoseaua Pipera 42, Voluntari, Ilfov, Romania"),
    ("D2 — Depot Bucharest South",  "Calea Văcărești 391, Sector 4, București, Romania"),
    ("D3 — Depot Ilfov-Otopeni",    "Calea București 1, Otopeni, Ilfov, Romania"),
    # Clienți
    ("Store District 1",            "Calea Victoriei 12, Sector 1, București, Romania"),
    ("Store District 2",            "Bulevardul Ferdinand 80, Sector 2, București, Romania"),
    ("Store District 3",            "Șoseaua Mihai Bravu 220, Sector 3, București, Romania"),
    ("Store District 4",            "Bulevardul Metalurgiei 67, Sector 4, București, Romania"),
    ("Store District 5",            "Calea 13 Septembrie 90, Sector 5, București, Romania"),
    ("Store District 6",            "Bulevardul Iuliu Maniu 541, Sector 6, București, Romania"),
    ("Store Pipera",                "Strada Pipera 46, Voluntari, Ilfov, Romania"),
    ("Store Baneasa",               "Șoseaua București-Ploiești 42, Sector 1, București, Romania"),
    ("Store Drumul Taberei",        "Bulevardul Timișoara 26, Sector 6, București, Romania"),
    ("Store Militari",              "Calea Crângași 10, Sector 6, București, Romania"),
    ("Store Colentina",             "Șoseaua Colentina 426, Sector 2, București, Romania"),
    ("Store Pantelimon",            "Șoseaua Pantelimon 302, Sector 2, București, Romania"),
    ("Store Titan",                 "Bulevardul 1 Decembrie 1918 12, Sector 3, București, Romania"),
    ("Store Rahova",                "Calea Rahovei 198, Sector 5, București, Romania"),
    ("Store Ferentari",             "Bulevardul Ferentari 62, Sector 5, București, Romania"),
    ("Store Giulesti",              "Calea Giulești 285, Sector 6, București, Romania"),
    ("Store Floreasca",             "Calea Floreasca 167, Sector 1, București, Romania"),
    ("Store Dorobanti",             "Bulevardul Dorobanților 5, Sector 1, București, Romania"),
    ("Store Obor",                  "Piața Obor 1, Sector 2, București, Romania"),
    ("Store Berceni",               "Șoseaua Berceni 187, Sector 4, București, Romania"),
]

def geocode(address: str):
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": address, "format": "json", "limit": 1},
            headers={"User-Agent": "FleetManagementApp/1.0"},
            timeout=10
        ).json()
        if resp:
            return float(resp[0]["lat"]), float(resp[0]["lon"]), resp[0].get("display_name", "")
    except Exception as e:
        print(f"  ERROR: {e}")
    return None, None, ""

print("Geocoding all locations...\n")
print(f"{'Name':<28} {'Latitude':>20} {'Longitude':>20}")
print("-" * 75)

results = []
for name, addr in locations:
    lat, lon, display = geocode(addr)
    if lat:
        print(f"{name:<28} {lat:>20.10f} {lon:>20.10f}")
        results.append((name, addr, lat, lon))
    else:
        print(f"{name:<28} {'NOT FOUND':>20}")
    time.sleep(1)  # Nominatim rate limit: 1 request/second

# Generează codul Python gata de copiat în data_models.py
print("\n\n" + "="*75)
print("COPY THIS INTO data_models.py")
print("="*75 + "\n")

depots  = [r for r in results if "Depot" in r[0]]
clients = [r for r in results if "Store" in r[0]]

print("DEPOTS_BUCHAREST = [")
depot_data = [
    (0, "D1 — Depot Bucharest North", "Șoseaua Pipera 42, Voluntari, Ilfov",         800, 6,  85.0, "{0: 2, 1: 2, 2: 1, 3: 1}"),
    (1, "D2 — Depot Bucharest South", "Calea Văcărești 391, Sector 4, București",     600, 5,  65.0, "{0: 2, 1: 2, 2: 1, 3: 1}"),
    (2, "D3 — Depot Ilfov-Otopeni",   "Calea București, Otopeni/Chiajna Area",        500, 3,  50.0, "{0: 2, 1: 1, 2: 1, 3: 0}"),
]
for i, (did, dname, daddr, cap, nveh, stock, alloc) in enumerate(depot_data):
    if i < len(depots):
        _, _, lat, lon = depots[i]
        print(f'    Depot({did}, "{dname}",')
        print(f'          lat={lat:.10f}, lon={lon:.10f},')
        print(f'          address="{daddr}",')
        print(f'          capacity={cap}, num_vehicles={nveh}, daily_stock_tonnes={stock},')
        print(f'          fleet_allocation={alloc}),')
        print()

print("]")
print()
print("CUSTOMERS_BUCHAREST = [")

customer_data = [
    (0,  "Store District 1",     "Calea Victoriei 12, Sector 1",            "demand_ambient=3.5"),
    (1,  "Store District 2",     "Bulevardul Ferdinand 80, Sector 2",        "demand_ambient=2.0"),
    (2,  "Store District 3",     "Șoseaua Mihai Bravu 220, Sector 3",        "demand_ambient=4.5"),
    (3,  "Store District 4",     "Bulevardul Metalurgiei 67, Sector 4",      "demand_ambient=3.0"),
    (4,  "Store District 5",     "Calea 13 Septembrie 90, Sector 5",         "demand_ambient=2.5"),
    (5,  "Store District 6",     "Bulevardul Iuliu Maniu 541, Sector 6",     "demand_ambient=3.0"),
    (6,  "Store Pipera",         "Strada Pipera 46, Voluntari, Ilfov",       "demand_ambient=4.0"),
    (7,  "Store Baneasa",        "Șoseaua București-Ploiești 42, Sector 1",  "demand_ambient=2.0"),
    (8,  "Store Drumul Taberei", "Bulevardul Timișoara 26, Sector 6",        "demand_ambient=4.0"),
    (9,  "Store Militari",       "Calea Crângași 10, Sector 6",              "demand_ambient=3.5"),
    (10, "Store Colentina",      "Șoseaua Colentina 426, Sector 2",          "demand_ambient=2.5"),
    (11, "Store Pantelimon",     "Șoseaua Pantelimon 302, Sector 2",         "demand_ambient=3.0"),
    (12, "Store Titan",          "Bulevardul 1 Decembrie 1918 12, Sector 3", "demand_ambient=4.0"),
    (13, "Store Rahova",         "Calea Rahovei 198, Sector 5",              "demand_ambient=2.0"),
    (14, "Store Ferentari",      "Bulevardul Ferentari 62, Sector 5",        "demand_ambient=2.5"),
    (15, "Store Giulesti",       "Calea Giulești 285, Sector 6",             "demand_ambient=3.5"),
    (16, "Store Floreasca",      "Calea Floreasca 167, Sector 1",            "demand_ambient=3.8, demand_refrigerated=0.7"),
    (17, "Store Dorobanti",      "Bulevardul Dorobanților 5, Sector 1",      "demand_ambient=3.0"),
    (18, "Store Obor",           "Piața Obor 1, Sector 2",                   "demand_ambient=3.5, demand_refrigerated=1.5"),
    (19, "Store Berceni",        "Șoseaua Berceni 187, Sector 4",            "demand_ambient=2.5"),
]

for i, (cid, cname, caddr, demand) in enumerate(customer_data):
    if i < len(clients):
        _, _, lat, lon = clients[i]
        print(f'    Customer({cid},  "{cname}",')
        print(f'             lat={lat:.10f}, lon={lon:.10f},')
        print(f'             address="{caddr}",')
        print(f'             {demand}),')
        print()

print("]")
print("\nDone! Copy the output above into data_models.py")