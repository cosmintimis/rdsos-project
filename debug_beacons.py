import socket
import struct
import sys
import os

packet_count = 0
beacon_count = 0

def debug_handler(raw_data):
    global packet_count, beacon_count
    packet_count += 1
    
    try:
        # Parse Radiotap - same as parser.py
        if len(raw_data) < 8:
            return
        
        radiotap_len = struct.unpack('<H', raw_data[2:4])[0]
        
        # Try to get signal (approx offset 22, but might vary)
        signal = 0
        try:
            if len(raw_data) > 22:
                signal = struct.unpack('b', raw_data[22:23])[0]
        except:
            pass
        
        # Parse 802.11 frame
        if len(raw_data) <= radiotap_len:
            return
        
        frame = raw_data[radiotap_len:]
        
        if len(frame) < 24:
            return
        
        # Frame Control
        fc = frame[0]
        type_ = (fc >> 2) & 0x3
        subtype = (fc >> 4) & 0xF
        
        # Print every 50th packet to show we're receiving
        if packet_count % 50 == 0:
            print(f"[*] Captured {packet_count} packets (Type={type_}, Subtype={subtype})")
        
        # FC_TYPE_MGMT = 0, FC_SUBTYPE_BEACON = 8
        if type_ == 0 and subtype == 8:
            beacon_count += 1
            
            # BSSID is at bytes 16-21
            bssid = frame[16:22]
            bssid_str = ':'.join('%02x' % b for b in bssid)
            
            # Tags start at offset 36
            ssid = "<Unknown>"
            channel = 0
            
            tag_offset = 36
            while tag_offset < len(frame):
                if tag_offset + 2 > len(frame):
                    break
                
                tag_num = frame[tag_offset]
                tag_len = frame[tag_offset+1]
                
                if tag_offset + 2 + tag_len > len(frame):
                    break
                
                tag_data = frame[tag_offset+2 : tag_offset+2+tag_len]
                
                if tag_num == 0:  # SSID
                    try:
                        ssid = tag_data.decode('utf-8')
                    except:
                        ssid = tag_data.hex()
                elif tag_num == 3:  # Channel
                    if len(tag_data) == 1:
                        channel = tag_data[0]
                
                tag_offset += 2 + tag_len
            
            print(f"[+] BEACON #{beacon_count}: SSID='{ssid}', BSSID={bssid_str}, Ch={channel}, Signal={signal}dBm")

    except Exception as e:
        print(f"[!] Error: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: sudo python3 debug_beacons.py <interface>")
        sys.exit(1)

    interface = sys.argv[1]
    print(f"[*] Debug Beacon Sniffer on {interface}")
    print(f"[*] Looking for Management frames (Type=0, Subtype=8)")
    print(f"[*] Press Ctrl+C to stop\n")
    
    try:
        s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))
        s.bind((interface, 0))
    except Exception as e:
        print(f"[!] Socket error: {e}")
        sys.exit(1)

    print("[*] Socket opened. Listening...\n")
    
    try:
        while True:
            pkt, _ = s.recvfrom(65536)
            debug_handler(pkt)
    except KeyboardInterrupt:
        print(f"\n\n[*] Stopped. Total: {packet_count} packets, {beacon_count} beacons")

if __name__ == "__main__":
    main()
