#############################################
# Code by Cédric-Yséry Zeiter
# June 2025
# Part of Bachelor thesis at ETH Zurich
# Supervised by Kevien Riehl
#############################################

#########################################
# General configuration for the simulation
#########################################  

GAS_HEIGHT = 1 # which cell in z-direction we are interested in
VERBOSE = True
FORCE_RECALCULATE = False
TIME_PER_SCREENSHOT = 3600 #seconds
SHOW_INTERFACE = False # Show the SUMO interface
REROUTING_PERIOD = 360 # rerouting period in seconds

#########################################
# Define the date
#########################################  

DATE = "07_20" # Date of the simulation
# DATE = "20_11"
# DATE = "05_17" # Date of the simulation

#########################################
# Define the grid for the village -> aim for a square grid of 10x10m
#########################################  

# ------------------ Erstfeld -------------------
GRID_LEFT = 16850
GRID_RIGHT = 18630
GRID_TOP = 37720
GRID_BOTTOM = 35000

# Grid dimensions
GRID_DIM_Y = 250
GRID_DIM_X = 160
GRID_DIM_Z = 50

VILLAGE_NAME = "erstfeld" 
VILLAGE_LARGE = "Erstfeld"

# # ------------------ Goeschenen -------------------
# GRID_LEFT = 12600
# GRID_RIGHT = 13700
# GRID_TOP = 20000
# GRID_BOTTOM = 18200

# # Grid dimensions
# GRID_DIM_Y = 180
# GRID_DIM_X = 100
# GRID_DIM_Z = 50

# VILLAGE_NAME = "goeschenen" 
# VILLAGE_LARGE = "Goeschenen"

# # ------------------ Gurtnellen -------------------
# GRID_LEFT = 15400
# GRID_RIGHT = 16500
# GRID_TOP = 27000
# GRID_BOTTOM = 24700

# # Grid dimensions
# GRID_DIM_Y = 230
# GRID_DIM_X = 110
# GRID_DIM_Z = 50

# VILLAGE_NAME = "gurtnellen" 
# VILLAGE_LARGE = "Gurtnellen"

# # ------------------ Schattdorf -------------------
# GRID_LEFT = 16900
# GRID_RIGHT = 19000
# GRID_TOP = 41500
# GRID_BOTTOM = 38300

# GRID_DIM_Y = 310
# GRID_DIM_X = 210
# GRID_DIM_Z = 50

# VILLAGE_NAME = "schattdorf" 
# VILLAGE_LARGE = "Schattdorf"


# # ------------------ Silenen -------------------
# GRID_LEFT = 18900
# GRID_RIGHT = 20100
# GRID_TOP = 34300
# GRID_BOTTOM = 29900

# GRID_DIM_Y = 430
# GRID_DIM_X = 115
# GRID_DIM_Z = 50

# VILLAGE_NAME = "silenen" 
# VILLAGE_LARGE = "Silenen"


# # ------------------ Wassen -------------------
# GRID_LEFT = 13500
# GRID_RIGHT = 15300
# GRID_TOP = 24500
# GRID_BOTTOM = 20900

# # Grid dimensions
# GRID_DIM_Y = 360
# GRID_DIM_X = 175
# GRID_DIM_Z = 50

# VILLAGE_NAME = "wassen" 
# VILLAGE_LARGE = "Wassen"



NETWORK_FILE = f"../villages/{VILLAGE_LARGE}/{VILLAGE_NAME}_osm.net.xml"  # Path to the network file
SUMO_FILE = f"../villages/{VILLAGE_LARGE}/{DATE}_{VILLAGE_NAME}.sumocfg" # Path to the SUMO config file
SPEED_FILE = f"../villages/{VILLAGE_LARGE}/{DATE}_exit_speeds_per_second_{VILLAGE_NAME}.csv"  # Path to the speed file