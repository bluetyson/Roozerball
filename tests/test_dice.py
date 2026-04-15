"""Tests for roozerball.engine.dice — deterministic via mocks."""

import unittest
from unittest.mock import patch

from roozerball.engine.dice import (
    skill_check, toughness_check, combat_roll,
    roll_injury_dice, roll_cycle_chart, roll_missed_shot,
    roll_ball_speed, roll_explosion,
    roll_2d6, roll_d6, roll_d12,
    CheckResult, InjuryResult, CycleChartResult, MissedShotResult,
)
from roozerball.engine.constants import InjuryFace


class TestBasicDice(unittest.TestCase):
    @patch("roozerball.engine.dice.random.randint", return_value=4)
    def test_roll_d6(self, mock_randint):
        self.assertEqual(roll_d6(), 4)

    @patch("roozerball.engine.dice.random.randint", side_effect=[3, 5])
    def test_roll_2d6(self, mock_randint):
        self.assertEqual(roll_2d6(), 8)

    @patch("roozerball.engine.dice.random.randint", return_value=7)
    def test_roll_d12(self, mock_randint):
        self.assertEqual(roll_d12(), 7)


class TestSkillCheck(unittest.TestCase):
    @patch("roozerball.engine.dice.roll_2d6", return_value=6)
    def test_success_when_roll_lte_target(self, _):
        result = skill_check(7, 0)
        self.assertIsInstance(result, CheckResult)
        self.assertTrue(result.success)
        self.assertEqual(result.roll, 6)
        self.assertEqual(result.target, 7)

    @patch("roozerball.engine.dice.roll_2d6", return_value=9)
    def test_failure_when_roll_gt_target(self, _):
        result = skill_check(7, 0)
        self.assertFalse(result.success)

    @patch("roozerball.engine.dice.roll_2d6", return_value=7)
    def test_modifier_applied(self, _):
        result = skill_check(5, 3)  # target = 8
        self.assertTrue(result.success)
        self.assertEqual(result.target, 8)


class TestToughnessCheck(unittest.TestCase):
    @patch("roozerball.engine.dice.roll_2d6", return_value=5)
    def test_success(self, _):
        result = toughness_check(7, -1)
        self.assertTrue(result.success)
        self.assertEqual(result.target, 6)

    @patch("roozerball.engine.dice.roll_2d6", return_value=10)
    def test_failure(self, _):
        result = toughness_check(7, 0)
        self.assertFalse(result.success)


class TestCombatRoll(unittest.TestCase):
    @patch("roozerball.engine.dice.roll_2d6", return_value=7)
    def test_combat_roll_sum(self, _):
        self.assertEqual(combat_roll(5, 2), 14)  # 7 + 5 + 2

    @patch("roozerball.engine.dice.roll_2d6", return_value=2)
    def test_combat_roll_minimum(self, _):
        self.assertEqual(combat_roll(0, 0), 2)


class TestRollInjuryDice(unittest.TestCase):
    @patch("roozerball.engine.dice._roll_injury_face",
           side_effect=[InjuryFace.BODY, InjuryFace.LEFT_ARM])
    def test_body_plus_limb_shaken(self, _):
        result = roll_injury_dice(fatality=False, bdd=False)
        self.assertEqual(result.injury_type, 'shaken')

    @patch("roozerball.engine.dice._roll_injury_face",
           side_effect=[InjuryFace.BODY, InjuryFace.LEFT_ARM])
    def test_body_plus_limb_fatality_badly_shaken(self, _):
        result = roll_injury_dice(fatality=True, bdd=False)
        self.assertEqual(result.injury_type, 'badly_shaken')

    @patch("roozerball.engine.dice._roll_injury_face",
           side_effect=[InjuryFace.HEAD, InjuryFace.HEAD])
    def test_double_head_unconscious(self, _):
        result = roll_injury_dice(fatality=False, bdd=False)
        self.assertEqual(result.injury_type, 'unconscious')

    @patch("roozerball.engine.dice._roll_injury_face",
           side_effect=[InjuryFace.HEAD, InjuryFace.HEAD])
    def test_double_head_fatality_dead(self, _):
        result = roll_injury_dice(fatality=True, bdd=False)
        self.assertEqual(result.injury_type, 'dead')

    @patch("roozerball.engine.dice._roll_injury_face",
           side_effect=[InjuryFace.BODY, InjuryFace.BODY])
    def test_double_body_badly_shaken(self, _):
        result = roll_injury_dice(fatality=False, bdd=False)
        self.assertEqual(result.injury_type, 'badly_shaken')

    @patch("roozerball.engine.dice._roll_injury_face",
           side_effect=[InjuryFace.BODY, InjuryFace.BODY])
    def test_double_body_fatality_dead(self, _):
        result = roll_injury_dice(fatality=True, bdd=False)
        self.assertEqual(result.injury_type, 'dead')

    @patch("roozerball.engine.dice._roll_injury_face",
           side_effect=[InjuryFace.LEFT_LEG, InjuryFace.LEFT_LEG])
    def test_double_limb_injured(self, _):
        result = roll_injury_dice(fatality=False, bdd=False)
        self.assertEqual(result.injury_type, 'injured')

    @patch("roozerball.engine.dice._roll_injury_face",
           side_effect=[InjuryFace.LEFT_ARM, InjuryFace.RIGHT_LEG])
    def test_no_combination(self, _):
        result = roll_injury_dice(fatality=False, bdd=False)
        self.assertEqual(result.injury_type, 'none')

    @patch("roozerball.engine.dice._roll_injury_face",
           side_effect=[InjuryFace.LEFT_ARM, InjuryFace.RIGHT_LEG, InjuryFace.BODY])
    def test_bdd_adds_third_die(self, _):
        result = roll_injury_dice(fatality=False, bdd=True)
        # BODY + LEFT_ARM (pair 0,2) or BODY + RIGHT_LEG (pair 1,2)
        # Both are body + limb → shaken
        self.assertIn(result.injury_type, ('shaken',))


