"""
MDVRP Algorithms:
  1. Customer-Depot Assignment  — assign each customer to the nearest depot
  2. Nearest Neighbor heuristic — greedy construction
  3. Clarke-Wright Savings      — merge-based construction
  4. 2-opt local search         — route improvement
"""
from typing import List, Dict, Tuple
from utils.data_models import Depot, Customer, Route, VehicleType, haversine


# ── 1. Customer-Depot Assignment ─────────────────────────────────────────────

def assign_customers_to_depots(
    depots: List[Depot],
    customers: List[Customer]
) -> Dict[int, List[Customer]]:
    """
    Assign each customer to the nearest depot using Haversine distance.
    Returns {depot_id: [Customer, ...]}
    """
    assignment: Dict[int, List[Customer]] = {d.id: [] for d in depots}
    for c in customers:
        best = min(depots, key=lambda d: haversine(c.lat, c.lon, d.lat, d.lon))
        assignment[best.id].append(c)
    return assignment


# ── 2. Nearest Neighbor ──────────────────────────────────────────────────────

def nearest_neighbor_routes(
    depot: Depot,
    customers: List[Customer],
    vehicle_capacity: float,
    vehicle_type: VehicleType
) -> List[Route]:
    """
    Nearest Neighbor heuristic for a single depot.
    At each step, select the closest feasible unvisited customer.
    """
    unvisited = customers.copy()
    routes: List[Route] = []

    while unvisited:
        route_customers: List[Customer] = []
        load = 0.0
        cur_lat, cur_lon = depot.lat, depot.lon

        while True:
            feasible = [c for c in unvisited if load + c.demand <= vehicle_capacity]
            if not feasible:
                break
            nearest = min(feasible, key=lambda c: haversine(cur_lat, cur_lon, c.lat, c.lon))
            route_customers.append(nearest)
            load += nearest.demand
            cur_lat, cur_lon = nearest.lat, nearest.lon
            unvisited.remove(nearest)

        if route_customers:
            total_dist = _route_dist(depot, route_customers)
            total_cost = vehicle_type.fixed_cost + total_dist * vehicle_type.cost_per_km
            routes.append(Route(
                depot=depot,
                vehicle_type=vehicle_type,
                customers=route_customers,
                total_distance=round(total_dist, 2),
                total_demand=round(load, 2),
                total_cost=round(total_cost, 2)
            ))

    return routes


# ── 3. Clarke-Wright Savings ─────────────────────────────────────────────────

def clarke_wright_routes(
    depot: Depot,
    customers: List[Customer],
    vehicle_capacity: float,
    vehicle_type: VehicleType
) -> List[Route]:
    """
    Clarke-Wright Savings algorithm for a single depot.

    Savings formula:
        s(i, j) = c(depot, i) + c(depot, j) - c(i, j)

    Merge condition:
        - i is the LAST customer in its route
        - j is the FIRST customer in its route
        - load(r_i) + load(r_j) <= vehicle_capacity
    """
    if not customers:
        return []

    # Step 1 — initialise one route per customer
    route_of: Dict[int, List[Customer]] = {c.id: [c] for c in customers}
    route_list: List[List[Customer]] = [route_of[c.id] for c in customers]

    # Step 2 — compute all savings
    savings: List[Tuple[float, Customer, Customer]] = []
    for i in range(len(customers)):
        for j in range(i + 1, len(customers)):
            ci, cj = customers[i], customers[j]
            s = (haversine(depot.lat, depot.lon, ci.lat, ci.lon)
               + haversine(depot.lat, depot.lon, cj.lat, cj.lon)
               - haversine(ci.lat, ci.lon, cj.lat, cj.lon))
            savings.append((s, ci, cj))

    # Step 3 — sort savings descending
    savings.sort(key=lambda x: -x[0])

    # Step 4 — merge routes
    def get_load(r):
        return sum(c.demand for c in r)

    for s_val, ci, cj in savings:
        ri = route_of.get(ci.id)
        rj = route_of.get(cj.id)
        if ri is None or rj is None or ri is rj:
            continue
        if get_load(ri) + get_load(rj) > vehicle_capacity:
            continue
        if ri[-1] is ci and rj[0] is cj:
            merged = ri + rj
            for c in merged:
                route_of[c.id] = merged
            route_list = [r for r in route_list if r is not ri and r is not rj]
            route_list.append(merged)

    # Build Route objects
    routes: List[Route] = []
    for r in route_list:
        load = get_load(r)
        total_dist = _route_dist(depot, r)
        total_cost = vehicle_type.fixed_cost + total_dist * vehicle_type.cost_per_km
        routes.append(Route(
            depot=depot,
            vehicle_type=vehicle_type,
            customers=r,
            total_distance=round(total_dist, 2),
            total_demand=round(load, 2),
            total_cost=round(total_cost, 2)
        ))

    return routes


