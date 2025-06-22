import pandas as pd
import threading
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from mac_vendor_lookup import MacLookup
import os
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
                mtime = os.path.getmtime(self.csv_path)
                if mtime != self.last_mtime:
                    self.last_mtime = mtime
                    ap_df, st_df = self._parse_csv()
                    if ap_df is not None or st_df is not None:
                        self.on_update(ap_df, st_df)
            except Exception as e:
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
                ap_df = pd.read_csv(StringIO(''.join(ap_lines)))
            # Parse Stations
            st_df = None
            if st_lines:
                from io import StringIO
                st_df = pd.read_csv(StringIO(''.join(st_lines)))
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
                pwr = row.get('Power', None)
                ssid = row.get('ESSID', '')
                last_seen = row.get('Last time seen', now.strftime('%H:%M:%S'))
                if bssid not in self.aps:
                    self.aps[bssid] = {
                        'mac': bssid,
                        'history': [],
                        'ssids': set(),
                        'last_seen': last_seen,
                        'type': 'AP',
                    }
                self.aps[bssid]['history'].append((now, pwr))
                self.aps[bssid]['ssids'].update([ssid] if isinstance(ssid, str) else [])
                self.aps[bssid]['last_seen'] = last_seen
        # Stations
        if st_df is not None:
            for _, row in st_df.iterrows():
                mac = row.get('Station MAC')
                if not mac or pd.isna(mac):
                    continue
                pwr = row.get('Power', row.get('PWR', None))
                ssid = row.get('Probed ESSIDs', '')
                last_seen = row.get('Last time seen', now.strftime('%H:%M:%S'))
                if mac not in self.stations:
                    self.stations[mac] = {
                        'mac': mac,
                        'history': [],
                        'ssids': set(),
                        'last_seen': last_seen,
                        'type': 'Station',
                    }
                self.stations[mac]['history'].append((now, pwr))
                self.stations[mac]['ssids'].update([ssid] if isinstance(ssid, str) else [])
                self.stations[mac]['last_seen'] = last_seen

    def get_aps(self):
        return self.aps

    def get_stations(self):
        return self.stations

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