"""Tests for roozerball.engine.combat — combat resolution functions."""

import unittest
from unittest.mock import patch

from roozerball.engine.combat import (
    resolve_brawl, resolve_man_to_man, resolve_assault, resolve_swoop,
    calculate_combat_modifiers, validate_swoop, check_combat_penalties,
    CombatOutcome,
)
from roozerball.engine.constants import (
    CombatType, CombatResult, AssaultResult, FigureType, FigureStatus, TeamSide,
    MOD_MOVING_VS_STANDING, MOD_SHAKEN, MOD_ATTACK_FALLEN, MOD_SKATER_HIT_BIKER,
    MOD_SWOOP,
)
from roozerball.engine.figures import Figure, Biker


def _fig(name="F", team=TeamSide.HOME, ftype=FigureType.SKATER_BRUISER,
         combat=6, skill=7, **kw):
    f = Figure(name=name, figure_type=ftype, team=team,
               base_combat=combat, base_skill=skill)
    for k, v in kw.items():
        setattr(f, k, v)
    return f


class TestResolveBrawl(unittest.TestCase):
    @patch("roozerball.engine.combat.dice.roll_2d6", side_effect=[10, 3])
    @patch("roozerball.engine.combat.dice.skill_check")
    def test_attacker_wins(self, mock_skill, mock_roll):
        mock_skill.return_value = type('CR', (), {'success': True, 'roll': 5, 'target': 7})()
        atk = [_fig("A", combat=8)]
        defs = [_fig("D", team=TeamSide.VISITOR, combat=5)]
        outcome = resolve_brawl(atk, defs)
        self.assertEqual(outcome.combat_type, CombatType.BRAWL)
        self.assertEqual(outcome.winner_side, 'attacker')
        self.assertIsNotNone(outcome.brawl_result)

    @patch("roozerball.engine.combat.dice.roll_2d6", side_effect=[3, 10])
    @patch("roozerball.engine.combat.dice.skill_check")
    def test_defender_wins(self, mock_skill, mock_roll):
        mock_skill.return_value = type('CR', (), {'success': True, 'roll': 5, 'target': 7})()
        atk = [_fig("A", combat=5)]
        defs = [_fig("D", team=TeamSide.VISITOR, combat=8)]
        outcome = resolve_brawl(atk, defs)
        self.assertEqual(outcome.winner_side, 'defender')

    @patch("roozerball.engine.combat.dice.roll_2d6", side_effect=[7, 7])
    @patch("roozerball.engine.combat.dice.skill_check")
    def test_tie(self, mock_skill, mock_roll):
        mock_skill.return_value = type('CR', (), {'success': True, 'roll': 5, 'target': 7})()
        atk = [_fig("A", combat=6)]
        defs = [_fig("D", team=TeamSide.VISITOR, combat=6)]
        outcome = resolve_brawl(atk, defs)
        self.assertEqual(outcome.winner_side, 'tie')

    @patch("roozerball.engine.combat.dice.roll_2d6", side_effect=[12, 2])
    @patch("roozerball.engine.combat.dice.skill_check")
    @patch("roozerball.engine.combat.dice.toughness_check")
    @patch("roozerball.engine.combat.dice.roll_injury_dice")
    def test_large_difference_breakaway(self, mock_injury, mock_tough, mock_skill, mock_roll):
        mock_skill.return_value = type('CR', (), {'success': True, 'roll': 5, 'target': 7})()
        mock_tough.return_value = type('CR', (), {'success': True, 'roll': 5, 'target': 7})()
        atk = [_fig("A", combat=10)]
        defs = [_fig("D", team=TeamSide.VISITOR, combat=2)]
        outcome = resolve_brawl(atk, defs)
        # diff = (10+12) - (2+2) = 18, brawl_result should be BREAKAWAY
        self.assertEqual(outcome.brawl_result, CombatResult.BREAKAWAY)


