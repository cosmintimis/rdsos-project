import sys
import os
sys.path.append(os.getcwd())

from core.parser import PacketParser
import struct

def create_mock_beacon():
    # Radiotap (18 bytes)
    # Header Rev (1), Pad (1), Len (2), Present (4) ...
    radiotap = struct.pack('BBHI', 0, 0, 18, 0) + b'\x00'*10
    
    # 802.11 Beacon Frame
    # FC (2), Dur (2), Addr1 (6), Addr2 (6), Addr3 (6), Seq (2)
    # Type=0, Subtype=8 -> 0x80
    fc = 0x80
    addr1 = b'\xff'*6 # Broadcast
    addr2 = b'\x00\x11\x22\x33\x44\x55' # Src
    addr3 = b'\x00\x11\x22\x33\x44\x55' # BSSID
    
    dot11 = struct.pack('B', fc) + b'\x00' + b'\x00\x00' + addr1 + addr2 + addr3 + b'\x00\x00'
    
    # Fixed Params (12 bytes)
    fixed = b'\x00'*12
    
    # Tags
    # SSID (Tag 0, Len 4, "TEST")
    ssid_tag = b'\x00\x04TEST'
    # Channel (Tag 3, Len 1, Ch 6)
    chan_tag = b'\x03\x01\x06'
    
    return radiotap + dot11 + fixed + ssid_tag + chan_tag

def create_mock_tcp():
    # Radiotap
    radiotap = struct.pack('BBHI', 0, 0, 18, 0) + b'\x00'*10
    
    # 802.11 Data Frame (Type 2, Subtype 0 -> 0x08)
    fc = 0x08
    # FC(2) + Dur(2) + Addrs(18) + Seq(2) = 24 bytes
    dot11 = struct.pack('B', fc) + b'\x00' + b'\x00\x00' + b'\x00'*18 + b'\x00\x00'
    
    # LLC SNAP (AA AA 03 00 00 00 08 00) -> IPv4
    llc = b'\xAA\xAA\x03\x00\x00\x00\x08\x00'
    
    # IP Header (20 bytes)
    # Ver/IHL=0x45, TOS=0, Len=40, ID=0, Flags=0, TTL=64, Proto=6 (TCP), Checksum=0, Src, Dst
    ip = struct.pack('!BBHHHBBH4s4s', 0x45, 0, 40, 0, 0, 64, 6, 0, b'\x7f\x00\x00\x01', b'\x7f\x00\x00\x01')
    
    # TCP Header (20 bytes)
    # Src=1234, Dst=80, Seq=0, Ack=0, Off=5, Flags=0, Win=0, Sum=0, Urg=0
    tcp = struct.pack('!HHLLBBHHH', 1234, 80, 0, 0, 0x50, 0, 0, 0, 0)
    
    # Payload
    payload = b'GET / HTTP/1.1\r\n'
    
    return radiotap + dot11 + llc + ip + tcp + payload

def test_beacon():
    print("Testing Beacon Parsing...")
    packet = create_mock_beacon()
    rt_len, _ = PacketParser.parse_radiotap(packet)
    info = PacketParser.parse_80211(packet, rt_len)
    
    if info and info['ssid'] == 'TEST' and info['channel'] == 6:
        print("PASS: Beacon parsed correctly.")
        print(info)
    else:
        print("FAIL: Beacon parsing failed.")
        print(info)

def test_tcp():
    print("\nTesting TCP Parsing...")
    packet = create_mock_tcp()
    rt_len, _ = PacketParser.parse_radiotap(packet)
    info = PacketParser.parse_ip_tcp(packet, rt_len)
    
    if info and info['dst_port'] == 80 and b'GET' in info['payload']:
        print("PASS: TCP parsed correctly.")
        print(info)
    else:
        print("FAIL: TCP parsing failed.")
        print(info)

if __name__ == "__main__":
    test_beacon()
    test_tcp()
