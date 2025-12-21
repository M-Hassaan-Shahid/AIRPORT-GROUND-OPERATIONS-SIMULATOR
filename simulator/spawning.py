"""
spawning.py - Arrival and Departure Generation
===============================================

Generate arrivals and departures based on parameters and current
simulation state. Assigns initial routes and properties.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any
from enum import Enum
import random
import uuid

from .layout import Layout, Node
from .params import SimulationParams, AircraftClass
from . import capacity
from . import routing


class FlightStatus(Enum):
    """Status of an aircraft flight."""
    SCHEDULED = "scheduled"
    TAXIING_OUT = "taxiing_out"
    TAKING_OFF = "taking_off"
    DEPARTED = "departed"
    LANDING = "landing"
    TAXIING_IN = "taxiing_in"
    PARKED = "parked"


@dataclass
class Aircraft:
    """
    An aircraft in the simulation.
    
    Attributes:
        id: Unique identifier
        aircraft_class: Size class (small, medium, large)
        is_arrival: True if arrival, False if departure
        route: The assigned Route object
        current_edge_idx: Index of the current edge in the route
        position_on_edge: Distance from start of current edge (meters)
        speed: Current speed (m/s)
        status: Current flight status
        gate_id: Assigned gate ID (if any)
        spawning_time: Simulation time when aircraft was created
        completion_time: Simulation time when aircraft finished
    """
    id: str
    aircraft_class: str
    is_arrival: bool
    route: Optional[routing.Route] = None
    current_edge_idx: int = 0
    position_on_edge: float = 0.0
    speed: float = 0.0
    status: FlightStatus = FlightStatus.SCHEDULED
    gate_id: Optional[str] = None
    spawning_time: float = 0.0
    completion_time: Optional[float] = None
    
    @property
    def current_edge_id(self) -> Optional[str]:
        """Get ID of current edge."""
        if self.route and 0 <= self.current_edge_idx < len(self.route.edges):
            return self.route.edges[self.current_edge_idx]
        return None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON/logging."""
        return {
            "id": self.id,
            "class": self.aircraft_class,
            "type": "arrival" if self.is_arrival else "departure",
            "status": self.status.value,
            "edge": self.current_edge_id,
            "position": self.position_on_edge,
            "speed": self.speed,
            "gate": self.gate_id
        }


def spawn_departures(layout: Layout, params: SimulationParams, 
                     capacity_state: capacity.CapacityState, 
                     router: routing.Router,
                     time: float, dt: float) -> List[Aircraft]:
    """
    Generate new departure aircraft.
    
    Logic:
    1. Check if traffic settings allow departures
    2. Determine number of aircraft to spawn based on rate and dt
    3. For each new aircraft:
       - Sample size class
       - Find available gate
       - If gate found, create aircraft and assign route to active runway
    
    Args:
        layout: Airport layout
        params: Simulation parameters
        capacity_state: Current capacity state
        router: Router for pathfinding
        time: Current simulation time
        dt: Time step duration
    
    Returns:
        List of newly created Aircraft objects
    """
    new_aircraft = []
    
    # Check if departures allowed
    rate = params.get_spawn_rate(is_arrival=False, time=time)
    if rate <= 0:
        return []
    
    # Calculate number to spawn (Poisson process approximation)
    # Rate is aircraft/minute, so convert to aircraft/step
    expected_spawns = (rate / 60.0) * dt
    
    # Use random chance for discrete events
    # Or accumulate fractional spawns (simple version: random check)
    rng = params._rng or random.Random()
    if rng.random() > expected_spawns:
        return []
        
    # Spawn one aircraft (could loop if rate is very high)
    
    # 1. Sample size class
    size_class = params.sample_aircraft_class(is_arrival=False)
    
    # 2. Find available gate
    gate_id = capacity_state.assign_gate(
        aircraft_id="PENDING", # Placeholder
        apron=None, # Any apron
        aircraft_class=size_class
    )
    
    if not gate_id:
        # No gates available, cannot spawn
        return []
    
    # 3. Determine destination (active runway end)
    wind_speed, wind_dir = params.get_wind(time)
    destinations = router.get_departure_destinations(wind_dir)
    
    if not destinations:
        # No active runway ends? Should not happen if layout valid
        capacity_state.release_gate(gate_id)
        return []
        
    # Pick a destination (randomly if multiple)
    destination = rng.choice(destinations)
    
    # 4. Find route
    route = router.get_route(gate_id, destination.id, size_class, is_arrival=False)
    
    if not route:
        # No route possible
        capacity_state.release_gate(gate_id)
        return []
    
    # 5. Create aircraft
    aircraft_id = f"DEP_{uuid.uuid4().hex[:6].upper()}"
    aircraft = Aircraft(
        id=aircraft_id,
        aircraft_class=size_class,
        is_arrival=False,
        route=route,
        status=FlightStatus.TAXIING_OUT,
        gate_id=gate_id,
        spawning_time=time
    )
    
    # Update gate occupancy with real ID
    capacity_state.gates[gate_id].occupied_by = aircraft_id
    
    new_aircraft.append(aircraft)
    return new_aircraft


