"""Tests for roozerball.engine.penalties — PenaltySystem and referees."""

import unittest
from unittest.mock import patch

from roozerball.engine.penalties import (
    PenaltySystem, PenaltyEvent, PENALTY_TABLE, Referee,
)
from roozerball.engine.constants import (
    FigureType, FigureStatus, TeamSide,
    MAX_FIGURES_PER_TEAM, MAX_SKATERS, MAX_CATCHERS, MAX_BIKERS,
    MAX_STOPPED_FIGURES, PENALTY_EJECTION_THRESHOLD,
    REFEREE_BASE_RATING,
)
from roozerball.engine.figures import Figure, Biker
from roozerball.engine.dice import CheckResult


def _fig(name="F", ftype=FigureType.SKATER_BRUISER, team=TeamSide.HOME, **kw):
    f = Figure(name=name, figure_type=ftype, team=team)
    for k, v in kw.items():
        setattr(f, k, v)
    return f


class TestSetupReferees(unittest.TestCase):
    def test_creates_three_refs(self):
        ps = PenaltySystem()
        self.assertEqual(len(ps.referees), 3)

    def test_ref_positions(self):
        ps = PenaltySystem()
        positions = {r.position for r in ps.referees}
        self.assertEqual(positions, {'floor_1', 'floor_2', 'tower'})

    def test_tower_follows_ball(self):
        ps = PenaltySystem()
        tower = [r for r in ps.referees if r.position == 'tower'][0]
        self.assertTrue(tower.follows_ball)


class TestCheckInfraction(unittest.TestCase):
    @patch("roozerball.engine.penalties.dice.referee_check",
           return_value=CheckResult(True, 5, 8))
    def test_detected_infraction(self, _):
        ps = PenaltySystem()
        fig = _fig(sector_index=0)
        event = ps.check_infraction(fig, 'attack_fallen')
        self.assertTrue(event.detected)
        self.assertEqual(event.minutes, PENALTY_TABLE['attack_fallen'])
        self.assertEqual(event.infraction, 'attack_fallen')

    @patch("roozerball.engine.penalties.dice.referee_check",
           return_value=CheckResult(False, 10, 8))
    def test_undetected_infraction(self, _):
        ps = PenaltySystem()
        fig = _fig(sector_index=0)
        event = ps.check_infraction(fig, 'attack_fallen')
        self.assertFalse(event.detected)

    @patch("roozerball.engine.penalties.dice.referee_check",
           return_value=CheckResult(True, 5, 8))
    def test_always_rolls_dice(self, mock_check):
        ps = PenaltySystem()
        fig = _fig(sector_index=0)
        ps.check_infraction(fig, 'ball_as_weapon')
        mock_check.assert_called()

    @patch("roozerball.engine.penalties.dice.referee_check",
           return_value=CheckResult(False, 10, 6))
    def test_far_side_penalty_applied(self, mock_check):
        ps = PenaltySystem()
        fig = _fig(sector_index=0)
        ps.check_infraction(fig, 'attack_fallen', ball_sector=6)
        # Far side: dist = 6 → modifier = -2, target = 8-2 = 6
        mock_check.assert_called_with(-2)

    @patch("roozerball.engine.penalties.dice.referee_check",
           return_value=CheckResult(True, 4, 8))
    def test_during_scoring_all_refs_check(self, mock_check):
        ps = PenaltySystem()
        fig = _fig(sector_index=0)
        event = ps.check_infraction(fig, 'attack_fallen', during_scoring=True)
        self.assertTrue(event.detected)
        # First ref detects → called once (returns immediately)
        self.assertGreaterEqual(mock_check.call_count, 1)

    @patch("roozerball.engine.penalties.dice.referee_check",
           return_value=CheckResult(False, 12, 8))
    def test_during_scoring_no_detection(self, mock_check):
        ps = PenaltySystem()
        fig = _fig(sector_index=0)
        event = ps.check_infraction(fig, 'attack_fallen', during_scoring=True)
        self.assertFalse(event.detected)
        # All three refs tried
        self.assertEqual(mock_check.call_count, 3)

    def test_penalty_logged(self):
        ps = PenaltySystem()
        fig = _fig(sector_index=0)
        with patch("roozerball.engine.penalties.dice.referee_check",
                    return_value=CheckResult(True, 5, 8)):
            ps.check_infraction(fig, 'biker_handles_ball')
        self.assertEqual(len(ps.penalty_log), 1)


