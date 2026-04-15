"""Tests for roozerball.engine.team — Team management and roster generation."""

import unittest
from unittest.mock import patch

from roozerball.engine.team import Team, StretcherBearer
from roozerball.engine.constants import (
    FigureType, TeamSide, Ring, TEAM_BUILDING_POINTS,
    MAX_SKATERS, MAX_CATCHERS, MAX_BIKERS, MAX_FIGURES_PER_TEAM,
)
from roozerball.engine.figures import Figure, Biker


class TestGenerateRoster(unittest.TestCase):
    def test_creates_20_figures(self):
        team = Team(side=TeamSide.HOME, name="Wombats")
        team.generate_roster()
        self.assertEqual(len(team.roster), 20)

    def test_roster_composition(self):
        team = Team(side=TeamSide.HOME, name="Wombats")
        team.generate_roster()
        bruisers = [f for f in team.roster if f.figure_type == FigureType.SKATER_BRUISER]
        speeders = [f for f in team.roster if f.figure_type == FigureType.SKATER_SPEEDER]
        bikers = [f for f in team.roster if f.figure_type == FigureType.BIKER]
        catchers = [f for f in team.roster if f.figure_type == FigureType.CATCHER]
        self.assertEqual(len(bruisers), 6)
        self.assertEqual(len(speeders), 4)
        self.assertEqual(len(bikers), 6)
        self.assertEqual(len(catchers), 4)

    def test_all_figures_have_correct_team(self):
        team = Team(side=TeamSide.VISITOR, name="Dropbears")
        team.generate_roster()
        for f in team.roster:
            self.assertEqual(f.team, TeamSide.VISITOR)

    def test_bikers_are_biker_instances(self):
        team = Team(side=TeamSide.HOME, name="Wombats")
        team.generate_roster()
        bikers = [f for f in team.roster if f.figure_type == FigureType.BIKER]
        for b in bikers:
            self.assertIsInstance(b, Biker)

    def test_building_points_consumed(self):
        team = Team(side=TeamSide.HOME, name="Wombats")
        team.generate_roster()
        # Points may be consumed if stat rolls hit 6
        self.assertLessEqual(team.building_points, TEAM_BUILDING_POINTS)


class TestSelectStartingLineup(unittest.TestCase):
    def test_selects_10_active(self):
        team = Team(side=TeamSide.HOME, name="Wombats")
        team.generate_roster()
        team.select_starting_lineup()
        self.assertEqual(len(team.active_figures), MAX_FIGURES_PER_TEAM)

    def test_lineup_composition(self):
        team = Team(side=TeamSide.HOME, name="Wombats")
        team.generate_roster()
        team.select_starting_lineup()
        skaters = [f for f in team.active_figures if f.is_skater]
        catchers = [f for f in team.active_figures if f.is_catcher]
        bikers = [f for f in team.active_figures if f.is_biker]
        self.assertEqual(len(skaters), MAX_SKATERS)
        self.assertEqual(len(catchers), MAX_CATCHERS)
        self.assertEqual(len(bikers), MAX_BIKERS)

    def test_active_on_field_bench_off(self):
        team = Team(side=TeamSide.HOME, name="Wombats")
        team.generate_roster()
        team.select_starting_lineup()
        for f in team.active_figures:
            self.assertTrue(f.is_on_field)
        for f in team.bench:
            self.assertFalse(f.is_on_field)

    def test_bench_has_remaining(self):
        team = Team(side=TeamSide.HOME, name="Wombats")
        team.generate_roster()
        team.select_starting_lineup()
        self.assertEqual(len(team.bench), 10)  # 20 - 10


