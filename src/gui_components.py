"""
GUI components module for the preset management application.
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os


class ToolTip:
    """Create a tooltip for a given widget"""
    
    def __init__(self, widget, text='widget info', enabled_var=None):
        self.widget = widget
        self.text = text
        self.enabled_var = enabled_var
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.tipwindow = None
        
    def enter(self, event=None):
        """Show tooltip on mouse enter"""
        self.show_tip()
        
    def leave(self, event=None):
        """Hide tooltip on mouse leave"""
        self.hide_tip()
        
    def show_tip(self):
        """Display tooltip"""
        if self.tipwindow or not self.text:
            return
        
        # Check if tips are enabled
        if self.enabled_var and not self.enabled_var.get():
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() + - 50
        
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(tw, text=self.text, justify='left',
                        background="#ffffe0", relief='solid', borderwidth=1,
                        font=("Arial", 8), padx=4, pady=2)
        label.pack(ipadx=1)
        
    def hide_tip(self):
        """Hide tooltip"""
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()


def create_main_window():
    """Create and configure the main application window"""
    root = tk.Tk()
    root.title("Mission Planning Tool")
    
    # Get screen dimensions and set window to full screen
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # Set window to 95% of screen size
    window_width = int(screen_width * 0.95)
    window_height = int(screen_height * 0.9)
    
    # Center the window
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    root.state('zoomed')  # Maximize on Windows
    
    return root


def create_menu_bar(root, callbacks, tips_enabled_var=None):
    """Create menu bar with File and Settings menus"""
    menubar = tk.Menu(root)
    
    # File menu
    file_menu = tk.Menu(menubar, tearoff=0)
    file_menu.add_command(label="Select folder", command=callbacks.get('select_folder'))
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=root.quit)
    menubar.add_cascade(label="File", menu=file_menu)
    
    # Settings menu
    settings_menu = tk.Menu(menubar, tearoff=0)
    settings_menu.add_command(label="Edit presets", command=callbacks.get('edit_presets'))
    settings_menu.add_separator()
    
    # Add tips toggle if variable provided
    if tips_enabled_var:
        settings_menu.add_checkbutton(label="Enable Tips", variable=tips_enabled_var, onvalue=True, offvalue=False)
    
    menubar.add_cascade(label="Settings", menu=settings_menu)
    
    root.config(menu=menubar)
    return menubar


def create_treeview(parent, map_callback=None, tips_enabled_var=None):
    """Create and configure the main TreeView widget with resizable map area below"""
    # Create main content frame
    main_content_frame = tk.Frame(parent)
    main_content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Create PanedWindow for resizable panes (table and map)
    paned_window = ttk.PanedWindow(main_content_frame, orient=tk.VERTICAL)
    paned_window.pack(fill=tk.BOTH, expand=True)
    
    # Create top frame for treeview
    top_frame = tk.Frame(paned_window)
    paned_window.add(top_frame, weight=3)  # Table gets more initial space
    
    # Define columns 
    columns = ("Phase ID", "Phase Type", "Path Model", "OAS", "Z", "Speed", "SBP", "SAS", "AcComInhibitor", "WBMS", "Preset", "Enable VS", "Configure VS")
    
    # Create TreeView in top frame
    tree = ttk.Treeview(top_frame, columns=columns, show="headings", height=15)
    
    # Configure column headings
    tree.heading("Phase ID", text="Phase ID")
    tree.heading("Phase Type", text="Phase Type") 
    tree.heading("Path Model", text="Path Model")
    tree.heading("OAS", text="OAS")
    tree.heading("Z", text="Z [m]")
    tree.heading("Speed", text="Speed (kt)")
    tree.heading("SBP", text="SBP Settings")
    tree.heading("SAS", text="SAS Settings")
    tree.heading("AcComInhibitor", text="AcComInhibitor")
    tree.heading("WBMS", text="WBMS Settings from CoMMI")
    tree.heading("Preset", text="WBMS Settings to Upload")
    tree.heading("Enable VS", text="Enable VS")
    tree.heading("Configure VS", text="Configure VS")
    
    # Set initial minimal widths for all columns
    for col in tree["columns"]:
        tree.column(col, width=80, minwidth=50)
    
    # Create scrollbars for TreeView
    v_scrollbar = ttk.Scrollbar(top_frame, orient=tk.VERTICAL, command=tree.yview)
    h_scrollbar = ttk.Scrollbar(top_frame, orient=tk.HORIZONTAL, command=tree.xview)
    
    tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
    
    # Grid layout for TreeView
    tree.grid(row=0, column=0, sticky="nsew")
    v_scrollbar.grid(row=0, column=1, sticky="ns")
    h_scrollbar.grid(row=1, column=0, sticky="ew")
    
    # Configure grid weights for TreeView
    top_frame.grid_rowconfigure(0, weight=1)
    top_frame.grid_columnconfigure(0, weight=1)
    
    # Create map container (second pane in PanedWindow)
    map_container = tk.Frame(paned_window)
    
    # Create map toggle button
    map_toggle_frame = tk.Frame(map_container)
    map_toggle_frame.pack(side=tk.TOP, fill=tk.X)
    
    # Map frame (initially visible by default)
    map_frame = tk.Frame(map_container, bg='lightgray')
    map_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)  # Show by default
    
    # Add map container to paned window
    paned_window.add(map_container, weight=2)  # Map gets less initial space
    
    # Toggle function
    def toggle_map():
        # Check if map_container is in the paned window
        if map_container in paned_window.panes():
            # Hide map by removing from paned window
            paned_window.remove(map_container)
            toggle_button.config(text="Show Map ▲")
        else:
            # Show map by adding back to paned window
            paned_window.add(map_container, weight=2)
            toggle_button.config(text="Hide Map ▼")
            # Call the map callback to initialize map if provided
            if map_callback:
                map_callback()
    
    # Create toggle button (initially shows "Hide Map" since map is visible)
    toggle_button = tk.Button(map_toggle_frame, text="Hide Map ▼", command=toggle_map)
    toggle_button.pack(side=tk.LEFT)
    
    # Add tooltip to map toggle button
    ToolTip(toggle_button, 
            "Show/hide the route map visualization.\n"
            "The map displays PTM route files from the loaded folder.\n"
            "Select phases in the table to highlight corresponding routes.", enabled_var=tips_enabled_var)
    
    # Add placeholder label to map frame
    map_label = tk.Label(map_frame, text="Map will appear after the mission folder selection", 
                        bg='lightgray', fg='gray', font=("Arial", 12))
    map_label.pack(expand=True)
    
    # Store references in tree object for later use
    tree.map_frame = map_frame  # type: ignore
    tree.map_toggle = toggle_map  # type: ignore
    tree.toggle_button = toggle_button  # type: ignore
    
    return tree


def create_control_panel(parent, presets, callbacks, tips_enabled_var=None):
    """Create control panel with preset dropdown and buttons"""
    control_frame = tk.Frame(parent)
    control_frame.pack(fill=tk.X, padx=10, pady=5)
    
    # Selected file label
    selected_file_var = tk.StringVar()
    selected_file_var.set("No file selected")
    file_label = tk.Label(control_frame, textvariable=selected_file_var, 
                         font=("Arial", 10), anchor="w")
    file_label.pack(fill=tk.X, pady=(0, 5))
    
    # Button frame
    button_frame = tk.Frame(control_frame)
    button_frame.pack(fill=tk.X)
    
    # Load folder button
    load_btn = tk.Button(button_frame, text="Load Mission Folder", 
                        command=callbacks.get('load_folder'),
                        font=("Arial", 10), width=20)
    load_btn.pack(side=tk.LEFT, padx=(0, 10))
    
    # Add tooltip to load button
    ToolTip(load_btn, 
            "Select a folder containing mission file (mim.*.xml),\n"
            "route files (ptm.*.xml), and payload configuration\n"
            "file (pl.*.json) to load mission data.", enabled_var=tips_enabled_var)
    
    # Preset dropdown
    preset_var = tk.StringVar()
    preset_combo = ttk.Combobox(button_frame, textvariable=preset_var, 
                               values=presets, state="readonly", width=40)
    preset_combo.pack(side=tk.LEFT, padx=(0, 10))
    if presets:
        preset_combo.current(0)
    
    # Add tooltip to preset dropdown
    ToolTip(preset_combo, 
            "Select a WBMS preset configuration to assign.\n"
            "Presets are loaded from presets.yaml file and can\n"
            "be edited using Settings > Edit presets menu.", enabled_var=tips_enabled_var)
    
    # Assign preset button
    assign_btn = tk.Button(button_frame, text="Assign WBMS Settings", 
                          command=lambda: callbacks.get('assign_preset')(preset_var.get()),
                          font=("Arial", 10), width=20)
    assign_btn.pack(side=tk.LEFT, padx=(0, 10))
    
    # Add tooltip to assign button
    ToolTip(assign_btn, 
            "Assign the selected WBMS preset from the dropdown\n"
            "to all currently selected phases in the table.", enabled_var=tips_enabled_var)
    
    # Auto-assign button
    auto_assign_btn = tk.Button(button_frame, text="Assign WBMS Settings from CoMMI", 
                               command=callbacks.get('auto_assign'),
                               bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), width=30)
    auto_assign_btn.pack(side=tk.LEFT, padx=(0, 10))
    
    # Add tooltip to auto-assign button
    ToolTip(auto_assign_btn, 
            "Automatically assign WBMS settings based on the WBMS payload\n"
            "settings selected in ECA CoMMI software. Settings will not be assigned\n"
            "if preset is not matching existing one from presets.yaml.", enabled_var=tips_enabled_var)
    
    # Clear preset button
    clear_btn = tk.Button(button_frame, text="Clear Settings", 
                         command=callbacks.get('clear_preset'),
                         font=("Arial", 10), width=15)
    clear_btn.pack(side=tk.LEFT, padx=(0, 10))
    
    # Add tooltip to clear button
    ToolTip(clear_btn, 
            "Remove WBMS preset assignments from all\n"
            "currently selected phases in the table.", enabled_var=tips_enabled_var)
    
    # Save Mission Params button (unified WBMS + VS)
    save_mission_btn = tk.Button(button_frame, text="Save Mission Params", 
                                 command=callbacks.get('save_mission_params'),
                                 bg="#FF9800", fg="white", font=("Arial", 10, "bold"), width=20)
    save_mission_btn.pack(side=tk.LEFT, padx=(0, 10))
    
    # Load Mission Params button
    load_mission_btn = tk.Button(button_frame, text="Load Mission Params", 
                                command=callbacks.get('load_mission_params'),
                                bg="#9C27B0", fg="white", font=("Arial", 10, "bold"), width=20)
    load_mission_btn.pack(side=tk.LEFT, padx=(0, 10))
    
    # Add tooltip to save button
    ToolTip(save_mission_btn, 
            "Save both WBMS presets and VS settings to a unified YAML file.\n"
            "File contains two sections: WBMS_params and VS_params.\n"
            "This file will be uploaded to the AUV for mission configuration.", enabled_var=tips_enabled_var)
    
    # Add tooltip to load button
    ToolTip(load_mission_btn, 
            "Load previously saved mission parameters from YAML file.\n"
            "Restores both WBMS preset assignments and VS settings\n"
            "for all phases from the selected file.", enabled_var=tips_enabled_var)
    
    # Export to CSV button
    export_csv_btn = tk.Button(button_frame, text="Export to CSV", 
                              command=callbacks.get('export_csv'),
                              bg="#2196F3", fg="white", font=("Arial", 10, "bold"), width=15)
    export_csv_btn.pack(side=tk.LEFT, padx=(0, 10))
    
    # Add tooltip to CSV export button
    ToolTip(export_csv_btn, 
            "Export all table data to CSV file for external analysis.\n"
            "Includes all columns: phase info, settings, VS data.", enabled_var=tips_enabled_var)
    
    return control_frame, selected_file_var, preset_combo


def auto_adjust_columns(tree):
    """Auto-adjust column widths to fit content"""
    column_widths = {}
    total_content_width = 0
    
    # Calculate optimal width for each column
    for col in tree["columns"]:
        header_text = tree.heading(col, "text")
        max_width = len(str(header_text)) * 8 + 20
        
        # Check width of all data in this column
        for item in tree.get_children():
            values = tree.item(item, "values")
            col_index = list(tree["columns"]).index(col)
            
            if col_index < len(values) and values[col_index]:
                content_text = str(values[col_index])
                content_width = len(content_text) * 8 + 20
                max_width = max(max_width, content_width)
        
        # Set minimum width and store
        column_widths[col] = max(80, max_width)
        total_content_width += column_widths[col]
    
    # Get available width (subtract padding and scrollbar space)
    available_width = tree.winfo_width() - 40
    if available_width < total_content_width:
        available_width = total_content_width
    
    # Distribute width proportionally
    for col in tree["columns"]:
        if total_content_width > 0:
            proportion = column_widths[col] / total_content_width
            final_width = int(available_width * proportion)
            final_width = max(80, final_width)  # Minimum width
        else:
            final_width = 120  # Default width
        
        tree.column(col, width=final_width, minwidth=80)


def setup_preset_dropdown_interaction(tree, presets, preset_combo, reload_callback):
    """Setup double-click interaction for preset assignment"""
    def on_double_click(event):
        """Handle double-click on TreeView cell"""
        item = tree.identify('item', event.x, event.y)
        column = tree.identify('column', event.x, event.y)
        
        if item and column == "#8":  # Preset column (8th column)
            show_preset_dropdown(item, event)
    
    def show_preset_dropdown(item, event):
        """Show dropdown for preset selection"""
        # Get current value
        current_values = tree.item(item, 'values')
        current_value = current_values[7] if len(current_values) > 7 else ""
        
        # Create popup window
        popup = tk.Toplevel(tree)
        popup.wm_overrideredirect(True)
        popup.configure(bg='white', bd=1, relief='solid')
        
        # Position popup at click location
        x = tree.winfo_rootx() + event.x
        y = tree.winfo_rooty() + event.y
        popup.geometry(f"+{x}+{y}")
        
        # Create listbox with presets
        listbox = tk.Listbox(popup, height=min(10, len(presets)))
        
        for preset in presets:
            listbox.insert(tk.END, preset)
            if preset == current_value:
                listbox.selection_set(tk.END)
        
        listbox.pack()
        
        def select_preset(event=None):
            selection = listbox.curselection()
            if selection:
                selected_preset = listbox.get(selection[0])
                tree.set(item, column="Preset", value=selected_preset)
                # Update preset combo to match
                preset_combo.set(selected_preset)
            popup.destroy()
        
        def close_popup(event=None):
            popup.destroy()
        
        listbox.bind("<Double-Button-1>", select_preset)
        listbox.bind("<Return>", select_preset)
        listbox.bind("<Escape>", close_popup)
        popup.bind("<FocusOut>", close_popup)
        
        listbox.focus_set()
    
    tree.bind("<Double-1>", on_double_click)


def show_info_message(title, message):
    """Show info message dialog"""
    messagebox.showinfo(title, message)


def show_error_message(title, message):
    """Show error message dialog"""
    messagebox.showerror(title, message)
