import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import matplotlib
matplotlib.use('Agg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from datetime import datetime
from widgets import GlassPanel, NeonLabel
from backend import SignalProcessor

def style_treeview(tree):
    style = ttk.Style(tree.master)
    style.theme_use("clam")
    style.configure("Treeview",
                    background="#10131a",
                    foreground="#00ffe7",
                    fieldbackground="#10131a",
                    rowheight=35,
                    font=("Consolas", 13),
                    borderwidth=0,
                    relief="flat")
    style.map("Treeview",
              background=[('selected', '#00ffe7')],
              foreground=[('selected', '#181c24')])
    style.configure("Treeview.Heading",
                    background="#10131a",
                    foreground="#00ffe7",
                    font=("Orbitron", 11, "bold"),
                    borderwidth=0)
    style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])

class DeviceTable(ttk.Treeview):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self["columns"] = ("mac", "vendor", "pwr", "dist", "ssids", "last_seen")
        self.heading("#0", text="", anchor="w")
        self.column("#0", width=1, stretch=tk.NO)
        self.heading("mac", text="MAC Address 🌐")
        self.column("mac", width=180)
        self.heading("vendor", text="Vendor")
        self.column("vendor", width=160)
        self.heading("pwr", text="PWR 📶")
        self.column("pwr", width=100)
        self.heading("dist", text="DIST (m) 📡")
        self.column("dist", width=120)
        self.heading("ssids", text="SSIDs 🔒")
        self.column("ssids", width=220)
        self.heading("last_seen", text="Last Seen 🛰️")
        self.column("last_seen", width=120, anchor='center')
        style_treeview(self)
        
        self.tag_configure('alert', foreground='#ff0055', font=("Consolas", 10, "bold"))
        self.tag_configure('strong', foreground='#00ff88')
        self.tag_configure('medium', foreground='#ffff99')
        self.tag_configure('weak', foreground='#708090')
        
        self.bind("<<TreeviewSelect>>", self._on_select)

    def update_devices(self, devices, vendor_lookup, watchlist_mgr):
        self.delete(*self.get_children())
        for mac, dev in devices.items():
            history = dev.get('history', [])
            pwr_val = history[-1][1] if history else None
            if pwr_val is not None and not pd.isna(pwr_val):
                bars = "▮" * min(5, max(1, int((100+pwr_val)//20)))
                pwr_str = f"{int(pwr_val)}dBm {bars.ljust(5, '▯')}"
            else:
                pwr_str = "?"
            
            ssids_display = ", ".join(list(dev.get('ssids', set()))) or "(Unknown)"
            vendor = vendor_lookup.get_vendor(mac)
            last_seen = dev.get('last_seen', '')
            
            tag = 'weak'
            if watchlist_mgr.is_watched(mac): tag = 'alert'
            elif pwr_val is not None and not pd.isna(pwr_val):
                if pwr_val >= -50: tag = 'strong'
                elif pwr_val >= -75: tag = 'medium'

            dist = SignalProcessor.estimate_distance(pwr_val)
            dist_str = f"{dist}m"
            self.insert('', 'end', values=(mac, vendor, pwr_str, dist_str, ssids_display, last_seen), tags=(tag,))

    def _on_select(self, event):
        selection = self.selection()
        if not selection: return
        item = selection[0]
        mac = self.item(item, 'values')[0]
        self.app._show_device_details(mac)

class MovementGraphPanel(GlassPanel):
    def __init__(self, master, app, get_devices, get_device_history, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.get_devices = get_devices
        self.get_device_history = get_device_history
        NeonLabel(self, text="Signal Strength (PWR) Over Time").pack(pady=(10, 0), anchor="nw", padx=20)
        self._init_plot()

    def _init_plot(self):
        self.fig, self.ax = plt.subplots(figsize=(5, 3), dpi=100)
        self.fig.patch.set_facecolor('#10131a')
        self.ax.set_facecolor('none')
        self.ax.tick_params(colors='#00ffe7', labelsize=8)
        self.ax.grid(True, color='#00ffe7', alpha=0.1, linestyle='--')
        for spine in self.ax.spines.values():
            spine.set_color('#00ffe7')
            spine.set_alpha(0.3)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def update_mac_list(self):
        self._update_plot()

    def _update_plot(self):
        if not self.winfo_exists() or self.app._is_closing: return
        self.ax.clear()
        self.ax.set_facecolor('none')
        self.ax.grid(True, color='#00ffe7', alpha=0.1)
        devices = self.get_devices()
        colors = ['#00ffe7', '#ff00ff', '#f0f000', '#00ff00', '#ff0000']
        for i, (mac, dev) in enumerate(list(devices.items())[:5]):
            history = self.get_device_history(mac)
            if not history: continue
            pwrs = [float(h[1]) if h[1] is not None and not pd.isna(h[1]) else -100 for h in history]
            x = range(len(pwrs))
            self.ax.plot(x, pwrs, color=colors[i % len(colors)], linewidth=2, label=mac[:8], alpha=0.8)
        self.ax.set_ylim(-105, -25)
        self.ax.legend(facecolor='#10131a', edgecolor='#00ffe7', labelcolor='#00ffe7', fontsize=7, loc='upper right')
        self.canvas.draw()

class TacticalRadarPanel(GlassPanel):
    def __init__(self, master, app, get_devices, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.get_devices = get_devices
        self.canvas = tk.Canvas(self, bg='#10131a', highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=2, pady=2)
        ctk.CTkButton(self, text="⛶", width=30, height=30, fg_color="transparent", border_width=1, border_color="#00ffe7", command=self._on_popout).place(relx=1, rely=0, x=-40, y=10)
        
        # Highlighting state
        self.highlight_color = "#ffff00" # Bright yellow for selection
        self._update_radar()

    def _draw_compass(self, cx, cy, r):
        self.canvas.create_text(cx, cy-r-10, text="N", fill="#ff0055", font=("Orbitron", 8, "bold"), tags='nodes')
        self.canvas.create_text(cx, cy+r+10, text="S", fill="#00ffe7", font=("Orbitron", 8), tags='nodes')
        self.canvas.create_text(cx+r+10, cy, text="E", fill="#00ffe7", font=("Orbitron", 8), tags='nodes')
        self.canvas.create_text(cx-r-10, cy, text="W", fill="#00ffe7", font=("Orbitron", 8), tags='nodes')

    def _update_radar(self):
        if not self.winfo_exists() or self.app._is_closing: return
        self.canvas.delete('nodes')
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w <= 1: self.after(100, self._update_radar); return
        cx, cy, max_r = w//2, h//2, min(w, h)//2.5
        for r in [max_r*0.3, max_r*0.6, max_r]: self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline='#00ffe7', width=1, dash=(5,5), tags='nodes')
        self._draw_compass(cx, cy, max_r)
        devices = self.get_devices()
        for i, (mac, dev) in enumerate(list(devices.items())[:8]):
            pwr = dev.get('history', [[0,-100]])[-1][1]
            dist = SignalProcessor.estimate_distance(pwr)
            angle = np.deg2rad(i * 45)
            r = min(max_r, (dist/100)*max_r)
            x, y = cx + r*np.cos(angle), cy + r*np.sin(angle)
            
            is_selected = (mac == self.app.selected_mac)
            color = self.highlight_color if is_selected else "#00ffe7"
            width = 3 if is_selected else 1
            
            self.canvas.create_line(cx, cy, x, y, fill=color, width=width, dash=(2,2), tags='nodes')
            self.canvas.create_oval(x-6 if is_selected else x-5, y-6 if is_selected else y-5, 
                                   x+6 if is_selected else x+5, y+6 if is_selected else y+5, 
                                   fill=color, outline='', tags='nodes')
            self.canvas.create_text(x, y-15, text=f"D-{i}", fill=color, font=("Consolas", 7, "bold" if is_selected else "normal"), tags='nodes')
        self.after(2000, self._update_radar)

    def _on_popout(self):
        popout = ctk.CTkToplevel(self.app)
        popout.title("TACTICAL RADAR - FULLSCREEN")
        popout.geometry("900x800")
        TacticalRadarPanel(popout, app=self.app, get_devices=self.get_devices).pack(fill="both", expand=True, padx=10, pady=10)

class MiniMapPanel(TacticalRadarPanel):
    def __init__(self, master, app, get_devices, **kwargs):
        super().__init__(master, app, get_devices, **kwargs)
        self.zoom = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self._drag_data = {"x": 0, "y": 0}
        self._bind_interactions()

    def _bind_interactions(self):
        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag_motion)
        self.canvas.bind("<MouseWheel>", self._on_zoom)
        # Linux scroll support
        self.canvas.bind("<Button-4>", self._on_zoom)
        self.canvas.bind("<Button-5>", self._on_zoom)

    def _on_drag_start(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _on_drag_motion(self, event):
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        self.offset_x += dx
        self.offset_y += dy
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        self._update_radar() # Force immediate redraw

    def _on_zoom(self, event):
        if event.num == 4 or event.delta > 0:
            self.zoom *= 1.1
        elif event.num == 5 or event.delta < 0:
            self.zoom /= 1.1
        self.zoom = max(0.1, min(self.zoom, 10.0))
        self._update_radar()

    def _create_widgets(self):
        pass # Already using parent's canvas

    def _update_radar(self):
        if not self.winfo_exists() or self.app._is_closing: return
        self.canvas.delete('nodes')
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w <= 1: self.after(500, self._update_radar); return
        
        cx, cy = (w // 2) + self.offset_x, (h // 2) + self.offset_y
        grid_color = '#0e3b3a'
        
        # Apply zoom to grid step
        step = int(30 * self.zoom)
        if step > 5:
            start_x = cx % step
            for x in range(start_x, w, step): self.canvas.create_line(x, 0, x, h, fill=grid_color, width=1, dash=(1,5), tags='nodes')
            start_y = cy % step
            for y in range(start_y, h, step): self.canvas.create_line(0, y, w, y, fill=grid_color, width=1, dash=(1,5), tags='nodes')
        
        self.canvas.create_text(20, 20, text=f"ZOOM: {self.zoom:.1f}x", fill="#0fffc0", font=("Orbitron", 8), tags='nodes')
        self.canvas.create_text(20, 40, text="DRAG TO PAN", fill="#0fffc0", font=("Orbitron", 7), tags='nodes')

        devices = self.get_devices()
        
        # 1. Synthesize and Draw Walls
        wall_segments = SignalProcessor.synthesize_wall_segments(devices, w, h, self.zoom, self.offset_x, self.offset_y)
        for segment in wall_segments:
            x1, y1, x2, y2 = segment['coords']
            self.canvas.create_line(x1, y1, x2, y2, fill=segment['color'], width=3, capstyle='round', tags='nodes')

        # 2. Draw Origin (Operator)
        self.canvas.create_rectangle(cx-5, cy-5, cx+5, cy+5, fill='#0fffc0', outline='', tags='nodes')
        self.canvas.create_text(cx, cy+15, text="YOU", fill="#0fffc0", font=("Orbitron", 7), tags='nodes')
        
        for i, (mac, dev) in enumerate(list(devices.items())[:15]):
            history = dev.get('history', [])
            pwr = history[-1][1] if history else -100
            dist = SignalProcessor.estimate_distance(pwr)
            material = SignalProcessor.classify_material(history)
            
            is_selected = (mac == self.app.selected_mac)
            
            angle = np.deg2rad((i * 137.5) % 360)
            r = (dist / 100.0) * (min(w, h) // 2) * self.zoom
            
            x = cx + r * np.cos(angle)
            y = cy + r * np.sin(angle)
            
            base_color = {'Metal': '#ff0055', 'Wood': '#cc9966', 'Human': '#00ff88', 'Wall': '#666666'}.get(material, '#00ffe7')
            color = self.highlight_color if is_selected else base_color
            
            # Draw highlight pulse if selected
            if is_selected:
                self.canvas.create_oval(x-10, y-10, x+10, y+10, outline=color, width=2, tags='nodes')

            self.canvas.create_rectangle(x-4, y-4, x+4, y+4, fill='#10131a', outline=color, width=2 if is_selected else 1, tags='nodes')
            self.canvas.create_text(x, y-12, text=f"{material[:2]}", fill=color, font=("Consolas", 7, "bold" if is_selected else "normal"), tags='nodes')
        
        # Slower auto-refresh if not dragging
        self.after(2000, self._update_radar)

    def _on_popout(self):
        popout = ctk.CTkToplevel(self.app)
        popout.title("DYNAMIC FLOORPLAN - FULLSCREEN")
        popout.geometry("900x800")
        MiniMapPanel(popout, app=self.app, get_devices=self.get_devices).pack(fill="both", expand=True, padx=10, pady=10)
