"""Tier 3 constants — enhanced palette, layout, and animation parameters.

Builds on Tier 2 values with richer colour gradients, glow parameters,
and scene-graph node settings.
"""
from __future__ import annotations

import math
from roozerball.engine.constants import Ring

# ---------------------------------------------------------------------------
# Window layout
# ---------------------------------------------------------------------------
WINDOW_WIDTH = 1500
WINDOW_HEIGHT = 900
BOARD_WIDTH = 920
PANEL_X = 930
PANEL_WIDTH = WINDOW_WIDTH - PANEL_X - 10
FPS = 60
WINDOW_TITLE = "Roozerball — Tier 3 (Enhanced Pygame)"

# ---------------------------------------------------------------------------
# Board geometry
# ---------------------------------------------------------------------------
BOARD_CX = 430
BOARD_CY = 400

RING_RADII: dict[Ring, tuple[int, int]] = {
    Ring.FLOOR:  (45, 95),
    Ring.LOWER:  (95, 155),
    Ring.MIDDLE: (155, 225),
    Ring.UPPER:  (225, 305),
    Ring.CANNON: (305, 345),
}

SQUARES_PER_RING_MAP: dict[Ring, int] = {
    Ring.FLOOR: 4,
    Ring.LOWER: 4,
    Ring.MIDDLE: 6,
    Ring.UPPER: 6,
    Ring.CANNON: 6,
}

SLOT_OFFSETS: dict[int, list[tuple[int, int]]] = {
    4: [(-12, -10), (12, -10), (-12, 10), (12, 10)],
    6: [(-18, -10), (0, -10), (18, -10), (-18, 10), (0, 10), (18, 10)],
}

# ---------------------------------------------------------------------------
# Colour palette — deeper, richer, with glow variants
# ---------------------------------------------------------------------------
BG_COLOR = (12, 17, 29)
PANEL_BG = (22, 30, 46)
PANEL_BG_LIGHT = (30, 40, 58)
PANEL_BORDER = (70, 80, 100)
PANEL_BORDER_GLOW = (100, 120, 160)
TEXT_PRIMARY = (240, 242, 248)
TEXT_SECONDARY = (140, 150, 170)
TEXT_ACCENT = (255, 200, 50)
TEXT_HIGHLIGHT = (50, 220, 255)
TEXT_SUCCESS = (80, 220, 120)
TEXT_DANGER = (255, 80, 80)

# Team colours — richer with glow
HOME_COLOR = (40, 130, 200)
HOME_GLOW = (60, 160, 255)
VISITOR_COLOR = (220, 50, 50)
VISITOR_GLOW = (255, 80, 80)

# Track colours — layered incline gradient
CROWD_BASE = (20, 12, 8)
CROWD_SHADES = [
    (min(255, 22 + i * 6), min(255, 14 + i * 3), min(255, 10 + i * 2))
    for i in range(6)
]

RING_FILLS: dict[Ring, tuple[int, int, int]] = {
    Ring.CANNON: (38, 48, 68),
    Ring.UPPER:  (22, 30, 45),
    Ring.MIDDLE: (26, 36, 52),
    Ring.LOWER:  (28, 40, 56),
    Ring.FLOOR:  (24, 32, 44),
}
RING_GRADIENT_INNER: dict[Ring, tuple[int, int, int]] = {
    Ring.CANNON: (48, 58, 80),
    Ring.UPPER:  (30, 38, 55),
    Ring.MIDDLE: (34, 44, 62),
    Ring.LOWER:  (36, 48, 66),
    Ring.FLOOR:  (30, 38, 52),
}
CENTRAL_FILL = (10, 16, 30)
CENTRAL_GLOW = (18, 28, 50)
LANE_LINE = (50, 60, 78)
LANE_LINE_BRIGHT = (65, 78, 100)
GOAL_HOME_FILL = (15, 75, 40)
GOAL_HOME_GLOW = (25, 110, 55)
GOAL_VISITOR_FILL = (110, 25, 25)
GOAL_VISITOR_GLOW = (160, 35, 35)
INITIATIVE_OUTLINE = (120, 180, 255)
INITIATIVE_GLOW = (80, 140, 255)

# Sprite colours — per type / team with glow variants
SPRITE_COLORS_HOME: dict[str, dict[str, tuple[int, int, int]]] = {
    "bruiser": {"fill": (65, 140, 255), "accent": (30, 60, 100), "glow": (100, 170, 255)},
    "speeder": {"fill": (10, 200, 225), "accent": (20, 80, 100), "glow": (60, 230, 255)},
    "catcher": {"fill": (20, 200, 140), "accent": (8, 80, 60),   "glow": (60, 230, 170)},
    "biker":   {"fill": (150, 100, 255), "accent": (80, 35, 155), "glow": (180, 140, 255)},
}
SPRITE_COLORS_VISITOR: dict[str, dict[str, tuple[int, int, int]]] = {
    "bruiser": {"fill": (245, 75, 75),  "accent": (130, 30, 30),  "glow": (255, 120, 120)},
    "speeder": {"fill": (255, 125, 30), "accent": (130, 50, 20),  "glow": (255, 160, 80)},
    "catcher": {"fill": (250, 165, 20), "accent": (125, 55, 20),  "glow": (255, 200, 80)},
    "biker":   {"fill": (242, 80, 160), "accent": (135, 28, 70),  "glow": (255, 130, 200)},
}
INJURED_FILL = (60, 70, 85)
INJURED_ACCENT = (45, 55, 70)
INJURED_GLOW = (80, 90, 110)

