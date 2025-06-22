import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from backend import CSVWatcher, DeviceTracker, VendorLookup, WatchlistManager
import threading
import os
# --- New imports for plotting ---
import matplotlib
matplotlib.use('Agg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import numpy as np
import subprocess
import signal
import shutil

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# --- Neon/Glassmorphism Table Style Helper ---
def style_treeview(tree):
    style = ttk.Style(tree)
    style.theme_use('clam')
    style.configure("Treeview",
                    background="#181c24",
                    fieldbackground="#181c24",
                    foreground="#00ffe7",
                    rowheight=32,
                    font=("Consolas", 13),
                    borderwidth=0,
                    relief="flat")
    style.map("Treeview",
              background=[('selected', '#00ffe7')],
              foreground=[('selected', '#181c24')])
    style.configure("Treeview.Heading",
                    background="#10131a",
                    foreground="#00ffe7",
                    font=("Orbitron", 13, "bold"),
                    borderwidth=0)
    style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])

class GlassPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(corner_radius=20, fg_color=("#181c24", "#181c24"), border_width=2, border_color="#00ffe7")
        self._add_glassmorphism()

    def _add_glassmorphism(self):
        # Simulate glassmorphism with a semi-transparent overlay
        self.canvas = tk.Canvas(self, bg=self['bg'], highlightthickness=0)
        self.canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.canvas.create_rectangle(0, 0, 1000, 1000, fill='#1a1f2b', outline='', stipple='gray25')

class DeviceTable(ttk.Treeview):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self["columns"] = ("mac", "vendor", "pwr", "ssids", "last_seen")
        self.heading("#0", text="")
        self.column("#0", width=0, stretch=False)
        self.heading("mac", text="MAC Address")
        self.heading("vendor", text="Vendor")
        self.heading("pwr", text="PWR")
        self.heading("ssids", text="SSIDs")
        self.heading("last_seen", text="Last Seen")
        self.column("mac", width=180)
        self.column("vendor", width=140)
        self.column("pwr", width=60, anchor='center')
        self.column("ssids", width=320)
        self.column("last_seen", width=100, anchor='center')
        style_treeview(self)
        self.tag_configure('strong', background='#0fffc0')
        self.tag_configure('weak', background='#1a1f2b')
        self.tag_configure('medium', background='#00ffe7')  # removed alpha
        self.tag_configure('alert', background='#ff0055', foreground='#ffffff')

    def update_devices(self, devices, vendor_lookup, watchlist_mgr):
        self.delete(*self.get_children())
        for mac, dev in devices.items():
            # For APs, use correct columns
            pwr = dev['history'][-1][1] if dev['history'] else None
            try:
                pwr_val = int(pwr)
            except:
                pwr_val = -100
            # For APs, SSID is ESSID
            ssids = ', '.join([s for s in dev['ssids'] if s])
            vendor = vendor_lookup.get_vendor(mac)
            last_seen = dev.get('last_seen', '')
            if watchlist_mgr.is_watched(mac):
                tag = 'alert'
            elif pwr_val >= -50:
                tag = 'strong'
            elif pwr_val >= -70:
                tag = 'medium'
            else:
                tag = 'weak'
            self.insert('', 'end', values=(mac, vendor, pwr, ssids, last_seen), tags=(tag,))

