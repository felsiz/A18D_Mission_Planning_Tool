"""
Data processing module for handling XML and JSON files.
Extracts mission data and payload configurations.
"""
import xml.etree.ElementTree as ET
import json
import glob
import os
import math


def find_mission_files(folder_path):
    """Find all mission XML files in the specified folder"""
    return glob.glob(os.path.join(folder_path, "mim.*.xml"))


def load_payload_configs(folder_path):
    """Load payload configurations from pl.*.json files"""
    payload_configs = {}
    
    pl_files = glob.glob(os.path.join(folder_path, "pl.*.json"))
    for pl_file in pl_files:
        try:
            with open(pl_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for item in data:
                if 'rule' in item and 'settings' in item['rule']:
                    # Extract phase_id from rule settings
                    phase_id = None
                    for setting in item['rule']['settings']:
                        if setting.get('name') == 'phase_id':
                            phase_id = setting.get('int')
                            break
                    
                    if phase_id is not None:
                        payload_name = item.get('payload', {}).get('name', '')
                        payload_alias = item.get('payload_alias', '')
                        
                        if phase_id not in payload_configs:
                            payload_configs[phase_id] = {}
                        
                        payload_configs[phase_id][payload_name] = payload_alias
        except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
            print(f"Error loading {pl_file}: {e}")
    
    return payload_configs


def calculate_distance_meters(lat1, lon1, lat2, lon2):
    """Calculate distance between two GPS coordinates using Haversine formula"""
    if any(coord is None for coord in [lat1, lon1, lat2, lon2]):
        return None
    
    # Convert latitude and longitude from degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = (math.sin(dlat/2)**2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2)
    c = 2 * math.asin(math.sqrt(a))
    
    # Earth radius in meters (average)
    earth_radius_m = 6371000
    
    # Calculate distance in meters
    distance = earth_radius_m * c
    return round(distance, 1)


def calculate_bearing(lat1, lon1, lat2, lon2):
    """Calculate bearing (direction) from point 1 to point 2 in degrees"""
    if any(coord is None for coord in [lat1, lon1, lat2, lon2]):
        return None
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2) 
    dlon_rad = math.radians(lon2 - lon1)
    
    # Calculate bearing
    y = math.sin(dlon_rad) * math.cos(lat2_rad)
    x = (math.cos(lat1_rad) * math.sin(lat2_rad) - 
         math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad))
    
    bearing_rad = math.atan2(y, x)
    bearing_deg = math.degrees(bearing_rad)
    
    # Normalize to 0-360 degrees
    bearing_deg = (bearing_deg + 360) % 360
    return bearing_deg


def calculate_destination_point(lat, lon, bearing_deg, distance_m):
    """Calculate destination point given start point, bearing and distance"""
    if any(param is None for param in [lat, lon, bearing_deg, distance_m]):
        return None, None
    
    # Earth radius in meters
    earth_radius_m = 6371000
    
    # Convert to radians
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    bearing_rad = math.radians(bearing_deg)
    
    # Angular distance
    angular_dist = distance_m / earth_radius_m
    
    # Calculate destination latitude
    dest_lat_rad = math.asin(
        math.sin(lat_rad) * math.cos(angular_dist) +
        math.cos(lat_rad) * math.sin(angular_dist) * math.cos(bearing_rad)
    )
    
    # Calculate destination longitude
    dest_lon_rad = lon_rad + math.atan2(
        math.sin(bearing_rad) * math.sin(angular_dist) * math.cos(lat_rad),
        math.cos(angular_dist) - math.sin(lat_rad) * math.sin(dest_lat_rad)
    )
    
    # Convert back to degrees
    dest_lat = math.degrees(dest_lat_rad)
    dest_lon = math.degrees(dest_lon_rad)
    
    return dest_lat, dest_lon


def calculate_vs_distance(folder_path, phase_id):
    """Calculate distance for VS phase using GPS coordinates from PTM file"""
    try:
        coordinates = get_route_coordinates_from_map_viewer(folder_path, phase_id)
        if coordinates:
            start_lat = coordinates.get('START_LAT')
            start_lon = coordinates.get('START_LON')
            end_lat = coordinates.get('END_LAT') 
            end_lon = coordinates.get('END_LON')
            
            distance = calculate_distance_meters(start_lat, start_lon, end_lat, end_lon)
            return distance
        return None
    except Exception:
        return None


