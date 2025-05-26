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
import pandas as pd
import requests

from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from helper import convert_sumo_coordinates_to_lat_lon, printv
from config import GRID_LEFT, GRID_RIGHT, GRID_BOTTOM, GRID_TOP



#########################################
# Functions
#########################################  

def create_geolocator(user_agent="bachelor_thesis_eth", delay=1.0, verbose=False):
    """
    Create a geolocator and rate-limited reverse geocode function.

    Args:
        user_agent(str): Name under which the API will see me
        delay(float): In seconds, delay of api-calls, minimum 1.0s
        verbose(bool): If more stuff should be printed

    Returns:
        function: A rate-limited reverse geocoding function.

    """
    printv("Start function create_geolocator", verbose=verbose, color="blue")

    delay = min(delay, 3.0)

    geolocator = Nominatim(user_agent=user_agent)
    geocode = RateLimiter(geolocator.reverse, min_delay_seconds=delay)
    return geocode


def get_building_info(lat, lon, geocode_func, verbose=False):
    """
    Query Nominatim reverse geocoder for a building at (lat, lon) and try to fetch its polygon.

    Args:
        lat (float): Latitude in degrees.
        lon (float): Longitude in degrees.
        geocode_func (function): Geolocator function for reverse calls
        verbose(bool): If more stuff should be printed

    Returns:
        dictionary with all kinds of data about the given lat, lon

    """
    printv("Start function get_building_info", verbose=verbose, color="blue")

    try:
        location = geocode_func((lat, lon), exactly_one=True)
        if location:
            address = location.raw.get('address', {})
            osm_id = location.raw.get('osm_id')
            osm_type = location.raw.get('osm_type')

            polygon = None

            # Try to fetch polygon if type and id are available
            if osm_id and osm_type:
                try:
                    # Convert type to Overpass API style: N, W, R
                    type_map = {"node": "N", "way": "W", "relation": "R"}
                    osm_type_letter = type_map.get(osm_type)

                    if osm_type_letter:
                        overpass_url = "https://overpass-api.de/api/interpreter"
                        query = f"""
                        [out:json];
                        {osm_type}({osm_id});
                        out body;
                        >;
                        out skel qt;
                        """
                        response = requests.post(overpass_url, data=query)
                        if response.status_code == 200:
                            data = response.json()

                            # Check if this way is a house/residential building
                            is_house = False
                            building_type = None

                            for elem in data['elements']:
                                if elem['type'] == 'way' and 'tags' in elem:
                                    tags = elem.get('tags', {})

                                    print(
                                        "house type (check for weird stuff):", tags.get('building'))
                                    # Check building tag (manually saw that besides the normal housing names, sometimes OSM also just hase house: yes)
                                    if tags.get('building') in ['house', 'residential', 'detached', 'semidetached_house',
                                                                'terrace', 'apartments', 'hotel', 'farm_auxiliary', 'yes', 'farm', 'farm_auxiliary', 'bungalow', 'cabin', 'annexe', 'dormitory', 'static_caravan']:
                                        is_house = True
                                        building_type = tags.get('building')
                                        break

                            # Only if it is a building where people live
                            if is_house:
                                nodes = {elem['id']: (
                                    elem['lon'], elem['lat']) for elem in data['elements'] if elem['type'] == 'node'}
                                for elem in data['elements']:
                                    if elem['type'] == 'way' and 'nodes' in elem:
                                        coords = [
                                            nodes[node_id] for node_id in elem['nodes'] if node_id in nodes]
                                        if coords:
                                            polygon = "POLYGON((" + ", ".join(
                                                f"{lon} {lat}" for lon, lat in coords) + "))"
                                            break

                            else:
                                # If it is not a house, just return the data without polygon
                                polygon = None
                                is_house = False
                                building_type = None

                            # Add building type to the return data
                            return {
                                'lat': lat,
                                'lon': lon,
                                'place_id': location.raw.get('place_id'),
                                'osm_type': osm_type,
                                'osm_id': osm_id,
                                'house_number': address.get('house_number'),
                                'road': address.get('road'),
                                'polygon': polygon,
                                'village': address.get('village'),
                                'state': address.get('state'),
                                'postcode': address.get('postcode'),
                                'bounding_box': location.raw.get('boundingbox'),
                                'building_type': building_type,
                                'is_house': is_house
                            }
                except Exception as e:
                    printv(f"[WARNING] Failed to fetch OSM polygon: {e}", verbose=verbose, color="red")

            return {
                'lat': lat,
                'lon': lon,
                'place_id': location.raw.get('place_id'),
                'osm_type': osm_type,
                'osm_id': osm_id,
                'house_number': address.get('house_number'),
                'road': address.get('road'),
                'polygon': polygon,
                'village': address.get('village'),
                'state': address.get('state'),
                'postcode': address.get('postcode'),
                'bounding_box': location.raw.get('boundingbox')
            }
    except Exception as e:
        printv(f"[ERROR] ({lat}, {lon}): {e}", verbose=verbose, color="red")

    return {
        'lat': lat,
        'lon': lon,
        'place_id': None,
        'osm_type': None,
        'osm_id': None,
        'house_number': None,
        'road': None,
        'polygon': None,
        'village': None,
        'state': None,
        'postcode': None,
        'bounding_box': None
    }


