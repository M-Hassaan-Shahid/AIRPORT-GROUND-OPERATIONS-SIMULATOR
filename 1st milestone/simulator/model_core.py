"""
model_core.py - Wireless Cellular Automaton Core
=================================================

This module defines the microscopic state and update rules.
IT IS DESIGNED TO BE IMPLEMENTED BY THE RESEARCH PARTNER.

Current implementation is a STUB/PLACEHOLDER that provides
basic movement logic to allow the simulation loop to run.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Any
from .layout import Layout, Edge, EdgeType
from .params import SimulationParams
from .spawning import Aircraft, FlightStatus
from . import rules
from . import capacity


@dataclass
class SimulationState:
    """
    Complete state of the cellular automaton simulation.
    """
    aircraft: List[Aircraft] = field(default_factory=list)
    time: float = 0.0
    
    # Track statistics for the current step
    metrics_snapshot: Dict[str, Any] = field(default_factory=dict)


def init_state(layout: Layout, params: SimulationParams) -> SimulationState:
    """
    Initialize the simulation state.
    """
    return SimulationState(
        aircraft=[],
        time=0.0,
        metrics_snapshot={}
    )


def step(state: SimulationState, 
         layout: Layout, 
         params: SimulationParams, 
         capacity_state: capacity.CapacityState,
         dt: float = 1.0) -> Tuple[SimulationState, Dict[str, Any]]:
    """
    Advance the simulation by one time step.
    
    Args:
        state: Current simulation state
        layout: Airport layout
        params: Simulation parameters
        capacity_state: Current capacity state (mutated in place)
        dt: Time step size in seconds
        
    Returns:
        Tuple of (new_state, observables_dict)
    """
    
    # 1. Update time
    new_time = state.time + dt
    
    # 2. Process each aircraft
    active_aircraft = []
    
    # Simple movement logic for placeholder:
    # Move aircraft along their route edges at assigned speed
    
    for aircraft in state.aircraft:
        
        # Skip if finished
        if aircraft.status in [FlightStatus.DEPARTED, FlightStatus.PARKED] and aircraft.completion_time:
             # Keep them in list? usually remove or move to "finished" list
             # For this simple loop, we'll filter them out of active list eventually
             # but we might want to keep them for a bit or archive them
             if new_time - aircraft.completion_time > 60: # Keep for 1 min then remove
                 continue
        
        # Handle movement
        if aircraft.route and aircraft.current_edge_idx < len(aircraft.route.edges):
            edge_id = aircraft.route.edges[aircraft.current_edge_idx]
            edge = layout.get_edge(edge_id)
            
            if edge:
                # Calculate speed limit
                limit = rules.get_speed_limit(edge, aircraft.aircraft_class, params)
                
                # Check separation/congestion (Placeholder)
                # In real CA, this would check cells ahead.
                # Here, we check if edge is congested in capacity module
                
                # Simple acceleration/deceleration
                if aircraft.speed < limit:
                    aircraft.speed += 2.0 * dt # Accelerate
                elif aircraft.speed > limit:
                    aircraft.speed -= 2.0 * dt # Brake
                
                # Move
                dist_moved = aircraft.speed * dt
                aircraft.position_on_edge += dist_moved
                
                # Check if reached end of edge
                if aircraft.position_on_edge >= edge.length:
                    # Move to next edge
                    remaining_dist = aircraft.position_on_edge - edge.length
                    
                    # Check if allowed to enter next edge
                    next_idx = aircraft.current_edge_idx + 1
                    
                    if next_idx < len(aircraft.route.edges):
                        next_edge_id = aircraft.route.edges[next_idx]
                        next_edge = layout.get_edge(next_edge_id)
                        
                        # Use capacity module to manage occupancy
                        capacity_state.remove_from_edge(aircraft.id, edge_id)
                        capacity_state.add_to_edge(aircraft.id, next_edge_id)
                        
                        aircraft.current_edge_idx = next_idx
                        aircraft.position_on_edge = remaining_dist
                    else:
                        # Reached destination
                        finish_aircraft(aircraft, new_time, capacity_state)
        
        active_aircraft.append(aircraft)
    
    state.aircraft = active_aircraft
    state.time = new_time
    
    # 3. Compute observables for metrics
    observables = {
        "aircraft_count": len(active_aircraft),
        "departures_count": len([a for a in active_aircraft if not a.is_arrival]),
        "arrivals_count": len([a for a in active_aircraft if a.is_arrival]),
    }
    
    return state, observables


def finish_aircraft(aircraft: Aircraft, time: float, 
                    capacity_state: capacity.CapacityState):
    """Handle aircraft reaching destination."""
    aircraft.completion_time = time
    aircraft.speed = 0.0
    
    if aircraft.is_arrival:
        aircraft.status = FlightStatus.PARKED
        # It's at the gate, keep gate occupied
    else:
        aircraft.status = FlightStatus.DEPARTED
        # Left ground, release gate if it had one (should have released on pushback really)
        if aircraft.gate_id:
            capacity_state.release_gate(aircraft.gate_id)
            
    # Remove from any edge occupancy
    if aircraft.current_edge_id:
        capacity_state.remove_from_edge(aircraft.id, aircraft.current_edge_id)
