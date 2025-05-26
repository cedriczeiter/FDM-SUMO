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

from helper import printv, save_vec_to_csv

from config import GRID_DIM_X, GRID_DIM_Y

#########################################
# Functions
#########################################  
def process_data_statistics(data_folder, avg_data_folder, verbose=False):
    """
    Process all data files to calculate max, min, avg, and max-min differences

    Args:
        data_folder: Path to folder containing the data files
        avg_data_folder: Path to folder to store the average data files
        verbose (bool): if more info printed
    """
    printv("Start function process_data_statistics",
           verbose=verbose, color="cyan", decorate=True)

    # Get all files matching the pattern "data_*_*.csv"
    file_pattern = os.path.join(data_folder, "data_*_*.csv")
    files = glob.glob(file_pattern)

    print(f"Found {len(files)} files matching the pattern: {file_pattern}")

    # Group files by data type
    data_types = {}
    for file in files:
        filename = os.path.basename(file)
        parts = filename.split("_")
        if len(parts) == 3: # noise data or old formatting without height example: data_co_3000
            data_key = f"{parts[0]}_{parts[1]}"  # e.g., "data_co"

            # Extract timestamp (seconds of the day) from the filename
            # Handle potential file extensions like .csv
            timestamp_str = parts[2].split('.')[0]
        elif len(parts) == 4: # data with height, example: data_co_1_3000
            data_key = f"{parts[0]}_{parts[1]}"  # e.g., "data_co"
            height = int(parts[2])  # e.g., "1"
            if height != 1:
                continue
            timestamp_str = parts[3].split('.')[0]
        else:
            break

        try:
            timestamp = int(timestamp_str)

            # round to closest 3600*k
            timestamp = round(timestamp / 3600) * 3600
            # check if the timestamp is valid
            if timestamp < 0 or timestamp > 86400:
                printv(f"Warning: Invalid timestamp {timestamp} in filename: {filename}",
                        verbose=verbose, color="yellow")
                continue

            # check if our dict already has this kind of information, else create
            if data_key not in data_types:
                data_types[data_key] = []

            # Store both file path and its timestamp
            data_types[data_key].append((file, timestamp))
        except ValueError:
            printv(f"Warning: Couldn't parse timestamp from filename: {filename}",
                    verbose=verbose, color="yellow")

    # Process each data type
    for data_key, file_data in data_types.items():
        calculate_statistics(data_key, file_data, avg_data_folder, verbose=verbose)

    print("All statistics files created successfully")


def calculate_statistics(data_key, file_data, avg_data_folder, verbose=False):
    """
    Calculate max, min, avg, and max-min difference for a specific data type,
    as well as hourly, 8-hourly, and 24-hourly moving averages

    Args:
        data_key: Data type key (e.g., "data_co")
        file_data: List of tuples (file_path, timestamp) for this data type
        avg_data_folder: Path to the folder to save the processed data files
        verbose (bool): if more to be printed
    """

    # Initialize arrays for statistics
    max_array = np.zeros((GRID_DIM_X, GRID_DIM_Y))
    min_array = np.full((GRID_DIM_X, GRID_DIM_Y), np.inf)
    sum_array = np.zeros((GRID_DIM_X, GRID_DIM_Y))


    # Sort file_data by timestamp
    file_data.sort(key=lambda x: x[1])

    printv(f"Running statistics for files of type {data_key}: ", verbose=verbose, color="cyan", decorate=True)
    for file, timestamp in file_data:
        printv(f"  {file} at {timestamp}", verbose=verbose)

    # Count for average calculation
    file_list = [item[0] for item in file_data]
    file_count = len(file_list)

    # Dictionary to store data for each timestamp
    timestamp_data = {}

    # Process each file for this data type
    for file, timestamp in file_data:
        # Read the CSV file
        df = pd.read_csv(file)

        # Convert to numpy array
        current_array = df.values

        # Store data for this timestamp
        timestamp_data[timestamp] = current_array

        # Update statistics arrays for overall statistics
        max_array = np.maximum(max_array, current_array)
        min_array = np.minimum(min_array, current_array)
        sum_array += current_array

    # Replace infinity with zeros in min_array (for cells that had no data)
    min_array[np.isinf(min_array)] = 0

    # Calculate overall average
    avg_array = sum_array / file_count if file_count > 0 else sum_array

    # Calculate max-min difference
    diff_array = max_array - min_array

    # Save overall statistics to files in the processed_data directory
    save_vec_to_csv(max_array, avg_data_folder, f"{data_key}_max.csv")
    save_vec_to_csv(min_array, avg_data_folder, f"{data_key}_min.csv")
    save_vec_to_csv(avg_array, avg_data_folder, f"{data_key}_avg.csv")
    save_vec_to_csv(diff_array, avg_data_folder, f"{data_key}_diff.csv")


    # Calculate moving averages
    calculate_moving_averages(data_key, timestamp_data,
                              avg_data_folder, verbose)

    print(f"Statistics for {data_key} saved successfully")


