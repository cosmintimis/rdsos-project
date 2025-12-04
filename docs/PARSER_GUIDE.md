# Parser Implementation Guide

**A comprehensive guide to understanding `core/parser.py` - how WiFi and network packets are parsed from raw bytes.**

---

## Table of Contents

1. [Overview: The Packet Journey](#overview-the-packet-journey)
2. [What Standards We Use](#what-standards-we-use)
3. [Packet Types You'll See](#packet-types-youll-see)
4. [Monitor Mode: Radiotap + 802.11](#monitor-mode-radiotap--80211)
5. [Managed Mode: Ethernet Frames](#managed-mode-ethernet-frames)
6. [IP Layer Parsing](#ip-layer-parsing)
7. [Transport Layer: TCP/UDP/ICMP](#transport-layer-tcpudpicmp)
8. [Application Layer: HTTP](#application-layer-http)
9. [Why "ETH" Packets Without Protocol](#why-eth-packets-without-protocol)
10. [Complete Parsing Flow](#complete-parsing-flow)

---

## Overview: The Packet Journey

When you capture network traffic, you receive **raw bytes** from the network interface. Your job is to **interpret** these bytes according to protocol specifications.

```
Raw Bytes from Network Card:
[00 00 18 00 2e 48 00 00 10 6c 09 a0 ...]
              ↓
        Parse Layer by Layer
              ↓
┌─────────────────────────────────────┐
│ Physical/Link Layer                 │
│ - Radiotap (Monitor) OR Ethernet    │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ Network Layer                       │
│ - IP (v4/v6), ARP, etc.            │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ Transport Layer                     │
│ - TCP, UDP, ICMP                    │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ Application Layer                   │
│ - HTTP, DNS, etc.                   │
└─────────────────────────────────────┘
```

---

## What Standards We Use

Our parser implements these **official standards**:

| Layer | Standard | Reference | Description |
|-------|----------|-----------|-------------|
| **WiFi Metadata** | Radiotap | [radiotap.org](https://www.radiotap.org/) | WiFi capture metadata (signal, channel, rate) |
| **WiFi MAC** | IEEE 802.11 | IEEE Std 802.11-2020 | WiFi frame format (beacons, data) |
| **WiFi Security** | IEEE 802.11i | IEEE Std 802.11i-2004 | WPA2 RSN Information Element |
| **WiFi Security** | IEEE 802.11w | IEEE Std 802.11w-2009 | WPA3 Protected Management Frames |
| **Ethernet** | IEEE 802.3 | IEEE Std 802.3-2018 | Ethernet II frame format |
| **IP** | IPv4 | RFC 791 | Internet Protocol version 4 |
| **TCP** | TCP | RFC 793 | Transmission Control Protocol |
| **UDP** | UDP | RFC 768 | User Datagram Protocol |
| **ICMP** | ICMP | RFC 792 | Internet Control Message Protocol |
| **HTTP** | HTTP/1.1 | RFC 7230-7235 | Hypertext Transfer Protocol |

**Key References:**
- **IEEE 802.11**: WiFi standard (beacons, management frames)
- **RFC 791**: IP header format and addressing
- **RFC 793**: TCP header, flags, connection management
- **RFC 768**: UDP header (simpler than TCP)
- **RFC 792**: ICMP types and codes

---

## Packet Types You'll See

### In **Monitor Mode** (WiFi Analysis):

**Type 1: Management Frames** (`802.11`)
```
What: WiFi control/management
Example: Beacons (network announcements)
Why: Discover WiFi networks, get SSID, channel, security
```

**Type 2: Data Frames with IP** (`TCP`, `UDP`, `ICMP`)
```
What: Actual data transmission
Example: Web browsing, file transfer
Why: Capture network traffic (often encrypted!)
```

### In **Managed Mode** (Connected WiFi / Ethernet):

**Type 1: Ethernet Only** (`ETH`)
```
What: Non-IP protocols
Examples:
  - ARP (Address Resolution Protocol)
  - IPv6 (if you don't parse it)
  - LLDP (Link Layer Discovery)
  - STP (Spanning Tree Protocol)
Why: Many network protocols don't use IP!
```

**Type 2: Ethernet + IP** (`TCP`, `UDP`, `ICMP`)
```
What: Standard internet traffic
Example: HTTP, DNS, ping
Why: Most internet applications use IP
```

---

## Monitor Mode: Radiotap + 802.11

### 1. Radiotap Header

**Standard:** [radiotap.org](https://www.radiotap.org/)  
**Purpose:** Metadata about WiFi capture (NOT part of actual WiFi frame)

**Structure:**
```
┌─────────────────────────────────────┐
│ Byte 0-1: Version (0x00 0x00)      │ Always 0
│ Byte 2-3: Length                    │ Header size (usually 18-36 bytes)
│ Byte 4-7: Present Flags             │ Which fields are present
│ Byte 8+: Field Values               │ Signal strength, channel, etc.
└─────────────────────────────────────┘
```

**What We Parse:**
```python
# From parse_radiotap() in parser.py

# 1. Read header length (bytes 2-3)
radiotap_len = struct.unpack('<H', data[2:4])[0]
# Format: '<H' = little-endian unsigned short (2 bytes)

# 2. Find signal strength (typically at offset 22)
signal = struct.unpack('b', data[22:23])[0]
# Format: 'b' = signed byte (-128 to 127)
# Result: Signal in dBm (e.g., -53 dBm)
```

**Why We Parse It:**
- **Signal Strength**: Shows how strong the WiFi signal is
- **Channel**: Which frequency the packet was captured on
- **Data Rate**: How fast data is transmitted

---

### 2. 802.11 Frame Parsing

**Standard:** IEEE 802.11-2020  
**Purpose:** WiFi MAC layer (addressing, frame types)

**Frame Structure:**
```
┌──────────────────────────────────────┐
│ Frame Control (2 bytes)              │ Type/Subtype of frame
├──────────────────────────────────────┤
│ Duration/ID (2 bytes)                │ Time reserved for transmission
├──────────────────────────────────────┤
│ Address 1 (6 bytes)                  │ Destination MAC
├──────────────────────────────────────┤
│ Address 2 (6 bytes)                  │ Source MAC / BSSID
├──────────────────────────────────────┤
│ Address 3 (6 bytes)                  │ BSSID / Additional address
├──────────────────────────────────────┤
│ Sequence Control (2 bytes)           │ Fragment/sequence number
├──────────────────────────────────────┤
│ Frame Body (variable)                │ Actual data (beacons, etc.)
└──────────────────────────────────────┘
```

**Frame Control Breakdown:**
```python
# Byte 0 of frame (after Radiotap)
fc = frame[0]

# Bits 2-3: Type (0=Management, 1=Control, 2=Data)
type_ = (fc >> 2) & 0x3

# Bits 4-7: Subtype (0x08 for Beacon)
subtype = (fc >> 4) & 0xF

# Example: Beacon Frame
# fc = 0x80 = 10000000 binary
# type_ = (0x80 >> 2) & 0x3 = 0 (Management)
# subtype = (0x80 >> 4) & 0xF = 8 (Beacon)
```

**Reference:**
```
IEEE 802.11-2020, Section 9.2.4.1 (Frame Control field)
Type values:
  0 = Management (beacons, probe requests, authentication)
  1 = Control (ACK, RTS, CTS)
  2 = Data (actual payload)
  
Management Subtypes:
  0x00 = Association Request
  0x04 = Probe Request
  0x08 = Beacon ← What we capture!
  0x0B = Authentication
```

---

### 3. Beacon Frame Parsing

**Purpose:** Extract WiFi network information from beacon broadcasts

**Beacon Body Structure:**
```
┌──────────────────────────────────────┐
│ Timestamp (8 bytes)                  │ Microseconds since AP started
├──────────────────────────────────────┤
│ Beacon Interval (2 bytes)            │ Time between beacons (~100ms)
├──────────────────────────────────────┤
│ Capability Info (2 bytes)            │ Privacy bit, etc.
├──────────────────────────────────────┤
│ Tagged Parameters (variable)         │ SSID, Channel, Security, etc.
└──────────────────────────────────────┘
```

**Tagged Parameters Format:**
```
Each tag:
[Tag Number][Length][Data]
  1 byte     1 byte   'Length' bytes

Examples:
Tag 0:  SSID (network name)
Tag 3:  DS Parameter Set (channel number)
Tag 48: RSN (WPA2/WPA3 security info)
Tag 221: Vendor Specific (WPA, etc.)
```

**Code Example:**
```python
# From parse_80211() in parser.py

# Skip to tagged parameters (after fixed fields)
offset = 36  # 24 (MAC header) + 12 (fixed parameters)

while offset < len(frame) - 2:
    tag_num = frame[offset]
    tag_len = frame[offset + 1]
    tag_data = frame[offset+2 : offset+2+tag_len]
    
    if tag_num == 0:  # SSID
        ssid = tag_data.decode('utf-8', errors='ignore')
    elif tag_num == 3:  # Channel
        channel = tag_data[0]
    elif tag_num == 48:  # RSN
        security_info = parse_rsn_ie(tag_data)
    
    offset += 2 + tag_len  # Move to next tag
```

**Reference:** IEEE 802.11-2020, Section 9.4.2.3 (Beacon frame format)

---

### 4. RSN Information Element (WPA2/WPA3)

**Standard:** IEEE 802.11i-2004 (WPA2), IEEE 802.11w-2009 (WPA3)  
**Purpose:** Encrypted network security details

**Structure:**
```
┌──────────────────────────────────────┐
│ Version (2 bytes)                    │ Usually 0x0001
├──────────────────────────────────────┤
│ Group Cipher Suite (4 bytes)        │ Broadcast/multicast encryption
│   - OUI (3 bytes): 00:0F:AC         │ IEEE OUI
│   - Type (1 byte): 04 = CCMP (AES)  │ Cipher type
├──────────────────────────────────────┤
│ Pairwise Cipher Count (2 bytes)     │ Number of options
├──────────────────────────────────────┤
│ Pairwise Cipher Suites (4*N bytes)  │ Unicast encryption options
├──────────────────────────────────────┤
│ AKM Suite Count (2 bytes)           │ Authentication methods
├──────────────────────────────────────┤
│ AKM Suites (4*N bytes)              │ Auth Key Management
│   - Type 2: WPA2-PSK (password)     │
│   - Type 8: WPA3-SAE                │
└──────────────────────────────────────┘
```

**Cipher Types (IEEE 802.11i):**
```
0x00: Use group cipher
0x01: WEP-40 (BROKEN - don't use!)
0x02: TKIP (weak - WPA)
0x04: CCMP (AES) ← WPA2 standard
0x05: WEP-104 (BROKEN)
0x08: GCMP (newer, faster)
0x09: GCMP-256 (more secure)
```

**AKM Types (Authentication):**
```
0x01: WPA2-Enterprise (802.1X/EAP RADIUS)
0x02: WPA2-PSK (Pre-Shared Key - password)
0x08: WPA3-SAE (Simultaneous Authentication of Equals)
0x12: OWE (Opportunistic Wireless Encryption - no password)
```

**Code Example:**
```python
# From parse_rsn_ie() in parser.py

# Parse group cipher (bytes 2-5)
group_cipher_oui = data[2:5]  # Should be 00:0F:AC
group_cipher_type = data[5]    # 0x04 = CCMP

if group_cipher_type == 4:
    group_cipher = "CCMP (AES)"
elif group_cipher_type == 2:
    group_cipher = "TKIP"

# Parse AKM suites
akm_count = struct.unpack('<H', data[akm_offset:akm_offset+2])[0]
for i in range(akm_count):
    suite = data[akm_offset+2+i*4 : akm_offset+6+i*4]
    akm_type = suite[3]
    
    if akm_type == 2:
        auth_methods.append("WPA2-PSK")
    elif akm_type == 8:
        auth_methods.append("WPA3-SAE")
```

**Reference:** IEEE 802.11i-2004, Section 7.3.2.25 (RSN Information Element)

---

## Managed Mode: Ethernet Frames

**Standard:** IEEE 802.3 (Ethernet II)  
**Purpose:** Wired network or WiFi in managed mode

**Ethernet II Frame:**
```
┌──────────────────────────────────────┐
│ Destination MAC (6 bytes)            │ ff:ff:ff:ff:ff:ff = broadcast
├──────────────────────────────────────┤
│ Source MAC (6 bytes)                 │ Sender's hardware address
├──────────────────────────────────────┤
│ EtherType (2 bytes)                  │ Next protocol identifier
│   0x0800 = IPv4                      │ ← Most common
│   0x0806 = ARP                       │ ← Address resolution
│   0x86DD = IPv6                      │ ← Not parsed yet
│   0x8100 = VLAN tag                  │ ← Virtual LAN
└──────────────────────────────────────┘
```

**EtherType Values (IANA Registry):**
```
0x0800: IPv4 (Internet Protocol)        ← We parse this!
0x0806: ARP (Address Resolution)        ← Seen as "ETH" only
0x86DD: IPv6                             ← Seen as "ETH" only
0x8100: VLAN (802.1Q)                    ← Seen as "ETH" only
0x88CC: LLDP (Link Layer Discovery)     ← Seen as "ETH" only
0x8847: MPLS unicast                     ← Seen as "ETH" only
```

**Why You See "ETH" Packets:**

```python
# From parse_ip_tcp() in parser.py

ethertype = struct.unpack('!H', data[12:14])[0]

if ethertype == 0x0800:  # IPv4
    # Parse IP header → might become TCP/UDP/ICMP
    return parse_ip_layer(...)
else:
    # Not IPv4! Return as "ETH" only
    return {
        'type': 'ETH',
        'src_mac': format_mac(data[6:12]),
        'dst_mac': format_mac(data[0:6]),
        'ethertype': f'0x{ethertype:04x}',
        'ethertype_name': get_ethertype_name(ethertype)
    }
```

**Common "ETH Only" Packets You'll See:**

1. **ARP (0x0806)** - Address Resolution Protocol
   ```
   Purpose: Maps IP addresses to MAC addresses
   Example: "Who has 192.168.1.1? Tell 192.168.1.100"
   Why: Needed before sending IP packets on local network
   ```

2. **IPv6 (0x86DD)** - Internet Protocol version 6
   ```
   Purpose: Next-generation IP addressing
   Example: Modern networks use both IPv4 and IPv6
   Why: Not implemented in your parser yet
   ```

3. **LLDP (0x88CC)** - Link Layer Discovery Protocol
   ```
   Purpose: Device discovery on local network
   Example: Switches announcing their capabilities
   Why: Network management, not internet traffic
   ```

**Reference:** [IANA EtherType Registry](https://www.iana.org/assignments/ieee-802-numbers/)

---

## IP Layer Parsing

**Standard:** RFC 791 (IPv4)  
**Purpose:** Route packets across networks

**IPv4 Header (20 bytes minimum):**
```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
┌───────┬───────┬───────────────┬───────────────────────────────┐
│Version│  IHL  │   DSCP  │ ECN │        Total Length           │
│ (4)   │ (4)   │  (6)    │ (2) │         (16 bits)             │
├───────────────────────────────┼───────────────────────────────┤
│        Identification         │Flags│   Fragment Offset       │
│          (16 bits)            │ (3) │      (13 bits)          │
├───────────────┬───────────────┼───────────────────────────────┤
│      TTL      │   Protocol    │      Header Checksum          │
│   (8 bits)    │   (8 bits)    │         (16 bits)             │
├───────────────┴───────────────┼───────────────────────────────┤
│                    Source IP Address (32 bits)                │
├───────────────────────────────────────────────────────────────┤
│                 Destination IP Address (32 bits)              │
└───────────────────────────────────────────────────────────────┘
```

**Field-by-Field Parsing:**

```python
# From parse_ip_tcp() in parser.py

# Byte 0: Version + IHL
version_ihl = ip_header[0]
version = version_ihl >> 4        # Upper 4 bits
ihl = version_ihl & 0x0F          # Lower 4 bits
header_length = ihl * 4            # IHL in 32-bit words

# Byte 1: DSCP + ECN
tos = ip_header[1]
dscp = tos >> 2                    # Upper 6 bits
ecn = tos & 0x3                    # Lower 2 bits

# Bytes 2-3: Total Length
total_length = struct.unpack('!H', ip_header[2:4])[0]
# '!' = network byte order (big-endian)
# 'H' = unsigned short (2 bytes)

# Byte 8: Time To Live
ttl = ip_header[8]

# Byte 9: Protocol
protocol = ip_header[9]
# 1 = ICMP, 6 = TCP, 17 = UDP

# Bytes 12-15: Source IP
src_ip = socket.inet_ntoa(ip_header[12:16])
# Converts bytes to "192.168.1.1" format

# Bytes 16-19: Destination IP
dst_ip = socket.inet_ntoa(ip_header[16:20])
```

**Protocol Field Values (IANA):**
```
1   = ICMP (Internet Control Message Protocol)
6   = TCP (Transmission Control Protocol)
17  = UDP (User Datagram Protocol)
41  = IPv6 encapsulation
47  = GRE (Generic Routing Encapsulation)
50  = ESP (Encapsulating Security Payload - IPsec)
```

**Reference:** RFC 791, Section 3.1 (Internet Header Format)

---

## Transport Layer: TCP/UDP/ICMP

### 1. TCP (Transmission Control Protocol)

**Standard:** RFC 793  
**Purpose:** Reliable, ordered data delivery

**TCP Header:**
```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
┌───────────────────────────────┬───────────────────────────────┐
│        Source Port            │       Destination Port        │
├───────────────────────────────┴───────────────────────────────┤
│                      Sequence Number                          │
├───────────────────────────────────────────────────────────────┤
│                   Acknowledgment Number                       │
├───────┬───┬───┬───────────────┬───────────────────────────────┤
│ Data  │Res│Flg│               │      Window Size              │
│Offset │   │ags│               │                               │
├───────┴───┴───┴───────────────┼───────────────────────────────┤
│          Checksum             │       Urgent Pointer          │
└───────────────────────────────┴───────────────────────────────┘
```

**TCP Flags (Byte 13):**
```
Bit 0: FIN (Finish - close connection)
Bit 1: SYN (Synchronize - start connection)
Bit 2: RST (Reset - abort connection)
Bit 3: PSH (Push - send immediately)
Bit 4: ACK (Acknowledgment)
Bit 5: URG (Urgent)
Bit 6: ECE (ECN Echo)
Bit 7: CWR (Congestion Window Reduced)
```

**Parsing Code:**
```python
# Bytes 0-1: Source Port
src_port = struct.unpack('!H', tcp_header[0:2])[0]

# Bytes 2-3: Destination Port
dst_port = struct.unpack('!H', tcp_header[2:4])[0]

# Bytes 4-7: Sequence Number
seq_num = struct.unpack('!I', tcp_header[4:8])[0]
# 'I' = unsigned int (4 bytes)

# Byte 12: Data Offset + Reserved + Flags
data_offset = (tcp_header[12] >> 4) & 0xF
tcp_header_length = data_offset * 4

# Byte 13: Flags
tcp_flags = tcp_header[13]
flags = {
    'FIN': bool(tcp_flags & 0x01),
    'SYN': bool(tcp_flags & 0x02),
    'RST': bool(tcp_flags & 0x04),
    'PSH': bool(tcp_flags & 0x08),
    'ACK': bool(tcp_flags & 0x10),
    'URG': bool(tcp_flags & 0x20),
}
flags_str = ''.join(k for k, v in flags.items() if v)
# Example: "SYN,ACK" or "PSH,ACK"
```

**Common Port Numbers:**
```
20/21: FTP (File Transfer)
22:    SSH (Secure Shell)
23:    Telnet
25:    SMTP (Email)
53:    DNS (Domain Name System)
80:    HTTP (Web) ← We parse this!
443:   HTTPS (Secure Web)
```

**Reference:** RFC 793, Section 3.1 (TCP Header Format)

---

### 2. UDP (User Datagram Protocol)

**Standard:** RFC 768  
**Purpose:** Fast, connectionless data delivery

**UDP Header (Only 8 bytes!):**
```
┌───────────────────────────────┬───────────────────────────────┐
│        Source Port            │       Destination Port        │
├───────────────────────────────┼───────────────────────────────┤
│          Length               │           Checksum            │
└───────────────────────────────┴───────────────────────────────┘
```

**Parsing Code:**
```python
# Much simpler than TCP!
src_port = struct.unpack('!H', udp_header[0:2])[0]
dst_port = struct.unpack('!H', udp_header[2:4])[0]
length = struct.unpack('!H', udp_header[4:6])[0]
checksum = struct.unpack('!H', udp_header[6:8])[0]
```

**Common UDP Services:**
```
53:   DNS (Domain Name System)
67/68: DHCP (IP address assignment)
123:  NTP (Network Time Protocol)
161:  SNMP (Network Management)
514:  Syslog (System Logging)
1900: SSDP (Service Discovery)
```

**Reference:** RFC 768 (User Datagram Protocol)

---

### 3. ICMP (Internet Control Message Protocol)

**Standard:** RFC 792  
**Purpose:** Network diagnostics and error reporting

**ICMP Header:**
```
┌───────────────┬───────────────┬───────────────────────────────┐
│     Type      │     Code      │          Checksum             │
│   (8 bits)    │   (8 bits)    │         (16 bits)             │
├───────────────┴───────────────┼───────────────────────────────┤
│ Rest of Header (varies by type - 4 bytes)                     │
└───────────────────────────────────────────────────────────────┘
```

**Common ICMP Types:**
```
Type 0: Echo Reply (ping response)
Type 3: Destination Unreachable
Type 8: Echo Request (ping) ← We detect this!
Type 11: Time Exceeded (traceroute)
```

**Echo Request/Reply Structure:**
```
For Type 0 (Reply) and Type 8 (Request):
┌───────────────┬───────────────┐
│  Identifier   │   Sequence    │
│   (2 bytes)   │   (2 bytes)   │
└───────────────┴───────────────┘
```

**Parsing Code:**
```python
icmp_type = icmp_header[0]
icmp_code = icmp_header[1]
checksum = struct.unpack('!H', icmp_header[2:4])[0]

if icmp_type == 8:  # Echo Request
    identifier = struct.unpack('!H', icmp_header[4:6])[0]
    sequence = struct.unpack('!H', icmp_header[6:8])[0]
    type_name = "Echo Request (ping)"
elif icmp_type == 0:  # Echo Reply
    type_name = "Echo Reply (ping response)"
```

**Reference:** RFC 792 (Internet Control Message Protocol)

---

## Application Layer: HTTP

**Standard:** RFC 7230-7235 (HTTP/1.1)  
**Purpose:** Web page transfer

**HTTP Request Format:**
```
GET /index.html HTTP/1.1\r\n
Host: www.example.com\r\n
User-Agent: Mozilla/5.0\r\n
Accept: text/html\r\n
\r\n
[optional body]
```

**HTTP Response Format:**
```
HTTP/1.1 200 OK\r\n
Content-Type: text/html\r\n
Content-Length: 1234\r\n
\r\n
<html>...</html>
```

**Parsing Code:**
```python
# Detect HTTP on port 80
if src_port == 80 or dst_port == 80:
    text = payload.decode('ascii', errors='ignore')
    lines = text.split('\r\n')
    first_line = lines[0]
    
    # HTTP Request: starts with method
    if first_line.startswith('GET '):
        parts = first_line.split(' ')
        method = parts[0]  # GET
        path = parts[1]    # /index.html
        version = parts[2] # HTTP/1.1
        
    # HTTP Response: starts with HTTP/
    elif first_line.startswith('HTTP/'):
        parts = first_line.split(' ', 2)
        version = parts[0]      # HTTP/1.1
        status_code = parts[1]   # 200
        status_text = parts[2]   # OK
```

**Common HTTP Methods:**
```
GET:    Retrieve resource
POST:   Submit data
PUT:    Update resource
DELETE: Remove resource
HEAD:   Get headers only
```

**Reference:** RFC 7230, Section 3 (Message Format)

---

## Why "ETH" Packets Without Protocol

### Understanding the Layers

```
Scenario 1: Complete Stack (HTTP over TCP)
┌─────────────┐
│   HTTP      │ Type: "TCP" with 'http' data
├─────────────┤
│   TCP       │
├─────────────┤
│   IP        │
├─────────────┤
│  Ethernet   │
└─────────────┘

Scenario 2: Just IP (Ping)
┌─────────────┐
│   ICMP      │ Type: "ICMP"
├─────────────┤
│   IP        │
├─────────────┤
│  Ethernet   │
└─────────────┘

Scenario 3: Non-IP Protocol (ARP)
┌─────────────┐
│   ARP       │ Type: "ETH" only!
├─────────────┤
│  Ethernet   │
└─────────────┘
```

### ARP Example (Most Common "ETH" Packet)

**Purpose:** Map IP addresses to MAC addresses

**ARP Packet:**
```
Ethernet Header:
  Dst MAC: FF:FF:FF:FF:FF:FF (broadcast)
  Src MAC: AA:BB:CC:DD:EE:FF
  EtherType: 0x0806 (ARP)

ARP Payload:
  Operation: Request (1)
  Sender MAC: AA:BB:CC:DD:EE:FF
  Sender IP: 192.168.1.100
  Target MAC: 00:00:00:00:00:00 (unknown)
  Target IP: 192.168.1.1
  
Question: "Who has 192.168.1.1? Tell 192.168.1.100"
```

**Why It's Important:**
```
Before sending IP packet to 192.168.1.1:
1. Computer sends ARP request ← You see this as "ETH"
2. Router responds with its MAC ← You see this as "ETH"
3. Now computer can send IP packet ← You see this as "TCP"/"UDP"
```

### Other Non-IP Protocols You'll See:

1. **IPv6 (0x86DD)**
   - Next-generation IP
   - Seen if you haven't implemented IPv6 parsing

2. **VLAN Tags (0x8100)**
   - Virtual LAN separation
   - Common in enterprise networks

3. **LLDP (0x88CC)**
   - Device discovery
   - Switches/routers announce themselves

4. **STP (Spanning Tree Protocol)**
   - Prevents network loops
   - Bridge Protocol Data Units (BPDUs)

---

## Complete Parsing Flow

```python
def PacketParser.parse_packet(packet_bytes, managed_mode):
    """
    Entry point for packet parsing
    """
    
    if managed_mode:
        # Managed Mode: Ethernet frame
        # ┌─────────────┐
        # │  Ethernet   │ ← Start here
        # └─────────────┘
        return parse_ip_tcp(packet_bytes)
    else:
        # Monitor Mode: Radiotap + 802.11
        # ┌─────────────┐
        # │  Radiotap   │ ← Start here
        # ├─────────────┤
        # │   802.11    │
        # └──────────────┘
        
        # Step 1: Parse Radiotap (metadata)
        radiotap_len, signal = parse_radiotap(packet_bytes)
        
        # Step 2: Parse 802.11 frame
        frame = packet_bytes[radiotap_len:]
        result = parse_80211(frame, signal, radiotap_len)
        
        if result['type'] == 'BEACON':
            # Beacon frame → for WiFi analysis
            return result
        elif result['type'] == '802.11':
            # Data frame → might have IP inside
            # Try to parse as Ethernet/IP
            data = result.get('data', b'')
            return parse_ip_tcp(data)
```

**Decision Tree:**
```
Raw Packet
    │
    ├─ Managed Mode?
    │   └─ YES → parse_ip_tcp()
    │            ├─ EtherType 0x0800? → Parse IP
    │            │   ├─ Protocol 6? → Parse TCP
    │            │   │   └─ Port 80? → Parse HTTP
    │            │   ├─ Protocol 17? → Parse UDP
    │            │   └─ Protocol 1? → Parse ICMP
    │            └─ Other EtherType → Return "ETH"
    │
    └─ NO (Monitor Mode) → parse_radiotap() + parse_80211()
                            ├─ Beacon? → Return WiFi info
                            └─ Data? → parse_ip_tcp()
```

---

## Summary: What Gets Parsed

| Layer | What | Standard | Result Type |
|-------|------|----------|-------------|
| **Physical/Link** | Radiotap | [radiotap.org](https://www.radiotap.org/) | Signal strength |
| **MAC (WiFi)** | 802.11 Beacon | IEEE 802.11-2020 | `BEACON` |
| **MAC (WiFi)** | 802.11 Data | IEEE 802.11-2020 | `802.11` → further parsed |
| **MAC (Wired)** | Ethernet | IEEE 802.3 | Proceed to Network layer |
| **Network** | ARP | RFC 826 | `ETH` (not implemented) |
| **Network** | IPv4 | RFC 791 | Proceed to Transport layer |
| **Network** | IPv6 | RFC 8200 | `ETH` (not implemented) |
| **Transport** | TCP | RFC 793 | `TCP` |
| **Transport** | UDP | RFC 768 | `UDP` |
| **Transport** | ICMP | RFC 792 | `ICMP` |
| **Application** | HTTP | RFC 7230 | `TCP` with `http` field |

---

## References & Further Reading

**Official Standards:**
- [IEEE 802.11-2020](https://standards.ieee.org/standard/802_11-2020.html) - WiFi MAC and PHY
- [RFC 791 - IP](https://www.rfc-editor.org/rfc/rfc791) - Internet Protocol
- [RFC 793 - TCP](https://www.rfc-editor.org/rfc/rfc793) - Transmission Control Protocol
- [RFC 768 - UDP](https://www.rfc-editor.org/rfc/rfc768) - User Datagram Protocol
- [RFC 792 - ICMP](https://www.rfc-editor.org/rfc/rfc792) - Internet Control Message Protocol
- [RFC 7230 - HTTP/1.1](https://www.rfc-editor.org/rfc/rfc7230) - Message Syntax and Routing

**Online Resources:**
- [Radiotap.org](https://www.radiotap.org/) - Radiotap specification
- [IANA Protocols](https://www.iana.org/protocols) - Official protocol numbers
- [Wireshark Wiki](https://wiki.wireshark.org/) - Packet analysis examples
- [IEEE Registration Authority](https://standards.ieee.org/products-programs/regauth/) - OUI database

**Tools for Comparison:**
- **Wireshark** - Compare your parsing with professional tool
- **tcpdump** - Command-line packet analyzer
- **tshark** - Wireshark's CLI version

---

**This guide explains every aspect of `core/parser.py` from raw bytes to application data. Each parsing decision follows official standards and specifications!** 📡