def spawn_arrivals(layout: Layout, params: SimulationParams, 
                   capacity_state: capacity.CapacityState, 
                   router: routing.Router,
                   time: float, dt: float) -> List[Aircraft]:
    """
    Generate new arrival aircraft.
    
    Logic:
    1. Check if traffic settings allow arrivals
    2. Determine number to spawn
    3. For each new aircraft:
       - Sample size class
       - Pick active runway entry point
       - Find assigned gate
       - Determine route from runway exit to gate
    
    Args:
        layout: Airport layout
        params: Simulation parameters
        capacity_state: Current capacity state
        router: Router for pathfinding
        time: Current simulation time
        dt: Time step duration
        
    Returns:
        List of newly created Aircraft objects
    """
    new_aircraft = []
    
    # Check if arrivals allowed
    rate = params.get_spawn_rate(is_arrival=True, time=time)
    if rate <= 0:
        return []
    
    # Calculate spawns
    expected_spawns = (rate / 60.0) * dt
    rng = params._rng or random.Random()
    if rng.random() > expected_spawns:
        return []
    
    # Spawn one aircraft
    
    # 1. Sample size class
    size_class = params.sample_aircraft_class(is_arrival=True)
    
    # 2. Pick start point (active runway end)
    wind_speed, wind_dir = params.get_wind(time)
    starts = router.get_arrival_start_points(wind_dir)
    
    if not starts:
        return []
        
    start_node = rng.choice(starts)
    
    # 3. Assign a gate
    # For arrivals, we need to know where they are going
    gate_id = capacity_state.assign_gate(
        aircraft_id="PENDING", 
        apron=None, 
        aircraft_class=size_class
    )
    
    if not gate_id:
        # No gates available - usually would go to holding stack
        # For this sim, we just don't spawn
        return []
    
    # 4. Find route
    # Note: Route actually starts from runway exit, not runway end
    # But for graph connectivity, we might route from end -> exit -> taxiway -> gate
    # Or we assume they land and exit at optimal point
    
    # Simplified: Find route from start_node (runway end) to gate
    # Logic in routing or rules should handle "runway occupancy" to exit
    
    # Try different runway exits to find optimal one?
    # For now, just route from landing start point
    route = router.get_route(start_node.id, gate_id, size_class, is_arrival=True)
    
    if not route:
        capacity_state.release_gate(gate_id)
        return []
    
    # 5. Create aircraft
    aircraft_id = f"ARR_{uuid.uuid4().hex[:6].upper()}"
    aircraft = Aircraft(
        id=aircraft_id,
        aircraft_class=size_class,
        is_arrival=True,
        route=route,
        status=FlightStatus.LANDING,
        gate_id=gate_id,
        spawning_time=time
    )
    
    # Update gate occupancy with real ID (reservation)
    capacity_state.gates[gate_id].occupied_by = aircraft_id
    
    new_aircraft.append(aircraft)
    return new_aircraft
