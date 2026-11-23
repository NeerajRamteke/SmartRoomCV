# SmartRoomCV

SmartRoomCV is an AI-enabled smart classroom system that detects people with YOLO and ByteTrack, divides the camera view into four zones, and controls lights and fans automatically or manually. The project includes a desktop visualization, a React dashboard, optional Blynk control, energy prediction, and an optional Firebase bridge.

## Features

- YOLO11 person detection and ByteTrack object tracking
- Four-zone occupancy detection
- Automatic and manual light/fan control
- OpenCV camera view and Pygame classroom visualization
- React/Vite dashboard with live zone and tracking data
- Flask API and Random Forest energy prediction
- Optional Blynk virtual-pin integration
- Optional Firebase Realtime Database history and analytics
- Virtual classroom demo

## Project Structure

```text
SmartRoomCV/
├── main_new.py                         # Main camera application
├── main_backup.py                      # Previous camera application backup
├── virtual_classroom.py                # Pygame demonstration using simulated people
├── yolo11n.pt                          # YOLO11 model
├── serviceAccountKey.json              # Firebase credentials (keep private)
├── SmartRoomCV_Dashboard/
│   ├── server.py                       # Dashboard API and energy model
│   ├── smartroomcv_energy_model.pkl    # Trained energy prediction model
│   ├── src/                            # React dashboard source
│   └── package.json
└── SmartRoomCV_Firebase_Addon/
    ├── firebase_bridge.py              # Firebase Realtime Database bridge
    ├── .env.example
    └── requirements-firebase.txt
```

## Requirements

- Windows 10/11
- Python 3.11 recommended
- Node.js 18 or newer
- A webcam
- Internet access only for Blynk or Firebase features

## Installation

Create and activate a Python virtual environment in the project root:

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install opencv-python pygame requests ultralytics flask flask-cors joblib pandas scikit-learn
```

Install the dashboard dependencies:

```powershell
cd SmartRoomCV_Dashboard
npm install
cd ..
```

## Run the Camera Application

Start from the project root:

```powershell
.\venv\Scripts\Activate.ps1
python main_new.py
```

Press `Q` or `Esc` to stop. The application:

- Opens camera index `0` by default
- Loads `yolo11n.pt`
- Divides the frame into four quadrants
- Sends occupancy and device state to the dashboard
- Optionally sends state to Blynk and Firebase

To change the camera, edit `CAMERA_INDEX` in `main_new.py`.

## Run the Dashboard

Open a terminal and start the Flask backend:

```powershell
.\venv\Scripts\Activate.ps1
cd SmartRoomCV_Dashboard
python server.py
```

The backend runs at `http://127.0.0.1:5000`.

Open a second terminal and start the React frontend:

```powershell
cd SmartRoomCV_Dashboard
npm run dev
```

Open `http://localhost:5173`. The dashboard refreshes live state every 1.5 seconds and supports manual device overrides.

## Run the Virtual Classroom

This demo uses simulated people and does not require a webcam:

```powershell
.\venv\Scripts\Activate.ps1
python virtual_classroom.py
```

## Optional Blynk Integration

Set the Blynk authentication token in `main_new.py` or as an environment variable:

```powershell
$env:BLYNK_AUTH_TOKEN="your_blynk_token"
python main_new.py
```

The application uses virtual pins `V0`-`V9`. Keep the token private and do not commit it.

## Optional Firebase Integration

Install the Firebase dependencies:

```powershell
.\venv\Scripts\Activate.ps1
python -m pip install -r SmartRoomCV_Firebase_Addon\requirements-firebase.txt
```

From the Firebase add-on directory, copy the environment template:

```powershell
Copy-Item SmartRoomCV_Firebase_Addon\.env.example SmartRoomCV_Firebase_Addon\.env
```

Set `FIREBASE_DATABASE_URL` in the `.env` file and place the downloaded Firebase service-account JSON at the project root as `serviceAccountKey.json`, or set `FIREBASE_SERVICE_ACCOUNT` to another private local path.

Start the bridge:

```powershell
cd SmartRoomCV_Firebase_Addon
python firebase_bridge.py
```

The bridge runs at `http://127.0.0.1:5001`. Useful endpoints:

- `/api/health`
- `/api/current`
- `/api/history?limit=100`
- `/api/analytics`

See [SmartRoomCV_Firebase_Addon/SMARTROOMCV_FIREBASE_SETUP.md](SmartRoomCV_Firebase_Addon/SMARTROOMCV_FIREBASE_SETUP.md) for complete Firebase setup.

## API Endpoints

Dashboard backend:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/state` | Read live classroom state |
| POST | `/api/state` | Update live classroom state |
| POST | `/api/control` | Set a light/fan manual override |
| POST | `/api/control/automatic` | Return a device to automatic control |
| POST | `/api/predict-energy` | Predict energy for one zone |
| GET | `/api/energy-prediction` | Predict whole-lab energy |
| GET | `/api/health` | Check backend health |

## Security

Never commit secrets or private credentials:

- `.env`
- `serviceAccountKey.json`
- Firebase service-account JSON files
- Blynk authentication tokens

These patterns are covered by the project [`.gitignore`](.gitignore). Firebase database credentials and Blynk tokens must remain local.