def calculate_vs_angle(vs_start_depth, vs_end_depth, vs_distance):
    """Calculate VS angle using arctan(delta_depth / vs_distance)"""
    try:
        if vs_start_depth is None or vs_end_depth is None or vs_distance is None or vs_distance == 0:
            return None
        
        # Calculate delta depth (positive when going deeper)
        delta_depth = float(vs_end_depth) - float(vs_start_depth)
        
        # Calculate angle in radians using arctan
        angle_rad = math.atan(delta_depth / float(vs_distance))
        
        # Convert to degrees
        angle_deg = math.degrees(angle_rad)
        
        return round(angle_deg, 2)
    except (ValueError, TypeError, ZeroDivisionError):
        return None


def find_all_phase_ids_types_z(xml_path, payload_configs=None):
    """Extract phase information from XML mission file"""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    result = []

    def search_phases(phases):
        for phase in phases:
            if phase.tag == "Phase":
                phase_id = phase.attrib.get("Id")
                action_impl = phase.find("./Action/ActionImpl")
                phase_type = action_impl.attrib.get("Type") if action_impl is not None else "None"
                
                # Find Z/Depth
                z_col = "—"
                z_mode = None  # "Depth" or "Altitude" 
                z_value = None  # numeric value
                if action_impl is not None:
                    guidance = action_impl.find("GuidancePrms")
                    if guidance is not None:
                        z = guidance.find("Z")
                        z_is_alt = guidance.find("Z_Is_Alt")
                        depth = guidance.find("Depth")
                        if z is not None and z_is_alt is not None:
                            try:
                                z_value = round(float(z.text.strip()), 1)
                                if z_is_alt.text.strip().lower() == "true":
                                    z_col = f"Altitude: {z_value}"
                                    z_mode = "Altitude"
                                else:
                                    z_col = f"Depth: {z_value}"
                                    z_mode = "Depth"
                            except (ValueError, TypeError):
                                # Fallback to original text if conversion fails
                                if z_is_alt.text.strip().lower() == "true":
                                    z_col = f"Altitude: {z.text.strip()}"
                                    z_mode = "Altitude"
                                    try:
                                        z_value = float(z.text.strip())
                                    except:
                                        z_value = None
                                else:
                                    z_col = f"Depth: {z.text.strip()}"
                                    z_mode = "Depth"
                                    try:
                                        z_value = float(z.text.strip())
                                    except:
                                        z_value = None
                        elif depth is not None:
                            try:
                                depth_value = round(float(depth.text.strip()), 1)
                                z_col = f"Depth: {depth_value}"
                                z_mode = "Depth"
                                z_value = depth_value
                            except (ValueError, TypeError):
                                # Fallback to original text if conversion fails
                                z_col = f"Depth: {depth.text.strip()}"
                                z_mode = "Depth"
                                try:
                                    z_value = float(depth.text.strip())
                                except:
                                    z_value = None
                
                # Get speed from Transit_Speed
                speed_col = "—"
                path_model = "—"
                if action_impl is not None:
                    guidance = action_impl.find("GuidancePrms")
                    if guidance is not None:
                        transit_speed = guidance.find("Transit_Speed")
                        if transit_speed is not None:
                            try:
                                # Convert m/s to knots (divide by 0.514444445)
                                speed_ms = float(transit_speed.text.strip())
                                speed_kt = round(speed_ms / 0.514444445, 1)
                                speed_col = f"{speed_kt}"
                            except (ValueError, TypeError):
                                # Fallback to original text if conversion fails
                                speed_col = f"{transit_speed.text.strip()} m/s"
                        
                        # Extract Path_Model for PathTrackingAuv phases
                        path_model_elem = guidance.find("Path_Model")
                        if path_model_elem is not None and path_model_elem.text:
                            path_model = path_model_elem.text.strip()
                        
                        # Extract Point_Model for TransitAuv phases  
                        point_model_elem = guidance.find("Point_Model")
                        if point_model_elem is not None and point_model_elem.text:
                            path_model = point_model_elem.text.strip()
                
                # Get payload aliases from configurations
                wbms_alias = "—"
                sas_alias = "—"
                sbp_alias = "—"
                oas_enabled = "❌"  # Default to disabled OAS
                acominhibitor_enabled = "❌"  # Default to disabled AcComInhibitor
                phase_id_int = None  # Initialize phase_id_int
                if payload_configs:
                    try:
                        phase_id_int = int(phase_id)
                        if phase_id_int in payload_configs:
                            wbms_alias = payload_configs[phase_id_int].get('wbms', '—')
                            sas_alias = payload_configs[phase_id_int].get('sas', '—')
                            sbp_alias = payload_configs[phase_id_int].get('sbp', '—')
                            oas_alias = payload_configs[phase_id_int].get('oas', '—')
                            acominhibitor_alias = payload_configs[phase_id_int].get('acominhibitor', '—')
                            
                            # Check if OAS is WithObstacleAvoidance
                            if oas_alias == "WithObstacleAvoidance":
                                oas_enabled = "✓"  # Checkmark for OAS enabled
                            else:
                                oas_enabled = "❌"  # Three red X symbols for OAS absent/disabled
                            
                            # Check if AcComInhibitor is enabled (has any alias)
                            if acominhibitor_alias != "—":
                                acominhibitor_enabled = "✓"  # Checkmark for AcComInhibitor enabled
                            else:
                                acominhibitor_enabled = "❌"  # Red X for AcComInhibitor disabled
                    except (ValueError, TypeError):
                        phase_id_int = None  # Reset to None if conversion fails
                
                # Skip phases with type "None", "DeepDive", "GpsRelockAuv", "Delay" or "DeepAscent"
                # Also skip phase_id 1 if phase_id_int is valid
                if (phase_type not in ["None", "DeepDive", "DeepAscent", "GpsRelockAuv", "Delay"] and 
                    (phase_id_int is None or phase_id_int != 1)):
                    result.append((phase_id, phase_type, z_col, speed_col, wbms_alias, sas_alias, sbp_alias, path_model, oas_enabled, acominhibitor_enabled, z_mode, z_value))
                
                subphases = phase.find("Phases")
                if subphases is not None:
                    search_phases(subphases.findall("Phase"))

    phases_root = root.find("Phases")
    if phases_root is not None:
        search_phases(phases_root.findall("Phase"))

    return result


