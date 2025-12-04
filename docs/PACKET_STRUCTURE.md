# WiFi Raw Packet Structure Deep Dive

## 📦 Complete Packet Structure in Monitor Mode

When capturing WiFi packets in monitor mode, each packet has this structure:

```
┌─────────────────────────────────────────────────────────────┐
│  [Radiotap Header] - Capture metadata (variable length)     │
├─────────────────────────────────────────────────────────────┤
│  [802.11 MAC Header] - WiFi frame control & addresses (24+) │
├─────────────────────────────────────────────────────────────┤
│  [Frame Body] - Management/Control/Data payload (variable)  │
├─────────────────────────────────────────────────────────────┤
│  [FCS] - Frame Check Sequence (4 bytes) [Often stripped]    │
└─────────────────────────────────────────────────────────────┘
```

### Is This All a Packet Contains?

**Yes, but with important details:**

1. **In Monitor Mode**: You get ALL four parts (though FCS is often stripped by the driver)
2. **In Managed Mode**: You get **Ethernet header** instead of Radiotap + 802.11 header
3. **The data varies**: Frame Body content depends on frame type (Management/Control/Data)

---

## 1. 📡 Radiotap Header (Monitor Mode Only)

### Purpose
Radiotap is **NOT part of the actual WiFi frame**. It's **metadata added by your WiFi driver** about the capture conditions.

### Structure
```
 0               1               2               3
 0 1 2 3 4 5 6 7 0 1 2 3 4 5 6 7 0 1 2 3 4 5 6 7 0 1 2 3 4 5 6 7
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  Version (0)  |    Pad (0)    |        Length (little endian) |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                   Present Flags (bitmap)                      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                   ... Variable fields ...                     |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### Present Flags Bitmap

Each bit indicates if a field is present:

| Bit | Field | Size | Alignment | Your Code |
|-----|-------|------|-----------|-----------|
| 0 | TSFT (timestamp) | 8 bytes | 8 | ❌ Skipped |
| 1 | Flags | 1 byte | 1 | ❌ Skipped |
| 2 | **Rate** | 1 byte | 1 | ❌ **Skipped (should use!)** |
| 3 | **Channel** | 4 bytes | 2 | ❌ **Skipped (available!)** |
| 4 | FHSS | 2 bytes | 2 | ❌ Skipped |
| 5 | **Antenna Signal** | 1 byte | 1 | ✅ **EXTRACTED** |
| 6 | **Antenna Noise** | 1 byte | 1 | ❌ **Not checked (useful!)** |
| 7 | Lock Quality | 2 bytes | 2 | ❌ Not checked |
| 10 | dBm TX Power | 1 byte | 1 | ❌ Not checked |
| 19 | MCS (802.11n) | 3 bytes | 1 | ❌ Not checked |
| 21 | VHT (802.11ac) | 12 bytes | 2 | ❌ Not checked |
| 23 | HE (802.11ax/WiFi 6) | variable | 2 | ❌ Not checked |

### What You Currently Extract from Radiotap:
```python
# Line 70-76 in parser.py
if present_0 & 0x20:  # Bit 5: Antenna Signal
    signal_strength = struct.unpack('b', packet[offset:offset+1])[0]
