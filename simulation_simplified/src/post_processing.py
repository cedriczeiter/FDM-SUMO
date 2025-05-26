#############################################
# Code by Cédric-Yséry Zeiter
# June 2025
# Part of Bachelor thesis at ETH Zurich
# Supervised by Kevien Riehl
#############################################

#########################################
# Imports
#########################################  

from process_gas_to_aqi import process_gas_to_aqi
from process_data import process_data_statistics
import os
from helper import printv



#########################################
# Functions
#########################################  

def post_processing_wrapper(data_folder, plot_folder, avg_data_folder, final_results_folder, verbose=False):

    """
    Post-process the data from the simulation.
    Args:
        data_folder (str): Path to the folder containing the simulation data.
        plot_folder (str): Path to the folder where plots will be saved.
        avg_data_folder (str): Path to the folder where average data will be saved.
        final_results_folder (str): Path to the folder where final results will be saved.
        verbose (bool): If more information should be printed.
    """

    printv("Start function post_processing_wrapper", verbose=verbose, color="blue", decorate=True)

    os.makedirs(data_folder, exist_ok=True)
    os.makedirs(plot_folder, exist_ok=True)
    os.makedirs(avg_data_folder, exist_ok=True)
    os.makedirs(final_results_folder, exist_ok=True)
    
    process_data_statistics(data_folder, avg_data_folder=avg_data_folder, verbose=verbose)

    process_gas_to_aqi(final_results_folder=final_results_folder, processed_data_folder=avg_data_folder, verbose=verbose)


