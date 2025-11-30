import sys
import queue
import argparse
from core.hopper import ChannelHopper
from core.sniffer import Sniffer
from core.parser import PacketParser
from gui.app import App
import subprocess

def check_monitor_mode(interface):
    """
    Checks if the interface is in Monitor mode using iwconfig.
    """
    try:
        # Run iwconfig
        result = subprocess.run(
            ["iwconfig", interface],
            capture_output=True,
            text=True
        )
        # Check output for "Mode:Monitor"
        if "Mode:Monitor" in result.stdout:
            return True
        return False
    except FileNotFoundError:
        # Try 'iw' command if iwconfig is missing
        try:
            result = subprocess.run(
                ["iw", "dev", interface, "info"],
                capture_output=True,
                text=True
            )
            if "type monitor" in result.stdout:
                return True
        except:
            pass
        return False
    except Exception as e:
        print(f"Warning: Could not check monitor mode: {e}")
        return False

def check_managed_mode(interface):
    """
    Checks if the interface is in Managed mode (not Monitor mode).
    """
    try:
        # Run iwconfig
        result = subprocess.run(
            ["iwconfig", interface],
            capture_output=True,
            text=True
        )
        # Check output for "Mode:Managed"
        if "Mode:Managed" in result.stdout:
            return True
        # Also check it's NOT in Monitor mode
        if "Mode:Monitor" in result.stdout:
            return False
        return False
    except FileNotFoundError:
        # Try 'iw' command if iwconfig is missing
        try:
            result = subprocess.run(
                ["iw", "dev", interface, "info"],
                capture_output=True,
                text=True
            )
            # If it's monitor, return False
            if "type monitor" in result.stdout:
                return False
            # If it's managed/station, return True
            if "type managed" in result.stdout or "type station" in result.stdout:
                return True
        except:
            pass
        return False
    except Exception as e:
        print(f"Warning: Could not check managed mode: {e}")
        return False


def packet_handler(raw_data, result_queue, debug=False, managed=False):
    """
    Callback for the sniffer thread.
    Parses packet and puts result in queue for GUI.
    """
    if debug:
        print(f"[DEBUG] Packet len: {len(raw_data)}")

    radiotap_len = 0
    signal = 0
    
    if not managed:
        # 1. Parse Radiotap (only in Monitor mode)
        radiotap_len, signal = PacketParser.parse_radiotap(raw_data)
        
        if debug and signal != 0:
            print(f"[DEBUG] Signal: {signal} dBm")
        
        # 2. Parse 802.11 Beacon
        beacon_info = PacketParser.parse_80211(raw_data, radiotap_len)
        if beacon_info:
            beacon_info['signal'] = signal # Add signal from Radiotap
            if debug:
                print(f"[DEBUG] Beacon: {beacon_info}")
            result_queue.put(beacon_info)
            return

    # 3. Parse IP/TCP (Sniffer)
    # In Managed mode, radiotap_len is 0, so it parses from byte 0 (Ethernet)
    tcp_info = PacketParser.parse_ip_tcp(raw_data, radiotap_len)
    if tcp_info:
        if debug:
            print(f"[DEBUG] TCP: {tcp_info}")
        result_queue.put(tcp_info)

def main():
    parser = argparse.ArgumentParser(description="Manual WiFi Analyzer & Sniffer")
    parser.add_argument("-i", "--interface", required=True, help="Wireless interface in Monitor mode (e.g., wlan0mon)")
    parser.add_argument("-c", "--channel", type=int, help="Lock to specific channel")
    parser.add_argument("-m", "--managed", action="store_true", help="Run in Managed Mode (Ethernet headers)")
    parser.add_argument("--debug", action="store_true", help="Enable debug output to terminal")
    args = parser.parse_args()
    
    interface = args.interface
    debug_mode = args.debug
    managed_mode = args.managed
    
    print(f"[*] Starting on interface: {interface}")
    
    # Check for Monitor Mode (unless managed)
    if not managed_mode:
        if not check_monitor_mode(interface):
            print(f"Error: Interface {interface} is not in Monitor mode.")
            print("Please enable monitor mode using 'sudo airmon-ng start <interface>' or equivalent.")
            sys.exit(1)
    else:
        # Check for Managed Mode
        if not check_managed_mode(interface):
            print(f"Error: Interface {interface} is not in Managed mode.")
            print("The interface appears to be in Monitor mode or another mode.")
            print("Please disable monitor mode using 'sudo airmon-ng stop <interface>' or")
            print("reconnect to a WiFi network to return to Managed mode.")
            sys.exit(1)
        print("[*] Running in Managed Mode (Ethernet)")

    
    # Queue for thread communication
    result_queue = queue.Queue()
    
    # Start Channel Hopper (if not locked and not managed)
    # Hopper only works in Monitor mode usually
    hopper = None
    if not managed_mode:
        if args.channel:
            print(f"[*] Locking to Channel {args.channel}")
            subprocess.run(["iwconfig", interface, "channel", str(args.channel)])
        else:
            hopper = ChannelHopper(interface)
            hopper.start()
    
    # Start Sniffer
    # We use a lambda to pass the queue to the handler
    sniffer = Sniffer(interface, lambda pkt: packet_handler(pkt, result_queue, debug_mode, managed_mode))
    sniffer.start()
    
    # Start GUI
    print("[*] Initializing GUI...")
    try:
        app = App(result_queue)
        print("[*] GUI initialized. Starting mainloop...")
        app.mainloop()
    except KeyboardInterrupt:
        print("\n[*] Stopping...")
    except Exception as e:
        print(f"\n[!] CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("[*] Cleaning up threads...")
        if hopper: hopper.stop()
        sniffer.stop()
        sys.exit(0)

if __name__ == "__main__":
    main()
