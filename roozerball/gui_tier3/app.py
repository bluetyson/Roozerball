"""Tier 3 Pygame application — main game loop and event dispatch.

Replaces the Tier 2 application with scene-graph-driven rendering,
advanced particle effects, and themed UI.

Tier 3 enhancements over Tier 2:
  * Scene-graph node architecture for structured rendering
  * Radial grid with per-tile incline gradient overlays
  * Ball heat glow with animated shimmer
  * Speed lines on fast-moving figures
  * Goal-flash celebration overlay
  * Advanced particle system (trails, exhaust, dust, confetti)
  * Themed UI with rounded panels and shadow dialogs
  * Motorcycle exhaust particles on biker movement
  * Dust cloud particles on figure falls/knockdowns
"""
from __future__ import annotations

import math
import os
import random as _rng
from typing import Any, Dict, List, Optional, Tuple

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from roozerball.engine.constants import FigureStatus, FigureType, Ring, TeamSide
from roozerball.engine.game import Game
from roozerball.engine.scoring import calculate_scoring_modifiers
from roozerball.engine.team import Team
from roozerball.gui_tier3.constants import (
    BG_COLOR,
    FPS,
    MODE_CVC,
    MODE_HVC,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
)
from roozerball.gui_tier3.renderer import BoardRenderer, _slot_center, _square_center
from roozerball.gui_tier3.ui import (
    CombatTargetDialog,
    ControlBar,
    EscalateDialog,
    GameOverDialog,
    MessageDialog,
    NewMatchDialog,
    PackFormationDialog,
    ScoringDialog,
    SidePanel,
    TeamGenDialog,
    TowBarDialog,
    clear_dice_log,
    log_dice,
)


