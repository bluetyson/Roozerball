"""Pygame-specific constants for the Roozerball Tier 2 GUI.

Defines colours, layout dimensions, sprite settings, and animation
parameters used throughout the Pygame renderer and UI.
"""
from __future__ import annotations

from roozerball.engine.constants import Ring

# ---------------------------------------------------------------------------
# Window layout
# ---------------------------------------------------------------------------
WINDOW_WIDTH = 1500
WINDOW_HEIGHT = 900
BOARD_WIDTH = 920
PANEL_X = 930          # Left edge of the right-hand UI panel
PANEL_WIDTH = WINDOW_WIDTH - PANEL_X - 10
FPS = 60

# ---------------------------------------------------------------------------
# Board geometry (matches Tkinter version)
# ---------------------------------------------------------------------------
BOARD_CX = 430
BOARD_CY = 380

RING_RADII: dict[Ring, tuple[int, int]] = {
    Ring.FLOOR:  (40, 90),
    Ring.LOWER:  (90, 150),
    Ring.MIDDLE: (150, 220),
    Ring.UPPER:  (220, 300),
    Ring.CANNON: (300, 340),
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
# Colour palettes
# ---------------------------------------------------------------------------
BG_COLOR = (17, 24, 39)           # #111827
PANEL_BG = (31, 41, 55)           # #1f2937
PANEL_BORDER = (107, 114, 128)    # #6b7280
TEXT_PRIMARY = (249, 250, 251)     # #f9fafb
TEXT_SECONDARY = (156, 163, 175)   # #9ca3af
TEXT_ACCENT = (251, 191, 36)       # #fbbf24
TEXT_HIGHLIGHT = (34, 211, 238)    # #22d3ee

# Team colours
HOME_COLOR = (31, 119, 180)       # #1f77b4
VISITOR_COLOR = (214, 39, 40)     # #d62728

# Track colours
CROWD_SHADES = [
    (shade, shade // 2, shade // 3)
    for shade in (min(255, 25 + i * 8) for i in range(5))
]
RING_FILLS: dict[Ring, tuple[int, int, int]] = {
    Ring.CANNON: (45, 55, 72),
    Ring.UPPER:  (26, 35, 50),
    Ring.MIDDLE: (30, 41, 59),
    Ring.LOWER:  (31, 45, 61),
    Ring.FLOOR:  (28, 36, 49),
}
CENTRAL_FILL = (15, 23, 42)
LANE_LINE = (55, 65, 81)
GOAL_HOME_FILL = (20, 83, 45)
GOAL_VISITOR_FILL = (127, 29, 29)
INITIATIVE_OUTLINE = (147, 197, 253)

# Sprite colours — home
SPRITE_COLORS_HOME: dict[str, dict[str, tuple[int, int, int]]] = {
    "bruiser": {"fill": (59, 130, 246), "accent": (30, 58, 95)},
    "speeder": {"fill": (6, 182, 212),  "accent": (22, 78, 99)},
    "catcher": {"fill": (16, 185, 129), "accent": (6, 78, 59)},
    "biker":   {"fill": (139, 92, 246), "accent": (76, 29, 149)},
}
SPRITE_COLORS_VISITOR: dict[str, dict[str, tuple[int, int, int]]] = {
    "bruiser": {"fill": (239, 68, 68),  "accent": (127, 29, 29)},
    "speeder": {"fill": (249, 115, 22), "accent": (124, 45, 18)},
    "catcher": {"fill": (245, 158, 11), "accent": (120, 53, 15)},
    "biker":   {"fill": (236, 72, 153), "accent": (131, 24, 67)},
}
INJURED_FILL = (75, 85, 99)
INJURED_ACCENT = (55, 65, 81)

# Ball temperature colours
BALL_TEMP_COLORS: dict[str, tuple[int, int, int]] = {
    "very_hot": (255, 32, 32),
    "hot":      (255, 136, 0),
    "warm":     (251, 191, 36),
    "cool":     (96, 165, 250),
}
BALL_GLOW_COLORS: dict[str, tuple[int, int, int]] = {
    "very_hot": (255, 96, 96),
    "hot":      (255, 170, 68),
    "warm":     (253, 230, 138),
    "cool":     (147, 197, 253),
}
BALL_DEFAULT = (249, 115, 22)
BALL_GLOW_DEFAULT = (251, 191, 36)

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
ANIM_STEP_MS = 30
ANIM_STEPS = 12

PARTICLE_LIFETIME_MS = 600
PARTICLE_COUNT_CANNON = 24
PARTICLE_COUNT_CRASH = 12
PARTICLE_COUNT_GOAL = 30

# Camera
CAMERA_LERP_SPEED = 0.08   # interpolation factor per frame
CAMERA_MIN_ZOOM = 0.3
CAMERA_MAX_ZOOM = 3.0
CAMERA_ZOOM_STEP = 0.1

# Lighting
RING_BRIGHTNESS: dict[Ring, float] = {
    Ring.FLOOR:  1.0,
    Ring.LOWER:  0.92,
    Ring.MIDDLE: 0.82,
    Ring.UPPER:  0.72,
    Ring.CANNON: 0.60,
}
SHADOW_LENGTH_FACTOR: dict[Ring, float] = {
    Ring.FLOOR:  0.0,
    Ring.LOWER:  2.0,
    Ring.MIDDLE: 4.0,
    Ring.UPPER:  6.0,
    Ring.CANNON: 8.0,
}
SPOTLIGHT_RADIUS = 80
SPOTLIGHT_ALPHA = 50  # 0-255

# Animated sprites — frame counts per action
ANIM_FRAMES_IDLE = 2
ANIM_FRAMES_MOVE = 4
ANIM_FRAMES_COMBAT = 3
ANIM_FRAME_DURATION_MS = 150   # ms per frame

# ---------------------------------------------------------------------------
# UI geometry
# ---------------------------------------------------------------------------
PANEL_PADDING = 8
PANEL_SECTION_GAP = 6
FONT_SIZE_TITLE = 14
FONT_SIZE_BODY = 12
FONT_SIZE_SMALL = 10
FONT_SIZE_LABEL = 11

BUTTON_HEIGHT = 30
BUTTON_PADDING = 6
BUTTON_COLOR = (55, 65, 81)       # #374151
BUTTON_HOVER = (75, 85, 99)       # #4b5563
BUTTON_TEXT = TEXT_PRIMARY
BUTTON_BORDER = PANEL_BORDER

# Dialog
DIALOG_BG = (31, 41, 55)
DIALOG_BORDER = (107, 114, 128)
DIALOG_OVERLAY_ALPHA = 160

# Modes
MODE_CVC = "Computer vs Computer"
MODE_HVC = "Human vs Computer"

# Scoreboard overlay on canvas
SCOREBOARD_RIGHT = 890
SCOREBOARD_TOP = 12
SCOREBOARD_WIDTH = 240

# Max display limits
MAX_COMBAT_LINES = 3
MAX_DICE_LOG = 20
MAX_LOG_DISPLAY = 200
