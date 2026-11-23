import cv2
import pygame
import math
import requests
import sys
import os
from ultralytics import YOLO
import time

# ============================================================
# CONFIGURATION
# ============================================================

MODEL_PATH = "yolo11n.pt"
CONFIDENCE = 0.50
CAMERA_INDEX = 0

# Replace this locally with your newly regenerated Blynk token.
# Do not share the token publicly or commit it to Git.
BLYNK_TOKEN = os.getenv("BLYNK_AUTH_TOKEN", "PASTE_YOUR_NEW_BLYNK_TOKEN_HERE")
BLYNK_URL = "https://blynk.cloud/external/api/update"

# Flask backend from the SmartRoomCV web dashboard project.
DASHBOARD_API = "http://127.0.0.1:5000/api/state"
# Firebase bridge
FIREBASE_BRIDGE_API = "http://127.0.0.1:5001/api/state"
FIREBASE_SEND_INTERVAL = 2.0

last_firebase_send = 0.0
firebase_warning_shown = False

# Blynk virtual pins
LIGHT_PINS = {1: "V0", 2: "V2", 3: "V4", 4: "V6"}
FAN_PINS = {1: "V1", 2: "V3", 3: "V5", 4: "V7"}
PEOPLE_PIN = "V8"
ACTIVE_ZONES_PIN = "V9"

# YOLO tracking uses Ultralytics ByteTrack.
BYTETRACK_ENABLED = True
RASPBERRY_PI_IN_USE = False


# ============================================================
# BLYNK AND DASHBOARD CONNECTIONS
# ============================================================

session = requests.Session()
last_blynk_values = {}

# Manual device overrides are maintained by server.py when Blynk is used.
# None = automatic YOLO mode; True/False = manual ON/OFF.
CONTROL_POLL_INTERVAL = 0.5
last_control_poll = 0.0
manual_overrides = {
    zone: {"light": None, "fan": None}
    for zone in range(1, 5)
}
light_states = {zone: False for zone in range(1, 5)}
fan_states = {zone: False for zone in range(1, 5)}


def refresh_device_controls():
    """Read the effective manual/automatic device settings from Flask."""
    global last_control_poll, manual_overrides

    now = time.monotonic()
    if now - last_control_poll < CONTROL_POLL_INTERVAL:
        return

    last_control_poll = now

    try:
        response = session.get(DASHBOARD_API, timeout=0.5)
        response.raise_for_status()
        data = response.json()

        received_overrides = data.get("manual_overrides", {})
        received_zones = data.get("zones", {})

        for zone in range(1, 5):
            zone_key = str(zone)
            override = received_overrides.get(zone_key, {})
            manual_overrides[zone] = {
                "light": override.get("light"),
                "fan": override.get("fan")
            }

            zone_data = received_zones.get(zone_key, {})
            auto_state = bool(zone_status[zone])

            light_override = manual_overrides[zone]["light"]
            fan_override = manual_overrides[zone]["fan"]

            light_states[zone] = (
                bool(light_override)
                if light_override is not None
                else auto_state
            )
            fan_states[zone] = (
                bool(fan_override)
                if fan_override is not None
                else auto_state
            )

    except (requests.RequestException, ValueError, TypeError) as exc:
        # Keep the app running if the dashboard is temporarily unavailable.
        if not getattr(refresh_device_controls, "warning_shown", False):
            print(f"Could not read manual device controls from Flask: {exc}")
            refresh_device_controls.warning_shown = True


def update_blynk(pin, value):
    """Send one value to a Blynk virtual pin."""
    if not BLYNK_TOKEN or BLYNK_TOKEN == "PASTE_YOUR_NEW_BLYNK_TOKEN_HERE":
        return False

    try:
        response = session.get(
            BLYNK_URL,
            params={"token": BLYNK_TOKEN, pin: value},
            timeout=2
        )
        if response.status_code == 200:
            return True

        print(f"Blynk error for {pin}: HTTP {response.status_code}")
    except requests.RequestException as exc:
        print(f"Blynk connection error for {pin}: {exc}")

    return False


def send_if_changed(pin, value):
    """Send to Blynk only when the value changes."""
    value = int(value)
    if last_blynk_values.get(pin) != value:
        if update_blynk(pin, value):
            last_blynk_values[pin] = value