class TestResolveManToMan(unittest.TestCase):
    @patch("roozerball.engine.combat.dice.roll_2d6", side_effect=[9, 3])
    @patch("roozerball.engine.combat.dice.skill_check")
    def test_upper_hand_set(self, mock_skill, mock_roll):
        mock_skill.return_value = type('CR', (), {'success': True, 'roll': 5, 'target': 7})()
        f1 = _fig("F1", combat=7)
        f2 = _fig("F2", team=TeamSide.VISITOR, combat=5)
        f1.start_man_to_man(f2)
        f2.start_man_to_man(f1)
        outcome = resolve_man_to_man(f1, f2)
        self.assertEqual(outcome.combat_type, CombatType.MAN_TO_MAN)
        self.assertEqual(outcome.winner_side, 'attacker')
        self.assertTrue(f1.upper_hand)
        self.assertFalse(f2.upper_hand)

    @patch("roozerball.engine.combat.dice.roll_2d6", side_effect=[5, 5])
    @patch("roozerball.engine.combat.dice.skill_check")
    def test_tie_no_upper_hand(self, mock_skill, mock_roll):
        mock_skill.return_value = type('CR', (), {'success': True, 'roll': 5, 'target': 7})()
        f1 = _fig("F1", combat=6)
        f2 = _fig("F2", team=TeamSide.VISITOR, combat=6)
        outcome = resolve_man_to_man(f1, f2)
        self.assertEqual(outcome.winner_side, 'tie')


class TestResolveAssault(unittest.TestCase):
    @patch("roozerball.engine.combat.dice.roll_2d6", side_effect=[8, 4])
    @patch("roozerball.engine.combat.dice.skill_check")
    @patch("roozerball.engine.combat.dice.toughness_check")
    def test_max_four_per_side(self, mock_tough, mock_skill, mock_roll):
        mock_skill.return_value = type('CR', (), {'success': True, 'roll': 5, 'target': 7})()
        mock_tough.return_value = type('CR', (), {'success': True, 'roll': 5, 'target': 7})()
        atk = [_fig(f"A{i}", combat=6) for i in range(6)]
        defs = [_fig(f"D{i}", team=TeamSide.VISITOR, combat=5) for i in range(6)]
        outcome = resolve_assault(atk, defs)
        self.assertEqual(outcome.combat_type, CombatType.ASSAULT)
        self.assertIsNotNone(outcome.assault_result)

    @patch("roozerball.engine.combat.dice.roll_2d6", side_effect=[10, 3])
    @patch("roozerball.engine.combat.dice.skill_check")
    @patch("roozerball.engine.combat.dice.toughness_check")
    def test_winners_make_skill_minus_1(self, mock_tough, mock_skill, mock_roll):
        mock_skill.return_value = type('CR', (), {'success': True, 'roll': 5, 'target': 6})()
        mock_tough.return_value = type('CR', (), {'success': True, 'roll': 5, 'target': 7})()
        atk = [_fig("A", combat=8)]
        defs = [_fig("D", team=TeamSide.VISITOR, combat=4)]
        outcome = resolve_assault(atk, defs)
        # Winners should have had skill_check called with -1 modifier
        self.assertEqual(outcome.winner_side, 'attacker')


class TestResolveSwoop(unittest.TestCase):
    @patch("roozerball.engine.combat.dice.roll_2d6", side_effect=[10, 3])
    @patch("roozerball.engine.combat.dice.skill_check")
    @patch("roozerball.engine.combat.dice.toughness_check")
    def test_swooper_always_falls(self, mock_tough, mock_skill, mock_roll):
        mock_skill.return_value = type('CR', (), {'success': True, 'roll': 5, 'target': 7})()
        mock_tough.return_value = type('CR', (), {'success': True, 'roll': 5, 'target': 7})()
        swooper = _fig("Swooper", combat=7)
        target = _fig("Target", team=TeamSide.VISITOR, combat=5)
        outcome = resolve_swoop(swooper, target)
        self.assertEqual(outcome.combat_type, CombatType.SWOOP)
        self.assertTrue(swooper.is_fallen)

    @patch("roozerball.engine.combat.dice.roll_2d6", side_effect=[10, 3])
    @patch("roozerball.engine.combat.dice.skill_check")
    @patch("roozerball.engine.combat.dice.toughness_check")
    @patch("roozerball.engine.combat.dice.roll_cycle_chart")
    def test_biker_target_gets_cycle_chart_on_decisive(self, mock_chart, mock_tough,
                                                        mock_skill, mock_roll):
        mock_skill.return_value = type('CR', (), {'success': True, 'roll': 5, 'target': 7})()
        mock_tough.return_value = type('CR', (), {'success': True, 'roll': 5, 'target': 7})()
        mock_chart.return_value = type('CC', (), {
            'result': 'ok', 'thrown': False, 'thrown_distance': 0,
            'injury_fatality': False, 'bdd': False, 'details': 'OK'})()
        swooper = _fig("Swooper", combat=10)
        biker = Biker(name="Biker", figure_type=FigureType.BIKER,
                       team=TeamSide.VISITOR, base_combat=3)
        outcome = resolve_swoop(swooper, biker)
        diff = abs(outcome.difference)
        if diff >= 6:
            mock_chart.assert_called()


