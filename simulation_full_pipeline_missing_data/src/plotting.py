#############################################
# Code by Cédric-Yséry Zeiter
# June 2025
# Part of Bachelor thesis at ETH Zurich
# Supervised by Kevien Riehl
#############################################

#########################################
# Imports
#########################################  

import matplotlib.pyplot as plt
import re
from matplotlib.patches import Polygon as MplPolygon
import ast
import numpy as np
import pandas as pd

from helper import printv, array_to_csv, convert_lat_lon_to_sumo_coordinates, convert_sumo_coordinates_to_grid_x_y
import os
import glob
from config import NETWORK_FILE, GRID_LEFT, GRID_RIGHT, GRID_BOTTOM, GRID_TOP



#########################################
# Functions
#########################################  

def plot_heatmap(input_vec, house_polygons_df, name, verbose=False, log=True, print_house=False, house_coloring=False, min_max=False, output_path="../output/plot/"):
    """
    Plots a heatmap of the input vector and overlays house polygons.

    Args:
        input_vec (numpy 2D array): 2D array representing the heatmap data.
        house_polygons_df (DataFrame): DataFrame containing house polygons.
        name (str): Name for the heatmap and output file.
        verbose (bool): If True, prints additional information.
        log (bool): If we want to plot with a logarithmic scale (cutoff at zero)
        print_house (bool): If houses should be printed
        house_coloring (bool): If we want to check which input points belong to which house and color the entire house accordingly
        min_max (bool): If should min-max normalize
        output_path (str): In which folder the plot should be saved to
    Outputs:
        None (only saves to a file)
    """

    printv("Start function plot_heatmap",
           verbose=verbose, color="blue", decorate=True)
    
    grid_height = input_vec.shape[0]
    grid_width = input_vec.shape[1]


    # Option to make it logarithmic
    if log == True:
        input_vec = np.log(input_vec)
        input_vec[input_vec < 0] = 0

    # min-max normalization support
    if min_max:
        min_val = np.nanmin(input_vec)
        max_val = np.nanmax(input_vec)
        if max_val > min_val:
            input_vec = (input_vec - min_val) / (max_val - min_val)
        else:
            input_vec = np.zeros_like(input_vec)
            printv("Min and max are equal. Input was constant or empty. (error from plot_heatmap function with min_max true)", verbose=True, color="Red")

    # Start matplotlib stuff
    plt.figure(figsize=(10, 8))

    hm = plt.imshow(input_vec.T, cmap='hot', interpolation='nearest', extent=[GRID_LEFT, GRID_RIGHT, GRID_BOTTOM, GRID_TOP], origin='lower')
    plt.colorbar(label=f'{name}')
    plt.title(f'{name} Heatmap')
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.xlim(GRID_LEFT, GRID_RIGHT)
    plt.ylim(GRID_BOTTOM, GRID_TOP)

    hm_colors = hm.cmap(hm.norm(hm.get_array()))

    printv("Creaded plt and extracted colors", verbose=verbose)

    if print_house == True:
        ax = plt.gca()
        for i, row in house_polygons_df.iterrows():
            try:
                poly_wkt = row.get('polygon')
                bbox = row.get('bounding_box')

                house_lat = row.get('lat')
                house_lon = row.get('lon')

                house_x, house_y = convert_lat_lon_to_sumo_coordinates(
                    house_lat, house_lon, NETWORK_FILE)

                house_grid_x, house_grid_y = convert_sumo_coordinates_to_grid_x_y(
                    grid_left=GRID_LEFT, grid_right=GRID_RIGHT, grid_bottom=GRID_BOTTOM, grid_top=GRID_TOP, size_x=grid_width, size_y=grid_height, sumo_x=house_x, sumo_y=house_y, verbose=False)

                if house_coloring == True:
                    color = hm_colors[house_grid_y, house_grid_x]

                coords = None

                # Case 1: Real polygon exists
                if isinstance(poly_wkt, str) and poly_wkt.strip().startswith("POLYGON("):
                    matches = re.findall(r'(\d+\.\d+)\s+(\d+\.\d+)', poly_wkt)
                    if matches:
                        coords = [(float(lon), float(lat))
                                  for lon, lat in matches]

                # Case 2: Fallback to bounding box rectangle
                elif isinstance(bbox, str):
                    try:
                        # safely parse stringified list
                        bb = ast.literal_eval(bbox)
                        min_lat, max_lat, min_lon, max_lon = map(float, bb)
                        coords = [
                            (min_lon, min_lat),
                            (min_lon, max_lat),
                            (max_lon, max_lat),
                            (max_lon, min_lat),
                            (min_lon, min_lat)
                        ]
                    except Exception as e:
                        print(f"Could not parse bounding box at index {i}: {e}", color="Red")
                        continue

                # Plotting if coords were found
                if coords:
                    coords_sumo = [convert_lat_lon_to_sumo_coordinates(lat, lon, NETWORK_FILE)
                                   for lon, lat in coords]
                    if house_coloring == False:
                        poly_patch = MplPolygon(coords_sumo, closed=True, edgecolor='green',
                                                facecolor="none", linewidth=1, alpha=1.0)
                    else:
                        poly_patch = MplPolygon(coords_sumo, closed=True, edgecolor='None',
                                                facecolor=color, linewidth=0, alpha=1.0)
                    ax.add_patch(poly_patch)

            except Exception as e:
                printv(f"Error processing polygon at index {i}: {e}", color="Red")
                continue

    plt.grid(False)
    plt.tight_layout()
    plt.savefig(output_path+f'/{name}_heatmap.png')
    plt.close()
    printv("Finished the plot", verbose=verbose)


def plot_all_heatmaps(data_folder, plot_folder, house_polygons, print_houses=False, verbose=False):
    """
    Plots all heatmaps for the given data.
    Args:
        data_folder (str): Where to find all the csv
        plot_folder (str): Where to save my stuff to
        house_polygons (DataFrame): DataFrame containing house polygons.
        print_houses (bool): if print houses activated
        verbose (bool): If True, prints additional information.
    Outputs:
        None (only saves to files)

    """

    printv("Start function plot_all_heatmaps",
           verbose=verbose, color="blue", decorate=True)

    # Create the folder if doesnt exist for plot results
    os.makedirs(plot_folder, exist_ok=True)

    # Get all CSV files in the data folder
    csv_files = glob.glob(os.path.join(data_folder, "*.csv"))
    printv(f"Found {len(csv_files)} CSV files in {data_folder}", verbose=verbose)

    # Process each CSV file
    for csv_file in csv_files:
        try:
            # Get the base filename without extension
            base_name = os.path.basename(csv_file).replace(".csv", "")
            printv(f"Processing {base_name}", verbose=verbose)

            # Read CSV into a DataFrame and convert to numpy array
            df = pd.read_csv(csv_file)
            array_data = df.values

            # If file name starts with "data_", then normalize the data
            plot_name_extension = None
            if base_name.startswith("data_"):
                # Normalize the data to mg/m³
                plot_name_extension = "_mg_per_m3"

            # Plot heatmap for this data file
            plot_name = f"{base_name}{plot_name_extension if plot_name_extension else ''}"
            plot_heatmap(array_data, house_polygons, plot_name, verbose=verbose, log=False, print_house=print_houses, output_path=plot_folder)

        except Exception as e:
            printv(f"Error processing {csv_file}: {e}", verbose=True, color="Red")