def send_firebase_state(payload):
    """Send classroom state to the Firebase bridge."""
    global last_firebase_send, firebase_warning_shown

    now = time.monotonic()

    if now - last_firebase_send < FIREBASE_SEND_INTERVAL:
        return

    last_firebase_send = now

    try:
        response = requests.post(
            FIREBASE_BRIDGE_API,
            json=payload,
            timeout=1.5
        )
        response.raise_for_status()

        if firebase_warning_shown:
            print("Firebase bridge connection restored.")
            firebase_warning_shown = False

    except requests.RequestException as error:
        if not firebase_warning_shown:
            print("Firebase bridge is not responding.")
            print(f"Details: {error}")
            firebase_warning_shown = True



def send_dashboard_state(total_people, active_zones, zone_people, zone_status, tracks):
    """Send the latest occupancy/device state and tracked IDs to the Flask dashboard."""
    payload = {
        "total_people": int(total_people),
        "active_zones": int(active_zones),
        "tracks": tracks,
        "zones": {
            str(zone): {
                "people": int(zone_people[zone]),
                "light": bool(zone_status[zone]),
                "fan": bool(zone_status[zone])
            }
            for zone in range(1, 5)
        },
        "system": {
            "camera": "Online",
            "yolo": "Running",
            "bytetrack": "Not integrated" if not BYTETRACK_ENABLED else "Running",
            "blynk": "Configured" if BLYNK_TOKEN and BLYNK_TOKEN != "PASTE_YOUR_NEW_BLYNK_TOKEN_HERE" else "Token required",
            "raspberry_pi": "Not configured" if not RASPBERRY_PI_IN_USE else "Online"
        }
    }
# Send the same classroom data to Firebase
    send_firebase_state(payload)
    try:
        response = session.post(DASHBOARD_API, json=payload, timeout=0.5)
        response.raise_for_status()
        return True
    except requests.RequestException:
        # Keep the camera/pygame app running if the web dashboard is stopped.
        return False


# ============================================================
# LOAD YOLO MODEL
# ============================================================

print("Loading YOLO model...")
try:
    model = YOLO(MODEL_PATH)
except Exception as exc:
    print(f"ERROR: Could not load YOLO model '{MODEL_PATH}': {exc}")
    sys.exit(1)

print("YOLO model loaded successfully.")


# ============================================================
# OPEN CAMERA
# ============================================================

cap = cv2.VideoCapture(CAMERA_INDEX)
if not cap.isOpened():
    print("ERROR: Could not open camera. Check CAMERA_INDEX.")
    sys.exit(1)


# ============================================================
# INITIALIZE PYGAME
# ============================================================

pygame.init()

SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 780
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Smart Classroom - YOLO + Blynk + Dashboard")

# Colors
BLACK = (20, 20, 20)
WHITE = (245, 245, 245)
GRAY = (80, 80, 80)
LIGHT_GRAY = (170, 170, 170)
GREEN = (50, 220, 100)
RED = (230, 60, 60)
BLUE = (70, 150, 255)
YELLOW = (255, 220, 70)

# Fonts
font_title = pygame.font.SysFont("Arial", 28, bold=True)
font_zone = pygame.font.SysFont("Arial", 22, bold=True)
font_status = pygame.font.SysFont("Arial", 18)
font_small = pygame.font.SysFont("Arial", 16)

# Camera display area
CAM_X = 20
CAM_Y = 90
CAM_WIDTH = 670
CAM_HEIGHT = 500

# Virtual classroom area
ROOM_X = 720
ROOM_Y = 90
ROOM_WIDTH = 660
ROOM_HEIGHT = 500

# Original 2 x 2 classroom zones
MID_X = ROOM_X + ROOM_WIDTH // 2
MID_Y = ROOM_Y + ROOM_HEIGHT // 2

