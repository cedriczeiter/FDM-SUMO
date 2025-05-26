Accompaning code for Bachelor Thesis from Cédric-Yséry Zeiter - ETH Zürich - June 2025

# Gas diffusion model for SUMO traffic simulation
## Introduction
This project contains a gas diffusion model for traffic simulation in SUMO. It was developed for villages in the canton of Uri, Switerland.

## Structure of the repository
- route_matching: Contains code to match routes from other SUMO simulations to the a simulation of an area within.
- simulation_simplified: Contains the diffusion model (runs like this)
- simulation_full_pipline_missing_data: Contains full code used in the thesis. Does not include sensible data and does thus not execute without modification. Here for reference only.

## Instructions

### Running the route matching algotihm
Preparation: Insert instant loop detectors in other SUMO simulation at all entries and exits. Call them by this scheme: 
- `villagename_entry_A`, `villagename_entry_B`, etc. for entering lanes
- `villagename_exit_A`, `villagename_exit_B`, etc. for exiting lanes
1. Insert data from instant loop detectors from another sumo simulation into this folder (see the examples used and recreate similar structure). Also add a file withh the vehicle types used in the simulation. The file should be called `vehicle_types_new.xml`. (see example)
2. (Optional) Go over the Python files and change output file names.
3. Run the bash script `run_sumo_tool.sh'.
Output will be in folder `output` in same format as shown in example. Output contains routes and speeds for all exit lanes at every second in the simulation. If no vehicle has passed, the speed is set to -1.

### Running the simulation for the villages

Villages supported: Erstfeld, Goeschenen, Gurtnellen, Schattdorf, Silenen, Wassen (Uri, Switzerland)

Dates supported: 17.05.2024, 20.06.2024, and 20.11.2024

Note 1: The full pipeline will not be explained here, as it requires a lot of data that cannot be shared. The code is here for reference only.

Note 2: If one wants to simulate other villages or dates, input data needs to be changed. For this, replicate the structure of the current input data. The code supports simulations for any place or date, but needs to be modified. For more details, please contact me.
1. Go into the `simulation_simplified` folder.
2. Uncomment the right lines in the `src/config.py` file. (Date and village)
3. Install all requirments from the `requirements.txt` file.
4. Run the simulation with the command `python3 src/run_sim.py`.