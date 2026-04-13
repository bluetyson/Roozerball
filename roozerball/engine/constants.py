"""Roozerball game constants and enumerations.

All game rules constants extracted from the Roozerball rules document.
"""
from __future__ import annotations
from enum import Enum, IntEnum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Phase(Enum):
    CLOCK = "clock"
    BALL = "ball"
    INITIATIVE = "initiative"
    MOVEMENT = "movement"
    COMBAT = "combat"
    SCORING = "scoring"


class Ring(IntEnum):
    FLOOR = 0
    LOWER = 1
    MIDDLE = 2
    UPPER = 3
    CANNON = 4


class FigureType(Enum):
    SKATER_BRUISER = "bruiser"
    SKATER_SPEEDER = "speeder"
    CATCHER = "catcher"
    BIKER = "biker"


class FigureStatus(Enum):
    STANDING = "standing"
    FALLEN = "fallen"
    SHAKEN = "shaken"
    BADLY_SHAKEN = "badly_shaken"
    INJURED = "injured"
    UNCONSCIOUS = "unconscious"
    DEAD = "dead"
    MAN_TO_MAN = "man_to_man"
    OUT_OF_CONTENTION = "out_of_contention"


class BallState(Enum):
    IN_CANNON = "in_cannon"
    ON_TRACK = "on_track"
    FIELDED = "fielded"
    DEAD = "dead"
    NOT_IN_PLAY = "not_in_play"


class BallTemp(Enum):
    VERY_HOT = "very_hot"
    HOT = "hot"
    WARM = "warm"
    COOL = "cool"


class CombatType(Enum):
    BRAWL = "brawl"
    MAN_TO_MAN = "man_to_man"
    ASSAULT = "assault"
    SWOOP = "swoop"


class CombatResult(Enum):
    INDECISIVE = "indecisive"        # 0-2
    MARGINAL = "marginal"            # 3-5
    DECISIVE = "decisive"            # 6-8
    BREAKTHROUGH = "breakthrough"    # 9-11
    BREAKAWAY = "breakaway"          # 12-14, 15+
    CRUSH = "crush"                  # (assault only)


class AssaultResult(Enum):
    FAILS = "fails"                      # 0-2
    MARGINAL = "marginal"                # 3-5
    DECISIVE = "decisive"                # 6-8
    BREAKTHROUGH_BLOCK = "breakthrough"  # 9-14
    CRUSH = "crush"                      # 15+


class TeamSide(Enum):
    HOME = "home"
    VISITOR = "visitor"


class Direction(Enum):
    CLOCKWISE = "clockwise"
    COUNTERCLOCKWISE = "counterclockwise"


class InjuryFace(Enum):
    HEAD = "head"
    LEFT_ARM = "left_arm"
    RIGHT_ARM = "right_arm"
    LEFT_LEG = "left_leg"
    RIGHT_LEG = "right_leg"
    BODY = "body"


# ---------------------------------------------------------------------------
# Board constants  (Rules C1-C9)
# ---------------------------------------------------------------------------

SECTORS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']
NUM_SECTORS = len(SECTORS)

SQUARES_PER_RING = {
    Ring.FLOOR: 1,
    Ring.LOWER: 2,
    Ring.MIDDLE: 3,
    Ring.UPPER: 4,
    Ring.CANNON: 4,
}

TOTAL_SQUARES = {
    Ring.FLOOR: 12,
    Ring.LOWER: 24,
    Ring.MIDDLE: 36,
    Ring.UPPER: 48,
}

SLOTS_INCLINE = 4   # C4
SLOTS_FLOOR = 6     # C4

# ---------------------------------------------------------------------------
# Timing (Rules A1, T1, H4)
# ---------------------------------------------------------------------------

PERIOD_LENGTH = 20
NUM_PERIODS = 3
GAME_LENGTH = 60

# H4: Compressing time — each game turn = 2 minutes; 3-min penalties round up to 4
MINUTES_PER_TURN = 2
COMPRESSED_PENALTY_MINUTES = 4   # round-up of 3-minute penalty in 2-min-per-turn mode

# ---------------------------------------------------------------------------
# Team composition (Rules A2, B11)
# ---------------------------------------------------------------------------

MAX_FIGURES_PER_TEAM = 10
MAX_SKATERS = 5
MAX_CATCHERS = 2
MAX_BIKERS = 3
MAX_STOPPED_FIGURES = 2   # B5

# ---------------------------------------------------------------------------
# Ball (Rules A5-A10, C13-C14)
# ---------------------------------------------------------------------------

BALL_ACTIVATION_LAPS = 1     # A8
OFFENSE_LAP_LIMIT = 3        # A9
BALL_DECEL_PER_TURN = 2      # C14
BALL_MAX_TURNS = 7           # C14

# ---------------------------------------------------------------------------
# Bikes (Rules E1-E8)
# ---------------------------------------------------------------------------

BIKE_MIN_SPEED = 2      # E6
BIKE_MAX_SPEED = 12     # E1
MAX_TOW = 3             # E9
BIKE_MAX_TURN_SPEED = 6 # E7

# ---------------------------------------------------------------------------
# Stats (Rules D1-D5, H9)
# ---------------------------------------------------------------------------

STAT_MAX = {'skill': 11, 'combat': 10, 'toughness': 11}
TEAM_BUILDING_POINTS = 6   # H8

