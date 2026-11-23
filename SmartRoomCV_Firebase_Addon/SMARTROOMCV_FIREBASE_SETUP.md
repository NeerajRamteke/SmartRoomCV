# SmartRoomCV + Firebase Realtime Database (Windows / VS Code)

This add-on keeps the existing camera app, YOLO + ByteTrack, Blynk sender, and Flask dashboard intact. It runs a separate local Flask bridge on port 5001. The bridge uses Firebase Admin SDK to write live state and time-spaced history, and exposes current/history/analytics APIs for the dashboard.

## 1. Create Firebase project and database

1. Open https://console.firebase.google.com/ and select **Create a project**.
2. Give it a name such as `SmartRoomCV`.
3. Open **Build → Realtime Database → Create Database**.
4. Choose the database region closest to your users, then create the database.
5. Copy the complete **Database URL** shown on the Realtime Database page. It may end in `firebasedatabase.app` or `firebaseio.com`; use the exact URL Firebase displays.

## 2. Create a server service-account key

1. In Firebase Console, open **Project settings → Service accounts**.
2. Generate a new private key and download the JSON file.
3. Put it in your local SmartRoomCV project folder as `serviceAccountKey.json`.
4. Never upload this file to GitHub, the frontend, screenshots, or chat. The Admin SDK key has privileged server access.

## 3. Set safe database rules

The browser dashboard in this starter talks only to the local Flask bridge, not directly to Firebase. Keep client rules closed until authentication is added. In Realtime Database → Rules, use:

{
  "rules": {
    ".read": false,
    ".write": false
  }
}

The Firebase Admin SDK on the local server uses the service-account credentials and can access the database despite these client rules. Do not change the rules to public read/write.

## 4. Add files to your existing project

Copy `firebase_bridge.py` into the same project folder that contains `main.py` and `server.py`.
Copy `.env.example` to `.env` and replace the database URL. If you renamed the service-account JSON or placed it elsewhere, set `FIREBASE_SERVICE_ACCOUNT` to that local path.

Example `.env`:
FIREBASE_DATABASE_URL=https://YOUR_DATABASE_NAME.REGION.firebasedatabase.app
FIREBASE_SERVICE_ACCOUNT=serviceAccountKey.json
FIREBASE_BRIDGE_PORT=5001
FIREBASE_HISTORY_INTERVAL_SECONDS=10

Do not put quotes around these simple values. Replace the placeholder URL with the exact URL from Firebase Console.

## 5. Install packages in the existing Python virtual environment

Open PowerShell in `C:\\Users\\neera\\SmartRoomCV` (or your actual project path):

.\venv\Scripts\Activate.ps1
python -m pip install -r requirements-firebase.txt

If you prefer not to use a requirements file:
python -m pip install firebase-admin Flask Flask-Cors python-dotenv

## 6. Connect the existing camera app

Open `main_py_patch.txt` and follow the minimal patch instructions. It adds a separate sender that posts a snapshot every two seconds to `http://127.0.0.1:5001/api/state`. It does not replace or remove your existing dashboard POST or Blynk calls.

## 7. Run the three local processes

Terminal 1 — existing dashboard backend:
.\venv\Scripts\Activate.ps1
python server.py

Terminal 2 — Firebase bridge:
.\venv\Scripts\Activate.ps1
python firebase_bridge.py

Terminal 3 — existing camera application:
.\venv\Scripts\Activate.ps1
python main.py

If your project uses a different filename for the camera app, run that existing filename instead of `main.py`.

Check bridge health in a browser:
http://127.0.0.1:5001/api/health

Check latest cloud state:
http://127.0.0.1:5001/api/current

Check saved history:
http://127.0.0.1:5001/api/history?limit=100

Check analytics:
http://127.0.0.1:5001/api/analytics

## 8. Firebase data layout

smartroomcv/
  current/     Latest room snapshot (updated at most once per second)
  history/     Time-spaced snapshots (every 10 seconds by default)

Each snapshot includes timestamp, total_people, active_zones, zone-wise people/occupied/light/fan, tracks, and system status. History interval is configurable in `.env`.

## 9. Dashboard analytics

`dashboard_api_examples.js` contains small fetch helpers for the existing React/Vite dashboard. Add them to the frontend and call `getFirebaseAnalytics()` from a React effect to load historical metrics. Use your existing chart library or cards to render the values; this helper does not replace the dashboard UI.

For example:
- `sample_count`: number of saved history snapshots
- `average_people`: average people count across saved samples
- `peak_people`: highest people count in saved samples
- `average_active_zones`: average occupied-zone count
- `zone_occupancy_samples`: count of history samples in which each zone was occupied
- `hourly_average_people`: average count grouped by local hour

## 10. Common errors

- `FIREBASE_DATABASE_URL is missing`: edit `.env`; use the exact database URL from Firebase Console.
- Service account not found: check `FIREBASE_SERVICE_ACCOUNT` path.
- `Permission denied`: confirm the Admin SDK is initialized with the downloaded service-account key and correct database URL; do not make database rules public.
- Port 5001 in use: change `FIREBASE_BRIDGE_PORT` in `.env` and update `FIREBASE_BRIDGE_API` in `main.py` and `FIREBASE_BRIDGE` in the frontend helper.
- No history: run the bridge and camera app together and wait for at least one configured history interval.
- Analytics says no history: make sure the bridge is receiving POSTs and check `/api/history`.

## Security notes

- Keep `.env` and `serviceAccountKey.json` out of source control. Add both to `.gitignore`.
- The bridge binds to `127.0.0.1`, not all network interfaces. Do not deploy it publicly without adding authentication, request validation, rate limiting, and HTTPS.
- Firebase Authentication is intentionally not included yet, per the requested scope.
