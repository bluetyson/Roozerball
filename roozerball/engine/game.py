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
    validate_swoop,
)
from roozerball.engine.constants import (
    BallState,
    FigureStatus,
    FigureType,
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
BIKER_SCORING_INTERFERENCE_BASE_PENALTY = 3
BIKER_SCORING_INTERFERENCE_PER_OPPONENT = 3
# H3: endurance — max play time = toughness + 3; rest 3-6 min
ENDURANCE_REST_MIN = 3
ENDURANCE_REST_MAX = 6


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
        messages.extend(self._enforce_biker_ball_handling())

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
            # F14: loose ball pickup — figures in ball's path may use action to pick up
            if self.ball.state in (BallState.ON_TRACK,) and self.ball.carrier is None:
                ball_sq = self.board.get_square(
                    self.ball.sector_index, self.ball.ring, self.ball.position
                )
                for fig in ball_sq.figures_in_square():
                    if self.ball.carrier is not None:
                        break
                    messages.extend(self._try_loose_ball_pickup(fig, ball_sq))
            self.penalties.update_referee_positions(self.ball.sector_index)
            if self.ball.state == BallState.DEAD:
                messages.append("Ball is dead; teams hold their places for the next cannon blast.")

        self._record_messages(messages)
        return PhaseResult(Phase.BALL, messages)

    def execute_initiative_phase(self) -> PhaseResult:
        sector = dice.roll_d12() - 1
        self.current_initiative_sector = sector
        messages = [f"Initiative starts in sector {self.board.get_sector(sector).name}."]
        self._record_messages(messages)
        return PhaseResult(Phase.INITIATIVE, messages)

    def execute_movement_phase(self) -> PhaseResult:
        messages: List[str] = self._enforce_biker_ball_handling()
        if self.current_initiative_sector is None:
            messages.append("No initiative sector available.")
            self._record_messages(messages)
            return PhaseResult(Phase.MOVEMENT, messages)

        initial_carrier = self.ball.carrier
        initial_sector = initial_carrier.sector_index if initial_carrier is not None else None

        for figure in self.board.figures_in_initiative_order(self.current_initiative_sector):
            if not figure.is_on_field or figure.is_out_of_play or figure.has_moved:
                continue

            current_square = self.board.find_square_of_figure(figure)
            if current_square is None:
                continue

            # Backwards compatibility for callers/tests that set status directly
            # without calling Figure.fall().
            if figure.status == FigureStatus.FALLEN and not getattr(figure, "needs_stand_up", False):
                figure.needs_stand_up = True
            if getattr(figure, "needs_stand_up", False):
                messages.extend(self._attempt_stand(figure))
                continue

            destination = self.choose_movement_destination(figure, current_square)
            if destination is None:
                continue
            if not self._is_legal_movement_destination(figure, current_square, destination):
                messages.extend(self._handle_illegal_movement(figure, current_square, destination))
                continue
            if self._is_biker_goal_restricted_square(figure, destination):
                event = self.penalties.check_infraction(
                    figure,
                    "biker_near_goal",
                    ball_sector=self.ball.sector_index,
                )
                if event.detected:
                    messages.append(self._enforce_penalty(event))
                else:
                    messages.append(event.message)
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
                # F21-F24: obstacle skill check on entering square
                messages.extend(self._check_obstacle_entry(figure, destination))
                # F11: hand-off opportunity when ball carrier reaches a teammate
                if figure.has_ball:
                    messages.extend(self._check_handoff_opportunity(figure))
                # H3: track endurance
                self._advance_endurance(figure)

        messages.extend(self._enforce_ball_carrier_movement(initial_carrier, initial_sector))
        # A11: Goal tending — check if defense set up a screen but shooter didn't attempt
        messages.extend(self._check_goal_tending())
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

                # G12-G13: attacker picks one opposing figure; AI picks highest-combat
                # opponent, but all teammates in base-to-base may join
                outcome = resolve_brawl(home_figures, visitor_figures, board=self.board)
                for figure in home_figures + visitor_figures:
                    figure.has_fought = True
                    # H3: each combat subtracts 1 min from endurance
                    figure.endurance_used = getattr(figure, 'endurance_used', 0) + 1
                messages.extend(outcome.messages)
                messages.extend(self._apply_outcome_injuries(outcome))
                messages.extend(self._apply_combat_penalties(outcome))
                messages.extend(self._handle_dropped_balls(square))

        self._record_messages(messages)
        return PhaseResult(Phase.COMBAT, messages)

    def execute_scoring_phase(self) -> PhaseResult:
        messages: List[str] = self._enforce_biker_ball_handling()

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
            offense_penalties.extend(
                self._apply_biker_scoring_interference_penalties(
                    shooter=figure,
                    goal_square=square,
                    standing_opponents=standing_opponents,
                )
            )
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
        if getattr(figure, "auto_stand_next_turn", False):
            figure.has_moved = True
            self._complete_stand_up(figure)
            return [f"{figure.name} recovers and automatically stands."]

        modifier = self._standing_modifier(figure)
        result = dice.skill_check(figure.skill, modifier)
        figure.has_moved = True
        if result.success:
            self._complete_stand_up(figure)
            return [f"{figure.name} stands up ({result.roll} vs {result.target})."]

        injury = dice.roll_injury_dice(fatality=False)
        figure.needs_stand_up = True
        figure.auto_stand_next_turn = injury.injury_type == "none"
        messages = [f"{figure.name} fails to stand ({result.roll} vs {result.target})."]
        messages.extend(self._apply_injury_result(figure, injury))
        if injury.injury_type == "none":
            messages.append(f"{figure.name} appears uninjured and will stand automatically next turn.")
        return messages

    @staticmethod
    def _complete_stand_up(figure: Any) -> None:
        figure.needs_stand_up = False
        figure.auto_stand_next_turn = False
        if figure.status == FigureStatus.FALLEN:
            figure.status = FigureStatus.STANDING

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
                    figure.needs_stand_up = False
                    figure.auto_stand_next_turn = False
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
                    messages.append("Three-lap limit reached; dead ball.")
                    break
        return messages

    def _enforce_ball_carrier_movement(
        self,
        initial_carrier: Any,
        initial_sector: Optional[int],
    ) -> List[str]:
        """Enforce Rule B2 after movement resolution.

        Returns no messages when there is no continuing carrier to check or when
        the carrier advanced into a new sector. A carrier may remain in the
        attacking goal sector for up to two consecutive turns to complete a
        scoring attempt; otherwise the ball goes dead immediately.

        Returns:
            A list of status messages describing a legal goal-sector hold or the
            dead-ball outcome. An empty list means no follow-up message was needed.
        """
        if initial_carrier is None or self.ball.carrier is not initial_carrier:
            return []

        if not initial_carrier.has_ball:
            return []

        current_square = self.board.find_square_of_figure(initial_carrier)
        if current_square is None:
            return []

        if initial_sector is not None and current_square.sector_index != initial_sector:
            self.ball.stationary_goal_turns = 0
            return []

        is_attacking_goal = current_square.is_goal and current_square.goal_side == self.opponent_side(initial_carrier.team)
        if is_attacking_goal:
            self.ball.stationary_goal_turns += 1
            if self.ball.stationary_goal_turns <= 2:
                return [
                    f"{initial_carrier.name} holds in the goal sector for a scoring attempt "
                    f"({self.ball.stationary_goal_turns}/2)."
                ]

        self.ball.declare_dead()
        return ["Dead ball: the carrier failed to move into a new sector."]

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
            figure.needs_stand_up = False
            figure.auto_stand_next_turn = False
            self._remove_from_board(figure)
        elif injury_type == "dead":
            figure.status = FigureStatus.DEAD
            figure.is_on_field = False
            figure.needs_stand_up = False
            figure.auto_stand_next_turn = False
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
            figure.needs_stand_up = False
            figure.auto_stand_next_turn = False
            figure.released_tow_bar_this_turn = False
            figure.goal_screen_lap = None
            # Detach any tow bars
            if getattr(figure, 'tow_bar_holder', False):
                figure.is_towed = False
                figure.tow_bar_holder = False
                figure.towed_by = None
            if hasattr(figure, 'towing'):
                figure.towing.clear()
            # Clear carrying state
            figure.is_being_carried = False
            figure.carried_by = None
            figure.is_carrying = None
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
            and not self._is_biker_goal_restricted_square(figure, candidate)
        ]

    def _is_legal_movement_destination(self, figure: Any, origin: Square, destination: Square) -> bool:
        legal_destinations = {id(square) for square, _ in self._movement_options_with_costs(figure, origin)}
        return id(destination) in legal_destinations

    def _handle_illegal_movement(self, figure: Any, origin: Square, destination: Square) -> List[str]:
        clockwise_sector = self.board.prev_sector(origin.sector_index)
        if destination.sector_index != clockwise_sector:
            return [f"{figure.name} cannot move to an illegal destination and holds position."]

        offense_count = getattr(figure, "clockwise_offenses", 0) + 1
        setattr(figure, "clockwise_offenses", offense_count)
        infraction = "clockwise_movement_1st" if offense_count == 1 else "clockwise_movement_2nd"
        event = self.penalties.check_infraction(
            figure,
            infraction,
            ball_sector=self.ball.sector_index,
        )
        if event.detected:
            return [self._enforce_penalty(event)]
        return [event.message]

    def _standing_modifier(self, figure: Any) -> int:
        modifier = 0
        shaken_time = getattr(figure, "shaken_time", 0)
        if shaken_time > 0:
            modifier -= 1
            if shaken_time >= 4:
                modifier -= 1
        if any(injury.startswith("injured_") for injury in getattr(figure, "injuries", [])):
            modifier -= 1
        if "broken_arm" in getattr(figure, "injuries", []):
            modifier -= 1
        return modifier

    def _goal_adjacent_sectors(self, goal_sector: int) -> set[int]:
        return {
            goal_sector,
            self.board.prev_sector(goal_sector),
            self.board.next_sector(goal_sector),
        }

    def _is_biker_goal_restricted_square(self, figure: Any, square: Square) -> bool:
        if not getattr(figure, "is_biker", False):
            return False
        if square.ring != Ring.UPPER:
            return False
        restricted = self._goal_adjacent_sectors(self.board.home_goal_sector) | self._goal_adjacent_sectors(
            self.board.visitor_goal_sector
        )
        return square.sector_index in restricted

    def _apply_biker_scoring_interference_penalties(
        self,
        shooter: Any,
        goal_square: Square,
        standing_opponents: int,
    ) -> List[PenaltyEvent]:
        events: List[PenaltyEvent] = []
        for figure in self.all_figures():
            if figure.team != shooter.team or not getattr(figure, "is_biker", False) or not figure.is_on_field:
                continue
            square = self.board.find_square_of_figure(figure)
            if square is None or square.ring != Ring.UPPER:
                continue
            if square.sector_index not in self._goal_adjacent_sectors(goal_square.sector_index):
                continue
            event = self.penalties.check_infraction(
                figure,
                "biker_scoring_interference",
                ball_sector=self.ball.sector_index,
                during_scoring=True,
            )
            event.minutes = BIKER_SCORING_INTERFERENCE_BASE_PENALTY + (
                BIKER_SCORING_INTERFERENCE_PER_OPPONENT * standing_opponents
            )
            if event.detected:
                self._enforce_penalty(event)
            events.append(event)
        return events

    def _enforce_biker_ball_handling(self) -> List[str]:
        carrier = self.ball.carrier
        if carrier is None or not getattr(carrier, "is_biker", False):
            return []
        event = self.penalties.check_infraction(
            carrier,
            "biker_handles_ball",
            ball_sector=self.ball.sector_index,
        )
        messages: List[str] = []
        if event.detected:
            messages.append(self._enforce_penalty(event))
        else:
            messages.append(event.message)
        self.ball.declare_dead()
        messages.append("Dead ball: biker cannot legally handle the ball.")
        return messages

    # -----------------------------------------------------------------------
    # F21-F24: Obstacle skill check when entering a square
    # -----------------------------------------------------------------------

    def _check_obstacle_entry(self, figure: Any, square: Square) -> List[str]:
        """Rule F21-F24: skill check when entering a square with an obstacle."""
        messages: List[str] = []
        # F24: Cannot enter full or controlled squares (handled earlier by movement options)
        # F23: figure trying to stand is NOT an obstacle
        has_real_obstacle = square.is_obstacle_square()
        if not has_real_obstacle:
            # Check for obstacle figures that are truly obstacles (not F23 non-obstacles)
            for fig in square.figures_in_square():
                if fig is figure:
                    continue
                if (getattr(fig, 'status', None) in (FigureStatus.DEAD, FigureStatus.UNCONSCIOUS)
                        or (getattr(fig, 'status', None) == FigureStatus.INJURED
                            and not getattr(fig, 'needs_stand_up', False))):
                    has_real_obstacle = True
                    break
                # Fallen bike
                if (getattr(fig, 'is_biker', False)
                        and (getattr(fig, 'feet_down', False) or getattr(fig, 'cycle_damaged', False))):
                    has_real_obstacle = True
                    break
        if not has_real_obstacle:
            return messages

        # Catchers in same square protect teammates (T2 exception for unfielded ball)
        catchers_present = any(
            f.can_field_ball and f.is_on_field and f is not figure
            for f in square.figures_in_square()
            if getattr(f, 'team', None) == getattr(figure, 'team', None)
        )
        if catchers_present and getattr(figure, 'is_skater', False):
            return messages  # Protected

        result = dice.skill_check(getattr(figure, 'skill', 7))
        if not result.success:
            figure.fall()
            messages.append(
                f"{figure.name} fails obstacle check ({result.roll} vs {result.target}) — falls!")
            if figure.has_ball:
                messages.extend(self._drop_ball_from_carrier(figure))
        else:
            messages.append(f"{figure.name} clears obstacle ({result.roll} vs {result.target}).")
        return messages

    # -----------------------------------------------------------------------
    # F11-F13: Hand-off during movement / last-second / from prone
    # -----------------------------------------------------------------------

    def _check_handoff_opportunity(self, carrier: Any) -> List[str]:
        """Rule F11: Ball carrier may hand off to teammate in base-to-base contact.

        AI: hand off to best available skater in same square.
        """
        messages: List[str] = []
        if not carrier.has_ball:
            return messages
        carrier_sq = self.board.find_square_of_figure(carrier)
        if carrier_sq is None:
            return messages

        # F11: hand off to skater in same or adjacent square (base-to-base contact)
        best_target = None
        for team in self.teams:
            if getattr(team, 'side', None) != getattr(carrier, 'team', None):
                continue
            for fig in team.active_figures:
                if fig is carrier or not fig.is_on_field or fig.is_out_of_play:
                    continue
                if not getattr(fig, 'is_skater', False):
                    continue
                fig_sq = self.board.find_square_of_figure(fig)
                if fig_sq is None:
                    continue
                if self.board.are_in_base_to_base_contact(carrier_sq, fig_sq):
                    if best_target is None or fig.skill > best_target.skill:
                        best_target = fig

        if best_target is None:
            return messages

        # Only hand off if carrier is not a skater (catcher passes to skater)
        # or if carrier is fallen/prone (F13)
        carrier_is_catcher = getattr(carrier, 'is_catcher', False)
        carrier_is_fallen = getattr(carrier, 'is_fallen', False)
        if not carrier_is_catcher and not carrier_is_fallen:
            return messages  # Skater keeps ball unless manual hand-off in GUI

        # Check for opposing figures in same square (F28 hand-off modifier)
        opp_in_sq = len([
            f for f in carrier_sq.figures_in_square()
            if getattr(f, 'team', None) != getattr(carrier, 'team', None)
        ])
        modifier = -opp_in_sq  # -1 per opponent in square

        # F13: fallen carrier hand-off gives receiver -2 skill
        if carrier_is_fallen:
            modifier -= 2

        result = dice.skill_check(getattr(best_target, 'skill', 7), modifier)
        if result.success:
            carrier.has_ball = False
            best_target.has_ball = True
            self.ball.carrier = best_target
            messages.append(
                f"{carrier.name} hands off to {best_target.name} "
                f"({result.roll} vs {result.target}).")
        else:
            messages.append(
                f"{carrier.name} failed hand-off to {best_target.name} "
                f"({result.roll} vs {result.target}) — ball dropped!")
            messages.extend(self._drop_ball_from_carrier(carrier))
        return messages

    # -----------------------------------------------------------------------
    # A11: Goal-tending prohibition
    # -----------------------------------------------------------------------

    def _check_goal_tending(self) -> List[str]:
        """Rule A11: Defense may not goal-tend.

        If defenders set up a screen at an activated goal sector but no scoring
        attempt happened this lap, they must chase and complete another lap before
        screening again.  We enforce this by logging the violation and marking the
        figures (AI will move them away next turn).
        """
        messages: List[str] = []
        if not self.ball.is_activated:
            return messages

        offense_side = self.ball.activation_team
        if offense_side is None:
            return messages
        defense_side = self.opponent_side(offense_side)

        goal_sector = self.goal_sector_for_team(offense_side)

        # Count defenders stopped in the goal sector upper ring
        for sector in self.board.sectors:
            if sector.index != goal_sector:
                continue
            for square in sector.rings.get(Ring.UPPER, []):
                if not square.is_goal:
                    continue
                screening_defenders = [
                    f for f in square.figures_in_square()
                    if getattr(f, 'team', None) == defense_side
                    and getattr(f, 'is_standing', False)
                ]
                if not screening_defenders:
                    continue
                # Check if the carrier attempted a score this turn (has_scored_attempt)
                scorer_attempted = any(
                    f.has_scored_attempt or f.has_ball
                    for f in self.all_figures()
                    if getattr(f, 'team', None) == offense_side
                )
                if scorer_attempted:
                    break  # Shot was attempted — goal tending is legal

                # Screen with no shot attempted: mark for forced chase
                for df in screening_defenders:
                    lap = getattr(df, 'goal_screen_lap', None)
                    current_lap = self.ball.laps_since_activation
                    if lap == current_lap:
                        messages.append(
                            f"Goal-tending: {df.name} must chase and complete a lap before screening again.")
                    df.goal_screen_lap = current_lap  # mark this lap
        return messages

    # -----------------------------------------------------------------------
    # H3: Endurance tracking
    # -----------------------------------------------------------------------

    def _advance_endurance(self, figure: Any) -> None:
        """Rule H3: Track endurance depletion for active moving figures."""
        if not getattr(figure, 'is_on_field', False):
            return
        if getattr(figure, 'is_towed', False):
            return  # Towed skaters (on bike) don't deplete endurance
        endurance_used = getattr(figure, 'endurance_used', 0) + 1
        figure.endurance_used = endurance_used
        toughness = getattr(figure, 'base_toughness', 7)
        max_endurance = toughness + 3
        if endurance_used > max_endurance:
            # -1 per block exceeded
            blocks = endurance_used - max_endurance
            penalty = -blocks
            figure.speed_mod = min(0, getattr(figure, 'speed_mod', 0) + penalty)
            figure.skill_mod = min(0, getattr(figure, 'skill_mod', 0) + penalty)
            figure.combat_mod = min(0, getattr(figure, 'combat_mod', 0) + penalty)
            figure.toughness_mod = min(0, getattr(figure, 'toughness_mod', 0) + penalty)

    # -----------------------------------------------------------------------
    # Tow bar helpers (E9-E14)
    # -----------------------------------------------------------------------

    def _attach_tow_bar(self, biker: Any, skater: Any) -> List[str]:
        """Rule E9-E11: Attach skater to biker tow bar."""
        messages: List[str] = []
        if len(getattr(biker, 'towing', [])) >= 3:
            messages.append(f"{biker.name} already towing max 3 skaters.")
            return messages
        biker.towing.append(skater)
        skater.is_towed = True
        skater.tow_bar_holder = True
        skater.towed_by = biker
        messages.append(f"{skater.name} grabs tow bar of {biker.name}.")
        return messages

    def _detach_tow_bar(self, skater: Any) -> List[str]:
        """Rule E12-E14: Detach skater from tow bar."""
        messages: List[str] = []
        biker = getattr(skater, 'towed_by', None)
        if biker is not None and skater in getattr(biker, 'towing', []):
            biker.towing.remove(skater)
        skater.is_towed = False
        skater.tow_bar_holder = False
        skater.released_tow_bar_this_turn = True
        skater.towed_by = None
        messages.append(f"{skater.name} releases tow bar.")
        return messages

    # -----------------------------------------------------------------------
    # E15-E18: Crash triggers
    # -----------------------------------------------------------------------

    def _check_bike_crash(self, biker: Any, square: Square, modifier: int = 0) -> List[str]:
        """Rule E15: Biker makes skill roll; failure triggers cycle chart."""
        messages: List[str] = []
        result = dice.skill_check(getattr(biker, 'skill', 7), modifier)
        if result.success:
            return messages
        # Failed skill check → roll cycle chart (E15)
        chart = dice.roll_cycle_chart(modifier)
        messages.append(f"{biker.name} crashes! Cycle chart: {chart.details}")
        if chart.thrown:
            # E16: towed skaters make skill check
            for skater in list(getattr(biker, 'towing', [])):
                tow_mod = -2 if chart.result in ('thrown', 'bad_wreck') else -4
                tow_result = dice.skill_check(getattr(skater, 'skill', 7), tow_mod)
                if not tow_result.success:
                    skater.fall()
                    messages.append(f"{skater.name} loses footing after crash!")
                messages.extend(self._detach_tow_bar(skater))
            biker.fall()
            biker.feet_down = True
            messages.append(f"{biker.name} thrown from bike!")
            if chart.result in ('bad_wreck', 'major_wreck'):
                injury = dice.roll_injury_dice(fatality=(chart.result == 'major_wreck'))
                messages.extend(self._apply_injury_result(biker, injury))
                biker.cycle_damaged = True
            # E18: if no damage, biker can attempt to restart next turn
        elif chart.result in ('near_miss', 'skid'):
            # Skill check to stay upright
            stay_result = dice.skill_check(getattr(biker, 'skill', 7),
                                           -1 if chart.result == 'skid' else 0)
            if not stay_result.success:
                biker.fall()
                biker.feet_down = True
                messages.append(f"{biker.name} skids and falls!")
        return messages

    # -----------------------------------------------------------------------
    # E21: Damaged bike removal
    # -----------------------------------------------------------------------

    def _push_damaged_bike(self, biker: Any) -> int:
        """Rule E21: Return movement points for pushing damaged bike."""
        if getattr(biker, 'cycle_badly_damaged', False):
            return 2  # needs 2 figures, moves at 2 sq/turn
        if getattr(biker, 'cycle_damaged', False):
            return 3  # push at 3 sq/turn
        return 4  # on foot without bike: 4 sq/turn

    # -----------------------------------------------------------------------
    # E22-E26: Biker-specific combat rules
    # -----------------------------------------------------------------------

    def _check_biker_combat_legality(self, biker: Any) -> List[str]:
        """Rules E23-E26: Bikers cannot be legally attacked; penalties."""
        # E23: Any attack on biker draws penalty check (already in combat.py via G56)
        # E24: Biker scoring involvement prohibition
        # E25: Man-to-man auto cycle chart
        messages: List[str] = []
        if getattr(biker, 'status', None) == FigureStatus.MAN_TO_MAN:
            # E25: biker in man-to-man auto-rolls cycle chart at -1
            chart = dice.roll_cycle_chart(-1)
            messages.append(f"{biker.name} auto-rolls cycle chart (man-to-man): {chart.details}")
            if chart.thrown:
                biker.fall()
                biker.feet_down = True
                messages.append(f"{biker.name} thrown from bike in man-to-man!")
        return messages

    # -----------------------------------------------------------------------
    # F14-F15: Loose ball pickup during ball movement
    # -----------------------------------------------------------------------

    def _try_loose_ball_pickup(self, figure: Any, square: Square) -> List[str]:
        """Rule F14: Use action to attempt pickup as ball passes through square."""
        messages: List[str] = []
        if figure.has_acted or not figure.can_act:
            return messages
        if not figure.is_on_field or figure.is_out_of_play:
            return messages
        if getattr(figure, 'is_biker', False):
            return messages  # Bikers cannot pick up ball

        # Attempt pickup
        success, roll = self.ball.attempt_pickup(figure)
        figure.has_acted = True
        if success:
            messages.append(f"{figure.name} picks up loose ball (roll {roll})!")
        else:
            messages.append(f"{figure.name} fails to pick up ball (roll {roll}).")
        return messages

    # -----------------------------------------------------------------------
    # F26-F27: Carrying injured figures
    # -----------------------------------------------------------------------

    def _carry_figure(self, carrier: Any, injured: Any) -> List[str]:
        """Rule F26: One figure carries injured at half speed."""
        messages: List[str] = []
        injured.is_being_carried = True
        injured.carried_by = carrier
        carrier.is_carrying = injured
        # Speed halved (no downhill bonus)
        carrier.speed_mod = (getattr(carrier, 'speed_mod', 0) - carrier.base_speed // 2)
        messages.append(f"{carrier.name} carries {injured.name} (half speed).")
        return messages

    # -----------------------------------------------------------------------
    # F28-F33: Cannon track interactions
    # -----------------------------------------------------------------------

    def _check_cannon_track_ball_hit(self, figure: Any) -> List[str]:
        """Rules F31-F33: Ball hitting figure/cycle on cannon track."""
        messages: List[str] = []
        if self.ball.ring != Ring.CANNON:
            return messages

        biker = getattr(figure, 'is_biker', False)
        temp = self.ball.temperature

        if biker:
            # F32: Ball hitting cycle on cannon track
            r = dice.roll_d6()
            if temp.value >= 3 and r >= 3:  # Big Explosion on 3-6
                square = self.board.find_square_of_figure(figure)
                if square:
                    square.is_on_fire = True
                messages.append(f"{figure.name}'s bike explodes on cannon track! Big Explosion!")
            elif temp.value >= 2 and r >= 5:  # Very hot: explodes on 5-6
                messages.append(f"{figure.name}'s bike explodes on cannon track!")
        else:
            # F31: Ball hitting figure on cannon track
            from roozerball.engine.constants import BallTemp
            if temp == BallTemp.VERY_HOT:
                injury = dice.roll_injury_dice(fatality=True)
                messages.append(f"Ball hits {figure.name} on cannon track (fatal)!")
                messages.extend(self._apply_injury_result(figure, injury))
            elif temp == BallTemp.HOT:
                injury = dice.roll_injury_dice(fatality=False)
                messages.append(f"Ball hits {figure.name} on cannon track (hot)!")
                messages.extend(self._apply_injury_result(figure, injury))
            else:
                injury = dice.roll_injury_dice(fatality=True, bdd=True)
                messages.append(f"Ball hits {figure.name} on cannon track!")
                messages.extend(self._apply_injury_result(figure, injury))

        # F33: Figure/cycle knocked down to top slot of upper track
        upper_sq = self.board.get_square(figure.sector_index or 0, Ring.UPPER, 0)
        self.board.move_figure(figure, upper_sq)
        messages.append(f"{figure.name} knocked to upper track from cannon track hit.")
        return messages

    # -----------------------------------------------------------------------
    # G36: Goal sector push direction
    # -----------------------------------------------------------------------

    def _goal_push_direction(self, goal_sector: int) -> str:
        """Rule G36: 50% left, 50% right for pushes in goal sector."""
        return 'left' if dice.roll_d6() <= 3 else 'right'

    # -----------------------------------------------------------------------
    # H4: 2-minute time-compression mode
    # -----------------------------------------------------------------------

    @property
    def minutes_per_turn(self) -> int:
        """Rule H4: Default 1 min/turn; optional 2-min mode."""
        return getattr(self, '_minutes_per_turn', 1)

    def set_time_compression(self, enabled: bool) -> None:
        """Enable/disable H4 2-minute-per-turn mode."""
        self._minutes_per_turn = 2 if enabled else 1
