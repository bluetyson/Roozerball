"""Penalty and referee system for Roozerball.

Covers Rules B1-B16 (rules, penalties, referees).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, TYPE_CHECKING

from roozerball.engine.constants import (
    REFEREE_BASE_RATING, REFEREE_FAR_SIDE_PENALTY,
    PENALTY_EJECTION_THRESHOLD, MAX_FIGURES_PER_TEAM,
    MAX_SKATERS, MAX_CATCHERS, MAX_BIKERS, MAX_STOPPED_FIGURES,
    FigureStatus,
)
from roozerball.engine import dice

if TYPE_CHECKING:
    pass


@dataclass
class Referee:
    """A referee on the track (Rule B13)."""
    name: str
    position: str              # 'floor_1', 'floor_2', 'tower'
    view_sector: int = 0       # sector they face
    follows_ball: bool = False


@dataclass
class PenaltyEvent:
    """Record of a penalty."""
    figure: Any
    infraction: str
    minutes: int
    detected: bool
    detecting_ref: Optional[Referee] = None
    roll: int = 0
    target: int = 0
    negates_goal: bool = False
    message: str = ""


# Penalty minutes lookup
PENALTY_TABLE = {
    'ball_as_weapon': 3,                # B3
    'clockwise_movement_1st': 3,        # B4
    'clockwise_movement_2nd': 20,       # B4 (1 period)
    'extra_stopped_figure': 3,          # B5
    'skater_attacks_biker': 3,          # B6
    'biker_attacks': 3,                 # B7
    'biker_near_goal': 3,              # B8
    'biker_handles_ball': 3,           # B8
    'biker_scoring_interference': 9,   # B8 (3+3+3)
    'attack_fallen': 3,                # B10
    'infield_fighting': 3,            # B12
    'attack_referee': 60,             # B12 (ejection)
    'attack_stretcher_bearer': 20,    # H1 (1 period)
}


class PenaltySystem:
    """Manages referees and penalty detection/enforcement."""

    def __init__(self) -> None:
        self.referees: List[Referee] = []
        self.penalty_log: List[PenaltyEvent] = []
        self.ejection_threshold = PENALTY_EJECTION_THRESHOLD
        self.setup_referees()

    def setup_referees(self) -> None:
        """Create 3 refs (Rule B13)."""
        self.referees = [
            Referee('Floor Ref 1', 'floor_1', view_sector=0),
            Referee('Floor Ref 2', 'floor_2', view_sector=6),
            Referee('Tower Controller', 'tower', follows_ball=True),
        ]

    def check_infraction(
        self, figure: Any, infraction_type: str,
        ball_sector: Optional[int] = None,
        during_scoring: bool = False,
    ) -> PenaltyEvent:
        """Check if refs spot an infraction (Rules B14-B15).

        Always rolls dice regardless (Rule I2).
        """
        minutes = PENALTY_TABLE.get(infraction_type, 3)
        fig_sector = getattr(figure, 'sector_index', 0)

        # During scoring: all three refs check (B15)
        if during_scoring:
            detected = False
            for ref in self.referees:
                result = dice.referee_check(0)
                if result.success:
                    detected = True
                    event = PenaltyEvent(
                        figure=figure, infraction=infraction_type,
                        minutes=minutes, detected=True,
                        detecting_ref=ref, roll=result.roll,
                        target=result.target,
                        message=f"{ref.name} spots {infraction_type}!")
                    self.penalty_log.append(event)
                    return event
            # Not detected
            event = PenaltyEvent(
                figure=figure, infraction=infraction_type,
                minutes=minutes, detected=False,
                roll=0, target=REFEREE_BASE_RATING,
                message=f"{infraction_type} not spotted by any ref")
            self.penalty_log.append(event)
            return event

        # Normal check: each ref in range
        modifier = 0
        if ball_sector is not None and fig_sector is not None:
            # Far side penalty (B14)
            dist = abs(fig_sector - ball_sector)
            if dist > 6:
                dist = 12 - dist
            if dist >= 6:
                modifier = REFEREE_FAR_SIDE_PENALTY

        result = dice.referee_check(modifier)
        detected = result.success

        event = PenaltyEvent(
            figure=figure, infraction=infraction_type,
            minutes=minutes, detected=detected,
            roll=result.roll, target=result.target,
            message=f"{'DETECTED' if detected else 'Missed'}: {infraction_type} "
                    f"(roll {result.roll} vs {result.target})")
        self.penalty_log.append(event)
        return event

    def enforce_penalty(self, event: PenaltyEvent) -> str:
        """Remove figure to penalty box (Rule B16)."""
        if not event.detected:
            return "Penalty not detected"

        fig = event.figure
        fig.apply_penalty(event.minutes)
        fig.is_on_field = False

        # Check ejection (H2)
        if getattr(fig, 'penalty_count', 0) >= self.ejection_threshold:
            return f"{getattr(fig,'name','?')} EJECTED after {fig.penalty_count} penalties!"

        return f"{getattr(fig,'name','?')} to penalty box for {event.minutes} min"

    def update_referee_positions(self, ball_sector: int) -> None:
        """Tower ref follows ball; floor refs cover arcs."""
        for ref in self.referees:
            if ref.follows_ball:
                ref.view_sector = ball_sector

    def check_stopped_figures(self, figures: List[Any]) -> List[Any]:
        """Rule B5: Max 2 stopped figures. Returns excess."""
        stopped = [f for f in figures
                   if getattr(f, 'is_on_field', False)
                   and getattr(f, 'is_standing', False)
                   and not getattr(f, 'has_moved', False)
                   and getattr(f, 'status', None) not in
                   (FigureStatus.UNCONSCIOUS, FigureStatus.DEAD,
                    FigureStatus.INJURED)]
        if len(stopped) > MAX_STOPPED_FIGURES:
            return stopped[MAX_STOPPED_FIGURES:]
        return []

    def check_field_composition(self, figures: List[Any]) -> List[str]:
        """Rule B11: Check team composition limits."""
        violations = []
        on_field = [f for f in figures if getattr(f, 'is_on_field', False)]

        if len(on_field) > MAX_FIGURES_PER_TEAM:
            violations.append(f"Too many on field: {len(on_field)}/{MAX_FIGURES_PER_TEAM}")

        skaters = sum(1 for f in on_field if getattr(f, 'is_skater', False))
        catchers = sum(1 for f in on_field if getattr(f, 'is_catcher', False))
        bikers = sum(1 for f in on_field if getattr(f, 'is_biker', False))

        if skaters > MAX_SKATERS:
            violations.append(f"Too many skaters: {skaters}/{MAX_SKATERS}")
        if catchers > MAX_CATCHERS:
            violations.append(f"Too many catchers: {catchers}/{MAX_CATCHERS}")
        if bikers > MAX_BIKERS:
            violations.append(f"Too many bikers: {bikers}/{MAX_BIKERS}")

        return violations
