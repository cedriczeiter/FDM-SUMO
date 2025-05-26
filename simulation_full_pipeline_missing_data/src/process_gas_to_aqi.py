#############################################
# Code by Cédric-Yséry Zeiter
# June 2025
# Part of Bachelor thesis at ETH Zurich
# Supervised by Kevien Riehl
#############################################

#########################################
# Imports
#########################################  

import pandas as pd
import glob
import os
import numpy as np

from helper import printv, save_vec_to_csv, mg_per_m3_to_ppm
from config import GRID_DIM_X, GRID_DIM_Y



#########################################
# Functions
#########################################  

def process_gas_to_aqi(final_results_folder, processed_data_folder, verbose=False):
    """
    Process all emission data to calculate AQI scores based on
    different time averages (hourly, 8-hour, and 24-hour)

    Args:
        final_results_folder: Path to folder where final results will be saved
        processed_data_folder: Path to folder where processed data will be saved
        verbose: Whether to print verbose output
    """
    printv("Start function process_gas_to_aqi",
           verbose=verbose, color="cyan", decorate=True)

    # Save conversion factors for different pollutants
    pollutant_config = {
        "co": {"pattern": "_8h_avg_from_hour", "conversion_factor_us_AQI": mg_per_m3_to_ppm(28.01), "conversion_factor_AQIH":1e3}, #from mg/m3 to ppm, using CO molecular weight 28.01 g/mol
        "nox": {"pattern": "_1h_avg_hour", "conversion_factor_us_AQI": mg_per_m3_to_ppm(46.01)*1000, "conversion_factor_AQIH":1e3}, #from mg/m3 to ppb, using NO2 molecular weight 46.01 g/mol -> 1000 to convert to ppb
        "pmx": {"pattern": "_24h_avg_from_hour", "conversion_factor_us_AQI": 1e3, "conversion_factor_AQIH":1e3} #from mg/m3 to μg/m³
    }



    #########################################
    # Calcualte AQI for US (EPA)
    #########################################  

    # Dictionary to store AQI values for each pollutant
    all_aqi_data_US = {}

    # Process each pollutant for US AQI
    for pollutant, config in pollutant_config.items():
        printv(f"Processing {pollutant} AQI with {config['pattern']} pattern...",
               verbose=verbose, color="cyan")

        # Get all relevant files for this pollutant with the correct time average
        pattern = os.path.join(processed_data_folder, f"data_{pollutant}{config['pattern']}*.csv")
        files = glob.glob(pattern)

        if not files:
            printv(f"No files found for {pollutant} with pattern {config['pattern']}",
                   verbose=verbose, color="yellow")
            continue

        # Calculate AQI for each time window and find maximum
        max_aqi = np.zeros((GRID_DIM_X, GRID_DIM_Y))

        for file_path in files:
            # Extract time label from filename
            filename = os.path.basename(file_path)
            time_label = filename.split(config['pattern'])[1].split(".csv")[0]

            # Read data
            data = pd.read_csv(file_path).values

            # Calculate AQI for this time window
            aqi_array = np.zeros((GRID_DIM_X, GRID_DIM_Y))

            for x_ in range(GRID_DIM_X):
                for y_ in range(GRID_DIM_Y):
                    # Convert mass per cell to a concentration
                    concentration = data[x_, y_] * config['conversion_factor_us_AQI']

                    # Calculate AQI based on pollutant type
                    pollutant_type = 'CO' if pollutant == 'co' else 'NO2' if pollutant == 'nox' else 'PM2.5'
                    aqi_value = calculate_aqi_for_pollutant_US_AQI(concentration, pollutant_type)
                    aqi_array[x_, y_] = aqi_value

            # Update maximum AQI if this time window has higher values
            max_aqi = np.maximum(max_aqi, aqi_array)

            printv(f"Processed {pollutant} AQI for time {time_label}",
                   verbose=verbose)

        # Save this pollutant's max AQI to file
        pollutant_aqi_filename = f"{pollutant}_max_aqi.csv"
        save_vec_to_csv(max_aqi, final_results_folder, pollutant_aqi_filename)
        printv(f"Saved maximum {pollutant} AQI to {pollutant_aqi_filename}",
               verbose=verbose, color="green")

        # Store for overall AQI calculation
        all_aqi_data_US[pollutant] = max_aqi

    # Calculate overall AQI (maximum of all pollutants)
    if all_aqi_data_US:
        overall_aqi = np.zeros((GRID_DIM_X, GRID_DIM_Y))

        # Initialize with first pollutant's data
        if 'co' in all_aqi_data_US:
            overall_aqi = all_aqi_data_US['co'].copy()
        elif 'nox' in all_aqi_data_US:
            overall_aqi = all_aqi_data_US['nox'].copy()
        elif 'pmx' in all_aqi_data_US:
            overall_aqi = all_aqi_data_US['pmx'].copy()

        # Find maximum AQI across all pollutants for each grid cell
        for x_ in range(GRID_DIM_X):
            for y_ in range(GRID_DIM_Y):
                aqi_values = []
                for pollutant in all_aqi_data_US:
                    aqi_values.append(all_aqi_data_US[pollutant][x_, y_])
                overall_aqi[x_, y_] = max(aqi_values) if aqi_values else 0

        # Save overall AQI
        overall_aqi_filename = "overall_max_aqi.csv"
        save_vec_to_csv(overall_aqi, final_results_folder, overall_aqi_filename)
        printv(f"Saved overall maximum AQI to {overall_aqi_filename}",
               verbose=verbose, color="green")
    else:
        printv("No AQI data was calculated for any pollutant",
               verbose=verbose, color="yellow")



    #########################################
    # Calcualte AQIH (Ireland)
    #########################################     

    # Process AQIH (Ireland) for NO2 and PM2.5 (CO is not considered)
    all_aqi_data_AQIH = {}
    for pollutant, config in pollutant_config.items():
        if pollutant == 'co':
            continue
        printv(f"Processing {pollutant} AQIH with {config['pattern']} pattern...",
               verbose=verbose, color="cyan")
        # Get all relevant files for this pollutant with the correct time average
        pattern = os.path.join(processed_data_folder, f"data_{pollutant}{config['pattern']}*.csv")
        files = glob.glob(pattern)
        if not files:
            printv(f"No files found for {pollutant} with pattern {config['pattern']}",
                   verbose=verbose, color="yellow")
            continue
        # Calculate AQI for each time window and find maximum
        max_aqi = np.zeros((GRID_DIM_X, GRID_DIM_Y))
        for file_path in files:
            # Extract time label from filename
            filename = os.path.basename(file_path)
            time_label = filename.split(config['pattern'])[1].split(".csv")[0]

            # Read data
            data = pd.read_csv(file_path).values

            # Calculate AQI for this time window
            aqi_array = np.zeros((GRID_DIM_X, GRID_DIM_Y))

            for x_ in range(GRID_DIM_X):
                for y_ in range(GRID_DIM_Y):
                    # Convert mass per cell to a concentration
                    concentration = data[x_, y_] * config['conversion_factor_AQIH']

                    # Calculate AQI based on pollutant type
                    pollutant_type = 'NO2' if pollutant == 'nox' else 'PM2.5'
                    aqi_value = calculate_aqi_for_pollutant_AQIH(concentration, pollutant_type)
                    aqi_array[x_, y_] = aqi_value

            # Update maximum AQI if this time window has higher values
            max_aqi = np.maximum(max_aqi, aqi_array)

            printv(f"Processed {pollutant} AQIH for time {time_label}",
                   verbose=verbose)
        # Save this pollutant's max AQI to file
        pollutant_aqi_filename = f"{pollutant}_max_aqih.csv"
        save_vec_to_csv(max_aqi, final_results_folder, pollutant_aqi_filename)
        printv(f"Saved maximum {pollutant} AQIH to {pollutant_aqi_filename}",
               verbose=verbose, color="green")
        # Store for overall AQI calculation
        all_aqi_data_AQIH[pollutant] = max_aqi
    # Calculate overall AQIH (maximum of all pollutants)
    if all_aqi_data_AQIH:
        overall_aqi = np.zeros((GRID_DIM_X, GRID_DIM_Y))

        # Initialize with first pollutant's data
        if 'nox' in all_aqi_data_AQIH:
            overall_aqi = all_aqi_data_AQIH['nox'].copy()
        elif 'pmx' in all_aqi_data_AQIH:
            overall_aqi = all_aqi_data_AQIH['pmx'].copy()

        # Find maximum AQI across all pollutants for each grid cell
        for x_ in range(GRID_DIM_X):
            for y_ in range(GRID_DIM_Y):
                aqi_values = []
                for pollutant in all_aqi_data_AQIH:
                    aqi_values.append(all_aqi_data_AQIH[pollutant][x_, y_])
                overall_aqi[x_, y_] = max(aqi_values) if aqi_values else 0

        # Save overall AQI
        overall_aqi_filename = "overall_max_aqih.csv"
        save_vec_to_csv(overall_aqi, final_results_folder, overall_aqi_filename)
        printv(f"Saved overall maximum AQIH to {overall_aqi_filename}",
               verbose=verbose, color="green")
    else:
        printv("No AQIH data was calculated for any pollutant",
               verbose=verbose, color="yellow")
    

