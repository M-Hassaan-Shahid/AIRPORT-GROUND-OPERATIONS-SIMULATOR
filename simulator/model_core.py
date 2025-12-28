"""
model_core.py - Nagel-Schreckenberg Cellular Automaton Core
============================================================

Implements microscopic surface movement using NaSch CA rules:
1. Acceleration: v = min(v + 1, vmax)
2. Deceleration: v = min(v, gap_to_aircraft_ahead)
3. Random braking: if rand() < p_slow: v -= 1
4. Movement: position += v

This module handles aircraft movement along routes, hold point waiting,
and runway entry/exit logic.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Any, Optional
import random

from .layout import Layout, Edge, EdgeType, NodeType
from .params import SimulationParams
from .spawning import Aircraft, FlightStatus
from . import rules
from . import capacity


# NaSch CA Parameters
DEFAULT_VMAX = 15.0  # Maximum speed in m/s (about 30 knots for taxiway)
DEFAULT_ACCELERATION = 2.0  # Acceleration rate in m/s^2
DEFAULT_P_SLOW = 0.2  # Random braking probability


@dataclass
class SimulationState:
    """
    Complete state of the cellular automaton simulation.
    
    Attributes:
        aircraft: List of all aircraft in simulation
        time: Current simulation time in seconds
        metrics_snapshot: Current step statistics for metrics
        completed_aircraft: Aircraft that have finished their journey
    """
    aircraft: List[Aircraft] = field(default_factory=list)
    time: float = 0.0
    metrics_snapshot: Dict[str, Any] = field(default_factory=dict)
    completed_aircraft: List[Aircraft] = field(default_factory=list)


def init_state(layout: Layout, params: SimulationParams) -> SimulationState:
    """
    Initialize the simulation state.
    
    Args:
        layout: Airport layout graph
        params: Simulation parameters
        
    Returns:
        Fresh SimulationState ready for simulation
    """
    return SimulationState(
        aircraft=[],
        time=0.0,
        metrics_snapshot={},
        completed_aircraft=[]
    )


def get_aircraft_ahead(current_aircraft: Aircraft, 
                       all_aircraft: List[Aircraft],
                       layout: Layout) -> Tuple[Optional[Aircraft], float]:
    """
    Find the aircraft immediately ahead on the same or next edge.
    
    Returns:
        Tuple of (aircraft_ahead, gap_distance) or (None, inf)
    """
    if not current_aircraft.route:
        return None, float('inf')
    
    current_edge_idx = current_aircraft.current_edge_idx
    current_pos = current_aircraft.position_on_edge
    current_edge = layout.get_edge(current_aircraft.current_edge_id) if current_aircraft.current_edge_id else None
    
    min_gap = float('inf')
    aircraft_ahead = None
    
    for other in all_aircraft:
        if other.id == current_aircraft.id:
            continue
        if other.status in [FlightStatus.DEPARTED, FlightStatus.PARKED]:
            continue
        if not other.route:
            continue
            
        # Check if on same edge
        if other.current_edge_id == current_aircraft.current_edge_id:
            if other.position_on_edge > current_pos:
                gap = other.position_on_edge - current_pos
                if gap < min_gap:
                    min_gap = gap
                    aircraft_ahead = other
                    
        # Check if on next edge (within lookahead distance)
        elif current_edge_idx + 1 < len(current_aircraft.route.edges):
            next_edge_id = current_aircraft.route.edges[current_edge_idx + 1]
            if other.current_edge_id == next_edge_id:
                # Gap = remaining on current edge + position on next edge
                if current_edge:
                    gap = (current_edge.length - current_pos) + other.position_on_edge
                    if gap < min_gap:
                        min_gap = gap
                        aircraft_ahead = other
    
    return aircraft_ahead, min_gap


def is_at_hold_point(aircraft: Aircraft, layout: Layout) -> Tuple[bool, Optional[str]]:
    """
    Check if aircraft is at a hold point node.
    
    Returns:
        Tuple of (is_at_hold, hold_point_node_id)
    """
    if not aircraft.route or aircraft.current_edge_idx >= len(aircraft.route.edges):
        return False, None
    
    edge_id = aircraft.route.edges[aircraft.current_edge_idx]
    edge = layout.get_edge(edge_id)
    
    if not edge:
        return False, None
    
    # Check if we're at the end of this edge (about to enter next)
    if aircraft.position_on_edge >= edge.length * 0.95:  # Near end of edge
        # Check if end node is a hold point
        end_node = layout.get_node(edge.end_node)
        if end_node and end_node.node_type == NodeType.HOLD_POINT:
            return True, end_node.id
            
    return False, None


def can_proceed_from_hold(aircraft: Aircraft, 
                          layout: Layout,
                          capacity_state: capacity.CapacityState,
                          params: SimulationParams) -> bool:
    """
    Check if aircraft at hold point can proceed.
    
    Rules:
    - Runway must be available (not occupied)
    - No aircraft ahead blocking the path
    - Priority rules satisfied
    """
    if not aircraft.route:
        return True
    
    # Check if heading to runway
    next_idx = aircraft.current_edge_idx + 1
    if next_idx >= len(aircraft.route.edges):
        return True  # End of route
    
    next_edge_id = aircraft.route.edges[next_idx]
    next_edge = layout.get_edge(next_edge_id)
    
    if not next_edge:
        return True
    
    # If next edge is runway, check runway availability
    if next_edge.edge_type == EdgeType.RUNWAY:
        # Check all runways for availability
        for runway_id, runway in capacity_state.runways.items():
            if not runway.is_available():
                return False
    
    # Check edge occupancy
    if capacity_state.is_edge_full(next_edge_id):
        return False
    
    return True


def nasch_step(aircraft: Aircraft,
               all_aircraft: List[Aircraft],
               layout: Layout,
               params: SimulationParams,
               capacity_state: capacity.CapacityState,
               dt: float,
               rng: random.Random) -> None:
    """
    Apply NaSch CA update rules to a single aircraft.
    
    NaSch Rules:
    1. Acceleration: v = min(v + accel*dt, vmax)
    2. Deceleration: v = min(v, gap / dt)
    3. Random braking: if rand() < p_slow: v = max(0, v - decel*dt)
    4. Movement: pos += v * dt
    
    Args:
        aircraft: Aircraft to update
        all_aircraft: All aircraft for gap calculation
        layout: Airport layout
        params: Simulation parameters
        capacity_state: Current capacity state
        dt: Time step size
        rng: Random number generator
    """
    # Skip finished aircraft
    if aircraft.status in [FlightStatus.DEPARTED, FlightStatus.PARKED]:
        return
    
    if not aircraft.route or aircraft.current_edge_idx >= len(aircraft.route.edges):
        return
    
    edge_id = aircraft.route.edges[aircraft.current_edge_idx]
    edge = layout.get_edge(edge_id)
    
    if not edge:
        return
    
    # Get speed limit for this edge
    vmax = rules.get_speed_limit(edge, aircraft.aircraft_class, params)
    
    # Check if at hold point
    at_hold, hold_id = is_at_hold_point(aircraft, layout)
    if at_hold and hold_id:
        # Check if we can proceed
        if not can_proceed_from_hold(aircraft, layout, capacity_state, params):
            # Wait at hold - track waiting time
            if not hasattr(aircraft, 'wait_start_time') or aircraft.wait_start_time is None:
                aircraft.wait_start_time = params._rng.random() if hasattr(params, '_rng') else 0
            aircraft.speed = 0.0
            # Add to hold queue if not already
            if hold_id in capacity_state.holds:
                if aircraft.id not in capacity_state.holds[hold_id].queue:
                    capacity_state.holds[hold_id].add(aircraft.id)
            return
        else:
            # Can proceed - occupy runway if entering
            next_idx = aircraft.current_edge_idx + 1
            if next_idx < len(aircraft.route.edges):
                next_edge = layout.get_edge(aircraft.route.edges[next_idx])
                if next_edge and next_edge.edge_type == EdgeType.RUNWAY:
                    # Occupy runway
                    for runway_id, runway in capacity_state.runways.items():
                        if runway.is_available():
                            runway.occupy(aircraft.id, aircraft.is_arrival)
                            break
            # Remove from hold queue
            if hold_id in capacity_state.holds:
                capacity_state.holds[hold_id].remove(aircraft.id)
    
    # --- NaSch Rules ---
    
    # 1. Acceleration
    v = min(aircraft.speed + DEFAULT_ACCELERATION * dt, vmax)
    
    # 2. Deceleration based on gap to aircraft ahead
    aircraft_ahead, gap = get_aircraft_ahead(aircraft, all_aircraft, layout)
    if aircraft_ahead is not None and gap < float('inf'):
        # Leave safety margin
        safe_gap = max(0, gap - 10.0)  # 10m safety buffer
        max_safe_speed = safe_gap / dt if dt > 0 else 0
        v = min(v, max_safe_speed)
    
    # 3. Random braking (stochastic noise)
    if v > 0 and rng.random() < DEFAULT_P_SLOW:
        v = max(0, v - DEFAULT_ACCELERATION * dt)
    
    # 4. Movement
    aircraft.speed = max(0, v)
    dist_moved = aircraft.speed * dt
    aircraft.position_on_edge += dist_moved
    
    # Check if reached end of edge
    if aircraft.position_on_edge >= edge.length:
        remaining = aircraft.position_on_edge - edge.length
        
        # Move to next edge
        next_idx = aircraft.current_edge_idx + 1
        
        # Remove from current edge
        capacity_state.remove_from_edge(aircraft.id, edge_id)
        
        # Release runway if leaving it
        if edge.edge_type == EdgeType.RUNWAY:
            for runway_id, runway in capacity_state.runways.items():
                if runway.current_aircraft == aircraft.id:
                    runway.release()
        
        if next_idx < len(aircraft.route.edges):
            next_edge_id = aircraft.route.edges[next_idx]
            
            # Update edge occupancy
            capacity_state.add_to_edge(aircraft.id, next_edge_id)
            
            aircraft.current_edge_idx = next_idx
            aircraft.position_on_edge = max(remaining, 0)  # Carry over any extra distance
            
            # Update status based on edge type
            next_edge = layout.get_edge(next_edge_id)
            if next_edge:
                if next_edge.edge_type == EdgeType.RUNWAY:
                    if aircraft.is_arrival:
                        aircraft.status = FlightStatus.LANDING
                    else:
                        aircraft.status = FlightStatus.TAKING_OFF
                elif aircraft.status == FlightStatus.TAKING_OFF:
                    aircraft.status = FlightStatus.TAXIING_OUT
                elif aircraft.status == FlightStatus.LANDING:
                    aircraft.status = FlightStatus.TAXIING_IN
        else:
            # Finished all edges - mark for completion
            aircraft.current_edge_idx = next_idx  # This triggers completion in step()


def finish_aircraft(aircraft: Aircraft, time: float, 
                    capacity_state: capacity.CapacityState) -> None:
    """
    Handle aircraft reaching destination.
    
    Args:
        aircraft: Aircraft that finished
        time: Current simulation time
        capacity_state: Capacity state for cleanup
    """
    aircraft.completion_time = time
    aircraft.speed = 0.0
    
    # Calculate taxi time
    if hasattr(aircraft, 'spawning_time'):
        taxi_time = time - aircraft.spawning_time
        if not hasattr(aircraft, 'taxi_time'):
            aircraft.taxi_time = taxi_time
    
    if aircraft.is_arrival:
        aircraft.status = FlightStatus.PARKED
        # Aircraft is at gate, keep gate occupied
    else:
        aircraft.status = FlightStatus.DEPARTED
        # Release gate for departures
        if aircraft.gate_id:
            capacity_state.release_gate(aircraft.gate_id)
    
    # Release runway if still occupied
    for runway_id, runway in capacity_state.runways.items():
        if runway.current_aircraft == aircraft.id:
            runway.release()
    
    # Remove from any edge occupancy
    if aircraft.current_edge_id:
        capacity_state.remove_from_edge(aircraft.id, aircraft.current_edge_id)


def step(state: SimulationState, 
         layout: Layout, 
         params: SimulationParams, 
         capacity_state: capacity.CapacityState,
         dt: float = 1.0) -> Tuple[SimulationState, Dict[str, Any]]:
    """
    Advance the simulation by one time step using NaSch CA rules.
    
    Args:
        state: Current simulation state
        layout: Airport layout
        params: Simulation parameters
        capacity_state: Current capacity state (mutated in place)
        dt: Time step size in seconds
        
    Returns:
        Tuple of (new_state, observables_dict)
    """
    # Get RNG from params or create one
    rng = getattr(params, '_rng', None) or random.Random()
    
    # 1. Update time
    new_time = state.time + dt
    
    # 2. Update hold queue waiting times
    for hold_id, queue in capacity_state.holds.items():
        queue.update_waiting_times(dt)
    
    # 3. Process each aircraft with NaSch rules
    active_aircraft = []
    newly_completed = []
    
    # Sort by position for proper conflict resolution (front-to-back)
    sorted_aircraft = sorted(
        state.aircraft,
        key=lambda a: (a.current_edge_idx, a.position_on_edge),
        reverse=True  # Process from front to back
    )
    
    for aircraft in sorted_aircraft:
        # Check if finished
        if aircraft.status in [FlightStatus.DEPARTED, FlightStatus.PARKED]:
            if aircraft.completion_time:
                # Keep completed aircraft for a bit for metrics
                if new_time - aircraft.completion_time > 60:
                    state.completed_aircraft.append(aircraft)
                    continue
            active_aircraft.append(aircraft)
            continue
        
        # Check if reached destination
        if aircraft.route and aircraft.current_edge_idx >= len(aircraft.route.edges):
            finish_aircraft(aircraft, new_time, capacity_state)
            newly_completed.append(aircraft)
            active_aircraft.append(aircraft)
            continue
        
        # Apply NaSch step
        nasch_step(aircraft, sorted_aircraft, layout, params, capacity_state, dt, rng)
        
        # Check again if finished after movement
        if aircraft.route and aircraft.current_edge_idx >= len(aircraft.route.edges):
            finish_aircraft(aircraft, new_time, capacity_state)
            newly_completed.append(aircraft)
        
        active_aircraft.append(aircraft)
    
    state.aircraft = active_aircraft
    state.time = new_time
    
    # 4. Compute observables for metrics
    active_non_finished = [a for a in active_aircraft 
                          if a.status not in [FlightStatus.DEPARTED, FlightStatus.PARKED]]
    
    # Queue lengths at hold points
    total_queue_length = sum(len(q.queue) for q in capacity_state.holds.values())
    max_queue_length = max((len(q.queue) for q in capacity_state.holds.values()), default=0)
    
    # Runway status
    runways_occupied = sum(1 for r in capacity_state.runways.values() if not r.is_available())
    
    observables = {
        "time": new_time,
        "aircraft_count": len(active_non_finished),
        "total_aircraft": len(active_aircraft),
        "departures_count": len([a for a in active_non_finished if not a.is_arrival]),
        "arrivals_count": len([a for a in active_non_finished if a.is_arrival]),
        "queue_length": total_queue_length,
        "max_queue_length": max_queue_length,
        "runways_occupied": runways_occupied,
        "newly_completed": len(newly_completed),
        "completed_aircraft": newly_completed,
    }
    
    # Store in state for reference
    state.metrics_snapshot = observables
    
    return state, observables
