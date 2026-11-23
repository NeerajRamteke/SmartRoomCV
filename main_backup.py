import cv2
import pygame
import math
import requests
import sys
from ultralytics import YOLO


# ============================================================
# BLYNK CONFIGURATION
# ============================================================

BLYNK_TOKEN = "BG1mpn5ebeL9QbJXc4prqlM4S_tqr3o0"
BLYNK_URL = "https://blynk.cloud/external/api/update"


# ============================================================
# YOLO CONFIGURATION
# ============================================================

MODEL_PATH = "yolo11n.pt"
CONFIDENCE = 0.50
CAMERA_INDEX = 0


# ============================================================
# BLYNK VIRTUAL PINS
# ============================================================

LIGHT_PINS = {
    1: "V0",
    2: "V2",
    3: "V4",
    4: "V6"
}

FAN_PINS = {
    1: "V1",
    2: "V3",
    3: "V5",
    4: "V7"
}

PEOPLE_PIN = "V8"
ACTIVE_ZONES_PIN = "V9"


# ============================================================
# BLYNK SESSION
# ============================================================

session = requests.Session()

last_sent = {}


def update_blynk(pin, value):
    try:
        url = f"{BLYNK_URL}?token={BLYNK_TOKEN}&{pin}={value}"

        response = session.get(url, timeout=2)

        if response.status_code == 200:
            return True

        print(f"Blynk error for {pin}: {response.status_code}")

    except requests.RequestException as e:
        print(f"Blynk connection error: {e}")

    return False


def send_if_changed(pin, value):

    if last_sent.get(pin) != value:

        if update_blynk(pin, value):
            last_sent[pin] = value


# ============================================================
# LOAD YOLO MODEL
# ============================================================

print("Loading YOLO model...")

model = YOLO(MODEL_PATH)

print("YOLO model loaded successfully.")


# ============================================================
# OPEN CAMERA
# ============================================================

cap = cv2.VideoCapture(CAMERA_INDEX)

if not cap.isOpened():
    print("ERROR: Could not open camera.")
    sys.exit()


# ============================================================
# INITIALIZE PYGAME
# ============================================================

pygame.init()

SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 780

screen = pygame.display.set_mode(
    (SCREEN_WIDTH, SCREEN_HEIGHT)
)

pygame.display.set_caption(
    "Smart Classroom - YOLO + Blynk"
)


# ============================================================
# COLORS
# ============================================================

BLACK = (20, 20, 20)
WHITE = (245, 245, 245)
GRAY = (80, 80, 80)
LIGHT_GRAY = (170, 170, 170)

GREEN = (50, 220, 100)
RED = (230, 60, 60)
BLUE = (70, 150, 255)
YELLOW = (255, 220, 70)
ORANGE = (255, 150, 50)


# ============================================================
# FONTS
# ============================================================

font_title = pygame.font.SysFont(
    "Arial",
    28,
    bold=True
)

font_zone = pygame.font.SysFont(
    "Arial",
    22,
    bold=True
)

font_status = pygame.font.SysFont(
    "Arial",
    18
)

font_small = pygame.font.SysFont(
    "Arial",
    16
)


# ============================================================
# CAMERA DISPLAY AREA
# ============================================================

CAM_X = 20
CAM_Y = 90

CAM_WIDTH = 670
CAM_HEIGHT = 500


# ============================================================
# VIRTUAL CLASSROOM AREA
# ============================================================

ROOM_X = 720
ROOM_Y = 90

ROOM_WIDTH = 660
ROOM_HEIGHT = 500


# ============================================================
# CLASSROOM ZONE POSITIONS
# ============================================================

MID_X = ROOM_X + ROOM_WIDTH // 2
MID_Y = ROOM_Y + ROOM_HEIGHT // 2