class TestSubstitution(unittest.TestCase):
    def setUp(self):
        self.team = Team(side=TeamSide.HOME, name="Wombats")
        self.team.generate_roster()
        self.team.select_starting_lineup()

    def test_get_available_substitute(self):
        sub = self.team.get_available_substitute(FigureType.SKATER_BRUISER)
        # bench has bruisers (1 extra), so should find one
        self.assertIsNotNone(sub)
        self.assertEqual(sub.figure_type, FigureType.SKATER_BRUISER)

    def test_get_substitute_respects_ready(self):
        # Make all bench bruisers not ready
        for f in self.team.bench:
            if f.figure_type == FigureType.SKATER_BRUISER:
                f.penalty_time = 5
        sub = self.team.get_available_substitute(FigureType.SKATER_BRUISER)
        self.assertIsNone(sub)

    def test_substitute_swaps(self):
        original = self.team.active_figures[0]
        sub = self.team.get_available_substitute(original.figure_type)
        if sub is None:
            self.skipTest("No substitute available for this type")
        self.team.substitute(original, sub)
        self.assertIn(sub, self.team.active_figures)
        self.assertNotIn(original, self.team.active_figures)
        self.assertIn(original, self.team.bench)
        self.assertTrue(sub.is_on_field)
        self.assertFalse(original.is_on_field)


class TestCanFieldWithRegularSkater(unittest.TestCase):
    def test_true_when_all_catchers_out(self):
        team = Team(side=TeamSide.HOME, name="Wombats")
        team.generate_roster()
        for f in team.roster:
            if f.is_catcher:
                f.status = FigureType.CATCHER  # won't match is_out_of_play
                f.is_on_field = False
                f.status = FigureType.CATCHER  # override; need actual incapacitation
        # Actually make all catchers dead
        for f in team.roster:
            if f.is_catcher:
                from roozerball.engine.constants import FigureStatus
                f.status = FigureStatus.DEAD
        self.assertTrue(team.can_field_with_regular_skater())

    def test_false_when_catchers_available(self):
        team = Team(side=TeamSide.HOME, name="Wombats")
        team.generate_roster()
        self.assertFalse(team.can_field_with_regular_skater())


class TestAdvanceTimers(unittest.TestCase):
    def test_reduces_all_roster_timers(self):
        team = Team(side=TeamSide.HOME, name="Wombats")
        team.generate_roster()
        team.roster[0].penalty_time = 3
        team.roster[1].shaken_time = 2
        team.advance_timers()
        self.assertEqual(team.roster[0].penalty_time, 2)
        self.assertEqual(team.roster[1].shaken_time, 1)


class TestAddScore(unittest.TestCase):
    def test_increment(self):
        team = Team(side=TeamSide.HOME, name="Wombats")
        team.add_score(1)
        self.assertEqual(team.score, 1)
        team.add_score(2)
        self.assertEqual(team.score, 3)


class TestFiguresOnField(unittest.TestCase):
    def test_only_on_field(self):
        team = Team(side=TeamSide.HOME, name="Wombats")
        team.generate_roster()
        team.select_starting_lineup()
        team.active_figures[0].is_on_field = False
        self.assertEqual(len(team.figures_on_field()), MAX_FIGURES_PER_TEAM - 1)


class TestActiveCatchers(unittest.TestCase):
    def test_returns_on_field_catchers(self):
        team = Team(side=TeamSide.HOME, name="Wombats")
        team.generate_roster()
        team.select_starting_lineup()
        catchers = team.active_catchers()
        self.assertEqual(len(catchers), MAX_CATCHERS)
        for c in catchers:
            self.assertTrue(c.is_catcher)


class TestStretcherBearer(unittest.TestCase):
    def test_defaults(self):
        sb = StretcherBearer(team=TeamSide.HOME)
        self.assertEqual(sb.speed, 3)
        self.assertEqual(sb.slots_required, 2)
        self.assertTrue(sb.moves_last)
        self.assertTrue(sb.can_move_clockwise)

    def test_reset_turn(self):
        sb = StretcherBearer(team=TeamSide.HOME)
        sb.has_moved = True
        sb.reset_turn()
        self.assertFalse(sb.has_moved)


if __name__ == "__main__":
    unittest.main()
