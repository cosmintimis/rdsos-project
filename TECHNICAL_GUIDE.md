# Technical Guide: WiFi Analyzer Deep Dive

This document explains the technical concepts, protocols, and implementation details of the WiFi Analyzer project.

---

## Table of Contents
1. [WiFi Fundamentals](#wifi-fundamentals)
2. [802.11 Protocol Stack](#80211-protocol-stack)
3. [Beacon Frames Explained](#beacon-frames-explained)
4. [Packet Structure](#packet-structure)
5. [Monitor Mode vs Managed Mode](#monitor-mode-vs-managed-mode)
6. [Raw Socket Programming](#raw-socket-programming)
7. [Manual Packet Parsing](#manual-packet-parsing)
8. [OUI Lookup](#oui-lookup)

---

## WiFi Fundamentals

### What is WiFi?

WiFi is a wireless networking technology that uses radio waves to provide network connectivity. It operates in the **2.4 GHz** and **5 GHz** frequency bands.

### WiFi Channels

Think of WiFi channels like "radio stations" for your wireless network:

- **2.4 GHz Band**: Channels 1-14 (we use 1-13 in most regions)
  - Channel 1 = 2.412 GHz
  - Channel 6 = 2.437 GHz
  - Channel 11 = 2.462 GHz
  - Each channel is separated by **5 MHz**

- **Channel Bandwidth**: Each WiFi network uses ~**20-22 MHz** of bandwidth
  - This means a network on Channel 1 actually occupies channels -1 to 3
  - This is why the graph shows trapezoids spanning **multiple channels**
  
- **Why Channels Matter**: 
  - Overlapping channels cause **interference**
  - Best practice: Use channels 1, 6, and 11 (they don't overlap)

### Signal Strength (dBm)

Signal strength is measured in **dBm** (decibel-milliwatts):

- **-30 dBm**: Excellent (very close to router)
- **-50 dBm**: Very good (strong signal) - **GREEN** 🟢
- **-60 dBm**: Good (reliable connection) - **YELLOW** 🟡
- **-70 dBm**: Fair (weak but usable) - **YELLOW** 🟡
- **-80 dBm**: Poor (unstable) - **RED** 🔴
- **-90 dBm**: Very weak (barely detectable) - **RED** 🔴

**Note**: dBm is a logarithmic scale, so -50 dBm is 10× stronger than -60 dBm!

---

## 802.11 Protocol Stack

WiFi uses the **802.11** family of protocols. Here's the packet structure:

```
┌─────────────────────────────────────────────────────┐
│  Physical Layer (Radio Waves)                       │
├─────────────────────────────────────────────────────┤
│  Radiotap Header (metadata: signal strength, etc.)  │
├─────────────────────────────────────────────────────┤
│  802.11 MAC Header (addresses, frame type)          │
├─────────────────────────────────────────────────────┤
│  802.11 Frame Body (data: SSID, rates, etc.)        │
├─────────────────────────────────────────────────────┤
│  Frame Check Sequence (FCS - error checking)        │
└─────────────────────────────────────────────────────┘
```

### Frame Types

802.11 has three types of frames:

1. **Management Frames** (Type 0):
   - **Beacon** (Subtype 8): Announces WiFi network presence
   - Probe Request/Response: Device searching for networks
   - Authentication/Deauthentication: Connection setup/teardown

2. **Control Frames** (Type 1):
   - ACK: Acknowledge packet receipt
   - RTS/CTS: Request/Clear to send

3. **Data Frames** (Type 2):
   - Actual user data (web traffic, files, etc.)

**Our analyzer focuses on Beacon frames** to discover networks.

---

## Beacon Frames Explained

### What is a Beacon?

A **beacon frame** is like a WiFi network's "heartbeat" - it's a broadcast packet sent every **~100ms** by access points to announce their presence.

### Why Beacons Matter

- **Discovery**: Devices use beacons to find available networks
- **Information**: Beacons contain network details (SSID, security, channel)
- **Passive Scanning**: You can detect networks without connecting

### Beacon Frame Structure

```
┌─────────────────────────────────────────────────┐
│ 802.11 Header                                   │
│  - Type: Management (0)                         │
│  - Subtype: Beacon (8)                          │
│  - BSSID: AP's MAC address (e.g., 40:3F:8C:...) │
├─────────────────────────────────────────────────┤
│ Fixed Parameters (12 bytes)                     │
│  - Timestamp: When beacon was sent              │
│  - Beacon Interval: 100ms (typical)             │
│  - Capability Info: Security flags              │
├─────────────────────────────────────────────────┤
│ Tagged Parameters (variable)                    │
│  - Tag 0: SSID (network name)                   │
│  - Tag 3: Channel (DS Parameter Set)            │
│  - Tag 48: RSN (WPA2 security)                  │
│  - Tag 221: Vendor-specific (WPA, etc.)         │
└─────────────────────────────────────────────────┘
```

### Example: Parsing "Example Network"

When your analyzer sees "Example Network (1)", here's what happened:

1. **Captured beacon packet** on Channel 1
2. **Parsed Radiotap**: Signal = -53 dBm (strong!)
3. **Parsed 802.11 Header**: 
   - Frame Type = 0 (Management)
   - Subtype = 8 (Beacon)
   - BSSID = `02:00:00:AB:CD:EF`
4. **Parsed Tagged Parameters**:
   - Tag 0: SSID = "Example Network"
   - Tag 3: Channel = 1
   - Tag 48: Security = WPA2
5. **OUI Lookup**: `40:3F:8C` → Vendor name

---

## Packet Structure

### What Does Raw Data Look Like?

When you capture a beacon, you get **raw bytes**. Here's a simplified example:

```
Byte Position:  0   1   2   3   4   5   6   7   8   ...
Raw Bytes:     00  00  18  00  2e  48  00  00  10  6c  ...
               └─Radiotap─┘  └───────802.11 Header────...
```

### Radiotap Header

```
Offset  Size  Field              Example
------  ----  -----------------  -------
0       1     Version            0x00
1       1     Pad                0x00
2       2     Length             24 bytes
4       4     Present Flags      0x0000482e
8       8     MAC Timestamp      varies
16      1     Flags              0x10
17      1     Data Rate          54 Mbps
18      2     Channel Frequency  2412 MHz
20      2     Channel Flags      0x00a0
22      1     Antenna Signal     -53 dBm  ← We extract this!
23      1     Antenna            0
```

**What we care about**: Byte 22 = Signal Strength in dBm (signed 8-bit integer)

### 802.11 Header (Management Frame)

```
Offset  Size  Field              Example
------  ----  -----------------  -------
0       2     Frame Control      0x0080  (Type=0, Subtype=8 = Beacon)
2       2     Duration           0x0000
4       6     Destination        FF:FF:FF:FF:FF:FF (broadcast)
10      6     Source (BSSID)     02:00:00:AB:CD:EF
16      6     BSSID              02:00:00:AB:CD:EF
22      2     Sequence Control   varies
```

**Key field**: Frame Control Byte 0, Bits 2-3 = Type, Bits 4-7 = Subtype

To check if it's a beacon:
```python
fc = frame[0]
type_ = (fc >> 2) & 0x3      # Extract bits 2-3
subtype = (fc >> 4) & 0xF    # Extract bits 4-7

if type_ == 0 and subtype == 8:
    # It's a beacon!
```

### Beacon Frame Body (Tagged Parameters)

After the 24-byte header, we have fixed parameters (12 bytes), then tagged parameters:

```
Tag Format:
┌────────┬────────┬─────────────────┐
│Tag Num │ Length │ Data            │
│1 byte  │1 byte  │ 'Length' bytes  │
└────────┴────────┴─────────────────┘

Example Tags:
Tag 0 (SSID):
[00] [0F] [45 78 61 6D 70 6C 65 20 4E 65 74 77 6F 72 6B]
 ↑    ↑    └─"Example Network" in ASCII─┘
Tag#  Len

Tag 3 (Channel):
[03] [01] [01]
 ↑    ↑    ↑
Tag#  Len  Channel 1
```

---

## Monitor Mode vs Managed Mode

### Managed Mode (Normal WiFi)

- **What it is**: Normal mode where your WiFi connects to an access point
- **What you see**: Only packets meant for your device
- **Encryption**: OS handles decryption (if you're connected)
- **Use case**: Packet sniffer for Ethernet traffic

```
Your Device ←─encrypted─→ Router ←──→ Internet
     (Only sees your own traffic)
```

### Monitor Mode

- **What it is**: "Promiscuous" mode that captures ALL WiFi packets in the air
- **What you see**: Everyone's packets (encrypted if WPA2/WPA3)
- **Encryption**: Cannot decrypt others' traffic (we don't have the keys)
- **Use case**: WiFi analyzer, detecting all networks

```
AP1 ╲         ╱ AP2
     ╲       ╱
      Your Antenna  ← Sees ALL beacons, all traffic
     ╱       ╲
Device1      Device2
```

**Important**: In monitor mode:
- ✅ You CAN see: Beacons, MAC addresses, signal strength, channels
- ❌ You CANNOT see: Encrypted data contents (without the WiFi password)

---

## Raw Socket Programming

### What is a Raw Socket?

A **raw socket** gives you direct access to network packets, bypassing the OS's normal TCP/IP stack.

### Socket Types

```python
# Normal socket (TCP/IP)
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# ↑ OS handles everything, you get clean data

# Raw socket (Ethernet)
s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))
# ↑ You get RAW bytes, must parse everything manually
```

### Why Raw Sockets?

- **Full Control**: See every byte of every packet
- **Low-Level Access**: Monitor mode captures, Radiotap headers
- **Learning**: Understand how protocols actually work

### Security Requirement

Raw sockets require **root privileges** because they can:
- Capture all traffic (privacy risk)
- Craft malicious packets (security risk)

```bash
# Must run with sudo
sudo python3 main.py -i wlan0
```

---

## Manual Packet Parsing

### Why Manual Parsing?

This project uses **only Python standard library** - no scapy, no pypcap. This forces you to:
- Understand packet structures deeply
- Learn binary data manipulation
- Appreciate what libraries do for you!

### The `struct` Module

Python's `struct` module converts between bytes and Python types:

```python
import struct

# Read 2 bytes as unsigned short (little-endian)
value = struct.unpack('<H', bytes([0x12, 0x34]))[0]
# Result: 0x3412 = 13330

# Common format characters:
# 'B' = unsigned byte (0-255)
# 'b' = signed byte (-128 to 127)  ← Signal strength!
# 'H' = unsigned short (2 bytes)
# '<' = little-endian, '>' = big-endian
```

### Example: Extracting Signal Strength

```python
def parse_radiotap(packet):
    # Radiotap length is at bytes 2-3 (little-endian short)
    rt_len = struct.unpack('<H', packet[2:4])[0]
    
    # Signal strength is typically 8 bytes before end of radiotap
    # (this is a simplification - real code checks flags)
    signal_pos = rt_len - 8
    signal = struct.unpack('b', packet[signal_pos:signal_pos+1])[0]
    
    return rt_len, signal  # Returns (24, -53) for example
```

### Example: Checking Frame Type

```python
def parse_80211(packet, radiotap_len):
    frame = packet[radiotap_len:]  # Skip radiotap
    
    # Frame Control is first 2 bytes
    fc = frame[0]
    type_ = (fc >> 2) & 0x3      # Bits 2-3
    subtype = (fc >> 4) & 0xF    # Bits 4-7
    
    if type_ == 0 and subtype == 8:
        return "BEACON"
    elif type_ == 2:
        return "DATA"
    else:
        return "OTHER"
```

### Example: Extracting SSID

```python
def extract_ssid(frame):
    tag_offset = 36  # Tags start after fixed parameters
    
    while tag_offset < len(frame):
        tag_num = frame[tag_offset]
        tag_len = frame[tag_offset + 1]
        tag_data = frame[tag_offset + 2 : tag_offset + 2 + tag_len]
        
        if tag_num == 0:  # SSID tag
            return tag_data.decode('utf-8')
        
        tag_offset += 2 + tag_len  # Move to next tag
    
    return "<Hidden>"
```

---

## OUI Lookup

### What is OUI?

**OUI** (Organizationally Unique Identifier) is the first 3 bytes of a MAC address, assigned by IEEE to manufacturers.

### MAC Address Structure

```
MAC: 02:00:00:AB:CD:EF
     └─OUI──┘ └─Device─┘
     
40:3F:8C = Manufacturer (assigned by IEEE)
B4:A0:F6 = Device ID (manufacturer assigns)
```

### Example OUI Mappings

```
00:00:0C → Cisco Systems
3C:5A:B4 → Google
40:3F:8C → Broadcom (used in many routers/laptops)
DC:A6:32 → Raspberry Pi Foundation
```

### How We Do OUI Lookup

1. **Download IEEE database**:
   ```bash
   python3 utils/update_oui.py
   ```
   
   This downloads from: https://standards.ieee.org/develop/regauth/oui/oui.txt

2. **Parse and store as JSON**:
   ```json
   {
     "00:00:0C": "Cisco Systems, Inc.",
     "40:3F:8C": "Broadcom Corporation",
     ...
   }
   ```

3. **Lookup in code**:
   ```python
   def get_vendor(mac_address):
       oui = mac_address[:8].upper()  # "40:3F:8C"
       return OUI_DB.get(oui, "Unknown")
   ```

### Why OUI is Useful

- **Identify device type**: Apple devices, Google phones, TP-Link routers
- **Security**: Detect unauthorized devices on your network
- **Troubleshooting**: Know which manufacturer to contact for issues

---

## Summary: Data Flow

Here's the complete journey of data in this project:

```
1. WiFi Access Point
   ↓ (broadcasts beacon every ~100ms)
   
2. Your WiFi Card (in monitor mode)
   ↓ (captures raw radio waves)
   
3. Raw Socket (AF_PACKET)
   ↓ (receives raw bytes)
   
4. Packet Parser
   ├─→ parse_radiotap()  → signal strength (-53 dBm)
   ├─→ parse_80211()     → frame type, BSSID, channel
   └─→ extract tags      → SSID, security, etc.
   
5. OUI Lookup
   └─→ get_vendor()      → "Broadcom Corporation"
   
6. Queue
   └─→ result_queue.put({'type': 'BEACON', 'ssid': 'Example Network', ...})
   
7. GUI (Tkinter)
   ├─→ Access Points Tab  → Display card with WiFi icon
   └─→ Channel Graph Tab  → Draw trapezoid on channel 1
```

---

## Further Reading

- [IEEE 802.11 Standard](https://standards.ieee.org/standard/802_11-2020.html)
- [Radiotap Format](https://www.radiotap.org/)
- [OUI Database](https://standards.ieee.org/develop/regauth/oui/)
- [Python `struct` Documentation](https://docs.python.org/3/library/struct.html)
- [Linux Wireless Tools](https://wireless.wiki.kernel.org/en/users/documentation/iw)

---

## Glossary

- **AP**: Access Point (WiFi router)
- **BSSID**: Basic Service Set Identifier (AP's MAC address)
- **dBm**: Decibel-milliwatts (signal strength unit)
- **SSID**: Service Set Identifier (WiFi network name)
- **OUI**: Organizationally Unique Identifier (manufacturer code in MAC)
- **Beacon**: Management frame announcing WiFi network
- **Monitor Mode**: Capture all WiFi packets in the air
- **Radiotap**: Header with signal/channel metadata
- **802.11**: WiFi protocol family
- **Tag**: Information element in beacon frame

---

*This guide is for educational purposes to help you understand WiFi technology and network protocols.*
