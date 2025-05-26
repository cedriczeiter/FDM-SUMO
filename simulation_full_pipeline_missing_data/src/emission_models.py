#############################################
# Code by Cédric-Yséry Zeiter
# June 2025
# Part of Bachelor thesis at ETH Zurich
# Supervised by Kevien Riehl
#############################################

#########################################
# Imports
#########################################  

import numpy as np
import os
import sys
if 'SUMO_HOME' in os.environ:
    sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))
import traci
import numba as nb

from config import GRID_LEFT, GRID_RIGHT, GRID_BOTTOM, GRID_TOP, GRID_DIM_X, GRID_DIM_Y, GRID_DIM_Z
from helper import printv

#########################################
# Numba JIT Compilation -> optimize performance
#########################################  

@nb.jit(nopython=True)
def _process_diffusion(old_matrix, padded, dx2, dy2, dz2, diffusion, loss_rate, default_value, dt, V):
    """Combined function that processes all diffusion steps in one optimized pass"""
    x_dim, y_dim, z_dim = old_matrix.shape
    
    # Convert to concentration
    for i in range(x_dim):
        for j in range(y_dim):
            for k in range(z_dim):
                padded[i+1, j+1, k+1] = old_matrix[i, j, k] / V
    
    # Apply no-flux boundary at bottom
    for i in range(padded.shape[0]):
        for j in range(padded.shape[1]):
            padded[i, j, 0] = padded[i, j, 1]
    
    # Calculate diffusion coefficients
    diff_x = diffusion / dx2
    diff_y = diffusion / dy2
    diff_z = diffusion / dz2
    
    # Process diffusion and update in single pass to avoid extra array allocations
    for i in range(x_dim):
        for j in range(y_dim):
            for k in range(z_dim):
                # Calculate diffusion change
                diff_change = (
                    diff_x * (padded[i+2,j+1,k+1] + padded[i,j+1,k+1] - 2*padded[i+1,j+1,k+1]) +
                    diff_y * (padded[i+1,j+2,k+1] + padded[i+1,j,k+1] - 2*padded[i+1,j+1,k+1]) +
                    diff_z * (padded[i+1,j+1,k+2] + padded[i+1,j+1,k] - 2*padded[i+1,j+1,k+1])
                )
                
                # Apply change directly to the matrix
                old_matrix[i,j,k] += dt * V * diff_change - dt * loss_rate * old_matrix[i,j,k]
                
                # Ensure no value below default
                if old_matrix[i,j,k] < default_value * V:
                    old_matrix[i,j,k] = default_value * V
    
    return old_matrix

@nb.jit(nopython=True)
def _add_emissions(old_matrix, x_indices, y_indices, emissions, grid_dim_x, grid_dim_y):
    """Add emissions to the matrix efficiently"""
    for i in range(len(x_indices)):
        x_idx = x_indices[i]
        y_idx = y_indices[i]
        if 0 <= x_idx < grid_dim_x and 0 <= y_idx < grid_dim_y:
            old_matrix[x_idx, y_idx, 0] += emissions[i]
    return old_matrix


#########################################
# Preallocate padded concentration matrix
#########################################  

padded_shape = (GRID_DIM_X + 2, GRID_DIM_Y + 2, GRID_DIM_Z + 2)
padded_concentration = np.zeros(padded_shape)


#########################################
# Functions
#########################################  

