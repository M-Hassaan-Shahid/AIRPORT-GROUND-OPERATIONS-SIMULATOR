"""
rules.py - Local and Global Rules
===================================

Encode all rule logic that interprets layout and parameters into
constraints for movement: access, speed, separation, and priority.
"""

from typing import List, Optional, Any
from .layout import Edge, Node, EdgeType, NodeType, AllowedFlow
from .params import SimulationParams, PriorityMode, AircraftClass


def can_access(edge: Edge, aircraft_class: str, is_arrival: bool) -> bool:
    """
    Check if an aircraft can use a specific edge.
    
    Access rules:
    - Arrivals may use arrival-only edges, both edges, and rapid exits
    - Departures may use departure-only edges and both edges, but NOT rapid exits
    - Aircraft must respect size class restrictions
    
    Args:
        edge: The edge to check access for
        aircraft_class: Size class of the aircraft (small/medium/large)
        is_arrival: True if aircraft is an arrival, False for departure
    
    Returns:
        True if the aircraft can use the edge
    """
    # Check flow direction
    if edge.allowed_flow == AllowedFlow.ARRIVAL and not is_arrival:
        return False
    if edge.allowed_flow == AllowedFlow.DEPARTURE and is_arrival:
        return False
    
    # Rapid exits are for arrivals only
    if edge.edge_type == EdgeType.RAPID_EXIT and not is_arrival:
        return False
    
    # Future: Check size class restrictions on edge
    # For now, all sizes can use all edge types
    
    return True


def get_section_type(edge: Edge) -> str:
    """
    Get the section type string for an edge.
    Used for speed and separation calculations.
    """
    if edge.edge_type == EdgeType.RUNWAY:
        return "runway"
    elif edge.edge_type == EdgeType.APRON_LINK:
        return "apron"
    else:  # TAXIWAY, RAPID_EXIT
        return "taxiway"


def get_speed_limit(edge: Edge, aircraft_class: str, params: SimulationParams, 
                    weather: str = None) -> float:
    """
    Calculate the allowed speed on an edge.
    
    Speed = base_speed[class] × section_mult × weather_mult
    
    If edge has a speed_hint, use the minimum of calculated and hint.
    
    Args:
        edge: The edge to calculate speed for
        aircraft_class: Size class of the aircraft
        params: Simulation parameters
        weather: Optional weather condition (uses current if not provided)
    
    Returns:
        Maximum allowed speed in m/s
    """
    section_type = get_section_type(edge)
    calculated_speed = params.get_speed_limit(aircraft_class, section_type, weather)
    
    # Use edge hint if specified
    if edge.speed_hint is not None:
        return min(calculated_speed, edge.speed_hint)
    
    return calculated_speed


def get_separation_distance(edge: Edge, params: SimulationParams, 
                            weather: str = None) -> float:
    """
    Calculate required separation distance for an edge.
    
    Note: On runways, separation is N/A since only 1 aircraft is allowed.
    This function still returns a value for potential approach/departure use.
    
    Separation = base_separation × weather_mult
    
    Args:
        edge: The edge to calculate separation for
        params: Simulation parameters
        weather: Optional weather condition
    
    Returns:
        Required separation distance in meters
    """
    section_type = get_section_type(edge)
    return params.get_separation(section_type, weather)


def get_priority_order(queue: List[Any], priority_mode: PriorityMode,
                       get_arrival_status: callable = None,
                       get_size_class: callable = None) -> List[int]:
    """
    Determine the priority order for a queue of aircraft.
    
    Args:
        queue: List of aircraft (or any objects) in the queue
        priority_mode: The priority mode to use
        get_arrival_status: Function to get is_arrival status from aircraft
        get_size_class: Function to get size class from aircraft
    
    Returns:
        List of indices in priority order (first = highest priority)
    """
    if not queue:
        return []
    
    indices = list(range(len(queue)))
    
    if priority_mode == PriorityMode.FIFO:
        # Already in order
        return indices
    
    elif priority_mode == PriorityMode.RANDOM:
        import random
        random.shuffle(indices)
        return indices
    
    elif priority_mode == PriorityMode.DEPART_FIRST:
        # Departures before arrivals
        if get_arrival_status:
            indices.sort(key=lambda i: get_arrival_status(queue[i]))
        return indices
    
    elif priority_mode == PriorityMode.ARRIVE_FIRST:
        # Arrivals before departures
        if get_arrival_status:
            indices.sort(key=lambda i: not get_arrival_status(queue[i]))
        return indices
    
    elif priority_mode == PriorityMode.SIZE_PRIORITY:
        # LARGE > MEDIUM > SMALL
        if get_size_class:
            size_order = {"large": 0, "medium": 1, "small": 2}
            indices.sort(key=lambda i: size_order.get(get_size_class(queue[i]), 1))
        return indices
    
    elif priority_mode == PriorityMode.WEIGHTED:
        # For future: implement weighted scoring
        return indices
    
    return indices


