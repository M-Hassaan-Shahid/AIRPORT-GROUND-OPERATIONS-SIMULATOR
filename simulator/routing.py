"""
routing.py - Route Assignment and Rerouting
=============================================

Handle all pathfinding and rerouting over the layout graph.
Uses Dijkstra's algorithm for shortest paths.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
import heapq
from .layout import Layout, Node, Edge, NodeType, EdgeType, AllowedFlow
from . import rules


@dataclass
class Route:
    """
    A route from origin to destination.
    
    Attributes:
        edges: List of edge IDs in order
        origin_node: Starting node ID
        destination_node: Ending node ID
        total_length: Total route length in meters
    """
    edges: List[str]
    origin_node: str
    destination_node: str
    total_length: float = 0.0
    
    def is_empty(self) -> bool:
        return len(self.edges) == 0


@dataclass 
class RouteCache:
    """Cache for precomputed routes."""
    routes: Dict[Tuple[str, str, str, bool], Route] = field(default_factory=dict)
    # Key: (origin, destination, aircraft_class, is_arrival)


class Router:
    """
    Pathfinding and route management.
    """
    
    def __init__(self, layout: Layout):
        self.layout = layout
        self.cache = RouteCache()
        self._precomputed = False
    
    def precompute_routes(self) -> None:
        """
        Precompute common routes between key points.
        Routes from all gates to all runway entries (departures)
        Routes from all runway exits to all gates (arrivals)
        """
        gates = self.layout.get_gates()
        runway_ends = self.layout.get_runway_ends()
        
        # Get runway entries and exits
        runway_entries = [n for n in self.layout.nodes.values() 
                         if n.node_type == NodeType.RUNWAY_ENTRY]
        runway_exits = [n for n in self.layout.nodes.values() 
                       if n.node_type == NodeType.RUNWAY_EXIT]
        
        # Also include runway ends as potential entry/exit points
        all_runway_points = runway_ends + runway_entries + runway_exits
        
        # For each aircraft class
        for ac_class in ["small", "medium", "large"]:
            # Departure routes: Gate -> Runway Entry/End
            for gate in gates:
                for rwy_point in all_runway_points:
                    route = self.find_route(
                        gate.id, rwy_point.id, 
                        aircraft_class=ac_class, 
                        is_arrival=False
                    )
                    if route and not route.is_empty():
                        key = (gate.id, rwy_point.id, ac_class, False)
                        self.cache.routes[key] = route
            
            # Arrival routes: Runway Exit/End -> Gate
            for rwy_point in all_runway_points:
                for gate in gates:
                    route = self.find_route(
                        rwy_point.id, gate.id,
                        aircraft_class=ac_class,
                        is_arrival=True
                    )
                    if route and not route.is_empty():
                        key = (rwy_point.id, gate.id, ac_class, True)
                        self.cache.routes[key] = route
        
        self._precomputed = True
    
    def find_route(self, origin_id: str, destination_id: str,
                   aircraft_class: str = "medium",
                   is_arrival: bool = False) -> Optional[Route]:
        """
        Find shortest route from origin to destination.
        
        Uses Dijkstra's algorithm with edge weights based on length.
        Respects access rules for arrivals/departures.
        
        Args:
            origin_id: Starting node ID
            destination_id: Ending node ID
            aircraft_class: Size class of aircraft
            is_arrival: True if aircraft is an arrival
        
        Returns:
            Route object, or None if no path exists
        """
        # Check cache first
        cache_key = (origin_id, destination_id, aircraft_class, is_arrival)
        if cache_key in self.cache.routes:
            return self.cache.routes[cache_key]
        
        # Dijkstra's algorithm
        origin = self.layout.get_node(origin_id)
        destination = self.layout.get_node(destination_id)
        
        if not origin or not destination:
            return None
        
        # Priority queue: (distance, node_id, path_edges)
        pq = [(0.0, origin_id, [])]
        visited = set()
        
        while pq:
            dist, current_id, path = heapq.heappop(pq)
            
            if current_id in visited:
                continue
            visited.add(current_id)
            
            if current_id == destination_id:
                return Route(
                    edges=path,
                    origin_node=origin_id,
                    destination_node=destination_id,
                    total_length=dist
                )
            
            # Explore neighbors
            for edge in self.layout.get_edges_from_node(current_id):
                # Determine next node
                if edge.start_node == current_id:
                    next_id = edge.end_node
                elif not edge.one_way:
                    next_id = edge.start_node
                else:
                    continue  # Can't traverse this direction
                
                if next_id in visited:
                    continue
                
                # Check access rules
                if not rules.can_access(edge, aircraft_class, is_arrival):
                    continue
                
                new_dist = dist + edge.length
                new_path = path + [edge.id]
                heapq.heappush(pq, (new_dist, next_id, new_path))
        
        return None  # No path found
    
    def get_route(self, origin_id: str, destination_id: str,
                  aircraft_class: str = "medium",
                  is_arrival: bool = False) -> Optional[Route]:
        """
        Get a route, using cache if available.
        """
        cache_key = (origin_id, destination_id, aircraft_class, is_arrival)
        if cache_key in self.cache.routes:
            return self.cache.routes[cache_key]
        return self.find_route(origin_id, destination_id, aircraft_class, is_arrival)
    
    def reroute_if_needed(self, current_node_id: str, 
                          original_route: Route,
                          current_edge_idx: int,
                          aircraft_class: str,
                          is_arrival: bool,
                          blocked_edges: Set[str] = None,
                          congested_edges: Set[str] = None) -> Optional[Route]:
        """
        Check if rerouting is needed and find alternative.
        
        Rerouting rules:
        - Never reverse or backtrack
        - Only consider forward paths from current position
        - Avoid blocked/congested edges
        
        Args:
            current_node_id: Current node where aircraft is
            original_route: The original planned route
            current_edge_idx: Current index in the original route
            aircraft_class: Size class of aircraft
            is_arrival: True if aircraft is arrival
            blocked_edges: Set of edge IDs that are blocked
            congested_edges: Set of edge IDs that are congested
        
        Returns:
            New Route if rerouting needed, None if current route is fine
        """
        if blocked_edges is None:
            blocked_edges = set()
        if congested_edges is None:
            congested_edges = set()
        
        # Check if remaining route has any blocked edges
        remaining_edges = original_route.edges[current_edge_idx:]
        needs_reroute = False
        
        for edge_id in remaining_edges:
            if edge_id in blocked_edges:
                needs_reroute = True
                break
        
        if not needs_reroute:
            return None  # Current route is fine
        
        # Find alternative route avoiding blocked edges
        destination_id = original_route.destination_node
        
        # Modified Dijkstra avoiding blocked/heavily congested edges
        pq = [(0.0, current_node_id, [])]
        visited = set()
        
        while pq:
            dist, current_id, path = heapq.heappop(pq)
            
            if current_id in visited:
                continue
            visited.add(current_id)
            
            if current_id == destination_id:
                return Route(
                    edges=path,
                    origin_node=current_node_id,
                    destination_node=destination_id,
                    total_length=dist
                )
            
            for edge in self.layout.get_edges_from_node(current_id):
                # Skip blocked edges
                if edge.id in blocked_edges:
                    continue
                
                # Determine next node
                if edge.start_node == current_id:
                    next_id = edge.end_node
                elif not edge.one_way:
                    next_id = edge.start_node
                else:
                    continue
                
                if next_id in visited:
                    continue
                
                if not rules.can_access(edge, aircraft_class, is_arrival):
                    continue
                
                # Add congestion penalty
                edge_cost = edge.length
                if edge.id in congested_edges:
                    edge_cost *= 2.0  # Double cost for congested edges
                
                new_dist = dist + edge_cost
                new_path = path + [edge.id]
                heapq.heappush(pq, (new_dist, next_id, new_path))
        
        return None  # No alternative found
    
    def get_active_runway_ends(self, wind_direction: float) -> List[Node]:
        """
        Get runway ends that are active based on wind direction.
        
        Args:
            wind_direction: Wind direction in degrees
        
        Returns:
            List of active runway end nodes
        """
        runway_ends = self.layout.get_runway_ends()
        active_direction = rules.get_active_runway_direction(wind_direction)
        
        # Filter runway ends by direction
        # This is simplified - in reality, need to match runway numbers
        active_ends = []
        for node in runway_ends:
            # If node name contains the active direction number, include it
            if active_direction in node.name or active_direction in node.id:
                active_ends.append(node)
        
        # If no specific match, return all runway ends
        return active_ends if active_ends else runway_ends
    
    def get_departure_start_points(self) -> List[Node]:
        """Get nodes where departures can start (gates)."""
        return self.layout.get_gates()
    
    def get_arrival_start_points(self, wind_direction: float) -> List[Node]:
        """Get nodes where arrivals can start (active runway ends)."""
        return self.get_active_runway_ends(wind_direction)
    
    def get_departure_destinations(self, wind_direction: float) -> List[Node]:
        """Get nodes where departures go (active runway ends)."""
        return self.get_active_runway_ends(wind_direction)
    
    def get_arrival_destinations(self) -> List[Node]:
        """Get nodes where arrivals go (gates)."""
        return self.layout.get_gates()
    
    def get_edge_sequence_length(self, edge_ids: List[str]) -> float:
        """Calculate total length of a sequence of edges."""
        total = 0.0
        for edge_id in edge_ids:
            edge = self.layout.get_edge(edge_id)
            if edge:
                total += edge.length
        return total
    
    def get_nodes_on_route(self, route: Route) -> List[str]:
        """Get list of node IDs along a route."""
        if route.is_empty():
            return [route.origin_node, route.destination_node]
        
        nodes = [route.origin_node]
        for edge_id in route.edges:
            edge = self.layout.get_edge(edge_id)
            if edge:
                # Add the node we're going to
                if edge.start_node == nodes[-1]:
                    nodes.append(edge.end_node)
                else:
                    nodes.append(edge.start_node)
        return nodes
