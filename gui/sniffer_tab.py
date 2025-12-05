import tkinter as tk
from tkinter import ttk
import datetime
import time

class SnifferTab(ttk.Frame):
    def __init__(self, parent, interface=None, hopper=None):
        super().__init__(parent)
        
        # Store references
        self.interface = interface
        self.hopper = hopper
        
        # Pause state
        self.paused = False
        
        # Filter state
        self.filter_var = tk.StringVar(value="All Packets")
        
        # Controls
        controls_frame = tk.Frame(self)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Pause/Resume button
        self.pause_btn = tk.Button(
            controls_frame, 
            text="⏸ Pause Capture", 
            command=self.toggle_pause,
            bg="#FF9800",  # Orange initially (Active/Pauseable)
            fg="white",
            font=("Arial", 10, "bold"),
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor="hand2"
        )
        self.pause_btn.pack(side=tk.LEFT, padx=5)
        
        # Filter dropdown
        tk.Label(controls_frame, text="Filter:", font=("Arial", 10)).pack(side=tk.LEFT, padx=(20, 5))
        filter_options = [
            "All Packets",
            "HTTP Only",
            "TCP Only",
            "UDP Only",
            "ICMP Only",
            "IP Only (TCP/UDP/ICMP)"
        ]
        self.filter_dropdown = ttk.Combobox(
            controls_frame,
            textvariable=self.filter_var,
            values=filter_options,
            state="readonly",
            width=20
        )
        self.filter_dropdown.pack(side=tk.LEFT, padx=5)
        
        # Channel controls frame
        channel_frame = tk.Frame(controls_frame)
        channel_frame.pack(side=tk.LEFT, padx=(20, 0))
        
        tk.Label(channel_frame, text="Channel:", font=("Arial", 10)).pack(side=tk.LEFT, padx=(0, 5))
        self.channel_var = tk.StringVar()
        self.channel_entry = tk.Entry(channel_frame, textvariable=self.channel_var, width=5)
        self.channel_entry.pack(side=tk.LEFT, padx=2)
        
        self.lock_btn = tk.Button(
            channel_frame, 
            text="Lock", 
            command=self.set_channel,
            bg="#FF9800",
            fg="white",
            font=("Arial", 9, "bold"),
            relief=tk.FLAT,
            padx=8,
            pady=3,
            cursor="hand2"
        )
        self.lock_btn.pack(side=tk.LEFT, padx=2)
        
        self.resume_hop_btn = tk.Button(
            channel_frame, 
            text="Resume Hopping", 
            command=self.resume_hopping,
            bg="#2196F3",
            fg="white",
            font=("Arial", 9, "bold"),
            relief=tk.FLAT,
            padx=8,
            pady=3,
            cursor="hand2",
            state=tk.DISABLED  # Initially disabled (hopping by default)
        )
        self.resume_hop_btn.pack(side=tk.LEFT, padx=2)
        
        # Hopper status label
        self.hopper_status = tk.Label(
            controls_frame, 
            text="● Hopping" if hopper else "● Managed Mode",
            fg="#4CAF50" if hopper else "#888888",
            font=("Arial", 9)
        )
        self.hopper_status.pack(side=tk.LEFT, padx=10)
        
        # Treeview with enhanced columns
        columns = ('time', 'src_mac', 'src_ip', 'dst_mac', 'dst_ip', 'proto', 'info')
        self.tree = ttk.Treeview(self, columns=columns, show='headings')
        self.tree.heading('time', text='Time')
        self.tree.heading('src_mac', text='Src MAC')
        self.tree.heading('src_ip', text='Src IP')
        self.tree.heading('dst_mac', text='Dst MAC')
        self.tree.heading('dst_ip', text='Dst IP')
        self.tree.heading('proto', text='Protocol')
        self.tree.heading('info', text='Info')
        
        self.tree.column('time', width=70)
        self.tree.column('src_mac', width=130)
        self.tree.column('src_ip', width=100)
        self.tree.column('dst_mac', width=130)
        self.tree.column('dst_ip', width=100)
        self.tree.column('proto', width=60)
        self.tree.column('info', width=300)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind double-click to show details
        self.tree.bind("<Double-Button-1>", self.show_packet_details)
        
        # Store full packet data (for detail view)
        self.packet_data = {}

    def toggle_pause(self):
        """Toggle packet capture pause state"""
        self.paused = not self.paused
        if self.paused:
            self.pause_btn.config(
                text="▶ Resume Capture",
                bg="#4CAF50"  # Green for Resume (Go)
            )
        else:
            self.pause_btn.config(
                text="⏸ Pause Capture",
                bg="#FF9800"  # Orange for Pause (Stop/Wait)
            )

    def add_packet(self, packet_info):
        """
        packet_info: Enhanced with complete IP/TCP fields and HTTP data
        """
        # Skip if paused
        if self.paused:
            return
        
        # Apply filter
        current_filter = self.filter_var.get()
        packet_type = packet_info.get('type', '')
        
        if current_filter == "HTTP Only":
            # Only show packets with HTTP data
            if 'http' not in packet_info:
                return
        elif current_filter == "TCP Only":
            if packet_type != 'TCP':
                return
        elif current_filter == "UDP Only":
            if packet_type != 'UDP':
                return
        elif current_filter == "ICMP Only":
            if packet_type != 'ICMP':
                return
        elif current_filter == "IP Only (TCP/UDP/ICMP)":
            if packet_type not in ['TCP', 'UDP', 'ICMP']:
                return
        # "All Packets" - no filtering
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        # Extract MAC and IP addresses separately
        src_mac = packet_info.get('src_mac', 'N/A')
        src_ip = packet_info.get('src_ip', 'N/A')
        dst_mac = packet_info.get('dst_mac', 'N/A')
        dst_ip = packet_info.get('dst_ip', 'N/A')
        
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
            src_mac,
            src_ip,
            dst_mac,
            dst_ip,
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

    def set_channel(self):
        """Lock to specific channel and stop hopper"""
        ch = self.channel_var.get()
        if ch.isdigit():
            import subprocess
            
            # Stop the hopper if it's running
            if self.hopper and self.hopper.running:
                print(f"[*] Stopping channel hopper...")
                self.hopper.stop()
            
            # Always enable resume button if we have an interface (we are now in locked mode)
            if self.interface:
                self.hopper_status.config(text="● Locked", fg="#FF9800")
                self.resume_hop_btn.config(state=tk.NORMAL)
            
            # Lock to channel
            print(f"[*] Locking to channel {ch}")
            if_name = self.interface if self.interface else "wlan0"
            subprocess.run(["iwconfig", if_name, "channel", ch])

    def resume_hopping(self):
        """Resume channel hopping"""
        if self.interface:
            try:
                # Stop old hopper if running
                if self.hopper and self.hopper.running:
                    self.hopper.stop()
                    time.sleep(0.1)
                
                # Create NEW hopper thread
                from core.hopper import ChannelHopper
                print(f"[*] Resuming channel hopping on {self.interface}...")
                
                self.hopper = ChannelHopper(self.interface)
                self.hopper.start()
                
                # Update parent app's hopper reference
                if hasattr(self.master.master, 'hopper'):
                    self.master.master.hopper = self.hopper
                
                # Update UI
                self.hopper_status.config(text="● Hopping", fg="#4CAF50")
                self.resume_hop_btn.config(state=tk.DISABLED)
                self.channel_var.set("")
            except Exception as e:
                print(f"[!] Error resuming hopper: {e}")
        else:
            print("[!] Cannot resume hopping: Interface unknown")

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
        
        # Statistics Tab (first)
        stats_frame = tk.Frame(notebook, bg="#2b2b2b")
        notebook.add(stats_frame, text="📊 Statistics")
        self._add_statistics_tab(stats_frame, packet_info)
        
        # Ethernet/MAC Tab (always present)
        eth_frame = tk.Frame(notebook, bg="#2b2b2b")
        notebook.add(eth_frame, text="Ethernet/MAC")
        self._add_ethernet_tab(eth_frame, packet_info)
        
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
        
        # UDP Header Tab (if present)
        if packet_info.get('type') == 'UDP':
            udp_frame = tk.Frame(notebook, bg="#2b2b2b")
            notebook.add(udp_frame, text="UDP Header")
            self._add_udp_tab(udp_frame, packet_info)
        
        # ICMP Header Tab (if present)
        if packet_info.get('type') == 'ICMP':
            icmp_frame = tk.Frame(notebook, bg="#2b2b2b")
            notebook.add(icmp_frame, text="ICMP Header")
            self._add_icmp_tab(icmp_frame, packet_info)
        
        # WiFi Metadata Tab (if available - monitor mode)
        if packet_info.get('radiotap_signal') or packet_info.get('bssid'):
            wifi_frame = tk.Frame(notebook, bg="#2b2b2b")
            notebook.add(wifi_frame, text="WiFi Metadata")
            self._add_wifi_metadata_tab(wifi_frame, packet_info)
        
        # HTTP Payload Tab (if present)
        if 'http' in packet_info:
            http_frame = tk.Frame(notebook, bg="#2b2b2b")
            notebook.add(http_frame, text="HTTP Payload")
            self._add_http_tab(http_frame, packet_info['http'])

    def _add_summary_tab(self, parent, packet_info):
        """Add summary of packet"""
        text = tk.Text(parent, bg="#1e1e1e", fg="white", font=("Courier", 10), wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(parent, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        
        summary = f"""PACKET SUMMARY
==============

Type: {packet_info.get('type', 'Unknown')}
Time: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Source: {packet_info.get('src_ip', packet_info.get('src_mac', 'N/A'))}
Destination: {packet_info.get('dst_ip', packet_info.get('dst_mac', 'N/A'))}

Info: {packet_info.get('info', 'No additional info')}
"""
        
        text.insert(tk.END, summary)
        text.config(state=tk.DISABLED)

    def _add_ip_tab(self, parent, packet_info):
        """Add IP header details"""
        text = tk.Text(parent, bg="#1e1e1e", fg="white", font=("Courier", 9), wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(parent, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        
        ip_details = f"""IP HEADER
=========

Version: {packet_info.get('ip_version', 'N/A')}
Header Length: {packet_info.get('ip_header_length', 'N/A')} bytes
Type of Service (ToS): {packet_info.get('ip_tos', 'N/A')}
  - DSCP: {packet_info.get('ip_dscp', 'N/A')}
  - ECN: {packet_info.get('ip_ecn', 'N/A')}
Total Length: {packet_info.get('ip_total_length', 'N/A')} bytes
Identification: {packet_info.get('ip_identification', 'N/A')}
Flags: {packet_info.get('ip_flags', 'N/A')}
Fragment Offset: {packet_info.get('ip_fragment_offset', 'N/A')}
Time to Live (TTL): {packet_info.get('ip_ttl', 'N/A')}
Protocol: {packet_info.get('ip_protocol', 'N/A')} ({packet_info.get('ip_protocol_name', 'Unknown')})
Header Checksum: {packet_info.get('ip_checksum', 'N/A')}
Source IP: {packet_info.get('src_ip', 'N/A')}
Destination IP: {packet_info.get('dst_ip', 'N/A')}

Purpose: The IP header routes packets across networks using logical addressing.
It provides best-effort delivery without guarantees of reliability or ordering.
"""
        
        text.insert(tk.END, ip_details)
        text.config(state=tk.DISABLED)

    def _add_tcp_tab(self, parent, packet_info):
        """Add TCP header details"""
        text = tk.Text(parent, bg="#1e1e1e", fg="white", font=("Courier", 9), wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(parent, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        
        
        # Safely extract tcp_flags as an integer
        tcp_flags_raw = packet_info.get("tcp_flags", 0)
        if isinstance(tcp_flags_raw, int):
            tcp_flags = tcp_flags_raw
        elif isinstance(tcp_flags_raw, dict):
            tcp_flags = 0
        else:
            try:
                tcp_flags = int(tcp_flags_raw)
            except:
                tcp_flags = 0
        
        tcp_details = f"""TCP HEADER
==========

Connection:
  Source Port: {packet_info.get('src_port', 'N/A')}
  Destination Port: {packet_info.get('dst_port', 'N/A')}
  Service: {self._get_service_name(packet_info.get('dst_port'))}

Sequence Control:
  Sequence Number: {packet_info.get('tcp_seq_num', 'N/A')}
  Acknowledgment Number: {packet_info.get('tcp_ack_num', 'N/A')}

Header Information:
  Data Offset: {packet_info.get('tcp_data_offset', 'N/A')}
  Header Length: {packet_info.get('tcp_header_length', 'N/A')} bytes
  Payload Length: {len(packet_info.get('payload', b''))} bytes

Flags: {packet_info.get('tcp_flags_str', 'N/A')} (0x{tcp_flags:02x})
  ├─ FIN: {"✓" if tcp_flags & 0x01 else "✗"} (Close connection)
  ├─ SYN: {"✓" if tcp_flags & 0x02 else "✗"} (Start connection)
  ├─ RST: {"✓" if tcp_flags & 0x04 else "✗"} (Reset connection)
  ├─ PSH: {"✓" if tcp_flags & 0x08 else "✗"} (Push data immediately)
  ├─ ACK: {"✓" if tcp_flags & 0x10 else "✗"} (Acknowledge receipt)
  ├─ URG: {"✓" if tcp_flags & 0x20 else "✗"} (Urgent data)
  ├─ ECE: {"✓" if tcp_flags & 0x40 else "✗"} (ECN Echo)
  └─ CWR: {"✓" if tcp_flags & 0x80 else "✗"} (Congestion Window Reduced)

Flow Control:
  Window Size: {packet_info.get('tcp_window_size', 'N/A')} bytes
  Urgent Pointer: {packet_info.get('tcp_urgent_pointer', 'N/A')}

Integrity:
  Checksum: {packet_info.get('tcp_checksum', 'N/A')}

Connection State (based on flags):
  {self._analyze_tcp_state(packet_info)}

Purpose: TCP provides reliable, ordered, error-checked delivery of data between applications.
It uses sequence numbers to ensure all data arrives and in correct order.
"""
        
        text.insert(tk.END, tcp_details)
        text.config(state=tk.DISABLED)

    def _add_udp_tab(self, parent, packet_info):
        """Add UDP header details"""
        text = tk.Text(parent, bg="#1e1e1e", fg="white", font=("Courier", 9), wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(parent, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        
        udp_details = f"""UDP HEADER
==========

Source Port: {packet_info.get('src_port', 'N/A')}
Destination Port: {packet_info.get('dst_port', 'N/A')}
Length: {packet_info.get('udp_length', 'N/A')} bytes
Checksum: {packet_info.get('udp_checksum', 'N/A')}

Service: {packet_info.get('udp_service', 'Unknown')}

Purpose: UDP is a connectionless protocol for low-latency, loss-tolerating applications.
Common uses: DNS, DHCP, streaming media, online gaming, VoIP.
"""
        
        text.insert(tk.END, udp_details)
        text.config(state=tk.DISABLED)

    def _add_icmp_tab(self, parent, packet_info):
        """Add ICMP header details"""
        text = tk.Text(parent, bg="#1e1e1e", fg="white", font=("Courier", 9), wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(parent, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        
        icmp_details = f"""ICMP HEADER
===========

Type: {packet_info.get('icmp_type', 'N/A')} ({packet_info.get('icmp_type_name', 'Unknown')})
Code: {packet_info.get('icmp_code', 'N/A')}
Checksum: {packet_info.get('icmp_checksum', 'N/A')}
"""
        
        # Add ping-specific info if present
        if 'icmp_identifier' in packet_info:
            icmp_details += f"""
Identifier: {packet_info.get('icmp_identifier', 'N/A')}
Sequence Number: {packet_info.get('icmp_sequence', 'N/A')}
"""
        
        icmp_details += """
Purpose: ICMP is used for network diagnostics and error reporting.
Common uses: ping, traceroute, network unreachable messages.
"""
        
        text.insert(tk.END, icmp_details)
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
                http_details += f"\nBody (first 500 chars):\n{http_info['body']}\n"
        
        text.insert(tk.END, http_details)
        text.config(state=tk.DISABLED)

    def _add_statistics_tab(self, parent, packet_info):
        """Show packet statistics"""
        text = tk.Text(parent, bg="#1e1e1e", fg="white", font=("Courier", 10), wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(parent, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        
        stats = f"""PACKET STATISTICS
=================

Capture Information:
  Timestamp: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]}
  Packet Number: #{len(self.packet_data)}
  
Layer Breakdown:
  ├─ Link Layer (Ethernet/802.11): {"✓" if packet_info.get('src_mac') else "✗"}
  ├─ Network Layer (IP): {"✓" if packet_info.get('src_ip') else "✗"}
  ├─ Transport Layer (TCP/UDP/ICMP): {"✓" if packet_info.get('type') in ['TCP','UDP','ICMP'] else "✗"}
  └─ Application Layer (HTTP/etc): {"✓" if packet_info.get('http') else "✗"}

Packet Size:
  Total Length: {packet_info.get('ip_total_length', 'N/A')} bytes
  Header Overhead: {self._calculate_header_overhead(packet_info)} bytes
  Payload: {len(packet_info.get('payload', b''))} bytes

Protocol Stack:
{self._build_protocol_stack(packet_info)}
"""
        text.insert(tk.END, stats)
        text.config(state=tk.DISABLED)

    def _add_ethernet_tab(self, parent, packet_info):
        """Add Ethernet/MAC layer details"""
        text = tk.Text(parent, bg="#1e1e1e", fg="white", font=("Courier", 9), wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(parent, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        
        eth_details = f"""ETHERNET / MAC LAYER
====================

Source MAC Address: {packet_info.get('src_mac', 'N/A')}
  Vendor (OUI): {self._get_mac_vendor(packet_info.get('src_mac', ''))}
  
Destination MAC Address: {packet_info.get('dst_mac', 'N/A')}
  Vendor (OUI): {self._get_mac_vendor(packet_info.get('dst_mac', ''))}
  Type: {self._get_mac_type(packet_info.get('dst_mac', ''))}

EtherType: {packet_info.get('ethertype', 'N/A')} 
  Name: {packet_info.get('ethertype_name', 'Unknown')}
"""
        # Add VLAN details if present
        vlan_id = packet_info.get('vlan_id')
        if vlan_id is not None:
            vlan_priority = packet_info.get('vlan_priority', 0)
            priority_names = ['Best Effort', 'Background', 'Excellent Effort', 'Critical Apps',
                            'Video (<100ms)', 'Video (<10ms)', 'Internetwork Control', 'Network Control']
            priority_name = priority_names[vlan_priority] if vlan_priority < 8 else 'Unknown'
            eth_details += f"""
VLAN Information (802.1Q):
  VLAN ID: {vlan_id}
  VLAN Priority: {vlan_priority} ({priority_name})
"""
        eth_details += """
Common EtherTypes:
  0x0800 - IPv4 (Internet Protocol)
  0x0806 - ARP (Address Resolution Protocol)
  0x86DD - IPv6
  0x8100 - VLAN (802.1Q)

MAC Address Types:
  - Unicast: Sent to specific device
  - Broadcast: FF:FF:FF:FF:FF:FF (all devices on network)
  - Multicast: First byte odd (e.g., 01:00:5E:xx:xx:xx)

Purpose: The Ethernet layer provides local network delivery using hardware
addresses (MAC addresses). It operates at Layer 2 of the OSI model.
"""
        text.insert(tk.END, eth_details)
        text.config(state=tk.DISABLED)

    def _add_wifi_metadata_tab(self, parent, packet_info):
        """Add WiFi-specific metadata"""
        text = tk.Text(parent, bg="#1e1e1e", fg="white", font=("Courier", 9), wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(parent, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        
        wifi_details = f"""WIFI METADATA
=============

Capture Mode: {"Monitor Mode" if packet_info.get('radiotap_signal') else "Managed Mode"}

"""
        
        # Radiotap info (if available)
        if packet_info.get('radiotap_signal'):
            wifi_details += f"""Radiotap Information:
  Signal Strength: {packet_info.get('radiotap_signal', 'N/A')} dBm
  Channel Frequency: {packet_info.get('channel_freq', 'N/A')} MHz
  Channel Number: {packet_info.get('channel', 'N/A')}
  Data Rate: {packet_info.get('data_rate', 'N/A')} Mbps

Signal Quality:
  {self._analyze_signal_strength(packet_info.get('radiotap_signal', -100))}

"""
        
        # 802.11 info (if available)
        if packet_info.get('bssid'):
            wifi_details += f"""802.11 Frame Information:
  Access Point (BSSID): {packet_info.get('bssid', 'N/A')}
  Network Name (SSID): {packet_info.get('ssid', 'N/A')}
  Frame Type: {packet_info.get('frame_type', 'N/A')}
  To DS: {packet_info.get('to_ds', 'N/A')}
  From DS: {packet_info.get('from_ds', 'N/A')}
"""
        
        wifi_details += """
Purpose: WiFi metadata provides information about the wireless transmission,
including signal quality and Access Point details.
"""
        
        text.insert(tk.END, wifi_details)
        text.config(state=tk.DISABLED)

    # Helper methods
    def _get_service_name(self, port):
        """Map port to service name"""
        if not port:
            return "N/A"
        services = {
            20: "FTP Data", 21: "FTP Control",
            22: "SSH", 23: "Telnet",
            25: "SMTP", 53: "DNS",
            80: "HTTP", 443: "HTTPS",
            110: "POP3", 143: "IMAP",
            3306: "MySQL", 5432: "PostgreSQL",
            3389: "RDP", 5900: "VNC",
            8080: "HTTP Proxy", 8443: "HTTPS Alt"
        }
        service = services.get(port, f"Port {port}")
        return f"{service} ({port})"

    def _get_mac_vendor(self, mac):
        """Get vendor from MAC OUI"""
        if mac and len(mac) >= 8 and mac != "N/A":
            try:
                from utils.oui import get_vendor
                vendor = get_vendor(mac)
                return vendor if vendor else "Unknown Vendor"
            except:
                return "Unknown"
        return "N/A"

    def _get_mac_type(self, mac):
        """Determine MAC address type"""
        if not mac or mac == "N/A":
            return "Unknown"
        if mac == "FF:FF:FF:FF:FF:FF":
            return "Broadcast"
        try:
            first_byte = int(mac.split(':')[0], 16)
            if first_byte & 1:
                return "Multicast"
            return "Unicast"
        except:
            return "Unknown"

    def _analyze_tcp_state(self, packet_info):
        """Analyze TCP connection state"""
        try:
            flags = packet_info.get('tcp_flags', 0)
            
            # Handle case where tcp_flags might be a dict or other non-integer type
            if not isinstance(flags, int):
                # Try to extract from dict if it's a dict, otherwise default to 0
                if isinstance(flags, dict):
                    flags = 0  # Can't analyze dict flags
                else:
                    try:
                        flags = int(flags)
                    except (ValueError, TypeError):
                        flags = 0
            
            if flags & 0x02 and not flags & 0x10:  # SYN only
                return "→ Connection Request (SYN)"
            elif flags & 0x02 and flags & 0x10:     # SYN+ACK
                return "← Connection Accepted (SYN-ACK)"
            elif flags & 0x10 and not any([flags & 0x01, flags & 0x04]):  # ACK only
                return "↔ Established (ACK)"
            elif flags & 0x01:                       # FIN
                return "→ Closing Connection (FIN)"
            elif flags & 0x04:                       # RST
                return "✗ Connection Reset (RST)"
            elif flags & 0x08:                       # PSH
                return "⚡ Data Push (PSH+ACK)"
            return "Active"
        except Exception as e:
            return f"Error analyzing state: {str(e)}"


    def _calculate_header_overhead(self, packet_info):
        """Calculate total header bytes"""
        overhead = 0
        if packet_info.get('src_mac'):
            overhead += 14  # Ethernet
        if packet_info.get('ip_header_length'):
            overhead += packet_info.get('ip_header_length', 20)
        if packet_info.get('tcp_header_length'):
            overhead += packet_info.get('tcp_header_length', 0)
        elif packet_info.get('type') == 'UDP':
            overhead += 8  # UDP header
        elif packet_info.get('type') == 'ICMP':
            overhead += 8  # ICMP header
        return overhead if overhead > 0 else "N/A"

    def _build_protocol_stack(self, packet_info):
        """Build visual protocol stack"""
        stack = []
        if packet_info.get('src_mac'):
            stack.append("  Ethernet II")
        if packet_info.get('src_ip'):
            stack.append("    └─ IPv4")
            if packet_info.get('type') == 'TCP':
                stack.append("       └─ TCP")
                if packet_info.get('http'):
                    stack.append("          └─ HTTP")
            elif packet_info.get('type') == 'UDP':
                stack.append("       └─ UDP")
                service = packet_info.get('udp_service', '')
                if service and service != "Unknown":
                    stack.append(f"          └─ {service}")
            elif packet_info.get('type') == 'ICMP':
                stack.append("       └─ ICMP")
        return '\n'.join(stack) if stack else "  No protocol stack available"

    def _analyze_signal_strength(self, signal_dbm):
        """Analyze WiFi signal strength"""
        if signal_dbm >= -50:
            return "Excellent (>= -50 dBm)"
        elif signal_dbm >= -60:
            return "Good (-50 to -60 dBm)"
        elif signal_dbm >= -70:
            return "Fair (-60 to -70 dBm)"
        elif signal_dbm >= -80:
            return "Weak (-70 to -80 dBm)"
        else:
            return "Very Weak (< -80 dBm)"
