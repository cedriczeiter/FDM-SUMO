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
import pickle

from helper import convert_lat_lon_to_sumo_coordinates, printv
from collections import defaultdict
from config import GRID_BOTTOM, GRID_LEFT, GRID_RIGHT, GRID_TOP



#########################################
# Functions
#########################################  

def get_people_data(file_data, file_sumo, recalculate=False, verbose=True):
    """
    Get people data from the given file and filter it based on the specified coordinates.
    If the data has been processed before with the same parameters, it is loaded from a cache file.

    Args:
        file_data (str): Path to the input file.
        file_sumo (str): Path to the SUMO network file.
        recalculate (bool): If force recalculation of data even if cached data exists
        verbose (bool): If more information should be printed.

    Returns:
        dict: Dictionary with keys (x_coord, y_coord)->sumo system, and values as dictionaries containing:
            - 'count': Number of people at this coordinate
            - 'people': List of dictionaries containing people's attributes
    """

    printv("Start function get_people_data", verbose=verbose, color="blue", decorate=True)

    # Caching logic
    cache_folder = "../output/temp/"
    os.makedirs(cache_folder, exist_ok=True)
    cache_filename = f"../output/temp/cached_people_data_{GRID_LEFT}_{GRID_RIGHT}_{GRID_BOTTOM}_{GRID_TOP}.pkl"

    if os.path.exists(cache_filename) and not recalculate:
        printv(f"[INFO] Loading cached people data from '{cache_filename}'...", verbose=verbose)
        with open(cache_filename, 'rb') as f:
            return pickle.load(f)


    # Read data from the file
    with open(file_data, 'r') as f:
        data = f.readlines()[1:]  # skip header

    n = len(data)
    people_data = defaultdict(lambda: {"count": 0, "people": []})

    printv("[INFO] Start of reading people... can take multiple minutes to an hour",
           verbose=verbose)

    # Read the data and filter based on coordinates -> increment people amount and add metadata about the person
    counter = 0
    last_percentage = 0
    for line in data:
        counter += 1
        if verbose:
            percentage = (counter / n) * 100
            if percentage >= last_percentage:
                printv(f"Scanned people: {last_percentage} %", verbose=verbose)
                last_percentage += 10

        parts = line.strip().split(',')

        lat = float(parts[9])
        lon = float(parts[10])

        x_coord, y_coord = convert_lat_lon_to_sumo_coordinates(lat, lon, file_sumo)

        if (GRID_LEFT <= x_coord <= GRID_RIGHT) and (GRID_BOTTOM <= y_coord <= GRID_TOP):
            person_dict = {
                "age": parts[0],
                "level_of_employment": parts[1],
                "household_income": parts[2],
                "position_in_edu": parts[3],
                "position_in_bus": parts[4],
                "cars_drivetype": parts[5],
                "public_transport": parts[6],
                "has_car_and_licence": parts[11],
                "x_coord": x_coord,
                "y_coord": y_coord
            }

            coord_key = (x_coord, y_coord)
            people_data[coord_key]["count"] += 1
            people_data[coord_key]["people"].append(person_dict)

    printv("End of reading people", verbose=verbose)

    result = dict(people_data)

    # Save to cache
    with open(cache_filename, 'wb') as f:
        pickle.dump(result, f)

        printv(f"Saved processed people data to '{cache_filename}'", verbose=verbose)

    return result

    """
    Get people data from the given file and filter it based on the specified coordinates.
    If the data has been processed before with the same parameters, it is loaded from a cache file.

    Args:
        file_data (str): Path to the input file.
        file_sumo (str): Path to the SUMO network file.
        recalculate (bool): Wehter to force recalculation of data
        verbose (bool): If more information should be printed.

    Returns:
        dict: Dictionary with keys (x_coord, y_coord)->sumo system, and values as dictionaries containing:
            - 'count': Number of people at this coordinate
            - 'people': List of dictionaries containing people's attributes
    """

    printv("Start function get_people_data",
           verbose=verbose, color="blue", decorate=True)

    cache_folder = "../output/temp/"
    os.makedirs(cache_folder, exist_ok=True)
    cache_filename = f"../output/temp/cached_people_data_{GRID_LEFT1}_{GRID_RIGHT1}_{GRID_BOTTOM1}_{GRID_TOP1}.pkl"

    if os.path.exists(cache_filename) and not recalculate:
        printv(f"[INFO] Loading cached people data from '{cache_filename}'...", verbose=verbose)
        with open(cache_filename, 'rb') as f:
            return pickle.load(f)

    # Read data from the file
    with open(file_data, 'r') as f:
        data = f.readlines()[1:]  # skip header

    n = len(data)
    people_data = defaultdict(lambda: {"count": 0, "people": []})

    printv("[INFO] Start of reading people... can take multiple minutes to an hour",
           verbose=verbose)

    counter = 0
    last_percentage = 0
    for line in data:
        counter += 1
        if verbose:
            percentage = (counter / n) * 100
            if percentage >= last_percentage:
                printv(f"Scanned people: {last_percentage} %", verbose=verbose)
                last_percentage += 10

        parts = line.strip().split(',')

        lat = float(parts[9])
        lon = float(parts[10])

        x_coord, y_coord = convert_lat_lon_to_sumo_coordinates(
            lat, lon, file_sumo)

        if (GRID_LEFT1 <= x_coord <= GRID_RIGHT1) and (GRID_BOTTOM1 <= y_coord <= GRID_TOP1):
            person_dict = {
                "age": parts[0],
                "level_of_employment": parts[1],
                "household_income": parts[2],
                "position_in_edu": parts[3],
                "position_in_bus": parts[4],
                "cars_drivetype": parts[5],
                "public_transport": parts[6],
                "has_car_and_licence": parts[11],
                "x_coord": x_coord,
                "y_coord": y_coord
            }

            coord_key = (x_coord, y_coord)
            people_data[coord_key]["count"] += 1
            people_data[coord_key]["people"].append(person_dict)

    printv("End of reading people", verbose=verbose)

    result = dict(people_data)

    # Save to cache
    with open(cache_filename, 'wb') as f:
        pickle.dump(result, f)

        printv(f"Saved processed people data to '{cache_filename}'", verbose=verbose)

    return result