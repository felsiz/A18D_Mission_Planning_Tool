"""
Map viewer module for visualizing PTM route files.
"""
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
import math
import os
import tkinter as tk
from tkinter import messagebox


def parse_xml_path(xml_file):
    """Parse XML file and extract route coordinates"""
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    segments = []
    arcs = []
    
    for element in root:
        if element.tag == "Segment":
            segment_data = extract_segment_data(element)
            if segment_data:
                segments.append(segment_data)
        elif element.tag == "Arc":
            arc_data = extract_arc_data(element)
            if arc_data:
                arcs.append(arc_data)
    
    return segments, arcs


def extract_segment_data(segment):
    """Extract segment data"""
    name = segment.find("Name")
    start_point = segment.find("StartPoint")
    end_point = segment.find("EndPoint")
    ghost_params = segment.find("GhostSectionParams")
    
    if start_point is None or end_point is None:
        return None
    
    start_lat = start_point.find("Latitude")
    start_lon = start_point.find("Longitude")
    end_lat = end_point.find("Latitude")
    end_lon = end_point.find("Longitude")
    
    # Check that coordinates are not empty
    if (start_lat is None or start_lon is None or 
        end_lat is None or end_lon is None or
        start_lat.text is None or start_lon.text is None or
        end_lat.text is None or end_lon.text is None or
        not start_lat.text.strip() or not start_lon.text.strip() or
        not end_lat.text.strip() or not end_lon.text.strip()):
        return None
    
    speed = 0
    phase_id = None
    if ghost_params is not None:
        speed_elem = ghost_params.find("Speed")
        phase_ids_elem = ghost_params.find("PhaseIds")
        if speed_elem is not None and speed_elem.text is not None:
            try:
                speed = float(speed_elem.text)
            except ValueError:
                speed = 0
        if phase_ids_elem is not None and phase_ids_elem.text is not None:
            phase_id = phase_ids_elem.text
    
    return {
        'type': 'segment',
        'name': name.text if name is not None else "Unknown",
        'start_lat': float(start_lat.text),
        'start_lon': float(start_lon.text),
        'end_lat': float(end_lat.text),
        'end_lon': float(end_lon.text),
        'speed': speed,
        'phase_id': phase_id
    }


def extract_arc_data(arc):
    """Extract arc data"""
    name = arc.find("Name")
    start_point = arc.find("StartPoint")
    end_point = arc.find("EndPoint")
    center = arc.find("Center")
    clockwise = arc.find("ClockWise")
    ghost_params = arc.find("GhostSectionParams")
    
    if start_point is None or end_point is None or center is None:
        return None
    
    start_lat = start_point.find("Latitude")
    start_lon = start_point.find("Longitude")
    end_lat = end_point.find("Latitude")
    end_lon = end_point.find("Longitude")
    center_lat = center.find("Latitude")
    center_lon = center.find("Longitude")
    
    if (start_lat is None or start_lon is None or 
        end_lat is None or end_lon is None or
        center_lat is None or center_lon is None or
        start_lat.text is None or start_lon.text is None or
        end_lat.text is None or end_lon.text is None or
        center_lat.text is None or center_lon.text is None):
        return None
    
    speed = 0
    phase_id = None
    if ghost_params is not None:
        speed_elem = ghost_params.find("Speed")
        phase_ids_elem = ghost_params.find("PhaseIds")
        if speed_elem is not None and speed_elem.text is not None:
            try:
                speed = float(speed_elem.text)
            except ValueError:
                speed = 0
        if phase_ids_elem is not None and phase_ids_elem.text is not None:
            phase_id = phase_ids_elem.text
    
    return {
        'type': 'arc',
        'name': name.text if name is not None else "Unknown",
        'start_lat': float(start_lat.text),
        'start_lon': float(start_lon.text),
        'end_lat': float(end_lat.text),
        'end_lon': float(end_lon.text),
        'center_lat': float(center_lat.text),
        'center_lon': float(center_lon.text),
        'clockwise': clockwise.text.lower() == 'true' if clockwise is not None and clockwise.text is not None else True,
        'speed': speed,
        'phase_id': phase_id
    }


