"""
FSMVRP - Fleet Size and Mix Vehicle Routing Problem

Objective:
    min  Σ_t (f_t * n_t) + Σ_k Σ_(i,j) c_ij * x_ijk

Subject to:
    Σ_t n_t * Q_t >= total_demand      (demand coverage)
    n_t <= N_t_max   for all t          (availability)
    n_t >= 0, integer                   (integrality)
"""
from typing import List, Dict, Tuple, Optional, Any, Union
from itertools import product
from utils.data_models import VehicleType, Route, Depot, Customer, haversine


class FleetSolution:
    def __init__(self, allocation: Dict[int, int], vehicle_types: List[VehicleType],
                 total_demand: float, total_km: float):
        self.allocation = allocation
        self.vehicle_types = vehicle_types
        self.total_demand = total_demand
        self.total_km = total_km

        self.total_vehicles = sum(allocation.values())
        self.total_capacity = sum(
            allocation[vt.id] * vt.capacity
            for vt in vehicle_types if allocation.get(vt.id, 0) > 0
        )
        self.fixed_cost = sum(
            allocation[vt.id] * vt.fixed_cost
            for vt in vehicle_types if allocation.get(vt.id, 0) > 0
        )
        if self.total_vehicles > 0:
            # Calculate weighted average cost per km to apply to the total estimated distance
            avg_c_km = sum(allocation.get(vt.id, 0) * vt.cost_per_km for vt in vehicle_types) / self.total_vehicles
            self.variable_cost = avg_c_km * total_km
        else:
            self.variable_cost = 0
        self.total_cost = self.fixed_cost + self.variable_cost
        self.utilization = (total_demand / self.total_capacity * 100) if self.total_capacity > 0 else 0
        self.cost_per_ton = (self.total_cost / total_demand) if total_demand > 0 else 0

    def to_dict(self) -> list:
        rows = []
        for vt in self.vehicle_types:
            n = self.allocation.get(vt.id, 0)
            if n > 0:
                # Estimate variable cost share based on vehicle count proportion
                v_cost = (self.total_km / self.total_vehicles) * n * vt.cost_per_km
                rows.append({
                    "Vehicle type": vt.name,
                    "Units used": n,
                    "Total capacity (tonnes)": round(n * vt.capacity, 1),
                    "Fixed cost (EUR)": round(n * vt.fixed_cost, 0),
                    "Variable cost (EUR)": round(v_cost, 0),
                    "Total cost per type (EUR)": round(n * vt.fixed_cost + v_cost, 0),
                })
        return rows


def optimize_fleet(
    vehicle_types: List[VehicleType],
    total_demand: float,
    total_km: float,
    objective: str = "min_cost",
    max_vehicles: Optional[int] = None
) -> Tuple[Optional["FleetSolution"], Union[List["FleetSolution"], List[str]]]:
    """
    Enumerate all feasible fleet combinations and return the best solution.

    Objectives:
        'min_cost'     — minimise total cost (fixed + variable)
        'min_vehicles' — minimise number of vehicles used
        'balanced'     — maximise fleet utilisation (~85%), minimise cost
    """
    ranges = [range(0, vt.max_available + 1) for vt in vehicle_types]

    # Safety check for combinatorial explosion (> 50,000 combinations)
    total_combinations = 1
    for r in ranges: total_combinations *= len(r)
    if total_combinations > 50000:
        return None, ["__COMBINATORIAL_EXPLOSION__"]

    feasible: List[FleetSolution] = []

    for combo in product(*ranges):
        total_cap = sum(n * vt.capacity for vt, n in zip(vehicle_types, combo))
        total_veh = sum(combo)
        if total_cap < total_demand or total_veh == 0:
            continue
        if max_vehicles and total_veh > max_vehicles:
            continue

        allocation = {vt.id: n for vt, n in zip(vehicle_types, combo)}
        feasible.append(FleetSolution(allocation, vehicle_types, total_demand, total_km))

    if not feasible:
        return None, []

    feasible.sort(key=lambda s: s.total_cost)

    if objective == "min_cost":
        best = min(feasible, key=lambda s: s.total_cost)
    elif objective == "min_vehicles":
        best = min(feasible, key=lambda s: (s.total_vehicles, s.total_cost))
    else:  # balanced
        best = min(feasible, key=lambda s: abs(s.utilization - 85) * 100 + s.total_cost)

    return best, feasible[:20]


def sensitivity_analysis(
    vehicle_types: List[VehicleType],
    base_demand: float,
    base_km: float,
    demand_range: Tuple[float, float] = (0.5, 1.5),
    steps: int = 11
) -> List[dict]:
    """
    Run fleet optimization across a range of demand multipliers.
    Returns list of result dicts for chart rendering.
    """
    results = []
    low, high = demand_range
    step_size = (high - low) / (steps - 1)

    for i in range(steps):
        mult = low + i * step_size
        demand = base_demand * mult
        best, _ = optimize_fleet(vehicle_types, demand, base_km, objective="min_cost")
        if best:
            results.append({
                "demand_mult": round(mult, 2),
                "demand_t": round(demand, 1),
                "total_cost": round(best.total_cost, 0),
                "total_vehicles": best.total_vehicles,
                "utilization": round(best.utilization, 1),
                "cost_per_ton": round(best.cost_per_ton, 2)
            })

    return results


