#############################################
# Code by Cédric-Yséry Zeiter
# June 2025
# Part of Bachelor thesis at ETH Zurich
# Supervised by Kevien Riehl
#############################################

#########################################
# Imports
#########################################

import os
import sys
if 'SUMO_HOME' in os.environ:
    sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))
import traci
import numpy as np
import time
import math

from emission_models import process_gas_step, process_noise, calculate_optimal_dt, get_emissions_batched
from helper import get_cell_size, printv, parse_args, save_vec_to_csv, save_all_data
from sumo_commands import startSumo, stopSumo, update_edge_speeds, reroute_vehicles_to_avoid_traffic, add_time_dependent_traffic
from config import GRID_LEFT, GRID_RIGHT, GRID_BOTTOM, GRID_TOP, GRID_DIM_X, GRID_DIM_Y, GRID_DIM_Z, NETWORK_FILE, VERBOSE, FORCE_RECALCULATE, TIME_PER_SCREENSHOT, SHOW_INTERFACE, VILLAGE_NAME, REROUTING_PERIOD, DATE
from post_processing import post_processing_wrapper



#########################################
# Parse command line arguments
#########################################

args = parse_args()

RANDOM_TRAFFIC = bool(args.random_traffic)  
REROUTING_PERCENTAGE = args.rerouting_percentage  
WEEKDAY = bool(args.weekday)  # (0=weekend, 1=weekday)



#########################################
# Print overview of parameters for deubgging
#########################################

printv(f"Current village: {VILLAGE_NAME}", VERBOSE, 'yellow')
printv(f"Rerouting period: {REROUTING_PERIOD}", VERBOSE, 'yellow')
printv(f"Time per screenshot: {TIME_PER_SCREENSHOT}", VERBOSE, 'yellow')
printv(f"Rerouting percentage: {REROUTING_PERCENTAGE}", VERBOSE, 'yellow')
printv(f"Random traffic: {RANDOM_TRAFFIC}", VERBOSE, 'yellow')
printv(f"Weekday: {WEEKDAY}", VERBOSE, 'yellow')
printv(f"Force recalculation: {FORCE_RECALCULATE}", VERBOSE, 'yellow')
printv(f"Network-file: {NETWORK_FILE}", VERBOSE, 'yellow')



#########################################
# Parameters & variables initializing
#########################################

CELL_HEIGHT_Z = 2  # Cell height in meters (can be changed as needed)
SIM_TIME = TIME_PER_SCREENSHOT*24 # How long to run the simulation
CURR_TIME = time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime())# Get the current time

# File Locations
SYNPOP_DATA_FILE = "../../data_cleaned/synpop_clean_enriched.csv" # Path to the synpop data file -> contains information about people (not given in GitHub)
OUTPUT_PATH_TEMP = "../output/temp"  # where the caching files are stored

OUTPUT_PATH = f"../output_{VILLAGE_NAME}_{DATE}_rt_{RANDOM_TRAFFIC}_rp_{REROUTING_PERCENTAGE}_wd_{WEEKDAY}_{CURR_TIME}/"  # where the output files are stored
DATA_FOLDER = f"{OUTPUT_PATH}/data/" # where data from simulation is stored
PLOT_FOLDER = f"{OUTPUT_PATH}/data/plot" # where plots are stored
AVG_DATA_FOLDER = f"{OUTPUT_PATH}/data/avg/" # where average data is stored
FINAL_RESULTS_FOLDER = f"{OUTPUT_PATH}/data/final_results/" # where final results are stored

# Create folders if they do not exist
os.makedirs(OUTPUT_PATH, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)
os.makedirs(PLOT_FOLDER, exist_ok=True)
os.makedirs(AVG_DATA_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_PATH_TEMP, exist_ok=True)
os.makedirs(FINAL_RESULTS_FOLDER, exist_ok=True)

printv("Simulation started", VERBOSE, 'magenta', True)

# Set cell size in metres
cell_len_x_m, cell_len_y_m = get_cell_size(
    grid_left=GRID_LEFT, grid_right=GRID_RIGHT, grid_bottom=GRID_BOTTOM, grid_top=GRID_TOP,
    size_x=GRID_DIM_X, size_y=GRID_DIM_Y, filename=NETWORK_FILE, verbose=True)
cell_len_z_m = CELL_HEIGHT_Z


printv(f"Cell size in metres: x: {cell_len_x_m}, y: {cell_len_y_m}, z: {cell_len_z_m}", VERBOSE, 'yellow')
printv(f"Grid dimensions: {GRID_DIM_X} x {GRID_DIM_Y} x {GRID_DIM_Z}", VERBOSE, 'yellow')
printv(f"Simulation time: {SIM_TIME} seconds, screenshots every {TIME_PER_SCREENSHOT} seconds", VERBOSE, 'yellow')


