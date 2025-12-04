import sys
import time
import argparse
from core.hopper import ChannelHopper
from core.sniffer import Sniffer
from core.parser import PacketParser

def packet_handler(raw_data):
    # 1. Parse Radiotap
    radiotap_len, signal = PacketParser.parse_radiotap(raw_data)
    
    # 2. Parse 802.11 Beacon
    beacon_info = PacketParser.parse_80211(raw_data, radiotap_len)
    if beacon_info:
        if signal == -100 or signal == 0:
            # Debug: Print first 30 bytes of packet to analyze Radiotap
            print(f"[DEBUG] Raw Header: {raw_data[:30].hex()}")
        print(f"[BEACON] SSID: {beacon_info['ssid']} | Signal: {signal} dBm | Ch: {beacon_info['channel']}")
        return

    # 3. Parse IP/TCP (Sniffer)
    tcp_info = PacketParser.parse_ip_tcp(raw_data, radiotap_len)
    if tcp_info:
        if 'src_ip' in tcp_info:
            print(f"[TCP] {tcp_info['src_ip']}:{tcp_info['src_port']} -> {tcp_info['dst_ip']}:{tcp_info['dst_port']}")
        else:
            print(f"[DATA] {tcp_info.get('info', 'Unknown Packet')}")
    else:
        # Debug: Print what kind of frame this is if not Beacon and not parsed as Data
        try:
            fc = raw_data[radiotap_len]
            type_ = (fc >> 2) & 0x3
            subtype = (fc >> 4) & 0xF
            if type_ != 0: # Ignore other Mgmt frames for noise reduction
                print(f"[DEBUG] Unparsed Frame: Type={type_}, Subtype={subtype}, Len={len(raw_data)}")
        except:
            pass

def main():
    parser = argparse.ArgumentParser(description="Headless Debug Runner")
    parser.add_argument("-i", "--interface", required=True)
    parser.add_argument("-c", "--channel", type=int, help="Lock to specific channel")
    args = parser.parse_args()
    
    print(f"[*] Starting Headless Debugger on {args.interface}")
    
    hopper = None
    if args.channel:
        print(f"[*] Locking to Channel {args.channel}")
        import subprocess
        subprocess.run(["iwconfig", args.interface, "channel", str(args.channel)])
    else:
        # Start Hopper
        hopper = ChannelHopper(args.interface)
        hopper.start()
    
    # Start Sniffer
    sniffer = Sniffer(args.interface, packet_handler)
    sniffer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Stopping...")
        if hopper: hopper.stop()
        sniffer.stop()

if __name__ == "__main__":
    main()
