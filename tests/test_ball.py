"""Tests for roozerball.engine.ball — Ball mechanics."""

import unittest
from unittest.mock import patch, MagicMock

from roozerball.engine.ball import Ball, FieldResult
from roozerball.engine.constants import BallState, BallTemp, Ring, TeamSide
from roozerball.engine.figures import Figure
from roozerball.engine.constants import FigureType
from roozerball.engine.dice import CheckResult


def _fig(name="Catcher", ftype=FigureType.CATCHER, **kw):
    defaults = dict(name=name, figure_type=ftype, team=TeamSide.HOME)
    defaults.update(kw)
    return Figure(**defaults)


class TestFireCannon(unittest.TestCase):
    @patch("roozerball.engine.ball.dice.roll_ball_speed", return_value=25)
    @patch("roozerball.engine.ball.random.randint", return_value=3)
    def test_fire_cannon(self, _, __):
        ball = Ball()
        msg = ball.fire_cannon()
        self.assertEqual(ball.state, BallState.IN_CANNON)
        self.assertEqual(ball.temperature, BallTemp.VERY_HOT)
        self.assertEqual(ball.speed, 25)
        self.assertEqual(ball.sector_index, 3)
        self.assertEqual(ball.ring, Ring.CANNON)
        self.assertEqual(ball.turns_since_fired, 0)
        self.assertIsNone(ball.carrier)
        self.assertFalse(ball.is_activated)
        self.assertIn("25", msg)


class TestMoveBall(unittest.TestCase):
    def test_move_decelerates(self):
        ball = Ball(state=BallState.ON_TRACK, speed=10, ring=Ring.MIDDLE,
                    sector_index=5, turns_since_fired=0)
        ball.move_ball()
        self.assertEqual(ball.speed, 8)

    def test_move_clockwise(self):
        ball = Ball(state=BallState.ON_TRACK, speed=4, ring=Ring.MIDDLE,
                    sector_index=5, turns_since_fired=0)
        visited = ball.move_ball()
        # After decel, speed=2, moves clockwise 2 sectors
        self.assertEqual(len(visited), 2)

    def test_slip_down_on_even_turns(self):
        ball = Ball(state=BallState.ON_TRACK, speed=6, ring=Ring.UPPER,
                    sector_index=0, turns_since_fired=1)
        ball.move_ball()
        # turns_since_fired is now 2 (even) → slip down
        self.assertEqual(ball.ring, Ring.MIDDLE)

    def test_cannon_to_on_track_on_slip(self):
        ball = Ball(state=BallState.IN_CANNON, speed=6, ring=Ring.CANNON,
                    sector_index=0, turns_since_fired=1)
        ball.move_ball()
        # Even turn → slips down from CANNON (4) to UPPER (3)
        self.assertEqual(ball.ring, Ring.UPPER)
        self.assertEqual(ball.state, BallState.ON_TRACK)

    def test_dead_after_7_turns(self):
        ball = Ball(state=BallState.ON_TRACK, speed=10, ring=Ring.MIDDLE,
                    sector_index=0, turns_since_fired=6)
        ball.move_ball()
        self.assertEqual(ball.state, BallState.DEAD)

    def test_dead_when_speed_zero(self):
        ball = Ball(state=BallState.ON_TRACK, speed=1, ring=Ring.LOWER,
                    sector_index=0, turns_since_fired=0)
        ball.move_ball()
        # speed = max(0, 1 - 2) = 0
        self.assertEqual(ball.state, BallState.DEAD)

    def test_no_move_when_fielded(self):
        ball = Ball(state=BallState.FIELDED, speed=5)
        result = ball.move_ball()
        self.assertEqual(result, [])