class TestCycleChart(unittest.TestCase):
    @patch("roozerball.engine.dice.roll_2d6", return_value=2)
    def test_ok(self, _):
        r = roll_cycle_chart(0)
        self.assertEqual(r.result, 'ok')
        self.assertFalse(r.thrown)

    @patch("roozerball.engine.dice.roll_2d6", return_value=4)
    def test_near_miss(self, _):
        r = roll_cycle_chart(0)
        self.assertEqual(r.result, 'near_miss')

    @patch("roozerball.engine.dice.roll_2d6", return_value=6)
    def test_skid(self, _):
        r = roll_cycle_chart(0)
        self.assertEqual(r.result, 'skid')

    @patch("roozerball.engine.dice.roll_2d6", return_value=8)
    def test_thrown(self, _):
        r = roll_cycle_chart(0)
        self.assertEqual(r.result, 'thrown')
        self.assertTrue(r.thrown)

    @patch("roozerball.engine.dice.roll_2d6", return_value=10)
    def test_bad_wreck(self, _):
        r = roll_cycle_chart(0)
        self.assertEqual(r.result, 'bad_wreck')
        self.assertTrue(r.injury_fatality)

    @patch("roozerball.engine.dice.roll_2d6", return_value=12)
    def test_major_wreck(self, _):
        r = roll_cycle_chart(0)
        self.assertEqual(r.result, 'major_wreck')
        self.assertTrue(r.thrown)
        self.assertTrue(r.injury_fatality)

    @patch("roozerball.engine.dice.roll_2d6", return_value=11)
    def test_modifier_pushes_to_major(self, _):
        r = roll_cycle_chart(2)  # 11 + 2 = 13
        self.assertEqual(r.result, 'major_wreck')
        self.assertTrue(r.bdd)


class TestMissedShot(unittest.TestCase):
    @patch("roozerball.engine.dice.random.randint", return_value=1)
    def test_dead_ball(self, _):
        r = roll_missed_shot()
        self.assertTrue(r.dead_ball)
        self.assertIsNone(r.bounce_direction)

    @patch("roozerball.engine.dice.random.randint", return_value=3)
    def test_bounce_left(self, _):
        r = roll_missed_shot()
        self.assertFalse(r.dead_ball)
        self.assertEqual(r.bounce_direction, 'left')

    @patch("roozerball.engine.dice.random.randint", return_value=4)
    def test_bounce_right(self, _):
        r = roll_missed_shot()
        self.assertFalse(r.dead_ball)
        self.assertEqual(r.bounce_direction, 'right')


class TestBallSpeed(unittest.TestCase):
    @patch("roozerball.engine.dice.roll_3d6", return_value=10)
    def test_ball_speed_formula(self, _):
        self.assertEqual(roll_ball_speed(), 22)  # 10 + 12


class TestExplosion(unittest.TestCase):
    @patch("roozerball.engine.dice.roll_d6", return_value=3)
    def test_major_wreck_explodes_on_3(self, _):
        self.assertTrue(roll_explosion('major_wreck'))

    @patch("roozerball.engine.dice.roll_d6", return_value=2)
    def test_major_wreck_no_explode_on_2(self, _):
        self.assertFalse(roll_explosion('major_wreck'))

    @patch("roozerball.engine.dice.roll_d6", return_value=5)
    def test_bad_wreck_explodes_on_5(self, _):
        self.assertTrue(roll_explosion('bad_wreck'))

    @patch("roozerball.engine.dice.roll_d6", return_value=4)
    def test_bad_wreck_no_explode_on_4(self, _):
        self.assertFalse(roll_explosion('bad_wreck'))

    def test_other_severity_never_explodes(self):
        self.assertFalse(roll_explosion('ok'))


if __name__ == "__main__":
    unittest.main()