class Tier3App:
    """Desktop UI for Roozerball with Tier 3 enhanced graphics."""

    def __init__(self, game: Optional[Game] = None) -> None:
        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)
        _flags = pygame.RESIZABLE
        if hasattr(pygame, "SCALED"):
            _flags |= pygame.SCALED  # auto-scales to fit any screen size (pygame 2+)
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), _flags)
        self.clock = pygame.time.Clock()
        self.running = True

        self.game = game or Game()
        self.game_mode: str = MODE_CVC
        self.selected_figure: Optional[Any] = None

        # Components
        self.renderer = BoardRenderer()
        self.panel = SidePanel()
        self.control_bar = ControlBar()
        self._active_dialog: Optional[Any] = None

        # Human-interactive state
        self._interaction_mode: Optional[str] = None
        self._tow_selected_biker: Optional[Any] = None
        self._pending_movement_result: Optional[List] = None

        # Track previous figure positions for exhaust/dust effects
        self._prev_figure_positions: Dict[int, Tuple[int, int]] = {}

        clear_dice_log()

        self.control_bar.build({
            "New Match": self.new_match_dialog,
            "Next Phase": self.next_phase,
            "Play Turn": self.play_turn,
            "Gen Teams": self.open_team_gen,
            "Grab Tow": self._start_tow_attach,
            "Release Tow": self._start_tow_detach,
        })

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def mainloop(self) -> None:
        while self.running:
            dt_ms = self.clock.tick(FPS)
            self._handle_events()
            self._update(dt_ms)
            self._draw()
            pygame.display.flip()
        pygame.quit()

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if self._active_dialog is not None:
                self._active_dialog.handle_event(event)
                if self._active_dialog.done:
                    self._on_dialog_closed(self._active_dialog)
                    self._active_dialog = None
                continue

            if event.type == pygame.MOUSEMOTION:
                self.control_bar.handle_motion(event.pos)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self._on_left_click(event.pos)
                elif event.button in (2, 3):
                    self._on_pan_start(event.pos)
                elif event.button == 4:
                    self.renderer.camera.zoom_in()
                elif event.button == 5:
                    self.renderer.camera.zoom_out()

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button in (2, 3):
                    self._on_pan_end()

            elif event.type == pygame.MOUSEMOTION:
                if pygame.mouse.get_pressed()[1] or pygame.mouse.get_pressed()[2]:
                    self._on_pan_motion(event.rel)

            elif event.type == pygame.MOUSEWHEEL:
                if event.y > 0:
                    self.renderer.camera.zoom_in()
                elif event.y < 0:
                    self.renderer.camera.zoom_out()

            elif event.type == pygame.KEYDOWN:
                self._on_key(event)

    def _on_left_click(self, pos: Tuple[int, int]) -> None:
        if pos[1] < 52:
            self.control_bar.handle_click(pos)
            return

        if self._pending_movement_result is not None:
            sq = self.renderer.move_option_at(pos[0], pos[1])
            if sq is not None:
                self._pending_movement_result[0] = sq
                self._pending_movement_result.append("done")
                return

        if self._interaction_mode in ("tow_attach", "tow_detach"):
            fig = self.renderer.figure_at(pos[0], pos[1])
            if fig is not None:
                self._handle_tow_click(fig)
            else:
                self._interaction_mode = None
                self._tow_selected_biker = None
                self.control_bar.set_interaction("")
            return

        fig = self.renderer.figure_at(pos[0], pos[1])
        if fig is not None:
            self.selected_figure = fig
        else:
            self.selected_figure = None

    def _on_key(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_ESCAPE:
            if self._pending_movement_result is not None:
                self._pending_movement_result[0] = None
                self._pending_movement_result.append("done")
            elif self._interaction_mode:
                self._interaction_mode = None
                self._tow_selected_biker = None
                self.control_bar.set_interaction("")
        elif event.key == pygame.K_n:
            self.next_phase()
        elif event.key == pygame.K_p:
            self.play_turn()
        elif event.key == pygame.K_f:
            if self.game.ball.carrier is not None:
                self.renderer.camera.follow(self.game.ball.carrier)
        elif event.key == pygame.K_r:
            self.renderer.camera.reset()
        elif event.key == pygame.K_i:
            # Toggle isometric view (Tier 3)
            self.renderer.isometric = not self.renderer.isometric

    def _on_pan_start(self, pos: Tuple[int, int]) -> None:
        pass

    def _on_pan_motion(self, rel: Tuple[int, int]) -> None:
        self.renderer.camera.pan(rel[0], rel[1])

    def _on_pan_end(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def _update(self, dt_ms: float) -> None:
        self.renderer.update(dt_ms, self.game)
        self.control_bar.update_state(self.game, self.game_mode)
        self._emit_movement_particles()

    def _emit_movement_particles(self) -> None:
        """Emit exhaust for moving bikers, dust for fallen figures."""
        for fig in self.game.all_figures():
            sq = self.game.board.find_square_of_figure(fig)
            if sq is None:
                continue
            fid = id(fig)
            wx, wy = _slot_center(sq, fig.slot_index or 0)
            prev = self._prev_figure_positions.get(fid)
            self._prev_figure_positions[fid] = (int(wx), int(wy))

            if prev is None:
                continue

            # Biker exhaust
            if (
                fig.has_moved
                and getattr(fig, "is_biker", False)
                and fig.speed >= 4
            ):
                if (int(wx), int(wy)) != prev:
                    angle = math.atan2(wy - prev[1], wx - prev[0])
                    self.renderer.emit_exhaust_particles(wx, wy, angle)

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def _draw(self) -> None:
        self.screen.fill(BG_COLOR)

        move_opts = None
        if self.selected_figure is not None:
            move_opts = self.game.movement_options_with_costs(self.selected_figure)
        self.renderer.draw(
            self.screen, self.game, self.selected_figure, move_opts,
        )

        self.panel.draw(
            self.screen, self.game, self.selected_figure, self.game_mode,
        )
        self.control_bar.draw(self.screen)

        if self._active_dialog is not None:
            self._active_dialog.draw(self.screen)

    # ------------------------------------------------------------------
    # Dialog management
    # ------------------------------------------------------------------

    def _show_dialog(self, dialog: Any) -> None:
        self._active_dialog = dialog

    def _run_modal_dialog(self, dialog: Any) -> None:
        self._active_dialog = dialog
        while not dialog.done and self.running:
            dt_ms = self.clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    dialog.done = True
                    return
                dialog.handle_event(event)
            self._update(dt_ms)
            self._draw()
            pygame.display.flip()
        self._active_dialog = None

    def _on_dialog_closed(self, dialog: Any) -> None:
        pass

    # ------------------------------------------------------------------
    # Game actions
    # ------------------------------------------------------------------

    def new_match_dialog(self) -> None:
        dlg = NewMatchDialog()
        self._run_modal_dialog(dlg)
        if dlg.result_mode is None:
            return
        self.game_mode = dlg.result_mode
        home_name = dlg.result_home_name
        vis_name = dlg.result_visitor_name
        self.game = Game(home_name=home_name, visitor_name=vis_name)

        gen_home, gen_vis = dlg.wants_team_gen
        if gen_home:
            tdlg = TeamGenDialog(TeamSide.HOME, home_name)
            self._run_modal_dialog(tdlg)
            if tdlg.result_team is not None:
                self.game.home_team.roster = tdlg.result_team.roster
                for f in self.game.home_team.roster:
                    f.team = TeamSide.HOME
                self.game.home_team.select_starting_lineup()
        if gen_vis:
            tdlg = TeamGenDialog(TeamSide.VISITOR, vis_name)
            self._run_modal_dialog(tdlg)
            if tdlg.result_team is not None:
                self.game.visitor_team.roster = tdlg.result_team.roster
                for f in self.game.visitor_team.roster:
                    f.team = TeamSide.VISITOR
                self.game.visitor_team.select_starting_lineup()

        self.game.setup_match()
        self.selected_figure = None
        self._prev_figure_positions.clear()
        clear_dice_log()
        self.renderer.camera.reset()
        self._install_callbacks()

    def new_match(self) -> None:
        self.game = Game()
        self.selected_figure = None
        self._prev_figure_positions.clear()
        clear_dice_log()
        self.renderer.camera.reset()

    def open_team_gen(self) -> None:
        dlg = TeamGenDialog(TeamSide.HOME, self.game.home_team.name)
        self._run_modal_dialog(dlg)
        if dlg.result_team is not None:
            self.game.home_team.roster = dlg.result_team.roster
            for f in self.game.home_team.roster:
                f.team = TeamSide.HOME
            self.game.home_team.select_starting_lineup()
            self.game.setup_match()
            self.selected_figure = None

    # ------------------------------------------------------------------
    # Phase controls
    # ------------------------------------------------------------------

    def next_phase(self) -> None:
        if self.game.game_over:
            self._show_game_over_if_needed()
            return
        old_scores = dict(self.game.snapshot()["scores"])
        result = self.game.advance_phase()
        self._trigger_phase_effects(result, old_scores)
        self._check_game_over()

    def play_turn(self) -> None:
        if self.game.game_over:
            self._show_game_over_if_needed()
            return
        old_scores = dict(self.game.snapshot()["scores"])
        results = self.game.play_turn()
        for result in results:
            self._trigger_phase_effects(result, old_scores)
        self._check_game_over()

    def _trigger_phase_effects(
        self, result: Any, old_scores: Dict[str, int],
    ) -> None:
        if result is None:
            return
        for msg in result.messages:
            lower = msg.lower()
            if "cannon" in lower and "fire" in lower:
                self.renderer.emit_cannon_particles()
            if "crashes" in lower or "thrown" in lower or "falls" in lower:
                for fig in self.game.all_figures():
                    if fig.name in msg:
                        sq = self.game.board.find_square_of_figure(fig)
                        if sq is not None:
                            x, y = _square_center(sq)
                            self.renderer.emit_crash_particles(x, y)
                            # Tier 3: also emit dust
                            self.renderer.emit_dust_particles(x, y)
                        break
        new_scores = self.game.snapshot()["scores"]
        for name in new_scores:
            if new_scores.get(name, 0) > old_scores.get(name, 0):
                self.renderer.emit_goal_particles()
                break

    def _check_game_over(self) -> None:
        if self.game.game_over:
            self._show_game_over_if_needed()

    def _show_game_over_if_needed(self) -> None:
        result = self.game.match_result()
        scores = self.game.snapshot()["scores"]
        dlg = GameOverDialog(result, scores)
        self._run_modal_dialog(dlg)

    # ------------------------------------------------------------------
    # Human-interactive callbacks
    # ------------------------------------------------------------------

    def _install_callbacks(self) -> None:
        if self.game_mode == MODE_HVC:
            self.game.human_movement_callback = self._human_movement_cb
            self.game.human_combat_target_callback = self._human_combat_target_cb
            self.game.human_escalate_callback = self._human_escalate_cb
            self.game.human_tow_bar_callback = self._human_tow_bar_cb
            self.game.human_scoring_callback = self._human_scoring_cb
            self.game.human_pack_callback = self._human_pack_cb
        else:
            self.game.human_movement_callback = None
            self.game.human_combat_target_callback = None
            self.game.human_escalate_callback = None
            self.game.human_tow_bar_callback = None
            self.game.human_scoring_callback = None
            self.game.human_pack_callback = None

    def _human_movement_cb(
        self,
        figure: Any,
        current_square: Any,
        options: List[tuple],
    ) -> Optional[Any]:
        if not options:
            return None
        result_holder: List[Optional[Any]] = [None]
        self._pending_movement_result = result_holder
        self.control_bar.set_interaction(
            f"Click a destination for {figure.name} (SPD {figure.speed}) "
            f"or press Esc to skip"
        )

        while len(result_holder) <= 1 and self.running:
            dt_ms = self.clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    result_holder.append("done")
                    break
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    sq = self.renderer.move_option_at(event.pos[0], event.pos[1])
                    if sq is not None:
                        result_holder[0] = sq
                        result_holder.append("done")
                        break
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    result_holder[0] = None
                    result_holder.append("done")
                    break
                if event.type == pygame.MOUSEWHEEL:
                    if event.y > 0:
                        self.renderer.camera.zoom_in()
                    elif event.y < 0:
                        self.renderer.camera.zoom_out()

            self.renderer.update(dt_ms, self.game)
            self.screen.fill(BG_COLOR)
            self.renderer.draw(self.screen, self.game, figure, options)
            self.panel.draw(
                self.screen, self.game, figure, self.game_mode,
            )
            self.control_bar.draw(self.screen)
            pygame.display.flip()

        self._pending_movement_result = None
        self.control_bar.set_interaction("")
        return result_holder[0]

    def _human_combat_target_cb(
        self, attacker: Any, opponents: List[Any],
    ) -> Optional[Any]:
        if not opponents:
            return None
        dlg = CombatTargetDialog(attacker, opponents)
        self._run_modal_dialog(dlg)
        return dlg.result

    def _human_escalate_cb(self, figure: Any, opponent: Any) -> bool:
        dlg = EscalateDialog(figure, opponent)
        self._run_modal_dialog(dlg)
        return dlg.result

    def _human_tow_bar_cb(
        self, biker: Any, candidates: List[Any],
    ) -> Optional[List[Any]]:
        if not candidates:
            return []
        dlg = TowBarDialog(biker, candidates)
        self._run_modal_dialog(dlg)
        return dlg.result

    def _human_scoring_cb(
        self,
        shooter: Any,
        modifiers: List[Tuple[str, int]],
    ) -> bool:
        dlg = ScoringDialog(shooter, modifiers)
        self._run_modal_dialog(dlg)
        return dlg.result

    def _human_pack_cb(
        self, packs: List[List[Any]],
    ) -> Optional[List[int]]:
        if not packs:
            return []
        dlg = PackFormationDialog(packs)
        self._run_modal_dialog(dlg)
        return dlg.result

    # ------------------------------------------------------------------
    # Tow bar interaction
    # ------------------------------------------------------------------

    def _start_tow_attach(self) -> None:
        if self.game_mode != MODE_HVC:
            dlg = MessageDialog(
                "Tow Bar",
                "Tow controls only in Human vs Computer mode.",
            )
            self._run_modal_dialog(dlg)
            return
        self._interaction_mode = "tow_attach"
        self.control_bar.set_interaction(
            "Click a HOME biker to attach a tow bar..."
        )

    def _start_tow_detach(self) -> None:
        if self.game_mode != MODE_HVC:
            dlg = MessageDialog(
                "Tow Bar",
                "Tow controls only in Human vs Computer mode.",
            )
            self._run_modal_dialog(dlg)
            return
        self._interaction_mode = "tow_detach"
        self.control_bar.set_interaction(
            "Click a towed HOME skater to release tow bar..."
        )

    def _handle_tow_click(self, figure: Any) -> None:
        if self._interaction_mode == "tow_attach":
            if self._tow_selected_biker is None:
                if not getattr(figure, "is_biker", False):
                    self.control_bar.set_interaction(
                        "Please click a BIKER first."
                    )
                    return
                if getattr(figure, "team", None) != TeamSide.HOME:
                    self.control_bar.set_interaction(
                        "Please click a HOME biker."
                    )
                    return
                self._tow_selected_biker = figure
                self.control_bar.set_interaction(
                    f"Now click a skater for {figure.name}'s tow bar..."
                )
            else:
                if not getattr(figure, "is_skater", False):
                    self.control_bar.set_interaction(
                        "Please click a SKATER."
                    )
                    return
                if getattr(figure, "team", None) != TeamSide.HOME:
                    self.control_bar.set_interaction(
                        "Please click a HOME skater."
                    )
                    return
                msgs = self.game.attach_tow_bar(
                    self._tow_selected_biker, figure,
                )
                for m in msgs:
                    self.game.log.append(m)
                self._tow_selected_biker = None
                self._interaction_mode = None
                self.control_bar.set_interaction("")

        elif self._interaction_mode == "tow_detach":
            if not getattr(figure, "is_towed", False):
                self.control_bar.set_interaction(
                    "That figure is not being towed."
                )
                return
            if getattr(figure, "team", None) != TeamSide.HOME:
                self.control_bar.set_interaction(
                    "Please click a HOME figure."
                )
                return
            msgs = self.game.detach_tow_bar(figure)
            for m in msgs:
                self.game.log.append(m)
            self._interaction_mode = None
            self.control_bar.set_interaction("")


def launch() -> None:
    """Entry point for ``python -m roozerball.gui_tier3``."""
    app = Tier3App()
    app.mainloop()


if __name__ == "__main__":
    launch()
