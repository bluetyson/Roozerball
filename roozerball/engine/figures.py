"""Player / figure model for Roozerball.

Covers Rules D1-D31 (stats, actions, injuries, catchers) and E1-E2 (bikers).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from roozerball.engine.constants import (
    FigureType, FigureStatus, TeamSide, Ring,
    BIKE_MIN_SPEED, BIKE_MAX_SPEED, MAX_TOW,
)


@dataclass
class Figure:
    """A player figure on the Roozerball track."""

    name: str
    figure_type: FigureType
    team: TeamSide

    # Base stats (D1-D5)
    base_speed: int = 5
    base_skill: int = 7
    base_combat: int = 6
    base_toughness: int = 7

    # Modifiers
    speed_mod: int = 0
    skill_mod: int = 0
    combat_mod: int = 0
    toughness_mod: int = 0

    # Status
    status: FigureStatus = FigureStatus.STANDING
    has_ball: bool = False
    has_moved: bool = False      # cone tracking (Rule I4)
    has_fought: bool = False
    has_acted: bool = False      # one action per turn (D20)
    has_scored_attempt: bool = False
    is_on_field: bool = True
    needs_stand_up: bool = False
    auto_stand_next_turn: bool = False

    # Timers
    penalty_time: int = 0
    shaken_time: int = 0
    rest_time: int = 0
    endurance_remaining: int = 0  # calculated in __post_init__

    # Injuries (D6-D12)
    injuries: List[str] = field(default_factory=list)
    penalty_count: int = 0
    clockwise_offenses: int = 0

    # Man-to-man (G21-G26)
    man_to_man_partner: Optional[Any] = field(default=None, repr=False)
    man_to_man_drift: int = 0
    upper_hand: bool = False

    # Ball tracking (A8-A9)
    laps_completed: int = 0
    activation_sector: Optional[int] = None

    # Towing (E9-E14)
    is_towed: bool = False
    tow_bar_holder: bool = False
    towed_by: Optional[Any] = field(default=None, repr=False)
    towing: List[Any] = field(default_factory=list)
    tow_distance_this_turn: int = 0
    released_tow_bar_this_turn: bool = False   # G52: letting go of tow bar into fight

    # Carrying injured figures (F26-F27)
    is_being_carried: bool = False
    carried_by: Optional[Any] = field(default=None, repr=False)
    is_carrying: Optional[Any] = field(default=None, repr=False)

    # Endurance (H3)
    endurance_used: int = 0       # minutes of play used this game

    # Goal tending (A11)
    goal_screen_lap: Optional[int] = None   # lap count when screen was set up

    # Position
    sector_index: Optional[int] = None
    ring: Optional[Ring] = None
    square_position: Optional[int] = None
    slot_index: Optional[int] = None

    def __post_init__(self) -> None:
        self.endurance_remaining = self.base_toughness + 3  # H3

    # -- Effective stats with status penalties --
    def _status_penalty(self) -> int:
        if self.status == FigureStatus.BADLY_SHAKEN:
            return -2
        if self.status in (FigureStatus.SHAKEN,):
            return -1
        if 'broken_arm' in self.injuries:
            return -4
        if any(i.startswith('injured') for i in self.injuries):
            return -2
        return 0

    @property
    def speed(self) -> int:
        return max(0, self.base_speed + self.speed_mod + self._status_penalty())

    @property
    def skill(self) -> int:
        return max(0, self.base_skill + self.skill_mod + self._status_penalty())

    @property
    def combat(self) -> int:
        return max(0, self.base_combat + self.combat_mod + self._status_penalty())

    @property
    def toughness(self) -> int:
        return max(0, self.base_toughness + self.toughness_mod + self._status_penalty())

    # -- Type checks --
    @property
    def is_skater(self) -> bool:
        return self.figure_type in (FigureType.SKATER_BRUISER, FigureType.SKATER_SPEEDER)

    @property
    def is_catcher(self) -> bool:
        return self.figure_type == FigureType.CATCHER

    @property
    def is_biker(self) -> bool:
        return self.figure_type == FigureType.BIKER

    # -- Status checks --
    @property
    def is_standing(self) -> bool:
        """True when the figure is upright and not awaiting stand-up recovery."""
        if self.needs_stand_up:
            return False
        # "Standing" means upright/available on-skates for movement/control flow:
        # a figure is not standing while flagged as needing to stand up again.
        return self.status in (
            FigureStatus.STANDING,
            FigureStatus.MAN_TO_MAN,
            FigureStatus.SHAKEN,
            FigureStatus.BADLY_SHAKEN,
            FigureStatus.INJURED,
            FigureStatus.OUT_OF_CONTENTION,
        )

    @property
    def is_fallen(self) -> bool:
        return self.needs_stand_up or self.status == FigureStatus.FALLEN

    @property
    def is_out_of_play(self) -> bool:
        return self.status in (FigureStatus.UNCONSCIOUS, FigureStatus.DEAD) or not self.is_on_field

    # -- Capability checks --
    @property
    def can_score(self) -> bool:
        return self.is_skater and self.has_ball and self.is_on_field

    @property
    def can_field_ball(self) -> bool:
        return self.is_catcher  # A6, D24

    @property
    def can_fight(self) -> bool:
        return not self.has_fought and self.is_standing and self.is_on_field

    @property
    def can_act(self) -> bool:
        return not self.has_acted  # D20, D23

    @property
    def can_move(self) -> bool:
        return not self.has_moved and self.is_standing and self.is_on_field

    @property
    def slots_required(self) -> int:
        return 2 if self.is_biker else 1  # E5

    # -- Actions --
    def reset_turn(self) -> None:
        """Clear per-turn flags."""
        self.has_moved = False
        self.has_fought = False
        self.has_acted = False
        self.has_scored_attempt = False
        self.tow_distance_this_turn = 0
        self.released_tow_bar_this_turn = False

    def advance_timers(self) -> None:
        """Reduce penalty/shaken/rest timers by 1 (Rule T1)."""
        if self.penalty_time > 0:
            self.penalty_time -= 1
        if self.shaken_time > 0:
            self.shaken_time -= 1
        if self.rest_time > 0:
            self.rest_time -= 1

    def is_ready_to_return(self) -> bool:
        return self.penalty_time <= 0 and self.shaken_time <= 0 and self.rest_time <= 0

    def apply_penalty(self, minutes: int) -> None:
        self.penalty_time += minutes
        self.penalty_count += 1

    def fall(self) -> None:
        self.status = FigureStatus.FALLEN
        self.needs_stand_up = True
        self.auto_stand_next_turn = False

    def pick_up_ball(self) -> None:
        self.has_ball = True

    def drop_ball(self) -> None:
        self.has_ball = False

    def start_man_to_man(self, partner: Figure) -> None:
        self.status = FigureStatus.MAN_TO_MAN
        self.man_to_man_partner = partner
        self.man_to_man_drift = 3

    def end_man_to_man(self) -> None:
        if self.status == FigureStatus.MAN_TO_MAN:
            self.status = FigureStatus.STANDING
        self.man_to_man_partner = None
        self.man_to_man_drift = 0
        self.upper_hand = False

    def get_stat_summary(self) -> dict:
        return {
            'speed': self.speed, 'skill': self.skill,
            'combat': self.combat, 'toughness': self.toughness,
            'status': self.status.value, 'has_ball': self.has_ball,
        }


@dataclass
class Biker(Figure):
    """Motorcycle rider (Rules E1-E2)."""

    max_bike_speed: int = BIKE_MAX_SPEED
    cycle_damaged: bool = False
    cycle_badly_damaged: bool = False
    cycle_destroyed: bool = False
    feet_down: bool = False
    consecutive_turns_fixing: int = 0
    entered_field_this_turn: bool = False   # E6: entering field or standstill
    is_dismounted: bool = False             # E23: dismounted biker still counts as biker
    failed_stand_turns: int = 0             # E18: track failed bike-start attempts

    def __post_init__(self) -> None:
        self.figure_type = FigureType.BIKER
        self.base_speed = BIKE_MIN_SPEED
        super().__post_init__()

    @property
    def speed(self) -> int:
        if self.feet_down or self.cycle_destroyed:
            return 4 if self.is_dismounted else (3 if not self.cycle_badly_damaged else 2)
        base = self.max_bike_speed + self.speed_mod + self._status_penalty()
        tow_penalty = len(self.towing)
        # E6: entering field / starting from standstill: max move is 2
        if self.entered_field_this_turn:
            return BIKE_MIN_SPEED
        return max(BIKE_MIN_SPEED, min(BIKE_MAX_SPEED, base - tow_penalty))

    @property
    def can_score(self) -> bool:
        return False  # E2, B8

    @property
    def can_field_ball(self) -> bool:
        return False  # B8

    @property
    def slots_required(self) -> int:
        return 2  # E5
