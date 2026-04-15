"""Tests for roozerball.engine.board — Board, Square, Sector."""

import unittest

from roozerball.engine.board import Board, Square, Sector, Slot
from roozerball.engine.constants import (
    Ring, TeamSide, FigureType, FigureStatus,
    SLOTS_FLOOR, SLOTS_INCLINE, NUM_SECTORS, SQUARES_PER_RING,
)
from roozerball.engine.figures import Figure, Biker


def _make_fig(name="F", team=TeamSide.HOME, ftype=FigureType.SKATER_BRUISER,
              status=FigureStatus.STANDING) -> Figure:
    f = Figure(name=name, figure_type=ftype, team=team)
    f.status = status
    return f


class TestSquareCapacity(unittest.TestCase):
    def test_floor_capacity(self):
        sq = Square(0, Ring.FLOOR, 0)
        self.assertEqual(sq.capacity, SLOTS_FLOOR)
        self.assertEqual(len(sq.slots), SLOTS_FLOOR)

    def test_incline_capacity(self):
        for ring in (Ring.LOWER, Ring.MIDDLE, Ring.UPPER, Ring.CANNON):
            sq = Square(0, ring, 0)
            self.assertEqual(sq.capacity, SLOTS_INCLINE, f"ring={ring}")
            self.assertEqual(len(sq.slots), SLOTS_INCLINE, f"ring={ring}")


class TestSquareAddRemoveFigure(unittest.TestCase):
    def test_add_figure_succeeds(self):
        sq = Square(0, Ring.MIDDLE, 0)
        fig = _make_fig()
        self.assertTrue(sq.add_figure(fig))
        self.assertIn(fig, sq.figures_in_square())

    def test_add_figure_specific_slot(self):
        sq = Square(0, Ring.MIDDLE, 0)
        fig = _make_fig()
        self.assertTrue(sq.add_figure(fig, slot_index=2))
        self.assertIs(sq.slots[2].figure, fig)

    def test_add_biker_takes_two_slots(self):
        sq = Square(0, Ring.MIDDLE, 0)
        biker = Biker(name="B", figure_type=FigureType.BIKER, team=TeamSide.HOME)
        self.assertTrue(sq.add_figure(biker))
        occupied = sum(1 for s in sq.slots if s.figure is biker)
        self.assertEqual(occupied, 2)

    def test_add_figure_fails_when_full(self):
        sq = Square(0, Ring.MIDDLE, 0)
        for i in range(SLOTS_INCLINE):
            sq.add_figure(_make_fig(name=f"F{i}"))
        extra = _make_fig(name="Extra")
        self.assertFalse(sq.add_figure(extra))

    def test_remove_figure(self):
        sq = Square(0, Ring.MIDDLE, 0)
        fig = _make_fig()
        sq.add_figure(fig)
        sq.remove_figure(fig)
        self.assertNotIn(fig, sq.figures_in_square())
        self.assertEqual(sq.occupied_slots, 0)


class TestSquareControl(unittest.TestCase):
    def test_controlled_by_majority_upright(self):
        sq = Square(0, Ring.MIDDLE, 0)
        home1 = _make_fig("H1", TeamSide.HOME)
        home2 = _make_fig("H2", TeamSide.HOME)
        visitor = _make_fig("V1", TeamSide.VISITOR)
        sq.add_figure(home1)
        sq.add_figure(home2)
        sq.add_figure(visitor)
        self.assertTrue(sq.is_controlled_by(TeamSide.HOME))
        self.assertFalse(sq.is_controlled_by(TeamSide.VISITOR))

    def test_no_control_when_empty(self):
        sq = Square(0, Ring.MIDDLE, 0)
        self.assertFalse(sq.is_controlled_by(TeamSide.HOME))

    def test_no_control_when_even(self):
        sq = Square(0, Ring.MIDDLE, 0)
        sq.add_figure(_make_fig("H", TeamSide.HOME))
        sq.add_figure(_make_fig("V", TeamSide.VISITOR))
        self.assertFalse(sq.is_controlled_by(TeamSide.HOME))
        self.assertFalse(sq.is_controlled_by(TeamSide.VISITOR))

    def test_fallen_figures_not_counted(self):
        sq = Square(0, Ring.MIDDLE, 0)
        h = _make_fig("H", TeamSide.HOME, status=FigureStatus.FALLEN)
        v = _make_fig("V", TeamSide.VISITOR)
        sq.add_figure(h)
        sq.add_figure(v)
        self.assertFalse(sq.is_controlled_by(TeamSide.HOME))
        self.assertTrue(sq.is_controlled_by(TeamSide.VISITOR))


class TestBoardConstruction(unittest.TestCase):
    def setUp(self):
        self.board = Board()

    def test_twelve_sectors(self):
        self.assertEqual(len(self.board.sectors), 12)

    def test_rings_per_sector(self):
        for sector in self.board.sectors:
            for ring, expected_count in SQUARES_PER_RING.items():
                self.assertEqual(len(sector.rings[ring]), expected_count,
                                 f"sector={sector.name} ring={ring}")

    def test_total_squares(self):
        total = sum(len(sq_list) for sector in self.board.sectors
                    for sq_list in sector.rings.values())
        expected = NUM_SECTORS * sum(SQUARES_PER_RING.values())
        self.assertEqual(total, expected)

    def test_goals_set_up(self):
        self.assertIn(TeamSide.HOME, self.board.goals)
        self.assertIn(TeamSide.VISITOR, self.board.goals)
        self.assertEqual(self.board.goals[TeamSide.HOME].sector_index, 0)
        self.assertEqual(self.board.goals[TeamSide.VISITOR].sector_index, 6)

    def test_goal_squares_flagged(self):
        for sq in self.board.goals[TeamSide.HOME].scoring_squares:
            self.assertTrue(sq.is_goal)
            self.assertEqual(sq.goal_side, TeamSide.HOME)


