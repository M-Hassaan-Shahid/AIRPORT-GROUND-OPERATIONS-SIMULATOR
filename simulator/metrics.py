"""
metrics.py - Logging and Plot Data
===================================

Record simulation data and prepare aggregate results for plots.
Returns simple JSON structures for the UI to render.
"""

from typing import Dict, List, Any
import json
import csv
from .spawning import Aircraft


class MetricsCollector:
    """
    Collects and aggregates simulation data.
    """
    
    def __init__(self):
        # Time series data: metric_name -> list of (time, value)
        self.time_series: Dict[str, List[Tuple[float, float]]] = {
            "aircraft_on_ground": [],
            "queue_length_max": [],
            "runway_throughput": [], # ops per window
        }
        
        # Per-aircraft statistics
        self.completed_flights: List[Dict[str, Any]] = []
        
        # Event log
        self.events: List[Dict[str, Any]] = []
    
    def record(self, time: float, observables: Dict[str, Any]) -> None:
        """Record a time step's observables."""
        
        if "aircraft_count" in observables:
            self.time_series["aircraft_on_ground"].append((time, observables["aircraft_count"]))
            
        # Add more metrics here
    
    def record_flight_completion(self, aircraft: Aircraft) -> None:
        """Record stats for a completed flight."""
        stats = {
            "id": aircraft.id,
            "type": "arrival" if aircraft.is_arrival else "departure",
            "class": aircraft.aircraft_class,
            "duration": aircraft.completion_time - aircraft.spawning_time,
            "gate": aircraft.gate_id
        }
        self.completed_flights.append(stats)
    
    def get_summary(self) -> Dict[str, Any]:
        """Compute summary statistics."""
        total = len(self.completed_flights)
        arrivals = len([f for f in self.completed_flights if f["type"] == "arrival"])
        departures = len([f for f in self.completed_flights if f["type"] == "departure"])
        
        avg_duration = 0
        if total > 0:
            avg_duration = sum(f["duration"] for f in self.completed_flights) / total
            
        return {
            "total_flights": total,
            "total_arrivals": arrivals,
            "total_departures": departures,
            "avg_duration": avg_duration
        }
    
    def get_plot_data(self) -> Dict[str, Any]:
        """
        Prepare data for UI plots.
        Format: {"plots": [{"type": "line", "x": [...], "y": [...], "label": "..."}]}
        """
        plots = []
        
        # Aircraft on Ground Plot
        ts = self.time_series["aircraft_on_ground"]
        if ts:
            # Downsample if too many points
            step = max(1, len(ts) // 500)
            data = ts[::step]
            
            plots.append({
                "id": "aircraft_count",
                "type": "line",
                "title": "Aircraft on Ground",
                "x_label": "Time (s)",
                "y_label": "Count",
                "x": [p[0] for p in data],
                "y": [p[1] for p in data]
            })
            
        return {"plots": plots}
    
    def to_json(self) -> str:
        """Export all results as JSON."""
        return json.dumps({
            "summary": self.get_summary(),
            "plots": self.get_plot_data()["plots"]
        }, indent=2)
