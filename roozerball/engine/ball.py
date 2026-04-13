"""Ball mechanics for Roozerball.

Covers Rules A5-A10, C13-C19, D24-D31 (cannon firing, movement, fielding, hot ball).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, List, Optional, NamedTuple, TYPE_CHECKING

from roozerball.engine.constants import (
    BallState, BallTemp, Ring, TeamSide,
    BALL_DECEL_PER_TURN, BALL_MAX_TURNS, OFFENSE_LAP_LIMIT, SECTORS,
)
from roozerball.engine import dice

if TYPE_CHECKING:
    from roozerball.engine.board import Board


class FieldResult(NamedTuple):
    success: bool
    bobbled: bool
    injury_result: Any
    message: str


class MissedShotResult(NamedTuple):
    dead_ball: bool
    bounce_direction: Optional[str]


@dataclass
class Ball:
    """The steel game ball."""

    state: BallState = BallState.NOT_IN_PLAY
    temperature: BallTemp = BallTemp.COOL
    speed: int = 0
    sector_index: int = 0
    ring: Ring = Ring.CANNON
    position: int = 0
    carrier: Any = field(default=None, repr=False)
    turns_since_fired: int = 0
    activation_team: Optional[TeamSide] = None
    is_activated: bool = False
    laps_since_activation: int = 0
    activation_sector: Optional[int] = None
    fielding_team: Optional[TeamSide] = None
    carried_sector_progress: int = 0
    stationary_goal_turns: int = 0

    def fire_cannon(self) -> str:
        """Fire ball from cannon (Rule C13)."""
        self.speed = dice.roll_ball_speed()
        self.state = BallState.IN_CANNON
        self.ring = Ring.CANNON
        self.temperature = BallTemp.VERY_HOT
        self.sector_index = random.randint(0, 11)
        self.position = 0
        self.turns_since_fired = 0
        self.carrier = None
        self.is_activated = False
        self.laps_since_activation = 0
        self.carried_sector_progress = 0
        self.stationary_goal_turns = 0
        return f"Cannon fires! Ball at speed {self.speed} in sector {SECTORS[self.sector_index]}"

    def move_ball(self) -> List[dict]:
        """Move unfielded ball (Rules C13-C14). Returns list of squares visited."""
        if self.state not in (BallState.IN_CANNON, BallState.ON_TRACK):
            return []

        self.turns_since_fired += 1
        squares_visited = []

        # Decelerate
        self.speed = max(0, self.speed - BALL_DECEL_PER_TURN)

        # Move clockwise (ball moves clockwise, opposite to players)
        for _ in range(self.speed):
            self.sector_index = (self.sector_index - 1) % 12  # clockwise
            squares_visited.append({
                'sector': self.sector_index, 'ring': self.ring,
                'position': self.position
            })

        # Slip down half a square each turn
        if self.turns_since_fired % 2 == 0 and self.ring.value > Ring.FLOOR.value:
            new_ring_val = self.ring.value - 1
            self.ring = Ring(new_ring_val)
            if self.state == BallState.IN_CANNON:
                self.state = BallState.ON_TRACK

        # After 7 turns → dead (Rule C14)
        if self.turns_since_fired >= BALL_MAX_TURNS or self.speed <= 0:
            self.declare_dead()

        self.update_temperature()
        return squares_visited

    def attempt_field(self, catcher: Any) -> FieldResult:
        """Catcher attempts to field the ball (Rules D24-D31)."""
        modifier = 0
        injury_result = None

        # Hot ball modifiers (Rule D26)
        if self.temperature == BallTemp.VERY_HOT and self.ring == Ring.CANNON:
            modifier = -4
            injury_result = dice.roll_injury_dice(fatality=True, bdd=True)
        elif self.temperature == BallTemp.VERY_HOT:
            modifier = -2
        elif self.temperature == BallTemp.HOT:
            modifier = -1

        # Catcher chart (Rule D31)
        target = getattr(catcher, 'skill', 7) + modifier
        roll = dice.roll_2d6()
        diff = roll - target

        if diff <= 0:
            # Caught!
            self.state = BallState.FIELDED
            self.carrier = catcher
            catcher.has_ball = True
            self.fielding_team = getattr(catcher, 'team', None)
            self.activation_sector = self.sector_index
            self.carried_sector_progress = 0
            self.stationary_goal_turns = 0
            return FieldResult(True, False, injury_result, f"Caught! Roll {roll} vs {target}")

        if diff <= 2:
            # Bobbled (Rule D27)
            bounce_loss = dice.roll_ball_bounce()
            self.speed = max(0, self.speed - bounce_loss)
            self.sector_index = dice.roll_direction()
            if self.temperature in (BallTemp.VERY_HOT, BallTemp.HOT):
                injury_result = dice.roll_injury_dice(fatality=False)
                self.temperature = BallTemp.WARM
            return FieldResult(False, True, injury_result,
                               f"Bobbled! Roll {roll} vs {target}, speed now {self.speed}")

        # Complete miss
        return FieldResult(False, False, injury_result,
                           f"Missed! Roll {roll} vs {target}")

    def attempt_pickup(self, figure: Any, modifier: int = 0) -> tuple:
        """Skill check to pick up dropped ball (Rule C19). Catchers get +2."""
        if getattr(figure, "is_biker", False):
            return (False, 0)
        bonus = 2 if getattr(figure, 'is_catcher', False) else 0
        result = dice.skill_check(getattr(figure, 'skill', 7), modifier + bonus)
        if result.success:
            self.state = BallState.FIELDED
            self.carrier = figure
            figure.has_ball = True
        return (result.success, result.roll)

    def drop(self) -> str:
        """Drop ball (Rule C18). Rolls downhill next turn at speed 1."""
        if self.carrier:
            self.carrier.has_ball = False
        self.carrier = None
        self.state = BallState.ON_TRACK
        self.speed = 1
        self.carried_sector_progress = 0
        self.stationary_goal_turns = 0
        return "Ball dropped! Rolling downhill at speed 1"

    def declare_dead(self) -> None:
        """Declare ball dead (Rule A10)."""
        self.state = BallState.DEAD
        self.speed = 0
        self.carried_sector_progress = 0
        self.stationary_goal_turns = 0
        if self.carrier:
            self.carrier.has_ball = False
        self.carrier = None

    def bounce(self) -> str:
        """Ball bounces off obstacle (Rule C17)."""
        loss = dice.roll_ball_bounce()
        if loss >= self.speed:
            self.speed = 0
            self.declare_dead()
            return "Ball stopped by obstacle — dead ball"
        self.speed -= loss
        self.sector_index = dice.roll_direction()
        if self.temperature in (BallTemp.VERY_HOT, BallTemp.HOT):
            self.temperature = BallTemp.WARM
        return f"Ball bounces! New speed {self.speed}, sector {SECTORS[self.sector_index]}"

    def activate(self, team: TeamSide) -> str:
        """Activate ball for team (Rule A8)."""
        self.is_activated = True
        self.activation_team = team
        self.laps_since_activation = 0
        self.carried_sector_progress = 0
        self.stationary_goal_turns = 0
        return f"Ball activated for {team.value}!"

    def steal(self, stealing_team: TeamSide, steal_sector: int) -> str:
        """Ball stolen (Rule A12)."""
        self.is_activated = False
        self.activation_team = None
        self.activation_sector = steal_sector
        self.fielding_team = stealing_team
        self.laps_since_activation = 0
        self.carried_sector_progress = 0
        self.stationary_goal_turns = 0
        return f"Ball stolen by {stealing_team.value}!"

    def check_three_lap_limit(self) -> bool:
        """Rule A9: 3 laps → dead ball."""
        if self.is_activated and self.laps_since_activation >= OFFENSE_LAP_LIMIT:
            self.declare_dead()
            return True
        return False

    def update_temperature(self) -> None:
        """Update temperature based on ring position (Rule C15)."""
        if self.ring == Ring.CANNON:
            self.temperature = BallTemp.VERY_HOT
        elif self.ring == Ring.UPPER:
            self.temperature = BallTemp.HOT
        elif self.ring == Ring.MIDDLE:
            self.temperature = BallTemp.WARM
        else:
            self.temperature = BallTemp.COOL

    def resolve_missed_shot(self) -> MissedShotResult:
        """Rule F8: 50% dead, 25% left, 25% right."""
        return dice.roll_missed_shot()

    def reset(self) -> None:
        """Reset for new ball."""
        self.state = BallState.NOT_IN_PLAY
        self.temperature = BallTemp.COOL
        self.speed = 0
        self.carrier = None
        self.turns_since_fired = 0
        self.is_activated = False
        self.laps_since_activation = 0
        self.activation_sector = None
        self.activation_team = None
        self.fielding_team = None
        self.carried_sector_progress = 0
        self.stationary_goal_turns = 0