def get_best_vehicle_for_route(
    demand: float,
    distance: float,
    vehicle_types: List[VehicleType],
    current_usage: Optional[Dict[int, int]] = None,
    needs_refrigeration: bool = False
) -> Tuple[Optional[VehicleType], float]:
    """
    F(Z) from theory: Finds the cheapest vehicle (Fixed + Variable)
    that can transport demand Z over the given distance.
    Respects max_available constraints if current_usage is provided.
    """
    best_v = None
    min_total_cost = float('inf')

    for vt in vehicle_types:
        if vt.capacity >= demand:
            if needs_refrigeration != vt.is_refrigerated:
                continue
            if current_usage is not None:
                used = current_usage.get(vt.id, 0)
                if used >= vt.max_available:
                    continue

            cost = vt.fixed_cost + (distance * vt.cost_per_km)
            if cost < min_total_cost:
                min_total_cost = cost
                best_v = vt

    return best_v, min_total_cost


def _fixed_cost_for_demand(
    demand: float,
    vehicle_types: List[VehicleType],
    needs_refrigeration: bool = False
) -> float:
    """
    F(Z) — fixed cost only of the smallest (cheapest fixed cost) vehicle
    capable of serving demand Z. Used in the Combined Savings formula.

    Per theory: F(Z) = fixed cost of the smallest vehicle type that fits Z.
    We choose the vehicle with minimum fixed_cost among those with capacity >= demand.
    """
    candidates = [
        vt for vt in vehicle_types
        if vt.capacity >= demand and (needs_refrigeration == vt.is_refrigerated)
    ]
    if not candidates:
        # No single vehicle can handle this demand — return infinity to block the merge
        return float('inf')
    return min(vt.fixed_cost for vt in candidates)


