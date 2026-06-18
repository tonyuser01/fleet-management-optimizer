"""
MDVRP Algorithms:
  1. Customer-Depot Assignment  — assign each customer to the nearest depot
  2. Nearest Neighbor heuristic — greedy construction
  3. Clarke-Wright Savings      — merge-based construction
  4. 2-opt local search         — route improvement
"""
from typing import List, Dict, Tuple, Any, Union
from datetime import datetime, timedelta
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
    vehicle_type: VehicleType,
    max_distance: float = float('inf'),
    start_hour: int = 8,
    speed_kmh: float = 40.0,
    shift_end_hour: int = 22
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
            feasible = [
                c for c in unvisited 
                if load + c.demand <= vehicle_capacity and (c.needs_refrigeration == vehicle_type.is_refrigerated)
            ]
            if not feasible:
                break

            nearest = min(feasible, key=lambda c: haversine(cur_lat, cur_lon, c.lat, c.lon))

            # Check total distance constraint (C4) before accepting the customer
            if _route_dist(depot, route_customers + [nearest]) > max_distance:
                break
            
            # Check time windows (VRPTW)
            if not _is_time_feasible(depot, route_customers + [nearest], speed_kmh, start_hour, shift_end_hour):
                break
                
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
    vehicle_type: VehicleType,
    max_distance: float = float('inf'),
    start_hour: int = 8,
    speed_kmh: float = 40.0,
    shift_end_hour: int = 22
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
    # Skip customers that require refrigeration if the vehicle is not refrigerated
    route_of: Dict[int, List[Customer]] = {
        c.id: [c] for c in customers if c.needs_refrigeration == vehicle_type.is_refrigerated
    }
    # Track current load of each route object to avoid re-summing
    route_loads: Dict[int, float] = {id(r): sum(c.demand for c in r) for r in route_of.values()}

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

    # Step 4 — merge routes iteratively
    for s_val, ci, cj in savings:
        ri = route_of.get(ci.id)
        rj = route_of.get(cj.id)
        if ri is None or rj is None or ri is rj:
            continue
            
        # Capacity check (C3) using cached loads
        if route_loads[id(ri)] + route_loads[id(rj)] > vehicle_capacity:
            continue
            
        if ri[-1] is ci and rj[0] is cj:
            merged = ri + rj
            # Distance check (C4)
            if _route_dist(depot, merged) > max_distance:
                continue
            
            # Time Window check (VRPTW)
            if not _is_time_feasible(depot, merged, speed_kmh, start_hour, shift_end_hour):
                continue
                
            # Update load cache and references
            new_load = route_loads[id(ri)] + route_loads[id(rj)]
            route_loads[id(merged)] = new_load
            
            for c in merged:
                route_of[c.id] = merged

    # Build unique Route objects from the mapping
    routes: List[Route] = []
    seen_route_ids = set()
    for c_id in route_of:
        r = route_of[c_id]
        if id(r) in seen_route_ids: continue
        seen_route_ids.add(id(r))
        
        load = route_loads[id(r)]
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
    Rigorous 2-opt implementation for VRP routes.
    Includes the depot in the swap calculation to optimize Start/End links.
    """
    depot = route.depot
    customers = route.customers.copy()
    n = len(customers)
    if n < 2:
        return route

    improved = True
    while improved:
        improved = False
        
        # Construct the complete sequence: Depot -> C1 -> C2 -> ... -> Cn -> Depot
        nodes = [depot] + customers + [depot]
        
        # Iterate over all pairs of arcs (i, i+1) and (j, j+1)
        for i in range(n):
            for j in range(i + 2, n + 1):
                # Arc 1: (nodes[i], nodes[i+1])
                # Arc 2: (nodes[j], nodes[j+1])
                
                d_curr = haversine(nodes[i].lat, nodes[i].lon, nodes[i+1].lat, nodes[i+1].lon) + \
                         haversine(nodes[j].lat, nodes[j].lon, nodes[j+1].lat, nodes[j+1].lon)
                         
                d_new  = haversine(nodes[i].lat, nodes[i].lon, nodes[j].lat, nodes[j].lon) + \
                         haversine(nodes[i+1].lat, nodes[i+1].lon, nodes[j+1].lat, nodes[j+1].lon)
                
                if d_new < d_curr - 1e-6:
                    # Reverse the customer segment between the two arcs
                    customers[i:j] = customers[i:j][::-1]
                    improved = True
                    nodes = [depot] + customers + [depot]

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

def get_transport_stats(routes: List[Route]) -> Dict[str, float]:
    """
    Calculates theoretical transport metrics per scenario.
    - Traffic Flow (Ftrafic) [km/day]
    - Transport Flow (Ftransport) [veh-inc*km/day]
    - Empty Run Percentage (Pgol) [%]
    - Daily Performance (Pperformance) [tonne*km/day]
    """
    traffic_flow = 0.0
    return_dist = 0.0
    performance = 0.0
    
    for r in routes:
        traffic_flow += r.total_distance
        
        # Segment performance calculation: sum(load_on_segment * segment_distance)
        curr_lat, curr_lon = r.depot.lat, r.depot.lon
        current_load = r.total_demand
        
        if r.customers:
            for c in r.customers:
                dist = haversine(curr_lat, curr_lon, c.lat, c.lon)
                performance += current_load * dist
                current_load -= c.demand
                curr_lat, curr_lon = c.lat, c.lon
            
            # Return trip (always empty in this model)
            d_prime = haversine(curr_lat, curr_lon, r.depot.lat, r.depot.lon)
            return_dist += d_prime
            
    transport_flow = traffic_flow - return_dist
    empty_pct = (return_dist / traffic_flow * 100) if traffic_flow > 0 else 0
    
    return {
        "traffic_flow": traffic_flow,
        "transport_flow": transport_flow,
        "empty_pct": empty_pct,
        "performance": performance
    }

def _is_time_feasible(depot: Depot, customers: List[Customer], speed_kmh: float, start_hour: int, shift_end_hour: int = 22) -> bool:
    """
    Checks if a customer sequence is feasible regarding time windows.
    Includes driving time and service time.
    """
    current_time = start_hour * 60.0  # in minutes from midnight
    cur_lat, cur_lon = depot.lat, depot.lon
    
    for c in customers:
        dist = haversine(cur_lat, cur_lon, c.lat, c.lon)
        travel_time = (dist / speed_kmh) * 60.0
        arrival_time = current_time + travel_time
        
        # Check if we exceeded the closing time (converted to minutes)
        if arrival_time > c.time_window_close * 60:
            return False
        
        # If we arrive before opening, we wait
        current_time = max(arrival_time, c.time_window_open * 60.0)
        
        # Add unloading time (service time)
        current_time += c.service_time
        cur_lat, cur_lon = c.lat, c.lon
        
    # Returning to depot
    dist_back = haversine(cur_lat, cur_lon, depot.lat, depot.lon)
    arrival_depot = current_time + (dist_back / speed_kmh) * 60.0

    # Check if return to depot is before the global shift end
    return arrival_depot <= shift_end_hour * 60 


def _route_dist(depot: Depot, customers: List[Customer]) -> float:
    if not customers:
        return 0.0
    pts = ([(depot.lat, depot.lon)]
           + [(c.lat, c.lon) for c in customers]
           + [(depot.lat, depot.lon)])
    return sum(haversine(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
               for i in range(len(pts) - 1))


# ── Full MDVRP Solver ─────────────────────────────────────────────────────────

def _preprocess_split_deliveries(customers: List[Customer], vehicle_capacity: float) -> List[Customer]:
    """
    Helper to handle Split Delivery VRP (SDVRP).
    Handles Mixed Demands: Splits orders into Refrigerated and Ambient tasks.
    Then splits tasks into multiple virtual customers if they exceed vehicle capacity.
    """
    processed_customers = []
    for c in customers:
        # Sub-function to split a specific demand type
        def split_task(amt: float, is_ref: bool, suffix: str):
            if amt <= 0: return
            remaining = amt
            part = 1
            while remaining > 0:
                take = min(remaining, vehicle_capacity)
                processed_customers.append(Customer(
                    id=c.id * 1000 + (100 if is_ref else 200) + part,
                    name=f"{c.name} ({suffix} P{part})",
                    lat=c.lat, lon=c.lon, address=c.address,
                    demand_ambient=0.0 if is_ref else take,
                    demand_refrigerated=take if is_ref else 0.0,
                    needs_refrigeration=is_ref,
                    time_window_open=c.time_window_open,
                    time_window_close=c.time_window_close,
                    service_time=c.service_time // 2 if part > 1 else c.service_time
                ))
                remaining -= take
                part += 1

        # Handle both components of the order
        split_task(c.demand_refrigerated, True, "❄️")
        split_task(c.demand_ambient, False, "📦")

    return processed_customers

def validate_refrigeration_assignment(routes: List[Route]) -> List[str]:
    """
    Post-solve validation: checks that no customer requiring refrigeration
    has been assigned to a non-refrigerated vehicle.

    Returns a list of warning strings (empty if no violations found).
    This can happen if the CS merging logic incorrectly absorbs a
    refrigerated task into a non-refrigerated route.
    """
    warnings = []
    for i, route in enumerate(routes):
        if not route.vehicle_type.is_refrigerated:
            for c in route.customers:
                if c.needs_refrigeration:
                    warnings.append(
                        f"Route {i+1} ({route.depot.name}): customer "
                        f"'{c.name}' requires refrigeration but is assigned "
                        f"to '{route.vehicle_type.name}' (non-refrigerated)."
                    )
    return warnings


def solve_mdvrp(
    depots: List[Depot],
    customers: List[Customer],
    vehicle_type: Union[VehicleType, List[VehicleType]],
    algorithm: str = "clarke_wright",
    apply_2opt: bool = True,
    max_distance: float = float('inf'),
    load_balance: bool = False,
    start_hour: int = 8,
    speed_kmh: float = 40.0,
    shift_end_hour: int = 22
) -> Tuple[List[Route], Dict[int, List[Customer]], List[str]]:
    """
    Solve MDVRP:
      1. Assign customers to nearest depot
      2. Apply chosen construction heuristic per depot
      3. Re-assign customers if a depot is overloaded (load balancing)
      4. Optionally improve each route with 2-opt

    Returns (all_routes, depot_assignment)
    """
    # Determine capacity for splitting logic
    if isinstance(vehicle_type, list):
        max_cap = max(vt.capacity for vt in vehicle_type)
    else:
        max_cap = vehicle_type.capacity

    # 0. Split Deliveries Logic (SDVRP)
    processed_customers = _preprocess_split_deliveries(customers, max_cap)
    
    assignment = assign_customers_to_depots(depots, processed_customers)

    def solve_for_depot(d, custs):
        if not custs:
            return []

        if isinstance(vehicle_type, list):
            # Filter available vehicles at this depot based on fleet_allocation
            if d.fleet_allocation:
                depot_vts = [
                    vt for vt in vehicle_type
                    if d.fleet_allocation.get(vt.id, 0) > 0
                ]
                # If the depot has no allocated vehicles, use the entire fleet
                if not depot_vts:
                    depot_vts = vehicle_type
            else:
                depot_vts = vehicle_type

            from utils.fsmvrp_optimizer import solve_fsmvrp_combined_savings
            return solve_fsmvrp_combined_savings(d, custs, depot_vts)

        # Single vehicle — check if it's available at this depot
        if d.fleet_allocation and d.fleet_allocation.get(vehicle_type.id, 0) == 0:
            # The selected vehicle is not at this depot
            # Fallback: use the cheapest available vehicle at the depot
            available_vts = [
                vt for vt in (vehicle_type if isinstance(vehicle_type, list) else [vehicle_type])
                if d.fleet_allocation.get(vt.id, 0) > 0
            ]
            if not available_vts:
                # No vehicle at the depot — return empty, will be handled by the load balancer
                return []
            active_vt = available_vts[0]
        else:
            active_vt = vehicle_type

        if algorithm == "nearest_neighbor":
            routes = nearest_neighbor_routes(d, custs, active_vt.capacity, active_vt, max_distance, start_hour, speed_kmh, shift_end_hour)
        else:
            routes = clarke_wright_routes(d, custs, active_vt.capacity, active_vt, max_distance, start_hour, speed_kmh, shift_end_hour)

        if apply_2opt:
            routes = [two_opt_improve(r) for r in routes]
        return routes

    # Initial solve
    depot_routes = {d.id: solve_for_depot(d, assignment[d.id]) for d in depots}

    if load_balance:
        # Iteratively move customers from overloaded depots to underloaded ones
        for _ in range(15): # Max iterations to prevent infinite loops
            overloaded  = [d for d in depots if len(depot_routes[d.id]) > (sum(d.fleet_allocation.values()) if d.fleet_allocation else d.num_vehicles)]
            underloaded = [d for d in depots if len(depot_routes[d.id]) < (sum(d.fleet_allocation.values()) if d.fleet_allocation else d.num_vehicles)]
            
            if not overloaded or not underloaded:
                break
                
            best_move = None
            min_regret = float('inf')

            for d_from in overloaded:
                for c in assignment[d_from.id]:
                    d_from_dist = haversine(c.lat, c.lon, d_from.lat, d_from.lon)
                    for d_to in underloaded:
                        d_to_dist = haversine(c.lat, c.lon, d_to.lat, d_to.lon)
                        regret = d_to_dist - d_from_dist
                        
                        if regret < min_regret:
                            min_regret = regret
                            best_move = (c, d_from, d_to)
            
            if best_move:
                c, d_from, d_to = best_move
                assignment[d_from.id].remove(c)
                assignment[d_to.id].append(c)
                
                # Update routes for affected depots
                depot_routes[d_from.id] = solve_for_depot(d_from, assignment[d_from.id])
                depot_routes[d_to.id] = solve_for_depot(d_to, assignment[d_to.id])
            else:
                break

    all_routes: List[Route] = []
    for d_id in depot_routes:
        all_routes.extend(depot_routes[d_id])

    refrigeration_warnings = validate_refrigeration_assignment(all_routes)

    return all_routes, assignment, refrigeration_warnings
