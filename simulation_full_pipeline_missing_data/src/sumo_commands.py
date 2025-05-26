#############################################
# Code by Cédric-Yséry Zeiter
# June 2025
# Part of Bachelor thesis at ETH Zurich
# Supervised by Kevien Riehl
#############################################

#########################################
# Imports
#########################################  

import traci
import pandas as pd
import os
import numpy as np
import random
import datetime

from config import SUMO_FILE, SPEED_FILE
from helper import printv

# set seed for reproducibility
random.seed(42)



#########################################
# Functions
#########################################  

def count_non_workers_non_students_with_car(people_coordinates_on_grid):

    """
    Count the number of people who are neither employed nor in education and have a car.

    Args:
        people_coordinates_on_grid (dict): Dictionary containing people data with coordinates as keys.

    Returns:
        int: Number of people who are neither employed nor in education and have a car.
    """

    non_workers_non_students = 0
    
    for coord, data in people_coordinates_on_grid.items():
        if 'people' in data:
            for person in data['people']:
                # Check if this person is neither employed nor in education
                is_not_employed = not person.get('position_in_bus') or person['position_in_bus'] == ''
                is_not_student = not person.get('position_in_edu') or person['position_in_edu'] == ''
                has_car = person.get('has_car_and_licence') == 'True'
                
                if is_not_employed and is_not_student and has_car:
                    non_workers_non_students += 1

    return int(non_workers_non_students)
    

def count_workers_with_cars_adjusted(people_coordinates_on_grid):
    """
    Count the number of workers with cars and the total population with cars.

    Args:
        people_coordinates_on_grid (dict): Dictionary containing people data with coordinates as keys.
    Returns:
        tuple: Number of workers (adjusted by workload) with cars (and licence) and total population with cars (and licence) 
    """

    workers_with_cars = 0
    population_with_car = 0
    
    for coord, data in people_coordinates_on_grid.items():
        for person in data['people']:
            # Check if this person is employed and has a car
            is_employed = person.get('position_in_bus') and person['position_in_bus'] != ''
            has_car = person.get('has_car_and_licence') == 'True'

            if has_car:
                population_with_car += 1
            
            if is_employed and has_car:
                    # Get employment level and convert to weight
                    employment_level = person.get('level_of_employment')
                    weight = 0
                    
                    if employment_level == '0':
                        weight = 0
                    elif employment_level == '1-39':
                        weight = 0.2  # 20% of full-time
                    elif employment_level == '40-79':
                        weight = 0.6  # 60% of full-time
                    elif employment_level == '80-100':
                        weight = 0.9  # full-time
                    else:
                        # Skip this person if employment level doesn't match expected categories
                        continue
                    
                    workers_with_cars += weight

    return int(workers_with_cars), int(population_with_car)


def startSumo(zoom, x_off, y_off, dt=1.0, visual_interface=True, verbose=True):
    """
    Start the SUMO simulation with the specified parameters.
    Args:
        zoom (float): Zoom level for the SUMO GUI.
        x_off (float): X offset for the SUMO GUI.
        y_off (float): Y offset for the SUMO GUI.
        dt (float): Simulation time step.
        visual_interface (bool): Whether to use the SUMO GUI.
        verbose (bool): If more information should be printed.

    Returns:
        None
    """

    printv("Start function startSumo", verbose=verbose, color="blue", decorate=True)

    # Determine which binary to use
    if visual_interface:
        # Try to find sumo-gui first
        sumoBinary = "sumo-gui"
        # Check if sumo-gui exists
        if not os.path.exists(sumoBinary) and not os.system("which sumo-gui > /dev/null") == 0:
            printv("WARNING: Could not find sumo-gui, using regular sumo", verbose=verbose, color="yellow")
            sumoBinary = "sumo"
            visual_interface = False
    else:
        sumoBinary = "sumo"
    
    printv(f"Using SUMO binary: {sumoBinary}", verbose=verbose)
    
    # Create command
    sumoCmd = [sumoBinary, "-c", SUMO_FILE, "--start", "--quit-on-end", "--step-length", str(dt)]
    
    # Giving it labels based on current time in real time
    unique = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    printv(f"Opening connection test_label_{unique}", verbose=verbose)
    
    # Start SUMO
    try:
        traci.start(sumoCmd, label=f"test_label_{unique}")
    except Exception as e:
        printv(f"Error starting SUMO: {e}", verbose=verbose, color="red")
        raise
    
    # Only set GUI parameters if using the visual interface
    if visual_interface:
        try:
            traci.gui.setZoom("View #0", zoom)
            traci.gui.setOffset("View #0", x_off, y_off)
        except Exception as e:
            printv(f"Warning: Could not set GUI parameters: {e}", verbose=verbose, color="yellow")

    if verbose:
        print("Started SUMO")
        
    precompute_suitable_edges()
    create_delivery_vehicle_type()


def stopSumo(verbose=False):
    """
    End sumo simulation.

    Args:
        verbose (bool) : Tells if printed output
    """

    printv("Start function stopSumo", verbose=verbose, color="blue", decorate=True)

    traci.close()


