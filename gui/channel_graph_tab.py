import tkinter as tk
from tkinter import ttk

class ChannelGraphTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.graph_canvas = tk.Canvas(self, bg="#222222", highlightthickness=0)
        self.graph_canvas.pack(fill=tk.BOTH, expand=True)
        self.graph_canvas.bind("<Configure>", self.draw_graph)
        
        self.networks = {}

    def update_network(self, data):
        bssid = data.get('bssid')
        if bssid:
            self.networks[bssid] = data
            self.draw_graph()

    def get_signal_color(self, signal):
        if signal >= -50:
            return "#00ff00"
        elif signal >= -70:
            return "#ffff00"
        else:
            return "#ff0000"

    def draw_graph(self, event=None):
        self.graph_canvas.delete("all")
        w = self.graph_canvas.winfo_width()
        h = self.graph_canvas.winfo_height()
        
        if w < 10 or h < 10: return

        margin_left = 60
        margin_right = 20
        margin_top = 30
        margin_bottom = 50
        graph_w = w - margin_left - margin_right
        graph_h = h - margin_top - margin_bottom

        # Draw horizontal grid lines (-90 to -20 dBm)
        for db in range(-90, -10, 10):
            y = margin_top + graph_h - ((db - (-90)) / 70 * graph_h)
            self.graph_canvas.create_line(margin_left, y, w - margin_right, y, fill="#404040", width=1)
            self.graph_canvas.create_text(margin_left - 10, y, text=str(db), fill="#888888", anchor="e", font=("Arial", 9))

        # Draw vertical grid lines for each channel
        for ch in range(1, 15):
            x = margin_left + ((ch - 1) / 13 * graph_w)
            self.graph_canvas.create_line(x, margin_top, x, margin_top + graph_h, fill="#404040", width=1)

        # Y-axis label
        self.graph_canvas.create_text(
            15, h / 2,
            text="Signal Strength (dBm)",
            fill="#aaaaaa",
            font=("Arial", 10, "bold"),
            angle=90
        )

        # X-axis channel numbers
        for ch in range(1, 15):
            x = margin_left + ((ch - 1) / 13 * graph_w)
            self.graph_canvas.create_text(x, h - margin_bottom + 15, text=str(ch), fill="#888888", font=("Arial", 9))

        # X-axis label
        self.graph_canvas.create_text(
            w / 2, h - 10,
            text="Wi-Fi Channels",
            fill="#aaaaaa",
            font=("Arial", 10, "bold")
        )

        # Draw Networks as filled rectangles
        for bssid, data in self.networks.items():
            channel = data.get('channel')
            signal = data.get('signal', -100)
            ssid = data.get('ssid', '')
            
            if not channel or signal < -90 or channel > 14: continue
            
            # Channel width for 2.4GHz is ~22MHz, spanning about 4-5 channels visually
            # We'll make each AP span about 2.5 channels on each side at the bottom
            # and narrower at the top for a trapezoidal shape
            channel_span_bottom = 2.5
            channel_span_top = 1.5  # Narrower at the peak
            
            # X positions
            center_x = margin_left + ((channel - 1) / 13 * graph_w)
            
            # Bottom corners (wider)
            half_width_bottom = (graph_w / 13) * channel_span_bottom
            left_x_bottom = max(margin_left, center_x - half_width_bottom)
            right_x_bottom = min(w - margin_right, center_x + half_width_bottom)
            
            # Top corners (narrower)
            half_width_top = (graph_w / 13) * channel_span_top
            left_x_top = max(margin_left, center_x - half_width_top)
            right_x_top = min(w - margin_right, center_x + half_width_top)
            
            # Y positions
            signal_normalized = max(-90, min(-20, signal))
            signal_ratio = (signal_normalized - (-90)) / 70
            peak_y = margin_top + graph_h - (signal_ratio * graph_h)
            base_y = margin_top + graph_h
            
            color = self.get_signal_color(signal)
            
            # Create trapezoidal polygon
            # Points: bottom-left, top-left, top-right, bottom-right
            points = [
                left_x_bottom, base_y,    # Bottom left (wider)
                left_x_top, peak_y,       # Top left (narrower)
                right_x_top, peak_y,      # Top right (narrower)
                right_x_bottom, base_y    # Bottom right (wider)
            ]
            
            # Draw filled trapezoid with transparency effect
            self.graph_canvas.create_polygon(
                points,
                fill=color,
                outline=color,
                width=2,
                stipple="gray50"  # Creates semi-transparency effect
            )
            
            # Draw top line (signal level)
            self.graph_canvas.create_line(
                left_x_top, peak_y,
                right_x_top, peak_y,
                fill=color,
                width=2
            )
            
            # Draw label with SSID and channel
            label_text = f"{ssid} ({channel})" if ssid else f"({channel})"
            
            # Draw text background for better readability
            self.graph_canvas.create_text(
                center_x, peak_y - 10,
                text=label_text,
                fill=color,
                font=("Arial", 9, "bold")
            )
