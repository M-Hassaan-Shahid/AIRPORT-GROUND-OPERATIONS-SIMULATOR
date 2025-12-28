"""
capacity.py - Queues and Resource Management
==============================================

Manage capacities and queues for limited resources:
gates, hold points, and runways.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from .params import PriorityMode
from . import rules


class GateState(Enum):
    """State of a gate."""
    FREE = "free"
    OCCUPIED = "occupied"
    RESERVED = "reserved"


class RunwayState(Enum):
    """State of a runway."""
    CLEAR = "clear"
    OCCUPIED_ARRIVAL = "occupied_arrival"
    OCCUPIED_DEPARTURE = "occupied_departure"


@dataclass
class GateStatus:
    """Status of a single gate."""
    gate_id: str
    apron: str
    size_class: Optional[str]  # Size restriction (if any)
    state: GateState = GateState.FREE
    occupied_by: Optional[str] = None  # Aircraft ID
    
    def is_available(self, aircraft_class: str = None) -> bool:
        """Check if gate is available for an aircraft."""
        if self.state != GateState.FREE:
            return False
        if self.size_class and aircraft_class:
            # Check size compatibility
            size_order = {"small": 1, "medium": 2, "large": 3}
            return size_order.get(aircraft_class, 2) <= size_order.get(self.size_class, 2)
        return True


@dataclass
class HoldQueue:
    """Queue at a hold point."""
    hold_point_id: str
    queue: List[str] = field(default_factory=list)  # Aircraft IDs in order
    waiting_times: Dict[str, float] = field(default_factory=dict)  # ID -> wait time
    
    def add(self, aircraft_id: str) -> None:
        """Add aircraft to the queue."""
        if aircraft_id not in self.queue:
            self.queue.append(aircraft_id)
            self.waiting_times[aircraft_id] = 0.0
    
    def remove(self, aircraft_id: str) -> None:
        """Remove aircraft from the queue."""
        if aircraft_id in self.queue:
            self.queue.remove(aircraft_id)
        self.waiting_times.pop(aircraft_id, None)
    
    def update_waiting_times(self, dt: float) -> None:
        """Update waiting times by dt seconds."""
        for aircraft_id in self.queue:
            self.waiting_times[aircraft_id] = self.waiting_times.get(aircraft_id, 0) + dt
    
    def __len__(self) -> int:
        return len(self.queue)
    
    def is_empty(self) -> bool:
        return len(self.queue) == 0


@dataclass
class RunwayStatus:
    """Status of a runway."""
    runway_id: str
    state: RunwayState = RunwayState.CLEAR
    current_aircraft: Optional[str] = None
    active_direction: Optional[str] = None  # e.g., "21" or "03"
    
    def is_available(self) -> bool:
        """Check if runway is available for operations."""
        return self.state == RunwayState.CLEAR
    
    def occupy(self, aircraft_id: str, is_arrival: bool) -> None:
        """Mark runway as occupied."""
        self.current_aircraft = aircraft_id
        self.state = RunwayState.OCCUPIED_ARRIVAL if is_arrival else RunwayState.OCCUPIED_DEPARTURE
    
    def release(self) -> None:
        """Mark runway as clear."""
        self.current_aircraft = None
        self.state = RunwayState.CLEAR


@dataclass
class EdgeOccupancy:
    """Track occupancy of an edge (taxiway segment)."""
    edge_id: str
    aircraft_ids: List[str] = field(default_factory=list)
    capacity: int = 10  # Soft limit
    
    def add(self, aircraft_id: str) -> None:
        if aircraft_id not in self.aircraft_ids:
            self.aircraft_ids.append(aircraft_id)
    
    def remove(self, aircraft_id: str) -> None:
        if aircraft_id in self.aircraft_ids:
            self.aircraft_ids.remove(aircraft_id)
    
    def count(self) -> int:
        return len(self.aircraft_ids)
    
    def is_full(self) -> bool:
        return len(self.aircraft_ids) >= self.capacity


class CapacityState:
    """
    Central state for all capacity-limited resources.
    
    Tracks:
    - Gate occupancy and availability
    - Hold point queues
    - Runway status
    - Edge occupancies (taxiways)
    """
    
    def __init__(self):
        self.gates: Dict[str, GateStatus] = {}
        self.holds: Dict[str, HoldQueue] = {}
        self.runways: Dict[str, RunwayStatus] = {}
        self.edges: Dict[str, EdgeOccupancy] = {}
        self._aircraft_lookup: Dict[str, Dict] = {}  # For quick lookups
    
    def initialize_from_layout(self, layout, params) -> None:
        """
        Initialize capacity tracking from layout.
        
        Args:
            layout: Layout object with nodes and edges
            params: SimulationParams with capacity settings
        """
        from .layout import NodeType, EdgeType
        
        # Initialize gates
        for node in layout.get_gates():
            self.gates[node.id] = GateStatus(
                gate_id=node.id,
                apron=node.apron or "default",
                size_class=node.size_class,
            )
        
        # Initialize hold points
        for node in layout.get_hold_points():
            self.holds[node.id] = HoldQueue(hold_point_id=node.id)
        
        # Initialize runways
        runway_edges = layout.get_edges_by_type(EdgeType.RUNWAY)
        runway_ids = set()
        for edge in runway_edges:
            # Use start node or a common identifier
            runway_id = f"RWY_{edge.id}"
            if runway_id not in runway_ids:
                self.runways[runway_id] = RunwayStatus(runway_id=runway_id)
                runway_ids.add(runway_id)
        
        # If no runways found, create a default one
        if not self.runways:
            self.runways["RWY_MAIN"] = RunwayStatus(runway_id="RWY_MAIN")
        
        # Initialize edge occupancies
        for edge_id, edge in layout.edges.items():
            capacity = edge.capacity_hint or 10
            self.edges[edge_id] = EdgeOccupancy(edge_id=edge_id, capacity=capacity)
    
    # Gate management
    def get_available_gates(self, apron: str = None, aircraft_class: str = None) -> List[str]:
        """Get list of available gate IDs."""
        available = []
        for gate_id, gate in self.gates.items():
            if apron and gate.apron != apron:
                continue
            if gate.is_available(aircraft_class):
                available.append(gate_id)
        return available
    
    def assign_gate(self, aircraft_id: str, gate_id: str = None, 
                    apron: str = None, aircraft_class: str = None) -> Optional[str]:
        """
        Assign a gate to an aircraft.
        
        Args:
            aircraft_id: ID of the aircraft
            gate_id: Specific gate to assign (optional)
            apron: Preferred apron (optional)
            aircraft_class: Size class for compatibility check
        
        Returns:
            Gate ID if assigned, None if no gate available
        """
        if gate_id and gate_id in self.gates:
            gate = self.gates[gate_id]
            if gate.is_available(aircraft_class):
                gate.state = GateState.OCCUPIED
                gate.occupied_by = aircraft_id
                return gate_id
            return None
        
        # Find any available gate
        available = self.get_available_gates(apron, aircraft_class)
        if available:
            gate_id = available[0]
            self.gates[gate_id].state = GateState.OCCUPIED
            self.gates[gate_id].occupied_by = aircraft_id
            return gate_id
        
        return None
    
    def release_gate(self, gate_id: str) -> None:
        """Release a gate."""
        if gate_id in self.gates:
            self.gates[gate_id].state = GateState.FREE
            self.gates[gate_id].occupied_by = None
    
    def get_gate_for_aircraft(self, aircraft_id: str) -> Optional[str]:
        """Get the gate assigned to an aircraft."""
        for gate_id, gate in self.gates.items():
            if gate.occupied_by == aircraft_id:
                return gate_id
        return None
    
    # Hold queue management
    def add_to_hold(self, aircraft_id: str, hold_point_id: str) -> None:
        """Add aircraft to a hold queue."""
        if hold_point_id not in self.holds:
            self.holds[hold_point_id] = HoldQueue(hold_point_id=hold_point_id)
        self.holds[hold_point_id].add(aircraft_id)
    
    def remove_from_hold(self, aircraft_id: str, hold_point_id: str) -> None:
        """Remove aircraft from a hold queue."""
        if hold_point_id in self.holds:
            self.holds[hold_point_id].remove(aircraft_id)
    
    def get_hold_queue_length(self, hold_point_id: str) -> int:
        """Get length of a hold queue."""
        if hold_point_id in self.holds:
            return len(self.holds[hold_point_id])
        return 0
    
    def can_release_from_hold(self, hold_point_id: str, 
                              runway_id: str = None) -> bool:
        """
        Check if an aircraft can be released from hold.
        """
        # Check hold queue is not empty
        if hold_point_id not in self.holds or self.holds[hold_point_id].is_empty():
            return False
        
        # Check runway is available
        if runway_id:
            if runway_id in self.runways:
                if not self.runways[runway_id].is_available():
                    return False
        else:
            # Check any runway
            if not any(r.is_available() for r in self.runways.values()):
                return False
        
        return True
    
    def get_next_from_hold(self, hold_point_id: str, priority_mode: PriorityMode,
                           aircraft_data: Dict[str, Any] = None) -> Optional[str]:
        """
        Get the next aircraft ID to release from hold.
        
        Args:
            hold_point_id: ID of the hold point
            priority_mode: Priority mode for ordering
            aircraft_data: Dict of aircraft_id -> aircraft data for priority checks
        
        Returns:
            Aircraft ID to release, or None
        """
        if hold_point_id not in self.holds:
            return None
        
        queue = self.holds[hold_point_id].queue
        if not queue:
            return None
        
        # Get priority order
        def get_arrival(ac_id):
            if aircraft_data and ac_id in aircraft_data:
                return aircraft_data[ac_id].get("is_arrival", False)
            return False
        
        def get_size(ac_id):
            if aircraft_data and ac_id in aircraft_data:
                return aircraft_data[ac_id].get("aircraft_class", "medium")
            return "medium"
        
        idx = rules.get_next_to_release(queue, priority_mode, get_arrival, get_size)
        return queue[idx] if idx is not None else None
    
    def release_from_hold(self, hold_point_id: str, aircraft_id: str) -> bool:
        """Release an aircraft from hold."""
        if hold_point_id in self.holds:
            if aircraft_id in self.holds[hold_point_id].queue:
                self.holds[hold_point_id].remove(aircraft_id)
                return True
        return False
    
    def update_hold_waiting_times(self, dt: float) -> None:
        """Update all hold queue waiting times."""
        for hold in self.holds.values():
            hold.update_waiting_times(dt)
    
    # Runway management
    def is_runway_available(self, runway_id: str = None) -> bool:
        """Check if a runway is available."""
        if runway_id:
            return runway_id in self.runways and self.runways[runway_id].is_available()
        return any(r.is_available() for r in self.runways.values())
    
    def get_available_runway(self) -> Optional[str]:
        """Get an available runway ID."""
        for runway_id, runway in self.runways.items():
            if runway.is_available():
                return runway_id
        return None
    
    def occupy_runway(self, aircraft_id: str, runway_id: str, is_arrival: bool) -> bool:
        """Mark runway as occupied by aircraft."""
        if runway_id in self.runways:
            if self.runways[runway_id].is_available():
                self.runways[runway_id].occupy(aircraft_id, is_arrival)
                return True
        return False
    
    def release_runway(self, runway_id: str) -> None:
        """Release a runway."""
        if runway_id in self.runways:
            self.runways[runway_id].release()
    
    def get_runway_for_aircraft(self, aircraft_id: str) -> Optional[str]:
        """Get the runway occupied by an aircraft."""
        for runway_id, runway in self.runways.items():
            if runway.current_aircraft == aircraft_id:
                return runway_id
        return None
    
    def set_active_runway_direction(self, direction: str) -> None:
        """Set active direction for all runways."""
        for runway in self.runways.values():
            runway.active_direction = direction
    
    # Edge occupancy management
    def add_to_edge(self, aircraft_id: str, edge_id: str) -> None:
        """Add aircraft to an edge."""
        if edge_id not in self.edges:
            self.edges[edge_id] = EdgeOccupancy(edge_id=edge_id)
        self.edges[edge_id].add(aircraft_id)
    
    def remove_from_edge(self, aircraft_id: str, edge_id: str) -> None:
        """Remove aircraft from an edge."""
        if edge_id in self.edges:
            self.edges[edge_id].remove(aircraft_id)
    
    def is_edge_congested(self, edge_id: str) -> bool:
        """Check if an edge is congested (at or near capacity)."""
        if edge_id in self.edges:
            return self.edges[edge_id].is_full()
        return False
    
    def is_edge_full(self, edge_id: str) -> bool:
        """Alias for is_edge_congested."""
        return self.is_edge_congested(edge_id)
    
    def get_edge_occupancy(self, edge_id: str) -> int:
        """Get number of aircraft on an edge."""
        if edge_id in self.edges:
            return self.edges[edge_id].count()
        return 0
    
    # Aggregate statistics
    def get_total_aircraft_on_ground(self) -> int:
        """Get total aircraft on the ground."""
        all_aircraft = set()
        for gate in self.gates.values():
            if gate.occupied_by:
                all_aircraft.add(gate.occupied_by)
        for hold in self.holds.values():
            all_aircraft.update(hold.queue)
        for runway in self.runways.values():
            if runway.current_aircraft:
                all_aircraft.add(runway.current_aircraft)
        for edge in self.edges.values():
            all_aircraft.update(edge.aircraft_ids)
        return len(all_aircraft)
    
    def get_snapshot(self) -> Dict[str, Any]:
        """Get a snapshot of current capacity state for metrics."""
        return {
            "gates": {
                gate_id: {"state": gate.state.value, "occupied_by": gate.occupied_by}
                for gate_id, gate in self.gates.items()
            },
            "holds": {
                hold_id: {"queue_length": len(hold), "queue": list(hold.queue)}
                for hold_id, hold in self.holds.items()
            },
            "runways": {
                runway_id: {"state": runway.state.value, "aircraft": runway.current_aircraft}
                for runway_id, runway in self.runways.items()
            },
            "edge_occupancies": {
                edge_id: edge.count()
                for edge_id, edge in self.edges.items()
            },
        }