# ---------------------------------------------------------------------------
# Referees (Rules B13-B14)
# ---------------------------------------------------------------------------

REFEREE_BASE_RATING = 8
REFEREE_FAR_SIDE_PENALTY = -2

# ---------------------------------------------------------------------------
# Penalties (Rule H2)
# ---------------------------------------------------------------------------

PENALTY_EJECTION_THRESHOLD = 5

# ---------------------------------------------------------------------------
# Incline movement (Rules C10-C11)
# ---------------------------------------------------------------------------

# Consecutive downhill bonuses: +1, +2, +2 (max +5 upper→floor)
DOWNHILL_CONSECUTIVE = [1, 2, 2]
# Consecutive uphill extra costs: 1, 2, 2
UPHILL_CONSECUTIVE_EXTRA = [1, 2, 2]

# ---------------------------------------------------------------------------
# Starting positions (Rule C12)
# ---------------------------------------------------------------------------

# Cycling pattern: sector indices for alternating team placement
STARTING_SECTOR_CYCLE = [0, 4, 2]   # A, E, C

# ---------------------------------------------------------------------------
# Combat modifiers (Rules G44-G57)
# ---------------------------------------------------------------------------

MOD_SUPPORTING_FIGURE = 1       # G44
MOD_HOLDING_TOW_BAR = 1         # G45
MOD_SLOT_ABOVE = 1              # G46
MOD_BALL_AS_WEAPON = 3          # G47  (illegal)
MOD_CONTROLS_SQUARE = 1         # G48
MOD_UPPER_HAND = 1              # G49
MOD_MOVING_VS_STANDING = 2      # G50
MOD_SLOT_BEHIND = 2             # G51
MOD_RELEASE_TOW_INTO_FIGHT = 2  # G52
MOD_SWOOP = 2                   # G53
MOD_SHAKEN = -1                 # G54
MOD_INJURED = -2                # G54
MOD_ATTACK_FALLEN = 4           # G55  (illegal)
MOD_SKATER_HIT_BIKER = 4        # G56  (illegal)
MOD_BIKE_AS_WEAPON = 5          # G57  (illegal)

# ---------------------------------------------------------------------------
# Scoring modifiers (Rules F1-F7)
# ---------------------------------------------------------------------------

SCORE_MOD_DISTANCE = -1                    # per square from goal
SCORE_MOD_STANDING_OPPONENT = -1           # per standing opponent
SCORE_MOD_MOVING_PERPENDICULAR = -1
SCORE_MOD_PRONE = -4
SCORE_MOD_MAN_TO_MAN = -2
SCORE_MOD_THIRD_IN_M2M = -2
SCORE_MOD_DEF_DECISIVE = -1
SCORE_MOD_DEF_BLOCK_BREAKAWAY = -2
SCORE_MOD_OFF_DECISIVE = 1
SCORE_MOD_OFF_BREAKTHROUGH_BREAKAWAY = 2
SCORE_MOD_OFF_CRUSH = 4
SCORE_MOD_AGAINST_GOAL = 2


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

def get_brawl_result(difference: int) -> CombatResult:
    """Return brawl result from the Brawl Results column (G15-G20)."""
    d = abs(difference)
    if d <= 2:
        return CombatResult.INDECISIVE
    if d <= 5:
        return CombatResult.MARGINAL
    if d <= 8:
        return CombatResult.DECISIVE
    if d <= 11:
        return CombatResult.BREAKTHROUGH
    return CombatResult.BREAKAWAY   # 12+


def get_assault_result(difference: int) -> AssaultResult:
    """Return assault result (G30-G35)."""
    d = abs(difference)
    if d <= 2:
        return AssaultResult.FAILS
    if d <= 5:
        return AssaultResult.MARGINAL
    if d <= 8:
        return AssaultResult.DECISIVE
    if d <= 14:
        return AssaultResult.BREAKTHROUGH_BLOCK
    return AssaultResult.CRUSH


def get_skill_check_info(difference: int) -> dict:
    """Return skill-check column info for given combat difference (G5-G10).

    Returns dict with keys:
        who:  'all' or 'losers'
        skill_mod: modifier to skill check
        toughness_mod: modifier to toughness check
        fatality: whether injury dice use fatality flag
        auto_fall: whether losers automatically fall
        bdd: whether Blue Die of Death is added
    """
    d = abs(difference)
    if d <= 2:
        return dict(who='all', skill_mod=0, toughness_mod=0,
                    fatality=False, auto_fall=False, bdd=False)
    if d <= 5:
        return dict(who='losers', skill_mod=0, toughness_mod=0,
                    fatality=False, auto_fall=False, bdd=False)
    if d <= 8:
        return dict(who='losers', skill_mod=-1, toughness_mod=0,
                    fatality=False, auto_fall=False, bdd=False)
    if d <= 11:
        return dict(who='losers', skill_mod=-2, toughness_mod=-1,
                    fatality=True, auto_fall=False, bdd=False)
    if d <= 14:
        return dict(who='losers', skill_mod=-3, toughness_mod=-2,
                    fatality=True, auto_fall=False, bdd=False)
    return dict(who='losers', skill_mod=0, toughness_mod=-3,
                fatality=True, auto_fall=True, bdd=True)