class MovementGraphPanel(GlassPanel):
    def __init__(self, master, get_devices, get_device_history, **kwargs):
        super().__init__(master, **kwargs)
        self.get_devices = get_devices
        self.get_device_history = get_device_history
        self.selected_mac = None
        self._create_widgets()
        self._init_plot()

    def _create_widgets(self):
        self.mac_var = tk.StringVar()
        self.mac_dropdown = ttk.Combobox(self, textvariable=self.mac_var, font=("Consolas", 12), state="readonly")
        self.mac_dropdown.place(x=30, y=20, width=320)
        self.mac_dropdown.bind("<<ComboboxSelected>>", self._on_mac_selected)
        # Neon style
        self.mac_dropdown.configure(background="#10131a", foreground="#00ffe7")

    def _init_plot(self):
        self.fig, self.ax = plt.subplots(figsize=(5, 2.5), dpi=100)
        self.fig.patch.set_facecolor('#181c24')
        self.ax.set_facecolor('#10131a')
        self.ax.tick_params(colors='#00ffe7', labelsize=10)
        self.ax.spines['bottom'].set_color('#00ffe7')
        self.ax.spines['top'].set_color('#00ffe7')
        self.ax.spines['right'].set_color('#00ffe7')
        self.ax.spines['left'].set_color('#00ffe7')
        self.ax.set_title('Signal Strength (PWR) Over Time', color='#00ffe7', fontweight='bold', fontsize=13)
        self.ax.set_xlabel('Time', color='#00ffe7')
        self.ax.set_ylabel('PWR (dBm)', color='#00ffe7')
        self.line, = self.ax.plot([], [], color='#00ffe7', linewidth=2, marker='o', markerfacecolor='#00ffe7', markeredgewidth=0)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().place(x=30, y=60, width=440, height=280)
        self.fig.tight_layout()

    def update_mac_list(self):
        macs = list(self.get_devices().keys())
        self.mac_dropdown['values'] = macs
        if self.selected_mac not in macs:
            self.selected_mac = macs[0] if macs else None
            self.mac_var.set(self.selected_mac if self.selected_mac else "")
        self._update_plot()

    def _on_mac_selected(self, event=None):
        self.selected_mac = self.mac_var.get()
        self._update_plot()

    def _update_plot(self):
        if not self.selected_mac:
            self.line.set_data([], [])
            self.ax.relim()
            self.ax.autoscale_view()
            self.canvas.draw()
            return
        history = self.get_device_history(self.selected_mac)
        if not history:
            self.line.set_data([], [])
        else:
            times = [h[0].strftime('%H:%M:%S') for h in history]
            pwrs = [int(h[1]) if h[1] is not None and str(h[1]).lstrip('-').isdigit() else -100 for h in history]
            self.line.set_data(range(len(times)), pwrs)
            self.ax.set_xticks(range(len(times)))
            self.ax.set_xticklabels(times, rotation=45, color='#00ffe7')
            self.ax.set_ylim(min(pwrs + [-100]) - 5, max(pwrs + [-30]) + 5)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()