class TestBoardSectorNavigation(unittest.TestCase):
    def setUp(self):
        self.board = Board()

    def test_next_sector_wraps(self):
        self.assertEqual(self.board.next_sector(11), 0)
        self.assertEqual(self.board.next_sector(0), 1)

    def test_prev_sector_wraps(self):
        self.assertEqual(self.board.prev_sector(0), 11)
        self.assertEqual(self.board.prev_sector(5), 4)

    def test_sector_distance(self):
        self.assertEqual(self.board.sector_distance(0, 3), 3)
        self.assertEqual(self.board.sector_distance(10, 1), 3)


class TestBoardPlaceAndFind(unittest.TestCase):
    def setUp(self):
        self.board = Board()

    def test_place_figure_and_find(self):
        fig = _make_fig()
        self.assertTrue(self.board.place_figure(fig, 3, Ring.MIDDLE, 1))
        sq = self.board.find_square_of_figure(fig)
        self.assertIsNotNone(sq)
        self.assertEqual(sq.sector_index, 3)
        self.assertEqual(sq.ring, Ring.MIDDLE)
        self.assertEqual(sq.position, 1)

    def test_place_updates_figure_position_fields(self):
        fig = _make_fig()
        self.board.place_figure(fig, 5, Ring.UPPER, 2)
        self.assertEqual(fig.sector_index, 5)
        self.assertEqual(fig.ring, Ring.UPPER)
        self.assertEqual(fig.square_position, 2)

    def test_find_returns_none_when_missing(self):
        fig = _make_fig()
        self.assertIsNone(self.board.find_square_of_figure(fig))

    def test_clear_all_figures(self):
        fig = _make_fig()
        self.board.place_figure(fig, 0, Ring.FLOOR, 0)
        self.board.clear_all_figures()
        self.assertIsNone(self.board.find_square_of_figure(fig))


class TestFiguresInInitiativeOrder(unittest.TestCase):
    def setUp(self):
        self.board = Board()

    def test_returns_floor_before_upper(self):
        f_floor = _make_fig("Floor")
        f_upper = _make_fig("Upper")
        self.board.place_figure(f_upper, 0, Ring.UPPER, 0)
        self.board.place_figure(f_floor, 0, Ring.FLOOR, 0)
        order = self.board.figures_in_initiative_order(0)
        self.assertLess(order.index(f_floor), order.index(f_upper))

    def test_sector_order_follows_starting_sector(self):
        f_s0 = _make_fig("S0")
        f_s1 = _make_fig("S1")
        self.board.place_figure(f_s0, 0, Ring.MIDDLE, 0)
        self.board.place_figure(f_s1, 1, Ring.MIDDLE, 0)
        order = self.board.figures_in_initiative_order(0)
        self.assertLess(order.index(f_s0), order.index(f_s1))

    def test_no_duplicates_for_bikers(self):
        biker = Biker(name="B", figure_type=FigureType.BIKER, team=TeamSide.HOME)
        self.board.place_figure(biker, 2, Ring.MIDDLE, 0)
        order = self.board.figures_in_initiative_order(0)
        self.assertEqual(order.count(biker), 1)


class TestInclineBonus(unittest.TestCase):
    def setUp(self):
        self.board = Board()

    def test_single_downhill(self):
        self.assertEqual(self.board.calculate_incline_bonus([-1]), 1)

    def test_consecutive_downhill_two(self):
        self.assertEqual(self.board.calculate_incline_bonus([-1, -1]), 3)

    def test_consecutive_downhill_three(self):
        self.assertEqual(self.board.calculate_incline_bonus([-1, -1, -1]), 5)

    def test_single_uphill(self):
        self.assertEqual(self.board.calculate_incline_bonus([1]), -1)

    def test_consecutive_uphill_two(self):
        self.assertEqual(self.board.calculate_incline_bonus([1, 1]), -3)

    def test_flat_no_change(self):
        self.assertEqual(self.board.calculate_incline_bonus([0, 0]), 0)

    def test_mixed_resets_consecutive(self):
        # down then up resets the consecutive counter
        bonus = self.board.calculate_incline_bonus([-1, 1])
        self.assertEqual(bonus, 0)


class TestBoardAdjacentSquares(unittest.TestCase):
    def setUp(self):
        self.board = Board()

    def test_adjacent_includes_next_and_prev_sector_same_ring(self):
        sq = self.board.get_square(5, Ring.MIDDLE, 0)
        adj = self.board.get_adjacent_squares(sq)
        adj_sector_indices = {s.sector_index for s in adj if s.ring == Ring.MIDDLE}
        self.assertIn(4, adj_sector_indices)
        self.assertIn(6, adj_sector_indices)

    def test_adjacent_includes_cross_ring(self):
        sq = self.board.get_square(3, Ring.MIDDLE, 0)
        adj = self.board.get_adjacent_squares(sq)
        adj_rings = {s.ring for s in adj if s.sector_index == 3}
        self.assertIn(Ring.LOWER, adj_rings)
        self.assertIn(Ring.UPPER, adj_rings)


class TestClearFigurePositions(unittest.TestCase):
    def test_clears_position_fields(self):
        board = Board()
        fig = _make_fig()
        board.place_figure(fig, 2, Ring.LOWER, 0)
        board.clear_figure_positions([fig])
        self.assertIsNone(fig.sector_index)
        self.assertIsNone(fig.ring)
        self.assertIsNone(fig.square_position)
        self.assertIsNone(fig.slot_index)


if __name__ == "__main__":
    unittest.main()
