"""
FSMVRP — Fleet Size and Mix Vehicle Routing Problem

Objective:
    min  Σ_t (f_t * n_t) + Σ_k Σ_(i,j) c_ij * x_ijk

Subject to:
    Σ_t n_t * Q_t >= total_demand      (demand coverage)
    n_t <= N_t_max   for all t          (availability)
    n_t >= 0, integer                   (integrality)
"""
from typing import List, Dict, Tuple, Optional, Any
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
        self.variable_cost = sum(
            allocation[vt.id] * vt.cost_per_km * total_km
            for vt in vehicle_types if allocation.get(vt.id, 0) > 0
        )
        self.total_cost = self.fixed_cost + self.variable_cost
        self.utilization = (total_demand / self.total_capacity * 100) if self.total_capacity > 0 else 0
        self.cost_per_ton = (self.total_cost / total_demand) if total_demand > 0 else 0

    def to_dict(self) -> list:
        rows = []
        for vt in self.vehicle_types:
            n = self.allocation.get(vt.id, 0)
            if n > 0:
                rows.append({
                    "Vehicle type": vt.name,
                    "Units used": n,
                    "Total capacity (t)": round(n * vt.capacity, 1),
                    "Fixed cost (€)": round(n * vt.fixed_cost, 0),
                    "Variable cost (€)": round(n * vt.cost_per_km * self.total_km, 0),
                    "Total cost per type (€)": round(
                        n * vt.fixed_cost + n * vt.cost_per_km * self.total_km, 0
                    ),
                })
        return rows


def optimize_fleet(
    vehicle_types: List[VehicleType],
    total_demand: float,
    total_km: float,
    objective: str = "min_cost",
    max_vehicles: Optional[int] = None
) -> Tuple[Optional["FleetSolution"], List["FleetSolution"]]:
    """
    Enumerate all feasible fleet combinations and return the best solution.

    Objectives:
        'min_cost'     — minimise total cost (fixed + variable)
        'min_vehicles' — minimise number of vehicles used
        'balanced'     — maximise fleet utilisation (~85%), minimise cost
    """
    ranges = [range(0, vt.max_available + 1) for vt in vehicle_types]
    
    # Safety check for combinatorial explosion
    total_combinations = 1
    for r in ranges: total_combinations *= len(r)
    if total_combinations > 50000:
        return None, [] # Or handle more gracefully for large fleets

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
    Now respects max_available constraints if current_usage is provided.
    """
    best_v = None
    min_total_cost = float('inf')
    
    for vt in vehicle_types:
        if vt.capacity >= demand:
            # Check refrigeration compatibility
            if needs_refrigeration and not vt.is_refrigerated:
                continue
            # Check if we have this vehicle available
            if current_usage is not None:
                used = current_usage.get(vt.id, 0)
                if used >= vt.max_available:
                    continue

            cost = vt.fixed_cost + (distance * vt.cost_per_km)
            if cost < min_total_cost:
                min_total_cost = cost
                best_v = vt
                
    return best_v, min_total_cost


def solve_fsmvrp_combined_savings(
    depot: Depot,
    customers: List[Customer],
    vehicle_types: List[VehicleType]
) -> List[Route]:
    """
    Combined Savings (CS) implementation for FSMVRP.
    S_ij = s_ij + F(Zi) + F(Zj) - F(Zi + Zj)
    """
    if not customers:
        return []

    def _get_dist(pts_list):
        d = 0.0
        full_path = [depot] + pts_list + [depot]
        for i in range(len(full_path)-1):
            d += haversine(full_path[i].lat, full_path[i].lon, 
                           full_path[i+1].lat, full_path[i+1].lon)
        return d

    # Track fleet usage: {vehicle_type_id: count}
    fleet_usage: Dict[int, int] = {vt.id: 0 for vt in vehicle_types}

    # 1. Initialization: Every customer has their own route
    current_routes: List[Dict[str, Any]] = []
    for c in customers:
        dist = _get_dist([c])
        # During init, we try to assign but we don't strictly block yet 
        # because we might not have enough vehicles for 1-to-1 routes.
        vt, cost = get_best_vehicle_for_route(
            c.demand, dist, vehicle_types, 
            needs_refrigeration=c.needs_refrigeration
        )
        if vt:
            current_routes.append({
                'customers': [c],
                'demand': c.demand,
                'dist': dist,
                'vt': vt,
                'cost': cost,
                'needs_refrigeration': c.needs_refrigeration
            })
            fleet_usage[vt.id] += 1

    # 2. Calculate Combined Savings (CS)
    # Using a simplified iterative approach for CS
    merged_any = True
    while merged_any:
        merged_any = False
        best_merge = None
        max_cs = -float('inf')

        for i in range(len(current_routes)):
            for j in range(len(current_routes)):
                if i == j: continue
                
                ri = current_routes[i]
                rj = current_routes[j]
                
                combined_customers = ri['customers'] + rj['customers']
                combined_demand = ri['demand'] + rj['demand']
                combined_dist = _get_dist(combined_customers)
                combined_needs_ref = ri['needs_refrigeration'] or rj['needs_refrigeration']
                
                # F(Zi + Zj)
                best_vt_merged, cost_merged = get_best_vehicle_for_route(
                    combined_demand, combined_dist, vehicle_types,
                    needs_refrigeration=combined_needs_ref
                )
                
                if not best_vt_merged: continue
                
                # --- Finite Fleet Constraint Check ---
                # If we merge, we release vt_i and vt_j, and acquire vt_merged
                test_usage = fleet_usage.copy()
                test_usage[ri['vt'].id] -= 1
                test_usage[rj['vt'].id] -= 1
                test_usage[best_vt_merged.id] += 1
                
                # Check if this merge is feasible with the available fleet
                if any(test_usage[tid] > next(v for v in vehicle_types if v.id == tid).max_available 
                       for tid in test_usage):
                    continue

                # Formula CS: S_ij = (Cost_i + Cost_j) - Cost_merged
                cs_value = (ri['cost'] + rj['cost']) - cost_merged
                
                if cs_value > max_cs and cs_value > 0:
                    max_cs = cs_value
                    best_merge = (i, j, combined_customers, combined_demand, 
                                  combined_dist, best_vt_merged, cost_merged, 
                                  test_usage, combined_needs_ref)

        if best_merge:
            idx_i, idx_j, new_cust, new_dem, new_dist, new_vt, new_cost, new_usage, new_ref = best_merge
            # Update route list
            first = min(idx_i, idx_j)
            second = max(idx_i, idx_j)
            current_routes.pop(second)
            current_routes.pop(first)
            
            current_routes.append({
                'customers': new_cust, 'demand': new_dem, 
                'dist': new_dist, 'vt': new_vt, 'cost': new_cost,
                'needs_refrigeration': new_ref
            })
            merged_any = True
            fleet_usage = new_usage

    # 3. Transform into Route objects
    final_routes = []
    for r in current_routes:
        final_routes.append(Route(
            depot=depot, vehicle_type=r['vt'], customers=r['customers'],
            total_distance=round(r['dist'], 2),
            total_demand=round(r['demand'], 2),
            total_cost=round(r['cost'], 2)
        ))
    return final_routes
