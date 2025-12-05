# Parser Improvement Plan

## 🎯 Executive Summary

**Current State:** Parser extracts only **signal strength** from Radiotap (1 of 6+ useful fields)

**Goal:** Extract all valuable Radiotap data while maintaining clean, best-practice code

**Benefit:** Richer analysis, better UI, SNR calculation, actual data rates

---

## 📋 Implementation Plan

### Phase 1: Enhanced Radiotap Parsing (HIGH PRIORITY)

#### 1.1 Return Enhanced RadiotapInfo Object

**Current:**
```python
def parse_radiotap(packet):
    return radiotap_len, signal_strength  # Only 2 values!
```

**Proposed:**
```python
def parse_radiotap(packet):
    return {
        'header_length': radiotap_len,
        'signal': signal_strength,      # dBm
        'noise': noise_level,            # dBm  
        'snr': signal - noise,           # dB
        'rate': data_rate,               # Mbps
        'channel_freq': freq,            # MHz
        'channel_flags': channel_flags,  # 2GHz/5GHz, OFDM/CCK
        'timestamp': tsft,               # microseconds
        'flags': radiotap_flags          # FCS, fragmentation, etc.
    }
```

**Why:** Single cohesive object vs multiple return values. Easier to extend.

#### 1.2 Extract All Valuable Fields

**Fields to Add:**

```python
def parse_radiotap(packet):
    try:
        # ... existing header parsing ...
        
        # Initialize all fields
        result = {
            'header_length': radiotap_len,
            'signal': -100,
            'noise': -100,
            'snr': 0,
            'rate': 0.0,
            'channel_freq': 0,
            'channel_flags': 0,
            'channel_number': 0,
            'tsft': 0,
            'flags': 0,
            'mcs_index': None,
            'guard_interval': None
        }
        
        # Bit 0: TSFT
        if present_0 & 0x1:
            offset = align(offset, 8)
            if offset + 8 <= radiotap_len:
                result['tsft'] = struct.unpack('<Q', packet[offset:offset+8])[0]
            offset += 8
        
        # Bit 1: Flags  
        if present_0 & 0x2:
            offset = align(offset, 1)
            if offset + 1 <= radiotap_len:
                result['flags'] = packet[offset]
            offset += 1
        
        # Bit 2: Rate ⭐ HIGH VALUE
        if present_0 & 0x4:
            offset = align(offset, 1)
            if offset + 1 <= radiotap_len:
                result['rate'] = packet[offset] * 0.5  # Convert to Mbps
            offset += 1
        
        # Bit 3: Channel ⭐ HIGH VALUE
        if present_0 & 0x8:
            offset = align(offset, 2)
            if offset + 4 <= radiotap_len:
                freq, flags = struct.unpack('<HH', packet[offset:offset+4])
                result['channel_freq'] = freq
                result['channel_flags'] = flags
                # Calculate channel number from frequency
                if 2412 <= freq <= 2484:
                    result['channel_number'] = (freq - 2407) // 5
                elif freq == 2484:
                    result['channel_number'] = 14
                elif freq >= 5000:
                    result['channel_number'] = (freq - 5000) // 5
            offset += 4
        
        # Bit 4: FHSS
        if present_0 & 0x10:
            offset = align(offset, 2)
            offset += 2
        
        # Bit 5: Antenna Signal ✅ Already done
        if present_0 & 0x20:
            offset = align(offset, 1)
            if offset + 1 <= radiotap_len:
                result['signal'] = struct.unpack('b', packet[offset:offset+1])[0]
            offset += 1
        
        # Bit 6: Antenna Noise ⭐ NEW - Calculate SNR!
        if present_0 & 0x40:
            offset = align(offset, 1)
            if offset + 1 <= radiotap_len:
                result['noise'] = struct.unpack('b', packet[offset:offset+1])[0]
                result['snr'] = result['signal'] - result['noise']
            offset += 1
        
        # Bit 7: Lock Quality
        if present_0 & 0x80:
            offset = align(offset, 2)
            offset += 2
        
        # Bit 8: TX Attenuation
        if present_0 & 0x100:
            offset = align(offset, 2)
            offset += 2
        
        # Bit 9: dB TX Attenuation
        if present_0 & 0x200:
            offset = align(offset, 2)
            offset += 2
        
        
        # Bit 10: dBm TX Power ⭐ HIGH VALUE - Use for distance calculation!
        if present_0 & 0x400:
            offset = align(offset, 1)
            if offset + 1 <= radiotap_len:
                result['tx_power'] = struct.unpack('b', packet[offset:offset+1])[0]
            offset += 1
        
        # Bit 11: Antenna
        if present_0 & 0x800:
            offset = align(offset, 1)
            if offset + 1 <= radiotap_len:
                result['antenna'] = packet[offset]
            offset += 1

        
        # Bit 12: dB Antenna Signal
        if present_0 & 0x1000:
            offset = align(offset, 1)
            offset += 1
        
        # Bit 13: dB Antenna Noise
        if present_0 & 0x2000:
            offset = align(offset, 1)
            offset += 1
        
        # Bit 19: MCS (802.11n) ⭐ MEDIUM VALUE
        if present_0 & 0x80000:  # Bit 19
            offset = align(offset, 1)
            if offset + 3 <= radiotap_len:
                known = packet[offset]
                flags = packet[offset + 1]
                mcs = packet[offset + 2]
                if known & 0x01:  # MCS index known
                    result['mcs_index'] = mcs
                if known & 0x04:  # Guard interval known
                    result['guard_interval'] = 'short' if flags & 0x04 else 'long'
            offset += 3
        
        # Bit 30: Vendor Namespace ⭐ NEW - Extract OUI for vendor detection!
        if present_0 & 0x40000000:  # Bit 30
            offset = align(offset, 2)
            if offset + 6 <= radiotap_len:
                # Vendor namespace: OUI (3 bytes) + Sub-namespace (1) + Length (2)
                oui = packet[offset:offset+3]
                result['vendor_oui'] = ':'.join(f'{b:02x}' for b in oui)
                # Skip sub-namespace and length, data varies by vendor
            offset += 6  # Minimum vendor namespace size
        
        return result
        
    except Exception as e:
        print(f"Parse Radiotap Error: {e}")
        return {
            'header_length': 0,
            'signal': -100,
            'noise': -100,
            'snr': 0,
            'rate': 0.0,
            'channel_freq': 0,
            'channel_flags': 0,
            'channel_number': 0,
            'tsft': 0,
            'flags': 0
        }
```

