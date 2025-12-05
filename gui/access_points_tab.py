import tkinter as tk
from tkinter import ttk
from utils.oui import get_vendor
from utils.constants import get_frequency, get_signal_color

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

    def draw_wifi_icon(self, canvas, x, y, size, color, signal):
        """Draw polished WiFi icon with wide arcs and small dot"""
        # Calculate number of arcs (1-3) based on signal strength
        if signal >= -50:
            num_arcs = 3  # Full signal
        elif signal >= -70:
            num_arcs = 2  # Medium signal
        else:
            num_arcs = 1  # Low signal
        
        # Smaller base dot for cleaner look
        dot_radius = size * 0.12
        dot_y = y
        
        # Draw 3 wide curved arcs stacked vertically ABOVE the dot
        for i in range(3):
            # Determine if this arc should be active or dim
            if i < num_arcs:
                arc_color = color
                arc_width = 2.5
            else:
                arc_color = "#555555"  # Dim inactive arcs
                arc_width = 2
            
            # Make arcs progressively wider and more spaced
            # Larger multiplier = wider, more prominent arcs
            arc_radius = size * (0.3 + i * 0.3)
            arc_center_y = dot_y - dot_radius - (i + 1) * size * 0.18
            
            # Draw arc with 100-degree span for wider curves
            canvas.create_arc(
                x - arc_radius, arc_center_y - arc_radius,
                x + arc_radius, arc_center_y + arc_radius,
                start=40,       # Start angle
                extent=100,     # Wider arc span for more curve
                outline=arc_color,
                width=arc_width,
                style=tk.ARC
            )
        
        # Draw small solid base dot
        canvas.create_oval(
            x - dot_radius, dot_y - dot_radius,
            x + dot_radius, dot_y + dot_radius,
            fill=color,
            outline=color
        )

    def show_detail_dialog(self, bssid):
        """Show detailed information dialog for selected AP"""
        data = self.networks.get(bssid)
        if not data:
            return
        
        # Use BSSID as fallback for empty/hidden SSID
        ssid = data.get('ssid', '')
        if not ssid or ssid == '':
            ssid = f"Unknown ({bssid[:8]}...)"
        
        dialog = tk.Toplevel(self)
        dialog.title(f"Details: {ssid}")
        dialog.geometry("550x550")
        dialog.configure(bg="#2b2b2b")
        
        # Make dialog modal - wait for visibility first
        dialog.transient(self)
        dialog.wait_visibility()
        dialog.grab_set()
        
        # Scrollable content frame with padding
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
        channel_freq = data.get('channel_freq', 0)
        signal = data.get('signal', -100)
        noise = data.get('noise', -100)
        snr = data.get('snr', 0)
        rate = data.get('rate', 0.0)
        tx_power = data.get('tx_power')
        vendor_oui = data.get('vendor_oui')
        
        center_freq = channel_freq if channel_freq > 0 else self._channel_to_frequency(channel)
        
        # Use actual TX power if available, otherwise default
        distance = self._estimate_distance(signal, center_freq, tx_power)
        
        bandwidth = 20  # MHz (standard for 2.4 GHz)
        start_freq = center_freq - (bandwidth / 2)
        end_freq = center_freq + (bandwidth / 2)
        signal_quality = self._signal_quality(signal)
        snr_quality = self._snr_quality(snr) if snr > 0 else "N/A"
        
        # Get vendors
        ap_vendor = get_vendor(data.get('bssid', ''))
        chipset_vendor = get_vendor(vendor_oui) if vendor_oui else None
        
        details = [
            ("SSID:", ssid),
            ("BSSID (MAC):", data.get('bssid', 'Unknown')),
            ("AP Vendor:", ap_vendor),
        ]
        
        # Add chipset vendor if available from Radiotap
        if chipset_vendor and chipset_vendor != ap_vendor:
            details.append(("Chipset:", f"{chipset_vendor} ({vendor_oui})"))
        
        details.extend([
            ("", ""),  # Spacer
            ("Channel:", f"{channel} ({center_freq} MHz)"),
            ("Bandwidth:", f"{bandwidth} MHz ({start_freq:.0f}-{end_freq:.0f} MHz)"),
            ("Band:", "2.4 GHz"),
            ("", ""),  # Spacer
        ])
        
        # Radio metrics section - TX Power only (Rate is misleading - shows beacon tx rate, not AP capability)
        if tx_power is not None:
            details.append(("TX Power:", f"{tx_power} dBm"))
            details.append(("", ""))  # Spacer
        
        details.extend([
            ("Signal Strength:", f"{signal} dBm"),
            ("Signal Quality:", signal_quality),
        ])
        
        if noise > -100:
            details.append(("Noise Floor:", f"{noise} dBm"))
        if snr > 0:
            details.append(("SNR:", f"{snr} dB ({snr_quality})"))
        
        details.extend([
            ("Est. Distance:", f"~{distance:.0f}m"),
            ("", ""),  # Spacer
            ("Security:", data.get('security', 'Unknown')),
        ])
        
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
        
        bar_fill = tk.Frame(bar_container, bg=get_signal_color(signal))
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
            # Use BSSID as fallback for empty SSID
            ssid = data.get('ssid', '')
            if not ssid or ssid == '':
                ssid = f"Unknown ({bssid[:8]}...)"
            
            signal = data.get('signal', -100)
            channel = data.get('channel', 0)
            crypto = data.get('crypto', 'Open')
            vendor = get_vendor(bssid)
            freq = get_frequency(channel)
            
            color = get_signal_color(signal)
            
            if bssid not in self.network_widgets:
                # Create new card
                card = tk.Frame(self.scrollable_frame, bg="#333333", pady=5, padx=5, bd=1, relief="flat")
                card.pack(fill="x", pady=2, padx=5)
                
                # Make card clickable
                card.bind("<Button-1>", lambda e, b=bssid: self.show_detail_dialog(b))
                card.configure(cursor="hand2")
                
                # WiFi icon on the left
                icon_canvas = tk.Canvas(card, width=32, height=60, bg="#333333", highlightthickness=0)
                icon_canvas.grid(row=0, column=0, rowspan=4, padx=(5, 10), pady=5, sticky="s")
                
                # Draw icon with base dot at bottom of canvas (y=55, near bottom of 60px canvas)
                self.draw_wifi_icon(icon_canvas, 16, 55, 24, color, signal)
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
                self.draw_wifi_icon(widgets['icon'], 16, 55, 24, color, signal)
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

    def _estimate_distance(self, signal_dbm, frequency_mhz, tx_power_dbm=None):
        """
        Estimate distance from signal strength using a practical indoor model
        
        Uses a simplified log-distance path loss model adjusted for indoor environments:
          PL(d) = PL(d0) + 10*n*log10(d/d0)
        Where:
          n = path loss exponent (2.0 for free space, 3.0-4.0 for indoor)
        
        Assumptions:
          - TX power: from Radiotap if available, otherwise ~15 dBm
          - Path loss exponent: 2.5 (typical indoor environment)
          - Reference distance: 1 meter
        
        Note: This is an approximation. Actual distance varies with:
          - Walls, furniture, and obstacles
          - Interference and multipath
          - Antenna characteristics
        """
        import math
        
        # Use Radiotap TX power if available, otherwise fallback
        if tx_power_dbm is not None:
            TX_POWER = tx_power_dbm
        else:
            TX_POWER = 15  # dBm fallback assumption
        
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
        if signal_dbm >= -30:
            return "Perfect"
        elif signal_dbm >= -50:
            return "Excellent"
        elif signal_dbm >= -60:
            return "Good"
        elif signal_dbm >= -67:
            return "Fair"
        elif signal_dbm >= -70:
            return "Light"
        elif signal_dbm >= -80:
            return "Weak"
        else:
            return "Poor"
    
    def _snr_quality(self, snr_db):
        """Evaluate SNR (Signal-to-Noise Ratio) quality"""
        if snr_db >= 40:
            return "Excellent"
        elif snr_db >= 25:
            return "Good"
        elif snr_db >= 15:
            return "Fair"
        elif snr_db >= 10:
            return "Poor"
        else:
            return "Very Poor"
