import json
import os

# Path to the JSON database
# Assumes it is in the same directory as this script
DB_PATH = os.path.join(os.path.dirname(__file__), 'oui_db.json')

def load_database(path):
    """Loads the JSON database efficiently."""
    if not os.path.exists(path):
        # Fallback or silent fail
        return {}
    
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

# Load once at module level
OUI_DB = load_database(DB_PATH)

def get_vendor(mac_address):
    """
    Looks up the vendor for a given MAC address string (XX:XX:XX:XX:XX:XX).
    """
    if not mac_address or len(mac_address) < 8:
        return "Unknown"

    try:
        # Normalize MAC: upper case and ensure standard format for lookup
        # This takes the first 8 chars (XX:XX:XX)
        oui = mac_address[:8].upper().replace('-', ':')
        return OUI_DB.get(oui, "Unknown")
    except:
        return "Unknown"
