Milestone 1 Deliverables
========================

Objective:
"Set up the project architecture, convert the notebook logic into a clean modular structure, define the airport layout/parameter formats, and get a basic end-to-end simulation loop running."

Included Files & folders:
-------------------------

1. simulator/ (The Modular Backend Code)
   - Contains the converted Python logic organized into modules:
   - layout.py    : Airport graph data structure.
   - params.py    : Configurable simulation parameters.
   - runner.py    : The core simulation loop orchestrator.
   - rules.py     : Movement and priority rules.
   - routing.py   : Pathfinding logic.
   - ...and other core modules.

2. data/ (Data Formats)
   - Contains the JSON Schemas defining the interface between UI and Backend.
   - sample_airport.json : Example layout file.

3. verify_sim.py (Verification)
   - A ready-to-run script that validates the end-to-end simulation loop.
   - Run this to see the backend generating traffic and collecting results.

4. ui/ (Frontend Source Code)
   - The React-based user interface source code.
   - Includes the Path Builder (updated to export compatible JSON) and Simulation screens.
   - Note: 'node_modules' is excluded to keep the delivery clean. Run 'npm install' inside this folder to setup dependencies.

Instructions:
-------------
To verify the backed loop:
1. Open a terminal in this folder.
2. Run: python verify_sim.py
3. You will see the simulation steps execution and final metrics output.

To run the Frontend:
1. Go to ui/ folder: cd ui
2. Install dependencies: npm install
3. Start dev server: npm run dev
