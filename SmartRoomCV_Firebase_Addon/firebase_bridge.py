import os
import time
from datetime import datetime, timezone
from threading import Lock

import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

APP_NAME = "SmartRoomCV Firebase Bridge"
DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL", "").strip()
SERVICE_ACCOUNT = os.getenv("FIREBASE_SERVICE_ACCOUNT", "serviceAccountKey.json").strip()
HOST = "127.0.0.1"
PORT = int(os.getenv("FIREBASE_BRIDGE_PORT", "5001"))
HISTORY_INTERVAL_SECONDS = max(5, int(os.getenv("FIREBASE_HISTORY_INTERVAL_SECONDS", "10")))

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": [
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:3000", "http://127.0.0.1:3000"
]}})

write_lock = Lock()
last_history_write = 0.0
last_latest_write = 0.0
firebase_ready = False


def initialize_firebase():
    global firebase_ready
    if not DATABASE_URL:
        raise RuntimeError("FIREBASE_DATABASE_URL is missing in the .env file.")
    if not os.path.isfile(SERVICE_ACCOUNT):
        raise RuntimeError(
            f"Firebase service-account JSON was not found: {SERVICE_ACCOUNT}. "
            "Set FIREBASE_SERVICE_ACCOUNT to its full local path in .env."
        )

    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT)
        firebase_admin.initialize_app(cred, {"databaseURL": DATABASE_URL})
    firebase_ready = True
    print("Firebase Admin SDK connected.")
    print("Realtime Database:", DATABASE_URL)


def normalize_payload(payload):
    if not isinstance(payload, dict):
        raise ValueError("JSON body must be an object.")

    zones_in = payload.get("zones", {})
    zones = {}
    for zone_id in range(1, 5):
        item = zones_in.get(str(zone_id), zones_in.get(zone_id, {})) or {}
        zones[str(zone_id)] = {
            "people": max(0, int(item.get("people", 0))),
            "occupied": bool(item.get("people", 0)),
            "light": bool(item.get("light", False)),
            "fan": bool(item.get("fan", False)),
        }

    total_people = max(0, int(payload.get("total_people", sum(z["people"] for z in zones.values()))))
    active_zones = max(0, min(4, int(payload.get(
        "active_zones", sum(1 for z in zones.values() if z["occupied"])
    ))))

    return {
        "total_people": total_people,
        "active_zones": active_zones,
        "zones": zones,
        "tracks": payload.get("tracks", []) if isinstance(payload.get("tracks", []), list) else [],
        "system": payload.get("system", {}) if isinstance(payload.get("system", {}), dict) else {},
    }


@app.get("/api/health")
def health():
    return jsonify({
        "service": APP_NAME,
        "status": "online",
        "firebase_ready": firebase_ready,
        "history_interval_seconds": HISTORY_INTERVAL_SECONDS,
    })


@app.post("/api/state")
def receive_state():
    global last_history_write, last_latest_write
    try:
        payload = normalize_payload(request.get_json(silent=True) or {})
        now = time.time()
        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
        payload["timestamp"] = now
        payload["timestamp_iso"] = now_iso

        with write_lock:
            # Limit cloud writes: latest state at most once per second.
            if now - last_latest_write >= 1.0:
                db.reference("smartroomcv/current").set(payload)
                last_latest_write = now

            # Save a history snapshot at a controlled interval, not on every video frame.
            if now - last_history_write >= HISTORY_INTERVAL_SECONDS:
                db.reference("smartroomcv/history").push(payload)
                last_history_write = now

        return jsonify({
            "ok": True,
            "firebase": "connected",
            "timestamp": now_iso,
            "history_saved": now - last_history_write < 0.01,
        }), 200
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        app.logger.exception("Firebase write failed")
        return jsonify({"ok": False, "error": "Firebase write failed", "details": str(exc)}), 503


@app.get("/api/current")
def current_state():
    try:
        data = db.reference("smartroomcv/current").get()
        return jsonify(data or {})
    except Exception:
        app.logger.exception("Firebase current-state read failed")
        return jsonify({"error": "Could not read current state from Firebase"}), 503


@app.get("/api/history")
def history():
    try:
        limit = request.args.get("limit", default=500, type=int)
        limit = max(1, min(limit or 500, 2000))
        data = db.reference("smartroomcv/history").get() or {}
        rows = []
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict):
                    row = dict(value)
                    row["record_id"] = key
                    rows.append(row)
        rows.sort(key=lambda row: float(row.get("timestamp", 0)))
        return jsonify(rows[-limit:])
    except Exception:
        app.logger.exception("Firebase history read failed")
        return jsonify({"error": "Could not read history from Firebase"}), 503


@app.get("/api/analytics")
def analytics():
    try:
        data = db.reference("smartroomcv/history").get() or {}
        rows = list(data.values()) if isinstance(data, dict) else []
        rows = [r for r in rows if isinstance(r, dict) and "timestamp" in r]
        rows.sort(key=lambda row: float(row.get("timestamp", 0)))

        if not rows:
            return jsonify({
                "sample_count": 0,
                "average_people": 0,
                "peak_people": 0,
                "average_active_zones": 0,
                "zone_occupancy_samples": {"1": 0, "2": 0, "3": 0, "4": 0},
                "hourly_average_people": [],
                "message": "No history yet. Start the camera app and wait for history samples."
            })

        zone_occupancy = {str(i): 0 for i in range(1, 5)}
        hourly = {}
        people_values = []
        active_values = []

        for row in rows:
            people = max(0, int(row.get("total_people", 0)))
            active = max(0, int(row.get("active_zones", 0)))
            people_values.append(people)
            active_values.append(active)
            stamp = float(row.get("timestamp", 0))
            hour = datetime.fromtimestamp(stamp, timezone.utc).astimezone().strftime("%Y-%m-%d %H:00")
            hourly.setdefault(hour, []).append(people)
            zones = row.get("zones", {})
            for zone_id in ("1", "2", "3", "4"):
                zone = zones.get(zone_id, {}) if isinstance(zones, dict) else {}
                if bool(zone.get("occupied", zone.get("people", 0) > 0)):
                    zone_occupancy[zone_id] += 1

        hourly_rows = [
            {"hour": hour, "average_people": round(sum(vals) / len(vals), 2), "samples": len(vals)}
            for hour, vals in sorted(hourly.items())
        ]

        return jsonify({
            "sample_count": len(rows),
            "average_people": round(sum(people_values) / len(people_values), 2),
            "peak_people": max(people_values),
            "average_active_zones": round(sum(active_values) / len(active_values), 2),
            "zone_occupancy_samples": zone_occupancy,
            "hourly_average_people": hourly_rows,
        })
    except Exception:
        app.logger.exception("Firebase analytics failed")
        return jsonify({"error": "Could not calculate analytics"}), 503


if __name__ == "__main__":
    initialize_firebase()
    print(f"{APP_NAME} running at http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=False, threaded=True)