def get_house_polygons(list_coords, netfile, recalculate=False, verbose=True, output_dir="../output/temp"):
    """
    Convert multiple SUMO coordinates to lat/lon and retrieve building info from Nominatim API.

    Note:
        This is not perfect. Some API-calls dont find the houses but roads instead and will just be discarted

    Args:
        list_coords (list of (x, y)): SUMO coordinates.
        netfile (str): Path to SUMO .net.xml file.
        recalculate (bool): If True, force re-fetching data.
        verbose (bool): Print extra info.
        output_dir (str): Directory to store result CSV.

    Returns:
        pd.DataFrame: DataFrame with lat, lon, bounding_box and Polygon shape for all given coords.
    """

    printv("Start function get_house_polygons",
           verbose=verbose, color="blue", decorate=True)

    if len(list_coords) == 0:
        printv("No coordinates found in the people data get_house_polygons.", True, "red")
        return pd.DataFrame()

    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(
        output_dir,
        f"house_polygons_{GRID_LEFT}_{GRID_RIGHT}_{GRID_BOTTOM}_{GRID_TOP}.csv"
    )

    # Check if output file already exists and if we should recalculate (caching)
    if not recalculate and os.path.exists(output_file):
        printv(f"Loading existing data from {output_file}", verbose=verbose)
        return pd.read_csv(output_file)

    # Convert SUMO to lat/lon
    printv("Start converting latlon coords", verbose=verbose)
    latlon_coords = [convert_sumo_coordinates_to_lat_lon(x, y, netfile) for x, y in list_coords]

    # Set up geocode function
    geocode = create_geolocator()

    printv("Start fetching information", verbose=verbose)
    # Fetch building info
    records = [get_building_info(lat, lon, geocode) for lat, lon in latlon_coords]

    # Make dataframe out of records
    df = pd.DataFrame(records)

    # only keep the ones of type "way", the rest are api errors
    house_polygons = df[df['osm_type'] == 'way'].copy()

    # Only keep rows with is_house == True
    house_polygons = house_polygons[house_polygons['is_house'] == True].copy()

    # Keep only relevant columns
    house_polygons = house_polygons[['lat', 'lon', 'bounding_box', 'polygon']]

    # Deduplicate based on osm_id (only keep unique buildings)
    if 'osm_id' in house_polygons.columns:
        house_polygons = house_polygons.dropna(subset=['osm_id']).drop_duplicates(subset=['osm_id'])

    house_polygons.to_csv(output_file, index=False)

    printv(f"Saved data to {output_file}", verbose=verbose)

    return house_polygons