# Import the speed data from the CSV file once
speed_data = pd.read_csv(SPEED_FILE) # call once at the beginning
def update_edge_speeds(time_step):
    """
    Update edge speeds based on the current simulation time. Looks at data from the CSV file, generated by Manon files.

    Args:
        time_step (float): Current simulation time step.

    Returns:
        None
    """
    # Get the speeds for the current time step (if available)
    if int(time_step) < len(speed_data):
        current_speeds = speed_data.iloc[int(time_step)]
        
        # Process each edge in the CSV
        for edge in current_speeds.keys():
            if edge == 'time':  # Skip the time column
                continue
                
            # Get the edge ID without the 'lane_exit_' prefix
            speed = current_speeds[edge]
            
            # Apply speed only if not -1.0 (placeholds for the morning)
            if speed != -1.0:
                try:
                    traci.edge.setMaxSpeed(edge, float(speed))
                except traci.TraCIException as e:
                    print(f"Error setting speed for edge {edge}: {e}")


def reroute_vehicles_to_avoid_traffic(reroute_percentage, vehicle_ids):
    """
    Reroutes a given percentage of vehicles to avoid traffic.
    
    Args:
        reroute_percentage (float): Percentage of vehicles to reroute (0.0-1.0)
        vehicle_ids (list): List of vehicle IDs to consider for rerouting.

    Returns:
        None
    """
    num_to_reroute = int(len(vehicle_ids) * reroute_percentage)
    
    if num_to_reroute == 0:
        return
        
    # Randomly select vehicles to reroute
    vehicles_to_reroute = np.random.choice(vehicle_ids, size=num_to_reroute, replace=False)
    
    for veh_id in vehicles_to_reroute:
        # Compute new route with current traffic conditions
        traci.vehicle.rerouteTraveltime(veh_id, currentTravelTimes=True)
        
        traci.vehicle.setRoutingMode(veh_id, 1)  # 1 = ROUTING_MODE_AGGREGATED (looks at the current traffic conditions)


# Precompute suitable edges for delivery vehicles (the type that can go into housing areas)
SUITABLE_EDGES = []
def precompute_suitable_edges():
    """
    Precompute suitable edges for delivery vehicles to improve performance
    """
    global SUITABLE_EDGES
        
    # Get all edges that can be used as start points
    edges = traci.edge.getIDList()
    suitable_edges = []
    
    for edge in edges:
        if edge.startswith(':'):  # Skip internal/junction edges
            continue
            
        try:
            # Check if edge has lanes
            lane_count = traci.edge.getLaneNumber(edge)
            if lane_count <= 0:
                continue
                
            # Check permissions on all lanes
            edge_valid = False

            lane_id = f"{edge}_0"
            try:
                allowed = traci.lane.getAllowed(lane_id)
                lane_speed = traci.lane.getMaxSpeed(lane_id)
                
                # Calculate if the lane looks like it could be used by private cars (sometimes delivery vehicles only allowed inside the villages)
                delivery_allowed = (not allowed) or (('delivery' in allowed) and ('pedestrian' not in allowed)) or ('passenger' in allowed)
                correct_speed = lane_speed < 17  # ~60 km/h, such as in areas where people live
                
                if delivery_allowed and correct_speed:
                    edge_valid = True
                else:
                    continue
            except Exception as e:
                print(f"Error checking lane permissions for {lane_id}: {e}")
                continue
        
            # Check speed limit (avoid highways)
            if edge_valid:
                suitable_edges.append(edge)
                
        except Exception as e:
            # Skip edges with errors
            print(f"Error processing edge {edge}: {e}")
            continue
    
    SUITABLE_EDGES = suitable_edges
    print(f"Precomputed {len(SUITABLE_EDGES)} suitable edges for delivery vehicles (speed limit < 17 m/s)")


def add_random_delivery_vehicle():
    """
    Add a single random delivery vehicle (has access to housing areas) to the simulation
    """
    global SUITABLE_EDGES
    
    if not SUITABLE_EDGES or len(SUITABLE_EDGES) < 2:
        print("Not enough suitable edges available")
        return False
        
    # Try up to 5 times to find a valid route
    for attempt in range(5):
        try:
            # Generate a random route using precomputed suitable edges
            from_edge = random.choice(SUITABLE_EDGES)
            possible_to_edges = [e for e in SUITABLE_EDGES if e != from_edge]
            
            if not possible_to_edges:
                continue
                
            to_edge = random.choice(possible_to_edges)
            
            try:
                route = traci.simulation.findRoute(from_edge, to_edge, vType="resident_type")
                
                # Skip invalid or very short routes
                if len(route.edges) <= 1 or route.cost >= 1000000:  # High cost indicates invalid route
                    print(f"Skipping invalid route from {from_edge} to {to_edge}")
                    continue
                
            except traci.exceptions.TraCIException:
                # Invalid route
                continue
                
            # Generate a unique vehicle ID
            veh_id = f"resident_{int(traci.simulation.getTime())}_{random.randint(0, 100000)}"
            
            # Create the vehicle with safe insertion parameters
            try:
                # Use a different approach: first create route, then add vehicle
                route_id = f"route_{veh_id}"
                try:
                    traci.route.add(route_id, route.edges)
                except traci.exceptions.TraCIException:
                    # Route might already exist
                    continue
                
                # Add the vehicle
                traci.vehicle.add(veh_id, route_id, typeID="resident_type", departSpeed="0")
                traci.vehicle.setColor(veh_id, (255, 0, 0, 255)) # red color, easier to see
                traci.vehicle.setSpeedFactor(veh_id, random.uniform(0.8, 1.0))
                print(f"Successfully added vehicle {veh_id}")
                return True
            except traci.exceptions.TraCIException as e:
                print(f"Failed to add vehicle: {e}")
                continue
            
        except Exception as e:
            print(f"Unexpected error when trying to add vehicle: {e}")
            continue
            
    return False