class GeoMapPanel(GlassPanel):
    def __init__(self, master, get_devices, get_ap_details=None, **kwargs):
        super().__init__(master, **kwargs)
        self.get_devices = get_devices
        self.get_ap_details = get_ap_details
        self.width = 480
        self.height = 340
        self.center = (self.width // 2, self.height // 2)
        self.radius_max = 140  # Max distance for weakest signal
        self.device_angles = {}  # MAC -> angle
        self.radar_angle = 0
        self.dot_positions = {}  # MAC -> (x, y, r)
        self._create_widgets()
        self.after(100, self._update_map)
        self.after(30, self._animate_radar)
        self.canvas.bind("<Button-1>", self._on_click)

    def _create_widgets(self):
        self.canvas = tk.Canvas(self, width=self.width, height=self.height, bg='#181c24', highlightthickness=0)
        self.canvas.place(x=10, y=40)
        self.canvas.create_oval(self.center[0]-self.radius_max-20, self.center[1]-self.radius_max-20,
                               self.center[0]+self.radius_max+20, self.center[1]+self.radius_max+20,
                               fill='#10131a', outline='#00ffe7', width=2, stipple='gray25')
        self.canvas.create_oval(self.center[0]-8, self.center[1]-8, self.center[0]+8, self.center[1]+8,
                               fill='#00ffe7', outline='')
        self.canvas.create_text(self.center[0], self.center[1]+18, text='Origin', fill='#00ffe7', font=("Consolas", 10, "bold"))

    def _update_map(self):
        self.canvas.delete('device')
        self.dot_positions = {}
        devices = self.get_devices()
        macs = list(devices.keys())
        n = len(macs)
        for i, mac in enumerate(macs):
            dev = devices[mac]
            pwr = dev['history'][-1][1] if dev['history'] else None
            try:
                pwr_val = int(pwr)
                unknown_pwr = False
            except:
                pwr_val = -60
                unknown_pwr = True
            r = self._pwr_to_radius(pwr_val)
            if mac not in self.device_angles:
                self.device_angles[mac] = 2 * np.pi * i / max(n, 1)
            angle = self.device_angles[mac]
            x = self.center[0] + r * np.cos(angle)
            y = self.center[1] + r * np.sin(angle)
            self._draw_neon_dot(x, y, mac, pwr if not unknown_pwr else "?", unknown_pwr)
            self.dot_positions[mac] = (x, y, 16)  # 16 is the outer dot radius
        self.after(1000, self._update_map)

    def _pwr_to_radius(self, pwr):
        pwr = max(-90, min(-30, pwr if pwr is not None else -90))
        return 20 + (self.radius_max - 20) * (abs(pwr + 30) / 60)

    def _draw_neon_dot(self, x, y, mac, pwr, unknown_pwr=False):
        colors = ["#00ffe7", "#00ffe7", "#00ffe7"] if not unknown_pwr else ["#ff00ff", "#ff00ff", "#ff00ff"]
        for r, color in zip([16, 12, 8], colors):
            self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=color, outline='', tags='device')
        self.canvas.create_text(x, y-18, text=mac, fill="#00ffe7" if not unknown_pwr else "#ff00ff", font=("Consolas", 9, "bold"), tags='device')
        self.canvas.create_text(x, y+14, text=f"{pwr} dBm", fill="#0fffc0" if not unknown_pwr else "#ff00ff", font=("Consolas", 8), tags='device')

    def _animate_radar(self):
        self.canvas.delete('radar_sweep')
        angle_rad = np.deg2rad(self.radar_angle)
        x2 = self.center[0] + (self.radius_max+20) * np.cos(angle_rad)
        y2 = self.center[1] + (self.radius_max+20) * np.sin(angle_rad)
        self.canvas.create_line(self.center[0], self.center[1], x2, y2, fill="#00ffe7", width=3, tags='radar_sweep')
        self.canvas.create_arc(self.center[0]-self.radius_max-20, self.center[1]-self.radius_max-20,
                              self.center[0]+self.radius_max+20, self.center[1]+self.radius_max+20,
                              start=self.radar_angle-10, extent=20, style='arc', outline="#00ffe7", width=6, tags='radar_sweep')
        self.radar_angle = (self.radar_angle + 2) % 360
        self.after(20, self._animate_radar)

    def _on_click(self, event):
        # Find which dot was clicked
        for mac, (x, y, r) in self.dot_positions.items():
            if (event.x - x)**2 + (event.y - y)**2 <= r**2:
                self._show_device_details(mac)
                break

    def _show_device_details(self, mac):
        if not self.get_ap_details:
            return
        details = self.get_ap_details(mac)
        if not details:
            show_error_popup("Device Details", f"No details found for {mac}")
            return
        popup = ctk.CTkToplevel(self)
        popup.title(f"Device Details: {mac}")
        popup.geometry("500x400")
        popup.configure(bg="#181c24")
        text = ""
        for k, v in details.items():
            text += f"{k}: {v}\n"
        label = ctk.CTkTextbox(popup, width=480, height=380, font=("Consolas", 13), fg_color="#181c24", text_color="#00ffe7")
        label.insert("1.0", text)
        label.configure(state="disabled")
        label.pack(padx=10, pady=10)

