import pandas as pd

villages = ['erstfeld', 'goeschenen', 'gurtnellen', 'schattdorf', 'silenen', 'wassen']

for village in villages:
 
    # Load your parsed exit data
    df = pd.read_csv(f"output/reconstructed_trips_{village}.csv") 
    
    # Extract relevant columns
    df_exit = df[["arrival", "to", "arrival_speed"]].copy()
    df_exit.rename(columns={"to": "exit_edge", "arrival": "time", "arrival_speed": "speed"}, inplace=True)
    
    # Determine simulation time range (rounded to full seconds)
    start_time = 0
    end_time = 3600*24 # full day of speeds
    
    # Get all unique exit edges
    exit_edges = sorted(df_exit["exit_edge"].unique())
    
    # Initialize storage with all -1 values
    exit_speed_map = {edge: [-1] * (end_time - start_time + 1) for edge in exit_edges}
    
    # First pass: record exact arrival times and speeds
    for _, row in df_exit.iterrows():
        t = int(row["time"]) - start_time
        edge = row["exit_edge"]
        speed = row["speed"]
        
        # Skip entries outside our time range
        if t < 0 or t >= len(exit_speed_map[edge]):
            continue
            
        # Set the current time speed
        exit_speed_map[edge][t] = speed
    
    # Second pass: fill gaps between arrivals properly
    for edge in exit_edges:
        last_speed = -1
        for t in range(len(exit_speed_map[edge])):
            if exit_speed_map[edge][t] != -1:
                # Found a new arrival, update the last_speed
                last_speed = exit_speed_map[edge][t]
            elif last_speed != -1:
                # Fill gaps with the last known speed
                exit_speed_map[edge][t] = last_speed
    
    # Create DataFrame
    time_index = list(range(start_time, end_time + 1))
    result_df = pd.DataFrame({"time": time_index})
    for edge in exit_edges:
        result_df[edge] = exit_speed_map[edge]
    
    # Save to CSV
    result_df.to_csv(f"output/20_11_exit_speeds_per_second_{village}.csv", index=False)
    print(f"output/20_11_exit_speeds_per_second_{village}.csv")