class TestEnforcePenalty(unittest.TestCase):
    def test_detected_penalty_applied(self):
        ps = PenaltySystem()
        fig = _fig()
        event = PenaltyEvent(figure=fig, infraction='attack_fallen',
                             minutes=3, detected=True)
        msg = ps.enforce_penalty(event)
        self.assertEqual(fig.penalty_time, 3)
        self.assertEqual(fig.penalty_count, 1)
        self.assertFalse(fig.is_on_field)
        self.assertIn("penalty box", msg.lower())

    def test_undetected_penalty_not_applied(self):
        ps = PenaltySystem()
        fig = _fig()
        event = PenaltyEvent(figure=fig, infraction='attack_fallen',
                             minutes=3, detected=False)
        msg = ps.enforce_penalty(event)
        self.assertEqual(fig.penalty_time, 0)
        self.assertTrue(fig.is_on_field)
        self.assertIn("not detected", msg.lower())

    def test_ejection_on_threshold(self):
        ps = PenaltySystem()
        fig = _fig()
        fig.penalty_count = PENALTY_EJECTION_THRESHOLD - 1
        event = PenaltyEvent(figure=fig, infraction='attack_fallen',
                             minutes=3, detected=True)
        msg = ps.enforce_penalty(event)
        self.assertIn("EJECTED", msg)


class TestCheckStoppedFigures(unittest.TestCase):
    def test_returns_excess_over_two(self):
        ps = PenaltySystem()
        figs = [_fig(f"F{i}") for i in range(4)]
        for f in figs:
            f.is_on_field = True
            f.has_moved = False
        excess = ps.check_stopped_figures(figs)
        self.assertEqual(len(excess), 2)

    def test_no_excess_when_under_limit(self):
        ps = PenaltySystem()
        figs = [_fig(f"F{i}") for i in range(2)]
        for f in figs:
            f.is_on_field = True
            f.has_moved = False
        excess = ps.check_stopped_figures(figs)
        self.assertEqual(len(excess), 0)

    def test_moved_figures_not_counted(self):
        ps = PenaltySystem()
        figs = [_fig(f"F{i}") for i in range(4)]
        for f in figs:
            f.is_on_field = True
            f.has_moved = True
        excess = ps.check_stopped_figures(figs)
        self.assertEqual(len(excess), 0)


class TestCheckFieldComposition(unittest.TestCase):
    def test_valid_composition(self):
        ps = PenaltySystem()
        figs = (
            [_fig(f"S{i}", ftype=FigureType.SKATER_BRUISER) for i in range(5)]
            + [_fig(f"C{i}", ftype=FigureType.CATCHER) for i in range(2)]
            + [Biker(name=f"B{i}", figure_type=FigureType.BIKER,
                     team=TeamSide.HOME) for i in range(3)]
        )
        for f in figs:
            f.is_on_field = True
        violations = ps.check_field_composition(figs)
        self.assertEqual(violations, [])

    def test_too_many_total(self):
        ps = PenaltySystem()
        figs = [_fig(f"S{i}") for i in range(11)]
        for f in figs:
            f.is_on_field = True
        violations = ps.check_field_composition(figs)
        self.assertTrue(any("Too many on field" in v for v in violations))

    def test_too_many_skaters(self):
        ps = PenaltySystem()
        figs = [_fig(f"S{i}", ftype=FigureType.SKATER_BRUISER) for i in range(6)]
        for f in figs:
            f.is_on_field = True
        violations = ps.check_field_composition(figs)
        self.assertTrue(any("skaters" in v.lower() for v in violations))

    def test_too_many_catchers(self):
        ps = PenaltySystem()
        figs = [_fig(f"C{i}", ftype=FigureType.CATCHER) for i in range(3)]
        for f in figs:
            f.is_on_field = True
        violations = ps.check_field_composition(figs)
        self.assertTrue(any("catchers" in v.lower() for v in violations))

    def test_too_many_bikers(self):
        ps = PenaltySystem()
        figs = [Biker(name=f"B{i}", figure_type=FigureType.BIKER,
                       team=TeamSide.HOME) for i in range(4)]
        for f in figs:
            f.is_on_field = True
        violations = ps.check_field_composition(figs)
        self.assertTrue(any("bikers" in v.lower() for v in violations))

    def test_off_field_not_counted(self):
        ps = PenaltySystem()
        figs = [_fig(f"S{i}", ftype=FigureType.SKATER_BRUISER) for i in range(7)]
        for f in figs[:5]:
            f.is_on_field = True
        for f in figs[5:]:
            f.is_on_field = False
        violations = ps.check_field_composition(figs)
        self.assertEqual(violations, [])


class TestUpdateRefereePositions(unittest.TestCase):
    def test_tower_follows_ball(self):
        ps = PenaltySystem()
        ps.update_referee_positions(8)
        tower = [r for r in ps.referees if r.follows_ball][0]
        self.assertEqual(tower.view_sector, 8)


if __name__ == "__main__":
    unittest.main()
