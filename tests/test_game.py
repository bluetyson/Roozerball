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
        self.assertTrue(figure.needs_stand_up)

    def test_fallen_figure_with_no_injury_failure_auto_stands_next_turn(self) -> None:
        figure = self.game.home_team.active_figures[0]
        figure.fall()
        self.game.current_initiative_sector = figure.sector_index

        with patch("roozerball.engine.game.dice.skill_check", return_value=CheckResult(False, 10, 7)):
            with patch(
                "roozerball.engine.game.dice.roll_injury_dice",
                return_value=InjuryResult("none", 0, None, "no injury"),
            ):
                first = self.game.execute_movement_phase()

        self.assertIn("will stand automatically next turn", " ".join(first.messages))
        self.assertTrue(figure.needs_stand_up)
        self.assertTrue(figure.auto_stand_next_turn)

        figure.has_moved = False
        second = self.game.execute_movement_phase()
        self.assertIn("automatically stands", " ".join(second.messages))
        self.assertFalse(figure.needs_stand_up)
        self.assertEqual(figure.status, FigureStatus.STANDING)

    def test_shaken_prone_figure_continues_standing_attempts(self) -> None:
        figure = self.game.home_team.active_figures[0]
        figure.status = FigureStatus.SHAKEN
        figure.shaken_time = 2
        figure.needs_stand_up = True
        self.game.current_initiative_sector = figure.sector_index

        with patch("roozerball.engine.game.dice.skill_check", side_effect=[CheckResult(False, 9, 6), CheckResult(True, 4, 6)]):
            with patch(
                "roozerball.engine.game.dice.roll_injury_dice",
                return_value=InjuryResult("none", 0, None, "no injury"),
            ):
                first = self.game.execute_movement_phase()
                figure.has_moved = False
                second = self.game.execute_movement_phase()

        self.assertIn("fails to stand", " ".join(first.messages))
        self.assertIn("stands", " ".join(second.messages))
        self.assertFalse(figure.needs_stand_up)

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
        self.assertFalse(self.game.field_reset_pending)

    def test_ball_carrier_must_enter_new_sector_or_ball_goes_dead(self) -> None:
        figure = self.game.home_team.active_figures[0]
        self.game.board.clear_all_figures()
        self.game.board.clear_figure_positions(self.game.all_figures(include_benched=True))
        self.game.board.place_figure(figure, 0, Ring.MIDDLE, 0)
        self.game.ball.state = BallState.FIELDED
        self.game.ball.carrier = figure
        figure.pick_up_ball()
        self.game.current_initiative_sector = figure.sector_index

        with patch.object(self.game, "choose_movement_destination", return_value=self.game.board.get_square(0, Ring.UPPER, 0)):
            result = self.game.execute_movement_phase()

        self.assertIn("failed to move into a new sector", " ".join(result.messages))
        self.assertEqual(self.game.ball.state, BallState.DEAD)

    def test_ball_carrier_can_hold_goal_sector_for_up_to_two_turns(self) -> None:
        figure = self.game.home_team.active_figures[0]
        self.game.board.clear_all_figures()
        self.game.board.clear_figure_positions(self.game.all_figures(include_benched=True))
        self.game.board.place_figure(figure, self.game.board.visitor_goal_sector, Ring.UPPER, 0)
        self.game.ball.state = BallState.FIELDED
        self.game.ball.carrier = figure
        figure.pick_up_ball()
        self.game.current_initiative_sector = figure.sector_index

        goal_square = self.game.board.get_square(self.game.board.visitor_goal_sector, Ring.UPPER, 0)
        with patch.object(self.game, "choose_movement_destination", return_value=goal_square):
            first = self.game.execute_movement_phase()
        self.assertIn("holds in the goal sector", " ".join(first.messages))
        self.assertEqual(self.game.ball.state, BallState.FIELDED)

        figure.has_moved = False
        with patch.object(self.game, "choose_movement_destination", return_value=goal_square):
            second = self.game.execute_movement_phase()
        self.assertIn("holds in the goal sector", " ".join(second.messages))
        self.assertEqual(self.game.ball.state, BallState.FIELDED)

        figure.has_moved = False
        with patch.object(self.game, "choose_movement_destination", return_value=goal_square):
            third = self.game.execute_movement_phase()
        self.assertIn("failed to move into a new sector", " ".join(third.messages))
        self.assertEqual(self.game.ball.state, BallState.DEAD)

    def test_dead_ball_from_ball_phase_does_not_queue_field_reset(self) -> None:
        self.game.ball.state = BallState.ON_TRACK
        self.game.ball.speed = 1
        self.game.ball.sector_index = 0
        self.game.ball.ring = Ring.MIDDLE
        self.game.ball.turns_since_fired = 6

        result = self.game.execute_ball_phase()

        self.assertIn("teams hold their places", " ".join(result.messages))
        self.assertEqual(self.game.ball.state, BallState.DEAD)
        self.assertFalse(self.game.field_reset_pending)

    def test_successful_goal_still_resets_the_field(self) -> None:
        figure = self.game.home_team.active_figures[0]
        self.game.board.clear_all_figures()
        self.game.board.clear_figure_positions(self.game.all_figures(include_benched=True))
        self.game.board.place_figure(figure, self.game.board.visitor_goal_sector, Ring.UPPER, 0)
        self.game.ball.state = BallState.FIELDED
        self.game.ball.carrier = figure
        self.game.ball.sector_index = figure.sector_index
        self.game.ball.ring = figure.ring
        self.game.ball.position = figure.square_position
        figure.pick_up_ball()

        with patch("roozerball.engine.scoring.dice.roll_2d6", return_value=2):
            result = self.game.execute_scoring_phase()

        self.assertIn("scores for home", " ".join(result.messages))
        self.assertIn("Scoring/dead-ball reset", " ".join(result.messages))
        self.assertEqual(self.game.home_team.score, 1)
        self.assertEqual(self.game.ball.state, BallState.NOT_IN_PLAY)
        self.assertFalse(self.game.field_reset_pending)

    def test_movement_options_do_not_offer_clockwise_destinations(self) -> None:
        figure = self.game.home_team.active_figures[0]
        self.game.board.clear_all_figures()
        self.game.board.clear_figure_positions(self.game.all_figures(include_benched=True))
        self.game.board.place_figure(figure, 0, Ring.MIDDLE, 0)

        options = self.game.movement_options(figure)
        clockwise_sector = self.game.board.prev_sector(0)

        self.assertTrue(options)
        self.assertFalse(any(square.sector_index == clockwise_sector for square in options))

    def test_biker_movement_options_exclude_goal_restricted_upper_track(self) -> None:
        biker = next(figure for figure in self.game.home_team.active_figures if figure.is_biker)
        self.game.board.clear_all_figures()
        self.game.board.clear_figure_positions(self.game.all_figures(include_benched=True))
        self.game.board.place_figure(biker, 5, Ring.UPPER, 0)

        options = self.game.movement_options(biker)
        restricted = {11, 0, 1, 5, 6, 7}
        self.assertFalse(any(square.ring == Ring.UPPER and square.sector_index in restricted for square in options))

    def test_biker_holding_ball_is_penalized_and_creates_dead_ball(self) -> None:
        biker = next(figure for figure in self.game.home_team.active_figures if figure.is_biker)
        self.game.board.clear_all_figures()
        self.game.board.clear_figure_positions(self.game.all_figures(include_benched=True))
        self.game.board.place_figure(biker, 2, Ring.MIDDLE, 0)
        biker.pick_up_ball()
        self.game.ball.state = BallState.FIELDED
        self.game.ball.carrier = biker
        self.game.current_initiative_sector = 2

        with patch("roozerball.engine.penalties.dice.referee_check", return_value=CheckResult(True, 5, 8)):
            result = self.game.execute_movement_phase()

        self.assertIn("biker cannot legally handle the ball", " ".join(result.messages).lower())
        self.assertEqual(self.game.ball.state, BallState.DEAD)
        self.assertFalse(biker.has_ball)


if __name__ == "__main__":
    unittest.main()
