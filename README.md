# WiFi CyberScan (Next-Gen)

A stunning, real-time Python GUI for Wi-Fi analytics and environment mapping. Highly modular, tactical, and built for advanced signal research. Visualize nearby wireless devices, access points, and physical obstructions with a high-fidelity cyberpunk dashboard.

![Cyber-Scan](/assets/image-v2.0.png)

---

## 🚀 "Next-Level" Features

### 📡 Advanced Signal Sensing

- **Wall Geometry Synthesis**: Automatically calculates and draws oriented wall segments (red) based on path attenuation clusters.
- **Spectral Material Analysis**: Differentiates between **Metal**, **Concrete Wall**, **Human Presence**, and **Wood** using signal jitter and spectral signature analysis.
- **Multi-Band Client Detection**: Scans across **2.4GHz and 5GHz** (`--band abg`) to capture modern iPhones, Androids, and laptops.
- **Unassociated Tracking**: Intercepts probe requests from devices searching for WiFi, even if they aren't connected.

### 🗺️ Interactive Tactical Maps

- **2D Floorplan (Pan & Zoom)**: Google Maps-style navigation. Click and drag to pan, scroll to zoom into specific signal zones.
- **Dynamic Selection Highlighting**: Selected devices glow and pulse on all maps for instant recognition.
- **Tactical Radar**: 360-degree spatial radar with distance estimation and material labels.

### 🛠️ Professional UI & Architecture

- **Modular Refactor**: Decoupled `backend.py`, `viz_panels.py`, `widgets.py`, and `main.py` for maximum performance and stability.
- **Advanced Filtering**: Isolate **Mobile Devices Only**, filter by Signal Floor (dBm), or security type (WPA2/Open).
- **Interface Wizard**: Built-in monitor-mode selection and automated `airodump-ng` lifecycle management.
- **Zero-Error Engineering**: Guarded callbacks and hardened shutdown logic for a clean terminal exit every time.

---

## 📋 Requirements

- Python 3.8+
- Linux (Kali, OS, Ubuntu/Debian)
- [aircrack-ng](https://www.aircrack-ng.org/) suite installed.
- WiFi Adapter supporting **Monitor Mode**.
- Root privileges.

---

## ⚙️ Installation & Usage

1. **Clone & Setup Environment**:

```bash
git clone https://github.com/sadaqaty/wifi-cyberscan.git
cd wifi-cyberscan
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Run as Root**:

```bash
sudo ./venv/bin/python3 main.py
```

3. **Operation**:
   - Select your wireless interface when prompted.
   - Use the **SCAN FILTERS** to isolate specific device types.
   - Click any row in the table to generate a **Device Analysis Report** and highlight its position on the map.

---

## 🚦 Security & Disclaimer

- **Root is strictly required** for raw socket access and monitor mode.
- Use this tool ONLY on networks and environments where you have explicit authorization.
- The author is not responsible for any misuse of this analytical tool.

---

## 💎 Credits

- **Engine**: [airodump-ng](https://www.aircrack-ng.org/)
- **Graphics**: [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) & Matplotlib
- **Logic**: Built with agentic AI precision for professional signal monitoring.
- **Author**: [Sadaqaty](https://github.com/Sadaqaty)
