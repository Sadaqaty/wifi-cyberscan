import customtkinter as ctk
import tkinter as tk
import os
import signal
import subprocess
import threading
from datetime import datetime
import pandas as pd

from widgets import SetupWizard, NeonLabel, GlassPanel, show_error_popup
from viz_panels import DeviceTable, MovementGraphPanel, TacticalRadarPanel, MiniMapPanel
from backend import CSVWatcher, DeviceTracker, VendorLookup, WatchlistManager, get_wireless_interfaces

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class MainApp(ctk.CTk):
    def __init__(self, interface, operator):
        super().__init__()
        self.interface = interface
        self.operator = operator
        self.title(f"WiFi CyberScan // {operator} // {interface}")
        self.geometry("1280x720")
        self.configure(fg_color="#10131a")
        
        # Backend Logic
        self.device_tracker = DeviceTracker()
        self.vendor_lookup = VendorLookup()
        self.watchlist_mgr = WatchlistManager()
        self.csv_path = "scan-01.csv"
        self._airodump_proc = None
        self.selected_mac = None
        self._is_closing = False
        self._after_ids = []
        self._check_root()
        self._create_layout()
        self._start_scan()
        self._update_clock()
        self._flash_indicator()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _check_root(self):
        if os.geteuid() != 0:
            show_error_popup("PRIVILEGE ERROR", "This application requires root privileges for WiFi scanning.\nPlease run with 'sudo python3 main.py'")

    def _create_layout(self):
        # 1. Header
        self.header = tk.Frame(self, bg="#10131a", height=50)
        self.header.pack(fill="x", side="top", pady=5)
        
        self.title_lbl = ctk.CTkLabel(self.header, text="WIFI CYBERSCAN // REAL-TIME TERMINAL", font=("Orbitron", 14, "bold"), text_color="#00ffe7")
        self.title_lbl.pack(side="left", padx=20)
        
        self.scan_indicator = ctk.CTkLabel(self.header, text="● SCANNING", font=("Orbitron", 10), text_color="#ff0055")
        self.scan_indicator.pack(side="left", padx=10)
        
        self.status_bar = ctk.CTkLabel(self.header, text=f"OPERATOR: {self.operator} | INTERFACE: {self.interface}", font=("Consolas", 10), text_color="#0fffc0")
        self.status_bar.pack(side="right", padx=20)
        
        self.clock_lbl = ctk.CTkLabel(self.header, text="", font=("Consolas", 10), text_color="#0fffc0")
        self.clock_lbl.pack(side="right", padx=10)

        # Main Viewport
        self.viewport = ctk.CTkFrame(self, fg_color="transparent")
        self.viewport.pack(fill="both", expand=True, padx=10, pady=5)

        # 2. Table (Top Row)
        self.table_panel = GlassPanel(self.viewport, height=250)
        self.table_panel.pack(fill="x", side="top", pady=5)
        self.device_table = DeviceTable(self.table_panel, app=self)
        self.device_table.pack(fill="both", expand=True, padx=10, pady=10)

        # 3. Middle Section (Graph & Radar)
        self.mid_frame = ctk.CTkFrame(self.viewport, fg_color="transparent")
        self.mid_frame.pack(fill="both", expand=True, side="top", pady=5)
        
        self.graph_panel = MovementGraphPanel(self.mid_frame, app=self, get_devices=self._get_current_devices, get_device_history=self._get_current_device_history, width=700)
        self.graph_panel.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        self.radar_panel = TacticalRadarPanel(self.mid_frame, app=self, get_devices=self._get_current_devices, width=400)
        self.radar_panel.pack(side="right", fill="both", expand=True)

        # 4. Bottom Section (Details, Map, Filters, Log)
        self.bottom_frame = ctk.CTkFrame(self.viewport, fg_color="transparent")
        self.bottom_frame.pack(fill="x", side="bottom", pady=5)

        # 4.1 Device Details
        self.detail_panel = GlassPanel(self.bottom_frame, width=300, height=200)
        self.detail_panel.pack(side="left", fill="both", expand=True, padx=5, pady=(5, 10))
        NeonLabel(self.detail_panel, text="DEVICE DETAIL").pack(pady=5)
        self.detail_text = ctk.CTkTextbox(self.detail_panel, fg_color="transparent", font=("Consolas", 11), text_color="#0fffc0")
        self.detail_text.pack(fill="both", expand=True, padx=10, pady=5)

        # 4.2 Mini-Map
        self.mini_map_panel = MiniMapPanel(self.bottom_frame, app=self, get_devices=self._get_current_devices, width=262, height=190)
        self.mini_map_panel.pack(side="left", fill="both", expand=True, padx=5, pady=(5, 10))
        NeonLabel(self.mini_map_panel, text="SIG-MINI-MAP").place(x=10, y=5)

        # 4.3 Filters
        self.filter_panel = GlassPanel(self.bottom_frame, width=300, height=200)
        self.filter_panel.pack(side="left", fill="both", expand=True, padx=5, pady=(5, 10))
        NeonLabel(self.filter_panel, text="SCAN FILTERS").pack(pady=5)
        
        self.f_wpa2 = ctk.CTkCheckBox(self.filter_panel, text="WPA2 Only", font=("Consolas", 10))
        self.f_wpa2.pack(pady=2)
        self.f_open = ctk.CTkCheckBox(self.filter_panel, text="Open Only", font=("Consolas", 10))
        self.f_open.pack(pady=2)
        
        self.f_mobile = ctk.CTkCheckBox(self.filter_panel, text="Mobile/Client Only", font=("Consolas", 10), text_color="#0fffc0")
        self.f_mobile.pack(pady=2)
        
        self.filter_slider = ctk.CTkSlider(self.filter_panel, from_=-100, to=-30)
        self.filter_slider.set(-100)
        self.filter_slider.pack(pady=10, side="top", padx=10)
        ctk.CTkButton(self.filter_panel, text="FORCE UPDATE", height=28, fg_color="#00ffe7", text_color="#10131a", command=self._update_all_views).pack(pady=5)

        # 4.4 Data Log
        self.log_panel = GlassPanel(self.bottom_frame, width=300, height=200)
        self.log_panel.pack(side="left", fill="both", expand=True, padx=5, pady=(5, 10))
        NeonLabel(self.log_panel, text="DATA LOG").pack(pady=5)
        self.log_box = ctk.CTkTextbox(self.log_panel, font=("Consolas", 9), fg_color="transparent", text_color="#00ffe7")
        self.log_box.pack(fill="both", expand=True, padx=10, pady=5)

    def _start_scan(self):
        if self._is_closing: return
        # Clean up old scan...
        # Clean up old scan files more aggressively
        for f in os.listdir("."):
            if f.startswith("scan-"):
                try: os.remove(f)
                except: pass

        try:
            # Log airodump output for debugging
            self.error_log = open("airodump.log", "w")
            # Upgrade to multi-band (abg) for 5GHz support
            cmd = ["sudo", "airodump-ng", "--write", "scan", "--output-format", "csv", "--band", "abg", self.interface]
            self._airodump_proc = subprocess.Popen(cmd, stdout=self.error_log, stderr=self.error_log, preexec_fn=os.setsid)
            # Give it a second to create the file
            self.after(2000, self._start_watcher)
        except Exception as e:
            self._log_event(f"ERROR: Failed to start airodump: {e}")

    def _start_watcher(self, retries=5):
        if self._is_closing: return
        if not os.path.exists(self.csv_path):
            # Try to find any scan-*.csv if airodump named it differently
            scans = sorted([f for f in os.listdir(".") if f.startswith("scan-") and f.endswith(".csv")])
            if scans:
                self.csv_path = scans[0]
                self._log_event(f"RECOVERY: Found {self.csv_path}")
            elif retries > 0:
                self._log_event(f"WAITING FOR DATA... ({retries})")
                self.after(2000, lambda: self._start_watcher(retries - 1))
                return
            else:
                self._log_event(f"ERROR: {self.csv_path} not found. Check airodump.log or run as sudo.")
                return

        self.watcher = CSVWatcher(self.csv_path, self.on_csv_update)
        self.watcher.start()
        self._log_event(f"Monitoring: {self.csv_path}")

    def _update_clock(self):
        if self._is_closing: return
        self.clock_lbl.configure(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self._after_ids.append(self.after(1000, self._update_clock))

    def _get_filtered_devices(self):
        merged = {**self.device_tracker.get_aps(), **self.device_tracker.get_stations()}
        filtered = {}
        min_pwr = self.filter_slider.get()
        for mac, dev in merged.items():
            pwr = dev.get('history', [[0,-100]])[-1][1]
            if pwr < min_pwr: continue
            if self.f_wpa2.get() and "WPA2" not in str(dev.get('enc', '')): continue
            if self.f_open.get() and "OPN" not in str(dev.get('enc', '')): continue
            if self.f_mobile.get() and dev.get('type') != 'STA': continue
            filtered[mac] = dev
        return filtered

    def _get_current_devices(self):
        return self._get_filtered_devices()

    def _get_current_device_history(self, mac):
        dev = self.device_tracker.get_device(mac)
        dtype = dev.get('type', 'AP') if dev else 'AP'
        return self.device_tracker.get_device_history(mac, device_type=dtype)

    def on_csv_update(self, ap_df, st_df):
        self.device_tracker.update_from_df(ap_df, st_df)
        self.after(0, self._update_all_views)

    def _update_all_views(self):
        devices = self._get_current_devices()
        self.device_table.update_devices(devices, self.vendor_lookup, self.watchlist_mgr)
        self.graph_panel.update_mac_list()

    def _show_device_details(self, mac):
        self.selected_mac = mac
        # Trigger immediate map redraw for responsive feedback
        if hasattr(self, 'radar_panel'): self.radar_panel._update_radar()
        if hasattr(self, 'mini_map_panel'): self.mini_map_panel._update_radar()
        
        dev = self.device_tracker.get_device(mac)
        if not dev: return
        details = f"--- DEVICE ANALYSIS REPORT ---\nID: {mac}\nTYPE: {dev.get('type', 'Unknown')}\n"
        details += f"VENDOR: {self.vendor_lookup.get_vendor(mac)}\n"
        details += f"LAST SEEN: {dev.get('last_seen', '?')}\n"
        details += f"DETECTED SSIDs: {', '.join(dev.get('ssids', [])) or 'None'}\n"
        details += f"SENSING STATUS: PROBING...\n"
        
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", details)
        self.detail_text.configure(state="disabled")

    def _log_event(self, message):
        self.log_box.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_box.see("end")

    def _flash_indicator(self):
        if self._is_closing: return
        c = self.scan_indicator.cget("text_color")
        self.scan_indicator.configure(text_color="#10131a" if c == "#ff0055" else "#ff0055")
        self._after_ids.append(self.after(500, self._flash_indicator))

    def on_closing(self):
        self._is_closing = True
        # Cancel all pending callbacks
        for aid in self._after_ids:
            try: self.after_cancel(aid)
            except: pass
        
        if self._airodump_proc:
            try: 
                # Kill the whole process group
                os.killpg(os.getpgid(self._airodump_proc.pid), signal.SIGTERM)
            except: pass
        if hasattr(self, 'error_log'):
            try: self.error_log.close()
            except: pass
        self.destroy()

def main():
    ifaces = get_wireless_interfaces()
    if not ifaces:
        print("Error: No wireless interfaces detected.")
        return
    
    def start_app(iface, op):
        app = MainApp(iface, op)
        app.mainloop()

    wizard = SetupWizard(start_app, ifaces)
    wizard.mainloop()

if __name__ == "__main__":
    main()