"""Tests for roozerball.engine.figures — Figure and Biker."""

import unittest

from roozerball.engine.figures import Figure, Biker
from roozerball.engine.constants import (
    FigureType, FigureStatus, TeamSide, Ring,
    BIKE_MIN_SPEED, BIKE_MAX_SPEED,
)


def _fig(**kw) -> Figure:
    defaults = dict(name="Test", figure_type=FigureType.SKATER_BRUISER, team=TeamSide.HOME)
    defaults.update(kw)
    return Figure(**defaults)


class TestFigureStatProperties(unittest.TestCase):
    def test_base_stats_no_penalty(self):
        f = _fig(base_speed=5, base_skill=7, base_combat=6, base_toughness=7)
        self.assertEqual(f.speed, 5)
        self.assertEqual(f.skill, 7)
        self.assertEqual(f.combat, 6)
        self.assertEqual(f.toughness, 7)

    def test_shaken_penalty_minus_1(self):
        f = _fig(base_skill=7)
        f.status = FigureStatus.SHAKEN
        self.assertEqual(f.skill, 6)
        self.assertEqual(f.speed, 4)

    def test_badly_shaken_penalty_minus_2(self):
        f = _fig(base_combat=6)
        f.status = FigureStatus.BADLY_SHAKEN
        self.assertEqual(f.combat, 4)

    def test_broken_arm_injury_penalty(self):
        f = _fig(base_skill=7)
        f.injuries.append('broken_arm')
        self.assertEqual(f.skill, 3)  # -4

    def test_injured_prefix_penalty(self):
        f = _fig(base_toughness=7)
        f.injuries.append('injured_left_leg')
        self.assertEqual(f.toughness, 5)  # -2

    def test_stat_mod_adds(self):
        f = _fig(base_speed=5, speed_mod=2)
        self.assertEqual(f.speed, 7)

    def test_stat_never_negative(self):
        f = _fig(base_speed=1, speed_mod=-5)
        self.assertEqual(f.speed, 0)

    def test_endurance_set_on_init(self):
        f = _fig(base_toughness=8)
        self.assertEqual(f.endurance_remaining, 11)  # 8 + 3


class TestFigureTypeChecks(unittest.TestCase):
    def test_is_skater_bruiser(self):
        f = _fig(figure_type=FigureType.SKATER_BRUISER)
        self.assertTrue(f.is_skater)
        self.assertFalse(f.is_catcher)
        self.assertFalse(f.is_biker)

    def test_is_skater_speeder(self):
        f = _fig(figure_type=FigureType.SKATER_SPEEDER)
        self.assertTrue(f.is_skater)

    def test_is_catcher(self):
        f = _fig(figure_type=FigureType.CATCHER)
        self.assertTrue(f.is_catcher)
        self.assertFalse(f.is_skater)

    def test_is_biker(self):
        f = _fig(figure_type=FigureType.BIKER)
        self.assertTrue(f.is_biker)


class TestFigureCapabilities(unittest.TestCase):
    def test_can_score_skater_with_ball(self):
        f = _fig(figure_type=FigureType.SKATER_BRUISER)
        f.has_ball = True
        f.is_on_field = True
        self.assertTrue(f.can_score)

    def test_cannot_score_without_ball(self):
        f = _fig(figure_type=FigureType.SKATER_BRUISER)
        f.has_ball = False
        self.assertFalse(f.can_score)

    def test_catcher_cannot_score(self):
        f = _fig(figure_type=FigureType.CATCHER)
        f.has_ball = True
        self.assertFalse(f.can_score)

    def test_can_field_ball_catcher_only(self):
        catcher = _fig(figure_type=FigureType.CATCHER)
        skater = _fig(figure_type=FigureType.SKATER_BRUISER)
        self.assertTrue(catcher.can_field_ball)
        self.assertFalse(skater.can_field_ball)

    def test_can_fight(self):
        f = _fig()
        f.has_fought = False
        f.is_on_field = True
        self.assertTrue(f.can_fight)

    def test_cannot_fight_already_fought(self):
        f = _fig()
        f.has_fought = True
        self.assertFalse(f.can_fight)

    def test_cannot_fight_fallen(self):
        f = _fig()
        f.fall()
        self.assertFalse(f.can_fight)

    def test_cannot_fight_off_field(self):
        f = _fig()
        f.is_on_field = False
        self.assertFalse(f.can_fight)


class TestFigureFall(unittest.TestCase):
    def test_fall_sets_status_and_needs_stand_up(self):
        f = _fig()
        f.fall()
        self.assertEqual(f.status, FigureStatus.FALLEN)
        self.assertTrue(f.needs_stand_up)
        self.assertFalse(f.auto_stand_next_turn)

    def test_is_fallen_after_fall(self):
        f = _fig()
        f.fall()
        self.assertTrue(f.is_fallen)
        self.assertFalse(f.is_standing)


