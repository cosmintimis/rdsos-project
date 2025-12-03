import tkinter as tk
from tkinter import ttk
from utils.oui import get_vendor
from utils.constants import get_frequency

class AccessPointsTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        
        # Scrollable container for the list
        self.canvas = tk.Canvas(self, bg="#222222", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#222222")
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=800)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Bind resize to update inner frame width
        self.canvas.bind('<Configure>', self._on_canvas_configure)

        # Data storage
        self.networks = {}
        self.network_widgets = {}

    def _on_canvas_configure(self, event):
        items = self.canvas.find_withtag("all")
        if items:
            self.canvas.itemconfig(items[0], width=event.width)

    def update_network(self, data):
        bssid = data.get('bssid')
        if bssid:
            self.networks[bssid] = data
            self.update_list()

    def get_signal_color(self, signal):
        if signal >= -50:
            return "#00ff00"  # Green
        elif signal >= -70:
            return "#ffff00"  # Yellow
        else:
            return "#ff0000"  # Red

    def draw_wifi_icon(self, canvas, x, y, size, color, signal):
        """Draw WiFi icon with bars based on signal strength"""
        # Calculate number of bars (1-4) based on signal
        if signal >= -50:
            bars = 4
        elif signal >= -60:
            bars = 3
        elif signal >= -70:
            bars = 2
        else:
            bars = 1
        
        # Draw WiFi arcs from center
        for i in range(4):
            if i < bars:
                bar_color = color
            else:
                bar_color = "#555555"  # Dim color for inactive bars
            
            radius = (i + 1) * (size / 8)
            arc_start = 225  # Start angle
            arc_extent = 90  # Arc span
            
            canvas.create_arc(
                x - radius, y - radius, x + radius, y + radius,
                start=arc_start, extent=arc_extent,
                outline=bar_color, width=2, style=tk.ARC
            )
        
        # Draw center dot
        dot_size = size / 10
        canvas.create_oval(
            x - dot_size, y - dot_size, x + dot_size, y + dot_size,
            fill=color, outline=color
        )

    def show_detail_dialog(self, bssid):
        """Show detailed information dialog for selected AP"""
        data = self.networks.get(bssid)
        if not data:
            return
        
        dialog = tk.Toplevel(self)
        dialog.title(f"Details: {data.get('ssid', '<Hidden>')}")
        dialog.geometry("500x400")
        dialog.configure(bg="#2b2b2b")
        
        # Make dialog modal - wait for visibility first
        dialog.transient(self)
        dialog.wait_visibility()  # Wait for window to be viewable
        dialog.grab_set()
        
        # Content frame with padding
        content = tk.Frame(dialog, bg="#2b2b2b", padx=20, pady=20)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(
            content,
            text=data.get('ssid', '<Hidden>'),
            font=("Arial", 18, "bold"),
            fg="white",
            bg="#2b2b2b"
        )
        title_label.pack(pady=(0, 20))
        
         
        # Calculate channel information
        channel = data.get('channel', 0)
        signal = data.get('signal', -100)
        center_freq = self._channel_to_frequency(channel)
        distance = self._estimate_distance(signal, center_freq)
        bandwidth = 20  # MHz (standard for 2.4 GHz)
        start_freq = center_freq - (bandwidth / 2)
        end_freq = center_freq + (bandwidth / 2)
        signal_quality = self._signal_quality(signal)
        
        details = [
            ("SSID:", data.get('ssid', 'Unknown')),
            ("BSSID (MAC):", data.get('bssid', 'Unknown')),
            ("Vendor:", get_vendor(data.get('bssid', ''))),
            ("", ""),  # Spacer
            ("Channel:", f"{channel} ({center_freq} MHz) | Est. Distance: ~{distance:.0f}m"),
            ("Bandwidth:", f"{bandwidth} MHz ({start_freq:.0f}-{end_freq:.0f} MHz)"),
            ("Band:", "2.4 GHz"),
            ("", ""),  # Spacer
            ("Signal Strength:", f"{signal} dBm"),
            ("Signal Quality:", signal_quality),
            ("", ""),  # Spacer
            ("Security:", data.get('security', 'Unknown')),
        ]
        
        # Add RSN security details if available
        if 'auth_methods' in data and data['auth_methods']:
            details.append(("Authentication:", ", ".join(data['auth_methods'][:2])))
        if 'group_cipher' in data:
            details.append(("Group Cipher:", data['group_cipher']))
        if 'pairwise_ciphers' in data and data['pairwise_ciphers']:
            details.append(("Pairwise Cipher:", ", ".join(data['pairwise_ciphers'][:2])))
        
        for label_text, value_text in details:
            row = tk.Frame(content, bg="#2b2b2b")
            row.pack(fill=tk.X, pady=5)
            
            label = tk.Label(
                row,
                text=label_text,
                font=("Arial", 11, "bold"),
                fg="#888888",
                bg="#2b2b2b",
                width=18,
                anchor="w"
            )
            label.pack(side=tk.LEFT)
            
            value = tk.Label(
                row,
                text=value_text,
                font=("Arial", 11),
                fg="white",
                bg="#2b2b2b",
                anchor="w"
            )
            value.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Signal strength bar
        signal = data.get('signal', -100)
        signal_percent = max(0, min(100, ((signal + 100) / 50) * 100))
        
        bar_frame = tk.Frame(content, bg="#2b2b2b")
        bar_frame.pack(fill=tk.X, pady=20)
        
        bar_label = tk.Label(
            bar_frame,
            text="Signal Quality:",
            font=("Arial", 11, "bold"),
            fg="#888888",
            bg="#2b2b2b"
        )
        bar_label.pack(anchor="w")
        
        bar_container = tk.Frame(bar_frame, bg="#444444", height=20)
        bar_container.pack(fill=tk.X, pady=5)
        bar_container.pack_propagate(False)
        
        bar_fill = tk.Frame(bar_container, bg=self.get_signal_color(signal))
        bar_fill.place(relwidth=signal_percent/100, relheight=1)
        
        # Close button
        close_btn = tk.Button(
            content,
            text="Close",
            command=dialog.destroy,
            bg="#444444",
            fg="white",
            font=("Arial", 11),
            relief=tk.FLAT,
            padx=20,
            pady=10,
            cursor="hand2"
        )
        close_btn.pack(pady=10)

    def update_list(self):
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
                
                # Make card clickable
                card.bind("<Button-1>", lambda e, b=bssid: self.show_detail_dialog(b))
                card.configure(cursor="hand2")
                
                # WiFi Icon
                icon_canvas = tk.Canvas(card, width=32, height=32, bg="#333333", highlightthickness=0)
                icon_canvas.grid(row=0, column=0, rowspan=2, padx=5)
                self.draw_wifi_icon(icon_canvas, 16, 16, 24, color, signal)
                icon_canvas.bind("<Button-1>", lambda e, b=bssid: self.show_detail_dialog(b))
                
                # SSID
                lbl_ssid = tk.Label(card, text=ssid, font=("Arial", 12, "bold"), fg="white", bg="#333333", anchor="w")
                lbl_ssid.grid(row=0, column=1, sticky="w")
                lbl_ssid.bind("<Button-1>", lambda e, b=bssid: self.show_detail_dialog(b))
                
                # BSSID (MAC)
                lbl_bssid = tk.Label(card, text=f"{bssid} ({vendor})", font=("Arial", 9), fg="#aaaaaa", bg="#333333", anchor="w")
                lbl_bssid.grid(row=1, column=1, sticky="w")
                lbl_bssid.bind("<Button-1>", lambda e, b=bssid: self.show_detail_dialog(b))
                
                # Details
                details_text = f"CH {channel}  {freq}MHz  {crypto}"
                lbl_details = tk.Label(card, text=details_text, font=("Arial", 10, "bold"), fg=color, bg="#333333", anchor="w")
                lbl_details.grid(row=2, column=1, sticky="w")
                lbl_details.bind("<Button-1>", lambda e, b=bssid: self.show_detail_dialog(b))
                
                # Signal Text
                lbl_signal = tk.Label(card, text=f"{signal} dBm", font=("Arial", 10), fg=color, bg="#333333")
                lbl_signal.grid(row=0, column=2, sticky="ne", padx=5)
                lbl_signal.bind("<Button-1>", lambda e, b=bssid: self.show_detail_dialog(b))

                # Store references
                self.network_widgets[bssid] = {
                    'frame': card,
                    'icon': icon_canvas,
                    'ssid': lbl_ssid,
                    'bssid': lbl_bssid,
                    'details': lbl_details,
                    'signal': lbl_signal
                }
                
                card.grid_columnconfigure(1, weight=1)
                
            else:
                # Update existing card
                widgets = self.network_widgets[bssid]
                widgets['icon'].delete("all")
                self.draw_wifi_icon(widgets['icon'], 16, 16, 24, color, signal)
                widgets['ssid'].config(text=ssid)
                widgets['bssid'].config(text=f"{bssid} ({vendor})")
                widgets['details'].config(text=f"CH {channel}  {freq}MHz  {crypto}", fg=color)
                widgets['signal'].config(text=f"{signal} dBm", fg=color)

    def _channel_to_frequency(self, channel):
        """Convert 2.4 GHz channel number to center frequency in MHz"""
        if 1 <= channel <= 13:
            return 2407 + (channel * 5)
        elif channel == 14:
            return 2484  # Special case for Japan
        return 0

    def _estimate_distance(self, signal_dbm, frequency_mhz):
        """
        Estimate distance from signal strength using a practical indoor model
        
        Uses a simplified log-distance path loss model adjusted for indoor environments:
          PL(d) = PL(d0) + 10*n*log10(d/d0)
        Where:
          n = path loss exponent (2.0 for free space, 3.0-4.0 for indoor)
        
        Assumptions:
          - TX power: ~15 dBm (realistic for most WiFi APs at antenna)
          - Path loss exponent: 2.5 (typical indoor environment)
          - Reference distance: 1 meter
        
        Note: This is an approximation. Actual distance varies with:
          - Walls, furniture, and obstacles
          - Interference and multipath
          - Antenna characteristics
        """
        import math
        
        # More realistic TX power for indoor WiFi APs
        # (accounts for actual antenna output, not regulatory max)
        TX_POWER = 15  # dBm
        
        # Path loss at reference distance (1 meter) for 2.4 GHz
        # Using FSPL: PL(1m) = 20*log10(frequency) + 20*log10(1) + 32.45 - 20*log10(c/f)
        freq_ghz = frequency_mhz / 1000.0
        if freq_ghz > 0:
            PL_1m = 20 * math.log10(freq_ghz) + 32.45
        else:
            return 0
        
        # Actual path loss from signal strength
        path_loss = TX_POWER - signal_dbm
        
        # Path loss exponent (2.0 = free space, 3.0-4.0 = indoor with obstacles)
        # Using 2.5 as a middle ground for typical indoor environment
        n = 2.5
        
        # Solve for distance: PL(d) = PL(1m) + 10*n*log10(d)
        # d = 10^((PL(d) - PL(1m)) / (10*n))
        if path_loss > PL_1m:
            distance = 10 ** ((path_loss - PL_1m) / (10 * n))
            return max(1, distance)  # Minimum 1 meter
        else:
            return 1  # Very close, minimum 1 meter

    def _signal_quality(self, signal_dbm):
        """Describe signal quality based on signal strength"""
        if signal_dbm >= -50:
            return "Excellent"
        elif signal_dbm >= -60:
            return "Good"
        elif signal_dbm >= -70:
            return "Fair"
        elif signal_dbm >= -80:
            return "Weak"
        else:
            return "Very Weak"