def calculate_arc_points(start_lat, start_lon, end_lat, end_lon, center_lat, center_lon, clockwise=True, num_points=50):
    """Calculate arc points"""
    # Calculate angles from center to start and end points
    start_angle = math.atan2(start_lat - center_lat, start_lon - center_lon)
    end_angle = math.atan2(end_lat - center_lat, end_lon - center_lon)
    
    # Arc radius
    radius = math.sqrt((start_lat - center_lat)**2 + (start_lon - center_lon)**2)
    
    # Determine arc direction
    if clockwise:
        if end_angle > start_angle:
            end_angle -= 2 * math.pi
        angles = np.linspace(start_angle, end_angle, num_points)
    else:
        if end_angle < start_angle:
            end_angle += 2 * math.pi
        angles = np.linspace(start_angle, end_angle, num_points)
    
    # Calculate arc point coordinates
    lats = center_lat + radius * np.sin(angles)
    lons = center_lon + radius * np.cos(angles)
    
    return lats, lons


def find_ptm_files(folder_path):
    """Find all PTM files in the specified folder"""
    ptm_files = []
    for name in os.listdir(folder_path):
        if name.startswith('ptm.') and name.endswith('.xml') and name != 'ptm.expectedpath.xml':
            ptm_files.append(os.path.join(folder_path, name))
    return sorted(ptm_files)


def find_tpm_files(folder_path):
    """Find all TPM files in the specified folder"""
    tpm_files = []
    for name in os.listdir(folder_path):
        if name.startswith('tpm.') and name.endswith('.xml'):
            tpm_files.append(os.path.join(folder_path, name))
    return sorted(tpm_files)


def parse_tpm_file(tpm_file):
    """Parse TPM file and extract target point coordinates"""
    try:
        tree = ET.parse(tpm_file)
        root = tree.getroot()
        
        # Find LatLong element
        latlng = root.find('LatLong')
        if latlng is not None:
            lat_elem = latlng.find('Latitude')
            lon_elem = latlng.find('Longitude')
            
            if lat_elem is not None and lon_elem is not None:
                if lat_elem.text and lon_elem.text:
                    lat = float(lat_elem.text)
                    lon = float(lon_elem.text)
                else:
                    return None
                return {'lat': lat, 'lon': lon}
        
        return None
    except Exception as e:
        print(f"Error parsing TPM file {tpm_file}: {e}")
        return None


def meters_to_degrees(radius_meters, center_lat):
    """Convert radius in meters to degrees (lat/lon)"""
    import math
    
    # 1 degree latitude ≈ 111,320 meters everywhere
    lat_deg_radius = radius_meters / 111320.0
    
    # 1 degree longitude depends on latitude (cosine of latitude)
    lon_deg_radius = radius_meters / (111320.0 * math.cos(math.radians(center_lat)))
    
    return lat_deg_radius, lon_deg_radius


def create_circle_points(center_lat, center_lon, radius_meters, num_points=50):
    """Create circle points using the existing arc calculation logic"""
    import math
    
    # Convert radius to degrees
    lat_radius, lon_radius = meters_to_degrees(radius_meters, center_lat)
    
    # Create a full circle (0 to 2π)
    angles = [2 * math.pi * i / num_points for i in range(num_points + 1)]
    
    # Calculate circle points
    lats = [center_lat + lat_radius * math.sin(angle) for angle in angles]
    lons = [center_lon + lon_radius * math.cos(angle) for angle in angles]
    
    return lats, lons


def find_transit_phases_from_mission(mission_file):
    """Find TransitAuv and PathTrackingAuv phases from mission file"""
    try:
        tree = ET.parse(mission_file)
        root = tree.getroot()
        
        phases = []
        
        def traverse_phases(element, parent_path=""):
            for phase in element.findall('.//Phase'):
                phase_id = phase.get('Id')
                if phase_id is None:
                    continue
                    
                action = phase.find('Action/ActionImpl')
                if action is not None:
                    action_type = action.get('Type')
                    code_id = phase.find('CodeId')
                    
                    if action_type in ['TransitAuv', 'PathTrackingAuv'] and code_id is not None:
                        code_id_val = int(code_id.text) if code_id.text.isdigit() else -1
                        
                        phase_data = {
                            'phase_id': phase_id,
                            'code_id': code_id_val,
                            'type': action_type,
                            'point_model': None,
                            'path_model': None
                        }
                        
                        # Extract Point_Model for TransitAuv
                        if action_type == 'TransitAuv':
                            guidance_prms = action.find('GuidancePrms')
                            if guidance_prms is not None:
                                point_model = guidance_prms.find('Point_Model')
                                if point_model is not None and point_model.text:
                                    phase_data['point_model'] = point_model.text
                        
                        # Extract Path_Model for PathTrackingAuv
                        elif action_type == 'PathTrackingAuv':
                            guidance_prms = action.find('GuidancePrms')
                            if guidance_prms is not None:
                                path_model = guidance_prms.find('Path_Model')
                                if path_model is not None and path_model.text:
                                    phase_data['path_model'] = path_model.text
                        
                        phases.append(phase_data)
        
        traverse_phases(root)
        
        # Sort by code_id
        phases.sort(key=lambda x: x['code_id'])
        return phases
        
    except Exception as e:
        print(f"Error parsing mission file {mission_file}: {e}")
        return []


