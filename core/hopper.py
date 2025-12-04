import threading
import subprocess
import time

class ChannelHopper(threading.Thread):
    def __init__(self, interface, interval=0.5):
        super().__init__()
        self.interface = interface
        self.interval = interval
        self.daemon = True
        self.running = False
        self.channels = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
        self.current_channel = 1

    def run(self):
        self.running = True
        while self.running:
            for channel in self.channels:
                if not self.running:
                    break
                self.set_channel(channel)
                self.current_channel = channel
                time.sleep(self.interval)

    def set_channel(self, channel):
        try:
            #TODO: check if interface is up and in monitor mode 
            subprocess.run(
                ["iwconfig", self.interface, "channel", str(channel)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print(f"[DEBUG] Switched to Channel {channel}") 
        except Exception as e:
            print(f"[Hopper] Error setting channel {channel}: {e}")

    def stop(self):
        self.running = False