```

**Only extracting:** Signal Strength (-100 to 0 dBm)

### What You're Missing from Radiotap:

**High Value Fields:**

1. **Rate (bit 2)** - Connection speed in 500 kbps units
   ```python
   # Currently at line 56-58: just skipping
   if present_0 & 0x4:
       offset += 1  # WASTED!
   
   # Could be:
   if present_0 & 0x4:
       rate = packet[offset] * 0.5  # Mbps (e.g., 54 Mbps)
       offset += 1
   ```

2. **Channel (bit 3)** - Frequency & channel flags
   ```python
   # Currently at line 61-63: just skipping
   if present_0 & 0x8:
       offset += 4  # WASTED!
   
   # Could be:
   if present_0 & 0x8:
       freq, flags = struct.unpack('<HH', packet[offset:offset+4])
       # freq = 2437 (channel 6)
       # flags = 0x00a0 (2GHz, OFDM)
       offset += 4
   ```

3. **Antenna Noise (bit 6)** - Calculate SNR!
   ```python
   # Not currently checked at all!
   if present_0 & 0x40:  # Bit 6
       noise = struct.unpack('b', packet[offset:offset+1])[0]
       snr = signal - noise  # Signal-to-Noise Ratio
       offset += 1
   ```

---

## 2. 📻 802.11 MAC Header

### Structure (24 bytes minimum)
```
 0               1               2               3
 0 1 2 3 4 5 6 7 0 1 2 3 4 5 6 7 0 1 2 3 4 5 6 7 0 1 2 3 4 5 6 7
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  Frame Control (2) | Duration/ID (2) |   Address 1 (6 bytes)  →
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
→  Address 1 cont.  |          Address 2 (6 bytes)              →
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
→  Address 2 cont.  |          Address 3 (6 bytes)              →
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
→  Address 3 cont.  | Sequence Control (2) |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### Frame Control Field (2 bytes)
```
Bits 0-1:   Version (always 0)
Bits 2-3:   Type (0=Mgmt, 1=Control, 2=Data)
Bits 4-7:   Subtype (e.g., 8=Beacon for Management)
Bit  8:     To DS
Bit  9:     From DS
Bit  10:    More Fragments
Bit  11:    Retry
Bit  12:    Power Management
Bit  13:    More Data
Bit  14:    Protected Frame (WEP/WPA)
Bit  15:    Order
```

### What You Currently Extract from 802.11 Header:

**From Frame Control (line 203-206):**
```python
fc = frame[0]
type_ = (fc >> 2) & 0x3      # Type field
subtype = (fc >> 4) & 0xF    # Subtype field
# Only checking if type=0, subtype=8 (beacon)
```

**From Address Fields (line 210):**
```python
bssid = frame[16:22]  # Address 3 = BSSID for beacons
```

---

## 3. 📄 Frame Body (Variable Length)

### For Beacon Frames (what you parse):
```
┌─────────────────────────────────────┐
│  Fixed Parameters (12 bytes)        │
│  - Timestamp (8)                    │
│  - Beacon Interval (2)              │
│  - Capability Info (2)              │
├─────────────────────────────────────┤
│  Tagged Parameters (variable)       │
│  - SSID (tag 0)                     │
│  - Supported Rates (tag 1)          │
│  - DS Parameter Set / Channel (tag 3) │
│  - RSN (WPA2/WPA3) (tag 48)         │
│  - Vendor Specific / WPA (tag 221)  │
│  - ... many others ...              │
└─────────────────────────────────────┘
```

### What You Currently Extract from Frame Body:

**Tags you parse (line 222-254):**
```python
tag_num == 0:   SSID             ✅ Extracted
tag_num == 3:   Channel          ✅ Extracted  
tag_num == 48:  RSN (WPA2/WPA3)  ✅ Extracted (detailed!)
tag_num == 221: Vendor (WPA)     ✅ Extracted
```

**Capability Info (line 257-259):**
```python
cap_info = struct.unpack('<H', frame[34:36])[0]
if cap_info & 0x0010:  # Privacy bit
    security = "WEP"  # If no WPA
```

---

## 4. 🔒 FCS (Frame Check Sequence)

### What is it?
- **4-byte CRC32 checksum** at the end of every WiFi frame
- Used to detect transmission errors
- **Often stripped by WiFi drivers** before you see the packet

### In Your Code:
- ❌ **Not parsed** (and usually not even present in captured packets)
- Most drivers don't include FCS in monitor mode captures
- Can be enabled with `iw` commands if needed

---

## 🔄 Radiotap vs 802.11: Which is Better?

### The Critical Question: Should You Prefer Radiotap Data?

| Field | Radiotap Source | 802.11 Source | Which is Better? |
|-------|----------------|---------------|------------------|
| **Signal Strength** | ✅ Bit 5: Antenna Signal | ❌ Not in 802.11 | ✅ **Radiotap ONLY** |
| **Channel** | ✅ Bit 3: Channel (freq+flags) | ✅ Tag 3: DS Parameter | ⚠️ **Different purposes!** |
| **Data Rate** | ✅ Bit 2: Rate | ❌ Not in beacon | ✅ **Radiotap ONLY** |
| **Noise Level** | ✅ Bit 6: Noise | ❌ Not in 802.11 | ✅ **Radiotap ONLY** |
| **SSID** | ❌ N/A | ✅ Tag 0 | ✅ **802.11 ONLY** |
| **Security** | ❌ N/A | ✅ Tag 48/221 | ✅ **802.11 ONLY** |
| **BSSID** | ❌ N/A | ✅ Address 3 | ✅ **802.11 ONLY** |