def process_gas_step(old_matrix, x_vec, y_vec, emission_vec, cell_len_x_m, cell_len_y_m, cell_len_z_m, default_value, diffusion, loss_rate=0, verbose=False, dt=1):
    """
    Processes a single step of gas emissions and diffusion in the grid.
    Args:
        old_matrix (3D numpy array): Current gas concentration matrix
        x_vec (1D array): x positions of the new emissions in SUMO coords
        y_vec (1D array): y positions of the new emissions in SUMO coords
        emission_vec (1D array): Emission values at the corresponding positions
        cell_len_x_m (float): Real size of the grid cells in x-direction [m]
        cell_len_y_m (float): Real size of the grid cells in y-direction [m]
        cell_len_z_m (float): Real size of the grid cells in z-direction [m]
        default_value (float): Default value for gas concentration
        diffusion (float): Diffusion coefficient [m²/s]
        loss_rate (float): Loss rate coefficient [1/s]
        verbose (bool): If more information should be printed.
        dt (float): Time step length [seconds]
    Returns:
        3D numpy array: Updated gas concentration matrix after processing emissions and diffusion
    """
    printv("Start function process_gas_step", verbose=verbose)

    V = cell_len_x_m * cell_len_y_m * cell_len_z_m  # m³

    # Size of each cell in the grid in SUMO coordinates
    cell_dim_x = (GRID_RIGHT - GRID_LEFT) / GRID_DIM_X
    cell_dim_y = (GRID_TOP - GRID_BOTTOM) / GRID_DIM_Y

    # Add new emissions if available
    if len(x_vec) > 0:
        # Convert to numpy arrays and calculate indices
        x_vec_array = np.array(x_vec, dtype=np.float64)
        y_vec_array = np.array(y_vec, dtype=np.float64)
        emission_vec_array = np.array(emission_vec, dtype=np.float64)
        
        # Convert SUMO coordinates to grid indices
        x_indices = ((x_vec_array - GRID_LEFT) / cell_dim_x).astype(np.int32)
        y_indices = ((y_vec_array - GRID_BOTTOM) / cell_dim_y).astype(np.int32)
        
        old_matrix = _add_emissions(old_matrix, x_indices, y_indices, emission_vec_array, GRID_DIM_X, GRID_DIM_Y)
    
    # Cell dimensions squared for diffusion calculation
    dx2 = cell_len_x_m * cell_len_x_m
    dy2 = cell_len_y_m * cell_len_y_m
    dz2 = cell_len_z_m * cell_len_z_m

    # Reset padded array (preallocated for performance)
    global padded_concentration
    padded_concentration.fill(default_value)
    
    # Process diffusion in a single optimized step
    old_matrix = _process_diffusion(old_matrix, padded_concentration, dx2, dy2, dz2, diffusion, loss_rate, default_value, dt, V)
    
    return old_matrix


def process_noise(x_vec, y_vec, noise_vec, cell_len_x_m, cell_len_y_m, radius=500, background_dB=30, verbose=False):
    """
    Simulates how noise is perceived based on spherical sound propagation physics.

    Args:
        x_vec (1D array): x positions of the new emissions in SUMO coords
        y_vec (1D array): y positions of the new emissions in SUMO coords
        noise_vec (1D array): how much noise emitted at timepoint [dB]
        cell_len_x, cell_len_y (float): real size of the grid cells [m]
        radius (float): cutoff-radius of the noise source (for performance reasons dont calculate noise up to every cell in grid) [m]
        background_dB (float): background noise level [dB]
        verbose (bool): If more information should be printed.

    Returns:
        2D numpy array: Noise levels in the grid on ground level [dB]
    """
    printv("Start function process_noise", verbose=verbose)
    
    # Calculate cell dimensions for coordinate conversion
    cell_dim_x = (GRID_RIGHT - GRID_LEFT) / GRID_DIM_X
    cell_dim_y = (GRID_TOP - GRID_BOTTOM) / GRID_DIM_Y

    # Initialize with background noise (in linear scale)
    background_linear = 10 ** (background_dB/10)
    linear_matrix = np.ones((GRID_DIM_X, GRID_DIM_Y)) * background_linear
    
    printv(f"Grid dimensions: {GRID_DIM_X}x{GRID_DIM_Y}, Cell sizes: {cell_len_x_m}m x {cell_len_y_m}m", verbose=verbose)
    
    # Process each noise source
    for i in range(len(x_vec)):
        # Convert SUMO coordinates to grid indices
        x_idx = int((x_vec[i] - GRID_LEFT) / cell_dim_x)
        y_idx = int((y_vec[i] - GRID_BOTTOM) / cell_dim_y)
        
        # Skip if outside grid
        if not (0 <= x_idx < GRID_DIM_X and 0 <= y_idx < GRID_DIM_Y):
            continue
            
        # Get source power level - make sure it's above background
        Lw = max(noise_vec[i], background_dB) 
        
        # Find the cells within the radius for better performance -> create a bounding box
        x_min = max(0, x_idx - int(radius / cell_len_x_m))
        x_max = min(GRID_DIM_X, x_idx + int(radius / cell_len_x_m) + 1)
        y_min = max(0, y_idx - int(radius / cell_len_y_m))
        y_max = min(GRID_DIM_Y, y_idx + int(radius / cell_len_y_m) + 1)
        
        # Process only cells within the bounding box
        for x in range(x_min, x_max):
            for y in range(y_min, y_max):
                # Calculate distance squared in physical meters
                dx = (x - x_idx) * cell_len_x_m
                dy = (y - y_idx) * cell_len_y_m
                dist_squared_m = dx*dx + dy*dy
                
                # Skip if outside radius
                if dist_squared_m > radius*radius:
                    continue
                    
                # Surface area for spherical propagation (S = 4πr²)
                S = 4 * np.pi * max(dist_squared_m, 1.0)  # 1m minimum distance
                
                # Apply spherical spreading law: Lp = Lw - 10*log10(S)
                Lp = Lw - 10 * np.log10(S)
                
                # Convert to linear scale and add contribution
                linear_contribution = 10 ** (Lp/10)
                linear_matrix[x, y] += linear_contribution
    
    # Convert back to dB scale using logarithmic formula
    result = 10 * np.log10(linear_matrix)
    
    return result


