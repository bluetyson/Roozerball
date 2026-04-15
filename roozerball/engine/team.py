"""Team management and generation for Roozerball.

Covers Rules H6-H9 (team roster generation) and D14 (substitutions).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional

from roozerball.engine.constants import (
    FigureType, TeamSide, Ring, STAT_MAX, TEAM_BUILDING_POINTS,
    MAX_FIGURES_PER_TEAM, MAX_SKATERS, MAX_CATCHERS, MAX_BIKERS,
)
from roozerball.engine.figures import Figure, Biker


@dataclass
class StretcherBearer:
    """H1: Stretcher bearer stub — data model and placeholder.

    Properties:
    - 2 slots required (pair of bearers)
    - Move 3 squares per turn, always move last in their sector
    - Can travel any direction (including clockwise)
    - Takes 1 turn to pick up an injured figure
    """

    team: TeamSide
    name: str = "Stretcher Bearer"
    speed: int = 3
    slots_required: int = 2
    moves_last: bool = True
    can_move_clockwise: bool = True
    pickup_turns_required: int = 1
    is_carrying_injured: bool = False
    carried_figure: Optional[Figure] = None
    sector_index: Optional[int] = None
    ring: Optional[Ring] = None
    square_position: Optional[int] = None
    slot_index: Optional[int] = None
    has_moved: bool = False

    def reset_turn(self) -> None:
        self.has_moved = False


@dataclass
class Team:
    """A Roozerball team with roster generation and management."""

    side: TeamSide
    name: str
    roster: List[Figure] = field(default_factory=list)
    active_figures: List[Figure] = field(default_factory=list)
    penalty_box: List[Figure] = field(default_factory=list)
    bench: List[Figure] = field(default_factory=list)
    injured_out: List[Figure] = field(default_factory=list)
    score: int = 0
    building_points: int = TEAM_BUILDING_POINTS
    total_catchers: int = 4

    def generate_roster(self) -> None:
        """Generate full 20-member roster per Rules H6-H9.

        10 skaters (6 bruisers speed 5, 4 speeders speed 7),
        6 bikers (speed 2/12), 4 catchers (speed 6).
        """
        self.roster = []
        self.building_points = TEAM_BUILDING_POINTS

        # 6 Bruisers
        for i in range(6):
            fig = self._make_figure(f"{self.name} Bruiser {i+1}",
                                    FigureType.SKATER_BRUISER, speed=5)
            self.roster.append(fig)

        # 4 Speeders
        for i in range(4):
            fig = self._make_figure(f"{self.name} Speeder {i+1}",
                                    FigureType.SKATER_SPEEDER, speed=7)
            self.roster.append(fig)

        # 6 Bikers
        for i in range(6):
            fig = self._make_biker(f"{self.name} Biker {i+1}")
            self.roster.append(fig)

        # 4 Catchers
        for i in range(4):
            fig = self._make_figure(f"{self.name} Catcher {i+1}",
                                    FigureType.CATCHER, speed=6)
            self.roster.append(fig)

    def _roll_stat(self) -> int:
        """Roll d6 with building point logic (Rule H8).

        If roll is 6: spend 1 BP to keep, else reduce to 4.
        """
        roll = random.randint(1, 6)
        if roll == 6:
            if self.building_points > 0:
                self.building_points -= 1
                return 6
            return 4  # No points left, reduce to 4
        return roll

    def _make_figure(self, name: str, ftype: FigureType, speed: int) -> Figure:
        """Create a figure with stat generation per Rule H7."""
        is_bruiser = (ftype == FigureType.SKATER_BRUISER)

        # Skill: 5 + d6 (bruiser -1 unless roll is 1)
        skill_roll = self._roll_stat()
        skill = 5 + skill_roll
        if is_bruiser and skill_roll > 1:
            skill -= 1

        # Combat: 4 + d6 (bruiser +1 unless 6)
        combat_roll = self._roll_stat()
        combat = 4 + combat_roll
        if is_bruiser and combat_roll < 6:
            combat += 1

        # Toughness: 5 + d6 (bruiser +1 unless 6)
        tough_roll = self._roll_stat()
        toughness = 5 + tough_roll
        if is_bruiser and tough_roll < 6:
            toughness += 1

        # Apply maximums (Rule H9)
        skill = min(skill, STAT_MAX['skill'])
        combat = min(combat, STAT_MAX['combat'])
        toughness = min(toughness, STAT_MAX['toughness'])

        return Figure(
            name=name, figure_type=ftype, team=self.side,
            base_speed=speed, base_skill=skill,
            base_combat=combat, base_toughness=toughness,
        )

    def _make_biker(self, name: str) -> Biker:
        """Create a biker with stat generation (Rule H7 — biker -2 combat)."""
        skill_roll = self._roll_stat()
        skill = 5 + skill_roll

        combat_roll = self._roll_stat()
        combat = 4 + combat_roll - 2  # Biker -2 combat

        tough_roll = self._roll_stat()
        toughness = 5 + tough_roll

        skill = min(skill, STAT_MAX['skill'])
        combat = min(max(combat, 1), STAT_MAX['combat'])
        toughness = min(toughness, STAT_MAX['toughness'])

        return Biker(
            name=name, figure_type=FigureType.BIKER, team=self.side,
            base_speed=2, base_skill=skill,
            base_combat=combat, base_toughness=toughness,
        )

    def select_starting_lineup(self) -> None:
        """Choose 10 from roster: 5 skaters, 2 catchers, 3 bikers."""
        skaters = [f for f in self.roster if f.is_skater][:MAX_SKATERS]
        catchers = [f for f in self.roster if f.is_catcher][:MAX_CATCHERS]
        bikers = [f for f in self.roster if f.is_biker][:MAX_BIKERS]

        self.active_figures = skaters + catchers + bikers
        for f in self.active_figures:
            f.is_on_field = True

        self.bench = [f for f in self.roster if f not in self.active_figures]
        for f in self.bench:
            f.is_on_field = False

    def get_available_substitute(self, figure_type: FigureType) -> Optional[Figure]:
        """Find substitute of same type on bench (Rule D14)."""
        for f in self.bench:
            if f.figure_type == figure_type and f.is_ready_to_return():
                return f
        return None

    def substitute(self, original: Figure, replacement: Figure) -> None:
        if original in self.active_figures:
            self.active_figures.remove(original)
        if replacement in self.bench:
            self.bench.remove(replacement)
        self.active_figures.append(replacement)
        replacement.is_on_field = True
        original.is_on_field = False
        self.bench.append(original)

    def add_score(self, points: int = 1) -> None:
        self.score += points

    def figures_on_field(self) -> List[Figure]:
        return [f for f in self.active_figures if f.is_on_field]

    def active_catchers(self) -> List[Figure]:
        return [f for f in self.active_figures if f.is_catcher and f.is_on_field]

    def can_field_with_regular_skater(self) -> bool:
        """True if all 4 catchers incapacitated (Rule D30)."""
        working = [f for f in self.roster if f.is_catcher and not f.is_out_of_play]
        return len(working) == 0

    def advance_timers(self) -> None:
        for f in self.roster:
            f.advance_timers()
