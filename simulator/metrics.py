"""
metrics.py - Logging and Plot Data
===================================

Record simulation data and prepare aggregate results for plots.
Returns simple JSON structures for the UI to render.

Metrics collected:
- Aircraft on ground (time series)
- Queue lengths at hold points (time series)
- Runway throughput (operations per time window)
- Taxi times per aircraft
- Wait times at hold points
"""

from typing import Dict, List, Any, Tuple, Optional
import json
import statistics
from .spawning import Aircraft


class MetricsCollector:
    """
    Collects and aggregates simulation data for analysis and visualization.
    
    Time series data is recorded at each step and aggregated into plots.
    Per-aircraft statistics are recorded when flights complete.
    """
    
    def __init__(self):
        # Time series data: metric_name -> list of (time, value)
        self.time_series: Dict[str, List[Tuple[float, float]]] = {
            "aircraft_on_ground": [],
            "departures_on_ground": [],
            "arrivals_on_ground": [],
            "queue_length": [],
            "max_queue_length": [],
            "runways_occupied": [],
        }
        
        # Per-aircraft statistics
        self.completed_flights: List[Dict[str, Any]] = []
        
        # Taxi time distributions
        self.taxi_times: List[float] = []
        self.taxi_times_departure: List[float] = []
        self.taxi_times_arrival: List[float] = []
        
        # Wait times at hold points
        self.wait_times: List[float] = []
        
        # Throughput tracking
        self.throughput_window = 300  # 5 minute windows
        self.completions_by_window: Dict[int, int] = {}
        
        # Event log
        self.events: List[Dict[str, Any]] = []
        
        # Simulation parameters (set during run)
        self.sim_duration: float = 0
        self.start_time: float = 0
    
    def record(self, time: float, observables: Dict[str, Any]) -> None:
        """
        Record a time step's observables.
        
        Args:
            time: Current simulation time
            observables: Dictionary of metrics from model_core step
        """
        # Aircraft counts
        if "aircraft_count" in observables:
            self.time_series["aircraft_on_ground"].append(
                (time, observables["aircraft_count"])
            )
        
        if "departures_count" in observables:
            self.time_series["departures_on_ground"].append(
                (time, observables["departures_count"])
            )
            
        if "arrivals_count" in observables:
            self.time_series["arrivals_on_ground"].append(
                (time, observables["arrivals_count"])
            )
        
        # Queue metrics
        if "queue_length" in observables:
            self.time_series["queue_length"].append(
                (time, observables["queue_length"])
            )
            
        if "max_queue_length" in observables:
            self.time_series["max_queue_length"].append(
                (time, observables["max_queue_length"])
            )
        
        # Runway status
        if "runways_occupied" in observables:
            self.time_series["runways_occupied"].append(
                (time, observables["runways_occupied"])
            )
        
        # Process completed aircraft
        if "completed_aircraft" in observables:
            for aircraft in observables["completed_aircraft"]:
                self.record_flight_completion(aircraft)
    
    def record_flight_completion(self, aircraft: Aircraft) -> None:
        """
        Record stats for a completed flight.
        
        Args:
            aircraft: Completed Aircraft object
        """
        if aircraft.completion_time is None:
            return
            
        duration = aircraft.completion_time - aircraft.spawning_time
        
        stats = {
            "id": aircraft.id,
            "type": "arrival" if aircraft.is_arrival else "departure",
            "class": aircraft.aircraft_class,
            "duration": duration,
            "gate": aircraft.gate_id,
            "spawning_time": aircraft.spawning_time,
            "completion_time": aircraft.completion_time,
        }
        
        # Add taxi time if available
        if hasattr(aircraft, 'taxi_time'):
            stats["taxi_time"] = aircraft.taxi_time
            self.taxi_times.append(aircraft.taxi_time)
            if aircraft.is_arrival:
                self.taxi_times_arrival.append(aircraft.taxi_time)
            else:
                self.taxi_times_departure.append(aircraft.taxi_time)
        else:
            # Use duration as taxi time
            self.taxi_times.append(duration)
            if aircraft.is_arrival:
                self.taxi_times_arrival.append(duration)
            else:
                self.taxi_times_departure.append(duration)
        
        # Track wait time if available
        if hasattr(aircraft, 'wait_time') and aircraft.wait_time:
            stats["wait_time"] = aircraft.wait_time
            self.wait_times.append(aircraft.wait_time)
        
        self.completed_flights.append(stats)
        
        # Track throughput by window
        window_idx = int(aircraft.completion_time // self.throughput_window)
        self.completions_by_window[window_idx] = \
            self.completions_by_window.get(window_idx, 0) + 1
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Compute summary statistics.
        
        Returns:
            Dictionary with aggregated statistics
        """
        total = len(self.completed_flights)
        arrivals = len([f for f in self.completed_flights if f["type"] == "arrival"])
        departures = len([f for f in self.completed_flights if f["type"] == "departure"])
        
        # Duration statistics
        avg_duration = 0
        min_duration = 0
        max_duration = 0
        if total > 0:
            durations = [f["duration"] for f in self.completed_flights]
            avg_duration = statistics.mean(durations)
            min_duration = min(durations)
            max_duration = max(durations)
        
        # Taxi time statistics
        avg_taxi_time = 0
        avg_taxi_time_dep = 0
        avg_taxi_time_arr = 0
        if self.taxi_times:
            avg_taxi_time = statistics.mean(self.taxi_times)
        if self.taxi_times_departure:
            avg_taxi_time_dep = statistics.mean(self.taxi_times_departure)
        if self.taxi_times_arrival:
            avg_taxi_time_arr = statistics.mean(self.taxi_times_arrival)
        
        # Wait time statistics
        avg_wait_time = 0
        max_wait_time = 0
        if self.wait_times:
            avg_wait_time = statistics.mean(self.wait_times)
            max_wait_time = max(self.wait_times)
        
        # Throughput
        throughput_per_hour = 0
        if self.sim_duration > 0:
            throughput_per_hour = total / (self.sim_duration / 3600)
        
        # Queue statistics
        avg_queue = 0
        max_queue = 0
        if self.time_series["queue_length"]:
            queue_values = [v for _, v in self.time_series["queue_length"]]
            avg_queue = statistics.mean(queue_values) if queue_values else 0
            max_queue = max(queue_values) if queue_values else 0
        
        return {
            "total_flights": total,
            "total_arrivals": arrivals,
            "total_departures": departures,
            "avg_duration": round(avg_duration, 2),
            "min_duration": round(min_duration, 2),
            "max_duration": round(max_duration, 2),
            "avg_taxi_time": round(avg_taxi_time, 2),
            "avg_taxi_time_departure": round(avg_taxi_time_dep, 2),
            "avg_taxi_time_arrival": round(avg_taxi_time_arr, 2),
            "avg_wait_time": round(avg_wait_time, 2),
            "max_wait_time": round(max_wait_time, 2),
            "throughput_per_hour": round(throughput_per_hour, 2),
            "avg_queue_length": round(avg_queue, 2),
            "max_queue_length": max_queue,
        }
    
    def _downsample(self, data: List[Tuple[float, float]], 
                    max_points: int = 500) -> List[Tuple[float, float]]:
        """Downsample time series data if too many points."""
        if len(data) <= max_points:
            return data
        step = len(data) // max_points
        return data[::step]
    
    def get_plot_data(self) -> Dict[str, Any]:
        """
        Prepare data for UI plots.
        
        Returns:
            Dictionary with plots array in format expected by UI
        """
        plots = []
        
        # 1. Aircraft on Ground (Line Chart)
        ts = self.time_series["aircraft_on_ground"]
        if ts:
            data = self._downsample(ts)
            plots.append({
                "id": "aircraft_count",
                "type": "line",
                "title": "Aircraft on Ground",
                "x_label": "Time (s)",
                "y_label": "Count",
                "x": [p[0] for p in data],
                "y": [p[1] for p in data]
            })
        
        # 2. Queue Length (Line Chart)
        ts = self.time_series["queue_length"]
        if ts:
            data = self._downsample(ts)
            plots.append({
                "id": "queue_length",
                "type": "line",
                "title": "Hold Queue Length",
                "x_label": "Time (s)",
                "y_label": "Aircraft in Queue",
                "x": [p[0] for p in data],
                "y": [p[1] for p in data]
            })
        
        # 3. Departures vs Arrivals (Line Chart)
        dep_ts = self.time_series["departures_on_ground"]
        arr_ts = self.time_series["arrivals_on_ground"]
        if dep_ts and arr_ts:
            dep_data = self._downsample(dep_ts)
            arr_data = self._downsample(arr_ts)
            plots.append({
                "id": "traffic_mix",
                "type": "line",
                "title": "Traffic Mix",
                "x_label": "Time (s)",
                "y_label": "Count",
                "series": [
                    {
                        "label": "Departures",
                        "x": [p[0] for p in dep_data],
                        "y": [p[1] for p in dep_data]
                    },
                    {
                        "label": "Arrivals",
                        "x": [p[0] for p in arr_data],
                        "y": [p[1] for p in arr_data]
                    }
                ]
            })
        
        # 4. Taxi Time Distribution (Histogram)
        if self.taxi_times:
            # Create histogram bins
            min_val = min(self.taxi_times)
            max_val = max(self.taxi_times)
            num_bins = min(20, len(set(self.taxi_times)))
            if num_bins > 0 and max_val > min_val:
                bin_width = (max_val - min_val) / num_bins
                bins = [0] * num_bins
                bin_labels = []
                for i in range(num_bins):
                    bin_start = min_val + i * bin_width
                    bin_labels.append(f"{bin_start:.0f}")
                    for val in self.taxi_times:
                        if bin_start <= val < bin_start + bin_width:
                            bins[i] += 1
                
                plots.append({
                    "id": "taxi_time_dist",
                    "type": "bar",
                    "title": "Taxi Time Distribution",
                    "x_label": "Taxi Time (s)",
                    "y_label": "Frequency",
                    "x": bin_labels,
                    "y": bins
                })
        
        # 5. Throughput over time (Bar Chart)
        if self.completions_by_window:
            windows = sorted(self.completions_by_window.keys())
            throughputs = [self.completions_by_window[w] for w in windows]
            window_labels = [f"{w * self.throughput_window // 60}m" for w in windows]
            
            plots.append({
                "id": "throughput",
                "type": "bar",
                "title": "Runway Throughput (per 5 min)",
                "x_label": "Time Window",
                "y_label": "Operations",
                "x": window_labels,
                "y": throughputs
            })
        
        return {"plots": plots}
    
    def to_json(self) -> str:
        """
        Export all results as JSON.
        
        Returns:
            JSON string with summary and plots
        """
        return json.dumps({
            "summary": self.get_summary(),
            "plots": self.get_plot_data()["plots"],
            "flights": self.completed_flights[:100],  # Limit to first 100 for size
        }, indent=2)
    
    def to_csv(self, filepath: str) -> None:
        """
        Export completed flights to CSV.
        
        Args:
            filepath: Path to save CSV file
        """
        if not self.completed_flights:
            return
            
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.completed_flights[0].keys())
            writer.writeheader()
            writer.writerows(self.completed_flights)
