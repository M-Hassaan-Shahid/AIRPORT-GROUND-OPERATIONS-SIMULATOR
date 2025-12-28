"""
layout.py - Airport Graph Representation
=========================================

Represents the airport as a graph and handles JSON I/O for layouts.
Used by the Path Builder UI to save/load airport configurations.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import json


class NodeType(Enum):
    """Types of nodes in the airport graph."""
    INTERSECTION = "intersection"
    RUNWAY_END = "runway_end"
    RUNWAY_ENTRY = "runway_entry"
    RUNWAY_EXIT = "runway_exit"
    GATE = "gate"
    HOLD_POINT = "hold_point"
    APRON_CENTER = "apron_center"


class EdgeType(Enum):
    """Types of edges in the airport graph."""
    RUNWAY = "runway"
    TAXIWAY = "taxiway"
    APRON_LINK = "apron_link"
    RAPID_EXIT = "rapid_exit"


class AllowedFlow(Enum):
    """Direction restrictions for edges."""
    ARRIVAL = "arrival"
    DEPARTURE = "departure"
    BOTH = "both"


@dataclass
class Node:
    """
    A node in the airport graph.
    
    Attributes:
        id: Unique identifier for the node
        node_type: Type of node (intersection, gate, etc.)
        x: X coordinate in the layout
        y: Y coordinate in the layout
        name: Optional display name
        apron: Optional apron identifier (for gates)
        size_class: Optional size class restriction (SMALL, MEDIUM, LARGE)
    """
    id: str
    node_type: NodeType
    x: float
    y: float
    name: str = ""
    apron: Optional[str] = None
    size_class: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.node_type.value,
            "x": self.x,
            "y": self.y,
            "name": self.name,
            "apron": self.apron,
            "size_class": self.size_class,
        }
    
    @classmethod
    def from_dict(cls, node_id: str, data: Dict[str, Any]) -> "Node":
        """Create Node from dictionary."""
        return cls(
            id=node_id,
            node_type=NodeType(data.get("type", "intersection")),
            x=float(data.get("x", 0)),
            y=float(data.get("y", 0)),
            name=data.get("name", ""),
            apron=data.get("apron"),
            size_class=data.get("size_class"),
        )


@dataclass
class Edge:
    """
    An edge in the airport graph.
    
    Attributes:
        id: Unique identifier for the edge
        edge_type: Type of edge (runway, taxiway, etc.)
        start_node: ID of the start node
        end_node: ID of the end node
        length: Length of the edge in meters
        allowed_flow: Whether arrivals, departures, or both can use this edge
        one_way: Whether the edge is one-way
        speed_hint: Optional suggested speed limit (m/s)
        capacity_hint: Optional capacity limit
        polyline: Optional list of intermediate points [(x, y), ...]
    """
    id: str
    edge_type: EdgeType
    start_node: str
    end_node: str
    length: float
    allowed_flow: AllowedFlow = AllowedFlow.BOTH
    one_way: bool = False
    speed_hint: Optional[float] = None
    capacity_hint: Optional[int] = None
    polyline: List[Tuple[float, float]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.edge_type.value,
            "start": self.start_node,
            "end": self.end_node,
            "length": self.length,
            "allowed_flow": self.allowed_flow.value,
            "one_way": self.one_way,
            "speed_hint": self.speed_hint,
            "capacity_hint": self.capacity_hint,
            "polyline": self.polyline,
        }
    
    @classmethod
    def from_dict(cls, edge_id: str, data: Dict[str, Any]) -> "Edge":
        """Create Edge from dictionary."""
        return cls(
            id=edge_id,
            edge_type=EdgeType(data.get("type", "taxiway")),
            start_node=data.get("start", ""),
            end_node=data.get("end", ""),
            length=float(data.get("length", 0)),
            allowed_flow=AllowedFlow(data.get("allowed_flow", "both")),
            one_way=data.get("one_way", False),
            speed_hint=data.get("speed_hint"),
            capacity_hint=data.get("capacity_hint"),
            polyline=data.get("polyline", []),
        )


class Layout:
    """
    Airport layout as a graph structure.
    
    The layout contains nodes (intersections, gates, hold points, etc.)
    and edges (runways, taxiways, apron links).
    """
    
    def __init__(self, name: str = "Untitled Layout", version: str = "1.0"):
        self.name = name
        self.version = version
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, Edge] = {}
        
        # Cached adjacency lists for efficient queries
        self._edges_from: Dict[str, List[str]] = {}
        self._edges_to: Dict[str, List[str]] = {}
    
    def add_node(self, node: Node) -> None:
        """Add a node to the layout."""
        self.nodes[node.id] = node
        if node.id not in self._edges_from:
            self._edges_from[node.id] = []
        if node.id not in self._edges_to:
            self._edges_to[node.id] = []
    
    def add_edge(self, edge: Edge) -> None:
        """Add an edge to the layout and update adjacency lists."""
        self.edges[edge.id] = edge
        
        # Update adjacency lists
        if edge.start_node not in self._edges_from:
            self._edges_from[edge.start_node] = []
        self._edges_from[edge.start_node].append(edge.id)
        
        if edge.end_node not in self._edges_to:
            self._edges_to[edge.end_node] = []
        self._edges_to[edge.end_node].append(edge.id)
        
        # For bidirectional edges, add reverse connections
        if not edge.one_way:
            if edge.end_node not in self._edges_from:
                self._edges_from[edge.end_node] = []
            self._edges_from[edge.end_node].append(edge.id)
            
            if edge.start_node not in self._edges_to:
                self._edges_to[edge.start_node] = []
            self._edges_to[edge.start_node].append(edge.id)
    
    def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node by ID."""
        return self.nodes.get(node_id)
    
    def get_edge(self, edge_id: str) -> Optional[Edge]:
        """Get an edge by ID."""
        return self.edges.get(edge_id)
    
    def get_edges_from_node(self, node_id: str) -> List[Edge]:
        """Get all edges starting from a node."""
        edge_ids = self._edges_from.get(node_id, [])
        return [self.edges[eid] for eid in edge_ids if eid in self.edges]
    
    def get_edges_to_node(self, node_id: str) -> List[Edge]:
        """Get all edges ending at a node."""
        edge_ids = self._edges_to.get(node_id, [])
        return [self.edges[eid] for eid in edge_ids if eid in self.edges]
    
    def get_nodes_by_type(self, node_type: NodeType) -> List[Node]:
        """Get all nodes of a specific type."""
        return [n for n in self.nodes.values() if n.node_type == node_type]
    
    def get_edges_by_type(self, edge_type: EdgeType) -> List[Edge]:
        """Get all edges of a specific type."""
        return [e for e in self.edges.values() if e.edge_type == edge_type]
    
    def get_gates(self, apron: Optional[str] = None) -> List[Node]:
        """Get all gate nodes, optionally filtered by apron."""
        gates = self.get_nodes_by_type(NodeType.GATE)
        if apron:
            gates = [g for g in gates if g.apron == apron]
        return gates
    
    def get_hold_points(self) -> List[Node]:
        """Get all hold point nodes."""
        return self.get_nodes_by_type(NodeType.HOLD_POINT)
    
    def get_runway_ends(self) -> List[Node]:
        """Get all runway end nodes."""
        return self.get_nodes_by_type(NodeType.RUNWAY_END)
    
    def get_neighbors(self, node_id: str) -> List[str]:
        """Get IDs of all neighboring nodes."""
        neighbors = set()
        for edge in self.get_edges_from_node(node_id):
            if edge.start_node == node_id:
                neighbors.add(edge.end_node)
            elif not edge.one_way:
                neighbors.add(edge.start_node)
        return list(neighbors)
    
    def calculate_edge_length(self, edge_id: str) -> float:
        """Calculate edge length from node positions if not specified."""
        edge = self.get_edge(edge_id)
        if edge and edge.length > 0:
            return edge.length
        
        if edge:
            start = self.get_node(edge.start_node)
            end = self.get_node(edge.end_node)
            if start and end:
                import math
                return math.sqrt((end.x - start.x)**2 + (end.y - start.y)**2)
        return 0.0
    
    def to_json(self) -> str:
        """Serialize layout to JSON string."""
        data = {
            "name": self.name,
            "version": self.version,
            "nodes": {nid: node.to_dict() for nid, node in self.nodes.items()},
            "edges": {eid: edge.to_dict() for eid, edge in self.edges.items()},
        }
        return json.dumps(data, indent=2)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "nodes": {nid: node.to_dict() for nid, node in self.nodes.items()},
            "edges": {eid: edge.to_dict() for eid, edge in self.edges.items()},
        }
    
    @classmethod
    def from_json(cls, json_str: str) -> "Layout":
        """Deserialize layout from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Layout":
        """Create Layout from dictionary."""
        layout = cls(
            name=data.get("name", "Untitled Layout"),
            version=data.get("version", "1.0"),
        )
        
        # Load nodes
        for node_id, node_data in data.get("nodes", {}).items():
            layout.add_node(Node.from_dict(node_id, node_data))
        
        # Load edges
        for edge_id, edge_data in data.get("edges", {}).items():
            layout.add_edge(Edge.from_dict(edge_id, edge_data))
        
        return layout
    
    def validate(self) -> List[str]:
        """
        Validate the layout for common errors.
        Returns a list of error messages (empty if valid).
        """
        errors = []
        
        # Check that all edge endpoints exist
        for edge_id, edge in self.edges.items():
            if edge.start_node not in self.nodes:
                errors.append(f"Edge {edge_id}: start node '{edge.start_node}' not found")
            if edge.end_node not in self.nodes:
                errors.append(f"Edge {edge_id}: end node '{edge.end_node}' not found")
        
        # Check for at least one runway
        if not self.get_edges_by_type(EdgeType.RUNWAY):
            errors.append("Layout has no runway edges")
        
        # Check for at least one gate
        if not self.get_gates():
            errors.append("Layout has no gate nodes")
        
        # Check for runway ends
        if not self.get_runway_ends():
            errors.append("Layout has no runway end nodes")
        
        return errors


def load_layout(filepath: str) -> Layout:
    """Load a layout from a JSON file."""
    with open(filepath, 'r') as f:
        return Layout.from_json(f.read())


def save_layout(layout: Layout, filepath: str) -> None:
    """Save a layout to a JSON file."""
    with open(filepath, 'w') as f:
        f.write(layout.to_json())