def get_route_coordinates_from_map_viewer(folder_path, phase_id):
    """Extract coordinates using same logic as map_viewer"""
    from . import map_viewer  # Import here to avoid circular imports
    import glob
    
    # Find MIM file to get path_model for the phase
    mim_files = glob.glob(os.path.join(folder_path, "mim.*.xml"))
    if not mim_files:
        return None
    
    mim_file = mim_files[0]
    
    # Parse MIM file to find path_model for the given phase_id
    path_model = None
    try:
        tree = ET.parse(mim_file)
        root = tree.getroot()
        
        for phase in root.findall('.//Phase'):
            phase_id_attr = phase.get('Id') or phase.get('id')
            if phase_id_attr == str(phase_id):
                # Find PathTrackingAuv action within this phase - try both attribute formats
                path_tracking = phase.find('.//ActionImpl[@Type="PathTrackingAuv"]')
                if path_tracking is None:
                    path_tracking = phase.find('.//ActionImpl[@type="PathTrackingAuv"]')
                
                if path_tracking is not None:
                    # Try different possible element names
                    path_model_elem = path_tracking.find('.//Path_Model')
                    if path_model_elem is None:
                        path_model_elem = path_tracking.find('.//Path_model')
                    if path_model_elem is None:
                        path_model_elem = path_tracking.find('.//PathModel')
                    
                    if path_model_elem is not None and path_model_elem.text:
                        path_model = path_model_elem.text
                        break
    except Exception as e:
        return None
    
    if not path_model:
        return None
    
    # Find PTM files using same function as map viewer
    ptm_files = map_viewer.find_ptm_files(folder_path)
    
    # Find matching PTM file using path_model
    # path_model is like "ptm.PL5", we need to extract "PL5" part
    if path_model.startswith('ptm.'):
        route_name = path_model[4:]  # Remove "ptm." prefix
    else:
        route_name = path_model
    
    matching_file = None
    for ptm_file in ptm_files:
        filename = os.path.basename(ptm_file)
        # Look for ptm.{route_name}.xml
        expected_filename = f"ptm.{route_name}.xml"
        if filename == expected_filename:
            matching_file = ptm_file
            break
    
    if not matching_file:
        return None
    
    try:
        # Use same parsing logic as map viewer
        segments, arcs = map_viewer.parse_xml_path(matching_file)
        
        if not segments and not arcs:
            return None
        
        # Get coordinates from first and last elements
        start_coords = None
        end_coords = None
        
        # Try to get from segments first
        if segments:
            first_segment = segments[0]
            last_segment = segments[-1]
            
            start_coords = (first_segment.get('start_lat'), first_segment.get('start_lon'))
            end_coords = (last_segment.get('end_lat'), last_segment.get('end_lon'))
        
        # If no segments, try arcs
        elif arcs:
            first_arc = arcs[0]
            last_arc = arcs[-1]
            
            start_coords = (first_arc.get('start_lat'), first_arc.get('start_lon'))
            end_coords = (last_arc.get('end_lat'), last_arc.get('end_lon'))
        
        if start_coords and end_coords and all(coord is not None for coord in start_coords + end_coords):
            result = {
                'START_LAT': float(start_coords[0]),
                'START_LON': float(start_coords[1]),
                'END_LAT': float(end_coords[0]),
                'END_LON': float(end_coords[1])
            }
            return result
    
    except Exception as e:
        pass  # Silently fail, return None
    
    return None