class EmbeddedMapViewer:
    """Embedded map viewer for integration into main window"""
    
    def __init__(self, parent_frame, folder_path):
        self.parent_frame = parent_frame
        self.folder_path = folder_path
        self.current_highlighted_path = None
        self.current_highlighted_paths = []
        self.current_highlighted_transit_keys = []
        self.route_data = {}
        self.transit_data = {}
        
        self.setup_ui()
        self.load_and_display_routes()
    
    def setup_ui(self):
        """Setup embedded map UI"""
        # Clear the parent frame
        for widget in self.parent_frame.winfo_children():
            widget.destroy()
        
        # Create matplotlib figure
        self.fig = Figure(figsize=(6, 6), dpi=80, facecolor='white')
        self.ax = self.fig.add_subplot(111)
        
        # Integrate matplotlib with tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, self.parent_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def load_and_display_routes(self):
        """Load PTM and TPM files and display routes"""
        try:
            # Find PTM and TPM files in folder
            ptm_files = find_ptm_files(self.folder_path)
            tpm_files = find_tpm_files(self.folder_path)
            
            if not ptm_files and not tpm_files:
                self.ax.text(0.5, 0.5, 'No PTM or TPM files found', 
                            horizontalalignment='center', verticalalignment='center',
                            transform=self.ax.transAxes, fontsize=12, color='red')
                self.canvas.draw()
                return
            
            # Clear previous plot
            self.ax.clear()
            
            # Initialize data structures
            all_segments = []
            all_arcs = []
            
            # Store route data for highlighting
            self.route_data = {}
            
            # Process each PTM file
            for ptm_file in ptm_files:
                try:
                    segments, arcs = parse_xml_path(ptm_file)
                    filename = os.path.basename(ptm_file)
                    
                    # Add filename info to each segment/arc
                    for seg in segments:
                        seg['source_file'] = filename
                    for arc_item in arcs:
                        arc_item['source_file'] = filename
                    
                    all_segments.extend(segments)
                    all_arcs.extend(arcs)
                    
                    # Store route data for highlighting
                    self.route_data[filename] = {
                        'segments': segments,
                        'arcs': arcs,
                        'plot_objects': []  # Will store matplotlib objects
                    }
                    
                except Exception as e:
                    print(f"Error processing {ptm_file}: {e}")
            
            # Process each TPM file (target points for TransitAuv phases)
            for tpm_file in tpm_files:
                try:
                    target_point = parse_tpm_file(tpm_file)
                    if target_point:
                        filename = os.path.basename(tpm_file)
                        
                        # Store TPM data for highlighting
                        self.route_data[filename] = {
                            'segments': [],
                            'arcs': [],
                            'target_point': target_point,
                            'plot_objects': []  # Will store matplotlib objects for the target point
                        }
                        
                except Exception as e:
                    print(f"Error processing {tpm_file}: {e}")
            
            if not all_segments and not all_arcs and not tpm_files:
                self.ax.text(0.5, 0.5, 'No valid route data found', 
                            horizontalalignment='center', verticalalignment='center',
                            transform=self.ax.transAxes, fontsize=12, color='red')
                self.canvas.draw()
                return
            
            # Draw routes
            self.plot_routes(all_segments, all_arcs)
            
            # Load and draw TransitAuv phases
            self.load_and_draw_transit_phases()
            
            # Load and draw CircleTrackingAuv phases
            self.load_and_draw_circle_phases()
            
        except Exception as e:
            print(f"Error loading routes: {str(e)}")
    
    def plot_routes(self, segments, arcs):
        """Draw routes on matplotlib axes"""
        all_lats = []
        all_lons = []
        
        # Colors for different files
        try:
            colors = plt.cm.tab10(np.linspace(0, 1, 10))  # type: ignore
        except AttributeError:
            # Fallback for older matplotlib versions
            colors = plt.cm.get_cmap('tab10')(np.linspace(0, 1, 10))
        file_colors = {}
        color_idx = 0
        
        # Draw segments
        for segment in segments:
            source_file = segment.get('source_file', 'Unknown')
            if source_file not in file_colors:
                file_colors[source_file] = colors[color_idx % len(colors)]
                color_idx += 1
            
            color = file_colors[source_file]
            
            line, = self.ax.plot([segment['start_lon'], segment['end_lon']], 
                        [segment['start_lat'], segment['end_lat']], 
                        '-', color=color, linewidth=2)
            
            # Store plot object for highlighting
            if source_file in self.route_data:
                self.route_data[source_file]['plot_objects'].append({
                    'type': 'segment',
                    'line': line,
                    'original_color': color,
                    'original_linewidth': 2,
                    'data': segment
                })
            
            all_lats.extend([segment['start_lat'], segment['end_lat']])
            all_lons.extend([segment['start_lon'], segment['end_lon']])
        
        # Draw arcs
        for arc in arcs:
            source_file = arc.get('source_file', 'Unknown')
            if source_file not in file_colors:
                file_colors[source_file] = colors[color_idx % len(colors)]
                color_idx += 1
            
            color = file_colors[source_file]
            
            # Calculate arc points
            arc_lats, arc_lons = calculate_arc_points(
                arc['start_lat'], arc['start_lon'],
                arc['end_lat'], arc['end_lon'],
                arc['center_lat'], arc['center_lon'],
                arc['clockwise']
            )
            
            self.ax.plot(arc_lons, arc_lats, '-', color=color, linewidth=2)
            
            all_lats.extend(arc_lats)
            all_lons.extend(arc_lons)
        
        # Draw TPM target points
        for filename, route_info in self.route_data.items():
            if 'target_point' in route_info and route_info['target_point']:
                target_point = route_info['target_point']
                
                # Get color for this TPM file
                if filename not in file_colors:
                    file_colors[filename] = colors[color_idx % len(colors)]
                    color_idx += 1
                
                color = file_colors[filename]
                
                # Draw target point as a larger marker
                marker = self.ax.plot(target_point['lon'], target_point['lat'], 
                                    'o', color=color, markersize=8, markerfacecolor=color, 
                                    markeredgecolor='white', markeredgewidth=1)
                
                # Store plot object for highlighting
                route_info['plot_objects'].append({
                    'type': 'target_point',
                    'marker': marker[0],  # plot returns a list with one element
                    'original_color': color,
                    'original_markersize': 8,
                    'data': target_point
                })
                
                # Add to bounds calculation
                all_lats.append(target_point['lat'])
                all_lons.append(target_point['lon'])
        
        # Setup map bounds — handle both normal routes and straight lines
        if all_lats and all_lons:
            # Calculate coordinate ranges
            lat_range = max(all_lats) - min(all_lats)
            lon_range = max(all_lons) - min(all_lons)
            
            # Set minimum range to prevent collapsing for straight lines
            min_range = 0.001  # About 100 meters at equator
            
            # Calculate margins - use percentage for normal ranges, minimum for straight lines
            if lat_range > min_range:
                lat_margin = lat_range * 0.05  # 5% margin for normal ranges
            else:
                lat_margin = min_range  # Fixed margin for straight lines
                
            if lon_range > min_range:
                lon_margin = lon_range * 0.05  # 5% margin for normal ranges  
            else:
                lon_margin = min_range  # Fixed margin for straight lines
            
            # Set bounds with calculated margins
            self.ax.set_xlim(min(all_lons) - lon_margin, max(all_lons) + lon_margin)
            self.ax.set_ylim(min(all_lats) - lat_margin, max(all_lats) + lat_margin)
            
            # Remove any extra Matplotlib padding so the figure occupies the container tightly
            try:
                self.ax.margins(0)
            except Exception:
                pass
            try:
                self.fig.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
            except Exception:
                pass
        
        # Remove axis labels, ticks, and title
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.ax.set_xlabel('')
        self.ax.set_ylabel('')
        self.ax.set_title('')
        
        self.ax.grid(True, alpha=0.3)
        self.ax.set_aspect('equal', adjustable='box')
                
        self.canvas.draw()
    
    def load_and_draw_transit_phases(self):
        """Load TransitAuv and PathTrackingAuv phases and draw transit lines"""
        try:
            # Find mission file in folder
            mission_files = []
            for name in os.listdir(self.folder_path):
                if name.startswith('mim.') and name.endswith('.xml'):
                    mission_files.append(os.path.join(self.folder_path, name))
            
            if not mission_files:
                return
            
            # Use the first mission file found
            mission_file = mission_files[0]
            
            # Get transit phases from mission file
            transit_phases = find_transit_phases_from_mission(mission_file)
            
            if not transit_phases:
                return
            
            # Load coordinates for each phase
            phase_coordinates = []
            for phase in transit_phases:
                coord_data = {
                    'phase_id': phase['phase_id'],
                    'code_id': phase['code_id'],
                    'type': phase['type'],
                    'start_point': None,
                    'end_point': None,
                    'tpm_file': None,
                    'ptm_file': None
                }
                
                if phase['type'] == 'TransitAuv' and phase['point_model']:
                    # Load TPM file for target point
                    tpm_file = os.path.join(self.folder_path, f"{phase['point_model']}.xml")
                    coord_data['tpm_file'] = phase['point_model']  # Store TPM filename
                    if os.path.exists(tpm_file):
                        target_point = parse_tpm_file(tpm_file)
                        if target_point:
                            coord_data['end_point'] = target_point
                
                elif phase['type'] == 'PathTrackingAuv' and phase['path_model']:
                    # Load PTM file to get last point of path
                    ptm_file = os.path.join(self.folder_path, f"{phase['path_model']}.xml")
                    coord_data['ptm_file'] = phase['path_model']  # Store PTM filename
                    if os.path.exists(ptm_file):
                        segments, arcs = parse_xml_path(ptm_file)
                        if segments:
                            # Use last point of last segment as the end of this phase
                            last_segment = segments[-1]
                            coord_data['end_point'] = {
                                'lat': last_segment['end_lat'],
                                'lon': last_segment['end_lon']
                            }
                        elif arcs:
                            # If no segments but has arcs, use last point of last arc
                            last_arc = arcs[-1]
                            coord_data['end_point'] = {
                                'lat': last_arc['end_lat'],
                                'lon': last_arc['end_lon']
                            }
                
                phase_coordinates.append(coord_data)
            
            # Draw transit lines between phases
            self.draw_transit_lines(phase_coordinates)
            
        except Exception as e:
            print(f"Error loading transit phases: {e}")
    
    def load_and_draw_circle_phases(self):
        """Load CircleTrackingAuv phases and draw circles"""
        try:
            # Find mission file in folder
            mission_files = []
            for name in os.listdir(self.folder_path):
                if name.startswith('mim.') and name.endswith('.xml'):
                    mission_files.append(os.path.join(self.folder_path, name))
            
            if not mission_files:
                return
            
            # Use the first mission file found
            mission_file = mission_files[0]
            
            # Parse mission file to find CircleTrackingAuv phases
            circle_phases = []
            circle_counter = 1  # Counter for phases without id
            
            try:
                tree = ET.parse(mission_file)
                root = tree.getroot()
                
                for phase in root.findall('.//Phase'):
                    phase_id = phase.get('Id') or phase.get('id')  # Try both Id and id
                    
                    # Find ActionImpl element within this phase
                    action_impl = phase.find('.//ActionImpl')
                    if action_impl is not None:
                        phase_type = action_impl.get('Type')
                        
                        if phase_type == 'CircleTrackingAuv':
                            # Use counter if no phase_id
                            if not phase_id:
                                phase_id = f"circle_{circle_counter}"
                                circle_counter += 1
                            
                            # Get Point_Model (center point)
                            point_model_elem = phase.find('.//Point_Model')
                            circle_radius_elem = phase.find('.//Circle_Radius_m')
                            
                            if point_model_elem is not None and circle_radius_elem is not None:
                                point_model = point_model_elem.text
                                if circle_radius_elem.text:
                                    radius_meters = float(circle_radius_elem.text)
                                else:
                                    continue
                                
                                circle_phases.append({
                                    'phase_id': phase_id,
                                    'point_model': point_model,
                                    'radius_meters': radius_meters
                                })
            
            except Exception as e:
                print(f"Error parsing mission file for circles: {e}")
                return
            
            if not circle_phases:
                return
            
            # Load coordinates for each circle phase
            circle_data = []
            for phase in circle_phases:
                if phase['point_model']:
                    # Load TPM file for center point
                    tpm_file = os.path.join(self.folder_path, f"{phase['point_model']}.xml")
                    if os.path.exists(tpm_file):
                        center_point = parse_tpm_file(tpm_file)
                        if center_point:
                            circle_data.append({
                                'phase_id': phase['phase_id'],
                                'center_lat': center_point['lat'],
                                'center_lon': center_point['lon'],
                                'radius_meters': phase['radius_meters']
                            })
            
            # Draw circles
            if circle_data:
                self.draw_circles(circle_data)
                
        except Exception as e:
            print(f"Error loading circle phases: {e}")
    
    def draw_transit_lines(self, phase_coordinates):
        """Draw transit lines between phases"""
        if len(phase_coordinates) < 2:
            return
        
        # Colors for transit lines (different from PTM routes)
        transit_colors = ['red', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']
        
        all_transit_lats = []
        all_transit_lons = []
        
        # Draw transit lines only for TransitAuv phases
        for i in range(len(phase_coordinates) - 1):
            current_phase = phase_coordinates[i]
            next_phase = phase_coordinates[i + 1]
            
            # Only create transit line if the NEXT phase is TransitAuv
            if next_phase['type'] != 'TransitAuv':
                continue
            
            # Skip if we don't have end point for current phase or if next phase doesn't have end point
            if not current_phase['end_point'] or not next_phase['end_point']:
                continue
            
            # Skip if current phase is phase_id 1 (ignore its end_point)
            if str(current_phase['phase_id']) == '1':
                continue
            
            # Draw line FROM end of current phase TO TPM point of TransitAuv phase
            start_point = current_phase['end_point']
            end_point = next_phase['end_point']
            
            # Choose color for this transit line
            color = transit_colors[i % len(transit_colors)]
            
            # Draw transit line
            line, = self.ax.plot([start_point['lon'], end_point['lon']], 
                        [start_point['lat'], end_point['lat']], 
                        '-', color=color, linewidth=2, alpha=0.8)
            
            # Store transit line data for highlighting
            transit_key = f"transit_{current_phase['phase_id']}_to_{next_phase['phase_id']}"
            self.transit_data[transit_key] = {
                'line': line,
                'from_phase': current_phase['phase_id'],
                'to_phase': next_phase['phase_id'],
                'from_tpm_file': current_phase.get('tpm_file'),
                'to_tpm_file': next_phase.get('tpm_file'),
                'from_ptm_file': current_phase.get('ptm_file'),
                'to_ptm_file': next_phase.get('ptm_file'),
                'original_color': color,
                'original_linewidth': 2
            }
            
            # Add coordinates to bounds calculation
            all_transit_lats.extend([start_point['lat'], end_point['lat']])
            all_transit_lons.extend([start_point['lon'], end_point['lon']])
        
        # Update map bounds to include transit lines
        if all_transit_lats and all_transit_lons:
            # Get current bounds
            current_xlim = self.ax.get_xlim()
            current_ylim = self.ax.get_ylim()
            
            # Extend bounds to include transit coordinates
            min_lon = min(min(all_transit_lons), current_xlim[0])
            max_lon = max(max(all_transit_lons), current_xlim[1])
            min_lat = min(min(all_transit_lats), current_ylim[0])
            max_lat = max(max(all_transit_lats), current_ylim[1])
            
            # Calculate new margins
            lat_range = max_lat - min_lat
            lon_range = max_lon - min_lon
            
            min_range = 0.001
            
            if lat_range > min_range:
                lat_margin = lat_range * 0.05
            else:
                lat_margin = min_range
                
            if lon_range > min_range:
                lon_margin = lon_range * 0.05
            else:
                lon_margin = min_range
            
            # Update bounds
            self.ax.set_xlim(min_lon - lon_margin, max_lon + lon_margin)
            self.ax.set_ylim(min_lat - lat_margin, max_lat + lat_margin)
        
        self.canvas.draw()
    
    def draw_circles(self, circle_data):
        """Draw circles on the map for CircleTrackingAuv phases"""
        if not circle_data or not self.ax:
            return
        
        all_circle_lats = []
        all_circle_lons = []
            
        for circle_info in circle_data:
            center_lat = circle_info['center_lat']
            center_lon = circle_info['center_lon'] 
            radius_meters = circle_info['radius_meters']
            phase_id = circle_info['phase_id']
            
            # Create circle points
            lats, lons = create_circle_points(center_lat, center_lon, radius_meters)
            
            # Add circle coordinates to bounds calculation
            all_circle_lats.extend(lats)
            all_circle_lons.extend(lons)
            
            # Draw the circle
            circle_line, = self.ax.plot(lons, lats, color='purple', linewidth=2, alpha=0.7)
            
            # Draw center point
            center_point, = self.ax.plot(center_lon, center_lat, 'o', color='purple', markersize=6)
            
            # Store circle data for highlighting
            circle_key = f"circle_{phase_id}"
            if not hasattr(self, 'circle_data'):
                self.circle_data = {}
            
            self.circle_data[circle_key] = {
                'circle_line': circle_line,
                'center_point': center_point,
                'phase_id': phase_id,
                'original_color': 'purple',
                'original_linewidth': 2
            }
        
        # Update map bounds to include circles
        if all_circle_lats and all_circle_lons:
            # Get current bounds
            current_xlim = self.ax.get_xlim()
            current_ylim = self.ax.get_ylim()
            
            # Extend bounds to include circle coordinates
            min_lon = min(min(all_circle_lons), current_xlim[0])
            max_lon = max(max(all_circle_lons), current_xlim[1])
            min_lat = min(min(all_circle_lats), current_ylim[0])
            max_lat = max(max(all_circle_lats), current_ylim[1])
            
            # Calculate new margins
            lat_range = max_lat - min_lat
            lon_range = max_lon - min_lon
            
            min_range = 0.001
            
            if lat_range > min_range:
                lat_margin = lat_range * 0.05
            else:
                lat_margin = min_range
                
            if lon_range > min_range:
                lon_margin = lon_range * 0.05
            else:
                lon_margin = min_range
            
            # Update bounds
            self.ax.set_xlim(min_lon - lon_margin, max_lon + lon_margin)
            self.ax.set_ylim(min_lat - lat_margin, max_lat + lat_margin)
        
        self.canvas.draw()
    
    def highlight_multiple_phases(self, selected_phases):
        """Highlight multiple phases on the map (both PTM routes and transit lines)"""
        if not selected_phases:
            return
        
        # Clear previous highlighting
        self.clear_highlighting()
        
        highlighted_files = []
        highlighted_transit_keys = []
        highlighted_circle_keys = []
        highlighted_something = False
        
        # Process each selected phase
        for phase_data in selected_phases:
            phase_id = phase_data['phase_id']
            phase_type = phase_data['phase_type']
            path_model = phase_data['path_model']
            
            # For PathTrackingAuv phases - highlight PTM routes
            if phase_type == 'PathTrackingAuv' and path_model and path_model != "—":
                # Try to find matching PTM route file
                if hasattr(self, 'route_data'):
                    target_file = None
                    for filename in self.route_data.keys():
                        if filename.startswith('ptm.') and (path_model in filename or filename.startswith(f"ptm.{path_model}")):
                            target_file = filename
                            break
                    
                    if target_file and target_file in self.route_data:
                        plot_objects = self.route_data[target_file]['plot_objects']
                        
                        for obj in plot_objects:
                            if obj['type'] == 'segment':
                                obj['line'].set_linewidth(4)
                                obj['line'].set_alpha(1.0)
                                highlighted_something = True
                        
                        if target_file not in highlighted_files:
                            highlighted_files.append(target_file)
            
            # For TransitAuv phases - highlight transit lines connected to this phase
            elif phase_type == 'TransitAuv':
                if hasattr(self, 'transit_data'):
                    for transit_key, transit_info in self.transit_data.items():
                        # Convert phase_id to string for comparison since transit phases use strings
                        # Only highlight incoming transit lines (where this phase is the 'to_phase')
                        # since TPM represents the finish point of the TransitAuv phase
                        if str(transit_info['to_phase']) == str(phase_id):
                            if transit_key not in highlighted_transit_keys:
                                # Highlight transit line
                                transit_info['line'].set_linewidth(4)
                                transit_info['line'].set_alpha(1.0)
                                highlighted_transit_keys.append(transit_key)
                                highlighted_something = True
            
            # For CircleTrackingAuv phases - highlight circles
            elif phase_type == 'CircleTrackingAuv':
                if hasattr(self, 'circle_data'):
                    circle_key = f"circle_{phase_id}"
                    if circle_key in self.circle_data:
                        circle_info = self.circle_data[circle_key]
                        # Highlight circle line and center point
                        circle_info['circle_line'].set_linewidth(4)
                        circle_info['circle_line'].set_alpha(1.0)
                        circle_info['center_point'].set_markersize(10)
                        highlighted_circle_keys.append(circle_key)
                        highlighted_something = True
                    else:
                        # Try to find by phase_id directly
                        for key, circle_info in self.circle_data.items():
                            if circle_info['phase_id'] == phase_id:
                                circle_info['circle_line'].set_linewidth(4)
                                circle_info['circle_line'].set_alpha(1.0)
                                circle_info['center_point'].set_markersize(10)
                                highlighted_circle_keys.append(key)
                                highlighted_something = True
                                break
        
        # Store highlighted items for clearing later
        self.current_highlighted_paths = highlighted_files
        self.current_highlighted_transit_keys = highlighted_transit_keys
        self.current_highlighted_circle_keys = highlighted_circle_keys
        
        if highlighted_something:
            self.canvas.draw()
    

    def clear_highlighting(self):
        """Clear all route highlighting"""
        needs_redraw = False
        
        # Clear single path highlighting
        if hasattr(self, 'current_highlighted_path') and self.current_highlighted_path:
            if hasattr(self, 'route_data') and self.current_highlighted_path in self.route_data:
                plot_objects = self.route_data[self.current_highlighted_path]['plot_objects']
                
                for obj in plot_objects:
                    if obj['type'] == 'segment':
                        # Restore original PTM segment appearance
                        obj['line'].set_color(obj['original_color'])
                        obj['line'].set_linewidth(obj['original_linewidth'])
                        obj['line'].set_alpha(0.7)
                        needs_redraw = True
                    elif obj['type'] == 'target_point':
                        # Restore original TPM point appearance
                        obj['marker'].set_markersize(obj['original_markersize'])
                        obj['marker'].set_markeredgewidth(1)
                        obj['marker'].set_markeredgecolor('white')
                        needs_redraw = True
            
            self.current_highlighted_path = None
        
        # Clear multiple paths highlighting
        if hasattr(self, 'current_highlighted_paths') and self.current_highlighted_paths:
            if hasattr(self, 'route_data'):
                for highlighted_path in self.current_highlighted_paths:
                    if highlighted_path in self.route_data:
                        plot_objects = self.route_data[highlighted_path]['plot_objects']
                        
                        for obj in plot_objects:
                            if obj['type'] == 'segment':
                                # Restore original PTM segment appearance
                                obj['line'].set_color(obj['original_color'])
                                obj['line'].set_linewidth(obj['original_linewidth'])
                                obj['line'].set_alpha(0.7)
                                needs_redraw = True
                            elif obj['type'] == 'target_point':
                                # Restore original TPM point appearance
                                obj['marker'].set_markersize(obj['original_markersize'])
                                obj['marker'].set_markeredgewidth(1)
                                obj['marker'].set_markeredgecolor('white')
                                needs_redraw = True
            
            self.current_highlighted_paths = []
        
        # Clear transit lines highlighting
        if hasattr(self, 'current_highlighted_transit_keys') and self.current_highlighted_transit_keys:
            if hasattr(self, 'transit_data'):
                for transit_key in self.current_highlighted_transit_keys:
                    if transit_key in self.transit_data:
                        transit_info = self.transit_data[transit_key]
                        # Restore original appearance
                        transit_info['line'].set_color(transit_info['original_color'])
                        transit_info['line'].set_linewidth(transit_info['original_linewidth'])
                        transit_info['line'].set_alpha(0.8)
                        needs_redraw = True
            
            self.current_highlighted_transit_keys = []
        
        # Clear circle highlighting
        if hasattr(self, 'current_highlighted_circle_keys') and self.current_highlighted_circle_keys:
            if hasattr(self, 'circle_data'):
                for circle_key in self.current_highlighted_circle_keys:
                    if circle_key in self.circle_data:
                        circle_info = self.circle_data[circle_key]
                        # Restore original appearance
                        circle_info['circle_line'].set_color(circle_info['original_color'])
                        circle_info['circle_line'].set_linewidth(circle_info['original_linewidth'])
                        circle_info['circle_line'].set_alpha(0.7)
                        circle_info['center_point'].set_markersize(6)  # Original size
                        needs_redraw = True
            
            self.current_highlighted_circle_keys = []
        
        # Clear all transit highlighting if no specific keys were stored
        if hasattr(self, 'transit_data'):
            for transit_key, transit_info in self.transit_data.items():
                # Reset to original appearance
                transit_info['line'].set_color(transit_info['original_color'])
                transit_info['line'].set_linewidth(transit_info['original_linewidth'])
                transit_info['line'].set_alpha(0.8)
                needs_redraw = True
        
        # Clear circle highlighting
        if hasattr(self, 'circle_data'):
            for circle_key, circle_info in self.circle_data.items():
                # Reset to original appearance
                circle_info['circle_line'].set_color(circle_info['original_color'])
                circle_info['circle_line'].set_linewidth(circle_info['original_linewidth'])
                circle_info['circle_line'].set_alpha(0.7)
                circle_info['center_point'].set_markersize(6)  # Original size
                needs_redraw = True
        
        if needs_redraw:
            self.canvas.draw()