def get_next_to_release(queue: List[Any], priority_mode: PriorityMode,
                        get_arrival_status: callable = None,
                        get_size_class: callable = None) -> Optional[int]:
    """
    Get the index of the next aircraft to release from a queue.
    
    Args:
        queue: List of aircraft in the queue
        priority_mode: The priority mode to use
        get_arrival_status: Function to get is_arrival status
        get_size_class: Function to get size class
    
    Returns:
        Index of the aircraft to release, or None if queue is empty
    """
    order = get_priority_order(queue, priority_mode, get_arrival_status, get_size_class)
    return order[0] if order else None


def can_release_from_hold(runway_available: bool, next_edge_free: bool) -> bool:
    """
    Check if an aircraft at a hold point can be released.
    
    Release requirements:
    1. The next edge (toward runway) must be free
    2. The runway must be completely clear
    
    Args:
        runway_available: Whether the runway is available
        next_edge_free: Whether the next edge has capacity
    
    Returns:
        True if release is allowed
    """
    return runway_available and next_edge_free


def should_yield(first_aircraft: Any, second_aircraft: Any, 
                 node: Node, priority_mode: PriorityMode,
                 get_arrival_status: callable = None,
                 get_size_class: callable = None) -> bool:
    """
    Determine if first_aircraft should yield to second_aircraft at a node.
    
    Args:
        first_aircraft: Aircraft that would go first in FIFO
        second_aircraft: Aircraft that arrived second
        node: The intersection node
        priority_mode: Priority mode for intersections
        get_arrival_status: Function to get is_arrival status
        get_size_class: Function to get size class
    
    Returns:
        True if first_aircraft should yield (let second go first)
    """
    if priority_mode == PriorityMode.FIFO:
        return False  # First stays first
    
    elif priority_mode == PriorityMode.RANDOM:
        import random
        return random.random() > 0.5
    
    elif priority_mode == PriorityMode.DEPART_FIRST:
        if get_arrival_status:
            # Yield if first is arrival and second is departure
            return get_arrival_status(first_aircraft) and not get_arrival_status(second_aircraft)
        return False
    
    elif priority_mode == PriorityMode.ARRIVE_FIRST:
        if get_arrival_status:
            # Yield if first is departure and second is arrival
            return not get_arrival_status(first_aircraft) and get_arrival_status(second_aircraft)
        return False
    
    elif priority_mode == PriorityMode.SIZE_PRIORITY:
        if get_size_class:
            size_order = {"large": 0, "medium": 1, "small": 2}
            first_priority = size_order.get(get_size_class(first_aircraft), 1)
            second_priority = size_order.get(get_size_class(second_aircraft), 1)
            return second_priority < first_priority  # Yield if second has higher priority
        return False
    
    return False


def get_active_runway_direction(wind_direction: float) -> str:
    """
    Determine active runway direction based on wind.
    
    Aircraft land/takeoff into the wind, so the active direction
    is opposite to the wind direction.
    
    Args:
        wind_direction: Wind direction in degrees (0-360, where wind is coming FROM)
    
    Returns:
        Runway identifier (e.g., "09" or "27") based on wind direction
    """
    # For a runway oriented roughly east-west (09-27):
    # Wind from west (270°) → use 27 (land/takeoff heading east toward 270°)
    # Wind from east (90°) → use 09 (land/takeoff heading west toward 090°)
    
    # Normalize to 0-360
    wind_direction = wind_direction % 360
    
    # If wind is from west-ish (180-360), aircraft takeoff/land heading east
    # If wind is from east-ish (0-180), aircraft takeoff/land heading west
    if 180 <= wind_direction < 360:
        return "27"  # Use runway 27 (heading ~270°)
    else:
        return "09"  # Use runway 09 (heading ~90°)


def compute_runway_heading(runway_number: str) -> float:
    """
    Convert runway number to heading in degrees.
    
    Runway numbers are headings divided by 10.
    E.g., Runway 21 = 210°, Runway 03 = 30°
    """
    try:
        # Remove any L/R/C suffix
        num = ''.join(filter(str.isdigit, runway_number))
        return int(num) * 10
    except:
        return 0.0