---

### Phase 2: Update parse_80211 to Use Radiotap Data

**Current:**
```python
def parse_80211(packet, radiotap_len):
    # Parses beacon, gets channel from tag 3
    channel = 0
    # ... tag parsing ...
    elif tag_num == 3:  # DS Parameter Set
        channel = tag_data[0]
```

**Proposed:**
```python
def parse_80211(packet, radiotap_info):
    """
    Parse 802.11 frame with Radiotap context
    
    Args:
        packet: Raw packet bytes
        radiotap_info: Dict from parse_radiotap()
    """
    radiotap_len = radiotap_info['header_length']
    
    # Prefer Radiotap channel (more reliable)
    channel = radiotap_info.get('channel_number', 0)
    channel_freq = radiotap_info.get('channel_freq', 0)
    
    # ... beacon parsing ...
    
    # Still parse DS Parameter Set as fallback/verification
    elif tag_num == 3:
        beacon_channel = tag_data[0]
        # Use beacon channel only if Radiotap didn't provide it
        if channel == 0:
            channel = beacon_channel
        # Could log if mismatch for debugging
        elif channel != beacon_channel:
            print(f"Channel mismatch: Radiotap={channel}, Beacon={beacon_channel}")
    
    return {
        'type': 'BEACON',
        'ssid': ssid,
        'bssid': bssid_str,
        'channel': channel,
        'channel_freq': channel_freq,  # NEW: Actual frequency
        'signal': radiotap_info['signal'],
        'noise': radiotap_info['noise'],  # NEW
        'snr': radiotap_info['snr'],      # NEW
        'rate': radiotap_info['rate'],    # NEW
        'security': security,
        # ... rest of fields ...
    }
```

---

### Phase 3: Update Calling Code

**In main.py (line 95-101):**

