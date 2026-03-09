"""
Main application entry point for WBMS Mission Planning Tool.
Modular version using separate modules in src/ directory.
"""
import sys
import os
import tkinter as tk
from tkinter import ttk
from typing import Optional, Any
from tkinter import filedialog, messagebox
import yaml
import csv

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Constants
VS_CONFIGURE_TEXT = "Press Me"

from src.data_processor import find_mission_files, load_payload_configs, find_all_phase_ids_types_z, get_route_coordinates_from_map_viewer
from src.preset_manager import load_presets, auto_assign_from_wbms, PresetEditorWindow
from src.map_viewer import EmbeddedMapViewer
from src.gui_components import (
    create_main_window, create_menu_bar, create_treeview, 
    create_control_panel, auto_adjust_columns, setup_preset_dropdown_interaction,
    show_info_message, show_error_message
)
try:
    from src.vs_config import VSConfigWindow
except Exception:
    VSConfigWindow = None


class PresetManagerApp:
    """Main application class for WBMS Mission Planning Tool"""
    
    def __init__(self):
        self.root = create_main_window()
        self.tree: Optional[ttk.Treeview] = None
        self.selected_file_var: Optional[tk.StringVar] = None
        self.preset_combo: Optional[ttk.Combobox] = None
        self.presets = load_presets()
        self.selected_xml_path: Optional[str] = None
        self.current_folder: Optional[str] = None
        self.embedded_map: Optional[Any] = None  # Store reference to embedded map viewer
        # VS configurations: mapping phase_id (int) -> { subphase_id: {...}, ... }
        self.vs_configurations: dict[int, dict] = {}
        self.tips_enabled = tk.BooleanVar(value=True)  # Tips enabled by default
        
        self.setup_gui()
        self.setup_callbacks()
    
    def setup_gui(self):
        """Initialize GUI components"""
        # Create menu bar
        menu_callbacks = {
            'select_folder': self.load_folder,
            'edit_presets': self.open_presets_editor
        }
        create_menu_bar(self.root, menu_callbacks, self.tips_enabled)
        
        # Create main TreeView
        self.tree = create_treeview(self.root, self.initialize_map, self.tips_enabled)
        
        # Create control panel
        control_callbacks = {
            'load_folder': self.load_folder,
            'assign_preset': self.assign_preset,
            'auto_assign': self.auto_assign_from_wbms,
            'clear_preset': self.clear_preset,
            'save_mission_params': self.save_mission_params_to_yaml,
            'load_mission_params': self.load_mission_params_from_yaml,
            'export_csv': self.export_to_csv
        }
        
        control_frame, self.selected_file_var, self.preset_combo = create_control_panel(
            self.root, self.presets, control_callbacks, self.tips_enabled
        )
        
        # Setup preset dropdown interaction
        setup_preset_dropdown_interaction(
            self.tree, self.presets, self.preset_combo, self.reload_presets
        )
    
    def setup_callbacks(self):
        """Setup additional event callbacks"""
        if not self.tree:
            return
            
        # Bind resize event to auto-adjust columns
        def on_tree_configure(event):
            if self.tree and self.tree.get_children():  # Only adjust if there's data
                self.root.after(10, lambda: auto_adjust_columns(self.tree))
        
        self.tree.bind('<Configure>', on_tree_configure)
        
        # Bind selection event for map highlighting
        self.tree.bind("<<TreeviewSelect>>", self.on_phase_select)
        
        # Bind events for VS columns editing and general clicks
        self.tree.bind("<Button-1>", self.on_tree_click_unified)
        self.tree.bind("<Double-Button-1>", self.on_tree_double_click)
        
        # Also bind click on main window to deselect
        def on_window_click(event):
            # Only clear selection if click is not on the TreeView or buttons
            if not self.tree:
                return
            widget_class = event.widget.__class__.__name__
            if (event.widget != self.tree and 
                not str(event.widget).startswith(str(self.tree)) and
                widget_class not in ['Button', 'Combobox', 'Entry', 'Checkbutton', 'TButton', 'TCombobox', 'TEntry']):
                if hasattr(self.tree, 'selection') and self.tree.selection():
                    self.tree.selection_remove(self.tree.selection())
        
        self.root.bind('<Button-1>', on_window_click, add=True)
    
    def load_folder(self):
        """Load folder containing mission and payload files"""
        folder_path = filedialog.askdirectory(title="Select folder containing mission and payload files")
        if folder_path:
            self.current_folder = folder_path
            
            # Find all mission XML files in the folder
            xml_files = find_mission_files(folder_path)
            
            if not xml_files:
                show_error_message("Error", "No mission files (mim.*.xml) found in the selected folder")
                return
            
            # Load payload configurations from JSON files in the folder
            payload_configs = load_payload_configs(folder_path)
            
            # Use the first found mission file
            self.selected_xml_path = xml_files[0]
            if self.selected_file_var:
                self.selected_file_var.set(self.selected_xml_path)
            
            # Load and display data
            self.load_xml_data(payload_configs)
    
    def load_xml_data(self, payload_configs):
        """Load XML data and populate TreeView"""
        if not self.selected_xml_path:
            return
        
        try:
            # Clear existing data
            if self.tree:
                for item in self.tree.get_children():
                    self.tree.delete(item)
            
            # Get phase data from XML
            phases_data = find_all_phase_ids_types_z(self.selected_xml_path, payload_configs)
            
            # Populate TreeView
            if self.tree:
                all_phases_data = []  # Store for VS End calculation
                for phase_id, phase_type, z_col, speed_col, wbms_alias, sas_alias, sbp_alias, path_model, oas_enabled, acominhibitor_enabled, z_mode, z_value in phases_data:
                    all_phases_data.append((phase_id, phase_type, z_col, speed_col, wbms_alias, sas_alias, sbp_alias, path_model, oas_enabled, acominhibitor_enabled, z_mode, z_value))
                
                # Insert data with VS columns
                for i, (phase_id, phase_type, z_col, speed_col, wbms_alias, sas_alias, sbp_alias, path_model, oas_enabled, acominhibitor_enabled, z_mode, z_value) in enumerate(all_phases_data):
                    # Determine Enable VS checkbox - only show for eligible phases
                    enable_vs = ""  # Default empty
                    if phase_type == "PathTrackingAuv" and z_mode == "Depth":
                        enable_vs = "☐"  # Can be enabled
                    
                    # Note: VS per-phase subphases are configured in a separate window.
                    # Configure VS cell will be a clickable text only when enabled
                    configure_text = ""
                    if phase_type == "PathTrackingAuv" and z_mode == "Depth" and enable_vs == "☑":
                        configure_text = VS_CONFIGURE_TEXT

                    self.tree.insert("", "end", values=(
                        phase_id, phase_type, path_model, oas_enabled, z_col, speed_col,
                        sbp_alias, sas_alias, acominhibitor_enabled, wbms_alias, "", enable_vs, configure_text
                    ))
            
            # Auto-adjust column widths
            self.root.after(100, lambda: auto_adjust_columns(self.tree))

            # Initialize and update map when data is loaded
            if self.current_folder:
                try:
                    # Initialize map if not done yet
                    if not hasattr(self, 'embedded_map') or not self.embedded_map:
                        if hasattr(self.tree, 'map_frame'):
                            self.embedded_map = EmbeddedMapViewer(self.tree.map_frame, self.current_folder)  # type: ignore
                    
                    # Update map with new folder data
                    if hasattr(self, 'embedded_map') and self.embedded_map:
                        self.embedded_map.folder_path = self.current_folder
                        self.embedded_map.load_and_display_routes()
                except Exception as map_error:
                    print(f"Error initializing/updating map: {map_error}")
            
        except Exception as e:
            show_error_message("Error", f"Error loading XML data: {str(e)}")
    
    def assign_preset(self, preset_name):
        """Assign preset to selected phases"""
        if not self.tree:
            return
        selected = self.tree.selection()
        if not selected:
            show_error_message("No selection", "No phases selected to assign preset.")
            return
        
        for item in selected:
            self.tree.set(item, column="Preset", value=preset_name)
            # Remove any highlighting
            self.tree.item(item, tags=())
        
        # Auto-adjust column widths after assignment
        auto_adjust_columns(self.tree)
    
    def clear_preset(self):
        """Clear preset for selected item"""
        if not self.tree:
            return
        selected = self.tree.selection()
        if not selected:
            show_error_message("No selection", "No phases selected to clear preset.")
            return
        
        for item in selected:
            self.tree.set(item, column="Preset", value="")
            # Remove any highlighting tags
            self.tree.item(item, tags=())
        
        # Auto-adjust column widths after clearing
        auto_adjust_columns(self.tree)
    
    def auto_assign_from_wbms(self):
        """Automatically assign presets from WBMS payload column"""
        if not self.tree or not self.tree.get_children():
            show_error_message("No data", "No data loaded to auto-assign presets.")
            return
        
        auto_assign_from_wbms(self.tree, self.presets)
        
        # Auto-adjust column widths after auto-assignment
        auto_adjust_columns(self.tree)
    
    def reload_presets(self):
        """Reload presets from YAML file and update the dropdown"""
        self.presets = load_presets()
        if self.preset_combo:
            self.preset_combo['values'] = self.presets
            if self.presets:
                self.preset_combo.current(0)
        
        # Update preset dropdown interaction
        setup_preset_dropdown_interaction(
            self.tree, self.presets, self.preset_combo, self.reload_presets
        )
        
        show_info_message("Success", f"Reloaded {len(self.presets)} presets from file")
    
    def open_presets_editor(self):
        """Open preset editor window"""
        PresetEditorWindow(self.root, reload_callback=self.reload_presets)
    
    def initialize_map(self):
        """Initialize embedded map viewer"""
        if not self.current_folder:
            show_error_message("No folder", "Please select a folder with mission files first")
            return
        
        # Initialize map if not done yet
        if not hasattr(self, 'embedded_map') or not self.embedded_map:
            if hasattr(self.tree, 'map_frame'):
                self.embedded_map = EmbeddedMapViewer(self.tree.map_frame, self.current_folder)  # type: ignore
            else:
                show_error_message("Map Error", "Map display area not found")
    
    def toggle_map(self):
        """Toggle embedded map visibility"""
        if hasattr(self.tree, 'map_toggle'):
            self.tree.map_toggle()  # type: ignore
        else:
            show_error_message("Map Error", "Map toggle function not found")
    
    def on_phase_select(self, event):
        """Handle phase selection in tree for map highlighting"""
        if not hasattr(self, 'embedded_map') or not self.embedded_map or not self.tree:
            return
        
        selected = self.tree.selection()
        if not selected:
            # Clear highlighting if nothing selected
            if hasattr(self.embedded_map, 'clear_highlighting'):
                self.embedded_map.clear_highlighting()
            return
        
        # Get selected phase data - process ALL selected items
        selected_phases = []
        for item in selected:
            values = self.tree.item(item)['values']
            if len(values) >= 13:  # Check if we have all columns including AcComInhibitor
                phase_id = values[0]
                phase_type = values[1]
                path_model = values[2]  # Path_model is at index 2
                
                phase_data = {
                    'phase_id': phase_id,
                    'phase_type': phase_type,
                    'path_model': path_model
                }
                selected_phases.append(phase_data)
        
        # Highlight all selected phases or clear if none
        if selected_phases and hasattr(self.embedded_map, 'highlight_multiple_phases'):
            self.embedded_map.highlight_multiple_phases(selected_phases)
        else:
            # No phases selected - clear highlighting
            if hasattr(self.embedded_map, 'clear_highlighting'):
                self.embedded_map.clear_highlighting()
    
    def save_mission_params_to_yaml(self):
        """Save both WBMS presets and VS settings to unified YAML file"""
        if not self.tree or not self.current_folder or not self.selected_xml_path:
            show_error_message("No data", "No mission data loaded to save parameters.")
            return
        
        # ========== Collect WBMS Presets ==========
        wbms_params = {}
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            if len(values) >= 13:
                phase_id = values[0]
                preset = values[10]  # Preset column
                if preset:  # Only save if preset is assigned
                    wbms_params[int(phase_id)] = preset
        
        # ========== Generate VS Params with Coordinates ==========
        vs_phases = {}
        
        # Build a speed lookup from tree data
        speed_lookup = {}
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            if len(values) >= 13:
                phase_id = int(values[0])
                speed_text = str(values[5])  # Speed column
                try:
                    speed_lookup[phase_id] = float(speed_text)
                except (ValueError, TypeError):
                    speed_lookup[phase_id] = 2.0  # Default speed
        
        for phase_id, subphases in self.vs_configurations.items():
            if not subphases:  # Skip phases with no subphases
                continue
                
            try:
                # Get phase start/end coordinates from PTM
                from src.data_processor import get_route_coordinates_from_map_viewer, calculate_bearing, calculate_destination_point
                coordinates = get_route_coordinates_from_map_viewer(self.current_folder, phase_id)
                if not coordinates:
                    continue
                    
                phase_start_lat = coordinates.get('START_LAT')
                phase_start_lon = coordinates.get('START_LON')
                phase_end_lat = coordinates.get('END_LAT')
                phase_end_lon = coordinates.get('END_LON')
                
                if any(coord is None for coord in [phase_start_lat, phase_start_lon, phase_end_lat, phase_end_lon]):
                    continue
                
                # Calculate bearing from phase start to phase end
                bearing = calculate_bearing(phase_start_lat, phase_start_lon, phase_end_lat, phase_end_lon)
                if bearing is None:
                    continue
                
                # Get speed for this phase (convert from kt to m/s)
                phase_speed_kt = speed_lookup.get(phase_id, 2.0)
                phase_speed_ms = phase_speed_kt * 0.514444  # Convert knots to m/s
                
                # Sort subphases by ID
                subphase_keys = [k for k in subphases.keys() if isinstance(k, str) and '-' in k]
                subphase_keys.sort(key=lambda s: [int(x) if x.isdigit() else x for x in s.split('-')])
                
                # Generate coordinates for each subphase
                current_lat = phase_start_lat
                current_lon = phase_start_lon
                cumulative_distance = 0
                
                vs_phases[phase_id] = {}
                
                for subphase_id in subphase_keys:
                    subphase_data = subphases[subphase_id]
                    
                    # Get distance for this subphase
                    distance = 0
                    try:
                        distance_val = subphase_data.get('DISTANCE', '')
                        if distance_val:
                            distance = float(distance_val)
                    except (ValueError, TypeError):
                        distance = 0
                    
                    # Get depths
                    start_z = subphase_data.get('START_Z', '')
                    end_z = subphase_data.get('END_Z', '')
                    
                    try:
                        start_z = float(start_z) if start_z else 0.0
                        end_z = float(end_z) if end_z else 0.0
                    except (ValueError, TypeError):
                        start_z = 0.0
                        end_z = 0.0
                    
                    # Calculate end coordinates
                    if distance > 0:
                        end_lat, end_lon = calculate_destination_point(current_lat, current_lon, bearing, distance)
                        if end_lat is None or end_lon is None:
                            end_lat, end_lon = current_lat, current_lon
                    else:
                        end_lat, end_lon = current_lat, current_lon
                    
                    # Create subphase entry
                    vs_phases[phase_id][subphase_id] = {
                        'START_LAT': round(current_lat, 9),
                        'START_LON': round(current_lon, 9),
                        'START_Z': start_z,
                        'END_LAT': round(end_lat, 9),
                        'END_LON': round(end_lon, 9),
                        'END_Z': end_z,
                        'SPEED': round(phase_speed_ms, 8)
                    }
                    
                    # Next subphase starts where this one ends
                    current_lat = end_lat
                    current_lon = end_lon
                    
            except Exception as e:
                print(f"Error generating coordinates for phase {phase_id}: {e}")
                continue
        
        # Generate default filename
        mission_name = "mission"
        if self.selected_xml_path:
            base = os.path.basename(self.selected_xml_path)
            name_no_ext = os.path.splitext(base)[0]
            if 'mim.' in name_no_ext:
                parts = name_no_ext.split('mim.', 1)
                mission_name = parts[1] if len(parts) > 1 else name_no_ext
            else:
                mission_name = name_no_ext
        
        default_filename = f"WBMS-VS_params_{mission_name}.yaml"
        
        # Ask user for save location
        save_path = filedialog.asksaveasfilename(
            title="Save Mission Parameters",
            defaultextension=".yaml",
            initialfile=default_filename,
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")]
        )
        
        if save_path:
            try:
                # Create unified structure
                output_data = {
                    "WBMS_params": wbms_params,
                    "VS_params": vs_phases
                }
                
                with open(save_path, "w", encoding="utf-8") as f:
                    yaml.dump(output_data, f, allow_unicode=True, sort_keys=True, default_flow_style=False)
                
                # Prepare summary message
                summary_parts = []
                if wbms_params:
                    summary_parts.append(f"{len(wbms_params)} WBMS preset(s)")
                if vs_phases:
                    summary_parts.append(f"{len(vs_phases)} VS phase(s)")
                
                summary = " and ".join(summary_parts) if summary_parts else "Empty configuration"
                
                show_info_message("Success", f"Mission parameters saved to:\n{save_path}\n\n{summary}")
            except Exception as e:
                show_error_message("Error", f"Failed to save mission parameters:\n{str(e)}")
    
    def load_mission_params_from_yaml(self):
        """Load WBMS presets and VS settings from unified YAML file"""
        if not self.tree or not self.tree.get_children():
            show_error_message("No data", "Please load a mission folder first before loading parameters.")
            return
        
        # Ask user to select file
        load_path = filedialog.askopenfilename(
            title="Load Mission Parameters",
            defaultextension=".yaml",
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")]
        )
        
        if not load_path:
            return
        
        try:
            with open(load_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            
            if not data:
                show_error_message("Error", "Empty or invalid YAML file.")
                return
            
            # Extract sections
            wbms_params = data.get("WBMS_params", {})
            vs_phases = data.get("VS_params", {})
            
            # Apply WBMS presets and load VS configurations into memory
            wbms_loaded = 0
            for item in self.tree.get_children():
                values = list(self.tree.item(item)['values'])
                if len(values) >= 13:
                    phase_id = int(values[0])

                    # Load WBMS preset
                    if phase_id in wbms_params:
                        values[10] = wbms_params[phase_id]
                        wbms_loaded += 1

                    # Load VS settings into in-memory structure
                    if phase_id in vs_phases:
                        vs_data = vs_phases[phase_id]
                        # mark phase as having VS configured
                        if values[11] in ["☐", "☑"]:
                            values[11] = "☑"

                        # set configure text and store simplified VS data for VSConfigWindow
                        values[12] = VS_CONFIGURE_TEXT
                        try:
                            # Extract only relevant fields (DISTANCE, START_Z, END_Z) from subphases
                            simplified_data = {}
                            if isinstance(vs_data, dict):
                                for key, subphase in vs_data.items():
                                    if isinstance(key, str) and '-' in key and isinstance(subphase, dict):
                                        # Extract only the fields needed by VSConfigWindow
                                        simplified_subphase = {}
                                        
                                        # Calculate distance from coordinates
                                        start_lat = subphase.get('START_LAT')
                                        start_lon = subphase.get('START_LON') 
                                        end_lat = subphase.get('END_LAT')
                                        end_lon = subphase.get('END_LON')
                                        if all(coord is not None for coord in [start_lat, start_lon, end_lat, end_lon]):
                                            from src.data_processor import calculate_distance_meters
                                            distance = calculate_distance_meters(start_lat, start_lon, end_lat, end_lon)
                                            if distance is not None:
                                                simplified_subphase['DISTANCE'] = round(distance, 1)
                                        
                                        if 'START_Z' in subphase:
                                            simplified_subphase['START_Z'] = subphase['START_Z']
                                            simplified_subphase['START_Z'] = subphase['START_Z']
                                        if 'END_Z' in subphase:
                                            simplified_subphase['END_Z'] = subphase['END_Z']
                                        simplified_data[key] = simplified_subphase
                            self.vs_configurations[int(phase_id)] = simplified_data
                        except Exception:
                            pass

                    # Update tree item
                    self.tree.item(item, values=values)
            
            # Prepare summary
            summary_parts = []
            if wbms_loaded > 0:
                summary_parts.append(f"{wbms_loaded} WBMS preset(s)")
            if len(vs_phases) > 0:
                summary_parts.append(f"{len(vs_phases)} VS phase(s)")
            
            summary = " and ".join(summary_parts) if summary_parts else "No parameters"
            
            show_info_message("Success", f"Mission parameters loaded from:\n{load_path}\n\n{summary} restored.")
            
            # Auto-adjust columns
            auto_adjust_columns(self.tree)
            
        except Exception as e:
            show_error_message("Error", f"Failed to load mission parameters:\n{str(e)}")
    
    def on_tree_click_unified(self, event):
        """Handle single click on tree - VS checkbox toggle and general clicks"""
        if not self.tree:
            return
        
        item = self.tree.identify('item', event.x, event.y)
        column = self.tree.identify('column', event.x, event.y)
        
        # If clicked on empty space, clear selection
        if not item:
            self.tree.selection_remove(self.tree.selection())
            return
            
        # Get current values
        values = list(self.tree.item(item, 'values'))
        if len(values) < 13:  # Ensure we have the full table (13 columns)
            return

        # Column #12 is "Enable VS" (index 11 in values)
        if column == "#12":
            phase_type = values[1]
            z_col = values[4]  # Z column
            current_checkbox = values[11]

            # Only allow toggle for PathTrackingAuv phases with Depth mode that have a checkbox
            if (phase_type == "PathTrackingAuv" and ("Depth" in str(z_col)) and 
                current_checkbox in ["☐", "☑"]):  # Only if checkbox exists
                new_checkbox = "☑" if current_checkbox == "☐" else "☐"
                values[11] = new_checkbox
                # Update Configure VS cell text depending on checkbox (column index 12)
                if new_checkbox == "☑":
                    values[12] = VS_CONFIGURE_TEXT
                    # ensure a mapping exists in memory
                    try:
                        pid = int(values[0])
                        if pid not in self.vs_configurations:
                            self.vs_configurations[pid] = {}
                    except Exception:
                        pass
                else:
                    values[12] = ""
                    # optionally remove mapping
                if self.tree:
                    self.tree.item(item, values=values)
                # Prevent default selection behavior for checkbox column
                return "break"

        # Column #13 is "Configure VS" (index 12 in values) - open VS config window
        if column == "#13":
            # Only open if Configure VS text is present
            if len(values) >= 13 and values[12] == VS_CONFIGURE_TEXT:
                try:
                    phase_id = int(values[0])
                except Exception:
                    return
                    
                # Extract Z depth value from phase
                z_depth = None
                try:
                    z_col = str(values[4])  # Z column
                    if "Depth:" in z_col:
                        z_depth = float(z_col.replace("Depth:", "").strip())
                except (ValueError, TypeError):
                    z_depth = None
                    
                # Compute total distance if folder available
                total_distance = None
                if self.current_folder:
                    try:
                        from src.data_processor import calculate_vs_distance
                        total_distance = calculate_vs_distance(self.current_folder, phase_id)
                    except Exception:
                        total_distance = None

                # Open VS config window if available
                if VSConfigWindow:
                    VSConfigWindow(self.root, phase_id, self.vs_configurations, 
                                 total_distance=total_distance, phase_z_depth=z_depth)
            return "break"
    
    def on_tree_double_click(self, event):
        """Handle double click on tree (no inline editing for VS fields)"""
        if not self.tree:
            return
            
        item = self.tree.identify('item', event.x, event.y)
        column = self.tree.identify('column', event.x, event.y)
        
        if not item:
            return
            
        # No inline editing for VS fields - they are configured in separate modal
        return
    
    def edit_cell(self, item, col_index, current_value):
        """Create entry widget for cell editing"""
        if not self.tree:
            return
            
        # Get cell position
        bbox = self.tree.bbox(item, f"#{col_index + 1}")  # TreeView columns are 1-indexed
        if not bbox:
            return
            
        x, y, width, height = bbox
        
        # Create entry widget with better positioning
        entry = tk.Entry(self.tree, borderwidth=1, highlightthickness=0, relief='solid')
        entry.place(x=x + 1, y=y + 1, width=width - 2, height=height - 2)
        entry.insert(0, current_value if current_value not in ["None", ""] else "")
        entry.select_range(0, tk.END)
        
        # Force focus and grab
        entry.focus_force()
        entry.grab_set()
        
        def save_edit(event=None):
            try:
                new_value = entry.get().strip()
                
                # Validate numeric input
                if new_value and new_value.lower() != "none":
                    try:
                        float(new_value)  # Validate it's a number
                    except ValueError:
                        # Invalid number, restore original value
                        new_value = current_value
                elif not new_value:
                    new_value = "None"
                
                # Update tree item
                if self.tree:
                    values = list(self.tree.item(item, 'values'))
                    values[col_index] = new_value
                    
                    # No VS angle recalculation here (VS configured in separate window)
                    
                    self.tree.item(item, values=values)
            finally:
                cleanup()
        
        def cancel_edit(event=None):
            cleanup()
        
        def cleanup():
            try:
                entry.grab_release()
                entry.destroy()
            except:
                pass  # Widget may already be destroyed
        
        # Bind events
        entry.bind('<Return>', save_edit)
        entry.bind('<Escape>', cancel_edit)
        entry.bind('<FocusOut>', save_edit)
        
        # Also bind to parent to handle clicks outside
        def on_click_outside(event):
            if event.widget != entry:
                save_edit()
        
        self.root.bind('<Button-1>', on_click_outside, add=True)
        
        # Remove the binding after editing is done
        def remove_binding():
            try:
                self.root.unbind('<Button-1>')
            except:
                pass
        
        entry.bind('<Destroy>', lambda e: remove_binding())
    
    def export_to_csv(self):
        """Export all table data to CSV file"""
        if not self.tree or not self.tree.get_children():
            show_error_message("No data", "No data loaded to export.")
            return
        
        # Generate default filename
        mission_name = "mission_data"
        if self.selected_xml_path:
            base = os.path.basename(self.selected_xml_path)
            name_no_ext = os.path.splitext(base)[0]
            if 'mim.' in name_no_ext:
                parts = name_no_ext.split('mim.', 1)
                mission_name = parts[1] if len(parts) > 1 else name_no_ext
            else:
                mission_name = name_no_ext
        
        default_filename = f"{mission_name}_table_export.csv"
        
        # Ask user for save location
        save_path = filedialog.asksaveasfilename(
            title="Export Table to CSV",
            defaultextension=".csv",
            initialfile=default_filename,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if save_path:
            try:
                with open(save_path, "w", newline="", encoding="utf-8-sig") as csvfile:
                    writer = csv.writer(csvfile)
                    
                    # Write header (VS start/end/distance/angle removed)
                    columns = ["Phase ID", "Phase Type", "Path Model", "OAS", "Z", "Speed", 
                              "SBP", "SAS", "AcComInhibitor", "WBMS", "Preset", "Enable VS"]
                    writer.writerow(columns)
                    
                    # Write data rows (exclude Configure VS column)
                    for item in self.tree.get_children():
                        values = list(self.tree.item(item)['values'])
                        # Trim Configure VS column if present
                        if len(values) > 12:
                            values = values[:12]
                        # Convert special symbols to Excel-friendly text
                        converted_values = []
                        for value in values:
                            if value == "—":
                                converted_values.append("-")
                            elif value == "☐":
                                converted_values.append("NO")
                            elif value == "☑":
                                converted_values.append("YES")
                            elif value == "✓":
                                converted_values.append("YES")
                            elif value == "❌":
                                converted_values.append("NO")
                            else:
                                converted_values.append(str(value))
                        writer.writerow(converted_values)
                
                show_info_message("Success", f"Table data exported to:\n{save_path}")
            except Exception as e:
                show_error_message("Error", f"Failed to export CSV file:\n{str(e)}")
    
    def run(self):
        """Start the application"""
        # Show initial load dialog
        self.load_folder()
        
        # Start main loop
        self.root.mainloop()


def main():
    """Main entry point"""
    try:
        app = PresetManagerApp()
        app.run()
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()