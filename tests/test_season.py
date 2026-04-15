"""Tests for roozerball.engine.season — Season, SeasonRecord."""

import unittest
from unittest.mock import patch

from roozerball.engine.season import (
    Season, SeasonRecord,
    SEASON_GAMES, BUILDING_POINTS_PER_SEASON, NEW_SEASON_POINTS,
    MIN_GAMES_FOR_PROGRESSION, AGING_THRESHOLD_SEASONS, VETERAN_YEARS,
)
from roozerball.engine.team import Team
from roozerball.engine.constants import FigureType, FigureStatus, TeamSide
from roozerball.engine.figures import Figure


def _team(name="Wombats", side=TeamSide.HOME) -> Team:
    t = Team(side=side, name=name)
    t.generate_roster()
    t.select_starting_lineup()
    return t


class TestSeasonRecord(unittest.TestCase):
    def test_record_win(self):
        team = _team()
        rec = SeasonRecord(team=team)
        result = rec.record_game(3, 1)
        self.assertEqual(result, "win")
        self.assertEqual(rec.wins, 1)
        self.assertEqual(rec.games_played, 1)
        self.assertEqual(rec.points_scored, 3)
        self.assertEqual(rec.points_allowed, 1)

    def test_record_loss(self):
        team = _team()
        rec = SeasonRecord(team=team)
        result = rec.record_game(1, 4)
        self.assertEqual(result, "loss")
        self.assertEqual(rec.losses, 1)

    def test_record_draw(self):
        team = _team()
        rec = SeasonRecord(team=team)
        result = rec.record_game(2, 2)
        self.assertEqual(result, "draw")
        self.assertEqual(rec.draws, 1)

    def test_record_figure_game(self):
        team = _team()
        rec = SeasonRecord(team=team)
        rec.record_figure_game("Bruiser 1")
        rec.record_figure_game("Bruiser 1")
        self.assertEqual(rec.figure_games["Bruiser 1"], 2)

    def test_record_kill(self):
        team = _team()
        rec = SeasonRecord(team=team)
        rec.record_kill("Bruiser 1")
        self.assertEqual(rec.figure_kills["Bruiser 1"], 1)

    def test_record_points(self):
        team = _team()
        rec = SeasonRecord(team=team)
        rec.record_points("Bruiser 1", 3)
        self.assertEqual(rec.figure_points["Bruiser 1"], 3)


class TestAddTeam(unittest.TestCase):
    def test_add_team(self):
        season = Season()
        team = _team()
        season.add_team(team)
        self.assertIn(team, season.teams)
        self.assertIn(team.name, season.records)


class TestDeterminePlayoffs(unittest.TestCase):
    def test_top_4_by_wins(self):
        season = Season()
        teams = []
        for i in range(6):
            side = TeamSide.HOME if i % 2 == 0 else TeamSide.VISITOR
            t = _team(f"Team{i}", side)
            season.add_team(t)
            teams.append(t)
        # Give different win records
        for i, t in enumerate(teams):
            rec = season.records[t.name]
            for _ in range(i):
                rec.record_game(2, 1)  # wins
            for _ in range(SEASON_GAMES - i):
                rec.record_game(0, 1)  # losses
        playoffs = season.determine_playoffs()
        self.assertEqual(len(playoffs), 4)
        # Top 4 should be teams with most wins: Team5, Team4, Team3, Team2
        self.assertEqual(playoffs[0], "Team5")
        self.assertEqual(playoffs[1], "Team4")

    def test_fewer_than_four_teams(self):
        season = Season()
        for i in range(2):
            season.add_team(_team(f"T{i}", TeamSide.HOME if i == 0 else TeamSide.VISITOR))
        playoffs = season.determine_playoffs()
        self.assertEqual(len(playoffs), 2)


class TestBetweenGames(unittest.TestCase):
    def test_repairs_damaged_cycles(self):
        season = Season()
        team = _team()
        season.add_team(team)
        bikers = [f for f in team.roster if f.is_biker]
        if bikers:
            bikers[0].cycle_damaged = True
        msgs = season.between_games(team)
        if bikers:
            self.assertFalse(bikers[0].cycle_damaged)
            self.assertTrue(any("repaired" in m.lower() for m in msgs))

    def test_handles_badly_injured(self):
        season = Season()
        team = _team()
        season.add_team(team)
        team.roster[0].injuries = ['badly_injured']
        msgs = season.between_games(team)
        self.assertTrue(any("out for" in m.lower() for m in msgs))


