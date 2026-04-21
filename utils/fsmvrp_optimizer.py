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
    vehicle_types: List[VehicleType]
) -> Tuple[Optional[VehicleType], float]:
    """
    F(Z) from theory: Finds the cheapest vehicle (Fixed + Variable) 
    that can transport demand Z over the given distance.
    """
    best_v = None
    min_total_cost = float('inf')
    
    for vt in vehicle_types:
        if vt.capacity >= demand:
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
    Implementare Combined Savings (CS) pentru FSMVRP.
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

    # 1. Inițializare: Fiecare client are propria rută
    # route_data păstrează clienții, cererea, distanța și tipul de vehicul optim
    current_routes: List[Dict[str, Any]] = []
    for c in customers:
        dist = _get_dist([c])
        vt, cost = get_best_vehicle_for_route(c.demand, dist, vehicle_types)
        if vt:
            current_routes.append({
                'customers': [c],
                'demand': c.demand,
                'dist': dist,
                'vt': vt,
                'cost': cost
            })

    # 2. Calculăm economiile Combined Savings (CS)
    # Folosim o abordare iterativă simplificată pentru CS
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
                
                # Verificăm dacă clienții pot fi uniți (ri[-1] -> rj[0])
                # Notă: Într-o implementare completă verificăm poziția în listă. 
                # Aici simulăm fuziunea de rute Clarke-Wright.
                
                combined_customers = ri['customers'] + rj['customers']
                combined_demand = ri['demand'] + rj['demand']
                combined_dist = _get_dist(combined_customers)
                
                # F(Zi + Zj)
                best_vt_merged, cost_merged = get_best_vehicle_for_route(
                    combined_demand, combined_dist, vehicle_types
                )
                
                if not best_vt_merged: continue
                
                # Constrângerea M_k (Fleet Availability)
                # Verificăm dacă prin această fuziune nu depășim numărul total de vehicule pe tip
                # (Simulare simplificată: verificăm doar vehiculul curent)
                
                # Formula CS: S_ij = (Cost_i + Cost_j) - Cost_merged
                cs_value = (ri['cost'] + rj['cost']) - cost_merged
                
                if cs_value > max_cs and cs_value > 0:
                    max_cs = cs_value
                    best_merge = (i, j, combined_customers, combined_demand, 
                                  combined_dist, best_vt_merged, cost_merged)

        if best_merge:
            idx_i, idx_j, new_cust, new_dem, new_dist, new_vt, new_cost = best_merge
            # Actualizăm lista de rute
            # Ștergem rutele vechi (de la indexul mai mare la cel mai mic)
            first = min(idx_i, idx_j)
            second = max(idx_i, idx_j)
            current_routes.pop(second)
            current_routes.pop(first)
            
            current_routes.append({
                'customers': new_cust, 'demand': new_dem, 
                'dist': new_dist, 'vt': new_vt, 'cost': new_cost
            })
            merged_any = True

    # 3. Transformăm în obiecte Route
    final_routes = []
    for r in current_routes:
        final_routes.append(Route(
            depot=depot, vehicle_type=r['vt'], customers=r['customers'],
            total_distance=round(r['dist'], 2),
            total_demand=round(r['demand'], 2),
            total_cost=round(r['cost'], 2)
        ))
    return final_routes
