# Protocol IDs
ETH_P_ALL = 0x0003

# 802.11 Frame Controls
# Frame Control is 2 bytes.
# Type is bits 2-3 (0=Mgmt, 1=Control, 2=Data)
# Subtype is bits 4-7

# Management Frame Types (Type=0)
FC_TYPE_MGMT = 0
FC_SUBTYPE_BEACON = 8

# Data Frame Types (Type=2)
FC_TYPE_DATA = 2

# Radiotap Offsets (Common)
# Note: These can vary based on the Radiotap header length and present flags.
# We will need to parse the present flags dynamically, but for now we define some common constants.
# The header length is always at byte 2 (2 bytes).

# 802.11 Header Offsets
# Frame Control: 0-1
# Duration: 2-3
# Address 1 (Receiver): 4-9
# Address 2 (Transmitter/Source): 10-15
# Address 3 (BSSID/Filtering): 16-21
# Sequence Control: 22-23

def get_signal_color(signal):
    """
    Get color based on 7-tier signal strength classification
    Following industry standard WiFi signal quality guidelines
    
    Signal ranges:
    - Perfect (-30 and above): Bright Green - Maximum performance
    - Excellent (-50 to -30): Lime Green - All applications  
    - Good (-60 to -50): Yellow - Reliable for all uses
    - Fair (-67 to -60): Gold - Voice & non-HD video minimum
    - Light (-70 to -67): Orange - Light browsing, email
    - Weak (-80 to -70): Red-Orange - Unstable connection
    - Poor (below -80): Red - Unlikely to connect
    """
    if signal >= -30:
        return "#00FF00"  # Bright Green - Perfect
    elif signal >= -50:
        return "#7FFF00"  # Lime Green - Excellent  
    elif signal >= -60:
        return "#FFFF00"  # Yellow - Good
    elif signal >= -67:
        return "#FFD700"  # Gold - Fair
    elif signal >= -70:
        return "#FFA500"  # Orange - Light
    elif signal >= -80:
        return "#FF6347"  # Tomato/Red-Orange - Weak
    else:
        return "#FF0000"  # Red - Poor

def get_frequency(channel):
    """Calculates frequency in MHz for a given channel (2.4GHz)."""
    if 1 <= channel <= 13:
        return 2407 + (channel * 5)
    elif channel == 14:
        return 2484
    return 0
