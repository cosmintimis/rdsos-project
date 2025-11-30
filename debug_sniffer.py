import socket
import struct
import sys
import os
from core.sniffer import Sniffer
from core.parser import PacketParser

packet_count = 0

def debug_handler(raw_data):
    global packet_count
    packet_count += 1
    
    if packet_count % 100 == 0:
        print(f"[*] Captured {packet_count} packets so far...")
    
    try:
        # 1. Parse Radiotap
        radiotap_len, signal = PacketParser.parse_radiotap(raw_data)
        
        # 2. Parse 802.11
        # We only care about Beacons for this test
        beacon = PacketParser.parse_80211(raw_data, radiotap_len)
        
        if beacon:
            print(f"[+] BEACON FOUND: SSID={beacon['ssid']}, BSSID={beacon['bssid']}, Signal={signal}dBm")
        else:
            # Optional: Print what it IS if not a beacon, to see if we are capturing anything
            if len(raw_data) > radiotap_len:
                fc = raw_data[radiotap_len]
                type_ = (fc >> 2) & 0x3
                subtype = (fc >> 4) & 0xF
                # print(f"[-] Packet captured (Type {type_}, Subtype {subtype}), but not a beacon.")
                pass

    except Exception as e:
        print(f"[!] Error parsing packet: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: sudo python3 debug_sniffer.py <interface>")
        sys.exit(1)

    interface = sys.argv[1]
    print(f"[*] Starting Debug Sniffer on {interface}...")
    
    # Raw Socket
    try:
        s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))
        s.bind((interface, 0))
    except Exception as e:
        print(f"[!] Failed to open socket: {e}")
        sys.exit(1)

    print("[*] Socket opened. Listening for Beacons...")
    
    while True:
        try:
            pkt, _ = s.recvfrom(65536)
            debug_handler(pkt)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[!] Recv Error: {e}")
            break

if __name__ == "__main__":
    main()