class MainApp(ctk.CTk):
    def __init__(self):
        # Check for airmon-ng and airodump-ng before starting
        for tool in ["airmon-ng", "airodump-ng"]:
            if shutil.which(tool) is None:
                show_error_popup("Missing Dependency", f"{tool} is not installed or not in PATH. Please install aircrack-ng suite before running this tool.")
                exit(1)
        super().__init__()
        self.title("WiFi CyberScan - Real-Time Wireless Analytics")
        self.geometry("1280x900")
        self.configure(bg="#10131a")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        # --- Backend ---
        self.device_tracker = DeviceTracker()
        self.vendor_lookup = VendorLookup()
        self.watchlist_mgr = WatchlistManager()
        self.csv_path = "probe_log-01.csv"  # Change as needed
        self.csv_watcher = CSVWatcher(self.csv_path, self.on_csv_update, refresh_interval=2)
        self._airodump_proc = None
        self.ap_df = None
        self.st_df = None
        self._create_layout()
        self._start_monitor_mode()
        self.csv_watcher.start()

    def _run_cmd(self, cmd, require_sudo=True):
        if require_sudo and os.geteuid() != 0:
            cmd = ["sudo"] + cmd
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            show_error_popup("Command Failed", f"{' '.join(cmd)}\n{e.stderr}")
            return None
        except Exception as e:
            show_error_popup("Command Error", str(e))
            return None

    def _start_monitor_mode(self):
        # 1. Kill conflicting processes
        self._run_cmd(["airmon-ng", "check", "kill"])
        # 2. Start monitor mode on wlan0
        self._run_cmd(["airmon-ng", "start", "wlan0"])
        # 3. Start airodump-ng as background process
        try:
            if os.geteuid() != 0:
                cmd = ["sudo", "airodump-ng", "--write", "probe_log", "--output-format", "csv", "--manufacturer", "wlan0mon"]
            else:
                cmd = ["airodump-ng", "--write", "probe_log", "--output-format", "csv", "--manufacturer", "wlan0mon"]
            self._airodump_proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
        except Exception as e:
            show_error_popup("Airodump-ng Error", str(e))

    def _create_layout(self):
        # Unified dashboard layout, professional alignment
        main_width = 1200
        main_height = 860
        padding = 30
        table_height = 280
        panel_height = 350
        half_width = (main_width - 3 * padding) // 2
        self.main_panel = GlassPanel(self, width=main_width, height=main_height)
        self.main_panel.place(x=padding, y=padding)
        # Device Table (top, full width)
        self.device_table = DeviceTable(self.main_panel)
        self.device_table.place(x=padding, y=padding, width=main_width - 2*padding, height=table_height)
        # Movement Graph (bottom left)
        self.movement_panel = MovementGraphPanel(self.main_panel, self._get_current_devices, self._get_current_device_history, width=half_width, height=panel_height)
        self.movement_panel.place(x=padding, y=table_height + 2*padding)
        # Geo Map (bottom right)
        self.map_panel = GeoMapPanel(self.main_panel, self._get_current_devices, get_ap_details=self._get_ap_details, width=half_width, height=panel_height)
        self.map_panel.place(x=half_width + 2*padding, y=table_height + 2*padding)

    def _get_current_devices(self):
        return self.device_tracker.get_aps()

    def _get_current_device_history(self, mac):
        return self.device_tracker.get_device_history(mac, device_type='AP')

    def _get_ap_details(self, mac):
        if self.ap_df is not None and mac in self.ap_df['BSSID'].values:
            row = self.ap_df[self.ap_df['BSSID'] == mac].iloc[0]
            return {col: row[col] for col in self.ap_df.columns}
        return None

    def on_csv_update(self, ap_df, st_df):
        self.ap_df = ap_df
        self.st_df = st_df
        self.device_tracker.update_from_df(ap_df, st_df)
        self.after(0, self._update_all_views)

    def _update_all_views(self):
        devices = self._get_current_devices()
        self.device_table.update_devices(devices, self.vendor_lookup, self.watchlist_mgr)
        self.movement_panel.update_mac_list()
        # Map panel auto-updates itself

    def on_closing(self):
        self._stop_monitor_mode()
        self.destroy()

    def _stop_monitor_mode(self):
        # Kill airodump-ng process
        if self._airodump_proc:
            try:
                os.killpg(os.getpgid(self._airodump_proc.pid), signal.SIGTERM)
            except Exception as e:
                show_error_popup("Airodump-ng Kill Error", str(e))
        # Restart NetworkManager
        self._run_cmd(["systemctl", "start", "NetworkManager"])

if __name__ == "__main__":
    app = MainApp()
    app.mainloop() 