def add_time_dependent_traffic(weekday, curr_time, dt, population_with_car, working_population, inactive_population):
    """
    Add time-dependent random traffic to the simulation
    
    Args:
        weekday (bool): false if weekend, true if weekday
        curr_time (float): Current simulation time in seconds
        dt (float): Simulation time step
        population_with_car (int): How many people lie in the area with cars
        working_population(int): How many people are working with car (adjusted to the amount of work)
        inactive_population (int): People that are not working and not a student but have a car

    Returns:
        None
    """
    # Convert current time to hours (assuming curr_time is in seconds)
    curr_hour = (curr_time / 3600.0) % 24
    
    if weekday==True:
        if 0 <= curr_hour < 5:
            target_vehicles = population_with_car*0.001  # 0.1% of people at night per hour
        elif 5<= curr_hour < 9:
            target_vehicles = working_population*(1/3.) # working population with car, go to work over 3 hours
        elif 9 <= curr_hour < 11:
            target_vehicles = inactive_population*0.2*(1/2.)  # 20% of people that stay at home, over 2 hours do something in the morning
        elif 11 <= curr_hour < 13:
            target_vehicles = working_population*0.5*(1/2.)  # 50% of workers go home for lunch,, over two hours
        elif 13 <= curr_hour < 16:
            target_vehicles = inactive_population*0.15*(1/3.)   # 15 % drive around at afternoon
        elif 16 <= curr_hour < 19:
            target_vehicles = working_population*(1/3.)  # working population with car, come home from work over 3 hours
        elif 19 <= curr_hour < 21:
            target_vehicles = population_with_car*0.1*(1/2.)  # 10% of people do something in the evening, over 2 hours
        else:  # 21-24
            target_vehicles = population_with_car*0.001 # 0.1% of people at night per hour
    else:
        # Weekend traffic pattern
        if 0 <= curr_hour < 5:
            target_vehicles = population_with_car*0.001 # 0.1% of people at night per hour
        elif 5<= curr_hour < 8:
            target_vehicles = population_with_car*0.05*(1/3.) # 5% of people do somehting in the morning
        elif 9 <= curr_hour < 18:
            target_vehicles = population_with_car*0.25 # 25% of people do something during the day -> assuming that families use one car
        elif 18 <= curr_hour < 21:
            target_vehicles = population_with_car*0.05*(1/3.) # 5% of peoplen do something in the evening
        else:  # 21-24
            target_vehicles = population_with_car*0.001 # 0.1% of people at night per hour
            
    target_vehicles = int(target_vehicles)
    # Ensure target_vehicles is at least 1 per hour
    target_vehicles = max(target_vehicles, 1)
    # Calculate vehicles per second
    vehicles_per_second = target_vehicles / 3600.0
    
    # Expected vehicles per time step
    expected_vehicles = vehicles_per_second * dt
    
    # Probabilistic approach to spawn vehicles
    if random.random() < expected_vehicles:
        try:
            add_random_delivery_vehicle()
        except Exception as e:
            # Catch and log any exceptions but don't let them crash the simulation
            print(f"Error spawning vehicle: {e}")
    
    # For higher rates
    if expected_vehicles > 1:
        for _ in range(expected_vehicles):
            try:
                add_random_delivery_vehicle()
            except Exception as e:
                # Catch and log any exceptions but don't let them crash the simulation
                print(f"Error spawning additional vehicle: {e}")
                continue


def create_delivery_vehicle_type():
    """
    Create a custom vehicle type for delivery vehicles with specific permissions. -> allowed to go into housing areas
    This is important for the simulation to work properly.
    """
    try:
        # Create a custom vehicle type with delivery permissions
        traci.vehicletype.copy("DEFAULT_VEHTYPE", "resident_type")
        
        # IMPORTANT: Set vehicle class to "delivery" - this is critical for route access in housing areas
        traci.vehicletype.setVehicleClass("resident_type", "delivery")
        
        traci.vehicletype.setColor("resident_type", (255, 0, 0, 255))  # Red color
        
    except traci.exceptions.TraCIException as e:
        print(f"Error creating custom vehicle type: {e}")