def calculate_moving_averages(data_key, timestamp_data, avg_data_folder, verbose=False):
    """
    Calculate hourly, 8-hourly, and 24-hourly moving averages

    Args:
        data_key: Data type key (e.g., "data_co")
        timestamp_data: Dictionary mapping timestamps to data arrays
        avg_data_folder: Path to save the processed data files
        verbose: Whether to print verbose output
    """
    # Constants for time intervals in seconds
    HOUR_SEC = 3600
    EIGHT_HOUR_SEC = 8 * HOUR_SEC
    DAY_SEC = 24 * HOUR_SEC

    # Get sorted timestamps
    timestamps = sorted(timestamp_data.keys())

    if len(timestamps) == 0:
        printv(f"No data available for {data_key}", verbose=verbose, color="yellow")
        return

    # Define moving average windows to process
    windows = [
        {"name": "1h", "window_size": HOUR_SEC, "min_points": 1, "label": "hour"},
        {"name": "8h", "window_size": EIGHT_HOUR_SEC, "min_points": 8, "label": "from_hour"},
        {"name": "24h", "window_size": DAY_SEC, "min_points": 24, "label": "from_hour"}
    ]

    # Calculate moving averages for each window type
    for window in windows:
        printv(f"Calculating {window['name']} averages for {data_key}...", verbose=verbose)
        calculate_moving_average_for_window(
            data_key, 
            timestamps, 
            timestamp_data, 
            window["window_size"], 
            window["min_points"], 
            window["name"], 
            window["label"],
            avg_data_folder
        )


def calculate_moving_average_for_window(data_key, timestamps, timestamp_data, window_size, min_points, 
                                        window_name, time_label, avg_data_folder):
    """
    Calculate moving average for a specific window size
    
    Args:
        data_key: Data type key (e.g., "data_co")
        timestamps: Sorted list of timestamps
        timestamp_data: Dictionary mapping timestamps to data arrays
        window_size: Size of the window in seconds
        min_points: Minimum number of data points required to calculate the average
        window_name: Name of the window (e.g., "1h", "8h", "24h")
        time_label: Label to use in the filename (e.g., "hour", "from_hour")
        avg_data_folder: Path to save the processed data files
    """
    HOUR_SEC = 3600  # Hours in seconds for timestamp conversion
    print("In function calculate_moving_average_for_window")
    
    for start_time in timestamps:
        # Define the window end time
        end_time = start_time + window_size

        # Find timestamps that fall within this window
        window_timestamps = [t for t in timestamps if start_time <= t < end_time]
        print(f"  Window from {start_time} to {end_time}: {len(window_timestamps)} timestamps")

        # Only calculate if we have enough data points
        if len(window_timestamps) >= min_points:
            print("in if len(window_timestamps) >= min_points")
            # Initialize sum array and count
            window_sum = np.zeros((GRID_DIM_X, GRID_DIM_Y))
            count = 0

            # Sum up all arrays within the window
            for t in window_timestamps:
                window_sum += timestamp_data[t]
                count += 1

            # Calculate average
            window_avg = window_sum / count

            # Save to file with timestamp information
            start_hour = int(start_time / HOUR_SEC)
            filename = f"{data_key}_{window_name}_avg_{time_label}{start_hour}.csv"
            save_vec_to_csv(window_avg, avg_data_folder, filename)