ZONE_RECTS = {
    1: (ROOM_X, ROOM_Y, ROOM_WIDTH // 2, ROOM_HEIGHT // 2),
    2: (MID_X, ROOM_Y, ROOM_WIDTH // 2, ROOM_HEIGHT // 2),
    3: (ROOM_X, MID_Y, ROOM_WIDTH // 2, ROOM_HEIGHT // 2),
    4: (MID_X, MID_Y, ROOM_WIDTH // 2, ROOM_HEIGHT // 2)
}

zone_people = {1: 0, 2: 0, 3: 0, 4: 0}
zone_status = {1: False, 2: False, 3: False, 4: False}
fan_angle = {1: 0, 2: 0, 3: 0, 4: 0}


# ============================================================
# DRAW VIRTUAL DEVICES AND CLASSROOM
# ============================================================

def draw_light(surface, x, y, is_on):
    if is_on:
        for radius in range(35, 10, -5):
            glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            alpha = max(0, 80 - radius)
            pygame.draw.circle(glow, (255, 220, 70, alpha), (radius, radius), radius)
            surface.blit(glow, (x - radius, y - radius))

        pygame.draw.circle(surface, YELLOW, (x, y), 12)
        pygame.draw.circle(surface, WHITE, (x, y), 5)
    else:
        pygame.draw.circle(surface, GRAY, (x, y), 10)


def draw_fan(surface, x, y, angle, is_on):
    pygame.draw.circle(surface, GRAY, (x, y), 35, 3)
    pygame.draw.circle(surface, LIGHT_GRAY, (x, y), 8)

    for blade in range(4):
        current_angle = angle + blade * 90
        radians = math.radians(current_angle)
        end_x = x + int(math.cos(radians) * 30)
        end_y = y + int(math.sin(radians) * 30)
        pygame.draw.line(
            surface,
            WHITE if is_on else GRAY,
            (x, y),
            (end_x, end_y),
            7
        )


def draw_desk(surface, x, y):
    pygame.draw.rect(surface, (100, 100, 100), (x, y, 80, 35), border_radius=5)
    pygame.draw.line(surface, GRAY, (x + 10, y + 35), (x + 10, y + 50), 4)
    pygame.draw.line(surface, GRAY, (x + 70, y + 35), (x + 70, y + 50), 4)


def draw_student(surface, x, y):
    pygame.draw.circle(surface, BLUE, (x, y), 10)
    pygame.draw.line(surface, BLUE, (x, y + 10), (x, y + 30), 5)


def draw_classroom(surface):
    pygame.draw.rect(
        surface, (35, 35, 35),
        (ROOM_X, ROOM_Y, ROOM_WIDTH, ROOM_HEIGHT)
    )

    # Zone backgrounds and borders
    for zone in range(1, 5):
        x, y, w, h = ZONE_RECTS[zone]
        fill = (45, 65, 50) if zone_status[zone] else (35, 35, 35)
        pygame.draw.rect(surface, fill, (x, y, w, h))
        pygame.draw.rect(surface, GRAY, (x, y, w, h), 2)

    # Zone dividing lines
    pygame.draw.line(surface, WHITE, (MID_X, ROOM_Y), (MID_X, ROOM_Y + ROOM_HEIGHT), 2)
    pygame.draw.line(surface, WHITE, (ROOM_X, MID_Y), (ROOM_X + ROOM_WIDTH, MID_Y), 2)

    # Zone labels
    for zone in range(1, 5):
        x, y, _, _ = ZONE_RECTS[zone]
        label = font_zone.render(f"ZONE {zone}", True, WHITE)
        surface.blit(label, (x + 15, y + 15))

    fan_positions = {
        1: (ROOM_X + 120, ROOM_Y + 70),
        2: (MID_X + 120, ROOM_Y + 70),
        3: (ROOM_X + 120, MID_Y + 70),
        4: (MID_X + 120, MID_Y + 70)
    }
    light_positions = {
        1: (ROOM_X + 250, ROOM_Y + 60),
        2: (MID_X + 250, ROOM_Y + 60),
        3: (ROOM_X + 250, MID_Y + 60),
        4: (MID_X + 250, MID_Y + 60)
    }

    for zone in range(1, 5):
        fx, fy = fan_positions[zone]
        lx, ly = light_positions[zone]
        draw_fan(surface, fx, fy, fan_angle[zone], fan_states[zone])
        draw_light(surface, lx, ly, light_states[zone])

    desk_positions = [
        (ROOM_X + 45, ROOM_Y + 150),
        (ROOM_X + 150, ROOM_Y + 150),
        (MID_X + 45, ROOM_Y + 150),
        (MID_X + 150, ROOM_Y + 150),
        (ROOM_X + 45, MID_Y + 150),
        (ROOM_X + 150, MID_Y + 150),
        (MID_X + 45, MID_Y + 150),
        (MID_X + 150, MID_Y + 150)
    ]
    for x, y in desk_positions:
        draw_desk(surface, x, y)

    student_positions = {
        1: [(ROOM_X + 75, ROOM_Y + 135), (ROOM_X + 180, ROOM_Y + 135),
            (ROOM_X + 75, ROOM_Y + 235), (ROOM_X + 180, ROOM_Y + 235)],
        2: [(MID_X + 75, ROOM_Y + 135), (MID_X + 180, ROOM_Y + 135),
            (MID_X + 75, ROOM_Y + 235), (MID_X + 180, ROOM_Y + 235)],
        3: [(ROOM_X + 75, MID_Y + 135), (ROOM_X + 180, MID_Y + 135),
            (ROOM_X + 75, MID_Y + 235), (ROOM_X + 180, MID_Y + 235)],
        4: [(MID_X + 75, MID_Y + 135), (MID_X + 180, MID_Y + 135),
            (MID_X + 75, MID_Y + 235), (MID_X + 180, MID_Y + 235)]
    }

    for zone in range(1, 5):
        for i in range(min(zone_people[zone], len(student_positions[zone]))):
            sx, sy = student_positions[zone][i]
            draw_student(surface, sx, sy)


# ============================================================
# MAIN LOOP
# ============================================================

clock = pygame.time.Clock()
running = True
dashboard_warning_shown = False

print()
print("======================================")
print("SMART CLASSROOM STARTED")
print("Press Q or ESC to exit.")
print("Dashboard API:", DASHBOARD_API)
print("======================================")
print()

try:
    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
                running = False

        # Read and mirror camera
        ret, frame = cap.read()
        if not ret:
            print("ERROR: Could not read camera frame.")
            break

        frame = cv2.flip(frame, 1)
        height, width = frame.shape[:2]
        mid_x = width // 2
        mid_y = height // 2

        # Reset counts and tracking data for this frame
        zone_people = {1: 0, 2: 0, 3: 0, 4: 0}
        dashboard_tracks = []

        # Run YOLO + ByteTrack. persist=True keeps track IDs across frames.
        results = model.track(
            frame,
            conf=CONFIDENCE,
            persist=True,
            tracker="bytetrack.yaml",
            verbose=False
        )

        for result in results:
            if result.boxes is None:
                continue

            for box in result.boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])

                # COCO class 0 = person
                if class_id != 0 or confidence < CONFIDENCE:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2

                # ByteTrack ID may be None for an untracked detection.
                track_id = None
                if box.id is not None:
                    track_id = int(box.id[0])

                # Original 2 x 2 quadrant mapping
                if center_x < mid_x:
                    zone = 1 if center_y < mid_y else 3
                else:
                    zone = 2 if center_y < mid_y else 4

                zone_people[zone] += 1

                dashboard_tracks.append({
                    "id": track_id if track_id is not None else -1,
                    "zone": zone,
                    "x": round(center_x / max(width, 1), 4),
                    "y": round(center_y / max(height, 1), 4)
                })

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
                label = (
                    f"ID {track_id} {confidence:.2f} - Z{zone}"
                    if track_id is not None
                    else f"Person {confidence:.2f} - Z{zone}"
                )
                cv2.putText(
                    frame, label, (x1, max(y1 - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2
                )

        # Draw camera zone grid
        cv2.line(frame, (mid_x, 0), (mid_x, height), (255, 255, 255), 3)
        cv2.line(frame, (0, mid_y), (width, mid_y), (255, 255, 255), 3)

        zone_labels = [
            ("ZONE 1", (30, 40)),
            ("ZONE 2", (mid_x + 30, 40)),
            ("ZONE 3", (30, mid_y + 40)),
            ("ZONE 4", (mid_x + 30, mid_y + 40))
        ]
        for label, position in zone_labels:
            cv2.putText(
                frame, label, position,
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2
            )

        # Update occupancy status
        zone_status = {
            zone: zone_people[zone] > 0
            for zone in range(1, 5)
        }

        total_people = sum(zone_people.values())
        active_zones = sum(1 for zone in range(1, 5) if zone_status[zone])

        # Update Blynk values. A failed request is retried on the next loop
        # because the value is only cached after a successful response.
        # Read manual overrides set by Blynk through the ESP32.
        refresh_device_controls()

        # Only publish automatic occupancy values to Blynk when that device
        # is in automatic mode. Manual Blynk switch values remain untouched.
        for zone in range(1, 5):
            if manual_overrides[zone]["light"] is None:
                send_if_changed(LIGHT_PINS[zone], int(zone_status[zone]))

            if manual_overrides[zone]["fan"] is None:
                send_if_changed(FAN_PINS[zone], int(zone_status[zone]))

        send_if_changed(PEOPLE_PIN, total_people)
        send_if_changed(ACTIVE_ZONES_PIN, active_zones)

        # Update web dashboard API
        dashboard_ok = send_dashboard_state(
            total_people, active_zones, zone_people, zone_status, dashboard_tracks
        )
        if not dashboard_ok and not dashboard_warning_shown:
            print(
                "Dashboard API is not responding. "
                "Start server.py to enable web dashboard updates."
            )
            dashboard_warning_shown = True
        elif dashboard_ok:
            dashboard_warning_shown = False

        # Animate occupied-zone fans
        for zone in range(1, 5):
            if fan_states[zone]:
                fan_angle[zone] = (fan_angle[zone] + 12) % 360

        # Convert camera frame to Pygame surface
        camera_frame = cv2.resize(frame, (CAM_WIDTH, CAM_HEIGHT))
        camera_frame = cv2.cvtColor(camera_frame, cv2.COLOR_BGR2RGB)
        camera_surface = pygame.surfarray.make_surface(camera_frame.swapaxes(0, 1))

        # Draw main screen
        screen.fill(BLACK)

        title = font_title.render("SMART CLASSROOM - YOLO + BLYNK + DASHBOARD", True, WHITE)
        screen.blit(title, (20, 20))

        camera_label = font_status.render("LIVE CAMERA + PERSON DETECTION", True, WHITE)
        screen.blit(camera_label, (CAM_X, 65))

        classroom_label = font_status.render("VIRTUAL CLASSROOM", True, WHITE)
        screen.blit(classroom_label, (ROOM_X, 65))

        screen.blit(camera_surface, (CAM_X, CAM_Y))
        pygame.draw.rect(screen, WHITE, (CAM_X, CAM_Y, CAM_WIDTH, CAM_HEIGHT), 2)

        draw_classroom(screen)

        # Status bar
        status_y = 620
        pygame.draw.rect(
            screen, (30, 30, 30), (20, status_y, 1360, 130),
            border_radius=10
        )

        people_text = font_status.render(f"TOTAL PEOPLE: {total_people}", True, WHITE)
        screen.blit(people_text, (40, status_y + 15))

        active_text = font_status.render(f"ACTIVE ZONES: {active_zones}/4", True, WHITE)
        screen.blit(active_text, (250, status_y + 15))

        blynk_label = (
            "BLYNK: TOKEN REQUIRED"
            if not BLYNK_TOKEN or BLYNK_TOKEN == "PASTE_YOUR_NEW_BLYNK_TOKEN_HERE"
            else "BLYNK: CONFIGURED"
        )
        blynk_text = font_status.render(blynk_label, True, YELLOW)
        screen.blit(blynk_text, (500, status_y + 15))

        dashboard_text = font_status.render(
            "WEB DASHBOARD: ONLINE" if dashboard_ok else "WEB DASHBOARD: OFFLINE",
            True, GREEN if dashboard_ok else RED
        )
        screen.blit(dashboard_text, (760, status_y + 15))

        zone_positions = {
            1: (40, status_y + 55),
            2: (360, status_y + 55),
            3: (720, status_y + 55),
            4: (1040, status_y + 55)
        }

        for zone in range(1, 5):
            light_text = "ON" if light_states[zone] else "OFF"
            fan_text = "ON" if fan_states[zone] else "OFF"
            text = font_small.render(
                f"Zone {zone}: {zone_people[zone]} person(s) | "
                f"Light {light_text} | Fan {fan_text}",
                True, GREEN if (light_states[zone] or fan_states[zone]) else RED
            )
            screen.blit(text, zone_positions[zone])

        instruction = font_small.render("Press Q or ESC to exit", True, LIGHT_GRAY)
        screen.blit(instruction, (40, status_y + 95))

        pygame.display.flip()
        clock.tick(30)

finally:
    cap.release()
    pygame.quit()
    cv2.destroyAllWindows()
    session.close()
    print()
    print("======================================")
    print("SMART CLASSROOM STOPPED")
    print("======================================")
