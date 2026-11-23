
import pygame
import math
import random
import sys

# ============================================================
# VIRTUAL CLASSROOM
# 4 ZONES - 4 LIGHTS - 4 FANS
# ============================================================

pygame.init()

# -----------------------------
# WINDOW
# -----------------------------
WIDTH = 1200
HEIGHT = 750

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Smart Classroom - Virtual Room")

clock = pygame.time.Clock()

# -----------------------------
# COLORS
# -----------------------------
WHITE = (245, 247, 250)
BLACK = (25, 25, 25)
GRAY = (120, 120, 120)
LIGHT_GRAY = (220, 225, 230)
DARK_GRAY = (55, 60, 65)

BLUE = (45, 120, 220)
GREEN = (50, 180, 100)
RED = (220, 70, 70)
YELLOW = (255, 215, 70)
ORANGE = (245, 150, 50)

ROOM_BG = (235, 238, 242)
FLOOR = (210, 214, 218)

# -----------------------------
# FONTS
# -----------------------------
font_title = pygame.font.SysFont("Arial", 30, bold=True)
font_zone = pygame.font.SysFont("Arial", 22, bold=True)
font_normal = pygame.font.SysFont("Arial", 18)
font_small = pygame.font.SysFont("Arial", 15)
font_big = pygame.font.SysFont("Arial", 24, bold=True)

# -----------------------------
# CLASSROOM AREA
# -----------------------------
ROOM_X = 40
ROOM_Y = 110
ROOM_WIDTH = 1120
ROOM_HEIGHT = 570

MID_X = ROOM_X + ROOM_WIDTH // 2
MID_Y = ROOM_Y + ROOM_HEIGHT // 2

