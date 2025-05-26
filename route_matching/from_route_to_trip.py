import pandas as pd
import xml.etree.ElementTree as ET
villages = ['erstfeld', 'goeschenen', 'gurtnellen', 'schattdorf', 'silenen', 'wassen']

for village in villages:
    # Input CSV and output XML file names
    csv_file = f"output/reconstructed_trips_{village}.csv"
    output_xml = f"output/reconstructed_trips_{village}.trips.xml"
    
    # Load the CSV
    df = pd.read_csv(csv_file)
    df.sort_values(by="depart", inplace=True)
    # Create root <trips> element
    root = ET.Element("trips")
    
    # Populate trip elements
    for _, row in df.iterrows():
        trip = ET.SubElement(root, "trip")
        trip.set("id", row["vehID"])
        trip.set("depart", str(row["depart"]))
        trip.set("from", row["from"])
        trip.set("to", row["to"])
        trip.set("type", row["type"])
    
    # Save to XML
    tree = ET.ElementTree(root)
    tree.write(output_xml, encoding="utf-8", xml_declaration=True)
    
    print(f"SUMO trip file written to {output_xml}")