def solve_fsmvrp_combined_savings(
    depot: Depot,
    customers: List[Customer],
    vehicle_types: List[VehicleType]
) -> List[Route]:
    """
    Combined Savings (CS) implementation for FSMVRP.

    Formula (Golden et al. / Montoya-Torres):
        CS(i,j) = s_ij + F(Zi) + F(Zj) - F(Zi + Zj)

    where:
        s_ij  = c(d,i) + c(d,j) - c(i,j)   — classical Clarke-Wright distance saving
        F(Z)  = fixed cost of the smallest vehicle capable of serving demand Z
                (_fixed_cost_for_demand)

    This correctly integrates vehicle fixed costs into the savings logic,
    unlike standard CW which only considers distance.

    A merge is accepted only when CS(i,j) > 0, meaning the combined
    distance saving AND fleet-cost saving together justify the operation.
    """
    if not customers:
        return []

    def _route_dist(customers_list: List[Customer]) -> float:
        """Total distance: depot -> c1 -> c2 -> ... -> depot"""
        full = [depot] + customers_list + [depot]
        return sum(
            haversine(full[i].lat, full[i].lon, full[i+1].lat, full[i+1].lon)
            for i in range(len(full) - 1)
        )

    # Track fleet usage: {vehicle_type_id: count}
    fleet_usage: Dict[int, int] = {vt.id: 0 for vt in vehicle_types}

    # ── Step 1: Initialise — one route per customer ───────────────────────────
    current_routes: List[Dict[str, Any]] = []
    for c in customers:
        dist = _route_dist([c])
        vt, cost = get_best_vehicle_for_route(
            c.demand, dist, vehicle_types,
            needs_refrigeration=c.needs_refrigeration
        )
        if vt:
            current_routes.append({
                'customers':           [c],
                'demand':              c.demand,
                'dist':                dist,
                'vt':                  vt,
                'cost':                cost,
                'needs_refrigeration': c.needs_refrigeration,
            })
            fleet_usage[vt.id] += 1

    # ── Step 2: Iterative Combined Savings merging ────────────────────────────
    merged_any = True
    while merged_any:
        merged_any = False
        best_merge = None
        max_cs = 0.0  # Only accept strictly positive CS values

        for i in range(len(current_routes)):
            for j in range(len(current_routes)):
                if i == j:
                    continue

                ri = current_routes[i]
                rj = current_routes[j]

                # Avoid merging routes with different refrigeration requirements
                if ri['needs_refrigeration'] != rj['needs_refrigeration']:
                    continue

                combined_customers    = ri['customers'] + rj['customers']
                combined_demand       = ri['demand'] + rj['demand']
                combined_needs_ref    = ri['needs_refrigeration'] or rj['needs_refrigeration']

                # ── Clarke-Wright distance saving: s_ij = c(d,i) + c(d,j) - c(i,j) ──
                # c(d, i) = distance from depot to last customer of route i
                # c(d, j) = distance from depot to first customer of route j
                # c(i, j) = direct link cost between last of i and first of j
                last_i  = ri['customers'][-1]
                first_j = rj['customers'][0]

                c_d_i = haversine(depot.lat, depot.lon, last_i.lat,  last_i.lon)
                c_d_j = haversine(depot.lat, depot.lon, first_j.lat, first_j.lon)
                c_i_j = haversine(last_i.lat, last_i.lon, first_j.lat, first_j.lon)

                s_ij = c_d_i + c_d_j - c_i_j

                # ── F(Zi), F(Zj), F(Zi+Zj) — fixed cost savings ──────────────
                F_zi    = _fixed_cost_for_demand(ri['demand'],       vehicle_types, ri['needs_refrigeration'])
                F_zj    = _fixed_cost_for_demand(rj['demand'],       vehicle_types, rj['needs_refrigeration'])
                F_zizj  = _fixed_cost_for_demand(combined_demand,    vehicle_types, combined_needs_ref)

                if F_zizj == float('inf'):
                    # No single vehicle can handle combined demand — skip
                    continue

                # ── Combined Savings formula ──────────────────────────────────
                # CS(i,j) = s_ij + F(Zi) + F(Zj) - F(Zi+Zj)
                cs_value = s_ij + F_zi + F_zj - F_zizj

                if cs_value <= max_cs:
                    continue

                # ── Find the best vehicle for the merged route ────────────────
                combined_dist = _route_dist(combined_customers)
                best_vt_merged, cost_merged = get_best_vehicle_for_route(
                    combined_demand, combined_dist, vehicle_types,
                    needs_refrigeration=combined_needs_ref
                )
                if not best_vt_merged:
                    continue

                # ── Finite fleet feasibility check ────────────────────────────
                # Merging releases vt_i and vt_j, acquires vt_merged
                test_usage = fleet_usage.copy()
                test_usage[ri['vt'].id] -= 1
                test_usage[rj['vt'].id] -= 1
                test_usage[best_vt_merged.id] += 1

                if any(
                    test_usage[tid] > next(v for v in vehicle_types if v.id == tid).max_available
                    for tid in test_usage
                ):
                    continue

                max_cs = cs_value
                best_merge = (
                    i, j,
                    combined_customers, combined_demand, combined_dist,
                    best_vt_merged, cost_merged,
                    test_usage, combined_needs_ref
                )

        if best_merge:
            idx_i, idx_j, new_cust, new_dem, new_dist, new_vt, new_cost, new_usage, new_ref = best_merge
            first  = min(idx_i, idx_j)
            second = max(idx_i, idx_j)
            current_routes.pop(second)
            current_routes.pop(first)
            current_routes.append({
                'customers':           new_cust,
                'demand':              new_dem,
                'dist':                new_dist,
                'vt':                  new_vt,
                'cost':                new_cost,
                'needs_refrigeration': new_ref,
            })
            merged_any = True
            fleet_usage = new_usage

    # ── Step 3: Build Route objects ───────────────────────────────────────────
    return [
        Route(
            depot=depot,
            vehicle_type=r['vt'],
            customers=r['customers'],
            total_distance=round(r['dist'], 2),
            total_demand=round(r['demand'], 2),
            total_cost=round(r['cost'], 2)
        )
        for r in current_routes
    ]


def solve_fsmvrp_multi_depot(
    depots: List[Depot],
    customers: List[Customer],
    vehicle_types: List[VehicleType]
) -> List[Route]:
    """
    Multi-depot wrapper for FSMVRP Combined Savings.

    Steps:
        1. Assign each customer to the nearest depot (Haversine) —
           same Customer-Depot Assignment strategy as MDVRP.
        2. Run solve_fsmvrp_combined_savings independently per depot.
        3. Aggregate and return all routes.

    This ensures the FSMVRP page correctly uses all depots in the
    network, not just a single one.
    """
    if not depots or not customers:
        return []

    # ── Step 1: Customer-Depot Assignment (nearest depot) ────────────────────
    assignment: Dict[int, List[Customer]] = {d.id: [] for d in depots}
    for c in customers:
        nearest = min(depots, key=lambda d: haversine(c.lat, c.lon, d.lat, d.lon))
        assignment[nearest.id].append(c)

    # ── Step 2: Run CS per depot and aggregate ────────────────────────────────
    all_routes: List[Route] = []
    for depot in depots:
        depot_customers = assignment[depot.id]
        if not depot_customers:
            continue
        routes = solve_fsmvrp_combined_savings(depot, depot_customers, vehicle_types)
        all_routes.extend(routes)

    return all_routes