```python
# Current:
radiotap_len, signal = PacketParser.parse_radiotap(raw_data)
beacon_info = PacketParser.parse_80211(raw_data, radiotap_len)
if beacon_info:
    beacon_info['signal'] = signal

# Improved:
radiotap_info = PacketParser.parse_radiotap(raw_data)
if radiotap_info['header_length'] > 0:
    beacon_info = PacketParser.parse_80211(raw_data, radiotap_info)
    if beacon_info:
        result_queue.put(beacon_info)
```

---

### Phase 4: Enhanced UI Display

#### 4.1 Access Points Tab

**Current:**
```
Home Network
CH 3  2422MHz  WPA3
-58 dBm
```

**Enhanced:**
```
Home Network ★★★
CH 3 @ 2422MHz (54 Mbps)  WPA3
-58 dBm (SNR: 42 dB)
```

#### 4.2 Detail Dialog

**Add new fields:**
```python
details = [
    ("SSID:", ssid),
    ("BSSID (MAC):", bssid),
    ("Vendor:", vendor),
    ("", ""),
    
    # Enhanced Channel Section
    ("Channel:", f"{channel} ({channel_freq} MHz)"),
    ("Bandwidth:", f"20 MHz ({start_freq:.0f}-{end_freq:.0f} MHz)"),
    ("Band:", "2.4 GHz"),
    ("", ""),
    
    # NEW: Radio Details
    ("Data Rate:", f"{rate} Mbps"),  # NEW
    ("MCS Index:", f"{mcs}" if mcs else "N/A"),  # NEW for 802.11n
    ("", ""),
    
    # Enhanced Signal Section
    ("Signal Strength:", f"{signal} dBm"),
    ("Noise Floor:", f"{noise} dBm"),  # NEW
    ("SNR:", f"{snr} dB"),  # NEW
    ("Signal Quality:", signal_quality),
    ("Est. Distance:", f"~{distance:.0f}m"),
]
```

#### 4.3 SNR Quality Indicator

```python
def _snr_quality(self, snr_db):
    """Evaluate SNR quality"""
    if snr_db >= 40:
        return "Excellent (40+ dB)"
    elif snr_db >= 25:
        return "Good (25-40 dB)"
    elif snr_db >= 15:
        return "Fair (15-25 dB)"
    elif snr_db >= 10:
        return "Poor (10-15 dB)"
    else:
        return "Very Poor (<10 dB)"
```

---

## 🏗️ Best Practices Implementation

### 1. Clean Data Structure

**Create a dataclass for Radiotap:**

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class RadiotapInfo:
    """Radiotap header parsed information"""
    header_length: int
    signal: int = -100  # dBm
    noise: int = -100   # dBm
    snr: int = 0        # dB
    rate: float = 0.0   # Mbps
    channel_freq: int = 0  # MHz
    channel_number: int = 0
    channel_flags: int = 0
    tsft: int = 0
    flags: int = 0
    tx_power: int = 15  # dBm (default assumption)
    antenna: int = 0
    vendor_oui: Optional[str] = None  # From Radiotap Vendor Namespace
    mcs_index: Optional[int] = None
    guard_interval: Optional[str] = None
    
    @property
    def is_5ghz(self) -> bool:
        """Check if packet is on 5 GHz band"""
        return self.channel_freq >= 5000
    
    @property
    def is_2ghz(self) -> bool:
        """Check if packet is on 2.4 GHz band"""
        return 2400 <= self.channel_freq < 2500
```

### 2. Robust Error Handling

```python
def parse_radiotap(packet):
    """Parse with comprehensive error handling"""
    try:
        if len(packet) < 8:
            return RadiotapInfo(header_length=0)
        
        # Parse header
        radiotap_len = struct.unpack('<H', packet[2:4])[0]
        
        # Validate length
        if radiotap_len > len(packet) or radiotap_len < 8:
            print(f"Invalid Radiotap length: {radiotap_len}")
            return RadiotapInfo(header_length=0)
        
        # ... field extraction with bounds checking ...
        
    except struct.error as e:
        print(f"Struct unpack error in Radiotap: {e}")
        return RadiotapInfo(header_length=0)
    except Exception as e:
        print(f"Radiotap parsing error: {e}")
        return RadiotapInfo(header_length=0)