class TestGenerateReplacement(unittest.TestCase):
    @patch("roozerball.engine.season.dice.roll_2d6", return_value=7)
    def test_creates_figure(self, _):
        season = Season()
        team = _team()
        season.add_team(team)
        replacement = season.generate_replacement(team, FigureType.SKATER_BRUISER)
        self.assertIsNotNone(replacement)
        self.assertEqual(replacement.figure_type, FigureType.SKATER_BRUISER)
        self.assertEqual(replacement.team, team.side)

    @patch("roozerball.engine.season.dice.roll_2d6", return_value=7)
    def test_costs_building_points(self, _):
        season = Season()
        team = _team()
        season.add_team(team)
        bp_before = season.records[team.name].building_points
        season.generate_replacement(team, FigureType.SKATER_BRUISER)
        self.assertEqual(season.records[team.name].building_points, bp_before - 1)

    def test_returns_none_with_no_points(self):
        season = Season()
        team = _team()
        season.add_team(team)
        season.records[team.name].building_points = 0
        result = season.generate_replacement(team, FigureType.SKATER_BRUISER)
        self.assertIsNone(result)


class TestApplyStatProgression(unittest.TestCase):
    def test_improves_weakest_stat(self):
        season = Season()
        team = _team()
        season.add_team(team)
        fig = team.roster[0]
        fig.base_skill = 5
        fig.base_combat = 8
        fig.base_toughness = 8
        rec = season.records[team.name]
        rec.figure_games[fig.name] = MIN_GAMES_FOR_PROGRESSION
        msgs = season.apply_stat_progression()
        # Weakest is skill=5 → should increase to 6
        self.assertEqual(fig.base_skill, 6)
        self.assertTrue(any("+1 skill" in m for m in msgs))

    def test_no_progression_under_min_games(self):
        season = Season()
        team = _team()
        season.add_team(team)
        fig = team.roster[0]
        original_skill = fig.base_skill
        rec = season.records[team.name]
        rec.figure_games[fig.name] = MIN_GAMES_FOR_PROGRESSION - 1
        season.apply_stat_progression()
        self.assertEqual(fig.base_skill, original_skill)


class TestAdvanceToNextSeason(unittest.TestCase):
    def test_increments_season_number(self):
        season = Season()
        team = _team()
        season.add_team(team)
        season.advance_to_next_season()
        self.assertEqual(season.season_number, 2)

    def test_resets_records(self):
        season = Season()
        team = _team()
        season.add_team(team)
        rec = season.records[team.name]
        rec.record_game(3, 1)
        season.advance_to_next_season()
        self.assertEqual(rec.wins, 0)
        self.assertEqual(rec.games_played, 0)
        self.assertEqual(rec.building_points, NEW_SEASON_POINTS)

    @patch("roozerball.engine.season.dice.roll_d6", return_value=1)
    def test_veteran_retires(self, _):
        season = Season()
        team = _team()
        season.add_team(team)
        fig = team.roster[0]
        fig.seasons_played = VETERAN_YEARS - 1  # will become >= VETERAN_YEARS
        original_count = len(team.roster)
        msgs = season.advance_to_next_season()
        # roll_d6 returns 1 (<=3) → retires
        self.assertTrue(any("retires" in m.lower() for m in msgs))
        self.assertEqual(len(team.roster), original_count - 1)

    @patch("roozerball.engine.season.dice.roll_d6", return_value=5)
    def test_veteran_continues(self, _):
        season = Season()
        team = _team()
        season.add_team(team)
        fig = team.roster[0]
        fig.seasons_played = VETERAN_YEARS - 1
        original_count = len(team.roster)
        msgs = season.advance_to_next_season()
        self.assertTrue(any("continues" in m.lower() for m in msgs))
        self.assertEqual(len(team.roster), original_count)

    @patch("roozerball.engine.season.dice.roll_d6", return_value=6)
    def test_aging_speed_loss(self, _):
        season = Season()
        team = _team()
        season.add_team(team)
        fig = team.roster[0]
        fig.seasons_played = AGING_THRESHOLD_SEASONS  # will become > threshold
        original_speed = fig.base_speed
        season.advance_to_next_season()
        self.assertEqual(fig.base_speed, original_speed - 1)

    def test_clears_playoff_teams(self):
        season = Season()
        team = _team()
        season.add_team(team)
        season.playoff_teams = ["Team1"]
        season.advance_to_next_season()
        self.assertEqual(season.playoff_teams, [])


class TestIsRegularSeasonComplete(unittest.TestCase):
    def test_not_complete(self):
        season = Season()
        team = _team()
        season.add_team(team)
        self.assertFalse(season.is_regular_season_complete)

    def test_complete(self):
        season = Season()
        team = _team()
        season.add_team(team)
        rec = season.records[team.name]
        for _ in range(SEASON_GAMES):
            rec.record_game(1, 0)
        self.assertTrue(season.is_regular_season_complete)


if __name__ == "__main__":
    unittest.main()
