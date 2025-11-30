import tkinter as tk
from tkinter import ttk
import datetime

class SnifferTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        
        # Controls
        controls_frame = tk.Frame(self)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(controls_frame, text="Lock Channel:").pack(side=tk.LEFT)
        self.channel_var = tk.StringVar()
        tk.Entry(controls_frame, textvariable=self.channel_var, width=5).pack(side=tk.LEFT, padx=5)
        tk.Button(controls_frame, text="Set", command=self.set_channel).pack(side=tk.LEFT)
        
        # Treeview
        columns = ('time', 'src', 'dst', 'proto', 'info')
        self.tree = ttk.Treeview(self, columns=columns, show='headings')
        self.tree.heading('time', text='Time')
        self.tree.heading('src', text='Source')
        self.tree.heading('dst', text='Destination')
        self.tree.heading('proto', text='Protocol')
        self.tree.heading('info', text='Info')
        
        self.tree.column('time', width=80)
        self.tree.column('src', width=120)
        self.tree.column('dst', width=120)
        self.tree.column('proto', width=60)
        self.tree.column('info', width=400)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind double-click to show details
        self.tree.bind("<Double-Button-1>", self.show_packet_details)
        
        # Store full packet data (for detail view)
        self.packet_data = {}

    def add_packet(self, packet_info):
        """
        packet_info: Enhanced with complete IP/TCP fields and HTTP data
        """
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        src = packet_info.get('src_ip', 'N/A')
        dst = packet_info.get('dst_ip', 'N/A')
        
        # Fallback to MAC if IP is N/A
        if src == 'N/A': src = packet_info.get('src_mac', 'N/A')
        if dst == 'N/A': dst = packet_info.get('dst_mac', 'N/A')
        
        proto = packet_info.get('type', 'Unknown')
        
        # Enhanced info display
        if 'http' in packet_info:
            # HTTP packet - show method/path or status code
            http = packet_info['http']
            if http['type'] == 'HTTP_REQUEST':
                info = f"HTTP {http['method']} {http['path']}"
            else:
                info = f"HTTP {http['status_code']} {http['status_text']}"
        elif 'tcp_flags_str' in packet_info:
            # TCP packet - show flags
            info = packet_info.get('info', '')
        else:
            info = packet_info.get('info', '')
        
        # Insert into tree
        item_id = self.tree.insert("", 0, values=(
            timestamp,
            src,
            dst,
            proto,
            info
        ))
        
        # Store full packet data for detail view
        self.packet_data[item_id] = packet_info
        
        # Limit to 1000 packets
        if len(self.tree.get_children()) > 1000:
            oldest = self.tree.get_children()[-1]
            self.packet_data.pop(oldest, None)
            self.tree.delete(oldest)

    def show_packet_details(self, event):
        """Show detailed packet information in a dialog"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        packet_info = self.packet_data.get(item_id)
        if not packet_info:
            return
        
        # Create detail dialog
        dialog = tk.Toplevel(self)
        dialog.title("Packet Details")
        dialog.geometry("700x600")
        dialog.configure(bg="#2b2b2b")
        
        # Create notebook for different sections
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Summary Tab
        summary_frame = tk.Frame(notebook, bg="#2b2b2b")
        notebook.add(summary_frame, text="Summary")
        self._add_summary_tab(summary_frame, packet_info)
        
        # IP Header Tab (if present)
        if 'ip_version' in packet_info:
            ip_frame = tk.Frame(notebook, bg="#2b2b2b")
            notebook.add(ip_frame, text="IP Header")
            self._add_ip_tab(ip_frame, packet_info)
        
        # TCP Header Tab (if present)
        if 'tcp_seq_num' in packet_info:
            tcp_frame = tk.Frame(notebook, bg="#2b2b2b")
            notebook.add(tcp_frame, text="TCP Header")
            self._add_tcp_tab(tcp_frame, packet_info)
        
        # HTTP Payload Tab (if present)
        if 'http' in packet_info:
            http_frame = tk.Frame(notebook, bg="#2b2b2b")
            notebook.add(http_frame, text="HTTP Payload")
            self._add_http_tab(http_frame, packet_info['http'])

    def _add_summary_tab(self, parent, packet_info):
        """Add summary information"""
        text = tk.Text(parent, bg="#1e1e1e", fg="white", font=("Courier", 10), wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        summary = f"""PACKET SUMMARY
================