# Zone rectangles
ZONE_RECTS = {
    1: pygame.Rect(ROOM_X, ROOM_Y,
                   ROOM_WIDTH // 2, ROOM_HEIGHT // 2),

    2: pygame.Rect(MID_X, ROOM_Y,
                   ROOM_WIDTH // 2, ROOM_HEIGHT // 2),

    3: pygame.Rect(ROOM_X, MID_Y,
                   ROOM_WIDTH // 2, ROOM_HEIGHT // 2),

    4: pygame.Rect(MID_X, MID_Y,
                   ROOM_WIDTH // 2, ROOM_HEIGHT // 2),
}

# -----------------------------
# ZONE STATUS
# -----------------------------
zone_status = {
    1: False,
    2: False,
    3: False,
    4: False
}

zone_people = {
    1: 0,
    2: 0,
    3: 0,
    4: 0
}

# -----------------------------
# ANIMATION
# -----------------------------
fan_angle = {
    1: 0,
    2: 0,
    3: 0,
    4: 0
}

light_phase = 0

# -----------------------------
# DEMO PEOPLE
# -----------------------------
demo_people = []

random.seed(10)

# Create some sample students
for i in range(8):

    zone = random.randint(1, 4)

    rect = ZONE_RECTS[zone]

    x = random.randint(rect.left + 70, rect.right - 70)
    y = random.randint(rect.top + 100, rect.bottom - 60)

    demo_people.append({
        "zone": zone,
        "x": x,
        "y": y,
        "target_x": x,
        "target_y": y
    })


# ============================================================
# DRAW FUNCTIONS
# ============================================================

def draw_text(text, x, y, font, color=BLACK):

    surface = font.render(text, True, color)
    screen.blit(surface, (x, y))


# ------------------------------------------------------------
# LIGHT
# ------------------------------------------------------------

def draw_light(x, y, zone, is_on):

    if is_on:

        # Light glow
        for radius in range(55, 10, -8):

            alpha_surface = pygame.Surface(
                (radius * 2, radius * 2),
                pygame.SRCALPHA
            )

            alpha = int(20 + (55 - radius) * 2)

            pygame.draw.circle(
                alpha_surface,
                (255, 230, 100, alpha),
                (radius, radius),
                radius
            )

            screen.blit(
                alpha_surface,
                (x - radius, y - radius)
            )

        color = YELLOW

    else:

        color = GRAY

    # Lamp
    pygame.draw.circle(
        screen,
        color,
        (x, y),
        17
    )

    pygame.draw.circle(
        screen,
        DARK_GRAY,
        (x, y),
        17,
        2
    )

    pygame.draw.line(
        screen,
        DARK_GRAY,
        (x, y - 17),
        (x, y - 35),
        3
    )


# ------------------------------------------------------------
# FAN
# ------------------------------------------------------------

def draw_fan(x, y, zone, is_on):

    # Fan housing
    pygame.draw.circle(
        screen,
        DARK_GRAY,
        (x, y),
        32,
        3
    )

    if is_on:

        # Rotate blades
        angle = math.radians(fan_angle[zone])

        for i in range(4):

            blade_angle = angle + i * math.pi / 2

            x1 = x + math.cos(blade_angle) * 7
            y1 = y + math.sin(blade_angle) * 7

            x2 = x + math.cos(blade_angle + 0.55) * 26
            y2 = y + math.sin(blade_angle + 0.55) * 26

            pygame.draw.line(
                screen,
                BLUE,
                (x1, y1),
                (x2, y2),
                7
            )

    else:

        # Static blades
        for i in range(4):

            angle = i * math.pi / 2

            x1 = x + math.cos(angle) * 7
            y1 = y + math.sin(angle) * 7

            x2 = x + math.cos(angle + 0.55) * 23
            y2 = y + math.sin(angle + 0.55) * 23

            pygame.draw.line(
                screen,
                GRAY,
                (x1, y1),
                (x2, y2),
                6
            )

    pygame.draw.circle(
        screen,
        DARK_GRAY,
        (x, y),
        6
    )


# ------------------------------------------------------------
# STUDENT
# ------------------------------------------------------------

def draw_student(x, y):

    # Head
    pygame.draw.circle(
        screen,
        (230, 190, 150),
        (x, y - 20),
        10
    )

    # Body
    pygame.draw.rect(
        screen,
        BLUE,
        (x - 13, y - 10, 26, 32),
        border_radius=7
    )

    # Legs
    pygame.draw.line(
        screen,
        DARK_GRAY,
        (x - 5, y + 22),
        (x - 8, y + 38),
        4
    )

    pygame.draw.line(
        screen,
        DARK_GRAY,
        (x + 5, y + 22),
        (x + 8, y + 38),
        4
    )


# ------------------------------------------------------------
# DESKS
# ------------------------------------------------------------

def draw_desks(rect):

    rows = 2
    cols = 3

    spacing_x = rect.width // (cols + 1)
    spacing_y = rect.height // 4

    for r in range(rows):

        for c in range(cols):

            x = rect.left + spacing_x * (c + 1)
            y = rect.top + 110 + spacing_y * r

            desk_rect = pygame.Rect(
                x - 38,
                y - 12,
                76,
                28
            )

            pygame.draw.rect(
                screen,
                (175, 180, 185),
                desk_rect,
                border_radius=5
            )

            pygame.draw.rect(
                screen,
                DARK_GRAY,
                desk_rect,
                2,
                border_radius=5
            )


# ============================================================
# DRAW ZONE
# ============================================================

def draw_zone(zone):

    rect = ZONE_RECTS[zone]

    occupied = zone_status[zone]

    # Zone background
    if occupied:

        color = (255, 250, 220)

    else:

        color = ROOM_BG

    pygame.draw.rect(
        screen,
        color,
        rect
    )

    # Border
    border_color = GREEN if occupied else LIGHT_GRAY

    pygame.draw.rect(
        screen,
        border_color,
        rect,
        3
    )

    # Zone title
    draw_text(
        f"ZONE {zone}",
        rect.left + 18,
        rect.top + 15,
        font_zone
    )

    # Status
    status = "OCCUPIED" if occupied else "EMPTY"

    status_color = GREEN if occupied else GRAY

    draw_text(
        status,
        rect.left + 18,
        rect.top + 45,
        font_small,
        status_color
    )

    # People count
    draw_text(
        f"People: {zone_people[zone]}",
        rect.left + 18,
        rect.top + 68,
        font_small
    )

    # Light
    light_x = rect.left + rect.width // 2 - 60
    light_y = rect.top + 45

    draw_light(
        light_x,
        light_y,
        zone,
        occupied
    )

    # Fan
    fan_x = rect.right - 60
    fan_y = rect.top + 48

    draw_fan(
        fan_x,
        fan_y,
        zone,
        occupied
    )

    # Labels
    draw_text(
        "LIGHT",
        light_x - 22,
        light_y + 25,
        font_small
    )

    draw_text(
        "FAN",
        fan_x - 15,
        fan_y + 38,
        font_small
    )

    # Desks
    draw_desks(rect)


# ============================================================
# UPDATE DEMO PEOPLE
# ============================================================

def update_people():

    global demo_people

    # Reset counts
    for zone in zone_people:
        zone_people[zone] = 0

    # Count people
    for person in demo_people:

        zone = person["zone"]

        zone_people[zone] += 1

    # Update zone occupancy
    for zone in zone_status:

        zone_status[zone] = zone_people[zone] > 0


# ============================================================
# MAIN LOOP
# ============================================================

running = True

while running:

    # -----------------------------------------
    # EVENTS
    # -----------------------------------------

    for event in pygame.event.get():

        if event.type == pygame.QUIT:

            running = False

        # Press ESC
        if event.type == pygame.KEYDOWN:

            if event.key == pygame.K_ESCAPE:

                running = False

            # Press 1-4 to toggle student
            # in a zone for demonstration
            if event.key in [
                pygame.K_1,
                pygame.K_2,
                pygame.K_3,
                pygame.K_4
            ]:

                selected_zone = event.key - pygame.K_0

                # Add/remove demo student
                existing = None

                for p in demo_people:

                    if p["zone"] == selected_zone:

                        existing = p
                        break

                if existing:

                    demo_people.remove(existing)

                else:

                    rect = ZONE_RECTS[selected_zone]

                    demo_people.append({
                        "zone": selected_zone,
                        "x": random.randint(
                            rect.left + 70,
                            rect.right - 70
                        ),
                        "y": random.randint(
                            rect.top + 120,
                            rect.bottom - 60
                        ),
                        "target_x": 0,
                        "target_y": 0
                    })

    # -----------------------------------------
    # UPDATE
    # -----------------------------------------

    update_people()

    light_phase += 0.05

    # Rotate fans
    for zone in fan_angle:

        if zone_status[zone]:

            fan_angle[zone] += 15

            if fan_angle[zone] >= 360:

                fan_angle[zone] = 0

    # -----------------------------------------
    # DRAW BACKGROUND
    # -----------------------------------------

    screen.fill(WHITE)

    # Title
    draw_text(
        "SMART CLASSROOM",
        40,
        30,
        font_title
    )

    draw_text(
        "AI-Based Occupancy & Virtual Energy Control",
        40,
        65,
        font_small,
        GRAY
    )

    # -----------------------------------------
    # TOP STATISTICS
    # -----------------------------------------

    total_people = sum(zone_people.values())

    active_zones = sum(
        1 for zone in zone_status
        if zone_status[zone]
    )

    draw_text(
        f"TOTAL PEOPLE: {total_people}",
        750,
        35,
        font_normal
    )

    draw_text(
        f"ACTIVE ZONES: {active_zones}/4",
        950,
        35,
        font_normal
    )

    # -----------------------------------------
    # CLASSROOM
    # -----------------------------------------

    pygame.draw.rect(
        screen,
        FLOOR,
        (ROOM_X - 5, ROOM_Y - 5,
         ROOM_WIDTH + 10,
         ROOM_HEIGHT + 10),
        border_radius=8
    )

    for zone in range(1, 5):

        draw_zone(zone)

    # -----------------------------------------
    # DRAW STUDENTS
    # -----------------------------------------

    for person in demo_people:

        draw_student(
            person["x"],
            person["y"]
        )

    # -----------------------------------------
    # FOOTER
    # -----------------------------------------

    draw_text(
        "Press 1 / 2 / 3 / 4 to simulate a person entering a zone",
        40,
        705,
        font_small,
        GRAY
    )

    draw_text(
        "ESC = Exit",
        1030,
        705,
        font_small,
        GRAY
    )

    # -----------------------------------------
    # UPDATE DISPLAY
    # -----------------------------------------

    pygame.display.flip()

    clock.tick(60)


pygame.quit()
sys.exit()