def calculate_aqi_for_pollutant_US_AQI(concentration, pollutant):
    """
    Calculate AQI for a specific pollutant based on its concentration

    Args:
        concentration: Pollutant concentration (For CO: ppm, NO2: ppb, PM2.5: μg/m³)
        pollutant: Type of pollutant ('CO', 'NO2', or 'PM2.5')

    Returns:
        AQI value (0-500 scale)
    """
    # AQI breakpoints for different pollutants
    # Format: [concentration_low, concentration_high, index_low, index_high]

    # Source: https://www.airnow.gov/sites/default/files/2020-05/aqi-technical-assistance-document-sept2018.pdf

    breakpoints = {
        'CO': [
            [0, 4.4, 0, 50],
            [4.5, 9.4, 51, 100],
            [9.5, 12.4, 101, 150],
            [12.5, 15.4, 151, 200],
            [15.5, 30.4, 201, 300],
            [30.5, 40.4, 301, 400],
            [40.5, 50.4, 401, 500]
        ],
        'NO2': [
            [0, 53, 0, 50],
            [54, 100, 51, 100],
            [101, 360, 101, 150],
            [361, 649, 151, 200],
            [650, 1249, 201, 300],
            [1250, 1649, 301, 400],
            [1650, 2049, 401, 500]
        ],
        'PM2.5': [
            [0, 12.0, 0, 50],
            [12.1, 35.4, 51, 100],
            [35.5, 55.4, 101, 150],
            [55.5, 150.4, 151, 200],
            [150.5, 250.4, 201, 300],
            [250.5, 350.4, 301, 400],
            [350.5, 500.4, 401, 500]
        ]
    }

    # Find the appropriate breakpoint
    for bp in breakpoints[pollutant]:
        if bp[0] <= concentration <= bp[1]:
            # Linear interpolation, source: https://document.airnow.gov/technical-assistance-document-for-the-reporting-of-daily-air-quailty.pdf
            aqi = ((bp[3] - bp[2]) / (bp[1] - bp[0])) * \
                (concentration - bp[0]) + bp[2]
            return aqi

    # If concentration is higher than the highest breakpoint
    if concentration > breakpoints[pollutant][-1][1]:
        return 500
    # If concentration is zero or negative
    return 0

