
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timezone
from threading import Lock
import os
import joblib
import pandas as pd

# ============================================================
# SMARTROOMCV DASHBOARD + WHOLE-LAB ENERGY PREDICTION
# ============================================================

app = Flask(__name__)
CORS(app)

lock = Lock()

# Load the trained model
MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "smartroomcv_energy_model.pkl"
)

energy_bundle = joblib.load(MODEL_PATH)
energy_model = energy_bundle["model"]
energy_features = energy_bundle["features"]

# Assumed device ratings; change these to match your equipment.
LIGHT_WATTAGE = 12.0
FAN_WATTAGE = 60.0

# Energy prediction interval
INTERVAL_SECONDS = 60.0

# Print no more often than this many seconds, even if updates
# arrive continuously. Set to 0 to print every update.
PRINT_INTERVAL_SECONDS = 5.0
last_print_time = 0.0

# ============================================================
# SHARED DASHBOARD STATE
# ============================================================

state = {
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "total_people": 0,
    "active_zones": 0,
    "zones": {
        str(i): {
            "people": 0,
            "light": False,
            "fan": False
        }
        for i in range(1, 5)
    },
    # None means automatic mode; True/False means manual override.
    "manual_overrides": {
        str(i): {"light": None, "fan": None}
        for i in range(1, 5)
    },
    "tracks": [],
    "system": {
        "camera": "Waiting",
        "yolo": "Waiting",
        "bytetrack": "Waiting",
        "blynk": "Not checked",
        "raspberry_pi": "Not configured"
    },
    "history": []
}


# ============================================================
# WHOLE-LAB ENERGY PREDICTION
# ============================================================

def predict_lab_energy(print_result=True, interval_seconds=INTERVAL_SECONDS):
    """
    Predict energy for each of four zones using the latest
    occupancy and device states.

    Assumes the trained model predicts Wh per zone for the
    specified interval.
    """

    with lock:
        zones_snapshot = {
            str(i): dict(
                state["zones"].get(
                    str(i),
                    {"people": 0, "light": False, "fan": False}
                )
            )
            for i in range(1, 5)
        }

    zone_results = []
    total_people = 0
    total_ml_energy = 0.0
    total_formula_energy = 0.0
    total_power = 0.0

    for zone_number in range(1, 5):
        zone_data = zones_snapshot[str(zone_number)]

        people = int(zone_data.get("people", 0))
        light_on = int(bool(zone_data.get("light", False)))
        fan_on = int(bool(zone_data.get("fan", False)))

        if not 0 <= people <= 30:
            raise ValueError(
                f"Zone {zone_number}: people count must be 0-30"
            )

        # Build input with exactly the trained feature names.
        input_row = {
            "zone": zone_number,
            "people": people,
            "light_on": light_on,
            "fan_on": fan_on,
            "light_wattage_assumed_W": LIGHT_WATTAGE,
            "fan_wattage_assumed_W": FAN_WATTAGE,
            "interval_seconds": interval_seconds
        }

        features = pd.DataFrame([input_row])[energy_features]

        # Random Forest prediction for this zone and interval.
        ml_energy = max(
            0.0,
            float(energy_model.predict(features)[0])
        )

        # Independent physics-based estimate for comparison.
        power_w = (
            light_on * LIGHT_WATTAGE
            + fan_on * FAN_WATTAGE
        )

        formula_energy = (
            power_w * interval_seconds / 3600.0
        )

        total_people += people
        total_ml_energy += ml_energy
        total_formula_energy += formula_energy
        total_power += power_w

        zone_results.append({
            "zone": zone_number,
            "people": people,
            "light_on": bool(light_on),
            "fan_on": bool(fan_on),
            "predicted_energy_Wh": round(ml_energy, 4),
            "formula_energy_Wh": round(formula_energy, 4),
            "estimated_power_W": round(power_w, 2)
        })

    result = {
        "success": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_people": total_people,
        "zones": zone_results,
        "total_predicted_energy_Wh": round(total_ml_energy, 4),
        "total_formula_energy_Wh": round(total_formula_energy, 4),
        "total_estimated_power_W": round(total_power, 2),
        "interval_seconds": interval_seconds,
        "unit": "Wh",
        "model": "Random Forest Regressor",
        "data_type": "simulated_estimate"
    }

    if print_result:
        print("\n" + "=" * 68, flush=True)
        print("       SMARTROOMCV - WHOLE LAB ENERGY PREDICTION", flush=True)
        print("=" * 68, flush=True)

        for zone in zone_results:
            print(
                f"Zone {zone['zone']} | "
                f"People: {zone['people']:2d} | "
                f"Light: {'ON' if zone['light_on'] else 'OFF':3s} | "
                f"Fan: {'ON' if zone['fan_on'] else 'OFF':3s} | "
                f"ML Energy: {zone['predicted_energy_Wh']:.4f} Wh",
                flush=True
            )

        print("-" * 68, flush=True)
        print(f"TOTAL PEOPLE IN LAB       : {total_people}", flush=True)
        print(
            f"TOTAL ML ENERGY / "
            f"{interval_seconds:.0f} s : {total_ml_energy:.4f} Wh",
            flush=True
        )
        print(
            f"TOTAL FORMULA ENERGY      : "
            f"{total_formula_energy:.4f} Wh",
            flush=True
        )
        print(
            f"TOTAL ESTIMATED POWER     : "
            f"{total_power:.2f} W",
            flush=True
        )
        print("=" * 68 + "\n", flush=True)

    return result


