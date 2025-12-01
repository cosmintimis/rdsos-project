# WiFi Analyzer & Network Packet Sniffer

A professional WiFi analyzer and network packet sniffer built **from scratch** in Python for Linux, featuring a modern Tkinter GUI. This project implements **manual protocol parsing** using only Python's standard library.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-Educational-green.svg)
![Platform](https://img.shields.io/badge/Platform-Linux-red.svg)

## 🎯 Project Goals

**Educational Focus**: Learn network protocols by implementing packet parsing **manually**:
- ✅ **No high-level libraries** (no scapy, pypcap, impacket)
- ✅ **Raw socket programming** (`socket.AF_PACKET`)
- ✅ **Manual byte-level parsing** using `struct` module
- ✅ **Direct hardware control** via Linux WiFi tools

## ✨ Features

### 📡 WiFi Analyzer (Monitor Mode)

**Access Points Tab**:
- Real-time WiFi network discovery via beacon frame capture
- Color-coded signal strength indicators (WiFi icons: 🟢 🟡 🔴)
- Network details: SSID, BSSID, vendor (OUI lookup), channel, frequency
- **Advanced security analysis**: WPA2/WPA3 detection, cipher suites, authentication methods
- Click any network for detailed information dialog

**Channel Graph**:
- Visual spectrum analyzer showing network distribution
- Trapezoidal signal visualization representing bandwidth spread
- Real-time signal strength from -90 to -20 dBm
- Channel overlap detection (shows interference)

**Channel Hopping**:
- Automatically scans all 2.4GHz channels (1-13)
- Discovers networks across entire spectrum
- 0.5 second dwell time per channel

### 🔍 Packet Sniffer (Managed/Monitor Mode)

**Packet Capture**:
- Captures TCP, UDP, ICMP, and raw Ethernet frames
- **Complete protocol field extraction**:
  - **IP**: All 14 header fields (version, TTL, flags, checksum, etc.)
  - **TCP**: All fields (seq/ack numbers, flags, window size, etc.)
  - **UDP**: Port, length, checksum, service detection
  - **ICMP**: Type, code, ping detection
- **HTTP payload parsing**: Detects GET/POST requests and responses
- **Smart binary detection**: Distinguishes text vs binary content

**GUI Features**:
- ⏸️ **Pause/Resume** capture for inspection
- 🔍 **Protocol filter**: HTTP Only, TCP Only, UDP Only, ICMP Only
- 📊 **Packet details**: Double-click for multi-tab detailed view
- Real-time packet list with source/destination/protocol info

## 🛠️ Technical Highlights

### Manual Protocol Parsing

**802.11 WiFi Stack**:
```
Radiotap Header → 802.11 MAC → Beacon Frame Body → Tagged Parameters
     ↓                ↓              ↓                    ↓
Signal strength   Frame type     SSID, Channel      RSN (security)
```

**Network Stack**:
```
Ethernet/802.11 → IP → TCP/UDP/ICMP → HTTP
       ↓          ↓         ↓            ↓
   MAC addrs   IPs/TTL   Ports/Flags  Payload
```

**Protocols Implemented**:
- ✅ Radiotap (WiFi metadata)
- ✅ 802.11 Management Frames (beacons)
- ✅ RSN Information Element (WPA2/WPA3)
- ✅ Ethernet II frames
- ✅ IPv4 (complete header)
- ✅ TCP (complete header)
- ✅ UDP (complete header)
- ✅ ICMP (echo request/reply)
- ✅ HTTP (requests & responses)

### Architecture

```
┌─────────────────────────────────────────────────┐
│  GUI (Tkinter)                                  │
│  - Access Points Tab  - Sniffer Tab             │
│  - Channel Graph      - Packet Details Dialog   │
└──────────────────┬──────────────────────────────┘
                   │ queue.Queue
        ┌──────────┴──────────┐
        ↓                     ↓
┌───────────────┐    ┌────────────────┐
│ Channel       │    │ Packet Sniffer │
│ Hopper Thread │    │ Thread         │
│ (WiFi only)   │    │ (AF_PACKET)    │
└───────┬───────┘    └────────┬───────┘
        │                     │
        ↓                     ↓
┌──────────────────────────────────────┐
│  PacketParser (core/parser.py)       │
│  - parse_radiotap()                  │
│  - parse_80211()                     │
│  - parse_rsn_ie()                    │
│  - parse_ip_tcp()                    │
│  - parse_http_payload()              │
└──────────────────────────────────────┘
```

## 📋 Requirements

- **OS**: Linux (tested on Kali Linux)
- **Python**: 3.8+
- **WiFi Tools**: `airmon-ng`, `iwconfig` or `iw`
- **Permissions**: Root access (for raw sockets)

## 🚀 Installation & Usage

### 1. Enable Monitor Mode (for WiFi analysis)

```bash
sudo airmon-ng start wlan0
```

### 2. Run WiFi Analyzer

```bash
# Scan all channels with hopping
sudo python3 main.py -i wlan0

# Lock to specific channel
sudo python3 main.py -i wlan0 -c 6

# Enable debug output
sudo python3 main.py -i wlan0 --debug
```

### 3. Run Packet Sniffer (Managed Mode)

```bash
# Connect to WiFi first, then:
sudo python3 main.py -i wlan0 --managed
```

## 📁 Project Structure

```
project-rdsos/
├── main.py                    # Entry point, argument parsing
├── core/
│   ├── hopper.py             # Channel hopping thread (monitors all channels)
│   ├── sniffer.py            # Raw socket packet capture (AF_PACKET)
│   └── parser.py             # Manual packet parsing (500+ lines)
├── gui/
│   ├── app.py                # Main Tkinter window
│   ├── access_points_tab.py  # WiFi network list with detail dialog
│   ├── channel_graph_tab.py  # Visual spectrum analyzer
│   └── sniffer_tab.py        # Packet list with filters & pause
├── utils/
│   ├── constants.py          # Protocol IDs, frequency calculations
│   ├── oui.py               # MAC vendor lookup (IEEE database)
│   └── update_oui.py        # OUI database updater
└── README.md, TECHNICAL_GUIDE.md  # Documentation
```

## 🎓 Educational Value

This project teaches:

1. **Network Protocols**: Deep understanding of WiFi, IP, TCP, UDP, ICMP, HTTP
2. **Binary Data**: Parsing structured binary data with `struct`
3. **Raw Sockets**: Low-level network programming
4. **WiFi Technology**: Monitor mode, channels, beacons, security
5. **Threading**: Concurrent packet capture and GUI updates
6. **Linux Internals**: WiFi drivers, kernel interfaces

## 🔧 How It Works

### WiFi Analysis Mode

1. **Monitor Mode**: Interface captures all WiFi packets (promiscuous)
2. **Channel Hopping**: Cycles through channels 1-13 every 0.5s
3. **Beacon Detection**: Filters management frames (type 0, subtype 8)
4. **Manual Parsing**: Extracts SSID, BSSID, channel, signal from raw bytes
5. **RSN Analysis**: Parses security information (ciphers, auth methods)
6. **GUI Update**: Displays networks in real-time

### Packet Sniffer Mode

1. **Raw Socket**: Opens `AF_PACKET` socket (all link-layer frames)
2. **Packet Capture**: Receives Ethernet/802.11 frames
3. **Protocol Detection**: Identifies IP, TCP, UDP, ICMP by protocol field
4. **Field Extraction**: Parses all header fields (30+ fields per packet)
5. **HTTP Detection**: Checks port 80, parses GET/POST requests
6. **Binary Detection**: Identifies images/videos vs text content

## 🐛 Troubleshooting

### No WiFi networks detected

**Check monitor mode**:
```bash
iwconfig wlan0  # Should show "Mode:Monitor"
```

**Verify nearby networks**:
```bash
sudo airodump-ng wlan0  # Reference tool
```

**Solutions**:
- Ensure 2.4GHz networks nearby (project doesn't support 5GHz yet)
- Some WiFi cards have poor monitor mode support
- Try `sudo airmon-ng check kill` to stop interfering processes

### No packets in Sniffer tab

**For Monitor Mode**: Lock to a channel with active traffic:
```bash
sudo python3 main.py -i wlan0 -c 1
```

**For Managed Mode**: Ensure connected to WiFi:
```bash
nmcli dev status  # Check connection
```

## 📚 Documentation

- **[TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md)**: Deep dive into WiFi theory, packet structure, protocol details
- **[task.md](/.gemini/.../task.md)**: Development task tracking
- Code comments: Detailed explanations in parser.py

## 🎯 Future Enhancements

- [ ] 5GHz band support (channels 36-165)
- [ ] IPv6 support
- [ ] DNS query parsing
- [ ] Packet statistics dashboard
- [ ] Export to PCAP format
- [ ] Deauthentication attack detection

## ⚖️ License & Ethics

**Educational use only.** This tool is designed for learning network protocols.

**Legal considerations**:
- ✅ Use on your own networks
- ✅ Use in lab environments with permission
- ❌ Do not capture traffic on networks you don't own
- ❌ Do not use for malicious purposes

Packet sniffing and network analysis may be illegal without proper authorization.

## 🙏 Credits

- **OUI Database**: [IEEE Registration Authority](https://standards.ieee.org/develop/regauth/oui/)
- **Inspired by**: Android WiFi Analyzer, Wireshark
- **Built with**: Python standard library, Tkinter, Linux WiFi tools

---

**Made for educational purposes to understand WiFi and network protocols from the ground up.**

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
