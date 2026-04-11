"""
FSMVRP — Fleet Size and Mix Vehicle Routing Problem

Objective:
    min  Σ_t (f_t * n_t) + Σ_k Σ_(i,j) c_ij * x_ijk

Subject to:
    Σ_t n_t * Q_t >= total_demand      (demand coverage)
    n_t <= N_t_max   for all t          (availability)
    n_t >= 0, integer                   (integrality)
"""
from typing import List, Dict, Tuple, Optional
from itertools import product
from utils.data_models import VehicleType


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
