import urllib.request
import re
import json
import os

IEEE_OUI_URL = "http://standards-oui.ieee.org/oui/oui.txt"
DB_FILENAME = "oui_db.json"

def update_oui_db():
    print(f"[*] Downloading OUI data from {IEEE_OUI_URL}...")
    try:
        req = urllib.request.Request(
            IEEE_OUI_URL, 
            data=None, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        )
        with urllib.request.urlopen(req) as response:
            data = response.read().decode('utf-8')
    except Exception as e:
        print(f"[!] Failed to download OUI data: {e}")
        return

    print("[*] Parsing data...")
    # Regex to find lines like: "00-00-00   (hex)		XEROX CORPORATION"
    # We want to capture "00-00-00" and "XEROX CORPORATION"
    oui_pattern = re.compile(r'^([0-9A-F]{2}-[0-9A-F]{2}-[0-9A-F]{2})\s+\(hex\)\s+(.+)$', re.MULTILINE)
    
    vendors = {}
    matches = oui_pattern.findall(data)
    
    for mac_prefix, vendor_name in matches:
        # Convert 00-00-00 to 00:00:00
        oui = mac_prefix.replace('-', ':')
        vendors[oui] = vendor_name.strip()

    print(f"[*] Found {len(vendors)} vendors.")
    
    # Save to JSON
    db_path = os.path.join(os.path.dirname(__file__), DB_FILENAME)
    print(f"[*] Saving to {db_path}...")
    
    with open(db_path, 'w') as f:
        json.dump(vendors, f, indent=4)
        
    print("[+] Database updated successfully.")

if __name__ == "__main__":
    update_oui_db()
