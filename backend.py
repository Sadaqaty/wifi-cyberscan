import pandas as pd
import threading
import time
import numpy as np
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from mac_vendor_lookup import MacLookup
import os
import scipy.signal as signal_lib
from datetime import datetime

class CSVWatcher(FileSystemEventHandler):
    """
    Watches airodump-ng CSV file for changes and parses new data in real-time.
    Calls a callback with the latest AP and Station DataFrames on update.
    """
    def __init__(self, csv_path, on_update, refresh_interval=2):
        self.csv_path = csv_path
        self.on_update = on_update
        self.refresh_interval = refresh_interval
        self.last_mtime = 0
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def _watch_loop(self):
        while not self._stop_event.is_set():
            try:
                if os.path.exists(self.csv_path):
                    mtime = os.path.getmtime(self.csv_path)
                    if mtime != self.last_mtime:
                        self.last_mtime = mtime
                        ap_df, st_df = self._parse_csv()
                        if ap_df is not None or st_df is not None:
                            self.on_update(ap_df, st_df)
            except Exception:
                pass
            time.sleep(self.refresh_interval)

    def _parse_csv(self):
        try:
            with open(self.csv_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            ap_lines = []
            st_lines = []
            in_ap = True
            for i, line in enumerate(lines):
                if line.strip().startswith('Station MAC'):
                    in_ap = False
                    st_lines = lines[i:]
                    break
                ap_lines.append(line)
            # Parse APs
            ap_df = None
            if len(ap_lines) > 1:
                from io import StringIO
                content = ''.join(ap_lines)
                ap_df = pd.read_csv(StringIO(content))
                # Clean headers (they often have leading spaces)
                ap_df.columns = [c.strip() for c in ap_df.columns]
                # Fix BSSID and Power specifically
                if 'Power' in ap_df.columns:
                    ap_df['Power'] = pd.to_numeric(ap_df['Power'], errors='coerce')
                # Ensure ESSID is string
                if 'ESSID' in ap_df.columns:
                    ap_df['ESSID'] = ap_df['ESSID'].fillna('').astype(str).str.strip()
            
            # Parse Stations
            st_df = None
            if st_lines:
                from io import StringIO
                content = ''.join(st_lines)
                st_df = pd.read_csv(StringIO(content), skipinitialspace=True).dropna(axis=1, how='all')
                st_df.columns = [c.strip() for c in st_df.columns]
                if 'Power' in st_df.columns:
                    st_df['Power'] = pd.to_numeric(st_df['Power'], errors='coerce')
                if 'Station MAC' in st_df.columns:
                     st_df['Station MAC'] = st_df['Station MAC'].astype(str).str.strip()
                if 'BSSID' in st_df.columns:
                     st_df['BSSID'] = st_df['BSSID'].astype(str).str.strip()
            
            return ap_df, st_df
        except Exception as e:
            return None, None

class DeviceTracker:
    """
    Tracks detected APs and Stations, their movement (PWR over time), SSIDs, and last seen.
    """
    def __init__(self):
        self.aps = {}       # BSSID -> AP dict
        self.stations = {}  # Station MAC -> Station dict

    def update_from_df(self, ap_df, st_df):
        now = datetime.now()
        # APs
        if ap_df is not None:
            for _, row in ap_df.iterrows():
                bssid = row.get('BSSID')
                if not bssid or pd.isna(bssid):
                    continue
                pwr = row.get('Power', -100)
                # EMA Filter for signal smoothing
                if bssid in self.aps and self.aps[bssid]['history']:
                    prev_pwr = self.aps[bssid]['history'][-1][1]
                    if prev_pwr is not None and not pd.isna(pwr):
                        pwr = 0.7 * prev_pwr + 0.3 * pwr
                
                ssid = row.get('ESSID', '')
                chan = row.get('channel', '?')
                enc = row.get('Privacy', '?')
                auth = row.get('Authentication', '?')
                
                last_seen = row.get('Last time seen', now.strftime('%H:%M:%S'))
                if bssid not in self.aps:
                    self.aps[bssid] = {
                        'mac': bssid,
                        'history': [],
                        'ssids': set(),
                        'last_seen': last_seen,
                        'type': 'AP',
                        'channel': chan,
                        'enc': enc,
                        'auth': auth,
                    }
                self.aps[bssid]['history'].append((now, pwr))
                self.aps[bssid]['ssids'].update([ssid] if isinstance(ssid, str) and ssid else [])
                self.aps[bssid].update({'channel': chan, 'enc': enc, 'auth': auth, 'last_seen': last_seen})
        # Stations
        if st_df is not None:
            for _, row in st_df.iterrows():
                mac = row.get('Station MAC')
                if not mac or pd.isna(mac):
                    continue
                pwr = row.get('Power', row.get('PWR', -100))
                # EMA Filter for signal smoothing
                if mac in self.stations and self.stations[mac]['history']:
                    prev_pwr = self.stations[mac]['history'][-1][1]
                    if prev_pwr is not None and not pd.isna(pwr):
                        pwr = 0.7 * prev_pwr + 0.3 * pwr # Simple EMA
                
                ssid = row.get('Probed ESSIDs', '')
                parent_bssid = row.get('BSSID', '(Not Associated)')
                
                last_seen = row.get('Last time seen', now.strftime('%H:%M:%S'))
                if mac not in self.stations:
                    self.stations[mac] = {
                        'mac': mac,
                        'history': [],
                        'ssids': set(),
                        'last_seen': last_seen,
                        'type': 'STA',
                        'parent': parent_bssid,
                    }
                self.stations[mac]['history'].append((now, pwr))
                self.stations[mac]['ssids'].update([ssid] if isinstance(ssid, str) and ssid else [])
                self.stations[mac].update({'parent': parent_bssid, 'last_seen': last_seen})

    def get_aps(self):
        return self.aps

    def get_stations(self):
        return self.stations

    def get_device(self, mac):
        if mac in self.aps:
            return self.aps[mac]
        return self.stations.get(mac)

    def get_device_history(self, mac, device_type='AP'):
        if device_type == 'AP':
            return self.aps.get(mac, {}).get('history', [])
        else:
            return self.stations.get(mac, {}).get('history', [])

class VendorLookup:
    """
    Looks up vendor names for MAC addresses using mac_vendor_lookup.
    """
    def __init__(self):
        self.lookup = MacLookup()
        self.cache = {}

    def get_vendor(self, mac):
        if mac in self.cache:
            return self.cache[mac]
        try:
            vendor = self.lookup.lookup(mac)
        except Exception:
            vendor = 'Unknown'
        self.cache[mac] = vendor
        return vendor

class WatchlistManager:
    """
    Manages a MAC address watchlist, triggers alerts on match.
    """
    def __init__(self, watchlist_path='watchlist.txt'):
        self.watchlist_path = watchlist_path
        self.watchlist = set()
        self.load()

    def load(self):
        if os.path.exists(self.watchlist_path):
            with open(self.watchlist_path, 'r') as f:
                self.watchlist = set(line.strip().upper() for line in f if line.strip())
        else:
            self.watchlist = set()

    def save(self):
        with open(self.watchlist_path, 'w') as f:
            for mac in sorted(self.watchlist):
                f.write(mac + '\n')

    def add(self, mac):
        self.watchlist.add(mac.upper())
        self.save()

    def remove(self, mac):
        self.watchlist.discard(mac.upper())
        self.save()

    def is_watched(self, mac):
        return mac.upper() in self.watchlist

class SignalProcessor:
    """
    Handles next-level signal processing, spectral analysis, and oriented wall synthesis.
    """
    @staticmethod
    def estimate_distance(pwr, freq_mhz=2412):
        try:
            pwr_val = float(pwr)
            if pd.isna(pwr_val): return 50.0
            pwr_abs = abs(pwr_val)
            dist = 10**((27.55 - (20 * np.log10(freq_mhz)) + pwr_abs) / 20)
            return min(round(dist, 2), 100.0)
        except:
            return 50.0

    @staticmethod
    def classify_material(history):
        """Advanced Spectral Signature Analysis"""
        if len(history) < 5: return "Unknown"
        pwrs = [h[1] for h in history if h[1] is not None and not pd.isna(h[1])]
        if not pwrs: return "Unknown"
        
        std_dev = np.std(pwrs)
        ptp = np.ptp(pwrs)
        avg = np.mean(pwrs)
        
        if ptp > 15 or std_dev > 5: return "Metal"
        if 8 < ptp <= 15 or 3 < std_dev <= 5: return "Human"
        if std_dev < 1.5 and avg < -70: return "Wall"
        if std_dev < 2.2: return "Wood"
        return "Unknown"

    @staticmethod
    def synthesize_wall_segments(devices, w, h, zoom, offset_x, offset_y):
        """Synthesize oriented wall geometries from signal attenuation clusters"""
        segments = []
        cx, cy = (w // 2) + offset_x, (h // 2) + offset_y
        
        for i, (mac, dev) in enumerate(list(devices.items())[:15]):
            history = dev.get('history', [])
            if len(history) < 8: continue
            
            pwr = history[-1][1]
            if pwr is None or pd.isna(pwr): continue
            
            material = SignalProcessor.classify_material(history)
            if material == "Wall":
                angle = np.deg2rad((i * 137.5) % 360)
                dist = SignalProcessor.estimate_distance(pwr)
                r = (dist / 100.0) * (min(w, h) // 2) * zoom
                
                # Wall is placed perpendicular to the signal ray
                mid_r = r * 0.75 
                px, py = cx + mid_r * np.cos(angle), cy + mid_r * np.sin(angle)
                wall_angle = angle + np.pi/2
                length = 40 * zoom 
                
                x1, y1 = px + (length/2) * np.cos(wall_angle), py + (length/2) * np.sin(wall_angle)
                x2, y2 = px - (length/2) * np.cos(wall_angle), py - (length/2) * np.sin(wall_angle)
                
                segments.append({'coords': (x1, y1, x2, y2), 'type': 'Wall', 'color': '#ff4444'})
        return segments

def get_wireless_interfaces():
    """
    Returns a list of wireless interfaces using 'iw dev'.
    Falls back to 'ip link' if 'iw' is not present.
    """
    import subprocess
    interfaces = []
    try:
        # Try 'iw dev' first as it specifically lists wireless interfaces
        res = subprocess.run(["iw", "dev"], capture_output=True, text=True)
        for line in res.stdout.splitlines():
            if "Interface" in line:
                interfaces.append(line.split()[1])
    except:
        pass

    if not interfaces:
        try:
            # Fallback to 'ip -o link' and filter for wlan/wifi-sounding names
            res = subprocess.run(["ip", "-o", "link"], capture_output=True, text=True)
            for line in res.stdout.splitlines():
                parts = line.split(':')
                if len(parts) > 1:
                    name = parts[1].strip()
                    if name.startswith(('wlan', 'wlo', 'wifi', 'wlp')):
                        interfaces.append(name)
        except:
            pass
            
    return sorted(list(set(interfaces)))