"""Tests for roozerball.engine.constants lookup helpers."""

import unittest

from roozerball.engine.constants import (
    CombatResult, AssaultResult,
    get_brawl_result, get_assault_result, get_skill_check_info,
)


class TestGetBrawlResult(unittest.TestCase):
    """get_brawl_result uses abs(difference) and maps to CombatResult."""

    def test_indecisive_range(self):
        for d in (0, 1, 2, -1, -2):
            self.assertEqual(get_brawl_result(d), CombatResult.INDECISIVE, f"diff={d}")

    def test_marginal_range(self):
        for d in (3, 4, 5, -3, -5):
            self.assertEqual(get_brawl_result(d), CombatResult.MARGINAL, f"diff={d}")

    def test_decisive_range(self):
        for d in (6, 7, 8, -6, -8):
            self.assertEqual(get_brawl_result(d), CombatResult.DECISIVE, f"diff={d}")

    def test_breakthrough_range(self):
        for d in (9, 10, 11, -9, -11):
            self.assertEqual(get_brawl_result(d), CombatResult.BREAKTHROUGH, f"diff={d}")

    def test_breakaway_range(self):
        for d in (12, 15, 20, -12, -20):
            self.assertEqual(get_brawl_result(d), CombatResult.BREAKAWAY, f"diff={d}")


class TestGetAssaultResult(unittest.TestCase):
    """get_assault_result uses abs(difference) and maps to AssaultResult."""

    def test_fails_range(self):
        for d in (0, 1, 2):
            self.assertEqual(get_assault_result(d), AssaultResult.FAILS, f"diff={d}")

    def test_marginal_range(self):
        for d in (3, 4, 5):
            self.assertEqual(get_assault_result(d), AssaultResult.MARGINAL, f"diff={d}")

    def test_decisive_range(self):
        for d in (6, 7, 8):
            self.assertEqual(get_assault_result(d), AssaultResult.DECISIVE, f"diff={d}")

    def test_breakthrough_block_range(self):
        for d in (9, 10, 14):
            self.assertEqual(get_assault_result(d), AssaultResult.BREAKTHROUGH_BLOCK, f"diff={d}")

    def test_crush_range(self):
        for d in (15, 20):
            self.assertEqual(get_assault_result(d), AssaultResult.CRUSH, f"diff={d}")

    def test_negative_uses_abs(self):
        self.assertEqual(get_assault_result(-7), AssaultResult.DECISIVE)


class TestGetSkillCheckInfo(unittest.TestCase):
    """get_skill_check_info returns dict with who/skill_mod/toughness_mod/fatality/auto_fall/bdd."""

    def test_indecisive_band(self):
        info = get_skill_check_info(1)
        self.assertEqual(info['who'], 'all')
        self.assertEqual(info['skill_mod'], 0)
        self.assertEqual(info['toughness_mod'], 0)
        self.assertFalse(info['fatality'])
        self.assertFalse(info['auto_fall'])
        self.assertFalse(info['bdd'])

    def test_marginal_band(self):
        info = get_skill_check_info(4)
        self.assertEqual(info['who'], 'losers')
        self.assertEqual(info['skill_mod'], 0)
        self.assertFalse(info['fatality'])

    def test_decisive_band(self):
        info = get_skill_check_info(7)
        self.assertEqual(info['who'], 'losers')
        self.assertEqual(info['skill_mod'], -1)
        self.assertFalse(info['fatality'])

    def test_breakthrough_band(self):
        info = get_skill_check_info(10)
        self.assertEqual(info['who'], 'losers')
        self.assertEqual(info['skill_mod'], -2)
        self.assertEqual(info['toughness_mod'], -1)
        self.assertTrue(info['fatality'])
        self.assertFalse(info['auto_fall'])

    def test_breakaway_band_12_14(self):
        info = get_skill_check_info(13)
        self.assertEqual(info['skill_mod'], -3)
        self.assertEqual(info['toughness_mod'], -2)
        self.assertTrue(info['fatality'])
        self.assertFalse(info['bdd'])

    def test_crush_band_15_plus(self):
        info = get_skill_check_info(16)
        self.assertTrue(info['auto_fall'])
        self.assertTrue(info['bdd'])
        self.assertTrue(info['fatality'])
        self.assertEqual(info['toughness_mod'], -3)

    def test_negative_difference_uses_abs(self):
        info = get_skill_check_info(-10)
        self.assertEqual(info['who'], 'losers')
        self.assertEqual(info['skill_mod'], -2)

    def test_returns_all_expected_keys(self):
        info = get_skill_check_info(0)
        for key in ('who', 'skill_mod', 'toughness_mod', 'fatality', 'auto_fall', 'bdd'):
            self.assertIn(key, info)


if __name__ == "__main__":
    unittest.main()