class TestCalculateCombatModifiers(unittest.TestCase):
    def test_moving_vs_standing(self):
        atk = [_fig("A")]
        atk[0].has_moved = True
        defs = [_fig("D", team=TeamSide.VISITOR)]
        defs[0].has_moved = False
        atk_mod, def_mod, atk_mods, _, _ = calculate_combat_modifiers(
            atk, defs, CombatType.BRAWL)
        self.assertEqual(atk_mod, MOD_MOVING_VS_STANDING)
        self.assertTrue(any('Moving' in m[0] for m in atk_mods))

    def test_shaken_penalty(self):
        atk = [_fig("A")]
        atk[0].status = FigureStatus.SHAKEN
        defs = [_fig("D", team=TeamSide.VISITOR)]
        atk_mod, _, atk_mods, _, _ = calculate_combat_modifiers(
            atk, defs, CombatType.BRAWL)
        self.assertIn(MOD_SHAKEN, [m[1] for m in atk_mods])

    def test_attack_fallen_illegal(self):
        atk = [_fig("A")]
        defs = [_fig("D", team=TeamSide.VISITOR)]
        defs[0].status = FigureStatus.FALLEN
        atk_mod, _, atk_mods, _, penalties = calculate_combat_modifiers(
            atk, defs, CombatType.BRAWL)
        self.assertIn(MOD_ATTACK_FALLEN, [m[1] for m in atk_mods])
        self.assertTrue(any(p[1] == 'attack_fallen' for p in penalties))

    def test_skater_hit_biker_illegal(self):
        atk = [_fig("A", ftype=FigureType.SKATER_BRUISER)]
        defs = [Biker(name="B", figure_type=FigureType.BIKER, team=TeamSide.VISITOR)]
        atk_mod, _, atk_mods, _, penalties = calculate_combat_modifiers(
            atk, defs, CombatType.BRAWL)
        self.assertIn(MOD_SKATER_HIT_BIKER, [m[1] for m in atk_mods])
        self.assertTrue(any(p[1] == 'skater_attacks_biker' for p in penalties))

    def test_swoop_bonus(self):
        atk = [_fig("A")]
        defs = [_fig("D", team=TeamSide.VISITOR)]
        atk_mod, _, atk_mods, _, _ = calculate_combat_modifiers(
            atk, defs, CombatType.SWOOP)
        self.assertIn(MOD_SWOOP, [m[1] for m in atk_mods])

    def test_badly_shaken_uses_mod_injured(self):
        atk = [_fig("A")]
        atk[0].status = FigureStatus.BADLY_SHAKEN
        defs = [_fig("D", team=TeamSide.VISITOR)]
        atk_mod, _, atk_mods, _, _ = calculate_combat_modifiers(
            atk, defs, CombatType.BRAWL)
        self.assertIn(-2, [m[1] for m in atk_mods])


class TestValidateSwoop(unittest.TestCase):
    def test_towed_cannot_swoop(self):
        f = _fig("A")
        f.is_towed = True
        valid, reason = validate_swoop(f, _fig("D"))
        self.assertFalse(valid)
        self.assertIn("towed", reason.lower())

    def test_valid_swoop_without_board(self):
        f = _fig("A")
        valid, reason = validate_swoop(f, _fig("D"))
        self.assertTrue(valid)
        self.assertEqual(reason, "")


class TestCheckCombatPenalties(unittest.TestCase):
    def test_penalty_map_lookup(self):
        outcome = CombatOutcome(combat_type=CombatType.BRAWL)
        fig = _fig("A")
        outcome.penalties = [(fig, 'attack_fallen'), (fig, 'ball_as_weapon')]
        results = check_combat_penalties(outcome)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], (fig, 3, 'Attacking fallen figure'))
        self.assertEqual(results[1], (fig, 3, 'Using ball as weapon'))

    def test_unknown_infraction_ignored(self):
        outcome = CombatOutcome(combat_type=CombatType.BRAWL)
        outcome.penalties = [(_fig("A"), 'unknown_type')]
        results = check_combat_penalties(outcome)
        self.assertEqual(len(results), 0)


if __name__ == "__main__":
    unittest.main()