### The Answer: **USE BOTH!**

**Radiotap** tells you about the **physical layer** (how the packet was received):
- Signal strength
- Noise level  
- Data rate
- Channel frequency
- Radio properties

**802.11 Frame** tells you about the **network** (what the AP is broadcasting):
- Network name (SSID)
- Security settings
- Supported rates
- Capabilities
- Channel assignment

### Current vs Optimal Strategy:

| Data Point | Current Source | Optimal Source | Why |
|------------|----------------|----------------|-----|
| **Signal** | ✅ Radiotap | ✅ Radiotap | Only source |
| **Channel** | ❌ 802.11 Tag 3 | ✅ **Radiotap bit 3** | More reliable! |
| **Rate** | ❌ Not extracted | ✅ **Radiotap bit 2** | Shows actual speed |
| **Noise** | ❌ Not extracted | ✅ **Radiotap bit 6** | Calculate SNR |
| **SSID** | ✅ 802.11 Tag 0 | ✅ 802.11 Tag 0 | Only source |
| **Security** | ✅ 802.11 Tag 48 | ✅ 802.11 Tag 48 | Only source |

---

## 💡 Key Insights:

### Why Radiotap Channel > 802.11 Tag 3:

**802.11 DS Parameter (Tag 3):**
- Tells you which channel **the AP says it's on**
- Part of the management frame body
- Can be misleading if AP is misconfigured

**Radiotap Channel (bit 3):**
- Tells you which channel **your adapter actually received the packet on**
- Includes flags (2GHz/5GHz, CCK/OFDM, etc.)
- **More trustworthy** - it's what actually happened, not what AP claims

### Example Radiotap Channel Value:

In your current parser you skip this (line 61-63):
```python
if present_0 & 0x8:  # Channel present
    offset = align(offset, 2)
    freq, flags = struct.unpack('<HH', packet[offset:offset+4])
    # freq = 2437 (MHz)
    # flags = 0x00a0
    #   - 0x0080 = 2 GHz spectrum
    #   - 0x0020 = OFDM modulation
    offset += 4
```

This gives you:
- Exact frequency (2437 MHz)
- Band (2.4 GHz vs 5 GHz)
- Modulation (OFDM, CCK, etc.)
- Much richer than just "channel 6"

---

## 🎯 Verdict: Your Intuition is CORRECT!

> **"I'm thinking that radiotap information if exists is more useful than beacon frame"**

**Partially correct:**

✅ **For physical layer data** (signal, rate, noise, actual channel): **Radiotap is better**
✅ **Radiotap is ground truth** - it's what actually happened
✅ **You should extract more from Radiotap** - you're wasting valuable data

❌ **For network data** (SSID, security, capabilities): **Beacon frame is only source**

### The Best Approach:

**Extract BOTH and use each for what it's best at:**

1. **Radiotap** → Physical layer metrics
   - Signal strength ✅ (already doing)
   - **Noise level** (should add)
   - **Data rate** (should add)
   - **Actual channel frequency** (should add)

2. **802.11 Beacon** → Network information
   - SSID ✅ (already doing)
   - Security ✅ (already doing)
   - BSSID ✅ (already doing)

---

## 📊 Current Parser Analysis Summary

### What You're Doing Well:
✅ Correct Radiotap header length calculation  
✅ Proper alignment handling
✅ Detailed RSN/WPA parsing
✅ Clean separation of concerns

### What You're Missing:
❌ **Rate** - Skipping valuable speed data (line 56-58)
❌ **Radiotap Channel** - More reliable than beacon tag (line 61-63)
❌ **Noise** - Not checking bit 6 at all
❌ **MCS/VHT/HE** - Not checking 802.11n/ac/ax details

### Parser Efficiency:
- Currently: **~20% of Radiotap** data extracted
- Potential: **~80% useful data** available

---

## Next Step:
See the **Parser Improvement Plan** document for detailed implementation strategy.
