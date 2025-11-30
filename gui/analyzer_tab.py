import tkinter as tk
from tkinter import ttk
import math
from utils.oui import get_vendor
from utils.constants import get_frequency

class AnalyzerTab:
    def __init__(self, notebook):
        self.frame = ttk.Frame(notebook)
        notebook.add(self.frame, text="WiFi Analyzer")
        
        # Sub-tabs for "Access Points" and "Channel Graph"
        self.sub_notebook = ttk.Notebook(self.frame)
        self.sub_notebook.pack(fill=tk.BOTH, expand=True)
        
        # --- Tab 1: Access Points (List) ---
        self.list_frame = ttk.Frame(self.sub_notebook)
        self.sub_notebook.add(self.list_frame, text="Access Points")
        
        # Scrollable container for the list
        self.canvas = tk.Canvas(self.list_frame, bg="#222222", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.list_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#222222")
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=800) # Initial width
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Bind resize to update inner frame width
        self.canvas.bind('<Configure>', self._on_canvas_configure)

        # --- Tab 2: Channel Graph ---
        self.graph_frame = ttk.Frame(self.sub_notebook)
        self.sub_notebook.add(self.graph_frame, text="Channel Graph")
        
        self.graph_canvas = tk.Canvas(self.graph_frame, bg="#222222", highlightthickness=0)
        self.graph_canvas.pack(fill=tk.BOTH, expand=True)
        self.graph_canvas.bind("<Configure>", self.draw_graph)

        # Data storage
        self.networks = {} # BSSID -> Data
        self.network_widgets = {} # BSSID -> Widget Frame

    def _on_canvas_configure(self, event):
        # Update the width of the window to match the canvas
        items = self.canvas.find_withtag("all")
        if items:
            self.canvas.itemconfig(items[0], width=event.width)

    def update_data(self, networks):
        self.networks = networks
        self.update_list()
        self.draw_graph()

    def update_network(self, data):
        """Updates a single network from a beacon packet."""
        bssid = data.get('bssid')
        if bssid:
            # Merge with existing data if needed, or just overwrite
            # We might want to preserve some stats if we had them, but for now overwrite is fine
            # except maybe signal history?
            self.networks[bssid] = data
            self.update_list()
            self.draw_graph()

    def get_signal_color(self, signal):
        if signal >= -50:
            return "#00ff00" # Green
        elif signal >= -70:
            return "#ffff00" # Yellow
        else:
            return "#ff0000" # Red

    def update_list(self):
        # Remove widgets for networks that disappeared (optional, maybe keep them for a bit?)
        # For now, we just update or create.
        
        for bssid, data in self.networks.items():
            ssid = data.get('ssid', '<Hidden>')
            signal = data.get('signal', -100)
            channel = data.get('channel', 0)
            crypto = data.get('crypto', 'Open')
            vendor = get_vendor(bssid)
            freq = get_frequency(channel)
            
            color = self.get_signal_color(signal)
            
            if bssid not in self.network_widgets:
                # Create new card
                card = tk.Frame(self.scrollable_frame, bg="#333333", pady=5, padx=5, bd=1, relief="flat")
                card.pack(fill="x", pady=2, padx=5)
                
                # Layout
                # Row 1: Icon + SSID (Left), Signal (Right)
                # Row 2: BSSID + Vendor (Left)
                # Row 3: Channel + Freq + Security (Left)
                
                # Signal Icon (Simple Circle)
                icon_canvas = tk.Canvas(card, width=24, height=24, bg="#333333", highlightthickness=0)
                icon_canvas.grid(row=0, column=0, rowspan=2, padx=5)
                icon_canvas.create_oval(2, 2, 22, 22, fill=color, outline=color, tags="icon")
                
                # SSID
                lbl_ssid = tk.Label(card, text=ssid, font=("Arial", 12, "bold"), fg="white", bg="#333333", anchor="w")
                lbl_ssid.grid(row=0, column=1, sticky="w")
                
                # BSSID (MAC)
                lbl_bssid = tk.Label(card, text=f"{bssid} ({vendor})", font=("Arial", 9), fg="#aaaaaa", bg="#333333", anchor="w")
                lbl_bssid.grid(row=1, column=1, sticky="w")
                
                # Details
                details_text = f"CH {channel}  {freq}MHz  {crypto}"
                lbl_details = tk.Label(card, text=details_text, font=("Arial", 10, "bold"), fg=color, bg="#333333", anchor="w")
                lbl_details.grid(row=2, column=1, sticky="w")
                
                # Signal Text
                lbl_signal = tk.Label(card, text=f"{signal} dBm", font=("Arial", 10), fg=color, bg="#333333")
                lbl_signal.grid(row=0, column=2, sticky="ne", padx=5)

                # Store references to update later
                self.network_widgets[bssid] = {
                    'frame': card,
                    'icon': icon_canvas,
                    'ssid': lbl_ssid,
                    'bssid': lbl_bssid,
                    'details': lbl_details,
                    'signal': lbl_signal
                }
                
                # Configure grid weights
                card.grid_columnconfigure(1, weight=1)
                
            else:
                # Update existing card
                widgets = self.network_widgets[bssid]
                widgets['icon'].itemconfig("icon", fill=color, outline=color)
                widgets['ssid'].config(text=ssid)
                widgets['bssid'].config(text=f"{bssid} ({vendor})")
                widgets['details'].config(text=f"CH {channel}  {freq}MHz  {crypto}", fg=color)
                widgets['signal'].config(text=f"{signal} dBm", fg=color)

    def draw_graph(self, event=None):
        self.graph_canvas.delete("all")
        w = self.graph_canvas.winfo_width()
        h = self.graph_canvas.winfo_height()
        
        if w < 10 or h < 10: return

        # Margins
        margin_left = 40
        margin_bottom = 30
        graph_w = w - margin_left - 20
        graph_h = h - margin_bottom - 20

        # Axes
        # X: Channels 1-14
        # Y: -90 to -20 dBm
        
        # Draw Y Axis Grid
        for db in range(-90, -10, 10):
            y = graph_h - ((db - (-90)) / 70 * graph_h) + 20 # 70 is range (-20 - -90)
            self.graph_canvas.create_line(margin_left, y, w, y, fill="#444444", dash=(2, 4))
            self.graph_canvas.create_text(margin_left - 5, y, text=str(db), fill="#aaaaaa", anchor="e")

        # Draw X Axis Labels
        for ch in range(1, 15):
            x = margin_left + ((ch - 1) / 13 * graph_w)
            self.graph_canvas.create_text(x, h - 10, text=str(ch), fill="#aaaaaa")

        # Draw Networks
        for bssid, data in self.networks.items():
            channel = data.get('channel')
            signal = data.get('signal', -100)
            ssid = data.get('ssid', '')
            
            if not channel or signal < -90: continue
            
            # X position (center of channel)
            center_x = margin_left + ((channel - 1) / 13 * graph_w)
            
            # Width of curve (approx 2 channels wide for 2.4GHz)
            width_x = (graph_w / 13) * 2
            
            # Y position (peak)
            peak_y = graph_h - ((signal - (-90)) / 70 * graph_h) + 20
            base_y = graph_h + 20 # -90 dBm level
            
            # Color
            color = self.get_signal_color(signal)
            
            # Draw Parabola (Quadratic Bezier)
            # Start: (center - width/2, base)
            # Control: (center, peak - height_factor) ? No, simple arc
            # Using create_line with smoothed points is easier for parabola
            
            points = []
            steps = 20
            for i in range(steps + 1):
                t = i / steps # 0 to 1
                # x goes from -1 to 1 (relative to center)
                rel_x = (t * 2) - 1 
                
                # Parabola equation: y = 1 - x^2
                rel_y = 1 - (rel_x * rel_x)
                
                px = center_x + (rel_x * (width_x / 2))
                # Map rel_y (0 to 1) to screen Y (base_y to peak_y)
                py = base_y - (rel_y * (base_y - peak_y))
                points.extend([px, py])
                
            self.graph_canvas.create_line(points, fill=color, width=2, smooth=True)
            self.graph_canvas.create_text(center_x, peak_y - 10, text=ssid, fill=color, font=("Arial", 8))