Type: {packet_info.get('type', 'Unknown')}
Source: {packet_info.get('src_ip', packet_info.get('src_mac', 'N/A'))}
Destination: {packet_info.get('dst_ip', packet_info.get('dst_mac', 'N/A'))}
Protocol: {packet_info.get('ip_protocol_name', 'N/A')}
Info: {packet_info.get('info', '')}
"""
        text.insert(tk.END, summary)
        text.config(state=tk.DISABLED)

    def _add_ip_tab(self, parent, packet_info):
        """Add IP header details"""
        text = tk.Text(parent, bg="#1e1e1e", fg="white", font=("Courier", 9), wrap=tk.NONE)
        scrollbar = ttk.Scrollbar(parent, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        
        ip_details = f"""IPv4 HEADER
===========

Version: {packet_info.get('ip_version', 'N/A')}
Header Length (IHL): {packet_info.get('ip_ihl', 'N/A')} ({packet_info.get('ip_header_length', 'N/A')} bytes)
DSCP: {packet_info.get('ip_dscp', 'N/A')}
ECN: {packet_info.get('ip_ecn', 'N/A')}
Total Length: {packet_info.get('ip_total_length', 'N/A')} bytes
Identification: {packet_info.get('ip_identification', 'N/A')}
Flags:
  - Don't Fragment (DF): {packet_info.get('ip_flag_df', False)}
  - More Fragments (MF): {packet_info.get('ip_flag_mf', False)}
Fragment Offset: {packet_info.get('ip_fragment_offset', 'N/A')}
Time to Live (TTL): {packet_info.get('ip_ttl', 'N/A')}
Protocol: {packet_info.get('ip_protocol', 'N/A')} ({packet_info.get('ip_protocol_name', 'N/A')})
Header Checksum: {packet_info.get('ip_checksum', 'N/A')}
Source IP: {packet_info.get('src_ip', 'N/A')}
Destination IP: {packet_info.get('dst_ip', 'N/A')}
"""
        text.insert(tk.END, ip_details)
        text.config(state=tk.DISABLED)

    def _add_tcp_tab(self, parent, packet_info):
        """Add TCP header details"""
        text = tk.Text(parent, bg="#1e1e1e", fg="white", font=("Courier", 9), wrap=tk.NONE)
        scrollbar = ttk.Scrollbar(parent, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        
        tcp_flags = packet_info.get('tcp_flags', {})
        flags_detail = "\n".join([f"  - {flag}: {value}" for flag, value in tcp_flags.items()])
        
        tcp_details = f"""TCP HEADER
==========

Source Port: {packet_info.get('src_port', 'N/A')}
Destination Port: {packet_info.get('dst_port', 'N/A')}
Sequence Number: {packet_info.get('tcp_seq_num', 'N/A')}
Acknowledgment Number: {packet_info.get('tcp_ack_num', 'N/A')}
Data Offset: {packet_info.get('tcp_data_offset', 'N/A')} ({packet_info.get('tcp_header_length', 'N/A')} bytes)
Flags: [{packet_info.get('tcp_flags_str', 'N/A')}]
{flags_detail}
Window Size: {packet_info.get('tcp_window_size', 'N/A')} bytes
Checksum: {packet_info.get('tcp_checksum', 'N/A')}
Urgent Pointer: {packet_info.get('tcp_urgent_pointer', 'N/A')}
"""
        text.insert(tk.END, tcp_details)
        text.config(state=tk.DISABLED)

    def _add_http_tab(self, parent, http_info):
        """Add HTTP payload details"""
        text = tk.Text(parent, bg="#1e1e1e", fg="white", font=("Courier", 9), wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(parent, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        
        if http_info['type'] == 'HTTP_REQUEST':
            http_details = f"""HTTP REQUEST
============

Method: {http_info.get('method', 'N/A')}
Path: {http_info.get('path', 'N/A')}
Version: {http_info.get('version', 'N/A')}

Headers:
"""
            for header in http_info.get('headers', []):
                http_details += f"  {header}\n"
            
            if http_info.get('body'):
                http_details += f"\nBody (first 200 chars):\n{http_info['body']}\n"
        else:
            http_details = f"""HTTP RESPONSE
=============

Version: {http_info.get('version', 'N/A')}
Status Code: {http_info.get('status_code', 'N/A')}
Status Text: {http_info.get('status_text', 'N/A')}

Headers:
"""
            for header in http_info.get('headers', []):
                http_details += f"  {header}\n"
            
            if http_info.get('body'):
                http_details += f"\nBody (first 200 chars):\n{http_info['body']}\n"
        
        text.insert(tk.END, http_details)
        text.config(state=tk.DISABLED)

    def set_channel(self):
        ch = self.channel_var.get()
        if ch.isdigit():
            import subprocess
            print(f"[*] Locking to channel {ch}")
            subprocess.run(["iwconfig", "wlan0", "channel", ch])