def calculate_aqi_for_pollutant_AQIH(concentration, pollutant):
    """
    Calculate AQI for a specific pollutant based on its concentration

    Args:
        concentration: Pollutant concentration (For NO2: μg/m³, PM2.5: μg/m³)
        pollutant: Type of pollutant ('NO2', or 'PM2.5')

    Returns:
        AQI value (1-10 scale)
    """
    # AQIH breakpoints for different pollutants
    # Format: [concentration_low, concentration_high, index_low, index_high]
    # Source: https://airquality.ie/information/air-quality-index-for-health
    
    breakpoints = {
        'NO2': [
            [0, 67, 1, 1],
            [67, 134, 1, 2],
            [134, 200, 2, 3],
            [200, 267, 3, 4],
            [267, 334, 4, 5],
            [334, 400, 5, 6],
            [400, 467, 6, 7], 
            [467, 534, 7, 8],
            [534, 600, 8, 9],
            [600, float('inf'), 9, 10]
        ],
        'PM2.5': [
            [0, 11, 1, 1],
            [11, 23, 1, 2],
            [23, 35, 2, 3],
            [35, 53, 3, 4],
            [53, 70, 4, 5],
            [70, 88, 5, 6],
            [88, 106, 6, 7],
            [106, 124, 7, 8],
            [124, 142, 8, 9],
            [142, float('inf'), 9, 10]
        ]
    }

    # If pollutant is CO, ignore it as per Irish AQIH
    if pollutant == 'CO':
        assert(False), "CO is not considered in the AQIH system"
    
    # If concentration is negative, return the lowest index
    if concentration < 0:
        printv("negative concentration in AQIH detected", True, "red")
        return 1
    
    # Find the appropriate breakpoint and apply linear interpolation
    for bp in breakpoints[pollutant]:
        if bp[0] <= concentration < bp[1]:
            # Linear interpolation
            aqi = ((bp[3] - bp[2]) / (bp[1] - bp[0])) * (concentration - bp[0]) + bp[2]
            return aqi
    
    # If concentration is higher than the highest breakpoint
    return 10

