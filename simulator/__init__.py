"""
Airport Ground Operations Simulator
====================================

A research-grade Python simulation engine for airport ground traffic.
Models aircraft taxiing, queueing, and interactions using a discrete-time
cellular automaton approach.

Main API:
    from simulator import run_simulation
    results = run_simulation(layout_json, params_json)
"""

from .runner import run_simulation
from .layout import Layout, Node, Edge, NodeType, EdgeType
from .params import SimulationParams, ParamMode
from .model_core import SimulationState, init_state, step

__version__ = "1.0.0"
__all__ = [
    "run_simulation",
    "Layout",
    "Node", 
    "Edge",
    "NodeType",
    "EdgeType",
    "SimulationParams",
    "ParamMode",
    "SimulationState",
    "init_state",
    "step",
]
