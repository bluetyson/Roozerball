"""Game orchestration for Roozerball.

Coordinates the existing engine modules into a playable turn loop with
phase-by-phase progression and simple built-in computer control.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from roozerball.engine import dice
from roozerball.engine.ball import Ball
from roozerball.engine.board import Board, Square
from roozerball.engine.combat import (
    resolve_brawl,
)
from roozerball.engine.constants import (
    BallState,
    FigureStatus,
    Phase,
    PERIOD_LENGTH,
    NUM_PERIODS,
    Ring,
    TeamSide,
)
from roozerball.engine.penalties import PenaltyEvent, PenaltySystem
from roozerball.engine.scoring import attempt_score, check_scoring_penalties
from roozerball.engine.team import Team


PHASE_ORDER = [
    Phase.CLOCK,
    Phase.BALL,
    Phase.INITIATIVE,
    Phase.MOVEMENT,
    Phase.COMBAT,
    Phase.SCORING,
]
MAX_LOG_ENTRIES = 500


@dataclass
class PhaseResult:
    """Summary of one executed phase."""

    phase: Phase
    messages: List[str] = field(default_factory=list)


class Game:
    """Minimal playable Roozerball match controller."""

    def __init__(
        self,
        home_name: str = "Home",
        visitor_name: str = "Visitor",
    ) -> None:
        self.board = Board()
        self.ball = Ball()
        self.penalties = PenaltySystem()
        self.home_team = Team(TeamSide.HOME, home_name)
        self.visitor_team = Team(TeamSide.VISITOR, visitor_name)

        self.current_period = 1
        self.time_remaining = PERIOD_LENGTH
        self.turn_number = 0
        self.current_phase: Optional[Phase] = None
        self.phase_index = -1
        self.current_initiative_sector: Optional[int] = None
        self.game_over = False
        self.field_reset_pending = False
        self.log: List[str] = []
        self.turn_penalties: List[PenaltyEvent] = []
        self.last_phase_result: Optional[PhaseResult] = None

        self.setup_match()

    @property
    def teams(self) -> List[Team]:
        return [self.home_team, self.visitor_team]

    def setup_match(self) -> None:
        """Generate teams and place the starting lineups."""
        for team in self.teams:
            if not team.roster:
                team.generate_roster()
            team.select_starting_lineup()
        self._reset_field("Kickoff setup")
        self.log.clear()
        self._log("Match ready.")

    def advance_phase(self) -> PhaseResult:
        """Advance to and execute the next phase."""
        if self.game_over:
            result = PhaseResult(Phase.SCORING, ["Game over"])
            self.last_phase_result = result
            return result

        self.phase_index = (self.phase_index + 1) % len(PHASE_ORDER)
        phase = PHASE_ORDER[self.phase_index]
        self.current_phase = phase

        if phase == Phase.CLOCK:
            result = self.execute_clock_phase()
        elif phase == Phase.BALL:
            result = self.execute_ball_phase()
        elif phase == Phase.INITIATIVE:
            result = self.execute_initiative_phase()
        elif phase == Phase.MOVEMENT:
            result = self.execute_movement_phase()
        elif phase == Phase.COMBAT:
            result = self.execute_combat_phase()
        else:
            result = self.execute_scoring_phase()

        self.last_phase_result = result
        return result

    def play_turn(self) -> List[PhaseResult]:
        """Execute phases until the current turn reaches scoring."""
        results: List[PhaseResult] = []
        starting_turn = self.turn_number
        while not self.game_over:
            result = self.advance_phase()
            results.append(result)
            if result.phase == Phase.SCORING and self.turn_number > starting_turn:
                break
        return results

    def execute_clock_phase(self) -> PhaseResult:
        self.turn_number += 1
        messages = [f"Turn {self.turn_number} begins."]

        if self.turn_number > 1:
            self.time_remaining -= 1
            messages.append(f"Clock advances to {self.time_remaining}:00 in period {self.current_period}.")
        else:
            messages.append(f"Period {self.current_period} starts at {self.time_remaining}:00.")
        self.turn_penalties = []

        for figure in self.all_figures(include_benched=True):
            figure.reset_turn()
            figure.advance_timers()

        messages.extend(self._return_ready_figures())

        if self.time_remaining <= 0:
            if self.current_period >= NUM_PERIODS:
                self.game_over = True
                result = self.match_result()
                if result == "Draw":
                    messages.append("Game over. Match ended in a draw.")
                else:
                    messages.append(f"Game over. Winner: {result}.")
            else:
                self.current_period += 1
                self.time_remaining = PERIOD_LENGTH
                self.field_reset_pending = True
                messages.append(f"Start of period {self.current_period}. Field reset queued.")

        self._record_messages(messages)
        return PhaseResult(Phase.CLOCK, messages)

    def execute_ball_phase(self) -> PhaseResult:
        messages: List[str] = []

        if self.ball.state in (BallState.NOT_IN_PLAY, BallState.DEAD):
            self.ball.reset()
            messages.append(self.ball.fire_cannon())
            self.penalties.update_referee_positions(self.ball.sector_index)
            self.field_reset_pending = False
        elif self.ball.carrier is not None:
            messages.append(f"Ball controlled by {self.ball.carrier.name}.")
        else:
            visited = self.ball.move_ball()
            if visited:
                messages.append(
                    f"Ball rolls through {len(visited)} squares at speed {self.ball.speed} on {self.ball.ring.name.lower()}."
                )
            messages.extend(self._resolve_ball_path(visited))
            self.penalties.update_referee_positions(self.ball.sector_index)
            if self.ball.state == BallState.DEAD:
                self.field_reset_pending = True
                messages.append("Ball is dead; field reset queued.")

        self._record_messages(messages)
        return PhaseResult(Phase.BALL, messages)

    def execute_initiative_phase(self) -> PhaseResult:
        sector = dice.roll_d12() - 1
        self.current_initiative_sector = sector
        messages = [f"Initiative starts in sector {self.board.get_sector(sector).name}."]
        self._record_messages(messages)
        return PhaseResult(Phase.INITIATIVE, messages)

    def execute_movement_phase(self) -> PhaseResult:
        messages: List[str] = []
        if self.current_initiative_sector is None:
            messages.append("No initiative sector available.")
            self._record_messages(messages)
            return PhaseResult(Phase.MOVEMENT, messages)

        for figure in self.board.figures_in_initiative_order(self.current_initiative_sector):
            if not figure.is_on_field or figure.is_out_of_play or figure.has_moved:
                continue

            current_square = self.board.find_square_of_figure(figure)
            if current_square is None:
                continue

            if figure.status == FigureStatus.FALLEN:
                messages.extend(self._attempt_stand(figure))
                continue

            destination = self.choose_movement_destination(figure, current_square)
            if destination is None:
                continue

            origin = current_square
            if self.board.move_figure(figure, destination):
                figure.has_moved = True
                messages.append(
                    f"{figure.name} moves {self.board.get_sector(origin.sector_index).name}"
                    f"→{self.board.get_sector(destination.sector_index).name}"
                    f" ({origin.ring.name.lower()}→{destination.ring.name.lower()})."
                )
                if figure.has_ball:
                    messages.extend(self._update_ball_carrier_progress(figure, origin, destination))

        self._record_messages(messages)
        return PhaseResult(Phase.MOVEMENT, messages)

    def execute_combat_phase(self) -> PhaseResult:
        messages: List[str] = []
        if self.current_initiative_sector is None:
            messages.append("No initiative sector available.")
            self._record_messages(messages)
            return PhaseResult(Phase.COMBAT, messages)

        for sector_index in self.board.get_initiative_order(self.current_initiative_sector):
            for square in self.board.squares_in_initiative_order(sector_index):
                home_figures = self._fight_ready_figures(square, TeamSide.HOME)
                visitor_figures = self._fight_ready_figures(square, TeamSide.VISITOR)
                if not home_figures or not visitor_figures:
                    continue

                outcome = resolve_brawl(home_figures, visitor_figures)
                for figure in home_figures + visitor_figures:
                    figure.has_fought = True
                messages.extend(outcome.messages)
                messages.extend(self._apply_outcome_injuries(outcome))
                messages.extend(self._apply_combat_penalties(outcome))
                messages.extend(self._handle_dropped_balls(square))

        self._record_messages(messages)
        return PhaseResult(Phase.COMBAT, messages)

    def execute_scoring_phase(self) -> PhaseResult:
        messages: List[str] = []

        for figure in self.all_figures():
            if not figure.has_ball or not figure.can_score:
                continue
            square = self.board.find_square_of_figure(figure)
            if square is None:
                continue
            target_goal_side = self.opponent_side(figure.team)
            if not square.is_goal or square.goal_side != target_goal_side:
                continue

            standing_opponents = len([
                opp for opp in square.figures_in_square()
                if opp.team != figure.team and opp.is_standing
            ])
            scoring_attempt = attempt_score(
                shooter=figure,
                standing_opponents=standing_opponents,
                distance=0,
            )
            messages.extend(scoring_attempt.messages)
            offense_penalties = [
                event
                for event in self.turn_penalties
                if event.detected and event.figure.team == figure.team
            ]
            negated, negation_message = check_scoring_penalties(offense_penalties)
            if scoring_attempt.success and not negated:
                self.team_for_side(figure.team).add_score(1)
                messages.append(f"{figure.name} scores for {figure.team.value}!")
                self.ball.reset()
                figure.drop_ball()
                self.field_reset_pending = True
            elif negated:
                messages.append(negation_message)
            elif scoring_attempt.missed_shot_result and scoring_attempt.missed_shot_result.dead_ball:
                self.ball.declare_dead()
                self.field_reset_pending = True
                messages.append("Missed shot creates a dead ball.")

        if self.field_reset_pending:
            messages.append(self._reset_field("Scoring/dead-ball reset"))
            self.field_reset_pending = False

        self._record_messages(messages)
        return PhaseResult(Phase.SCORING, messages)

    def choose_movement_destination(self, figure: Any, current_square: Square) -> Optional[Square]:
        """Choose a simple AI destination for a figure."""
        reachable = [square for square, _ in self._movement_options_with_costs(figure, current_square)]
        if not reachable:
            return None

        if figure.has_ball:
            goal_sector = self.goal_sector_for_team(figure.team)
            return max(
                reachable,
                key=lambda square: (
                    square.sector_index == goal_sector,
                    square.ring == Ring.UPPER,
                    -self.board.sector_distance(square.sector_index, goal_sector),
                    square.ring.value,
                ),
            )

        if self.ball.carrier is None and self.ball.state in (BallState.IN_CANNON, BallState.ON_TRACK) and figure.can_field_ball:
            return min(
                reachable,
                key=lambda square: (
                    self._sector_gap(square.sector_index, self.ball.sector_index),
                    abs(square.ring.value - self.ball.ring.value),
                    -square.ring.value,
                ),
            )

        goal_sector = self.goal_sector_for_team(figure.team)
        return max(
            reachable,
            key=lambda square: (
                self.board.sector_distance(current_square.sector_index, square.sector_index),
                square.ring.value,
                -self.board.sector_distance(square.sector_index, goal_sector),
            ),
        )

    def movement_options(self, figure: Any) -> List[Square]:
        return [square for square, _ in self.movement_options_with_costs(figure)]

    def movement_options_with_costs(self, figure: Any) -> List[tuple[Square, int]]:
        square = self.board.find_square_of_figure(figure)
        return self._movement_options_with_costs(figure, square)

    def all_figures(self, include_benched: bool = False) -> List[Any]:
        figures: List[Any] = []
        for team in self.teams:
            figures.extend(team.roster if include_benched else team.active_figures)
        return figures

    def team_for_side(self, side: TeamSide) -> Team:
        return self.home_team if side == TeamSide.HOME else self.visitor_team

    def opponent_side(self, side: TeamSide) -> TeamSide:
        return TeamSide.VISITOR if side == TeamSide.HOME else TeamSide.HOME

    def goal_sector_for_team(self, side: TeamSide) -> int:
        return self.board.visitor_goal_sector if side == TeamSide.HOME else self.board.home_goal_sector

    def match_result(self) -> str:
        if self.home_team.score == self.visitor_team.score:
            return "Draw"
        return self.home_team.name if self.home_team.score > self.visitor_team.score else self.visitor_team.name

    def snapshot(self) -> Dict[str, Any]:
        """Return a serializable match snapshot for the GUI."""
        return {
            "period": self.current_period,
            "time_remaining": self.time_remaining,
            "turn": self.turn_number,
            "phase": self.current_phase.value if self.current_phase else "setup",
            "initiative_sector": self.current_initiative_sector,
            "scores": {
                self.home_team.name: self.home_team.score,
                self.visitor_team.name: self.visitor_team.score,
            },
            "ball": {
                "state": self.ball.state.value,
                "temperature": self.ball.temperature.value,
                "speed": self.ball.speed,
                "sector_index": self.ball.sector_index,
                "ring": self.ball.ring.name.lower(),
                "position": self.ball.position,
                "carrier": getattr(self.ball.carrier, "name", None),
            },
        }

    def _apply_outcome_injuries(self, outcome: Any) -> List[str]:
        messages: List[str] = []
        for figure in self.all_figures():
            injury = outcome.injuries.get(id(figure))
            if injury is None:
                continue
            messages.extend(self._apply_injury_result(figure, injury))
        return messages

    def _apply_combat_penalties(self, outcome: Any) -> List[str]:
        messages: List[str] = []
        for figure, infraction in outcome.penalties:
            event = self.penalties.check_infraction(figure, infraction)
            if event.detected:
                messages.append(self._enforce_penalty(event))
            else:
                messages.append(event.message)
        return messages

    def _attempt_stand(self, figure: Any) -> List[str]:
        result = dice.skill_check(figure.skill)
        figure.has_moved = True
        if result.success:
            figure.status = FigureStatus.STANDING
            return [f"{figure.name} stands up ({result.roll} vs {result.target})."]

        injury = dice.roll_injury_dice(fatality=False)
        messages = [f"{figure.name} fails to stand ({result.roll} vs {result.target})."]
        messages.extend(self._apply_injury_result(figure, injury))
        return messages

    def _return_ready_figures(self) -> List[str]:
        messages: List[str] = []
        for figure in self.all_figures():
            if figure.is_on_field or not figure.is_ready_to_return() or figure.is_out_of_play:
                continue
            sector_index = 0 if figure.team == TeamSide.HOME else 6
            for position in range(3):
                if self.board.place_figure(figure, sector_index, Ring.MIDDLE, position):
                    figure.status = FigureStatus.STANDING
                    figure.is_on_field = True
                    messages.append(f"{figure.name} returns to play.")
                    break
        return messages

    def _resolve_ball_path(self, visited: Iterable[Dict[str, Any]]) -> List[str]:
        messages: List[str] = []
        for square_info in visited:
            square = self.board.get_square(
                square_info["sector"],
                square_info["ring"],
                square_info["position"],
            )
            figures = square.figures_in_square()
            if not figures:
                continue

            catchers = [figure for figure in figures if figure.can_field_ball and figure.is_on_field]
            if catchers:
                catcher = max(catchers, key=lambda figure: figure.skill)
                result = self.ball.attempt_field(catcher)
                messages.append(f"{catcher.name}: {result.message}")
                if result.injury_result is not None:
                    messages.extend(self._apply_injury_result(catcher, result.injury_result))
                if result.success:
                    break
                continue

            for figure in figures:
                avoid = dice.skill_check(figure.skill)
                if avoid.success:
                    messages.append(f"{figure.name} avoids the ball.")
                    continue
                figure.fall()
                messages.append(f"{figure.name} is clipped by the ball and falls.")
        return messages

    def _update_ball_carrier_progress(self, figure: Any, origin: Square, destination: Square) -> List[str]:
        self.ball.sector_index = destination.sector_index
        self.ball.ring = destination.ring
        self.ball.position = destination.position
        sector_steps = self.board.sector_distance(origin.sector_index, destination.sector_index)
        if destination.sector_index == origin.sector_index and destination.ring != origin.ring:
            sector_steps = 0

        messages: List[str] = []
        if sector_steps <= 0:
            return messages

        self.ball.carried_sector_progress += sector_steps
        if not self.ball.is_activated and self.ball.carried_sector_progress >= 12:
            messages.append(self.ball.activate(figure.team))
            self.ball.carried_sector_progress -= 12

        while self.ball.carried_sector_progress >= 12:
            self.ball.carried_sector_progress -= 12
            if self.ball.is_activated:
                self.ball.laps_since_activation += 1
                if self.ball.check_three_lap_limit():
                    self.field_reset_pending = True
                    messages.append("Three-lap limit reached; dead ball.")
                    break
        return messages

    def _apply_injury_result(self, figure: Any, injury: Any) -> List[str]:
        messages: List[str] = [f"{figure.name}: {injury.details}"]
        injury_type = getattr(injury, "injury_type", "none")
        body_part = getattr(injury, "body_part", None)
        duration = getattr(injury, "duration", 0)

        if injury_type == "shaken":
            figure.status = FigureStatus.SHAKEN
            figure.shaken_time = duration
        elif injury_type == "badly_shaken":
            figure.status = FigureStatus.BADLY_SHAKEN
            figure.shaken_time = duration
        elif injury_type == "injured":
            figure.status = FigureStatus.INJURED
            figure.rest_time = duration
            if body_part:
                figure.injuries.append(f"injured_{body_part}")
                if "arm" in body_part:
                    figure.injuries.append("broken_arm")
        elif injury_type == "unconscious":
            figure.status = FigureStatus.UNCONSCIOUS
            figure.is_on_field = False
            self._remove_from_board(figure)
        elif injury_type == "dead":
            figure.status = FigureStatus.DEAD
            figure.is_on_field = False
            self._remove_from_board(figure)

        if figure.has_ball and figure.status != FigureStatus.STANDING:
            messages.extend(self._drop_ball_from_carrier(figure))
        return messages

    def _handle_dropped_balls(self, square: Square) -> List[str]:
        for figure in square.figures_in_square():
            if figure.has_ball and not figure.is_standing:
                return self._drop_ball_from_carrier(figure)
        return []

    def _drop_ball_from_carrier(self, figure: Any) -> List[str]:
        if self.ball.carrier is not figure:
            return []
        message = self.ball.drop()
        figure.drop_ball()
        self.ball.sector_index = figure.sector_index or 0
        self.ball.ring = figure.ring or Ring.MIDDLE
        self.ball.position = figure.square_position or 0
        return [message]

    def _fight_ready_figures(self, square: Square, team_side: TeamSide) -> List[Any]:
        return [
            figure
            for figure in square.figures_in_square()
            if figure.team == team_side and figure.can_fight
        ]

    def _enforce_penalty(self, event: PenaltyEvent) -> str:
        figure = event.figure
        self.turn_penalties.append(event)
        message = self.penalties.enforce_penalty(event)
        self._remove_from_board(figure)
        team = self.team_for_side(figure.team)
        if figure not in team.penalty_box:
            team.penalty_box.append(figure)
        return message

    def _remove_from_board(self, figure: Any) -> None:
        square = self.board.find_square_of_figure(figure)
        if square is not None:
            square.remove_figure(figure)
        figure.sector_index = None
        figure.ring = None
        figure.square_position = None
        figure.slot_index = None

    def _reset_field(self, reason: str) -> str:
        for figure in self.all_figures(include_benched=True):
            figure.drop_ball()
            if figure.status in (FigureStatus.MAN_TO_MAN, FigureStatus.FALLEN):
                figure.status = FigureStatus.STANDING
        self.board.place_starting_positions(
            [figure for figure in self.home_team.figures_on_field()],
            [figure for figure in self.visitor_team.figures_on_field()],
        )
        self.ball.reset()
        return reason

    def _record_messages(self, messages: Iterable[str]) -> None:
        for message in messages:
            self._log(message)

    def _log(self, message: str) -> None:
        self.log.append(message)
        if len(self.log) > MAX_LOG_ENTRIES:
            self.log = self.log[-MAX_LOG_ENTRIES:]

    @staticmethod
    def _sector_gap(first: int, second: int) -> int:
        return min((first - second) % 12, (second - first) % 12)

    def _movement_options_with_costs(
        self,
        figure: Any,
        square: Optional[Square],
    ) -> List[tuple[Square, int]]:
        if square is None:
            return []
        return [
            (candidate, cost)
            for candidate, cost in self.board.squares_in_range(square, figure.speed, figure.figure_type)
            if candidate.has_space_for(figure.figure_type)
            and candidate.controlling_team() not in (self.opponent_side(figure.team),)
        ]