class TestManToMan(unittest.TestCase):
    def test_start_man_to_man(self):
        f1 = _fig(name="A")
        f2 = _fig(name="B")
        f1.start_man_to_man(f2)
        self.assertEqual(f1.status, FigureStatus.MAN_TO_MAN)
        self.assertIs(f1.man_to_man_partner, f2)
        self.assertEqual(f1.man_to_man_drift, 3)

    def test_end_man_to_man(self):
        f1 = _fig(name="A")
        f2 = _fig(name="B")
        f1.start_man_to_man(f2)
        f1.upper_hand = True
        f1.end_man_to_man()
        self.assertEqual(f1.status, FigureStatus.STANDING)
        self.assertIsNone(f1.man_to_man_partner)
        self.assertEqual(f1.man_to_man_drift, 0)
        self.assertFalse(f1.upper_hand)

    def test_end_man_to_man_only_if_in_m2m_status(self):
        f = _fig()
        f.status = FigureStatus.FALLEN
        f.end_man_to_man()
        # Should not change status to STANDING if wasn't MAN_TO_MAN
        self.assertEqual(f.status, FigureStatus.FALLEN)


class TestAdvanceTimers(unittest.TestCase):
    def test_reduces_all_timers(self):
        f = _fig()
        f.penalty_time = 3
        f.shaken_time = 2
        f.rest_time = 1
        f.advance_timers()
        self.assertEqual(f.penalty_time, 2)
        self.assertEqual(f.shaken_time, 1)
        self.assertEqual(f.rest_time, 0)

    def test_timers_do_not_go_negative(self):
        f = _fig()
        f.penalty_time = 0
        f.advance_timers()
        self.assertEqual(f.penalty_time, 0)


class TestApplyPenalty(unittest.TestCase):
    def test_increments_penalty_count_and_time(self):
        f = _fig()
        f.apply_penalty(3)
        self.assertEqual(f.penalty_count, 1)
        self.assertEqual(f.penalty_time, 3)
        f.apply_penalty(5)
        self.assertEqual(f.penalty_count, 2)
        self.assertEqual(f.penalty_time, 8)


class TestResetTurn(unittest.TestCase):
    def test_clears_per_turn_flags(self):
        f = _fig()
        f.has_moved = True
        f.has_fought = True
        f.has_acted = True
        f.has_scored_attempt = True
        f.swooped_this_turn = True
        f.entered_field_this_turn = True
        f.reset_turn()
        self.assertFalse(f.has_moved)
        self.assertFalse(f.has_fought)
        self.assertFalse(f.has_acted)
        self.assertFalse(f.has_scored_attempt)
        self.assertFalse(f.swooped_this_turn)
        self.assertFalse(f.entered_field_this_turn)


class TestFigureReadyToReturn(unittest.TestCase):
    def test_ready_when_all_zero(self):
        f = _fig()
        self.assertTrue(f.is_ready_to_return())

    def test_not_ready_with_penalty(self):
        f = _fig()
        f.penalty_time = 1
        self.assertFalse(f.is_ready_to_return())


class TestFigureBallActions(unittest.TestCase):
    def test_pick_up_and_drop(self):
        f = _fig()
        f.pick_up_ball()
        self.assertTrue(f.has_ball)
        f.drop_ball()
        self.assertFalse(f.has_ball)


class TestSlotsRequired(unittest.TestCase):
    def test_skater_one_slot(self):
        f = _fig(figure_type=FigureType.SKATER_BRUISER)
        self.assertEqual(f.slots_required, 1)

    def test_biker_two_slots(self):
        f = _fig(figure_type=FigureType.BIKER)
        self.assertEqual(f.slots_required, 2)


# ----- Biker -----

class TestBiker(unittest.TestCase):
    def _biker(self, **kw) -> Biker:
        defaults = dict(name="Biker", figure_type=FigureType.BIKER, team=TeamSide.HOME)
        defaults.update(kw)
        return Biker(**defaults)

    def test_biker_post_init_sets_type(self):
        b = self._biker()
        self.assertEqual(b.figure_type, FigureType.BIKER)
        self.assertEqual(b.base_speed, BIKE_MIN_SPEED)

    def test_can_score_always_false(self):
        b = self._biker()
        b.has_ball = True
        self.assertFalse(b.can_score)

    def test_can_field_ball_always_false(self):
        b = self._biker()
        self.assertFalse(b.can_field_ball)

    def test_slots_required_always_two(self):
        b = self._biker()
        self.assertEqual(b.slots_required, 2)

    def test_speed_normal(self):
        b = self._biker()
        self.assertEqual(b.speed, BIKE_MAX_SPEED)

    def test_speed_feet_down(self):
        b = self._biker()
        b.feet_down = True
        self.assertEqual(b.speed, 3)

    def test_speed_entered_field(self):
        b = self._biker()
        b.entered_field_this_turn = True
        self.assertEqual(b.speed, BIKE_MIN_SPEED)

    def test_speed_with_tow(self):
        b = self._biker()
        other = _fig()
        b.towing = [other]
        # Speed = max_bike_speed - tow_penalty (1) but clamped to BIKE_MIN..BIKE_MAX
        self.assertEqual(b.speed, BIKE_MAX_SPEED - 1)

    def test_reset_turn_transitions_feet_down(self):
        b = self._biker()
        b.feet_down = True
        b.reset_turn()
        self.assertTrue(b.entered_field_this_turn)


if __name__ == "__main__":
    unittest.main()