ZONE_RECTS = {

    1: (
        ROOM_X,
        ROOM_Y,
        ROOM_WIDTH // 2,
        ROOM_HEIGHT // 2
    ),

    2: (
        MID_X,
        ROOM_Y,
        ROOM_WIDTH // 2,
        ROOM_HEIGHT // 2
    ),

    3: (
        ROOM_X,
        MID_Y,
        ROOM_WIDTH // 2,
        ROOM_HEIGHT // 2
    ),

    4: (
        MID_X,
        MID_Y,
        ROOM_WIDTH // 2,
        ROOM_HEIGHT // 2
    )
}


# ============================================================
# ZONE DATA
# ============================================================

zone_people = {
    1: 0,
    2: 0,
    3: 0,
    4: 0
}

zone_status = {
    1: False,
    2: False,
    3: False,
    4: False
}

fan_angle = {
    1: 0,
    2: 0,
    3: 0,
    4: 0
}


# ============================================================
# DRAW VIRTUAL LIGHT
# ============================================================

def draw_light(surface, x, y, is_on):

    if is_on:

        # Outer glow
        for radius in range(35, 10, -5):

            alpha_surface = pygame.Surface(
                (radius * 2, radius * 2),
                pygame.SRCALPHA
            )

            alpha = max(
                0,
                80 - radius
            )

            pygame.draw.circle(
                alpha_surface,
                (255, 220, 70, alpha),
                (radius, radius),
                radius
            )

            surface.blit(
                alpha_surface,
                (
                    x - radius,
                    y - radius
                )
            )

        pygame.draw.circle(
            surface,
            YELLOW,
            (x, y),
            12
        )

        pygame.draw.circle(
            surface,
            WHITE,
            (x, y),
            5
        )

    else:

        pygame.draw.circle(
            surface,
            GRAY,
            (x, y),
            10
        )


# ============================================================
# DRAW FAN
# ============================================================

def draw_fan(surface, x, y, angle, is_on):

    pygame.draw.circle(
        surface,
        GRAY,
        (x, y),
        35,
        3
    )

    pygame.draw.circle(
        surface,
        LIGHT_GRAY,
        (x, y),
        8
    )

    for i in range(4):

        current_angle = angle + (i * 90)

        rad = math.radians(
            current_angle
        )

        end_x = x + int(
            math.cos(rad) * 30
        )

        end_y = y + int(
            math.sin(rad) * 30
        )

        pygame.draw.line(
            surface,
            WHITE if is_on else GRAY,
            (x, y),
            (end_x, end_y),
            7
        )


# ============================================================
# DRAW DESKS
# ============================================================

def draw_desk(surface, x, y):

    pygame.draw.rect(
        surface,
        (100, 100, 100),
        (x, y, 80, 35),
        border_radius=5
    )

    pygame.draw.line(
        surface,
        GRAY,
        (x + 10, y + 35),
        (x + 10, y + 50),
        4
    )

    pygame.draw.line(
        surface,
        GRAY,
        (x + 70, y + 35),
        (x + 70, y + 50),
        4
    )


# ============================================================
# DRAW STUDENT
# ============================================================

def draw_student(surface, x, y):

    pygame.draw.circle(
        surface,
        BLUE,
        (x, y),
        10
    )

    pygame.draw.line(
        surface,
        BLUE,
        (x, y + 10),
        (x, y + 30),
        5
    )


# ============================================================
# DRAW CLASSROOM
# ============================================================

