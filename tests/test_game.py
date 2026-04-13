import unittest
from unittest.mock import patch

from roozerball.engine.ball import Ball
from roozerball.engine.constants import BallState, FigureStatus, Ring
from roozerball.engine.dice import CheckResult, InjuryResult
from roozerball.engine.game import Game


class GamePhaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = Game("Wombats", "Dropbears")

    def test_fallen_figure_attempts_to_stand_successfully(self) -> None:
        figure = self.game.home_team.active_figures[0]
        figure.status = FigureStatus.FALLEN
        self.game.current_initiative_sector = figure.sector_index

        with patch("roozerball.engine.game.dice.skill_check", return_value=CheckResult(True, 6, 7)):
            result = self.game.execute_movement_phase()

        self.assertIn("stands up", " ".join(result.messages))
        self.assertEqual(figure.status, FigureStatus.STANDING)
        self.assertTrue(figure.has_moved)

    def test_fallen_figure_failed_stand_applies_injury(self) -> None:
        figure = self.game.home_team.active_figures[0]
        figure.status = FigureStatus.FALLEN
        self.game.current_initiative_sector = figure.sector_index

        with patch("roozerball.engine.game.dice.skill_check", return_value=CheckResult(False, 11, 7)):
            with patch(
                "roozerball.engine.game.dice.roll_injury_dice",
                return_value=InjuryResult("shaken", 2, "body", "shaken result"),
            ):
                result = self.game.execute_movement_phase()

        self.assertIn("fails to stand", " ".join(result.messages))
        self.assertEqual(figure.status, FigureStatus.SHAKEN)
        self.assertEqual(figure.shaken_time, 2)

    def test_ball_path_avoidance_success_and_failure(self) -> None:
        figure = self.game.home_team.active_figures[0]
        self.game.board.clear_all_figures()
        self.game.board.clear_figure_positions(self.game.all_figures(include_benched=True))
        self.game.board.place_figure(figure, 0, Ring.MIDDLE, 0)
        path = [{"sector": 0, "ring": Ring.MIDDLE, "position": 0}]

        with patch("roozerball.engine.game.dice.skill_check", return_value=CheckResult(True, 5, 7)):
            messages = self.game._resolve_ball_path(path)
        self.assertIn("avoids the ball", " ".join(messages))
        self.assertEqual(figure.status, FigureStatus.STANDING)

        figure.status = FigureStatus.STANDING
        with patch("roozerball.engine.game.dice.skill_check", return_value=CheckResult(False, 11, 7)):
            messages = self.game._resolve_ball_path(path)
        self.assertIn("falls", " ".join(messages))
        self.assertEqual(figure.status, FigureStatus.FALLEN)

    def test_three_lap_limit_sets_dead_ball(self) -> None:
        figure = self.game.home_team.active_figures[0]
        origin = self.game.board.get_square(0, Ring.MIDDLE, 0)
        destination = self.game.board.get_square(1, Ring.MIDDLE, 0)
        self.game.board.place_figure(figure, 0, Ring.MIDDLE, 0)

        figure.pick_up_ball()
        self.game.ball = Ball(
            state=BallState.FIELDED,
            carrier=figure,
            ring=Ring.MIDDLE,
            sector_index=origin.sector_index,
            position=origin.position,
            is_activated=True,
            laps_since_activation=2,
            carried_sector_progress=11,
        )

        messages = self.game._update_ball_carrier_progress(figure, origin, destination)

        self.assertIn("Three-lap limit reached", " ".join(messages))
        self.assertEqual(self.game.ball.state, BallState.DEAD)
        self.assertTrue(self.game.field_reset_pending)


if __name__ == "__main__":
    unittest.main()
