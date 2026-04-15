"""Tests for roozerball.engine.scoring — scoring modifiers and attempts."""

import unittest
from unittest.mock import patch

from roozerball.engine.scoring import (
    attempt_score, calculate_scoring_modifiers, check_scoring_penalties,
    ScoringAttempt,
)
from roozerball.engine.constants import (
    FigureStatus, CombatResult, FigureType, TeamSide,
    SCORE_MOD_DISTANCE, SCORE_MOD_STANDING_OPPONENT, SCORE_MOD_PRONE,
    SCORE_MOD_MAN_TO_MAN, SCORE_MOD_AGAINST_GOAL,
    SCORE_MOD_OFF_DECISIVE, SCORE_MOD_OFF_BREAKTHROUGH_BREAKAWAY,
    SCORE_MOD_OFF_CRUSH, SCORE_MOD_DEF_DECISIVE, SCORE_MOD_DEF_BLOCK_BREAKAWAY,
)
from roozerball.engine.figures import Figure


def _shooter(has_ball=True, status=FigureStatus.STANDING, injuries=None, **kw):
    f = Figure(name="Shooter", figure_type=FigureType.SKATER_BRUISER,
               team=TeamSide.HOME, base_skill=7, **kw)
    f.has_ball = has_ball
    f.status = status
    if injuries:
        f.injuries = injuries
    return f


class TestCalculateScoringModifiers(unittest.TestCase):
    def test_distance_modifier(self):
        mods = calculate_scoring_modifiers(_shooter(), distance=3)
        dist_mods = [m for m in mods if 'Distance' in m[0]]
        self.assertEqual(len(dist_mods), 1)
        self.assertEqual(dist_mods[0][1], SCORE_MOD_DISTANCE * 3)

    def test_standing_opponents(self):
        mods = calculate_scoring_modifiers(_shooter(), standing_opponents=2)
        opp_mods = [m for m in mods if 'opponent' in m[0].lower()]
        self.assertEqual(opp_mods[0][1], SCORE_MOD_STANDING_OPPONENT * 2)

    def test_prone_shooter(self):
        shooter = _shooter()
        shooter.fall()
        mods = calculate_scoring_modifiers(shooter)
        self.assertTrue(any(m[1] == SCORE_MOD_PRONE for m in mods))

    def test_man_to_man_penalty(self):
        shooter = _shooter(status=FigureStatus.MAN_TO_MAN)
        mods = calculate_scoring_modifiers(shooter)
        self.assertTrue(any(m[1] == SCORE_MOD_MAN_TO_MAN for m in mods))

    def test_against_goal_bonus(self):
        mods = calculate_scoring_modifiers(_shooter(), distance=0)
        self.assertTrue(any(m[1] == SCORE_MOD_AGAINST_GOAL for m in mods))

    def test_offense_decisive_combat(self):
        mods = calculate_scoring_modifiers(
            _shooter(), combat_result=CombatResult.DECISIVE, is_offense_combat=True)
        self.assertTrue(any(m[1] == SCORE_MOD_OFF_DECISIVE for m in mods))

    def test_offense_breakthrough_combat(self):
        mods = calculate_scoring_modifiers(
            _shooter(), combat_result=CombatResult.BREAKTHROUGH, is_offense_combat=True)
        self.assertTrue(any(m[1] == SCORE_MOD_OFF_BREAKTHROUGH_BREAKAWAY for m in mods))

    def test_offense_crush_combat(self):
        mods = calculate_scoring_modifiers(
            _shooter(), combat_result=CombatResult.CRUSH, is_offense_combat=True)
        self.assertTrue(any(m[1] == SCORE_MOD_OFF_CRUSH for m in mods))

    def test_defense_decisive_combat(self):
        mods = calculate_scoring_modifiers(
            _shooter(), combat_result=CombatResult.DECISIVE, is_offense_combat=False)
        self.assertTrue(any(m[1] == SCORE_MOD_DEF_DECISIVE for m in mods))

    def test_defense_breakaway_combat(self):
        mods = calculate_scoring_modifiers(
            _shooter(), combat_result=CombatResult.BREAKAWAY, is_offense_combat=False)
        self.assertTrue(any(m[1] == SCORE_MOD_DEF_BLOCK_BREAKAWAY for m in mods))

    def test_broken_arm_auto_fail(self):
        mods = calculate_scoring_modifiers(_shooter(injuries=['broken_arm']))
        self.assertTrue(any(m[1] == -99 for m in mods))

    def test_no_combat_result(self):
        mods = calculate_scoring_modifiers(_shooter(), combat_result=None)
        combat_mods = [m for m in mods if 'ffense' in m[0] or 'efense' in m[0]]
        self.assertEqual(len(combat_mods), 0)


class TestAttemptScore(unittest.TestCase):
    @patch("roozerball.engine.scoring.dice.roll_2d6", return_value=5)
    def test_successful_goal(self, _):
        shooter = _shooter()
        result = attempt_score(shooter, distance=0)
        self.assertTrue(result.success)
        self.assertIn("GOAL", " ".join(result.messages))

    @patch("roozerball.engine.scoring.dice.roll_2d6", return_value=12)
    @patch("roozerball.engine.scoring.dice.roll_missed_shot")
    def test_missed_shot(self, mock_miss, _):
        from roozerball.engine.dice import MissedShotResult
        mock_miss.return_value = MissedShotResult(True, None)
        shooter = _shooter()
        result = attempt_score(shooter, distance=0)
        self.assertFalse(result.success)
        self.assertIn("Miss", " ".join(result.messages))
        mock_miss.assert_called_once()

    def test_non_skater_cannot_score(self):
        catcher = Figure(name="C", figure_type=FigureType.CATCHER,
                         team=TeamSide.HOME)
        catcher.has_ball = True
        result = attempt_score(catcher)
        self.assertFalse(result.success)
        self.assertIn("Only skaters", " ".join(result.messages))

    def test_no_ball_cannot_score(self):
        shooter = _shooter(has_ball=False)
        result = attempt_score(shooter)
        self.assertFalse(result.success)
        self.assertIn("ball", " ".join(result.messages).lower())

    def test_broken_arm_auto_drop(self):
        shooter = _shooter(injuries=['broken_arm'])
        result = attempt_score(shooter, distance=0)
        self.assertFalse(result.success)
        self.assertIn("Broken arm", " ".join(result.messages))


class TestCheckScoringPenalties(unittest.TestCase):
    def test_penalty_negates_goal(self):
        negated, msg = check_scoring_penalties(["some_penalty"])
        self.assertTrue(negated)
        self.assertIn("negated", msg.lower())

    def test_no_penalties_no_negation(self):
        negated, msg = check_scoring_penalties([])
        self.assertFalse(negated)
        self.assertEqual(msg, "")


if __name__ == "__main__":
    unittest.main()