def draw_classroom(surface):

    pygame.draw.rect(
        surface,
        (35, 35, 35),
        (
            ROOM_X,
            ROOM_Y,
            ROOM_WIDTH,
            ROOM_HEIGHT
        )
    )

    # Zone backgrounds
    for zone in range(1, 5):

        x, y, w, h = ZONE_RECTS[zone]

        if zone_status[zone]:

            pygame.draw.rect(
                surface,
                (45, 65, 50),
                (x, y, w, h)
            )

        else:

            pygame.draw.rect(
                surface,
                (35, 35, 35),
                (x, y, w, h)
            )

        pygame.draw.rect(
            surface,
            GRAY,
            (x, y, w, h),
            2
        )

    # Zone dividing lines
    pygame.draw.line(
        surface,
        WHITE,
        (MID_X, ROOM_Y),
        (MID_X, ROOM_Y + ROOM_HEIGHT),
        2
    )

    pygame.draw.line(
        surface,
        WHITE,
        (ROOM_X, MID_Y),
        (ROOM_X + ROOM_WIDTH, MID_Y),
        2
    )

    # Zone labels
    for zone in range(1, 5):

        x, y, w, h = ZONE_RECTS[zone]

        label = font_zone.render(
            f"ZONE {zone}",
            True,
            WHITE
        )

        surface.blit(
            label,
            (x + 15, y + 15)
        )

    # Fan and light positions
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

    # Draw fans and lights
    for zone in range(1, 5):

        fan_x, fan_y = fan_positions[zone]

        light_x, light_y = light_positions[zone]

        draw_fan(
            surface,
            fan_x,
            fan_y,
            fan_angle[zone],
            zone_status[zone]
        )

        draw_light(
            surface,
            light_x,
            light_y,
            zone_status[zone]
        )

    # Draw desks
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

        draw_desk(
            surface,
            x,
            y
        )

    # Draw virtual students based on people detected
    student_positions = {

        1: [
            (ROOM_X + 75, ROOM_Y + 135),
            (ROOM_X + 180, ROOM_Y + 135),
            (ROOM_X + 75, ROOM_Y + 235),
            (ROOM_X + 180, ROOM_Y + 235)
        ],

        2: [
            (MID_X + 75, ROOM_Y + 135),
            (MID_X + 180, ROOM_Y + 135),
            (MID_X + 75, ROOM_Y + 235),
            (MID_X + 180, ROOM_Y + 235)
        ],

        3: [
            (ROOM_X + 75, MID_Y + 135),
            (ROOM_X + 180, MID_Y + 135),
            (ROOM_X + 75, MID_Y + 235),
            (ROOM_X + 180, MID_Y + 235)
        ],

        4: [
            (MID_X + 75, MID_Y + 135),
            (MID_X + 180, MID_Y + 135),
            (MID_X + 75, MID_Y + 235),
            (MID_X + 180, MID_Y + 235)
        ]
    }

    for zone in range(1, 5):

        number_of_students = min(
            zone_people[zone],
            4
        )

        for i in range(number_of_students):

            sx, sy = student_positions[zone][i]

            draw_student(
                surface,
                sx,
                sy
            )


# ============================================================
# MAIN LOOP
# ============================================================

clock = pygame.time.Clock()

running = True

print()
print("======================================")
print("SMART CLASSROOM STARTED")
print("======================================")
print("Press Q or ESC to exit.")
print()


