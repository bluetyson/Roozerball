"""Season management for Roozerball.

Covers Rules H10-H14 (season structure, between-game management,
replacement figures, stat progression, next season).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from roozerball.engine import dice
from roozerball.engine.constants import FigureType
from roozerball.engine.team import Team


SEASON_GAMES = 10  # H10
BUILDING_POINTS_PER_SEASON = 4  # H12
NEW_SEASON_POINTS = 6  # H14
VETERAN_YEARS = 10  # H14
MIN_GAMES_FOR_PROGRESSION = 5  # H13: 50% of 10 games


@dataclass
class SeasonRecord:
    """Track a team's performance across a season (H10)."""
    team: Team
    wins: int = 0
    losses: int = 0
    draws: int = 0
    points_scored: int = 0
    points_allowed: int = 0
    games_played: int = 0
    figure_games: Dict[str, int] = field(default_factory=dict)  # figure name -> games played
    figure_kills: Dict[str, int] = field(default_factory=dict)  # figure name -> kills
    figure_points: Dict[str, int] = field(default_factory=dict)  # figure name -> points scored
    building_points: int = BUILDING_POINTS_PER_SEASON  # H12

    def record_game(self, scored: int, allowed: int) -> str:
        """Record a game result."""
        self.games_played += 1
        self.points_scored += scored
        self.points_allowed += allowed
        if scored > allowed:
            self.wins += 1
            return "win"
        elif scored < allowed:
            self.losses += 1
            return "loss"
        else:
            self.draws += 1
            return "draw"

    def record_figure_game(self, figure_name: str) -> None:
        """Track that a figure played in a game."""
        self.figure_games[figure_name] = self.figure_games.get(figure_name, 0) + 1

    def record_kill(self, figure_name: str) -> None:
        """Track a kill by a figure."""
        self.figure_kills[figure_name] = self.figure_kills.get(figure_name, 0) + 1

    def record_points(self, figure_name: str, points: int) -> None:
        """Track points scored by a figure."""
        self.figure_points[figure_name] = self.figure_points.get(figure_name, 0) + points


