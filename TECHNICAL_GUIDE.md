# Technical Guide: WiFi Analyzer Deep Dive

This document explains **everything** about WiFi technology, electromagnetic spectrum, and how this project works under the hood.

---

## Table of Contents

1. [Electromagnetic Spectrum Fundamentals](#electromagnetic-spectrum-fundamentals)
2. [Radio Waves & WiFi](#radio-waves--wifi)
3. [2.4GHz vs 5GHz: Complete Comparison](#24ghz-vs-5ghz-complete-comparison)
4. [WiFi Channels Explained](#wifi-channels-explained)
5. [802.11 Protocol Stack](#80211-protocol-stack)
6. [Monitor Mode vs Managed Mode](#monitor-mode-vs-managed-mode)
7. [Beacon Frames Deep Dive](#beacon-frames-deep-dive)
8. [Packet Structure & Parsing](#packet-structure--parsing)
9. [Raw Socket Programming](#raw-socket-programming)
10. [Security: WPA/WPA2/WPA3](#security-wpawpa2wpa3)

---

## Electromagnetic Spectrum Fundamentals

### What is Electromagnetic Radiation?

**Electromagnetic (EM) radiation** is energy that travels through space as **waves**. These waves don't need a medium (like air or water) to travel - they can move through a vacuum at the speed of light (299,792,458 m/s).

```
Electromagnetic Wave:
     ↑ Electric Field
     |    
~~~∿∿∿∿∿∿~~~ → Direction of travel
     |
     ↓ Magnetic Field
```

### The EM Spectrum

EM radiation comes in different wavelengths/frequencies, forming the **electromagnetic spectrum**:

```
Frequency (Hz)              | Type            | Example Use
---------------------------|-----------------|------------------
10^3  (1 kHz)              | Radio Waves     | AM Radio
10^6  (1 MHz)              | Radio Waves     | FM Radio  
10^9  (1 GHz)              | Microwaves      | WiFi (2.4/5 GHz)
10^12 (1 THz)              | Infrared        | Heat, Remote Controls
10^15 (1 PHz)              | Visible Light   | Human vision
10^16                      | Ultraviolet     | Sunburn
10^18                      | X-Rays          | Medical imaging
10^20                      | Gamma Rays      | Nuclear reactions
```

**Key relationship**: 
- **Higher frequency** = Shorter wavelength = More energy
- **Lower frequency** = Longer wavelength = Less energy

Formula: `Speed of Light = Frequency × Wavelength`
- `c = f × λ`
- `299,792,458 m/s = f × λ`

### WiFi on the EM Spectrum

WiFi uses **microwave radio waves**:

**2.4 GHz WiFi**:
- Frequency: 2,400,000,000 cycles per second
- Wavelength: `λ = c/f = 299,792,458 / 2,400,000,000 ≈ 0.125 meters (12.5 cm)`
- Energy: Low (non-ionizing, safe for humans)

**5 GHz WiFi**:
- Frequency: 5,000,000,000 cycles per second
- Wavelength: `λ = c/f = 299,792,458 / 5,000,000,000 ≈ 0.06 meters (6 cm)`
- Energy: Still low (non-ionizing)

---

## Radio Waves & WiFi

### How WiFi Transmits Data

WiFi uses **radio waves** to encode binary data (0s and 1s) and transmit it wirelessly.

**Process**:
1. **Data → Binary**: Your message becomes 1s and 0s
2. **Modulation**: Binary data modulates (changes) the radio wave
3. **Transmission**: Antenna broadcasts the modulated wave
4. **Reception**: Receiver's antenna picks up the wave
5. **Demodulation**: Extract binary data from the wave
6. **Binary → Data**: Reconstruct your message

**Modulation Techniques** (how 1s and 0s are encoded):

```
Original Signal (carrier wave):
   ∿∿∿∿∿∿∿∿∿∿∿

Amplitude Shift Keying (ASK) - Change amplitude:
   1: ∿∿∿∿∿∿∿∿∿    0: ∙∙∙∙∙∙∙∙∙
   (big waves)      (small waves)

Frequency Shift Keying (FSK) - Change frequency:
   1: ∿∿∿∿∿∿∿∿∿    0: ∾∾∾∾∾∾∾∾∾
   (fast cycles)    (slow cycles)

Phase Shift Keying (PSK) - Change phase:
   1: ∿∿∿∿∿∿∿∿∿    0: ∿∿ ‾‾ ∿∿
   (normal)         (inverted)
```

**WiFi uses**: OFDM (Orthogonal Frequency-Division Multiplexing)
- Combines multiple modulation techniques
- Uses many sub-carriers simultaneously
- Very efficient for high-speed data

### Antenna Physics

Your WiFi antenna **converts**:
- **Transmit**: Electrical signal → Radio waves
- **Receive**: Radio waves → Electrical signal

```
Transmit:                    Receive:
Computer                     Radio waves
   ↓                              ↓
Binary data                  Antenna
   ↓                              ↓
WiFi chip (modulates)        Electrical signal
   ↓                              ↓
Antenna (radiates)           WiFi chip (demodulates)
   ↓                              ↓
Radio waves                  Binary data
```

**Antenna gain** (measured in dBi):
- Higher dBi = More focused, longer range
- Lower dBi = Omnidirectional, shorter range

---

## 2.4GHz vs 5GHz: Complete Comparison

### Frequency Bands

**2.4 GHz Band** (This project supports):
- Frequency range: **2.400 - 2.4835 GHz**
- Channels: **1-14** (13 in Europe, 11 in USA, 14 in Japan)
- Bandwidth per channel: **20-22 MHz**
- **Wavelength**: ~12.5 cm

**5 GHz Band** (Not supported yet):
- Frequency range: **5.150 - 5.850 GHz**
- Channels: **36, 40, 44, 48, 52... up to 165**
- Bandwidth options: **20, 40, 80, 160 MHz**
- **Wavelength**: ~6 cm

### Physical Properties Comparison

| Property | 2.4 GHz | 5 GHz |
|----------|---------|-------|
| **Wavelength** | 12.5 cm (longer) | 6 cm (shorter) |
| **Wall Penetration** | ✅ Better | ❌ Worse |
| **Range** | ✅ Longer (~150m outdoor) | ❌ Shorter (~50m outdoor) |
| **Speed** | ❌ Slower (max ~600 Mbps) | ✅ Faster (max ~3.5 Gbps) |
| **Interference** | ❌ High (crowded) | ✅ Low (less crowded) |
| **Devices** | ✅ All devices | ❌ Newer devices only |

### Why These Differences?

**Physics of Wave Propagation**:

1. **Range & Penetration** (2.4 GHz wins):
   ```
   Longer wavelength (2.4 GHz) = 
   → Better diffraction around obstacles
   → Lower absorption by walls/materials
   → Longer range
   
   Shorter wavelength (5 GHz) =
   → More easily blocked by obstacles
   → Higher absorption
   → Shorter range but more bandwidth
   ```

2. **Speed** (5 GHz wins):
   ```
   Higher frequency (5 GHz) =
   → More "room" for channels
   → Wider channel bandwidth (160 MHz vs 20 MHz)
   → More data per second
   ```

3. **Interference** (5 GHz wins):
   ```
   2.4 GHz band:
   - Microwaves: ~2.45 GHz
   - Bluetooth: ~2.4 GHz
   - Cordless phones: ~2.4 GHz
   - Baby monitors: ~2.4 GHz
   → Very crowded!
   
   5 GHz band:
   - Less consumer devices
   - More channels available
   → Less crowded
   ```

### Real-World Scenarios

**Choose 2.4 GHz when**:
- ✅ Large house/office (need range)
- ✅ Thick walls
- ✅ Older devices
- ✅ IoT devices (smart home)

**Choose 5 GHz when**:
- ✅ Same room as router
- ✅ Need high speed (streaming 4K, gaming)
- ✅ Crowded apartment (many neighbors)
- ✅ Modern devices

---

## WiFi Channels Explained

### What is a Channel?

A **channel** is a specific frequency range that WiFi uses to communicate. Think of channels like **lanes on a highway** - they keep traffic organized.

### 2.4 GHz Channel Structure

```
Frequency (GHz):  2.400    2.420    2.440    2.460    2.480
                   |         |         |         |         |
Channel 1:      [====22MHz====]
Channel 2:         [====22MHz====]
Channel 3:            [====22MHz====]
Channel 4:               [====22MHz====]
...
Channel 11:                            [====22MHz====]
Channel 12:                               [====22MHz====]
Channel 13:                                  [====22MHz====]

Center Frequencies:
Ch 1:  2.412 GHz
Ch 6:  2.437 GHz
Ch 11: 2.462 GHz
```

**Key facts**:
- Each channel is **5 MHz** apart (center frequencies)
- Each channel uses **~22 MHz** bandwidth
- **Channels overlap!** (This causes interference)

### Channel Overlap Problem

```
Channel 1:    [-----WiFi Network A-----]
Channel 2:       [-----WiFi Network B-----]
Channel 3:          [-----WiFi Network C-----]
                 
                 ← OVERLAP = INTERFERENCE! →
```

**Solution: Non-overlapping channels**:
```
Channel 1:    [-----WiFi Network A-----]
                                    
Channel 6:                        [-----Network B-----]
                                    
Channel 11:                                          [-----Network C-----]

No overlap = No interference!
```

**Best practice**: Use channels **1, 6, and 11** only (these don't overlap).

### Why Channel Hopping is Essential

Your WiFi card can **only listen to ONE channel** at a time:

```
Without Hopping (locked to Ch 1):
Time: 0s----1s----2s----3s----4s----5s---->
      [Ch 1][Ch 1][Ch 1][Ch 1][Ch 1][Ch 1]
                    
Sees: Only networks on Channel 1

With Hopping:
Time: 0s-0.5s-1s-1.5s-2s-2.5s-3s-3.5s-4s-->
      [Ch 1][Ch 2][Ch 3][Ch 4][Ch 5][Ch 6]...
                    
Sees: Networks on ALL channels!
```

**This project's hopper**:
- Cycles through channels 1-13
- Spends 0.5 seconds per channel
- Full cycle: **6.5 seconds** (13 × 0.5s)
- Repeats forever

### Visualizing in Channel Graph

The **Channel Graph** tab shows:

```
Signal Strength (dBm)
        ↑
   -20  |
        |        _____
   -40  |       ╱     ╲ ← Network A (Channel 6)
        |      ╱       ╲
   -60  |  ___╱         ╲___
        | ╱                 ╲___
   -80  |╱                      ╲___
        |                            
   -100 └─┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬→
          1  2  3  4  5  6  7  8  9 10 11 12 13
                        WiFi Channels
```

**Trapezoid shape** represents:
- **Center**: Actual channel (e.g., Channel 6)
- **Width**: The ~22 MHz bandwidth (spanning ~4-5 channels)
- **Height**: Signal strength (higher = stronger)

---

## 802.11 Protocol Stack

### WiFi Protocol Family

**802.11** is the **IEEE standard** for WiFi. Different versions have evolved:

| Standard | Year | Max Speed | Frequency |
|----------|------|-----------|-----------|
| 802.11   | 1997 | 2 Mbps    | 2.4 GHz   |
| 802.11b  | 1999 | 11 Mbps   | 2.4 GHz   |
| **802.11g** | **2003** | **54 Mbps** | **2.4 GHz** ← This project |
| 802.11n  | 2009 | 600 Mbps  | 2.4/5 GHz |
| 802.11ac | 2013 | 3.5 Gbps  | 5 GHz     |
| 802.11ax (WiFi 6) | 2019 | 9.6 Gbps | 2.4/5 GHz |

### 802.11 Frame Structure

WiFi packets have a **layered structure**:

```
┌─────────────────────────────────────┐
│ Radiotap Header (variable length)  │ ← Metadata (our project parses this)
├─────────────────────────────────────┤
│ 802.11 MAC Header (24+ bytes)      │ ← Frame type, addresses
├─────────────────────────────────────┤
│ Frame Body (variable)               │ ← Actual data (beacons, data, etc.)
├─────────────────────────────────────┤
│ FCS - Frame Check Sequence (4 bytes)│ ← Error detection
└─────────────────────────────────────┘
```

### Frame Types

802.11 defines **three types** of frames:

**1. Management Frames** (Type 0):
```
Subtype 0x00: Association Request
Subtype 0x01: Association Response
Subtype 0x04: Probe Request
Subtype 0x05: Probe Response
Subtype 0x08: Beacon ← **This project captures these!**
Subtype 0x0B: Authentication
Subtype 0x0C: Deauthentication
```

**2. Control Frames** (Type 1):
```
Subtype 0x09: PS-Poll
Subtype 0x0B: RTS (Request to Send)
Subtype 0x0C: CTS (Clear to Send)
Subtype 0x0D: ACK (Acknowledgment)
```

**3. Data Frames** (Type 2):
```
Subtype 0x00: Data
Subtype 0x08: QoS Data
→ Contains: IP → TCP/UDP → HTTP (what sniffer tab captures)
```

---

## Monitor Mode vs Managed Mode

### Radio Modes Explained

Your WiFi card can operate in different *modes*:

**Managed Mode** (Normal WiFi):
```
Your Computer ↔ Access Point ↔ Internet
      ↑
   Connected, authenticated
   Only sees: Packets addressed to you
```

**Monitor Mode** (Promiscuous):
```
                 AP1 ╲
                      ╲ Broadcast beacons
                       ╲
Your Computer (listening)  ← Hears EVERYTHING
                       ╱
                      ╱ Networks
                 AP2 ╱
                 
Not connected to any AP
Sees ALL packets in the air
```

### Technical Differences

| Aspect | Managed Mode | Monitor Mode |
|--------|--------------|--------------|
| **Connected** | Must authenticate to AP | Not connected |
| **Packets seen** | Only your traffic | All WiFi traffic nearby |
| **Filtering** | Driver filters non-relevant | Driver passes all frames |
| **Decryption** | OS decrypts (has key) | Cannot decrypt (no keys) |
| **Use case** | Normal internet | Packet analysis |
| **Channel** | Fixed (AP's channel) | Can change (channel hopping) |

### What This Project Uses

**Monitor Mode** (Access Points Tab):
- **Purpose**: Discover WiFi networks
- **Sees**: Beacon frames from all APs
- **Cannot**: Connect to WiFi or decrypt data
- **Can**: See SSID, channel, signal, security type

**Managed/Monitor Mode** (Sniffer Tab):
- **Managed**: Capture traffic on connected network
- **Monitor**: Capture all 802.11 frames (often encrypted)

---

## Beacon Frames Deep Dive

### What is a Beacon Frame?

A **beacon** is WiFi's "heartbeat" - access points broadcast beacons **10 times per second** (every ~100ms) to announce their presence.

**Purpose**:
1. **Network Discovery**: Devices find available WiFi
2. **Synchronization**: Keep devices time-synced
3. **Information**: Advertise capabilities, security,channel

### Beacon Frame Structure

```
┌──────────────────────────────────────────────┐
│ Radiotap Header (variable, usually ~24 bytes)│
│  - Version, length, flags                    │
│  - Signal strength (dBm) ← We extract this!  │
│  - Channel frequency                         │
│  - Data rate                                 │
└──────────────────────────────────────────────┘
         ↓
┌──────────────────────────────────────────────┐
│ 802.11 Header (24 bytes)                     │
│  Byte 0: Frame Control                       │
│    - Type: 0 (Management)                    │
│    - Subtype: 8 (Beacon)                     │
│  Bytes 4-9: Destination (FF:FF:FF:FF:FF:FF) │
│  Bytes 10-15: Source (BSSID/AP MAC)         │
│  Bytes 16-21: BSSID (same as source)        │
└──────────────────────────────────────────────┘
         ↓
┌──────────────────────────────────────────────┐
│ Fixed Parameters (12 bytes)                  │
│  - Timestamp (8 bytes)                       │
│  - Beacon Interval (2 bytes): usually 100ms  │
│  - Capability Info (2 bytes): privacy bit    │
└──────────────────────────────────────────────┘
         ↓
┌──────────────────────────────────────────────┐
│ Tagged Parameters (variable)                 │
│  Tag 0: SSID (network name)                  │
│  Tag 3: DS Parameter Set (channel number)    │
│  Tag 48: RSN (WPA2/WPA3 security)           │
│  Tag 221: Vendor Specific (WPA, etc.)        │
└──────────────────────────────────────────────┘
```

### Tagged Parameters Format

Each tag follows this structure:

```
┌─────────┬─────────┬──────────────────┐
│ Tag Num │ Length  │ Data             │
│ 1 byte  │ 1 byte  │ 'Length' bytes   │
└─────────┴─────────┴──────────────────┘

Example - Tag 0 (SSID):
[00] [0D] [45 78 61 6D 70 6C 65 20 4E 65 74 77 6F 72 6B]
 ↑    ↑    └────"Example Network " in ASCII──────┘
Tag   Len   

Example - Tag 3 (Channel):
[03] [01] [06]
 ↑    ↑    ↑
Tag   Len  Channel 6
```

### How This Project Parses Beacons

```python
# 1. Parse Radiotap
radiotap_len, signal = parse_radiotap(packet)
# → signal = -53 dBm

# 2. Check frame type
frame = packet[radiotap_len:]
fc = frame[0]
type_ = (fc >> 2) & 0x3      # Bits 2-3
subtype = (fc >> 4) & 0xF    # Bits 4-7

if type_ == 0 and subtype == 8:
    # It's a beacon!
    
    # 3. Extract BSSID
    bssid = frame[10:16]  # Bytes 10-15
    # → "02:00:00:AB:CD:EF"
    
    # 4. Parse tagged parameters
    tag_offset = 36  # After fixed params
    while tag_offset < len(frame):
        tag_num = frame[tag_offset]
        tag_len = frame[tag_offset + 1]
        tag_data = frame[tag_offset+2 : tag_offset+2+tag_len]
        
        if tag_num == 0:  # SSID
            ssid = tag_data.decode('utf-8')
        elif tag_num == 3:  # Channel
            channel = tag_data[0]
        elif tag_num == 48:  # RSN
            security = parse_rsn_ie(tag_data)
```

---

## Packet Structure & Parsing

### Raw Bytes to Information

When you capture a packet, you get **raw bytes**. Your job is to **interpret** these bytes according to protocol specifications.

### Example: Real Beacon Packet

```
Hex Dump (actual captured bytes):
00 00 18 00 2e 48 00 00 | 10 6c 09 a0 00 00 00 00 | ← Radiotap (24 bytes)
10 00 00 00 44 18 00 00 | 80 00 00 00 ff ff ff ff | ← 802.11 Header start
ff ff 02 00 00 ab cd ef | 02 00 00 ab cd ef 00 00 | ← BSSID
...

Interpreted:
Radiotap Header:
  - Length: 24 bytes (offset 2-3: 0x0018)
  - Signal: -53 dBm (offset 22: 0xCB = -53 signed)
  
802.11 Header:
  - Frame Control: 0x0080
    - Type: 0 (bits 2-3)
    - Subtype: 8 (bits 4-7) → BEACON!
  - BSSID: 02:00:00:AB:CD:EF
  
Beacon Body:
  - Tag 0 (SSID): "Example Network"
  - Tag 3 (Channel): 1
  - Tag 48 (RSN): WPA2, CCMP cipher
```

### The `struct` Module

Python's `struct` module converts between bytes and Python types:

```python
import struct

# Read 2 bytes as unsigned short (little-endian)
data = b'\x18\x00'
value = struct.unpack('<H', data)[0]
# Result: 0x0018 = 24

# Format characters:
'<'  # Little-endian (least significant byte first)
'>'  # Big-endian (most significant byte first)
'!'  # Network byte order (= big-endian)

'B'  # unsigned char (1 byte, 0-255)
'b'  # signed char (1 byte, -128 to 127)
'H'  # unsigned short (2 bytes)
'I'  # unsigned int (4 bytes)
```

### IP Header Parsing Example

```python
# IP header is 20 bytes minimum
ip_header = packet[14:34]  # After Ethernet (14 bytes)

# Byte 0: Version + IHL
version_ihl = ip_header[0]
version = version_ihl >> 4     # Upper 4 bits
ihl = version_ihl & 0x0F       # Lower 4 bits

# Bytes 2-3: Total Length
total_length = struct.unpack('!H', ip_header[2:4])[0]

# Byte 8: TTL
ttl = ip_header[8]

# Byte 9: Protocol
protocol = ip_header[9]
# 1 = ICMP, 6 = TCP, 17 = UDP

# Bytes 12-15: Source IP
src_ip = socket.inet_ntoa(ip_header[12:16])
# Converts bytes to "192.168.1.1" format
```

---

## Raw Socket Programming

### What is a Raw Socket?

A **raw socket** gives you direct access to **network packets** at the link layer, bypassing the OS's TCP/IP stack.

```
Normal Socket (e.g., HTTP):
  Application
      ↓
  TCP/IP Stack (OS handles everything)
      ↓
  Network Driver
      ↓
  Physical Network

Raw Socket:
  Application ← Gets raw bytes directly!
      ↓
  Network Driver
      ↓
  Physical Network
```

### AF_PACKET Socket

This project uses `AF_PACKET` (Linux-specific):

```python
import socket

# Create raw socket
s = socket.socket(
    socket.AF_PACKET,    # Address family: packet interface
    socket.SOCK_RAW,     # Socket type: raw
    socket.htons(0x0003) # Protocol: ETH_P_ALL (all protocols)
)

# Bind to interface
s.bind(("wlan0", 0))

# Receive packet
packet = s.recvfrom(65535)[0]  # Up to 65535 bytes

# Now 'packet' contains RAW BYTES from wire!
```

**Why `0x0003` (ETH_P_ALL)?**
- Captures **all Ethernet packet types**
- Including: IPv4 (0x0800), ARP (0x0806), IPv6 (0x86DD)

### Monitor Mode Capture

In monitor mode, packets include **Radiotap header**:

```
packet = s.recvfrom(65535)[0]

Structure:
[Radiotap][802.11 Header][802.11 Body][FCS]
 ↑        ↑              ↑
 Metadata WiFi header   Actual data
```

**Parse order**:
1. Read Radiotap length (bytes 2-3)
2. Extract signal strength from Radiotap
3. Skip Radiotap, parse 802.11 header
4. Check frame type (beacon, data, etc.)
5. Parse frame body

---

## Security: WPA/WPA2/WPA3

### WiFi Security Evolution

```
Timeline:
1997: WEP (Wired Equivalent Privacy)
       ↓ Broken in 2001 (RC4 weak)
       
2003: WPA (WiFi Protected Access)
       ↓ Temporary fix using TKIP
       
2004: WPA2 (802.11i standard)
       Uses AES-CCMP (strong!)
       ↓ Still vulnerable to key reinstall (KRACK)
       
2018: WPA3 (802.11w + SAE)
       Uses SAE (Simultaneous Authentication of Equals)
       Forward secrecy, no pre-shared key vulnerabilities
```

### RSN Information Element

**RSN IE** (Robust Security Network) appears in beacon Tag 48:

```
Structure:
┌──────────┬────────────────┬─────────────────┬───────────┐
│ Version  │ Group Cipher   │ Pairwise Count  │ Pairwise  │
│ 2 bytes  │ 4 bytes        │ 2 bytes         │ Suites... │
└──────────┴────────────────┴─────────────────┴───────────┘
    ↓             ↓                                  ↓
  0x0001      OUI + Type                       OUI + Types
            (00:0F:AC:04)                  (00:0F:AC:04 = CCMP)

┌──────────────┬────────────┐
│ AKM Count    │ AKM Suites │
│ 2 bytes      │ ...        │
└──────────────┴────────────┘
                      ↓
               Authentication methods
           (00:0F:AC:02 = PSK)
           (00:0F:AC:08 = SAE/WPA3)
```

### Cipher Suites

**Group Cipher** (for broadcast/multicast):
- Type 2 (0x02): TKIP
- Type 4 (0x04): CCMP (AES) ← Recommended
- Type 8 (0x08): GCMP (newer, faster)

**Pairwise Cipher** (for unicast):
- Same options as group cipher
- Can have multiple (client chooses best)

### Authentication Methods (AKM)

- **Type 1**: WPA2-Enterprise (802.1X/EAP)
  - User uses RADIUS server authentication
  - Each user has unique credentials
  
- **Type 2**: WPA2-Personal (PSK - Pre-Shared Key)
  - Everyone shares same password
  - Most home networks
  
- **Type 8**: WPA3-SAE (Simultaneous Authentication of Equals)
  - Resistant to offline dictionary attacks
  - Forward secrecy (past sessions safe if key compromised)
  
- **Type 18**: OWE (Opportunistic Wireless Encryption)
  - Encryption without password
  - Like "secure open network"

### How This Project Detects Security

```python
# Parse tag 48 (RSN IE)
if tag_num == 48:
    rsn_info = parse_rsn_ie(tag_data)
    
    # Check AKM suites
    if any('SAE' in method for method in rsn_info['auth_methods']):
        security = "WPA3"
    else:
        security = "WPA2"
    
    # Show ciphers
    ciphers = rsn_info['pairwise_ciphers']  # e.g., ['CCMP (AES)']
    auth = rsn_info['auth_methods']         # e.g., ['WPA2-PSK']
```

---

## Project Data Flow

### Complete Journey of a Beacon

```
1. Access Point broadcasts beacon
   ↓ (radio waves at 2.437 GHz)
   
2. Your WiFi card antenna receives signal
   ↓ (converts to electrical signal)
   
3. WiFi driver processes packet
   ↓ (adds Radiotap metadata)
   
4. Raw socket receives packet
   packet = socket.recvfrom(65535)[0]
   ↓ (raw bytes)
   
5. parse_radiotap(packet)
   → extracts: length=24, signal=-53 dBm
   ↓
   
6. parse_80211(packet, radiotap_len=24)
   → checks: type=0, subtype=8 (BEACON!)
   → extracts: BSSID, timestamp
   ↓
   
7. Parse tagged parameters
   → Tag 0: SSID = "Example Network"
   → Tag 3: channel = 1
   → Tag 48: parse_rsn_ie() → WPA2, AES, PSK
   ↓
   
8. OUI lookup
   → "40:3F:8C" → "Broadcom"
   ↓
   
9. Put in queue
   result_queue.put({
       'type': 'BEACON',
       'ssid': 'Example Network',
       'bssid': '02:00:00:AB:CD:EF',
       'channel': 1,
       'signal': -53,
       'security': 'WPA2',
       'vendor': 'Broadcom',
       'pairwise_ciphers': ['CCMP (AES)'],
       'auth_methods': ['WPA2-PSK']
   })
   ↓
   
10. GUI processes queue (every 100ms)
    → Updates Access Points list
    → Updates Channel Graph
    
You see: Network card in GUI with green WiFi icon!
```

---

## Glossary

**802.11**: IEEE standard for WiFi wireless networks  
**Access Point (AP)**: WiFi router or transmitter  
**Beacon**: Periodic broadcast announcing WiFi network  
**BSSID**: Basic Service Set ID (AP's MAC address)  
**Channel**: Specific frequency range for WiFi communication  
**dBm**: Decibel-milliwatts (signal strength measurement)  
**EM Spectrum**: Range of all electromagnetic radiation frequencies  
**Frequency**: Number of wave cycles per second (Hz)  
**IEEE**: Institute of Electrical and Electronics Engineers  
**MAC Address**: Unique hardware identifier (48 bits)  
**Monitor Mode**: WiFi mode to capture all packets  
**OUI**: Organizationally Unique Identifier (vendor part of MAC)  
**Radiotap**: Header with WiFi metadata (signal, channel, etc.)  
**RSN**: Robust Security Network (WPA2/WPA3 info)  
**SSID**: Service Set Identifier (network name)  
**Wavelength**: Physical length of one wave cycle  

---

**This guide covers the fundamental physics and technology behind WiFi and this project. For implementation details, see the code and comments in `core/parser.py`.**