while running:

    # ========================================================
    # HANDLE PYGAME EVENTS
    # ========================================================

    for event in pygame.event.get():

        if event.type == pygame.QUIT:

            running = False

        elif event.type == pygame.KEYDOWN:

            if event.key in (
                pygame.K_ESCAPE,
                pygame.K_q
            ):

                running = False


    # ========================================================
    # READ CAMERA
    # ========================================================

    ret, frame = cap.read()

    if not ret:

        print("ERROR: Could not read camera frame.")

        break


    # Mirror camera
    frame = cv2.flip(
        frame,
        1
    )


    height, width = frame.shape[:2]

    # Camera zone boundaries
    mid_x = width // 2
    mid_y = height // 2


    # ========================================================
    # RESET ZONE COUNTS
    # ========================================================

    zone_people = {
        1: 0,
        2: 0,
        3: 0,
        4: 0
    }


    # ========================================================
    # YOLO DETECTION
    # ========================================================

    results = model(
        frame,
        verbose=False
    )


    for result in results:

        if result.boxes is None:
            continue


        for box in result.boxes:

            confidence = float(
                box.conf[0]
            )

            class_id = int(
                box.cls[0]
            )


            # Only detect persons
            if class_id != 0:
                continue


            if confidence < CONFIDENCE:
                continue


            # Get bounding box
            x1, y1, x2, y2 = map(
                int,
                box.xyxy[0]
            )


            # Find center of person
            center_x = (
                x1 + x2
            ) // 2

            center_y = (
                y1 + y2
            ) // 2


            # =================================================
            # DETERMINE ZONE
            # =================================================

            if center_x < mid_x:

                if center_y < mid_y:
                    zone = 1
                else:
                    zone = 3

            else:

                if center_y < mid_y:
                    zone = 2
                else:
                    zone = 4


            # Increase people count
            zone_people[zone] += 1


            # =================================================
            # DRAW PERSON BOX
            # =================================================

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )


            # Draw center point
            cv2.circle(
                frame,
                (center_x, center_y),
                5,
                (0, 0, 255),
                -1
            )


            # Person label
            label = (
                f"Person "
                f"{confidence:.2f} "
                f"- Z{zone}"
            )


            cv2.putText(
                frame,
                label,
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )


    # ========================================================
    # DRAW CAMERA ZONE GRID
    # ========================================================

    cv2.line(
        frame,
        (mid_x, 0),
        (mid_x, height),
        (255, 255, 255),
        3
    )


    cv2.line(
        frame,
        (0, mid_y),
        (width, mid_y),
        (255, 255, 255),
        3
    )


    # ========================================================
    # DRAW ZONE LABELS
    # ========================================================

    cv2.putText(
        frame,
        "ZONE 1",
        (30, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (255, 255, 255),
        2
    )


    cv2.putText(
        frame,
        "ZONE 2",
        (mid_x + 30, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (255, 255, 255),
        2
    )


    cv2.putText(
        frame,
        "ZONE 3",
        (30, mid_y + 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (255, 255, 255),
        2
    )


    cv2.putText(
        frame,
        "ZONE 4",
        (mid_x + 30, mid_y + 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (255, 255, 255),
        2
    )


    # ========================================================
    # UPDATE ZONE STATUS
    # ========================================================

    for zone in range(1, 5):

        zone_status[zone] = (
            zone_people[zone] > 0
        )


    # ========================================================
    # UPDATE BLYNK
    # ========================================================

    for zone in range(1, 5):

        state = int(
            zone_status[zone]
        )


        # Light
        send_if_changed(
            LIGHT_PINS[zone],
            state
        )


        # Fan
        send_if_changed(
            FAN_PINS[zone],
            state
        )


    # Total number of people
    total_people = sum(
        zone_people.values()
    )


    # Number of occupied zones
    active_zones = sum(
        1
        for zone in range(1, 5)
        if zone_status[zone]
    )


    # Send total people
    send_if_changed(
        PEOPLE_PIN,
        total_people
    )


    # Send active zones
    send_if_changed(
        ACTIVE_ZONES_PIN,
        active_zones
    )


    # ========================================================
    # ANIMATE FANS
    # ========================================================

    for zone in range(1, 5):

        if zone_status[zone]:

            fan_angle[zone] += 12

            if fan_angle[zone] >= 360:

                fan_angle[zone] -= 360


    # ========================================================
    # PREPARE CAMERA FOR PYGAME
    # ========================================================

    camera_frame = cv2.resize(
        frame,
        (CAM_WIDTH, CAM_HEIGHT)
    )


    # OpenCV BGR -> RGB
    camera_frame = cv2.cvtColor(
        camera_frame,
        cv2.COLOR_BGR2RGB
    )


    # Convert to Pygame surface
    camera_surface = pygame.surfarray.make_surface(
        camera_frame.swapaxes(0, 1)
    )


    # ========================================================
    # DRAW MAIN SCREEN
    # ========================================================

    screen.fill(
        BLACK
    )


    # ========================================================
    # TITLE
    # ========================================================

    title = font_title.render(
        "SMART CLASSROOM - YOLO + BLYNK",
        True,
        WHITE
    )


    screen.blit(
        title,
        (20, 20)
    )


    # ========================================================
    # CAMERA LABEL
    # ========================================================

    camera_label = font_status.render(
        "LIVE CAMERA + PERSON DETECTION",
        True,
        WHITE
    )


    screen.blit(
        camera_label,
        (CAM_X, 65)
    )


    # ========================================================
    # CLASSROOM LABEL
    # ========================================================

    classroom_label = font_status.render(
        "VIRTUAL CLASSROOM",
        True,
        WHITE
    )


    screen.blit(
        classroom_label,
        (ROOM_X, 65)
    )


    # ========================================================
    # DRAW CAMERA
    # ========================================================

    screen.blit(
        camera_surface,
        (CAM_X, CAM_Y)
    )


    # Camera border
    pygame.draw.rect(
        screen,
        WHITE,
        (
            CAM_X,
            CAM_Y,
            CAM_WIDTH,
            CAM_HEIGHT
        ),
        2
    )


    # ========================================================
    # DRAW VIRTUAL CLASSROOM
    # ========================================================

    draw_classroom(
        screen
    )


    # ========================================================
    # STATUS BAR
    # ========================================================

    STATUS_Y = 620


    pygame.draw.rect(
        screen,
        (30, 30, 30),
        (
            20,
            STATUS_Y,
            1360,
            130
        ),
        border_radius=10
    )


    # ========================================================
    # TOTAL PEOPLE
    # ========================================================

    people_text = font_status.render(
        f"TOTAL PEOPLE: {total_people}",
        True,
        WHITE
    )


    screen.blit(
        people_text,
        (40, STATUS_Y + 15)
    )


    # ========================================================
    # ACTIVE ZONES
    # ========================================================

    active_text = font_status.render(
        f"ACTIVE ZONES: {active_zones}/4",
        True,
        WHITE
    )


    screen.blit(
        active_text,
        (250, STATUS_Y + 15)
    )


    # ========================================================
    # BLYNK STATUS
    # ========================================================

    blynk_text = font_status.render(
        "BLYNK: CONNECTED",
        True,
        GREEN
    )


    screen.blit(
        blynk_text,
        (500, STATUS_Y + 15)
    )


    # ========================================================
    # ZONE STATUS
    # ========================================================

    for zone in range(1, 5):

        state_text = "ON" if zone_status[zone] else "OFF"

        state_color = (
            GREEN
            if zone_status[zone]
            else RED
        )


        text = font_small.render(
            f"Zone {zone}: "
            f"{zone_people[zone]} person(s) | "
            f"Light {state_text} | "
            f"Fan {state_text}",
            True,
            state_color
        )


        if zone == 1:

            x = 40
            y = STATUS_Y + 55

        elif zone == 2:

            x = 360
            y = STATUS_Y + 55

        elif zone == 3:

            x = 720
            y = STATUS_Y + 55

        else:

            x = 1040
            y = STATUS_Y + 55


        screen.blit(
            text,
            (x, y)
        )


    # ========================================================
    # INSTRUCTIONS
    # ========================================================

    instruction = font_small.render(
        "Press Q or ESC to exit",
        True,
        LIGHT_GRAY
    )


    screen.blit(
        instruction,
        (40, STATUS_Y + 95)
    )


    # ========================================================
    # UPDATE DISPLAY
    # ========================================================

    pygame.display.flip()


    # ========================================================
    # LIMIT FPS
    # ========================================================

    clock.tick(30)


# ============================================================
# CLEANUP
# ============================================================

cap.release()

pygame.quit()

cv2.destroyAllWindows()

print()
print("======================================")
print("SMART CLASSROOM STOPPED")
print("======================================")