class TestAttemptField(unittest.TestCase):
    @patch("roozerball.engine.ball.dice.roll_2d6", return_value=5)
    def test_catch_success(self, _):
        ball = Ball(state=BallState.ON_TRACK, speed=10, ring=Ring.MIDDLE,
                    temperature=BallTemp.COOL)
        catcher = _fig(base_skill=7)
        result = ball.attempt_field(catcher)
        self.assertTrue(result.success)
        self.assertFalse(result.bobbled)
        self.assertEqual(ball.state, BallState.FIELDED)
        self.assertIs(ball.carrier, catcher)
        self.assertTrue(catcher.has_ball)

    @patch("roozerball.engine.ball.dice.roll_2d6", return_value=9)
    @patch("roozerball.engine.ball.dice.roll_ball_bounce", return_value=5)
    @patch("roozerball.engine.ball.dice.roll_direction", return_value=4)
    def test_bobble(self, *_):
        ball = Ball(state=BallState.ON_TRACK, speed=10, ring=Ring.MIDDLE,
                    temperature=BallTemp.COOL)
        catcher = _fig(base_skill=7)
        result = ball.attempt_field(catcher)
        # diff = 9 - 7 = 2, which is <= 2 → bobble
        self.assertFalse(result.success)
        self.assertTrue(result.bobbled)
        self.assertEqual(ball.speed, 5)  # 10 - 5

    @patch("roozerball.engine.ball.dice.roll_2d6", return_value=12)
    def test_complete_miss(self, _):
        ball = Ball(state=BallState.ON_TRACK, speed=10, ring=Ring.MIDDLE,
                    temperature=BallTemp.COOL)
        catcher = _fig(base_skill=7)
        result = ball.attempt_field(catcher)
        self.assertFalse(result.success)
        self.assertFalse(result.bobbled)

    @patch("roozerball.engine.ball.dice.roll_2d6", return_value=5)
    @patch("roozerball.engine.ball.dice.roll_injury_dice")
    def test_very_hot_cannon_modifier(self, mock_injury, _):
        mock_injury.return_value = MagicMock(injury_type='shaken')
        ball = Ball(state=BallState.ON_TRACK, speed=10, ring=Ring.CANNON,
                    temperature=BallTemp.VERY_HOT)
        catcher = _fig(base_skill=7)
        result = ball.attempt_field(catcher)
        # target = 7 + (-4) = 3, roll=5 → diff = 5-3 = 2 → bobble
        self.assertTrue(result.bobbled or not result.success)


class TestAttemptPickup(unittest.TestCase):
    @patch("roozerball.engine.ball.dice.skill_check",
           return_value=CheckResult(True, 5, 9))
    def test_catcher_gets_bonus(self, mock_check):
        ball = Ball(state=BallState.ON_TRACK)
        catcher = _fig(ftype=FigureType.CATCHER, base_skill=7)
        success, roll = ball.attempt_pickup(catcher)
        self.assertTrue(success)
        self.assertEqual(ball.state, BallState.FIELDED)
        self.assertTrue(catcher.has_ball)
        # Check the +2 bonus was passed
        mock_check.assert_called_once_with(7, 2)

    @patch("roozerball.engine.ball.dice.skill_check",
           return_value=CheckResult(False, 10, 7))
    def test_skater_no_bonus(self, mock_check):
        ball = Ball(state=BallState.ON_TRACK)
        skater = _fig(ftype=FigureType.SKATER_BRUISER)
        success, roll = ball.attempt_pickup(skater)
        self.assertFalse(success)
        mock_check.assert_called_once_with(7, 0)

    def test_biker_cannot_pickup(self):
        from roozerball.engine.figures import Biker
        ball = Ball(state=BallState.ON_TRACK)
        biker = Biker(name="B", figure_type=FigureType.BIKER, team=TeamSide.HOME)
        success, roll = ball.attempt_pickup(biker)
        self.assertFalse(success)
        self.assertEqual(roll, 0)


class TestDrop(unittest.TestCase):
    def test_drop_clears_carrier(self):
        fig = _fig()
        fig.has_ball = True
        ball = Ball(state=BallState.FIELDED, carrier=fig, speed=0)
        msg = ball.drop()
        self.assertEqual(ball.state, BallState.ON_TRACK)
        self.assertEqual(ball.speed, 1)
        self.assertIsNone(ball.carrier)
        self.assertFalse(fig.has_ball)
        self.assertIn("dropped", msg.lower())


class TestDeclareDead(unittest.TestCase):
    def test_declare_dead(self):
        fig = _fig()
        fig.has_ball = True
        ball = Ball(state=BallState.FIELDED, carrier=fig, speed=5)
        ball.declare_dead()
        self.assertEqual(ball.state, BallState.DEAD)
        self.assertEqual(ball.speed, 0)
        self.assertIsNone(ball.carrier)
        self.assertFalse(fig.has_ball)