# ============================================================
# INDIVIDUAL-ZONE PREDICTION API
# ============================================================

@app.route("/api/predict-energy", methods=["POST"])
def predict_energy():
    try:
        payload = request.get_json(silent=True) or {}

        zone = int(payload.get("zone", 1))
        people = int(payload.get("people", 0))
        light_on = int(bool(payload.get("light_on", False)))
        fan_on = int(bool(payload.get("fan_on", False)))
        interval_seconds = float(
            payload.get("interval_seconds", INTERVAL_SECONDS)
        )
        light_wattage = float(
            payload.get("light_wattage_assumed_W", LIGHT_WATTAGE)
        )
        fan_wattage = float(
            payload.get("fan_wattage_assumed_W", FAN_WATTAGE)
        )

        if zone not in (1, 2, 3, 4):
            return jsonify({"error": "Zone must be 1, 2, 3, or 4"}), 400

        if not 0 <= people <= 30:
            return jsonify({"error": "People must be between 0 and 30"}), 400

        if not 0 < interval_seconds <= 86400:
            return jsonify({"error": "Interval must be 1-86400 seconds"}), 400

        if light_wattage < 0 or fan_wattage < 0:
            return jsonify({"error": "Wattage cannot be negative"}), 400

        input_row = {
            "zone": zone,
            "people": people,
            "light_on": light_on,
            "fan_on": fan_on,
            "light_wattage_assumed_W": light_wattage,
            "fan_wattage_assumed_W": fan_wattage,
            "interval_seconds": interval_seconds
        }

        features = pd.DataFrame([input_row])[energy_features]
        prediction = max(
            0.0,
            float(energy_model.predict(features)[0])
        )

        power_w = (
            light_on * light_wattage
            + fan_on * fan_wattage
        )
        formula_energy = power_w * interval_seconds / 3600.0

        print(
            f"[ZONE PREDICTION] Zone={zone}, People={people}, "
            f"ML={prediction:.4f} Wh, "
            f"Formula={formula_energy:.4f} Wh",
            flush=True
        )

        return jsonify({
            "success": True,
            **input_row,
            "light_on": bool(light_on),
            "fan_on": bool(fan_on),
            "predicted_energy_Wh": round(prediction, 4),
            "formula_energy_Wh": round(formula_energy, 4),
            "estimated_power_W": round(power_w, 2),
            "unit": "Wh",
            "model": "Random Forest Regressor",
            "data_type": "simulated_estimate"
        })

    except (TypeError, ValueError) as exc:
        return jsonify({"error": f"Invalid input: {exc}"}), 400
    except Exception:
        app.logger.exception("Zone energy prediction failed")
        return jsonify({"error": "Energy prediction failed"}), 500


# ============================================================
# WHOLE-LAB PREDICTION ENDPOINT
# ============================================================

@app.get("/api/predict-lab-energy")
def get_lab_energy_prediction():
    try:
        interval_seconds = float(
            request.args.get("interval_seconds", INTERVAL_SECONDS)
        )
        if not 0 < interval_seconds <= 86400:
            return jsonify({"error": "Interval must be 1-86400 seconds"}), 400

        return jsonify(predict_lab_energy(
            print_result=False,
            interval_seconds=interval_seconds
        ))
    except (TypeError, ValueError) as exc:
        return jsonify({"error": f"Invalid interval: {exc}"}), 400
    except Exception:
        app.logger.exception("Whole-lab prediction failed")
        return jsonify({"error": "Whole-lab prediction failed"}), 500


