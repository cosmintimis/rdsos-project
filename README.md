# WiFi Analyzer & Network Packet Sniffer

A professional WiFi analyzer and network packet sniffer built from scratch in Python for Kali Linux, featuring a modern Tkinter GUI inspired by Android WiFi Analyzer.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-Educational-green.svg)
![Platform](https://img.shields.io/badge/Platform-Kali%20Linux-red.svg)

## Features

### 📡 WiFi Analyzer
- **Access Points Tab**: List all detected WiFi networks with:
  - Color-coded signal strength indicators (WiFi icons)
  - SSID, BSSID, and vendor information (OUI lookup)
  - Channel, frequency, and security type
  - Click-to-expand detail dialog
- **Channel Graph**: Visual representation of WiFi channel usage
  - Trapezoidal signal visualization showing bandwidth spread
  - Real-time signal strength from -90 to -20 dBm
  - Channel overlap detection

### 🔍 Packet Sniffer
- Capture and analyze network traffic in real-time
- Support for both Monitor Mode (802.11) and Managed Mode (Ethernet)
- Display source/destination IPs and MACs
- HTTP traffic detection and preview

### 🛠️ Technical Highlights
- **Manual packet parsing** using only Python standard library (`struct`, `socket`)
- **No high-level libraries** (no scapy, pypcap, or impacket)
- **Raw socket programming** for direct packet capture
- **Dynamic OUI database** with automatic updates from IEEE

## Requirements

- **OS**: Kali Linux (or any Linux with WiFi tools)
- **Python**: 3.8 or higher
- **Tools**: `airmon-ng`, `iwconfig`
- **Permissions**: Root access (for raw socket operations)

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd project-rdsos
   ```

2. **Update OUI database** (optional):
   ```bash
   python3 utils/update_oui.py
   ```

3. **Enable monitor mode**:
   ```bash
   sudo airmon-ng start wlan0
   ```

## Usage

### WiFi Analyzer (Monitor Mode)

Analyze WiFi networks on 2.4GHz channels:

```bash
# Basic usage (channel hopping)
sudo python3 main.py -i wlan0

# Lock to specific channel
sudo python3 main.py -i wlan0 -c 6

# Enable debug output
sudo python3 main.py -i wlan0 --debug
```

### Packet Sniffer (Managed Mode)

Sniff Ethernet traffic on a connected interface:

```bash
sudo python3 main.py -i wlan0 --managed
```

## Project Structure

```
project-rdsos/
├── main.py                 # Application entry point
├── core/
│   ├── hopper.py          # Channel hopping thread
│   ├── sniffer.py         # Raw socket packet capture
│   └── parser.py          # Manual packet parsing (Radiotap, 802.11, IP, TCP)
├── gui/
│   ├── app.py             # Main Tkinter window
│   ├── access_points_tab.py  # AP list view with WiFi icons
│   ├── channel_graph_tab.py  # Channel visualization
│   └── sniffer_tab.py     # Packet list view
└── utils/
    ├── constants.py       # Protocol IDs and offsets
    ├── oui.py            # MAC vendor lookup
    └── update_oui.py     # OUI database updater
```

## How It Works

1. **Monitor Mode**: Interface captures all WiFi packets in the air
2. **Channel Hopping**: Cycles through channels 1-13 to detect all networks
3. **Packet Capture**: Raw socket (`AF_PACKET`) receives all traffic
4. **Manual Parsing**: 
   - Radiotap header → extract signal strength
   - 802.11 header → identify beacons, extract SSID/BSSID
   - IP/TCP headers → extract network traffic details
5. **Queue-based UI**: Background threads push data to GUI via `queue.Queue`

## Troubleshooting

### No packets captured

**Problem**: `tcpdump` shows 0 packets on monitor interface

**Solutions**:
1. Ensure monitor mode is active: `iwconfig wlan0`
2. Check for 2.4GHz networks nearby: `sudo iwlist wlan0 scan | grep "2.4"`
3. Try different WiFi adapter (some chipsets have poor monitor mode support)
4. Run `sudo airmon-ng check kill` to stop interfering processes

### GUI doesn't start

**Problem**: Application runs but no window appears

**Solutions**:
1. Ensure you have X11 display: `echo $DISPLAY`
2. If using SSH, enable X11 forwarding: `ssh -X user@host`
3. Check for errors in terminal output

### Empty access points list

**Problem**: GUI loads but no networks appear

**Solutions**:
1. Wait for channel hopper to cycle (13 channels × 0.5s = ~6.5 seconds)
2. Lock to a channel with active networks: `sudo python3 main.py -i wlan0 -c 1`
3. Verify `airodump-ng wlan0` can see networks

## Educational Purpose

This project was built as a learning exercise to understand:
- Raw socket programming in Python
- WiFi protocol stack (802.11, Radiotap)
- Packet structure and manual byte parsing
- Linux wireless tools and monitor mode
- GUI development with Tkinter

**Note**: This tool is for educational purposes only. Only use on networks you own or have permission to analyze.

## Credits

- **OUI Database**: [IEEE Registration Authority](https://standards.ieee.org/develop/regauth/oui/oui.txt)
- **Inspired by**: Android WiFi Analyzer

## License

Educational use only. Not for commercial or malicious purposes.
