import tkinter as tk
from tkinter import ttk
from gui.access_points_tab import AccessPointsTab
from gui.channel_graph_tab import ChannelGraphTab
from gui.sniffer_tab import SnifferTab

class App(tk.Tk):
    def __init__(self, queue, interface=None, hopper=None):
        super().__init__()
        self.title("Manual WiFi Analyzer & Sniffer")
        self.geometry("900x700")
        self.queue = queue
        self.interface = interface
        self.hopper = hopper
        
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create 3 top-level tabs
        self.access_points_tab = AccessPointsTab(self.notebook)
        self.channel_graph_tab = ChannelGraphTab(self.notebook)
        self.sniffer_tab = SnifferTab(self.notebook, interface=interface, hopper=hopper)  # Pass interface
        
        self.notebook.add(self.access_points_tab, text="Access Points")
        self.notebook.add(self.channel_graph_tab, text="Channel Graph")
        self.notebook.add(self.sniffer_tab, text="Packet Sniffer")
        
        self.process_queue()

    def process_queue(self):
        try:
            while not self.queue.empty():
                data = self.queue.get_nowait()
                type_ = data.get('type')
                
                if type_ == 'BEACON':
                    self.access_points_tab.update_network(data)
                    self.channel_graph_tab.update_network(data)
                elif type_ in ['TCP', 'IP', '802.11', 'ETH']:
                    self.sniffer_tab.add_packet(data)
        except Exception:
            pass
        finally:
            self.after(100, self.process_queue)