# ============================================================
# HEALTH AND STATE ENDPOINTS
# ============================================================

@app.get("/api/health")
def health():
    return jsonify({
        "ok": True,
        "service": "SmartRoomCV API"
    })


@app.get("/api/state")
def get_state():
    with lock:
        return jsonify(state)


@app.post("/api/state")
def update_state():
    global last_print_time

    incoming = request.get_json(silent=True)

    if not isinstance(incoming, dict):
        return jsonify({"error": "Expected a JSON object"}), 400

    with lock:
        # Merge zone updates so omitted zones are not erased.
        if "zones" in incoming:
            incoming_zones = incoming["zones"]

            if not isinstance(incoming_zones, dict):
                return jsonify({"error": "zones must be an object"}), 400

            for zone_id in ("1", "2", "3", "4"):
                if zone_id in incoming_zones:
                    zone_update = incoming_zones[zone_id]

                    if not isinstance(zone_update, dict):
                        return jsonify({
                            "error": f"Zone {zone_id} must be an object"
                        }), 400

                    state["zones"].setdefault(
                        zone_id,
                        {"people": 0, "light": False, "fan": False}
                    )

                    # Keep occupancy updates, but do not let main_new.py
                    # overwrite a device controlled manually from Blynk.
                    for field, field_value in zone_update.items():
                        if field in ("light", "fan"):
                            override = state["manual_overrides"][zone_id][field]
                            if override is not None:
                                state["zones"][zone_id][field] = override
                            else:
                                state["zones"][zone_id][field] = field_value
                        else:
                            state["zones"][zone_id][field] = field_value

        for key in ("total_people", "active_zones", "tracks", "system"):
            if key in incoming:
                state[key] = incoming[key]

        state["updated_at"] = datetime.now(timezone.utc).isoformat()

        state["history"].append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "people": int(state.get("total_people", 0)),
            "active_zones": int(state.get("active_zones", 0))
        })
        state["history"] = state["history"][-30:]

        now = datetime.now().timestamp()
        should_print = (
            PRINT_INTERVAL_SECONDS <= 0
            or now - last_print_time >= PRINT_INTERVAL_SECONDS
        )

        if should_print:
            last_print_time = now

    # Predict outside the lock, using a snapshot of the latest state.
    if should_print:
        try:
            predict_lab_energy(print_result=True)
        except Exception:
            app.logger.exception(
                "Automatic whole-lab energy prediction failed"
            )

    return jsonify({
        "ok": True,
        "updated_at": state["updated_at"]
    })


# ============================================================
# DEVICE CONTROL API
# ============================================================

@app.post("/api/control")
def control():
    data = request.get_json(silent=True) or {}

    zone = str(data.get("zone", ""))
    device = data.get("device")
    value = bool(data.get("value"))

    if zone not in ("1", "2", "3", "4"):
        return jsonify({"error": "Zone must be 1, 2, 3, or 4"}), 400

    if device not in ("light", "fan"):
        return jsonify({"error": "Device must be light or fan"}), 400

    with lock:
        state["zones"].setdefault(
            zone,
            {"people": 0, "light": False, "fan": False}
        )
        # A Blynk command activates a persistent manual override.
        state["manual_overrides"][zone][device] = value
        state["zones"][zone][device] = value
        state["updated_at"] = datetime.now(timezone.utc).isoformat()

    return jsonify({
        "ok": True,
        "zone": int(zone),
        "device": device,
        "value": value,
        "manual_override": True
    })


@app.post("/api/control/auto")
def set_automatic_control():
    """Release one manual override so YOLO can control that device again."""
    data = request.get_json(silent=True) or {}
    zone = str(data.get("zone", ""))
    device = data.get("device")

    if zone not in ("1", "2", "3", "4"):
        return jsonify({"error": "Zone must be 1, 2, 3, or 4"}), 400
    if device not in ("light", "fan"):
        return jsonify({"error": "Device must be light or fan"}), 400

    with lock:
        state["manual_overrides"][zone][device] = None
        state["updated_at"] = datetime.now(timezone.utc).isoformat()

    return jsonify({
        "ok": True,
        "zone": int(zone),
        "device": device,
        "mode": "automatic"
    })


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":
    print("SmartRoomCV Dashboard API starting...", flush=True)
    print(f"Energy model: {MODEL_PATH}", flush=True)
    print("API: http://127.0.0.1:5000", flush=True)

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        threaded=True
    )
