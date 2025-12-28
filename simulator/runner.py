"""
runner.py - Main Simulation Orchestrator
=========================================

Entry point for running simulations.
Orchestrates the simulation loop, integrates all modules, and returns results.
"""

from typing import Dict, Any, Optional
import json
import traceback

from .layout import Layout
from .params import SimulationParams
from . import rules
from . import capacity
from . import routing
from . import spawning
from . import metrics
from . import model_core


def run_simulation(layout_json: str, params_json: str) -> str:
    """
    Run a simulation with the given layout and parameters.
    
    Args:
        layout_json: JSON string of airport layout
        params_json: JSON string of simulation parameters
        
    Returns:
        JSON string containing results (summary, plots, etc.)
    """
    try:
        # 1. Load configuration
        layout = Layout.from_json(layout_json)
        params = SimulationParams.from_json(params_json)
        
        # Validate layout
        errors = layout.validate()
        if errors:
            return json.dumps({
                "error": "Layout validation failed",
                "details": errors
            }, indent=2)
        
        # 2. Initialize subsystems
        capacity_state = capacity.CapacityState()
        capacity_state.initialize_from_layout(layout, params)
        
        router = routing.Router(layout)
        router.precompute_routes()
        
        metrics_collector = metrics.MetricsCollector()
        metrics_collector.sim_duration = params.total_duration
        metrics_collector.start_time = 0
        
        # 3. Initialize Core State
        state = model_core.init_state(layout, params)
        
        # 4. Main Simulation Loop
        dt = params.time_step_size
        total_steps = int(params.total_duration / dt)
        
        for step_idx in range(total_steps):
            current_time = state.time
            
            # A. Update Environment (Wind/Weather)
            # Weather effects are handled in params.get_speed_limit etc.
            
            # B. Spawn Traffic
            new_departures = spawning.spawn_departures(
                layout, params, capacity_state, router, current_time, dt
            )
            state.aircraft.extend(new_departures)
            
            # Add initial edge occupancy for new departures
            for ac in new_departures:
                if ac.route and ac.route.edges:
                    capacity_state.add_to_edge(ac.id, ac.route.edges[0])
            
            new_arrivals = spawning.spawn_arrivals(
                layout, params, capacity_state, router, current_time, dt
            )
            state.aircraft.extend(new_arrivals)
            
            # Add initial edge occupancy for new arrivals
            for ac in new_arrivals:
                if ac.route and ac.route.edges:
                    capacity_state.add_to_edge(ac.id, ac.route.edges[0])
            
            # C. Step Model Core (Movement with NaSch CA rules)
            state, observables = model_core.step(
                state, layout, params, capacity_state, dt
            )
            
            # D. Collect Metrics (completed aircraft handled in observables)
            metrics_collector.record(current_time, observables)
        
        # 5. Build Results
        return metrics_collector.to_json()
        
    except Exception as e:
        # Return error as JSON
        result = {
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        return json.dumps(result, indent=2)

if __name__ == "__main__":
    # Test run
    # Would need dummy json strings
    print("Use import to run simulation.")
