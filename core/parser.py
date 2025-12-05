import struct
import socket
from utils.constants import *
from utils.oui import get_vendor

# Monitor mode: Radiotap + 802.11 Header + Payload + FCS
# Managed mode: Ethernet Header + Payload

class PacketParser:
    @staticmethod
    def parse_radiotap(packet):
        """
        Enhanced Radiotap parser - extracts comprehensive physical layer metrics.
        
        Returns dict with:
            header_length, signal, noise, snr, rate, channel_freq, channel_number,
            tx_power, vendor_oui, and more
        """
        try:
            # Radiotap Header: Version(1), Pad(1), Len(2), Present(4)
            if len(packet) < 8:
                return {'header_length': 0, 'signal': -100}
            
            radiotap_len = struct.unpack('<H', packet[2:4])[0]
            present_0 = struct.unpack('<I', packet[4:8])[0]
            
            # Validate length
            if radiotap_len > len(packet) or radiotap_len < 8:
                print(f"Invalid Radiotap length: {radiotap_len}")
                return {'header_length': 0, 'signal': -100}
            
            # Check if another present word exists (bit 31)
            offset = 8
            current_present = present_0
            while current_present & 0x80000000:
                if offset + 4 > len(packet):
                    break
                current_present = struct.unpack('<I', packet[offset:offset+4])[0]
                offset += 4
            
            # Helper to align offset
            def align(off, alignment):
                if off % alignment != 0:
                    return off + (alignment - (off % alignment))
                return off
            
            # Initialize result with defaults
            result = {
                'header_length': radiotap_len,
                'signal': -100,
                'noise': -100,
                'snr': 0,
                'rate': 0.0,
                'channel_freq': 0,
                'channel_number': 0,
                'channel_flags': 0,
                'tx_power': None,
                'vendor_oui': None,
                'tsft': 0,
                'flags': 0
            }
            
            # Bit 0: TSFT (timestamp)
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
            
            # Bit 2: Rate
            if present_0 & 0x4:
                offset = align(offset, 1)
                if offset + 1 <= radiotap_len:
                    result['rate'] = packet[offset] * 0.5  # 500 kbps units → Mbps
                offset += 1
            
            # Bit 3: Channel
            if present_0 & 0x8:
                offset = align(offset, 2)
                if offset + 4 <= radiotap_len:
                    freq, flags = struct.unpack('<HH', packet[offset:offset+4])
                    result['channel_freq'] = freq
                    result['channel_flags'] = flags
                    # Calculate channel number from frequency
                    if 2412 <= freq <= 2472:
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
            
            # Bit 5: Antenna Signal 
            if present_0 & 0x20:
                offset = align(offset, 1)
                if offset + 1 <= radiotap_len:
                    result['signal'] = struct.unpack('b', packet[offset:offset+1])[0]
                offset += 1
            
            # Bit 6: Antenna Noise
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
            
            # Bit 10: dBm TX Power
            if present_0 & 0x400:
                offset = align(offset, 1)
                if offset + 1 <= radiotap_len:
                    result['tx_power'] = struct.unpack('b', packet[offset:offset+1])[0]
                offset += 1
            
            # Bit 11: Antenna
            if present_0 & 0x800:
                offset = align(offset, 1)
                offset += 1
            
            # Bit 12: dB Antenna Signal
            if present_0 & 0x1000:
                offset = align(offset, 1)
                offset += 1
            
            # Bit 13: dB Antenna Noise
            if present_0 & 0x2000:
                offset = align(offset, 1)
                offset += 1
            
            # Bit 30: Vendor Namespace
            if present_0 & 0x40000000:
                offset = align(offset, 2)
                if offset + 6 <= radiotap_len:
                    # OUI is first 3 bytes
                    oui = packet[offset:offset+3]
                    result['vendor_oui'] = ':'.join(f'{b:02x}' for b in oui)
                offset += 6  # Skip entire vendor namespace
            
            return result
            
        except Exception as e:
            print(f"Parse Radiotap Error: {e}")
            return {'header_length': 0, 'signal': -100}

    @staticmethod
    def parse_rsn_ie(tag_data):
        """
        Parse RSN (Robust Security Network) Information Element.
        Extracts WPA2/WPA3 details, cipher suites, and authentication methods.
        
        Args:
            tag_data: RSN IE payload bytes
            
        Returns:
            dict with security details or None
        """
        try:
            if len(tag_data) < 8:
                return {'security': 'WPA2'}
            
            # Version (2 bytes)
            version = struct.unpack('<H', tag_data[0:2])[0]
            
            # Group Cipher Suite (4 bytes): OUI (3) + Type (1)
            group_cipher_type = tag_data[5] if len(tag_data) > 5 else 0
            
            cipher_map = {
                0: 'None',
                1: 'WEP-40',
                2: 'TKIP',
                4: 'CCMP (AES)',
                5: 'WEP-104',
                6: 'BIP',
                8: 'GCMP',
                9: 'GCMP-256',
                10: 'CCMP-256'
            }
            group_cipher = cipher_map.get(group_cipher_type, f'Unknown({group_cipher_type})')
            
            offset = 6
            
            # Pairwise Cipher Suite Count (2 bytes)
            if offset + 2 > len(tag_data):
                return {'security': 'WPA2', 'group_cipher': group_cipher}
            
            pairwise_count = struct.unpack('<H', tag_data[offset:offset+2])[0]
            offset += 2
            
            # Pairwise Cipher Suites (4 bytes each)
            pairwise_ciphers = []
            for i in range(min(pairwise_count, 5)):  # Limit to 5 to avoid issues
                if offset + 4 <= len(tag_data):
                    cipher_type = tag_data[offset + 3]
                    pairwise_ciphers.append(cipher_map.get(cipher_type, f'Unknown({cipher_type})'))
                    offset += 4
                else:
                    break
            
            # Auth Key Management (AKM) Suite Count (2 bytes)
            if offset + 2 > len(tag_data):
                return {
                    'security': 'WPA2',
                    'group_cipher': group_cipher,
                    'pairwise_ciphers': pairwise_ciphers
                }
            
            akm_count = struct.unpack('<H', tag_data[offset:offset+2])[0]
            offset += 2
            
            # AKM Suites (4 bytes each)
            akm_map = {
                1: 'WPA2-Enterprise (802.1X)',
                2: 'WPA2-Personal (PSK)',
                3: 'FT over 802.1X',
                4: 'FT over PSK',
                5: 'WPA2-Enterprise SHA256',
                6: 'WPA2-Personal SHA256',
                8: 'WPA3-SAE',
                9: 'FT over SAE',
                11: 'WPA3-Enterprise Suite-B',
                12: 'WPA3-Enterprise 192-bit',
                18: 'OWE (Opportunistic Wireless Encryption)'
            }
            
            auth_methods = []
            for i in range(min(akm_count, 5)):
                if offset + 4 <= len(tag_data):
                    akm_type = tag_data[offset + 3]
                    auth_methods.append(akm_map.get(akm_type, f'Unknown({akm_type})'))
                    offset += 4
                else:
                    break
            
            # Determine security type based on AKM
            security = 'WPA2'
            if any('WPA3' in method for method in auth_methods):
                security = 'WPA3'
            elif any('OWE' in method for method in auth_methods):
                security = 'OWE'
            
            return {
                'security': security,
                'rsn_version': version,
                'group_cipher': group_cipher,
                'pairwise_ciphers': pairwise_ciphers,
                'auth_methods': auth_methods
            }
            
        except Exception:
            return {'security': 'WPA2'}

    @staticmethod
    def parse_80211(packet, radiotap_info):
        """
        Parses 802.11 frame with Radiotap context.
        Returns a dictionary with frame info if it's a Beacon, else None.
        
        Args:
            packet: Raw packet bytes
            radiotap_info: Dict from parse_radiotap() with physical layer data
        """
        try:
            radiotap_len = radiotap_info.get('header_length', 0)
            if radiotap_len == 0:
                return None
                
            frame = packet[radiotap_len:]

            if len(frame) < 24:
                return None
            
            # Frame Control
            fc = frame[0]
            type_ = (fc >> 2) & 0x3
            subtype = (fc >> 4) & 0xF
            
            if type_ == FC_TYPE_MGMT and subtype == FC_SUBTYPE_BEACON:
                # Beacon Frame
                # Address 3 is BSSID (bytes 16-21)
                bssid = frame[16:22]
                bssid_str = ':'.join('%02x' % b for b in bssid)
                
                # Fixed Parameters (12 bytes) start at 24
                # Timestamp (8), Beacon Interval (2), Cap Info (2)
                # Tags start at 24 + 12 = 36
                tag_offset = 36
                
                ssid = ""
                security = "Open"
                rsn_details = {}
                # Prefer Radiotap channel (ground truth) with fallback to beacon tag
                channel = radiotap_info.get('channel_number', 0)
                beacon_channel = 0  # Will be set from DS Parameter Set if present
                
                while tag_offset < len(frame):
                    if tag_offset + 2 > len(frame): 
                        break
                        
                    tag_num = frame[tag_offset]
                    tag_len = frame[tag_offset+1]
                    
                    if tag_offset + 2 + tag_len > len(frame):
                        break
                    
                    tag_data = frame[tag_offset+2 : tag_offset+2+tag_len]
                    
                    if tag_num == 0: # SSID
                        try:
                            ssid = tag_data.decode('utf-8')
                        except:
                            ssid = tag_data.hex()
                    elif tag_num == 3: # DS Parameter Set (Channel)
                        if len(tag_data) == 1:
                            beacon_channel = tag_data[0]
                            # Use beacon channel only if Radiotap didn't provide it
                            if channel == 0:
                                channel = beacon_channel

                    elif tag_num == 48: # RSN (WPA2/WPA3)
                        # Parse detailed RSN information
                        rsn_info = PacketParser.parse_rsn_ie(tag_data)
                        if rsn_info:
                            security = rsn_info.get('security', 'WPA2')
                            # Store RSN details for later
                            rsn_details = rsn_info
                    elif tag_num == 221: # Vendor Specific (WPA)
                        # Check for Microsoft OUI 00:50:f2 and type 1
                        if len(tag_data) >= 4 and tag_data.startswith(b'\x00\x50\xf2\x01'):
                            if security == "Open": security = "WPA"
                            
                    tag_offset += 2 + tag_len
                
                # Check for WEP (Privacy bit in Capability Info)
                cap_info = struct.unpack('<H', frame[34:36])[0]
                if security == "Open" and (cap_info & 0x0010):
                    security = "WEP"
                vendor = get_vendor(bssid_str)
                
                result = {
                    'type': 'BEACON',
                    'ssid': ssid,
                    'bssid': bssid_str,
                    'channel': channel,
                    'channel_freq': radiotap_info.get('channel_freq', 0),
                    'security': security,
                    'vendor': vendor,
                    # Radiotap physical layer metrics
                    'signal': radiotap_info.get('signal', -100),
                    'noise': radiotap_info.get('noise', -100),
                    'snr': radiotap_info.get('snr', 0),
                    'rate': radiotap_info.get('rate', 0.0),
                    'tx_power': radiotap_info.get('tx_power'),
                    'vendor_oui': radiotap_info.get('vendor_oui')
                }

                
                # Add detailed RSN info if available
                if 'rsn_details' in locals() and rsn_details:
                    result['rsn_version'] = rsn_details.get('rsn_version')
                    result['group_cipher'] = rsn_details.get('group_cipher')
                    result['pairwise_ciphers'] = rsn_details.get('pairwise_ciphers', [])
                    result['auth_methods'] = rsn_details.get('auth_methods', [])
                    # Create crypto description
                    if result['pairwise_ciphers']:
                        result['crypto'] = f"{security} ({'/'.join(result['pairwise_ciphers'][:2])})"
                    else:
                        result['crypto'] = security
                else:
                    result['crypto'] = security
                
                return result
            
            return None
            
        except Exception as e:
            # print(f"Error parsing 802.11: {e}")
            return None

    @staticmethod
    def parse_ip_tcp(packet, radiotap_len):
        """
        Parses packet for IP/TCP data with COMPLETE header field extraction.
        Handles both Monitor Mode (Radiotap + 802.11) and Managed Mode (Ethernet).
        """
        try:
            # 1. Determine if it's 802.11 or Ethernet
            is_80211 = (radiotap_len > 0)
            data = packet[radiotap_len:]
            
            src_mac = "N/A"
            dst_mac = "N/A"
            ethertype = 0
            ip_offset = 0
            
            if is_80211:
                # 802.11 Data Frame
                if len(data) < 24: return None
                
                fc = data[0]
                type_ = (fc >> 2) & 0x3
                subtype = (fc >> 4) & 0xF
                
                if type_ != FC_TYPE_DATA:
                    return None
                
                # Extract MACs
                dst_mac_bytes = data[4:10]
                src_mac_bytes = data[10:16]
                
                dst_mac = ':'.join('%02x' % b for b in dst_mac_bytes)
                src_mac = ':'.join('%02x' % b for b in src_mac_bytes)
                
                # Check for Encryption
                flags = data[1]
                is_encrypted = (flags & 0x40) != 0
                
                if is_encrypted:
                    return {
                        'type': '802.11',
                        'src_mac': src_mac,
                        'dst_mac': dst_mac,
                        'info': 'Encrypted Data (WPA/WEP)'
                    }
                
                # Find LLC/SNAP
                llc_idx = -1
                for i in range(24, 40): 
                    if data[i:i+3] == b'\xAA\xAA\x03':
                        llc_idx = i
                        break
                
                if llc_idx != -1:
                    ethertype = struct.unpack('!H', data[llc_idx+6:llc_idx+8])[0]
                    ip_offset = llc_idx + 8
                else:
                    return {
                        'type': '802.11',
                        'src_mac': src_mac,
                        'dst_mac': dst_mac,
                        'info': 'Unknown 802.11 Data'
                    }
                    
            else:
                # Managed Mode - Parse Complete Ethernet Frame
                if len(data) < 14: return None
                
                # Ethernet II Frame Header (14 bytes)
                # Destination MAC (6 bytes)
                dst_mac_bytes = data[0:6]
                dst_mac = ':'.join('%02x' % b for b in dst_mac_bytes)
                
                # Source MAC (6 bytes)
                src_mac_bytes = data[6:12]
                src_mac = ':'.join('%02x' % b for b in src_mac_bytes)
                
                # EtherType (2 bytes)
                ethertype = struct.unpack('!H', data[12:14])[0]
                
                # EtherType mappings
                ethertype_map = {
                    0x0800: 'IPv4',
                    0x0806: 'ARP',
                    0x86DD: 'IPv6',
                    0x8100: 'VLAN-tagged',
                    0x8847: 'MPLS unicast',
                    0x8848: 'MPLS multicast'
                }
                ethertype_name = ethertype_map.get(ethertype, f'Unknown (0x{ethertype:04x})')
                
                ip_offset = 14
            
            # 2. Parse IP Header (COMPLETE - All Fields)
            if ethertype == 0x0800: # IPv4
                ip_header = data[ip_offset:ip_offset+20]
                if len(ip_header) < 20: return None
                
                # Byte 0: Version (4 bits) + IHL (4 bits)
                version_ihl = ip_header[0]
                version = version_ihl >> 4
                ihl = version_ihl & 0x0F
                header_length = ihl * 4
                
                # Byte 1: DSCP (6 bits) + ECN (2 bits)
                dscp_ecn = ip_header[1]
                dscp = dscp_ecn >> 2
                ecn = dscp_ecn & 0x03
               
                # Bytes 2-3: Total Length
                total_length = struct.unpack('!H', ip_header[2:4])[0]
                
                # Bytes 4-5: Identification
                identification = struct.unpack('!H', ip_header[4:6])[0]
                
                # Bytes 6-7: Flags (3 bits) + Fragment Offset (13 bits)
                flags_frag = struct.unpack('!H', ip_header[6:8])[0]
                flags = flags_frag >> 13
                flag_reserved = bool(flags & 0x04)
                flag_df = bool(flags & 0x02)  # Don't Fragment
                flag_mf = bool(flags & 0x01)  # More Fragments
                fragment_offset = flags_frag & 0x1FFF
                
                # Byte 8: TTL
                ttl = ip_header[8]
                
                # Byte 9: Protocol
                protocol = ip_header[9]
                protocol_names = {1: 'ICMP', 6: 'TCP', 17: 'UDP'}
                protocol_name = protocol_names.get(protocol, f'Protocol-{protocol}')
                
                # Bytes 10-11: Header Checksum
                checksum = struct.unpack('!H', ip_header[10:12])[0]
                
                # Bytes 12-19: Source and Destination IP
                src_ip = socket.inet_ntoa(ip_header[12:16])
                dst_ip = socket.inet_ntoa(ip_header[16:20])
                
                packet_info = {
                    'type': 'IP',
                    'src_mac': src_mac,
                    'dst_mac': dst_mac,
                    # Complete IP Header Fields
                    'ip_version': version,
                    'ip_ihl': ihl,
                    'ip_header_length': header_length,
                    'ip_dscp': dscp,
                    'ip_ecn': ecn,
                    'ip_total_length': total_length,
                    'ip_identification': identification,
                    'ip_flag_df': flag_df,
                    'ip_flag_mf': flag_mf,
                    'ip_fragment_offset': fragment_offset,
                    'ip_ttl': ttl,
                    'ip_protocol': protocol,
                    'ip_protocol_name': protocol_name,
                    'ip_checksum': f'0x{checksum:04x}',
                    'src_ip': src_ip,
                    'dst_ip': dst_ip,
                    'info': f'{protocol_name}: {src_ip} → {dst_ip}'
                }
                
                # 3. Parse TCP Header (COMPLETE - All Fields)
                if protocol == 6:  # TCP
                    tcp_offset = ip_offset + header_length
                    tcp_header = data[tcp_offset:tcp_offset+20]
                    if len(tcp_header) < 20: return packet_info
                    
                    # Bytes 0-1: Source Port
                    src_port = struct.unpack('!H', tcp_header[0:2])[0]
                    
                    # Bytes 2-3: Destination Port
                    dst_port = struct.unpack('!H', tcp_header[2:4])[0]
                    
                    # Bytes 4-7: Sequence Number
                    seq_num = struct.unpack('!I', tcp_header[4:8])[0]
                    
                    # Bytes 8-11: Acknowledgment Number
                    ack_num = struct.unpack('!I', tcp_header[8:12])[0]
                    
                    # Byte 12: Data Offset (4 bits) + Reserved (3 bits) + NS (1 bit)
                    offset_reserved_ns = tcp_header[12]
                    data_offset = offset_reserved_ns >> 4
                    tcp_header_length = data_offset * 4
                    ns_flag = bool(offset_reserved_ns & 0x01)
                    
                    # Byte 13: TCP Flags
                    flags_byte = tcp_header[13]
                    tcp_flags = {
                        'FIN': bool(flags_byte & 0x01),
                        'SYN': bool(flags_byte & 0x02),
                        'RST': bool(flags_byte & 0x04),
                        'PSH': bool(flags_byte & 0x08),
                        'ACK': bool(flags_byte & 0x10),
                        'URG': bool(flags_byte & 0x20),
                        'ECE': bool(flags_byte & 0x40),
                        'CWR': bool(flags_byte & 0x80),
                        'NS': ns_flag
                    }
                    flags_str = ''.join([k for k, v in tcp_flags.items() if v])
                    
                    # Bytes 14-15: Window Size
                    window_size = struct.unpack('!H', tcp_header[14:16])[0]
                    
                    # Bytes 16-17: Checksum
                    tcp_checksum = struct.unpack('!H', tcp_header[16:18])[0]
                    
                    # Bytes 18-19: Urgent Pointer
                    urgent_pointer = struct.unpack('!H', tcp_header[18:20])[0]
                    
                    # Calculate payload offset
                    payload_offset = tcp_offset + tcp_header_length
                    payload = data[payload_offset:]
                    
                    packet_info.update({
                        'type': 'TCP',
                        # Complete TCP Header Fields
                        'src_port': src_port,
                        'dst_port': dst_port,
                        'tcp_seq_num': seq_num,
                        'tcp_ack_num': ack_num,
                        'tcp_data_offset': data_offset,
                        'tcp_header_length': tcp_header_length,
                        'tcp_flags': tcp_flags,
                        'tcp_flags_str': flags_str,
                        'tcp_window_size': window_size,
                        'tcp_checksum': f'0x{tcp_checksum:04x}',
                        'tcp_urgent_pointer': urgent_pointer,
                        'payload': payload,
                        'info': f'TCP {src_port} → {dst_port} [{flags_str}]'
                    })
                    
                    # 4. Parse HTTP Payload (if port 80)
                    if src_port == 80 or dst_port == 80:
                        http_data = PacketParser.parse_http_payload(payload)
                        if http_data:
                            packet_info['http'] = http_data
                            packet_info['info'] = f"HTTP {http_data.get('method', http_data.get('status_code', ''))} {src_port} → {dst_port}"
                    
                # UDP Protocol (17)
                elif protocol == 17:  # UDP
                    udp_offset = ip_offset + header_length
                    udp_header = data[udp_offset:udp_offset+8]
                    if len(udp_header) < 8: return packet_info
                    
                    # UDP Header: Src Port (2), Dst Port (2), Length (2), Checksum (2)
                    src_port = struct.unpack('!H', udp_header[0:2])[0]
                    dst_port = struct.unpack('!H', udp_header[2:4])[0]
                    length = struct.unpack('!H', udp_header[4:6])[0]
                    udp_checksum = struct.unpack('!H', udp_header[6:8])[0]
                    
                    # Common UDP services
                    service_map = {
                        53: 'DNS',
                        67: 'DHCP (Server)',
                        68: 'DHCP (Client)',
                        123: 'NTP',
                        161: 'SNMP',
                        162: 'SNMP Trap',
                        514: 'Syslog',
                        1900: 'SSDP'
                    }
                    service = service_map.get(src_port) or service_map.get(dst_port) or ''
                    
                    payload_offset = udp_offset + 8
                    payload = data[payload_offset:]
                    
                    packet_info.update({
                        'type': 'UDP',
                        'src_port': src_port,
                        'dst_port': dst_port,
                        'udp_length': length,
                        'udp_checksum': f'0x{udp_checksum:04x}',
                        'udp_service': service,
                        'payload': payload,
                        'info': f'UDP {src_port} → {dst_port}' + (f' ({service})' if service else '')
                    })
                
                # ICMP Protocol (1)
                elif protocol == 1:  # ICMP
                    icmp_offset = ip_offset + header_length
                    icmp_header = data[icmp_offset:icmp_offset+8]
                    if len(icmp_header) < 8: return packet_info
                    
                    # ICMP Header: Type (1), Code (1), Checksum (2), Rest of Header (4)
                    icmp_type = icmp_header[0]
                    icmp_code = icmp_header[1]
                    icmp_checksum = struct.unpack('!H', icmp_header[2:4])[0]
                    rest_of_header = struct.unpack('!I', icmp_header[4:8])[0]
                    
                    # For Echo Request/Reply, rest_of_header contains:
                    # Identifier (2 bytes) + Sequence Number (2 bytes)
                    identifier = rest_of_header >> 16
                    sequence = rest_of_header & 0xFFFF
                    
                    # ICMP Type meanings
                    type_map = {
                        0: 'Echo Reply (Ping Reply)',
                        3: 'Destination Unreachable',
                        4: 'Source Quench',
                        5: 'Redirect',
                        8: 'Echo Request (Ping)',
                        11: 'Time Exceeded',
                        12: 'Parameter Problem',
                        13: 'Timestamp Request',
                        14: 'Timestamp Reply'
                    }
                    type_name = type_map.get(icmp_type, f'Type {icmp_type}')
                    
                    packet_info.update({
                        'type': 'ICMP',
                        'icmp_type': icmp_type,
                        'icmp_type_name': type_name,
                        'icmp_code': icmp_code,
                        'icmp_checksum': f'0x{icmp_checksum:04x}',
                        'icmp_identifier': identifier,
                        'icmp_sequence': sequence,
                        'info': f'ICMP {type_name}' + (f' (ID={identifier}, Seq={sequence})' if icmp_type in [0, 8] else '')
                    })
                    
                return packet_info
                
            return {
                'type': 'ETH',
                'src_mac': src_mac,
                'dst_mac': dst_mac,
                'info': f"EtherType 0x{ethertype:04x}"
            }
            
        except Exception:
            return None
    
    @staticmethod
    def parse_http_payload(payload):
        """
        Extract HTTP request/response from TCP payload.
        
        Args:
            payload: TCP payload bytes
        
        Returns:
            dict with HTTP details or None
        """
        if len(payload) < 10:
            return None
        
        try:
            # Decode as ASCII (HTTP is text-based)
            text = payload.decode('ascii', errors='ignore')
            lines = text.split('\r\n')
            
            if not lines:
                return None
            
            first_line = lines[0]
            
            # HTTP Request: "GET /path HTTP/1.1"
            if any(first_line.startswith(m) for m in ['GET ', 'POST ', 'PUT ', 'DELETE ', 'HEAD ', 'OPTIONS ', 'PATCH ']):
                parts = first_line.split(' ')
                method = parts[0] if len(parts) > 0 else 'UNKNOWN'
                path = parts[1] if len(parts) > 1 else '/'
                version = parts[2] if len(parts) > 2 else ''
                
                # Extract headers (until blank line)
                headers = []
                content_type = None
                for line in lines[1:]:
                    if line == '':
                        break
                    if ':' in line:
                        headers.append(line)
                        # Check for Content-Type
                        if line.lower().startswith('content-type:'):
                            content_type = line.split(':', 1)[1].strip()
                
                # Body is after blank line
                body_start = text.find('\r\n\r\n')
                if body_start != -1:
                    body_bytes = payload[body_start+4:]
                    body = PacketParser._format_http_body(body_bytes, content_type)
                else:
                    body = ''
                
                return {
                    'type': 'HTTP_REQUEST',
                    'method': method,
                    'path': path,
                    'version': version,
                    'headers': headers[:10],  # First 10 headers
                    'body': body,
                    'content_type': content_type
                }
            
            # HTTP Response: "HTTP/1.1 200 OK"
            elif first_line.startswith('HTTP/'):
                parts = first_line.split(' ', 2)
                version = parts[0] if len(parts) > 0 else ''
                status_code = parts[1] if len(parts) > 1 else '000'
                status_text = parts[2] if len(parts) > 2 else ''
                
                headers = []
                content_type = None
                content_length = None
                for line in lines[1:]:
                    if line == '':
                        break
                    if ':' in line:
                        headers.append(line)
                        # Check for Content-Type and Content-Length
                        line_lower = line.lower()
                        if line_lower.startswith('content-type:'):
                            content_type = line.split(':', 1)[1].strip()
                        elif line_lower.startswith('content-length:'):
                            try:
                                content_length = int(line.split(':', 1)[1].strip())
                            except:
                                pass
                
                body_start = text.find('\r\n\r\n')
                if body_start != -1:
                    body_bytes = payload[body_start+4:]
                    body = PacketParser._format_http_body(body_bytes, content_type, content_length)
                else:
                    body = ''
                
                return {
                    'type': 'HTTP_RESPONSE',
                    'version': version,
                    'status_code': status_code,
                    'status_text': status_text,
                    'headers': headers[:10],
                    'body': body,
                    'content_type': content_type
                }
        except:
            pass
        
        return None
    
    @staticmethod
    def _format_http_body(body_bytes, content_type, content_length=None):
        """
        Format HTTP body for display, detecting binary vs text content.
        
        Args:
            body_bytes: Raw body bytes
            content_type: Content-Type header value
            content_length: Content-Length header value
            
        Returns:
            Formatted string for display
        """
        if not body_bytes:
            return ''
        
        # Detect binary content types
        binary_types = [
            'image/', 'video/', 'audio/', 'application/octet-stream',
            'application/pdf', 'application/zip', 'font/', 'application/x-'
        ]
        
        is_binary = False
        if content_type:
            is_binary = any(content_type.lower().startswith(bt) for bt in binary_types)
        
        # Also check if data looks binary (lots of non-printable chars)
        if not is_binary and len(body_bytes) > 0:
            non_printable = sum(1 for b in body_bytes[:100] if b < 32 and b not in [9, 10, 13])
            if non_printable > len(body_bytes[:100]) * 0.3:  # >30% non-printable
                is_binary = True
        
        if is_binary:
            # Show binary indicator
            type_desc = content_type if content_type else "unknown type"
            size = content_length if content_length else len(body_bytes)
            return f"[Binary content: {type_desc}, {size} bytes]\n\nHex preview (first 64 bytes):\n{body_bytes[:64].hex(' ', 2)}"
        else:
            # Show text content
            try:
                text = body_bytes.decode('utf-8', errors='replace')
                return text[:500] if text else ''  # First 500 chars
            except:
                return body_bytes.decode('ascii', errors='ignore')[:500]

