"""
params.py - Hyperparameter System
==================================

Central hyperparameter system where each parameter has a mode
(off, fixed, random, realistic) and associated values.
Supports mid-run updates from the UI.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Union
import json
import random


class ParamMode(Enum):
    """Modes for parameter evaluation."""
    OFF = "off"
    FIXED = "fixed"
    RANDOM = "random"
    REALISTIC = "realistic"


class WeatherCondition(Enum):
    """Weather condition types."""
    GOOD = "good"
    MILD = "mild"
    BAD = "bad"


class TrafficMode(Enum):
    """Traffic mode types."""
    DEPARTURES_ONLY = "departures_only"
    ARRIVALS_ONLY = "arrivals_only"
    MIXED = "mixed"


class PriorityMode(Enum):
    """Priority mode for queues and intersections."""
    FIFO = "fifo"
    DEPART_FIRST = "depart_first"
    ARRIVE_FIRST = "arrive_first"
    WEIGHTED = "weighted"
    SIZE_PRIORITY = "size_priority"  # LARGE > MEDIUM > SMALL
    RANDOM = "random"


class AircraftClass(Enum):
    """Aircraft size categories."""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


@dataclass
class Parameter:
    """
    A configurable simulation parameter.
    
    Attributes:
        mode: How the parameter should be evaluated
        value: The fixed value (if mode is FIXED)
        min_val: Minimum value (for RANDOM mode)
        max_val: Maximum value (for RANDOM mode)
        choices: List of choices (for categorical parameters)
    """
    mode: ParamMode = ParamMode.FIXED
    value: Any = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    choices: Optional[List[Any]] = None
    
    def evaluate(self, rng: random.Random = None) -> Any:
        """
        Evaluate the parameter based on its mode.
        
        Args:
            rng: Random number generator for reproducibility
        
        Returns:
            The evaluated value
        """
        if self.mode == ParamMode.OFF:
            return None
        elif self.mode == ParamMode.FIXED:
            return self.value
        elif self.mode == ParamMode.RANDOM:
            if rng is None:
                rng = random.Random()
            if self.choices:
                return rng.choice(self.choices)
            elif self.min_val is not None and self.max_val is not None:
                return rng.uniform(self.min_val, self.max_val)
            return self.value
        elif self.mode == ParamMode.REALISTIC:
            # For realistic mode, value should be a distribution or time-series
            # For now, treat as fixed
            return self.value
        return self.value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "mode": self.mode.value,
            "value": self.value,
            "min_val": self.min_val,
            "max_val": self.max_val,
            "choices": self.choices,
        }
    
    @classmethod
    def from_dict(cls, data: Union[Dict[str, Any], Any]) -> "Parameter":
        """Create Parameter from dictionary or simple value."""
        if isinstance(data, dict) and "mode" in data:
            return cls(
                mode=ParamMode(data.get("mode", "fixed")),
                value=data.get("value"),
                min_val=data.get("min_val"),
                max_val=data.get("max_val"),
                choices=data.get("choices"),
            )
        # Simple value - treat as fixed
        return cls(mode=ParamMode.FIXED, value=data)


@dataclass
class SimulationParams:
    """
    Complete simulation parameters.
    
    All configurable aspects of the simulation are defined here.
    The UI can modify these and send them to the backend as JSON.
    """
    
    # Traffic parameters
    departure_spawn_rate: Parameter = field(default_factory=lambda: Parameter(value=0.5))  # aircraft/minute
    arrival_spawn_rate: Parameter = field(default_factory=lambda: Parameter(value=0.3))  # aircraft/minute
    departure_class_mix: Dict[str, float] = field(default_factory=lambda: {"small": 0.2, "medium": 0.5, "large": 0.3})
    arrival_class_mix: Dict[str, float] = field(default_factory=lambda: {"small": 0.3, "medium": 0.4, "large": 0.3})
    traffic_mode: TrafficMode = TrafficMode.MIXED
    
    # Environment parameters
    weather_condition: Parameter = field(default_factory=lambda: Parameter(value="good"))
    wind_speed: Parameter = field(default_factory=lambda: Parameter(value=0.0))  # m/s
    wind_direction: Parameter = field(default_factory=lambda: Parameter(value=180.0))  # degrees
    
    # Movement parameters - base speeds by aircraft class (m/s)
    speed_base: Dict[str, float] = field(default_factory=lambda: {"small": 5.0, "medium": 6.0, "large": 4.0})
    # Section multipliers
    speed_mult_section: Dict[str, float] = field(default_factory=lambda: {"runway": 1.0, "taxiway": 0.8, "apron": 0.5})
    # Weather multipliers
    speed_mult_weather: Dict[str, float] = field(default_factory=lambda: {"good": 1.0, "mild": 0.9, "bad": 0.7})
    
    # Separation parameters (meters)
    separation_runway: float = 100.0  # N/A - only 1 aircraft allowed, but used for approach/departure
    separation_taxiway: float = 50.0
    separation_apron: float = 30.0
    # Separation weather multipliers
    sep_mult_weather: Dict[str, float] = field(default_factory=lambda: {"good": 1.0, "mild": 1.2, "bad": 1.5})
    
    # Priority parameters
    runway_priority_mode: PriorityMode = PriorityMode.FIFO
    intersection_priority_mode: PriorityMode = PriorityMode.FIFO
    hold_release_priority: PriorityMode = PriorityMode.FIFO
    
    # Capacity parameters
    gate_capacities: Dict[str, int] = field(default_factory=lambda: {"apron_A": 10, "apron_B": 8})
    runway_capacity: int = 1  # Strictly 1 aircraft at a time
    
    # Simulation parameters
    time_step_size: float = 1.0  # seconds
    total_duration: float = 3600.0  # seconds (1 hour)
    random_seed: int = 42
    
    # Internal state
    _rng: random.Random = field(default=None, repr=False, compare=False)
    
    def __post_init__(self):
        """Initialize random number generator."""
        self._rng = random.Random(self.random_seed)
    
    def get_spawn_rate(self, is_arrival: bool, time: float = 0) -> float:
        """Get current spawn rate for arrivals or departures."""
        if self.traffic_mode == TrafficMode.DEPARTURES_ONLY and is_arrival:
            return 0.0
        if self.traffic_mode == TrafficMode.ARRIVALS_ONLY and not is_arrival:
            return 0.0
        
        param = self.arrival_spawn_rate if is_arrival else self.departure_spawn_rate
        return param.evaluate(self._rng) or 0.0
    
    def get_weather(self, time: float = 0) -> str:
        """Get current weather condition."""
        return self.weather_condition.evaluate(self._rng) or "good"
    
    def get_wind(self, time: float = 0) -> tuple:
        """Get current wind speed and direction."""
        speed = self.wind_speed.evaluate(self._rng) or 0.0
        direction = self.wind_direction.evaluate(self._rng) or 0.0
        return (speed, direction)
    
    def get_speed_limit(self, aircraft_class: str, section_type: str, weather: str = None) -> float:
        """
        Calculate speed limit for an aircraft.
        
        Speed = base_speed[class] × section_mult × weather_mult
        """
        if weather is None:
            weather = self.get_weather()
        
        base = self.speed_base.get(aircraft_class, 5.0)
        section_mult = self.speed_mult_section.get(section_type, 1.0)
        weather_mult = self.speed_mult_weather.get(weather, 1.0)
        
        return base * section_mult * weather_mult
    
    def get_separation(self, section_type: str, weather: str = None) -> float:
        """
        Get required separation distance for a section type.
        
        Separation = base_separation × weather_mult
        """
        if weather is None:
            weather = self.get_weather()
        
        if section_type == "runway":
            base = self.separation_runway
        elif section_type == "taxiway":
            base = self.separation_taxiway
        elif section_type == "apron":
            base = self.separation_apron
        else:
            base = self.separation_taxiway
        
        weather_mult = self.sep_mult_weather.get(weather, 1.0)
        return base * weather_mult
    
    def get_aircraft_class_probabilities(self, is_arrival: bool) -> Dict[str, float]:
        """Get size class probabilities for spawning."""
        if is_arrival:
            return self.arrival_class_mix
        return self.departure_class_mix
    
    def sample_aircraft_class(self, is_arrival: bool) -> str:
        """Sample an aircraft class based on probabilities."""
        probs = self.get_aircraft_class_probabilities(is_arrival)
        classes = list(probs.keys())
        weights = list(probs.values())
        return self._rng.choices(classes, weights=weights)[0]
    
    def get_total_gate_capacity(self, apron: str = None) -> int:
        """Get total gate capacity, optionally for a specific apron."""
        if apron:
            return self.gate_capacities.get(apron, 0)
        return sum(self.gate_capacities.values())
    
    def apply_midrun_update(self, updates: Dict[str, Any]) -> None:
        """
        Apply parameter updates during a simulation run.
        
        Only certain parameters can be safely changed mid-run.
        """
        safe_params = [
            "departure_spawn_rate", "arrival_spawn_rate",
            "weather_condition", "wind_speed", "wind_direction",
            "runway_priority_mode", "intersection_priority_mode", "hold_release_priority",
        ]
        
        for key, value in updates.items():
            if key in safe_params:
                if hasattr(self, key):
                    current = getattr(self, key)
                    if isinstance(current, Parameter):
                        if isinstance(value, dict):
                            setattr(self, key, Parameter.from_dict(value))
                        else:
                            current.value = value
                    elif isinstance(current, Enum):
                        # Handle enum updates
                        enum_class = type(current)
                        setattr(self, key, enum_class(value))
                    else:
                        setattr(self, key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "traffic": {
                "departure_spawn_rate": self.departure_spawn_rate.to_dict() if isinstance(self.departure_spawn_rate, Parameter) else self.departure_spawn_rate,
                "arrival_spawn_rate": self.arrival_spawn_rate.to_dict() if isinstance(self.arrival_spawn_rate, Parameter) else self.arrival_spawn_rate,
                "departure_class_mix": self.departure_class_mix,
                "arrival_class_mix": self.arrival_class_mix,
                "traffic_mode": self.traffic_mode.value,
            },
            "environment": {
                "weather_condition": self.weather_condition.to_dict() if isinstance(self.weather_condition, Parameter) else self.weather_condition,
                "wind_speed": self.wind_speed.to_dict() if isinstance(self.wind_speed, Parameter) else self.wind_speed,
                "wind_direction": self.wind_direction.to_dict() if isinstance(self.wind_direction, Parameter) else self.wind_direction,
            },
            "movement": {
                "speed_base": self.speed_base,
                "speed_mult_section": self.speed_mult_section,
                "speed_mult_weather": self.speed_mult_weather,
            },
            "separation": {
                "runway": self.separation_runway,
                "taxiway": self.separation_taxiway,
                "apron": self.separation_apron,
                "weather_mult": self.sep_mult_weather,
            },
            "priority": {
                "runway": self.runway_priority_mode.value,
                "intersection": self.intersection_priority_mode.value,
                "hold_release": self.hold_release_priority.value,
            },
            "capacity": {
                "gates": self.gate_capacities,
                "runway": self.runway_capacity,
            },
            "simulation": {
                "time_step_size": self.time_step_size,
                "total_duration": self.total_duration,
                "random_seed": self.random_seed,
            },
        }
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SimulationParams":
        """Create SimulationParams from dictionary."""
        params = cls()
        
        # Traffic
        if "traffic" in data:
            traffic = data["traffic"]
            if "departure_spawn_rate" in traffic:
                params.departure_spawn_rate = Parameter.from_dict(traffic["departure_spawn_rate"])
            if "arrival_spawn_rate" in traffic:
                params.arrival_spawn_rate = Parameter.from_dict(traffic["arrival_spawn_rate"])
            if "departure_class_mix" in traffic:
                params.departure_class_mix = traffic["departure_class_mix"]
            if "arrival_class_mix" in traffic:
                params.arrival_class_mix = traffic["arrival_class_mix"]
            if "traffic_mode" in traffic:
                params.traffic_mode = TrafficMode(traffic["traffic_mode"])
        
        # Environment
        if "environment" in data:
            env = data["environment"]
            if "weather_condition" in env:
                params.weather_condition = Parameter.from_dict(env["weather_condition"])
            if "wind_speed" in env:
                params.wind_speed = Parameter.from_dict(env["wind_speed"])
            if "wind_direction" in env:
                params.wind_direction = Parameter.from_dict(env["wind_direction"])
        
        # Movement
        if "movement" in data:
            movement = data["movement"]
            if "speed_base" in movement:
                params.speed_base = movement["speed_base"]
            if "speed_mult_section" in movement:
                params.speed_mult_section = movement["speed_mult_section"]
            if "speed_mult_weather" in movement:
                params.speed_mult_weather = movement["speed_mult_weather"]
        
        # Separation
        if "separation" in data:
            sep = data["separation"]
            if "runway" in sep:
                params.separation_runway = sep["runway"]
            if "taxiway" in sep:
                params.separation_taxiway = sep["taxiway"]
            if "apron" in sep:
                params.separation_apron = sep["apron"]
            if "weather_mult" in sep:
                params.sep_mult_weather = sep["weather_mult"]
        
        # Priority
        if "priority" in data:
            priority = data["priority"]
            if "runway" in priority:
                params.runway_priority_mode = PriorityMode(priority["runway"])
            if "intersection" in priority:
                params.intersection_priority_mode = PriorityMode(priority["intersection"])
            if "hold_release" in priority:
                params.hold_release_priority = PriorityMode(priority["hold_release"])
        
        # Capacity
        if "capacity" in data:
            cap = data["capacity"]
            if "gates" in cap:
                params.gate_capacities = cap["gates"]
            if "runway" in cap:
                params.runway_capacity = cap["runway"]
        
        # Simulation
        if "simulation" in data:
            sim = data["simulation"]
            if "time_step_size" in sim:
                params.time_step_size = sim["time_step_size"]
            if "total_duration" in sim:
                params.total_duration = sim["total_duration"]
            if "random_seed" in sim:
                params.random_seed = sim["random_seed"]
                params._rng = random.Random(params.random_seed)
        
        return params
    
    @classmethod
    def from_json(cls, json_str: str) -> "SimulationParams":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


def load_params(filepath: str) -> SimulationParams:
    """Load parameters from a JSON file."""
    with open(filepath, 'r') as f:
        return SimulationParams.from_json(f.read())


def save_params(params: SimulationParams, filepath: str) -> None:
    """Save parameters to a JSON file."""
    with open(filepath, 'w') as f:
        f.write(params.to_json())