# ── 4. 2-opt Local Search ─────────────────────────────────────────────────────

def two_opt_improve(route: Route) -> Route:
    """
    Apply 2-opt local search to reduce total route distance.
    Reverses a segment [i+1 .. j] if it yields a shorter route.
    """
    customers = route.customers.copy()
    improved = True
    while improved:
        improved = False
        for i in range(len(customers) - 1):
            for j in range(i + 2, len(customers)):
                d_before = (haversine(customers[i].lat, customers[i].lon,
                                      customers[i + 1].lat, customers[i + 1].lon) +
                            haversine(customers[j].lat, customers[j].lon,
                                      customers[(j + 1) % len(customers)].lat,
                                      customers[(j + 1) % len(customers)].lon))
                d_after  = (haversine(customers[i].lat, customers[i].lon,
                                      customers[j].lat, customers[j].lon) +
                            haversine(customers[i + 1].lat, customers[i + 1].lon,
                                      customers[(j + 1) % len(customers)].lat,
                                      customers[(j + 1) % len(customers)].lon))
                if d_after < d_before - 1e-6:
                    customers[i + 1:j + 1] = customers[i + 1:j + 1][::-1]
                    improved = True

    new_dist = _route_dist(route.depot, customers)
    new_cost = route.vehicle_type.fixed_cost + new_dist * route.vehicle_type.cost_per_km
    return Route(
        depot=route.depot,
        vehicle_type=route.vehicle_type,
        customers=customers,
        total_distance=round(new_dist, 2),
        total_demand=route.total_demand,
        total_cost=round(new_cost, 2)
    )


# ── Helper ────────────────────────────────────────────────────────────────────

def _route_dist(depot: Depot, customers: List[Customer]) -> float:
    if not customers:
        return 0.0
    pts = ([(depot.lat, depot.lon)]
           + [(c.lat, c.lon) for c in customers]
           + [(depot.lat, depot.lon)])
    return sum(haversine(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
               for i in range(len(pts) - 1))


# ── Full MDVRP Solver ─────────────────────────────────────────────────────────

def solve_mdvrp(
    depots: List[Depot],
    customers: List[Customer],
    vehicle_type: VehicleType,
    algorithm: str = "clarke_wright",
    apply_2opt: bool = True
) -> Tuple[List[Route], Dict[int, List[Customer]]]:
    """
    Solve MDVRP:
      1. Assign customers to nearest depot
      2. Apply chosen construction heuristic per depot
      3. Optionally improve each route with 2-opt

    Returns (all_routes, depot_assignment)
    """
    assignment = assign_customers_to_depots(depots, customers)
    all_routes: List[Route] = []

    for depot in depots:
        depot_customers = assignment[depot.id]
        if not depot_customers:
            continue

        if algorithm == "nearest_neighbor":
            routes = nearest_neighbor_routes(depot, depot_customers, vehicle_type.capacity, vehicle_type)
        else:
            routes = clarke_wright_routes(depot, depot_customers, vehicle_type.capacity, vehicle_type)

        if apply_2opt:
            routes = [two_opt_improve(r) for r in routes]

        all_routes.extend(routes)

    return all_routes, assignment