# Initialize vectors
CO_default_mgm3 = 0.2
PM2_default_mgm3 = 0.006
NO2_default_mgm3 = 0.017

factor = cell_len_x_m * cell_len_y_m * cell_len_z_m  # scale up to the box size

# each global vector is 3D with [mg] per cell
co_vector_global_mgcell = np.zeros((GRID_DIM_X, GRID_DIM_Y, GRID_DIM_Z)) + CO_default_mgm3 * factor
nox_vector_global_mgcell = np.zeros((GRID_DIM_X, GRID_DIM_Y, GRID_DIM_Z)) + NO2_default_mgm3 * factor
pmx_vector_global_mgcell = np.zeros((GRID_DIM_X, GRID_DIM_Y, GRID_DIM_Z)) + PM2_default_mgm3 * factor


# Noise exposure thresholds (in dB)
NOISE_THRESHOLD_LOW = 40  
NOISE_THRESHOLD_MID = 50   
NOISE_THRESHOLD_HIGH = 60  
NOISE_THERESHOLD_VERY_HIGH = 70

# Counters for number of seconds above threshold
noise_exposure_low = np.zeros((GRID_DIM_X, GRID_DIM_Y), dtype=np.int32)
noise_exposure_mid = np.zeros((GRID_DIM_X, GRID_DIM_Y), dtype=np.int32)
noise_exposure_high = np.zeros((GRID_DIM_X, GRID_DIM_Y), dtype=np.int32)
noise_exposure_very_high = np.zeros((GRID_DIM_X, GRID_DIM_Y), dtype=np.int32)


#########################################
# The simulation
#########################################

# assumptions for random traffic generation -> in original code based on population data
population_with_car, working_population, inactive_population = 1100, 1500, 300

#simulation constants
diffusion_CO = 5.0 # [m^2/s]
diffusion_nox = 5.0 # [m^2/s]
diffusion_pmx = 15.0 # [m^2/s]

loss_rate_co = 0.0  
loss_rate_nox = 0.0  
loss_rate_pmx = 0.001  # [1/s] -> loss rate of PM2.5

# Calculate timestep dt based on diffusion and loss rates using CFL condition (worst-case scenario)
dt = calculate_optimal_dt(
    cell_len_x_m=cell_len_x_m,
    cell_len_y_m=cell_len_y_m,
    cell_len_z_m=cell_len_z_m,
    diffusion=max(diffusion_CO, diffusion_nox, diffusion_pmx),
    loss_rate=max(loss_rate_co, loss_rate_nox, loss_rate_pmx),
    safety_factor=0.8  # 20% safety margin
)

# Ensure dt is a value that can evenly divide 1.0 (i.e., dt = 1/n for integer n) -> prevents stepping over second boundaries
n = math.ceil(1/dt)  # Find smallest integer n such that 1/n <= dt
dt = 1/n  # Set dt to this fraction

# Cap dt at 1 second to prevent excessive simulation time (maybe redundant)
dt = min(dt, 1)  # Cap at 1 second
printv(f"Using auto-calculated timestep dt = {dt} seconds", VERBOSE, "yellow")

# Floatingpoint safe modulo scheme
next_screenshot_time = TIME_PER_SCREENSHOT
next_rerouting_time = REROUTING_PERIOD
next_noise_update = 1.0


startSumo(200, GRID_LEFT, GRID_TOP, visual_interface=SHOW_INTERFACE, verbose=VERBOSE, dt=dt)

