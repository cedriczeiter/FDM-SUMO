import os
import xml.etree.ElementTree as ET
from collections import defaultdict
import csv

# output folder creation
os.makedirs("output", exist_ok=True)

villages = ['erstfeld', 'goeschenen', 'gurtnellen', 'schattdorf', 'silenen', 'wassen']

for village in villages:
    
    print("-------------------------------------------------")

    
    # --- Configuration ---
    sensor_dir = f"data/czeiter_loop_output/{village}"  # Set this to your folder with the entry/exit XML files
    output_csv = f"output/reconstructed_trips_{village}.csv"
    
    # --- Step 1: Parse all XMLs into a vehicle map ---
    vehicles = defaultdict(lambda: {"entry": None, "exit": None})
    
    total_datapoints = 0
    for filename in os.listdir(sensor_dir):
        print(f"Parsing {filename}...")
    
        if not filename.startswith(village):
            print(f"Skipping {filename} (not starting with {village})")
            continue  # Skip irrelevant files
        if not filename.endswith(".xml"):
            print(f"Skipping {filename} (not an XML file)")
            continue
        filepath = os.path.join(sensor_dir, filename)
    
        is_entry = "entry" in filename
        is_exit = "exit" in filename
        if not (is_entry or is_exit):
            print(f"Skipping {filename} (not an entry or exit file)")
            continue  # Skip irrelevant files
    
        tree = ET.parse(filepath)
        root = tree.getroot()
    
        for elem in root.findall("instantOut"): # Get all 'instantOut' elements (the output of the sensors)
            total_datapoints += 1
            state = elem.get("state")
            if state != "enter" and state != "leave":
                continue  # Only care about entry and exit times
    
            vehID = elem.get("vehID")
            time = float(elem.get("time")) # saved as string in seconds originally
            edge_id_raw = elem.get("id")  # e.g., 'erstfeld_entry_A'
            vtype = elem.get("type")
            speed = float(elem.get("speed"))
    
            # Convert e.g. 'erstfeld_entry_A' → 'lane_entry_A'
            if is_entry:
                lane_id = edge_id_raw.replace(f"{village}_entry", "lane_entry")
            else:
                lane_id = edge_id_raw.replace(f"{village}_exit", "lane_exit")
                
            if state != "enter" and state != "leave":
                print(f"Skipping {filename} (unexpected state {state})")
                continue
            if is_entry and state == "enter":
                vehicles[vehID]["entry"] = {
                    "time": time,
                    "edge": lane_id,
                    "type": vtype,
                    "speed": speed
                }
            elif is_exit and state == "leave":
                vehicles[vehID]["exit"] = {
                    "time": time,
                    "edge": lane_id,
                    "type": vtype,
                    "speed": speed
                }
                
    
    # --- Step 2: Filter complete trips ---
    trips = []
    for vehID, data in vehicles.items():
        if data["entry"] and data["exit"]: # check if both entry and exit exist
            trips.append({
                "vehID": vehID,
                "depart": data["entry"]["time"],
                "from": data["entry"]["edge"],
                "to": data["exit"]["edge"],
                "arrival": data["exit"]["time"],
                "arrival_speed": data["exit"]["speed"],
                "type": data["entry"]["type"],  # use entry type; same
            })
    
    # --- Step 3: Save to CSV ---
    with open(output_csv, mode='w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "vehID", "depart", "from", "to", "arrival", "arrival_speed", "type"
        ])
        writer.writeheader()
        writer.writerows(trips)
    
    print(f"Saved {len(trips)} trips to {output_csv} from a total of {total_datapoints} datapoints in the xml files (contains in and out and each sensor at least enter and leave state (and some random vehicles that only leave or enter) -> x4 factor minimum is realistic)")
