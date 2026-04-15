"""Tier 4 constants — realistic graphics parameters.

Extends Tier 3 values with procedural texture, post-processing,
multi-source lighting, crowd, stadium, and atmospheric settings.
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
WINDOW_TITLE = "Roozerball — Tier 4 (Realistic Graphics)"

# ---------------------------------------------------------------------------
# Board geometry (same as Tier 3)
# ---------------------------------------------------------------------------
BOARD_CX = 430
BOARD_CY = 460

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
# Colour palette — cinematic dark theme
# ---------------------------------------------------------------------------
BG_COLOR = (8, 12, 22)
PANEL_BG = (16, 22, 36)
PANEL_BG_LIGHT = (24, 32, 50)
PANEL_BORDER = (55, 70, 95)
PANEL_BORDER_GLOW = (80, 110, 160)
TEXT_PRIMARY = (235, 238, 245)
TEXT_SECONDARY = (130, 142, 165)
TEXT_ACCENT = (255, 210, 60)
TEXT_HIGHLIGHT = (60, 200, 255)
TEXT_SUCCESS = (80, 220, 120)
TEXT_DANGER = (255, 75, 75)

# Sky gradient (top of stadium)
SKY_TOP = (6, 8, 18)
SKY_BOTTOM = (15, 20, 35)

# Team colours
HOME_COLOR = (45, 135, 210)
HOME_GLOW = (70, 170, 255)
HOME_SECONDARY = (35, 100, 170)
VISITOR_COLOR = (225, 55, 55)
VISITOR_GLOW = (255, 90, 90)
VISITOR_SECONDARY = (175, 35, 35)

# Track surface — multi-layered concrete/asphalt look
TRACK_BASE = (42, 48, 58)
TRACK_GRAIN_LIGHT = (52, 58, 68)
TRACK_GRAIN_DARK = (32, 38, 48)
TRACK_LANE_MARKING = (80, 90, 110)
TRACK_SCUFF_COLOR = (36, 42, 52)

# Crowd stands
CROWD_BASE = (18, 12, 8)
CROWD_SHADES = [
    (min(255, 20 + i * 5), min(255, 13 + i * 3), min(255, 9 + i * 2))
    for i in range(8)
]
CROWD_SILHOUETTE_COLORS = [
    (30, 22, 18), (35, 26, 20), (28, 20, 15), (32, 24, 18),
]
CROWD_HIGHLIGHT = (55, 40, 30)

# Ring fills — deeper, more textured
RING_FILLS: dict[Ring, tuple[int, int, int]] = {
    Ring.CANNON: (35, 44, 62),
    Ring.UPPER:  (20, 28, 42),
    Ring.MIDDLE: (24, 34, 50),
    Ring.LOWER:  (26, 38, 54),
    Ring.FLOOR:  (22, 30, 42),
}
RING_GRADIENT_INNER: dict[Ring, tuple[int, int, int]] = {
    Ring.CANNON: (45, 55, 76),
    Ring.UPPER:  (28, 36, 52),
    Ring.MIDDLE: (32, 42, 60),
    Ring.LOWER:  (34, 46, 64),
    Ring.FLOOR:  (28, 36, 50),
}
CENTRAL_FILL = (8, 14, 28)
CENTRAL_GLOW = (16, 26, 48)
LANE_LINE = (48, 58, 75)
LANE_LINE_BRIGHT = (62, 76, 98)
GOAL_HOME_FILL = (12, 70, 38)
GOAL_HOME_GLOW = (22, 105, 52)
GOAL_VISITOR_FILL = (105, 22, 22)
GOAL_VISITOR_GLOW = (155, 32, 32)
INITIATIVE_OUTLINE = (120, 180, 255)
INITIATIVE_GLOW = (80, 140, 255)

# Sprite colours — per type / team with specular highlights
SPRITE_COLORS_HOME: dict[str, dict[str, tuple[int, int, int]]] = {
    "bruiser": {"fill": (60, 135, 250), "accent": (28, 58, 95), "glow": (95, 165, 255), "specular": (180, 215, 255)},
    "speeder": {"fill": (10, 195, 220), "accent": (18, 78, 98), "glow": (55, 225, 255), "specular": (170, 250, 255)},
    "catcher": {"fill": (18, 195, 135), "accent": (8, 78, 58), "glow": (55, 225, 165), "specular": (160, 255, 215)},
    "biker":   {"fill": (145, 95, 250),  "accent": (78, 32, 150), "glow": (175, 135, 255), "specular": (215, 195, 255)},
}
SPRITE_COLORS_VISITOR: dict[str, dict[str, tuple[int, int, int]]] = {
    "bruiser": {"fill": (240, 70, 70),  "accent": (125, 28, 28), "glow": (255, 115, 115), "specular": (255, 195, 195)},
    "speeder": {"fill": (250, 120, 28), "accent": (125, 48, 18), "glow": (255, 155, 75), "specular": (255, 210, 165)},
    "catcher": {"fill": (245, 160, 18), "accent": (120, 52, 18), "glow": (255, 195, 75), "specular": (255, 235, 175)},
    "biker":   {"fill": (238, 75, 155), "accent": (130, 25, 68), "glow": (255, 125, 195), "specular": (255, 195, 235)},
}
INJURED_FILL = (55, 65, 80)
INJURED_ACCENT = (42, 52, 66)
INJURED_GLOW = (75, 85, 105)
INJURED_SPECULAR = (100, 110, 130)

# Ball temperature colours — with metallic sheen
BALL_TEMP_COLORS: dict[str, tuple[int, int, int]] = {
    "very_hot": (255, 35, 35),
    "hot":      (255, 140, 8),
    "warm":     (255, 195, 45),
    "cool":     (95, 170, 250),
}
BALL_GLOW_COLORS: dict[str, tuple[int, int, int]] = {
    "very_hot": (255, 95, 95),
    "hot":      (255, 175, 65),
    "warm":     (255, 230, 135),
    "cool":     (145, 195, 255),
}
BALL_SHIMMER_COLORS: dict[str, tuple[int, int, int]] = {
    "very_hot": (255, 155, 55),
    "hot":      (255, 195, 95),
    "warm":     (255, 235, 175),
    "cool":     (195, 220, 255),
}
BALL_SPECULAR = (255, 255, 255)
BALL_DEFAULT = (255, 120, 28)
BALL_GLOW_DEFAULT = (255, 195, 45)

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
PARTICLE_COUNT_CANNON = 48
PARTICLE_COUNT_CRASH = 24
PARTICLE_COUNT_GOAL = 60
PARTICLE_COUNT_EXHAUST = 4
PARTICLE_COUNT_DUST = 8
PARTICLE_COUNT_SPARKS = 12
PARTICLE_COUNT_EMBERS = 6
PARTICLE_TRAIL_LENGTH = 10
PARTICLE_DEFAULT_COLORS: list[tuple[int, int, int]] = [
    (255, 200, 50), (255, 130, 30), (240, 70, 70), (255, 255, 255),
]

# Ambient particles (atmospheric dust motes)
AMBIENT_PARTICLE_COUNT = 40
AMBIENT_PARTICLE_LIFETIME_MS = 4000
AMBIENT_PARTICLE_COLORS = [
    (80, 85, 100), (90, 95, 110), (70, 75, 90), (100, 105, 120),
]
AMBIENT_PARTICLE_SIZE_RANGE = (1.0, 3.0)
AMBIENT_PARTICLE_SPEED_RANGE = (0.05, 0.2)

# Camera
CAMERA_LERP_SPEED = 0.06
CAMERA_MIN_ZOOM = 0.3
CAMERA_MAX_ZOOM = 3.0
CAMERA_ZOOM_STEP = 0.1

# Screen shake
SHAKE_CRASH_MAGNITUDE = 6.0
SHAKE_CRASH_DURATION_MS = 350
SHAKE_GOAL_MAGNITUDE = 4.0
SHAKE_GOAL_DURATION_MS = 500
SHAKE_CANNON_MAGNITUDE = 8.0
SHAKE_CANNON_DURATION_MS = 400
SHAKE_DECAY = 0.92

# Lighting / Incline
RING_BRIGHTNESS: dict[Ring, float] = {
    Ring.FLOOR:  1.0,
    Ring.LOWER:  0.88,
    Ring.MIDDLE: 0.75,
    Ring.UPPER:  0.62,
    Ring.CANNON: 0.50,
}
SHADOW_LENGTH_FACTOR: dict[Ring, float] = {
    Ring.FLOOR:  0.0,
    Ring.LOWER:  3.0,
    Ring.MIDDLE: 6.0,
    Ring.UPPER:  9.5,
    Ring.CANNON: 12.0,
}

# Multi-source stadium lighting
FLOODLIGHT_POSITIONS = [
    (-0.8, -1.0),   # top-left
    (0.8, -1.0),    # top-right
    (-1.0, 0.3),    # left
    (1.0, 0.3),     # right
]
FLOODLIGHT_COLOR = (255, 248, 235)
FLOODLIGHT_INTENSITY = 0.35
FLOODLIGHT_FALLOFF = 0.002

SPOTLIGHT_RADIUS = 100
SPOTLIGHT_ALPHA = 60
AMBIENT_GLOW_ALPHA = 12

# Animated sprites
ANIM_FRAMES_IDLE = 3
ANIM_FRAMES_MOVE = 6
ANIM_FRAMES_COMBAT = 4
ANIM_FRAMES_STAND_UP = 3
ANIM_FRAMES_FALL = 2
ANIM_FRAME_DURATION_MS = 120

# Speed lines
SPEED_LINE_COUNT = 4
SPEED_LINE_LENGTH = 25
SPEED_LINE_ALPHA = 130
SPEED_LINE_THRESHOLD = 5

# Motion blur afterimages
MOTION_BLUR_COUNT = 3
MOTION_BLUR_ALPHA_STEP = 35

# Goal flash
GOAL_FLASH_DURATION_MS = 1800
GOAL_FLASH_ALPHA_MAX = 90
GOAL_FLASH_COLOR = (255, 235, 55)

# Ball shimmer animation parameters
SHIMMER_FREQUENCY = 0.004
SHIMMER_AMPLITUDE = 0.35
SHIMMER_BASELINE = 0.7

# Ball afterimage trail
BALL_TRAIL_LENGTH = 5
BALL_TRAIL_ALPHA_STEP = 30

# Number of sectors on the track
NUM_TRACK_SECTORS = 12

# Text truncation limits
MAX_LOG_ENTRY_LENGTH = 60
MAX_ACTION_TEXT_LENGTH = 80

# ---------------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------------
BLOOM_ENABLED = True
BLOOM_THRESHOLD = 180
BLOOM_INTENSITY = 0.4
BLOOM_BLUR_PASSES = 2
BLOOM_DOWNSCALE = 4

VIGNETTE_ENABLED = True
VIGNETTE_STRENGTH = 0.55
VIGNETTE_RADIUS = 0.75

# Heat distortion near ball
HEAT_DISTORTION_ENABLED = True
HEAT_DISTORTION_RADIUS = 40
HEAT_DISTORTION_AMPLITUDE = 2.0
HEAT_DISTORTION_FREQUENCY = 0.006

# ---------------------------------------------------------------------------
# Procedural textures
# ---------------------------------------------------------------------------
TEXTURE_NOISE_SCALE = 3
TEXTURE_NOISE_OCTAVES = 3
TEXTURE_GRAIN_INTENSITY = 8
TEXTURE_LANE_WIDTH = 2
TEXTURE_SCUFF_COUNT = 60
TEXTURE_SCUFF_SIZE_RANGE = (2, 6)

# ---------------------------------------------------------------------------
# Crowd / Stadium
# ---------------------------------------------------------------------------
CROWD_DENSITY = 50  # silhouettes per sector
CROWD_BOB_SPEED = 0.002
CROWD_BOB_AMPLITUDE = 2.0
CROWD_WAVE_SPEED = 0.001

STADIUM_WALL_COLOR = (35, 40, 55)
STADIUM_WALL_HIGHLIGHT = (50, 58, 78)
STADIUM_RAILING_COLOR = (65, 75, 95)
STADIUM_LIGHT_RIG_COLOR = (50, 55, 70)

# ---------------------------------------------------------------------------
# Isometric perspective (optional pseudo-3D)
# ---------------------------------------------------------------------------
ISO_ENABLED_DEFAULT = False
ISO_TILT = 0.6
ISO_HEIGHT_PER_RING: dict[Ring, float] = {
    Ring.FLOOR:  0.0,
    Ring.LOWER:  8.0,
    Ring.MIDDLE: 18.0,
    Ring.UPPER:  30.0,
    Ring.CANNON: 42.0,
}

# ---------------------------------------------------------------------------
# UI geometry — glass-morphism style
# ---------------------------------------------------------------------------
PANEL_PADDING = 8
PANEL_SECTION_GAP = 5
PANEL_CORNER_RADIUS = 8
PANEL_GLASS_ALPHA = 185
PANEL_GLASS_BORDER_ALPHA = 60
FONT_SIZE_TITLE = 14
FONT_SIZE_BODY = 12
FONT_SIZE_SMALL = 10
FONT_SIZE_LABEL = 11
FONT_SIZE_HEADER = 16

BUTTON_HEIGHT = 30
BUTTON_PADDING = 6
BUTTON_COLOR = (35, 48, 72)
BUTTON_HOVER = (48, 65, 95)
BUTTON_ACTIVE = (62, 82, 115)
BUTTON_TEXT = TEXT_PRIMARY
BUTTON_BORDER = (75, 90, 118)
BUTTON_CORNER_RADIUS = 6
BUTTON_GRADIENT_TOP = (45, 58, 82)
BUTTON_GRADIENT_BOTTOM = (30, 42, 65)

# Dialog — glass-morphism
DIALOG_BG = (20, 30, 50)
DIALOG_BORDER = (75, 95, 130)
DIALOG_OVERLAY_ALPHA = 185
DIALOG_CORNER_RADIUS = 10
DIALOG_GLASS_ALPHA = 195

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
