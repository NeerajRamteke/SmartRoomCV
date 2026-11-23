# SmartRoomCV Dashboard

React + Vite dashboard with a Flask bridge for your existing Python YOLO11 + ByteTrack application.

## Requirements
- Node.js (LTS)
- Python 3.11 recommended
- Existing SmartRoomCV Python environment

## 1. Start the dashboard backend
Open PowerShell in this folder:

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
pip install flask flask-cors
python server.py
```

The API runs at http://127.0.0.1:5000.

## 2. Start the React frontend
Open a second PowerShell window in this folder:

```powershell
npm install
npm run dev
```

Open the local URL printed by Vite (usually http://localhost:5173).

## 3. Connect your existing YOLO/ByteTrack program
From your existing Python program, POST live state to the bridge. Example:

```python
import requests

DASHBOARD_API = "http://127.0.0.1:5000/api/state"

payload = {
    "total_people": 3,
    "active_zones": 2,
    "zones": {
        "1": {"people": 2, "light": True, "fan": True},
        "2": {"people": 0, "light": False, "fan": False},
        "3": {"people": 1, "light": True, "fan": True},
        "4": {"people": 0, "light": False, "fan": False}
    },
    "tracks": [
        {"id": 1, "zone": 1, "x": 0.25, "y": 0.30},
        {"id": 2, "zone": 1, "x": 0.34, "y": 0.45},
        {"id": 3, "zone": 3, "x": 0.70, "y": 0.65}
    ],
    "system": {
        "camera": "Online",
        "yolo": "Running",
        "bytetrack": "Running",
        "blynk": "Connected",
        "raspberry_pi": "Not configured"
    }
}

requests.post(DASHBOARD_API, json=payload, timeout=1)
```

Call this inside your existing processing loop after `zone_people`, `zone_status`, and tracking IDs have been calculated. Don't send sample values in your final integrated build; send values calculated from actual detections.

### Track coordinates
`x` and `y` are normalized camera-frame coordinates from 0.0 to 1.0. For example, `x=0.25, y=0.30` means 25% across the frame and 30% down. Keep the coordinate system aligned with the original four quadrant zones.

### Important
- This starter uses a local Flask bridge and demo fallback state.
- It does not turn real electrical devices on/off by itself.
- Blynk is still a separate integration. Your existing Python code can continue sending V0–V9 to Blynk.
- For Raspberry Pi deployment, run the backend on the Pi and set the frontend/API host accordingly.