class TestBounce(unittest.TestCase):
    @patch("roozerball.engine.ball.dice.roll_ball_bounce", return_value=3)
    @patch("roozerball.engine.ball.dice.roll_direction", return_value=7)
    def test_bounce_reduces_speed(self, *_):
        ball = Ball(state=BallState.ON_TRACK, speed=10, temperature=BallTemp.COOL)
        msg = ball.bounce()
        self.assertEqual(ball.speed, 7)
        self.assertEqual(ball.sector_index, 7)

    @patch("roozerball.engine.ball.dice.roll_ball_bounce", return_value=15)
    def test_bounce_kills_ball(self, _):
        ball = Ball(state=BallState.ON_TRACK, speed=10)
        ball.bounce()
        self.assertEqual(ball.state, BallState.DEAD)

    @patch("roozerball.engine.ball.dice.roll_ball_bounce", return_value=3)
    @patch("roozerball.engine.ball.dice.roll_direction", return_value=0)
    def test_hot_ball_cools_on_bounce(self, *_):
        ball = Ball(state=BallState.ON_TRACK, speed=10, temperature=BallTemp.VERY_HOT)
        ball.bounce()
        self.assertEqual(ball.temperature, BallTemp.WARM)


class TestActivate(unittest.TestCase):
    def test_activate(self):
        ball = Ball()
        msg = ball.activate(TeamSide.HOME)
        self.assertTrue(ball.is_activated)
        self.assertEqual(ball.activation_team, TeamSide.HOME)
        self.assertEqual(ball.laps_since_activation, 0)
        self.assertIn("home", msg.lower())


class TestSteal(unittest.TestCase):
    def test_steal_resets_activation(self):
        ball = Ball(is_activated=True, activation_team=TeamSide.HOME)
        msg = ball.steal(TeamSide.VISITOR, 5)
        self.assertFalse(ball.is_activated)
        self.assertIsNone(ball.activation_team)
        self.assertEqual(ball.fielding_team, TeamSide.VISITOR)
        self.assertEqual(ball.activation_sector, 5)


class TestThreeLapLimit(unittest.TestCase):
    def test_dies_at_3_laps(self):
        ball = Ball(is_activated=True, laps_since_activation=3)
        self.assertTrue(ball.check_three_lap_limit())
        self.assertEqual(ball.state, BallState.DEAD)

    def test_alive_under_3_laps(self):
        ball = Ball(is_activated=True, laps_since_activation=2)
        self.assertFalse(ball.check_three_lap_limit())

    def test_not_activated_no_limit(self):
        ball = Ball(is_activated=False, laps_since_activation=5)
        self.assertFalse(ball.check_three_lap_limit())


class TestUpdateTemperature(unittest.TestCase):
    def test_cannon_very_hot(self):
        ball = Ball(ring=Ring.CANNON)
        ball.update_temperature()
        self.assertEqual(ball.temperature, BallTemp.VERY_HOT)

    def test_upper_hot(self):
        ball = Ball(ring=Ring.UPPER)
        ball.update_temperature()
        self.assertEqual(ball.temperature, BallTemp.HOT)

    def test_middle_warm(self):
        ball = Ball(ring=Ring.MIDDLE)
        ball.update_temperature()
        self.assertEqual(ball.temperature, BallTemp.WARM)

    def test_lower_cool(self):
        ball = Ball(ring=Ring.LOWER)
        ball.update_temperature()
        self.assertEqual(ball.temperature, BallTemp.COOL)

    def test_floor_cool(self):
        ball = Ball(ring=Ring.FLOOR)
        ball.update_temperature()
        self.assertEqual(ball.temperature, BallTemp.COOL)


class TestReset(unittest.TestCase):
    def test_reset_clears_everything(self):
        fig = _fig()
        ball = Ball(state=BallState.FIELDED, temperature=BallTemp.HOT,
                    speed=10, carrier=fig, turns_since_fired=5,
                    is_activated=True, laps_since_activation=2,
                    activation_sector=3, activation_team=TeamSide.HOME,
                    fielding_team=TeamSide.HOME)
        ball.reset()
        self.assertEqual(ball.state, BallState.NOT_IN_PLAY)
        self.assertEqual(ball.temperature, BallTemp.COOL)
        self.assertEqual(ball.speed, 0)
        self.assertIsNone(ball.carrier)
        self.assertFalse(ball.is_activated)
        self.assertEqual(ball.laps_since_activation, 0)
        self.assertIsNone(ball.activation_sector)
        self.assertIsNone(ball.activation_team)
        self.assertIsNone(ball.fielding_team)


if __name__ == "__main__":
    unittest.main()
