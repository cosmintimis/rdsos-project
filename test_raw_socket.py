#!/usr/bin/env python3
import socket
import sys

if len(sys.argv) < 2:
    print("Usage: sudo python3 test_raw_socket.py <interface>")
    sys.exit(1)

interface = sys.argv[1]

print(f"[*] Creating raw socket on {interface}...")

try:
    # Try to create the socket
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))
    print(f"[+] Socket created successfully")
    
    # Bind to interface
    s.bind((interface, 0))
    print(f"[+] Bound to {interface}")
    
    # Try to receive ONE packet
    print(f"[*] Waiting for packets... (Ctrl+C to stop)")
    count = 0
    while count < 10:
        pkt, addr = s.recvfrom(65536)
        count += 1
        print(f"[+] Packet #{count}: {len(pkt)} bytes from {addr}")
    
    print(f"\n[+] SUCCESS: Captured {count} packets!")
    
except PermissionError:
    print("[!] Permission denied - run with sudo")
    sys.exit(1)
except Exception as e:
    print(f"[!] ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