# Ball temperature colours — with glow and heat shimmer
BALL_TEMP_COLORS: dict[str, tuple[int, int, int]] = {
    "very_hot": (255, 40, 40),
    "hot":      (255, 145, 10),
    "warm":     (255, 200, 50),
    "cool":     (100, 175, 255),
}
BALL_GLOW_COLORS: dict[str, tuple[int, int, int]] = {
    "very_hot": (255, 100, 100),
    "hot":      (255, 180, 70),
    "warm":     (255, 235, 140),
    "cool":     (150, 200, 255),
}
BALL_SHIMMER_COLORS: dict[str, tuple[int, int, int]] = {
    "very_hot": (255, 160, 60),
    "hot":      (255, 200, 100),
    "warm":     (255, 240, 180),
    "cool":     (200, 225, 255),
}
BALL_DEFAULT = (255, 125, 30)
BALL_GLOW_DEFAULT = (255, 200, 50)

# Figure type labels
FIGURE_LABELS: dict[str, str] = {
    "bruiser": "B",
    "speeder": "S",
    "catcher": "C",
    "biker":   "K",
}

# ---------------------------------------------------------------------------
# Animation & effects
# ---------------------------------------------------------------------------
ANIM_STEP_MS = 25
ANIM_STEPS = 16

# Particle system
PARTICLE_LIFETIME_MS = 800
PARTICLE_COUNT_CANNON = 36
PARTICLE_COUNT_CRASH = 18
PARTICLE_COUNT_GOAL = 45
PARTICLE_COUNT_EXHAUST = 3
PARTICLE_COUNT_DUST = 6
PARTICLE_TRAIL_LENGTH = 8
PARTICLE_DEFAULT_COLORS: list[tuple[int, int, int]] = [
    (255, 200, 50), (255, 130, 30), (240, 70, 70), (255, 255, 255),
]

# Camera
CAMERA_LERP_SPEED = 0.06
CAMERA_MIN_ZOOM = 0.3
CAMERA_MAX_ZOOM = 3.0
CAMERA_ZOOM_STEP = 0.1

# Lighting / Incline
RING_BRIGHTNESS: dict[Ring, float] = {
    Ring.FLOOR:  1.0,
    Ring.LOWER:  0.90,
    Ring.MIDDLE: 0.78,
    Ring.UPPER:  0.66,
    Ring.CANNON: 0.54,
}
SHADOW_LENGTH_FACTOR: dict[Ring, float] = {
    Ring.FLOOR:  0.0,
    Ring.LOWER:  2.5,
    Ring.MIDDLE: 5.0,
    Ring.UPPER:  7.5,
    Ring.CANNON: 10.0,
}
SPOTLIGHT_RADIUS = 90
SPOTLIGHT_ALPHA = 55
AMBIENT_GLOW_ALPHA = 15

# Animated sprites
ANIM_FRAMES_IDLE = 3
ANIM_FRAMES_MOVE = 6
ANIM_FRAMES_COMBAT = 4
ANIM_FRAMES_STAND_UP = 3
ANIM_FRAMES_FALL = 2
ANIM_FRAME_DURATION_MS = 120

# Speed lines
SPEED_LINE_COUNT = 3
SPEED_LINE_LENGTH = 20
SPEED_LINE_ALPHA = 120
SPEED_LINE_THRESHOLD = 5  # figures with SPD >= this get speed lines

# Goal flash
GOAL_FLASH_DURATION_MS = 1500
GOAL_FLASH_ALPHA_MAX = 80
GOAL_FLASH_COLOR = (255, 230, 50)

# Ball shimmer animation parameters
SHIMMER_FREQUENCY = 0.004
SHIMMER_AMPLITUDE = 0.3
SHIMMER_BASELINE = 0.7

# Number of sectors on the track
NUM_TRACK_SECTORS = 12

# Text truncation limits
MAX_LOG_ENTRY_LENGTH = 60
MAX_ACTION_TEXT_LENGTH = 80

# ---------------------------------------------------------------------------
# Isometric perspective (optional pseudo-3D)
# ---------------------------------------------------------------------------
ISO_ENABLED_DEFAULT = False
ISO_TILT = 0.6   # vertical compression factor for the elliptical view
ISO_HEIGHT_PER_RING: dict[Ring, float] = {
    Ring.FLOOR:  0.0,
    Ring.LOWER:  8.0,
    Ring.MIDDLE: 18.0,
    Ring.UPPER:  30.0,
    Ring.CANNON: 42.0,
}

# ---------------------------------------------------------------------------
# UI geometry
# ---------------------------------------------------------------------------
PANEL_PADDING = 8
PANEL_SECTION_GAP = 5
PANEL_CORNER_RADIUS = 6
FONT_SIZE_TITLE = 14
FONT_SIZE_BODY = 12
FONT_SIZE_SMALL = 10
FONT_SIZE_LABEL = 11
FONT_SIZE_HEADER = 16

BUTTON_HEIGHT = 30
BUTTON_PADDING = 6
BUTTON_COLOR = (40, 55, 78)
BUTTON_HOVER = (55, 72, 100)
BUTTON_ACTIVE = (70, 90, 120)
BUTTON_TEXT = TEXT_PRIMARY
BUTTON_BORDER = (80, 95, 120)
BUTTON_CORNER_RADIUS = 5

# Dialog
DIALOG_BG = (25, 35, 55)
DIALOG_BORDER = (80, 100, 135)
DIALOG_OVERLAY_ALPHA = 170
DIALOG_CORNER_RADIUS = 8

# Modes
MODE_CVC = "Computer vs Computer"
MODE_HVC = "Human vs Computer"

# Scoreboard overlay
SCOREBOARD_RIGHT = 895
SCOREBOARD_TOP = 14
SCOREBOARD_WIDTH = 250

# Max display limits
MAX_COMBAT_LINES = 4
MAX_DICE_LOG = 25
MAX_LOG_DISPLAY = 250
