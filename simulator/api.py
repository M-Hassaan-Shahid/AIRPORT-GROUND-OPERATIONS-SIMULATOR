"""
api.py - REST API Layer for Airport Ground Operations Simulator
================================================================

Provides a REST API for running simulations and retrieving results.
Built with Flask for simplicity - can be upgraded to FastAPI if needed.

Endpoints:
- POST /api/simulate - Run a simulation with layout and parameters
- GET /api/layouts - List available layouts
- POST /api/layouts - Save a new layout
- GET /api/params/defaults - Get default parameters
- GET /api/health - Health check

Usage:
    python -m simulator.api  # Starts server on port 5000
"""

import os
import json
import glob
from typing import Dict, Any, List

try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

from .runner import run_simulation
from .layout import Layout
from .params import SimulationParams


# Default paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
LAYOUTS_DIR = os.path.join(DATA_DIR, 'layouts')
PARAMS_DIR = os.path.join(DATA_DIR, 'params')


def create_app() -> 'Flask':
    """Create and configure the Flask application."""
    if not HAS_FLASK:
        raise ImportError("Flask is not installed. Run: pip install flask flask-cors")
    
    app = Flask(__name__)
    CORS(app)  # Enable CORS for React frontend
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        return jsonify({
            "status": "healthy",
            "service": "airport-simulator-api",
            "version": "1.0.0"
        })
    
    @app.route('/api/simulate', methods=['POST'])
    def run_sim():
        """
        Run a simulation with the provided layout and parameters.
        
        Request body:
        {
            "layout": {...},  // Layout JSON object
            "params": {...}   // Parameters JSON object (optional)
        }
        
        Returns:
        {
            "summary": {...},
            "plots": [...],
            "flights": [...]
        }
        """
        try:
            data = request.get_json()
            
            if not data or 'layout' not in data:
                return jsonify({"error": "Missing 'layout' in request body"}), 400
            
            layout_json = json.dumps(data['layout'])
            
            # Use provided params or load defaults
            if 'params' in data and data['params']:
                params_json = json.dumps(data['params'])
            else:
                default_params_path = os.path.join(PARAMS_DIR, 'default.json')
                if os.path.exists(default_params_path):
                    with open(default_params_path, 'r') as f:
                        params_json = f.read()
                else:
                    params_json = json.dumps(SimulationParams().to_dict())
            
            # Run simulation
            result_json = run_simulation(layout_json, params_json)
            result = json.loads(result_json)
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/layouts', methods=['GET'])
    def list_layouts():
        """
        List available saved layouts.
        
        Returns:
        {
            "layouts": [
                {"id": "sample_airport", "name": "Sample Airport", "path": "..."}
            ]
        }
        """
        layouts = []
        
        if os.path.exists(LAYOUTS_DIR):
            for filepath in glob.glob(os.path.join(LAYOUTS_DIR, '*.json')):
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    
                    filename = os.path.basename(filepath)
                    layout_id = os.path.splitext(filename)[0]
                    
                    layouts.append({
                        "id": layout_id,
                        "name": data.get('name', layout_id),
                        "path": filepath,
                        "nodes": len(data.get('nodes', [])),
                        "edges": len(data.get('edges', []))
                    })
                except Exception:
                    pass
        
        return jsonify({"layouts": layouts})
    
    @app.route('/api/layouts/<layout_id>', methods=['GET'])
    def get_layout(layout_id: str):
        """Get a specific layout by ID."""
        filepath = os.path.join(LAYOUTS_DIR, f"{layout_id}.json")
        
        if not os.path.exists(filepath):
            return jsonify({"error": f"Layout '{layout_id}' not found"}), 404
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        return jsonify(data)
    
    @app.route('/api/layouts', methods=['POST'])
    def save_layout():
        """
        Save a new layout.
        
        Request body:
        {
            "id": "my_airport",
            "layout": {...}
        }
        """
        try:
            data = request.get_json()
            
            if not data or 'layout' not in data:
                return jsonify({"error": "Missing 'layout' in request body"}), 400
            
            layout_id = data.get('id', 'unnamed_layout')
            layout_data = data['layout']
            
            # Validate layout
            layout = Layout.from_dict(layout_data)
            errors = layout.validate()
            if errors:
                return jsonify({"error": "Layout validation failed", "details": errors}), 400
            
            # Save to file
            os.makedirs(LAYOUTS_DIR, exist_ok=True)
            filepath = os.path.join(LAYOUTS_DIR, f"{layout_id}.json")
            
            with open(filepath, 'w') as f:
                json.dump(layout_data, f, indent=2)
            
            return jsonify({
                "success": True,
                "message": f"Layout saved as '{layout_id}'",
                "path": filepath
            })
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/params/defaults', methods=['GET'])
    def get_default_params():
        """Get default simulation parameters."""
        default_path = os.path.join(PARAMS_DIR, 'default.json')
        
        if os.path.exists(default_path):
            with open(default_path, 'r') as f:
                data = json.load(f)
            return jsonify(data)
        
        # Return built-in defaults
        return jsonify(SimulationParams().to_dict())
    
    @app.route('/api/params', methods=['POST'])
    def save_params():
        """
        Save simulation parameters.
        
        Request body:
        {
            "id": "my_params",
            "params": {...}
        }
        """
        try:
            data = request.get_json()
            
            if not data or 'params' not in data:
                return jsonify({"error": "Missing 'params' in request body"}), 400
            
            params_id = data.get('id', 'custom_params')
            params_data = data['params']
            
            # Validate params
            SimulationParams.from_dict(params_data)
            
            # Save to file
            os.makedirs(PARAMS_DIR, exist_ok=True)
            filepath = os.path.join(PARAMS_DIR, f"{params_id}.json")
            
            with open(filepath, 'w') as f:
                json.dump(params_data, f, indent=2)
            
            return jsonify({
                "success": True,
                "message": f"Parameters saved as '{params_id}'",
                "path": filepath
            })
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    return app


def run_server(host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
    """Run the API server."""
    app = create_app()
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Airport Simulator API Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    print(f"Starting Airport Simulator API on {args.host}:{args.port}")
    run_server(host=args.host, port=args.port, debug=args.debug)
