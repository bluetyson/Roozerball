"""Scoring mechanics for Roozerball.

Covers Rules F1-F9 (scoring requirements, modifiers, hit/miss).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple, TYPE_CHECKING

from roozerball.engine.constants import (
    FigureStatus, CombatResult,
    SCORE_MOD_DISTANCE, SCORE_MOD_STANDING_OPPONENT,
    SCORE_MOD_MOVING_PERPENDICULAR, SCORE_MOD_PRONE,
    SCORE_MOD_MAN_TO_MAN, SCORE_MOD_THIRD_IN_M2M,
    SCORE_MOD_DEF_DECISIVE, SCORE_MOD_DEF_BLOCK_BREAKAWAY,
    SCORE_MOD_OFF_DECISIVE, SCORE_MOD_OFF_BREAKTHROUGH_BREAKAWAY,
    SCORE_MOD_OFF_CRUSH, SCORE_MOD_AGAINST_GOAL,
)
from roozerball.engine import dice

if TYPE_CHECKING:
    from roozerball.engine.board import Board, Square


@dataclass
class ScoringAttempt:
    """Result of a scoring attempt."""
    shooter: Any
    modifiers: List[Tuple[str, int]] = field(default_factory=list)
    total_modifier: int = 0
    roll: int = 0
    target: int = 0
    success: bool = False
    missed_shot_result: Any = None
    messages: List[str] = field(default_factory=list)


def calculate_scoring_modifiers(
    shooter: Any,
    goal_square: Any = None,
    standing_opponents: int = 0,
    distance: int = 0,
    combat_result: Optional[CombatResult] = None,
    is_offense_combat: bool = True,
) -> List[Tuple[str, int]]:
    """Calculate scoring modifiers (Rules F1-F7)."""
    mods: List[Tuple[str, int]] = []

    # Distance from goal (F3)
    if distance > 0:
        mods.append(('Distance from goal', SCORE_MOD_DISTANCE * distance))

    # Standing opponents between shooter and goal (F3)
    if standing_opponents > 0:
        mods.append(('Standing opponents', SCORE_MOD_STANDING_OPPONENT * standing_opponents))

    # Fallen/prone shooter (F5)
    if getattr(shooter, 'is_fallen', False):
        mods.append(('Prone shooter', SCORE_MOD_PRONE))

    # Man-to-man (F3)
    if getattr(shooter, 'status', None) == FigureStatus.MAN_TO_MAN:
        mods.append(('Man-to-man', SCORE_MOD_MAN_TO_MAN))

    # Directly against goal (F3)
    if distance == 0:
        mods.append(('Against goal', SCORE_MOD_AGAINST_GOAL))

    # Combat effects (F3-F4)
    if combat_result:
        if is_offense_combat:
            if combat_result == CombatResult.DECISIVE:
                mods.append(('Offense decisive', SCORE_MOD_OFF_DECISIVE))
            elif combat_result in (CombatResult.BREAKTHROUGH, CombatResult.BREAKAWAY):
                mods.append(('Offense breakthrough/breakaway', SCORE_MOD_OFF_BREAKTHROUGH_BREAKAWAY))
            elif combat_result == CombatResult.CRUSH:
                mods.append(('Offense crush', SCORE_MOD_OFF_CRUSH))
        else:
            if combat_result == CombatResult.DECISIVE:
                mods.append(('Defense decisive', SCORE_MOD_DEF_DECISIVE))
            elif combat_result in (CombatResult.BREAKTHROUGH, CombatResult.BREAKAWAY):
                mods.append(('Defense block/breakaway', SCORE_MOD_DEF_BLOCK_BREAKAWAY))

    # Broken arm auto-drop (F6)
    if 'broken_arm' in getattr(shooter, 'injuries', []):
        mods.append(('Broken arm (auto-drop)', -99))  # Cannot score

    return mods


def attempt_score(
    shooter: Any,
    standing_opponents: int = 0,
    distance: int = 0,
    combat_result: Optional[CombatResult] = None,
    is_offense_combat: bool = True,
) -> ScoringAttempt:
    """Attempt to score (Rule F2)."""
    attempt = ScoringAttempt(shooter=shooter)

    # Check requirements (F1)
    if not getattr(shooter, 'is_skater', False):
        attempt.messages.append("Only skaters can score!")
        return attempt
    if not getattr(shooter, 'has_ball', False):
        attempt.messages.append("Shooter doesn't have the ball!")
        return attempt

    mods = calculate_scoring_modifiers(
        shooter, standing_opponents=standing_opponents,
        distance=distance, combat_result=combat_result,
        is_offense_combat=is_offense_combat)

    attempt.modifiers = mods
    attempt.total_modifier = sum(m[1] for m in mods)

    # Broken arm = auto-fail
    if attempt.total_modifier <= -50:
        attempt.messages.append("Broken arm — ball dropped before shot!")
        return attempt

    skill = getattr(shooter, 'skill', 7)
    attempt.target = skill + attempt.total_modifier
    attempt.roll = dice.roll_2d6()
    attempt.success = attempt.roll <= attempt.target

    if attempt.success:
        attempt.messages.append(
            f"GOAL! Roll {attempt.roll} vs {attempt.target}")
    else:
        attempt.messages.append(
            f"Miss! Roll {attempt.roll} vs {attempt.target}")
        # Missed shot die (F8)
        attempt.missed_shot_result = dice.roll_missed_shot()

    return attempt


def check_scoring_penalties(offense_penalties: List[Any]) -> Tuple[bool, str]:
    """Rule B9: Any penalty on offense during scoring negates the goal."""
    if offense_penalties:
        return True, "Goal negated — offense committed penalty during scoring turn"
    return False, ""
