import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional
import math

class VSConfigWindow:
    """Toplevel window to configure VS subphases for a phase.

    Parameters
    - parent: root window
    - phase_id: int
    - vs_configurations: dict mapping phase_id -> { subphase_id: data }
    - total_distance: optional total distance for the phase (meters)
    """

    def __init__(self, parent, phase_id: int, vs_configurations: Dict[int, Dict[str, Any]], 
                 total_distance: Optional[float] = None, phase_z_depth: Optional[float] = None):
        self.parent = parent
        self.phase_id = int(phase_id)
        self.vs_configurations = vs_configurations
        self.total_distance = total_distance
        self.phase_z_depth = phase_z_depth
        # Ensure entry exists
        if self.phase_id not in self.vs_configurations:
            self.vs_configurations[self.phase_id] = {}
            
        # Auto-create first subphase if none exist
        if not self.vs_configurations[self.phase_id]:
            first_subphase_id = f"{self.phase_id}-1"
            start_depth = self.phase_z_depth if self.phase_z_depth is not None else 0.0
            self.vs_configurations[self.phase_id][first_subphase_id] = {
                'DISTANCE': '', 
                'START_Z': start_depth, 
                'END_Z': ''
            }

        self.window = tk.Toplevel(self.parent)
        self.window.title(f"Configure VS - Phase {self.phase_id}")
        self.window.geometry("600x500")
        self.window.transient(self.parent)
        self.window.grab_set()

        # Show unallocated phase distance if provided
        if self.total_distance is not None:
            dist_frame = tk.Frame(self.window)
            dist_frame.pack(fill=tk.X, padx=10, pady=(8, 0))
            self.distance_label = tk.Label(dist_frame, text="", anchor='w', font=('Arial', 10, 'bold'))
            self.distance_label.pack(side=tk.LEFT)
            self.update_unallocated_distance()

        # Treeview for subphases with Distance, Start Depth, End Depth columns
        subphase_frame = tk.LabelFrame(self.window, text="Subphases Configuration", padx=5, pady=5)
        subphase_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))

        columns = ("Subphase ID", "Distance [m]", "Start Depth [m]", "End Depth [m]", "Angle [°]")
        self.tree = ttk.Treeview(subphase_frame, columns=columns, show='headings', height=10)
        
        # Configure headings and columns
        self.tree.heading("Subphase ID", text="Subphase ID")
        self.tree.heading("Distance [m]", text="Distance [m]")
        self.tree.heading("Start Depth [m]", text="Start Depth [m]")  
        self.tree.heading("End Depth [m]", text="End Depth [m]")
        self.tree.heading("Angle [°]", text="Angle [°]")
        
        self.tree.column("Subphase ID", width=100, minwidth=80)
        self.tree.column("Distance [m]", width=100, minwidth=80)
        self.tree.column("Start Depth [m]", width=120, minwidth=100)
        self.tree.column("End Depth [m]", width=120, minwidth=100)
        self.tree.column("Angle [°]", width=80, minwidth=60)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Bind double-click for editing
        self.tree.bind("<Double-Button-1>", self.on_double_click)

        # Buttons frame
        btn_frame = tk.Frame(self.window)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        add_btn = tk.Button(btn_frame, text="Add Subphase", command=self.add_subphase, width=15)
        add_btn.pack(side=tk.LEFT)

        delete_btn = tk.Button(btn_frame, text="Delete Subphase", command=self.delete_subphase, width=15)
        delete_btn.pack(side=tk.LEFT, padx=(10, 0))

        close_btn = tk.Button(btn_frame, text="Close", command=self.close, width=12)
        close_btn.pack(side=tk.RIGHT)

        # Populate existing subphases
        self.refresh()

    def calculate_angle(self, distance, start_depth, end_depth):
        """Calculate angle using trigonometry: angle = arctan(depth_diff / distance)"""
        try:
            distance_val = float(distance) if distance else 0
            start_val = float(start_depth) if start_depth else 0
            end_val = float(end_depth) if end_depth else 0
            
            if distance_val == 0:
                return ""
            
            depth_diff = end_val - start_val  # Positive when going deeper, negative when ascending
            angle_rad = math.atan(depth_diff / distance_val)
            angle_deg = math.degrees(angle_rad)
            return f"{angle_deg:.1f}"
        except (ValueError, TypeError, ZeroDivisionError):
            return ""

    def refresh(self):
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        # Insert existing subphases ordered with their data
        phase_data = self.vs_configurations.get(self.phase_id, {})
        subphases = [k for k in phase_data.keys() if isinstance(k, str) and '-' in k]
        subphases_sorted = sorted(subphases, key=lambda s: [int(x) if x.isdigit() else x for x in s.split('-')])
        
        for sp in subphases_sorted:
            sp_data = phase_data.get(sp, {})
            distance = sp_data.get('DISTANCE', '')
            start_depth = sp_data.get('START_Z', '')
            end_depth = sp_data.get('END_Z', '')
            angle = self.calculate_angle(distance, start_depth, end_depth)
            
            self.tree.insert('', 'end', values=(sp, distance, start_depth, end_depth, angle))
        
        # Update unallocated distance display
        if hasattr(self, 'distance_label'):
            self.update_unallocated_distance()

    def update_unallocated_distance(self):
        """Update the unallocated distance display"""
        if self.total_distance is None:
            return
            
        # Calculate sum of allocated distances
        allocated = 0.0
        phase_data = self.vs_configurations.get(self.phase_id, {})
        for key, subphase_data in phase_data.items():
            if isinstance(key, str) and '-' in key and isinstance(subphase_data, dict):
                distance_val = subphase_data.get('DISTANCE', '')
                if distance_val:
                    try:
                        allocated += float(distance_val)
                    except (ValueError, TypeError):
                        pass
        
        unallocated = self.total_distance - allocated
        self.distance_label.config(text=f"Unallocated Phase Distance: {unallocated:.2f} m")

    def add_subphase(self):
        mapping = self.vs_configurations.setdefault(self.phase_id, {})
        # Determine next suffix
        existing = [k for k in mapping.keys() if isinstance(k, str) and '-' in k]
        suffixes = []
        for k in existing:
            try:
                parts = k.split('-')
                if len(parts) == 2 and parts[0] == str(self.phase_id):
                    suffixes.append(int(parts[1]))
            except Exception:
                pass
        next_idx = 1
        if suffixes:
            next_idx = max(suffixes) + 1
        new_id = f"{self.phase_id}-{next_idx}"
        
        # Get start depth from previous subphase end depth
        start_depth = ''
        if suffixes:
            # Find the last (highest numbered) existing subphase
            last_suffix = max(suffixes)
            last_id = f"{self.phase_id}-{last_suffix}"
            last_data = mapping.get(last_id, {})
            end_z = last_data.get('END_Z', '')
            if end_z:
                start_depth = end_z
        
        # Initialize new subphase
        mapping[new_id] = {'DISTANCE': '', 'START_Z': start_depth, 'END_Z': ''}
        self.refresh()

    def delete_subphase(self):
        """Delete the last (highest numbered) subphase"""
        mapping = self.vs_configurations.get(self.phase_id, {})
        existing = [k for k in mapping.keys() if isinstance(k, str) and '-' in k]
        if not existing:
            return  # No subphases to delete
            
        # Find the last subphase (highest suffix)
        suffixes = []
        for k in existing:
            try:
                parts = k.split('-')
                if len(parts) == 2 and parts[0] == str(self.phase_id):
                    suffixes.append((int(parts[1]), k))
            except Exception:
                pass
        
        if suffixes:
            # Sort by suffix number and get the last one
            suffixes.sort(key=lambda x: x[0])
            last_subphase = suffixes[-1][1]
            del mapping[last_subphase]
            self.refresh()

    def on_double_click(self, event):
        """Handle double-click on treeview cells for editing"""
        item = self.tree.identify('item', event.x, event.y)
        column = self.tree.identify('column', event.x, event.y)
        
        if not item or column in ("#1", "#5"):  # Don't edit subphase ID or Angle
            return
            
        # Get current values
        values = list(self.tree.item(item)['values'])
        if len(values) < 5:
            return
            
        # Check if this is the first subphase and Start Depth column
        subphase_id = values[0]
        if column == "#3" and subphase_id == f"{self.phase_id}-1":  # Start Depth for first subphase
            return  # Don't allow editing
            
        col_index = int(column.replace('#', '')) - 1
        current_value = str(values[col_index])
        
        # Create edit entry
        self.edit_cell(item, column, current_value)
    
    def edit_cell(self, item, column, current_value):
        """Create entry widget for cell editing"""
        # Get cell position
        bbox = self.tree.bbox(item, column)
        if not bbox:
            return
            
        x, y, width, height = bbox
        
        # Create entry widget
        entry = tk.Entry(self.tree, borderwidth=1, highlightthickness=0)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, current_value if current_value not in ["None", ""] else "")
        entry.select_range(0, tk.END)
        entry.focus()
        
        def save_edit():
            new_value = entry.get().strip()
            
            # Update tree display
            values = list(self.tree.item(item)['values'])
            col_index = int(column.replace('#', '')) - 1
            values[col_index] = new_value  # Update values first
            
            # Update vs_configurations
            subphase_id = values[0]
            phase_data = self.vs_configurations.setdefault(self.phase_id, {})
            subphase_data = phase_data.setdefault(subphase_id, {})
            
            need_refresh = False
            
            if col_index == 1:  # Distance
                if new_value:
                    try:
                        subphase_data['DISTANCE'] = float(new_value)
                    except ValueError:
                        subphase_data['DISTANCE'] = new_value
                else:
                    subphase_data['DISTANCE'] = ''
                # Update unallocated distance when Distance column changes
                if hasattr(self, 'distance_label'):
                    self.update_unallocated_distance()
            elif col_index == 2:  # Start Depth
                # Don't allow editing first subphase start depth
                if subphase_id == f"{self.phase_id}-1":
                    entry.destroy()
                    return
                if new_value:
                    try:
                        start_depth_val = float(new_value)
                        subphase_data['START_Z'] = start_depth_val
                        
                        # Update end depth of previous subphase if it exists
                        parts = subphase_id.split('-')
                        if len(parts) == 2:
                            current_suffix = int(parts[1])
                            prev_id = f"{self.phase_id}-{current_suffix - 1}"
                            if prev_id in phase_data:
                                phase_data[prev_id]['END_Z'] = start_depth_val
                                need_refresh = True  # Refresh to update previous subphase
                                
                    except ValueError:
                        subphase_data['START_Z'] = new_value
                else:
                    subphase_data['START_Z'] = ''
            elif col_index == 3:  # End Depth
                if new_value:
                    try:
                        end_depth_val = float(new_value)
                        subphase_data['END_Z'] = end_depth_val
                        
                        # Update start depth of next subphase if it exists
                        parts = subphase_id.split('-')
                        if len(parts) == 2:
                            current_suffix = int(parts[1])
                            next_id = f"{self.phase_id}-{current_suffix + 1}"
                            if next_id in phase_data:
                                phase_data[next_id]['START_Z'] = end_depth_val
                                need_refresh = True  # Only refresh if next subphase exists
                                
                    except ValueError:
                        subphase_data['END_Z'] = new_value
                else:
                    subphase_data['END_Z'] = ''
            
            # Recalculate angle if Distance, Start Depth, or End Depth changed
            if col_index in [1, 2, 3]:
                distance = values[1]
                start_depth = values[2] 
                end_depth = values[3]
                angle = self.calculate_angle(distance, start_depth, end_depth)
                values[4] = angle  # Update angle in display
            
            self.tree.item(item, values=values)
            
            # Only refresh if we need to update next subphase
            if need_refresh:
                self.refresh()
            
            entry.destroy()
        
        def cancel_edit():
            entry.destroy()
        
        entry.bind('<Return>', lambda e: save_edit())
        entry.bind('<Escape>', lambda e: cancel_edit())
        entry.bind('<FocusOut>', lambda e: save_edit())

    def close(self):
        try:
            self.window.grab_release()
            self.window.destroy()
        except Exception:
            pass