@dataclass
class Season:
    """Manage a full season of Roozerball (H10-H14)."""
    teams: List[Team] = field(default_factory=list)
    records: Dict[str, SeasonRecord] = field(default_factory=dict)
    current_game: int = 0
    season_number: int = 1
    playoff_teams: List[str] = field(default_factory=list)

    def add_team(self, team: Team) -> None:
        """Register a team for the season."""
        self.teams.append(team)
        self.records[team.name] = SeasonRecord(team=team)

    @property
    def is_regular_season_complete(self) -> bool:
        """H10: Check if all 10 regular season games are played."""
        return all(r.games_played >= SEASON_GAMES for r in self.records.values())

    def determine_playoffs(self) -> List[str]:
        """H10: Determine playoff seeding based on wins, then point differential."""
        sorted_teams = sorted(
            self.records.values(),
            key=lambda r: (r.wins, r.points_scored - r.points_allowed),
            reverse=True,
        )
        # Top 4 teams make playoffs
        self.playoff_teams = [r.team.name for r in sorted_teams[:min(4, len(sorted_teams))]]
        return self.playoff_teams

    # -------------------------------------------------------------------
    # H11: Between games
    # -------------------------------------------------------------------

    def between_games(self, team: Team) -> List[str]:
        """H11: Handle between-game management for a team.

        - Empty roster slots filled with reserves
        - Damaged cycles repaired/replaced
        - Badly injured figures out for half season
        """
        messages: List[str] = []
        record = self.records.get(team.name)
        if record is None:
            return messages

        for figure in team.roster:
            # Repair damaged cycles
            if getattr(figure, 'cycle_damaged', False):
                figure.cycle_damaged = False
                figure.cycle_badly_damaged = False
                messages.append(f"{figure.name}'s cycle repaired.")

            # Badly injured = out for half season (5 games)
            injuries = getattr(figure, 'injuries', [])
            if 'badly_injured' in injuries or 'broken_arm' in injuries:
                figure.games_suspended = getattr(figure, 'games_suspended', 0) + 5
                messages.append(f"{figure.name} out for {figure.games_suspended} games (badly injured).")

            # Decrement suspension
            suspended = getattr(figure, 'games_suspended', 0)
            if suspended > 0:
                figure.games_suspended = suspended - 1
                if figure.games_suspended == 0:
                    messages.append(f"{figure.name} returns from injury!")
                    figure.injuries.clear()

        # Fill empty slots
        active_count = len([f for f in team.roster if not getattr(f, 'games_suspended', 0)])
        if active_count < len(team.roster):
            messages.append(f"{team.name}: {len(team.roster) - active_count} roster slots need filling.")

        return messages

    # -------------------------------------------------------------------
    # H12: Replacement figures
    # -------------------------------------------------------------------

    def generate_replacement(self, team: Team, figure_type: FigureType) -> Any:
        """H12: Generate a replacement figure with die-rolled stats.

        Same type as the replaced figure. Stats generated with die roll.
        Costs building points.
        """
        from roozerball.engine.figures import Figure
        record = self.records.get(team.name)
        if record is None or record.building_points <= 0:
            return None

        # Generate base stats via die rolls (2d6 for each stat, mapped to range)
        speed = max(3, min(8, dice.roll_2d6() - 3))
        skill = max(4, min(10, dice.roll_2d6()))
        combat = max(4, min(10, dice.roll_2d6()))
        toughness = max(4, min(10, dice.roll_2d6()))

        replacement = Figure(
            name=f"Replacement {figure_type.value.title()}",
            figure_type=figure_type,
            team=team.side,
            base_speed=speed,
            base_skill=skill,
            base_combat=combat,
            base_toughness=toughness,
        )
        record.building_points -= 1
        return replacement

    # -------------------------------------------------------------------
    # H13: Season stat progression
    # -------------------------------------------------------------------

    def apply_stat_progression(self) -> List[str]:
        """H13: End-of-season stat improvements.

        - Surviving figure who played >=50% of games: +1 to any stat (except speed)
        - League leader (most points or kills): +1 to two stats
        """
        messages: List[str] = []

        # Find league leaders
        all_points: List[tuple] = []  # (team, figure, points)
        all_kills: List[tuple] = []
        for team_name, record in self.records.items():
            for fig_name, pts in record.figure_points.items():
                all_points.append((team_name, fig_name, pts))
            for fig_name, kills in record.figure_kills.items():
                all_kills.append((team_name, fig_name, kills))

        points_leader = max(all_points, key=lambda x: x[2]) if all_points else None
        kills_leader = max(all_kills, key=lambda x: x[2]) if all_kills else None

        for team in self.teams:
            record = self.records.get(team.name)
            if record is None:
                continue

            for figure in team.roster:
                games = record.figure_games.get(figure.name, 0)
                if games < MIN_GAMES_FOR_PROGRESSION:
                    continue
                if not figure.is_on_field or figure.status.value in ('dead',):
                    continue

                # +1 to skill, combat, or toughness (improve lowest stat)
                stats = {
                    'skill': figure.base_skill,
                    'combat': figure.base_combat,
                    'toughness': figure.base_toughness,
                }
                best_stat = min(stats, key=stats.get)
                if best_stat == 'skill' and figure.base_skill < 10:
                    figure.base_skill += 1
                    messages.append(f"{figure.name}: +1 skill (now {figure.base_skill})")
                elif best_stat == 'combat' and figure.base_combat < 10:
                    figure.base_combat += 1
                    messages.append(f"{figure.name}: +1 combat (now {figure.base_combat})")
                elif best_stat == 'toughness' and figure.base_toughness < 10:
                    figure.base_toughness += 1
                    messages.append(f"{figure.name}: +1 toughness (now {figure.base_toughness})")

                # League leader bonus: +1 to two stats
                is_leader = False
                if points_leader and points_leader[1] == figure.name:
                    is_leader = True
                if kills_leader and kills_leader[1] == figure.name:
                    is_leader = True

                if is_leader:
                    for stat_name in sorted(stats, key=stats.get):
                        if stat_name == best_stat:
                            continue
                        if stat_name == 'skill' and figure.base_skill < 10:
                            figure.base_skill += 1
                            messages.append(f"{figure.name} (league leader): +1 skill")
                        elif stat_name == 'combat' and figure.base_combat < 10:
                            figure.base_combat += 1
                            messages.append(f"{figure.name} (league leader): +1 combat")
                        elif stat_name == 'toughness' and figure.base_toughness < 10:
                            figure.base_toughness += 1
                            messages.append(f"{figure.name} (league leader): +1 toughness")
                        break

        return messages

    # -------------------------------------------------------------------
    # H14: Next season
    # -------------------------------------------------------------------

    def advance_to_next_season(self) -> List[str]:
        """H14: Transition to the next season.

        - 6 new building points for replacements
        - 10-year veterans may retire
        - Continuing veterans: speed -1 per season after season 5
        """
        messages: List[str] = []
        self.season_number += 1

        for team in self.teams:
            record = self.records.get(team.name)
            if record is None:
                continue
            # Reset building points
            record.building_points = NEW_SEASON_POINTS
            record.wins = 0
            record.losses = 0
            record.draws = 0
            record.games_played = 0
            record.points_scored = 0
            record.points_allowed = 0
            record.figure_games.clear()
            record.figure_kills.clear()
            record.figure_points.clear()

            for figure in list(team.roster):
                seasons = getattr(figure, 'seasons_played', 0) + 1
                figure.seasons_played = seasons

                # 10-year veteran retirement check
                if seasons >= VETERAN_YEARS:
                    # 50% chance of retirement
                    if dice.roll_d6() <= 3:
                        messages.append(f"{figure.name} retires after {seasons} seasons!")
                        team.roster.remove(figure)
                        continue
                    else:
                        messages.append(f"{figure.name} continues for season {seasons + 1}!")

                # Aging: veterans lose stats over time (after season 5)
                if seasons > 5:
                    if figure.base_speed > 2:
                        figure.base_speed -= 1
                        messages.append(f"{figure.name}: speed drops to {figure.base_speed} (aging)")

        self.playoff_teams.clear()
        messages.append(f"Season {self.season_number} begins! ({NEW_SEASON_POINTS} building points per team)")
        return messages