while traci.simulation.getTime() <= SIM_TIME:

    curr_time = traci.simulation.getTime()
    traci.simulationStep()

    #########################################
    # Update edge speeds
    #########################################
    update_edge_speeds(curr_time)

    #########################################
    # Random traffic generation
    #########################################
    try:
        if RANDOM_TRAFFIC:
            add_time_dependent_traffic(WEEKDAY, curr_time, dt, population_with_car, working_population, inactive_population) # adds random traffic to the simulation
    except Exception as e:
        print(f"Error adding traffic: {e}")

    vehicle_ids = list(traci.vehicle.getIDList()) # get vehicles after spawning new ones

    #########################################
    # Reroute vehicles to avoid traffic jams
    #########################################
    # reroute a specific percentage of vehicles every REROUTING_PERIOD seconds
    if next_rerouting_time <= curr_time:
        next_rerouting_time += REROUTING_PERIOD
        if abs(REROUTING_PERCENTAGE) > 0.000001: # floating point safe check, to see if percentage is not zero
            reroute_vehicles_to_avoid_traffic(REROUTING_PERCENTAGE, vehicle_ids)

    #########################################
    # Add emissions from vehicles and diffuse pollutants
    #########################################        
    # get emissions from vehicles
    x_vec, y_vec, co_vec, nox_vec, pmx_vec, noise_vec = get_emissions_batched(vehicle_ids, dt)

    # diffusion and loss of pollutants
    co_vector_global_mgcell = process_gas_step(old_matrix=co_vector_global_mgcell, x_vec=x_vec, y_vec=y_vec, emission_vec=co_vec,
                                               cell_len_y_m=cell_len_y_m, cell_len_x_m=cell_len_x_m, cell_len_z_m=cell_len_z_m, default_value=CO_default_mgm3, diffusion=diffusion_CO, loss_rate=loss_rate_co, dt=dt)
    nox_vector_global_mgcell = process_gas_step(old_matrix=nox_vector_global_mgcell, x_vec=x_vec, y_vec=y_vec, emission_vec=nox_vec,
                                                cell_len_y_m=cell_len_y_m, cell_len_x_m=cell_len_x_m, cell_len_z_m=cell_len_z_m, default_value=NO2_default_mgm3, diffusion=diffusion_nox, loss_rate=loss_rate_nox, dt=dt)
    pmx_vector_global_mgcell = process_gas_step(old_matrix=pmx_vector_global_mgcell, x_vec=x_vec, y_vec=y_vec, emission_vec=pmx_vec,
                                                cell_len_y_m=cell_len_y_m, cell_len_x_m=cell_len_x_m, cell_len_z_m=cell_len_z_m, default_value=PM2_default_mgm3, diffusion=diffusion_pmx,  loss_rate=loss_rate_pmx, dt=dt)

    #########################################
    # Every second, process noise exposure and add to binary counters
    #########################################    
    if next_noise_update <= curr_time:
        next_noise_update += 1.0
        
        # Calculate current noise grid
        current_noise_grid = process_noise(x_vec=x_vec, y_vec=y_vec, noise_vec=noise_vec, cell_len_x_m=cell_len_x_m, cell_len_y_m=cell_len_y_m)
        
        noise_exposure_low += (current_noise_grid >= NOISE_THRESHOLD_LOW).astype(np.int32)
        noise_exposure_mid += (current_noise_grid >= NOISE_THRESHOLD_MID).astype(np.int32)
        noise_exposure_high += (current_noise_grid >= NOISE_THRESHOLD_HIGH).astype(np.int32)
        noise_exposure_very_high += (current_noise_grid >= NOISE_THERESHOLD_VERY_HIGH).astype(np.int32)

    #########################################
    # Take screenshot of data every TIME_PER_SCREENSHOT seconds
    #########################################  
    if next_screenshot_time <= curr_time:
        next_screenshot_time += TIME_PER_SCREENSHOT
        printv(f"Taking screenshot at time {curr_time} seconds of total {SIM_TIME}", VERBOSE, "yellow")
        noise_grid = process_noise(x_vec=x_vec, y_vec=y_vec, noise_vec=noise_vec, cell_len_x_m=cell_len_x_m, cell_len_y_m=cell_len_y_m)

        save_all_data(co_vector_global=co_vector_global_mgcell, 
              nox_vector_global=nox_vector_global_mgcell,
              pmx_vector_global=pmx_vector_global_mgcell, 
              noise_vector=noise_grid, 
              folder_path=DATA_FOLDER, 
              identifier=f"{curr_time}",
              cell_len_x_m=cell_len_x_m, 
              cell_len_y_m=cell_len_y_m, 
              cell_len_z_m=cell_len_z_m)
        

printv("Saving noise threshold data to CSV files", VERBOSE, "yellow")
save_vec_to_csv(noise_exposure_low, DATA_FOLDER, f"noise_exposure_{NOISE_THRESHOLD_LOW}db.csv")
save_vec_to_csv(noise_exposure_mid, DATA_FOLDER, f"noise_exposure_{NOISE_THRESHOLD_MID}db.csv") 
save_vec_to_csv(noise_exposure_high, DATA_FOLDER, f"noise_exposure_{NOISE_THRESHOLD_HIGH}db.csv")
save_vec_to_csv(noise_exposure_very_high, DATA_FOLDER, f"noise_exposure_{NOISE_THERESHOLD_VERY_HIGH}db.csv")


#########################################
# End the simulation
#########################################
stopSumo()


#########################################
# Post-processing of information
#########################################

post_processing_wrapper(data_folder=DATA_FOLDER, plot_folder=PLOT_FOLDER, avg_data_folder=AVG_DATA_FOLDER, final_results_folder=FINAL_RESULTS_FOLDER, verbose=VERBOSE)
