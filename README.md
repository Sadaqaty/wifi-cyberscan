# WiFi CyberScan

A stunning, real-time Python GUI for Wi-Fi probe/AP analytics, built for hackers, researchers, and enthusiasts. Visualize nearby wireless devices, access points, and probe requests with a cyberpunk dashboard, live radar, and animated analytics.

---

## Features

- **Real-Time Device Table:**
  - MAC, Vendor, Power, SSIDs, Last Seen
- **Animated Movement Graph:**
  - Signal strength (PWR) over time for each device
- **Live Geo Mapping:**
  - Radar-style map with neon dots and animated sweep
  - Click any dot for full device details (BSSID, ESSID, channel, etc.)
- **Auto Alerts:**
  - Watchlist support (highlighted in table)
- **Beautiful UI:**
  - Cyberpunk dark theme, neon accents, glassmorphism
  - Responsive, professional layout
- **Robust Backend:**
  - Live parsing of airodump-ng CSV logs
  - Handles missing data, errors, and tool checks

---

## Screenshots

![Cyber-Scan](/assets/Image.jpeg)

---

## Requirements

- Python 3.8+
- Linux (tested on Ubuntu/Debian)
- [aircrack-ng](https://www.aircrack-ng.org/) tools (`airmon-ng`, `airodump-ng`)
- Root privileges (for monitor mode and packet capture)

**Python packages:**
- customtkinter
- pandas
- mac_vendor_lookup
- matplotlib
- numpy
- Pillow
- watchdog
- sounddevice
- (see `requirements.txt`)

---

## Installation

1. **Clone the repo:**
```sh
git clone https://github.com/sadaqaty/wifi-cyberscan.git
cd wifi-cyberscan
```
2. **Install dependencies:**
```sh
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```
3. **Install aircrack-ng:**
```sh
sudo apt install aircrack-ng
```

---

## Usage

1. **Run the app as root (required for monitor mode):**
```sh
sudo env "PATH=$PATH" ./env/bin/python main.py
```
2. **The app will:**
   - Check for `airmon-ng` and `airodump-ng`.
   - Start monitor mode on `wlan0` and launch airodump-ng.
   - Parse and visualize live Wi-Fi data from `probe_log-01.csv`.

3. **Click any device dot on the radar to see full details.**

---

## Permissions & Security
- **Root is required** to enable monitor mode and capture packets.
- The app will kill conflicting network processes and restart NetworkManager on exit.
- Use in a legal and responsible manner.

---

## Troubleshooting
- **Missing airmon-ng/airodump-ng:** Install `aircrack-ng` and ensure it's in your PATH.
- **No devices shown:** Ensure your Wi-Fi adapter supports monitor mode and is not blocked.
- **Permission errors:** Always run as root (`sudo`).
- **UI glitches:** Use a modern Linux distro and Python 3.8+.

---

## Credits
- UI: [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
- Wi-Fi tools: [aircrack-ng](https://www.aircrack-ng.org/)
- Icons: [Font Awesome](https://fontawesome.com/) (if used)
- Author: [Sadaqaty](https://github.com/Sadaqaty)