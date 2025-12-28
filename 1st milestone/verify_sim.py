import sys
import os
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from simulator import run_simulation

def verify():
    print("Loading sample data...")
    try:
        with open('data/layouts/sample_airport.json', 'r') as f:
            layout_json = f.read()
        
        with open('data/params/default.json', 'r') as f:
            params_json = f.read()
            
        print("Running simulation...")
        results = run_simulation(layout_json, params_json)
        
        # Check results
        data = json.loads(results)
        
        if "error" in data:
            print(f"FAILED with error: {data['error']}")
            print(data['traceback'])
            return False
            
        summary = data.get("summary", {})
        print("\nSIMULATION RESULTS:")
        print(f"Total Flights: {summary.get('total_flights')}")
        print(f"Arrivals: {summary.get('total_arrivals')}")
        print(f"Departures: {summary.get('total_departures')}")
        print(f"Avg Duration: {summary.get('avg_duration'):.2f}s")
        
        plots = data.get("plots", [])
        print(f"\nGenerated {len(plots)} plots.")
        for p in plots:
             print(f"- {p.get('title')} ({len(p.get('x', []))} points)")
             
        # Check if we actually simulated something
        if len(data.get("plots", [])[0].get("x", [])) > 0:
            print("\nSUCCESS: Simulation ran and produced data.")
            return True
        else:
            print("\nWARNING: Simulation ran but produced no data points.")
            return False
            
    except Exception as e:
        print(f"FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    verify()
