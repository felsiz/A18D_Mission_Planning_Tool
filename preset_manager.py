"""
Preset management module for loading, saving and auto-assignment functionality.
"""
import os
import yaml
import tkinter as tk
from tkinter import ttk, messagebox

PRESETS_FILE = "presets.yaml"


def load_presets():
    """Load presets from YAML file"""
    if os.path.exists(PRESETS_FILE):
        with open(PRESETS_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or []
    
    # Create default presets if file doesn't exist
    default_presets = [
        "3-50_400_140_ED_512_2048",
        "3-50_400_140_ED_256_1024", 
        "3-40_400_140_ED_512_2048",
        "60ALT 3-75_400_120_ED_512_2048",
        "80ALT 3-110_400_90_ED_256_2048",
        "3-190_300_90_ED_256_2048",
        "3-190_400_90_ED_256_2048"
    ]
    
    save_presets(default_presets)
    return default_presets


def save_presets(presets):
    """Save presets to YAML file"""
    with open(PRESETS_FILE, "w", encoding="utf-8") as f:
        yaml.dump(presets, f, allow_unicode=True)


def auto_assign_from_wbms(tree, presets):
    """Automatically assign presets from WBMS payload column"""
    preset_names = [preset.strip() for preset in presets]
    
    assigned_count = 0
    highlighted_count = 0
    
    # Clear any existing highlighting first
    for item in tree.get_children():
        tree.item(item, tags=())
    
    for item in tree.get_children():
        values = tree.item(item, 'values')
        if len(values) >= 10:  # Now we have 10 columns with Path Model and OAS
            wbms_payload = values[8]  # WBMS column is now index 8 (after SBP and SAS swap)
            current_preset = values[9]  # Preset column is still index 9
            
            # Only process if WBMS payload has a real value (not empty and not "—")
            if wbms_payload and wbms_payload != "—" and wbms_payload.strip():
                # Check if WBMS payload matches any preset
                if wbms_payload in preset_names:
                    # Direct match found, assign preset
                    tree.set(item, column="Preset", value=wbms_payload)
                    assigned_count += 1
                else:
                    # WBMS payload has value but no match found in YAML
                    # Leave preset empty and highlight in yellow
                    tree.set(item, column="Preset", value="")
                    tree.item(item, tags=('highlight',))
                    highlighted_count += 1
            # If WBMS payload is empty or "—", do nothing (no highlighting, no assignment)
    
    # Configure tag for highlighting
    tree.tag_configure('highlight', background='yellow')
    
    # Show result message
    message = f"Auto-assignment complete:\n"
    message += f"• {assigned_count} presets assigned automatically\n"
    message += f"• {highlighted_count} cells highlighted (no matching preset found in YAML)"
    
    messagebox.showinfo("Auto-Assignment Results", message)
    
    return assigned_count, highlighted_count


class PresetEditorWindow:
    """Preset editor window class"""
    
    def __init__(self, parent, reload_callback=None):
        self.parent = parent
        self.reload_callback = reload_callback
        self.presets = load_presets()
        
        self.window = tk.Toplevel(parent)
        self.window.title("Edit Presets")
        self.window.geometry("500x400")
        self.window.transient(parent)
        self.window.grab_set()
        
        self._create_widgets()
        self._populate_listbox()
    
    def _create_widgets(self):
        """Create UI widgets"""
        # Main frame
        frame = tk.Frame(self.window)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Label(frame, text="Current Presets:", font=("Arial", 12, "bold")).pack(anchor="w")
        
        # Listbox with scrollbar
        listbox_frame = tk.Frame(frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
        
        scrollbar = tk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.presets_listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set)
        self.presets_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.presets_listbox.yview)
        
        # Entry for new preset
        entry_frame = tk.Frame(frame)
        entry_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(entry_frame, text="Add new preset:").pack(anchor="w")
        self.new_preset_entry = tk.Entry(entry_frame)
        self.new_preset_entry.pack(fill=tk.X, pady=(2, 5))
        
        # Buttons frame
        buttons_frame = tk.Frame(frame)
        buttons_frame.pack(fill=tk.X)
        
        tk.Button(buttons_frame, text="Add", command=self._add_preset).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(buttons_frame, text="Remove", command=self._remove_preset).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(buttons_frame, text="Close", command=self._close_editor).pack(side=tk.RIGHT)
        
        # Bind events
        self.new_preset_entry.bind('<Return>', lambda e: self._add_preset())
        self.presets_listbox.bind('<Delete>', lambda e: self._remove_preset())
    
    def _populate_listbox(self):
        """Fill listbox with current presets"""
        for preset in self.presets:
            self.presets_listbox.insert(tk.END, preset)
    
    def _add_preset(self):
        """Add new preset"""
        new_preset = self.new_preset_entry.get().strip()
        if new_preset and new_preset not in self.presets:
            self.presets.append(new_preset)
            self.presets_listbox.insert(tk.END, new_preset)
            self.new_preset_entry.delete(0, tk.END)
            save_presets(self.presets)
        else:
            messagebox.showwarning("Error", "Empty or duplicate preset name")
    
    def _remove_preset(self):
        """Remove selected preset"""
        selection = self.presets_listbox.curselection()
        if selection:
            index = selection[0]
            preset_name = self.presets_listbox.get(index)
            self.presets.remove(preset_name)
            self.presets_listbox.delete(index)
            save_presets(self.presets)
        else:
            messagebox.showwarning("No selection", "Please select a preset to remove")
    
    def _close_editor(self):
        """Close editor and refresh main window"""
        if self.reload_callback:
            self.reload_callback()
        self.window.destroy()