import socket
import threading
import sys
from utils.constants import ETH_P_ALL

class Sniffer(threading.Thread):
    def __init__(self, interface, callback):
        """
        interface: str, e.g., 'wlan0mon'
        callback: function, called with raw_data for each packet
        """
        super().__init__()
        self.interface = interface
        self.callback = callback
        self.daemon = True
        self.running = False
        self.socket = None

    def run(self):
        try:
            # Create raw socket
            # Use ETH_P_ALL (0x0003) to capture all packet types
            self.socket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))
            
            # Set large receive buffer (like airodump-ng does)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2**30)
            
            # Bind to interface
            self.socket.bind((self.interface, 0))
            self.running = True
            
            print(f"[*] Sniffer started on {self.interface}")
            
            while self.running:
                try:
                    # Receive packet
                    # 65536 is the max size of an IP packet
                    raw_data, _ = self.socket.recvfrom(65536)
                    if self.callback:
                        self.callback(raw_data)
                except OSError as e:
                    if self.running:
                        print(f"Socket error: {e}")
                    break
                except Exception as e:
                    print(f"Error processing packet: {e}")
                    continue

        except PermissionError:
            print("Error: Permission denied. Please run as root.")
            sys.exit(1)
        except Exception as e:
            print(f"Error starting sniffer: {e}")
            sys.exit(1)

    def stop(self):
        self.running = False
        if self.socket:
            self.socket.close()