```

### 3. Unit Tests

```python
# tests/test_parser.py
def test_radiotap_parsing():
    """Test Radiotap parsing with known good packet"""
    # Sample Radiotap header bytes
    packet = bytes([
        0x00, 0x00,  # Version, Pad
        0x1a, 0x00,  # Length: 26 bytes
        0x2f, 0x48, 0x00, 0x00,  # Present flags
        # TSFT (8 bytes)
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        # Flags, Rate
        0x10, 0x6c,
        # Channel
        0x85, 0x09, 0xa0, 0x00,
        # Signal
        0xc2,  # -62 dBm
        # Noise
        0x9b,  # -101 dBm
    ])
    
    info = PacketParser.parse_radiotap(packet)
    assert info.header_length == 26
    assert info.signal == -62
    assert info.noise == -101
    assert info.snr == 39
    assert info.rate == 54.0  # 0x6c * 0.5
    assert info.channel_freq == 2437  # 0x0985
```

---

## 📊 Expected Benefits

### Performance Metrics:

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Radiotap Data Extracted | 20% | 80% | +300% |
| Available Metrics | 1 (signal) | 7+ | +600% |
| Code Clarity | Good | Better | Type safety |
| UI Information Density | Basic | Rich | More useful |

### User Benefits:

1. **SNR Display** - More accurate signal quality assessment
2. **Data Rates** - See actual connection speeds (1-600+ Mbps)
3. **True Channel** - Ground truth from Radiotap vs AP claim
4. **802.11n/ac Info** - MCS index, guard interval
5. **Better Distance** - SNR-adjusted distance estimation

---

## 🔄 Migration Strategy

### Step 1: Add Enhanced Parser (Non-Breaking)
- Create new parse_radiotap_enhanced()
- Keep existing function for compatibility
- Add tests

### Step 2: Update Interface
- Change parse_80211 signature to accept RadiotapInfo
- Update calling code in main.py

### Step 3: UI Enhancements
- Add SNR display
- Add rate display
- Add MCS/VHT indicators

### Step 4: Remove Old Code
- Delete old parse_radiotap once migration complete
- Rename parse_radiotap_enhanced → parse_radiotap

---

## ✅ Implementation Checklist

### Phase 1: Core Parser
- [ ] Create RadiotapInfo dataclass
- [ ] Implement enhanced parse_radiotap()
- [ ] Extract: Rate, Channel, Noise
- [ ] Extract: TSFT, Flags
- [ ] Add MCS parsing (802.11n)
- [ ] Add bounds checking
- [ ] Write unit tests

### Phase 2: Integration
- [ ] Update parse_80211() signature
- [ ] Update main.py packet_handler
- [ ] Prefer Radiotap channel over beacon
- [ ] Calculate and store SNR

### Phase 3: UI Updates
- [ ] Add SNR display to AP cards
- [ ] Add rate display
- [ ] Add SNR to detail dialog
- [ ] Add noise floor display
- [ ] Create SNR quality indicator

### Phase 4: Advanced Features
- [ ] MCS/VHT display for 802.11n/ac
- [ ] Guard interval indicator
- [ ] Channel width detection
- [ ] 5GHz support using Radiotap

---

## 🎯 Priority Recommendation

**Must-Have (Phase 1):**
1. Rate extraction (bit 2)
2. Noise extraction (bit 6) → SNR calculation
3. Channel from Radiotap (bit 3)

**Nice-to-Have (Phase 2):**
4. MCS parsing (bit 19)
5. TSFT for timing analysis
6. Flags for frame properties

**Future Enhancement:**
7. VHT (802.11ac) parsing
8. HE (WiFi 6) parsing
9. FCS validation

---

## 📝 Code Quality Standards

1. **Type Hints**: Use Python type hints for all functions
2. **Docstrings**: Document all extractable fields
3. **Error Handling**: Graceful degradation on parse errors
4. **Logging**: Debug logs for field mismatches
5. **Testing**: Unit tests for each Radiotap field
6. **Comments**: Explain bit positions and formats

---

## 🚀 Ready to Implement!

Start with Phase 1, focusing on Rate, Channel, and Noise extraction.

Would you like me to implement the enhanced Radiotap parser now?