def calculate_optimal_dt(cell_len_x_m, cell_len_y_m, cell_len_z_m, diffusion, loss_rate=0, safety_factor=0.8, verbose=False):
    """Calculate the maximum stable timestep for diffusion simulation with safety margin.
    
    Args:
        cell_len_x_m, cell_len_y_m, cell_len_z_m: Cell dimensions in meters
        diffusion: Diffusion coefficient [m²/s]
        loss_rate: Loss rate coefficient [1/s]
        safety_factor: Factor to apply to max timestep (0-1) for stability margin
        verbose (bool): If more information should be printed.
        
    Returns:
        float: Optimal timestep in seconds
    """
    printv("Start function calculate_optimal_dt", verbose=verbose, decorate=True)


    # Calculate diffusion coefficients
    diff_x = diffusion / (cell_len_x_m * cell_len_x_m)  # [1/s]
    diff_y = diffusion / (cell_len_y_m * cell_len_y_m)  # [1/s]
    diff_z = diffusion / (cell_len_z_m * cell_len_z_m)  # [1/s]
    
    # Calculate maximum stable dt per CFL condition
    max_stable_dt = 2.0 / (loss_rate + 4 * (diff_x + diff_y + diff_z))
    
    # Apply safety factor to avoid being right at stability limit
    optimal_dt = max_stable_dt * safety_factor
    
    return optimal_dt


def get_emissions_batched(vehicle_ids, dt, verbose=False):
    """Get all vehicle data in a single batch using subscriptions
    
    Args:
        vehicle_ids (list): List of vehicle IDs to retrieve data for
        dt (float): Time step length [s]
        verbose (bool): If more information should be printed.
    Returns:
        tuple: Lists of x, y positions and emissions (CO, NOx, PMx, noise)
    
    """

    printv("Start function get_emissions_batched", verbose=verbose, decorate=True)

    # Data containers
    x_vec = []
    y_vec = []
    co_vec = []
    nox_vec = []
    pmx_vec = []
    noise_vec = []
    
    # Set up subscription for all vehicles at once
    for vehicle_id in vehicle_ids:
        traci.vehicle.subscribe(vehicle_id, [
            traci.constants.VAR_POSITION,
            traci.constants.VAR_COEMISSION,
            traci.constants.VAR_NOXEMISSION,
            traci.constants.VAR_PMXEMISSION,
            traci.constants.VAR_NOISEEMISSION
        ])
    
    # Retrieve all data with one socket call per vehicle (instead of 5)
    for vehicle_id in vehicle_ids:
        result = traci.vehicle.getSubscriptionResults(vehicle_id)
        if result is None:  # Handle potential None result
            continue
            
        position = result[traci.constants.VAR_POSITION]
        x_vec.append(position[0])
        y_vec.append(position[1])
        co_vec.append(result[traci.constants.VAR_COEMISSION] * dt)
        nox_vec.append(result[traci.constants.VAR_NOXEMISSION] * dt)
        pmx_vec.append(result[traci.constants.VAR_PMXEMISSION] * dt)
        noise_vec.append(result[traci.constants.VAR_NOISEEMISSION])
    
    return x_vec, y_vec, co_vec, nox_vec, pmx_vec, noise_vec
