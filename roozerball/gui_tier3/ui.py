"""Tier 3 UI — themed panels, rounded controls, animated transitions.

Enhancements over Tier 2:
  * Rounded rectangle panels with subtle glow borders
  * Themed buttons with active/hover/pressed states
  * Animated dice-roll popups
  * Improved dialog styling with shadow and corner radius
  * Better text layout with section headers
"""
from __future__ import annotations

import random as _rng
from typing import Any, Callable, Dict, List, Optional, Tuple

import pygame

from roozerball.engine.constants import FigureStatus, TeamSide
from roozerball.engine.team import Team
from roozerball.gui_tier3.constants import (
    BUTTON_ACTIVE,
    BUTTON_BORDER,
    BUTTON_COLOR,
    BUTTON_CORNER_RADIUS,
    BUTTON_HEIGHT,
    BUTTON_HOVER,
    BUTTON_PADDING,
    BUTTON_TEXT,
    DIALOG_BG,
    DIALOG_BORDER,
    DIALOG_CORNER_RADIUS,
    DIALOG_OVERLAY_ALPHA,
    FONT_SIZE_BODY,
    FONT_SIZE_HEADER,
    FONT_SIZE_LABEL,
    FONT_SIZE_SMALL,
    FONT_SIZE_TITLE,
    MAX_ACTION_TEXT_LENGTH,
    MAX_COMBAT_LINES,
    MAX_DICE_LOG,
    MAX_LOG_DISPLAY,
    MAX_LOG_ENTRY_LENGTH,
    MODE_CVC,
    MODE_HVC,
    PANEL_BG,
    PANEL_BG_LIGHT,
    PANEL_BORDER,
    PANEL_BORDER_GLOW,
    PANEL_CORNER_RADIUS,
    PANEL_PADDING,
    PANEL_SECTION_GAP,
    PANEL_WIDTH,
    PANEL_X,
    TEXT_ACCENT,
    TEXT_DANGER,
    TEXT_HIGHLIGHT,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_SUCCESS,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)

COMBAT_KEYWORDS = ("Brawl:", "Assault:", "Swoop:")

# ---------------------------------------------------------------------------
# Dice log (module-level)
# ---------------------------------------------------------------------------
_dice_log: List[str] = []


def log_dice(label: str, result: Any) -> None:
    _dice_log.append(f"{label}: {result}")
    if len(_dice_log) > MAX_DICE_LOG:
        _dice_log.pop(0)


def clear_dice_log() -> None:
    _dice_log.clear()


# ---------------------------------------------------------------------------
# Font helpers
# ---------------------------------------------------------------------------
_font_cache: Dict[Tuple[str, int, bool], pygame.font.Font] = {}


def _font(size: int, bold: bool = False) -> pygame.font.Font:
    key = ("arial", size, bold)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.SysFont(
            "arial,helvetica,sans-serif", size, bold=bold,
        )
    return _font_cache[key]


def _mono(size: int) -> pygame.font.Font:
    key = ("mono", size, False)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.SysFont(
            "couriernew,courier,monospace", size,
        )
    return _font_cache[key]


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------


def _draw_rounded_rect(
    surface: pygame.Surface,
    color: Tuple[int, ...],
    rect: pygame.Rect,
    radius: int = 6,
    border: int = 0,
) -> None:
    """Draw a rounded rectangle. Supports fill and outline."""
    if len(color) == 4:
        # RGBA — draw on an alpha surface
        tmp = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(tmp, color, (0, 0, rect.width, rect.height), border, radius)
        surface.blit(tmp, rect.topleft)
    else:
        pygame.draw.rect(surface, color, rect, border, radius)


# ---------------------------------------------------------------------------
# Button
# ---------------------------------------------------------------------------


class Button:
    """Themed clickable button with rounded corners."""

    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        callback: Optional[Callable[[], None]] = None,
    ) -> None:
        self.rect = rect
        self.text = text
        self.callback = callback
        self.hovered = False
        self.pressed = False
        self.visible = True

    def draw(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return
        if self.pressed:
            color = BUTTON_ACTIVE
        elif self.hovered:
            color = BUTTON_HOVER
        else:
            color = BUTTON_COLOR
        _draw_rounded_rect(surface, color, self.rect, BUTTON_CORNER_RADIUS)
        _draw_rounded_rect(
            surface, BUTTON_BORDER, self.rect, BUTTON_CORNER_RADIUS, 1,
        )
        font = _font(FONT_SIZE_BODY)
        txt = font.render(self.text, True, BUTTON_TEXT)
        surface.blit(
            txt,
            (self.rect.centerx - txt.get_width() // 2,
             self.rect.centery - txt.get_height() // 2),
        )

    def handle_motion(self, pos: Tuple[int, int]) -> None:
        self.hovered = self.rect.collidepoint(pos)
        if not self.hovered:
            self.pressed = False

    def handle_click(self, pos: Tuple[int, int]) -> bool:
        if self.visible and self.rect.collidepoint(pos):
            self.pressed = True
            if self.callback:
                self.callback()
            return True
        return False

    def handle_release(self) -> None:
        self.pressed = False


# ---------------------------------------------------------------------------
# Text input box
# ---------------------------------------------------------------------------


class TextInput:
    """Minimal text input field with rounded border."""

    def __init__(
        self,
        rect: pygame.Rect,
        text: str = "",
        placeholder: str = "",
    ) -> None:
        self.rect = rect
        self.text = text
        self.placeholder = placeholder
        self.active = False

    def draw(self, surface: pygame.Surface) -> None:
        bg = (50, 60, 80) if self.active else PANEL_BG
        _draw_rounded_rect(surface, bg, self.rect, 4)
        border_color = TEXT_HIGHLIGHT if self.active else PANEL_BORDER
        _draw_rounded_rect(surface, border_color, self.rect, 4, 1)
        font = _font(FONT_SIZE_BODY)
        display = self.text if self.text else self.placeholder
        color = TEXT_PRIMARY if self.text else TEXT_SECONDARY
        txt = font.render(display, True, color)
        surface.blit(
            txt, (self.rect.x + 6, self.rect.centery - txt.get_height() // 2),
        )

    def handle_click(self, pos: Tuple[int, int]) -> bool:
        self.active = self.rect.collidepoint(pos)
        return self.active

    def handle_key(self, event: pygame.event.Event) -> None:
        if not self.active:
            return
        if event.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
        elif event.key == pygame.K_RETURN:
            self.active = False
        elif event.unicode and event.unicode.isprintable():
            self.text += event.unicode


# ---------------------------------------------------------------------------
# Side panels
# ---------------------------------------------------------------------------


class SidePanel:
    """Renders the right-side info panels with rounded themed sections."""

    def __init__(self) -> None:
        self._scroll_offset: int = 0
        self._log_scroll: int = 0

    def draw(
        self,
        surface: pygame.Surface,
        game: Any,
        selected_figure: Optional[Any],
        game_mode: str,
    ) -> None:
        x = PANEL_X
        y = 8
        w = PANEL_WIDTH

        # Panel background
        panel_rect = pygame.Rect(x, 0, w + 10, WINDOW_HEIGHT)
        _draw_rounded_rect(surface, PANEL_BG, panel_rect, 0)

        y = self._draw_scoreboard(surface, x, y, w, game)
        y = self._draw_phase(surface, x, y, w, game)
        y = self._draw_selected(surface, x, y, w, game, selected_figure)
        y = self._draw_penalty_box(surface, x, y, w, game)
        y = self._draw_combat(surface, x, y, w, game)
        y = self._draw_dice_log(surface, x, y, w)
        self._draw_replay_log(surface, x, y, w, game)

    def _draw_section(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        w: int,
        title: str,
        lines: List[str],
        max_height: int = 200,
        title_color: Tuple[int, int, int] = TEXT_ACCENT,
    ) -> int:
        font_title = _font(FONT_SIZE_LABEL, bold=True)
        font_body = _mono(FONT_SIZE_SMALL)
        line_h = font_body.get_linesize()

        # Title
        title_surf = font_title.render(title, True, title_color)
        surface.blit(title_surf, (x + PANEL_PADDING, y))
        y += title_surf.get_height() + 2

        # Box
        content_h = min(max_height, max(line_h, len(lines) * line_h + 6))
        box_rect = pygame.Rect(
            x + PANEL_PADDING, y, w - PANEL_PADDING * 2, content_h,
        )
        _draw_rounded_rect(
            surface, (14, 20, 35), box_rect, PANEL_CORNER_RADIUS,
        )
        _draw_rounded_rect(
            surface, PANEL_BORDER, box_rect, PANEL_CORNER_RADIUS, 1,
        )

        # Content (clip to box)
        clip = surface.subsurface(box_rect)
        cy = 3
        for line in lines:
            if cy + line_h > content_h:
                break
            txt = font_body.render(line, True, TEXT_PRIMARY)
            clip.blit(txt, (6, cy))
            cy += line_h

        return y + content_h + PANEL_SECTION_GAP

    def _draw_scoreboard(
        self, surface: pygame.Surface, x: int, y: int, w: int, game: Any,
    ) -> int:
        snapshot = game.snapshot()
        scores = snapshot["scores"]
        score_text = " | ".join(f"{n}: {s}" for n, s in scores.items())
        lines = [
            f"Period {snapshot['period']} \u00b7 Time {snapshot['time_remaining']}:00 \u00b7 Turn {snapshot['turn']}",
            score_text,
        ]
        return self._draw_section(surface, x, y, w, "Scoreboard", lines, 42)

    def _draw_phase(
        self, surface: pygame.Surface, x: int, y: int, w: int, game: Any,
    ) -> int:
        snapshot = game.snapshot()
        phase = snapshot["phase"].replace("_", " ").title()
        sector = snapshot["initiative_sector"]
        sector_name = "\u2014"
        if sector is not None:
            sector_name = f"Sector {game.board.get_sector(sector).name}"
        ball = snapshot["ball"]
        lines = [
            f"Phase: {phase}",
            f"Initiative: {sector_name}",
            f"Ball: {ball['state']} \u00b7 {ball['temperature']} \u00b7 speed {ball['speed']}",
        ]
        return self._draw_section(surface, x, y, w, "Phase / Ball", lines, 56)

    def _draw_selected(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        w: int,
        game: Any,
        selected: Optional[Any],
    ) -> int:
        if selected is None:
            return self._draw_section(
                surface, x, y, w, "Selected Figure",
                ["No figure selected"], 22,
            )
        sq = game.board.find_square_of_figure(selected)
        location = "off track"
        if sq is not None:
            location = (
                f"{game.board.get_sector(sq.sector_index).name} / "
                f"{sq.ring.name.lower()} / {sq.position + 1}"
            )
        lines = [
            selected.name,
            f"Type: {selected.figure_type.value}",
            f"SPD {selected.speed}  SKL {selected.skill}  COM {selected.combat}  TGH {selected.toughness}",
            f"Status: {selected.status.value}",
            f"Location: {location}",
        ]
        if getattr(selected, "is_towed", False):
            lines.append(
                f"Towed by: {getattr(selected.towed_by, 'name', '?')}",
            )
        elif getattr(selected, "towing", []):
            names = ", ".join(
                getattr(f, "name", "?") for f in selected.towing
            )
            lines.append(f"Towing: {names}")
        endurance_used = getattr(selected, "endurance_used", 0)
        if endurance_used:
            max_e = getattr(selected, "base_toughness", 7) + 3
            lines.append(f"Endurance: {endurance_used}/{max_e}")
        return self._draw_section(
            surface, x, y, w, "Selected Figure", lines, 115,
        )

    def _draw_penalty_box(
        self, surface: pygame.Surface, x: int, y: int, w: int, game: Any,
    ) -> int:
        lines: List[str] = []
        for team in game.teams:
            entries = []
            for fig in team.active_figures:
                if fig.is_ready_to_return():
                    continue
                if (
                    fig.penalty_time <= 0
                    and fig.shaken_time <= 0
                    and fig.rest_time <= 0
                ):
                    continue
                timer = max(fig.penalty_time, fig.shaken_time, fig.rest_time)
                entries.append(f"{fig.name} ({timer}:00)")
            if entries:
                lines.append(f"{team.name}: " + ", ".join(entries))
        if not lines:
            lines = ["No figures in the box"]
        return self._draw_section(
            surface, x, y, w, "Penalty / Recovery", lines, 52,
        )

    def _draw_combat(
        self, surface: pygame.Surface, x: int, y: int, w: int, game: Any,
    ) -> int:
        text = "No combat resolved yet"
        result = game.last_phase_result
        if result is not None and result.phase.value == "combat":
            combat_lines = [line for line in result.messages if line]
            if combat_lines:
                text = "\n".join(combat_lines[-MAX_COMBAT_LINES:])
        else:
            recent = [
                e
                for e in reversed(game.log)
                if any(k in e for k in COMBAT_KEYWORDS)
            ]
            if recent:
                text = recent[0]
        lines = text.split("\n")
        return self._draw_section(
            surface, x, y, w, "Combat Resolution", lines, 56,
        )

    def _draw_dice_log(
        self, surface: pygame.Surface, x: int, y: int, w: int,
    ) -> int:
        lines = _dice_log[-12:] if _dice_log else ["(no rolls yet)"]
        return self._draw_section(
            surface, x, y, w, "Dice Rolls", lines, 85,
        )

    def _draw_replay_log(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        w: int,
        game: Any,
    ) -> None:
        font_title = _font(FONT_SIZE_LABEL, bold=True)
        font_body = _mono(FONT_SIZE_SMALL)
        line_h = font_body.get_linesize()

        title_surf = font_title.render("Replay Log", True, TEXT_ACCENT)
        surface.blit(title_surf, (x + PANEL_PADDING, y))
        y += title_surf.get_height() + 2

        remaining = WINDOW_HEIGHT - y - 8
        box_rect = pygame.Rect(
            x + PANEL_PADDING, y, w - PANEL_PADDING * 2, remaining,
        )
        _draw_rounded_rect(
            surface, (14, 20, 35), box_rect, PANEL_CORNER_RADIUS,
        )
        _draw_rounded_rect(
            surface, PANEL_BORDER, box_rect, PANEL_CORNER_RADIUS, 1,
        )

        entries = game.log[-MAX_LOG_DISPLAY:]
        clip = surface.subsurface(box_rect)
        cy = 3
        for entry in entries:
            if cy + line_h > remaining:
                break
            txt = font_body.render(entry[:MAX_LOG_ENTRY_LENGTH], True, TEXT_PRIMARY)
            clip.blit(txt, (6, cy))
            cy += line_h


# ---------------------------------------------------------------------------
# Control bar (top)
# ---------------------------------------------------------------------------


class ControlBar:
    """Top control bar with themed buttons and status labels."""

    def __init__(self) -> None:
        self.buttons: List[Button] = []
        self._mode_text = MODE_CVC
        self._interaction_text = ""
        self._score_text = ""
        self._last_action_text = ""

    def build(self, callbacks: Dict[str, Callable]) -> None:
        bx = 8
        bw = 100
        bh = BUTTON_HEIGHT
        by = 8
        self.buttons.clear()
        for name in [
            "New Match",
            "Next Phase",
            "Play Turn",
            "Gen Teams",
            "Grab Tow",
            "Release Tow",
        ]:
            cb = callbacks.get(name)
            self.buttons.append(Button(pygame.Rect(bx, by, bw, bh), name, cb))
            bx += bw + 6

    def draw(self, surface: pygame.Surface) -> None:
        # Background bar with slight gradient feel
        bar_rect = pygame.Rect(0, 0, WINDOW_WIDTH, 50)
        _draw_rounded_rect(surface, (22, 30, 46), bar_rect, 0)
        pygame.draw.line(
            surface, PANEL_BORDER, (0, 50), (WINDOW_WIDTH, 50),
        )

        for btn in self.buttons:
            btn.draw(surface)

        # Mode label
        font = _font(FONT_SIZE_SMALL)
        mode_surf = font.render(f"Mode: {self._mode_text}", True, TEXT_SECONDARY)
        surface.blit(mode_surf, (660, 12))

        # Interaction label
        if self._interaction_text:
            int_surf = font.render(self._interaction_text, True, (250, 170, 20))
            surface.blit(int_surf, (660, 30))

        # Score summary
        if self._score_text:
            score_font = _font(FONT_SIZE_BODY, bold=True)
            sc_surf = score_font.render(self._score_text, True, TEXT_PRIMARY)
            surface.blit(sc_surf, (WINDOW_WIDTH - sc_surf.get_width() - 16, 8))

        if self._last_action_text:
            act_font = _font(FONT_SIZE_SMALL)
            display = self._last_action_text[:MAX_ACTION_TEXT_LENGTH]
            act_surf = act_font.render(display, True, TEXT_SECONDARY)
            surface.blit(
                act_surf,
                (WINDOW_WIDTH - act_surf.get_width() - 16, 28),
            )

    def update_state(self, game: Any, mode: str) -> None:
        self._mode_text = mode
        snapshot = game.snapshot()
        scores = snapshot["scores"]
        self._score_text = " | ".join(f"{n}: {s}" for n, s in scores.items())
        result = game.last_phase_result
        if result is not None and result.messages:
            phase_name = result.phase.value.replace("_", " ").title()
            self._last_action_text = f"[{phase_name}] {result.messages[-1]}"
        else:
            self._last_action_text = ""

    def set_interaction(self, text: str) -> None:
        self._interaction_text = text

    def handle_motion(self, pos: Tuple[int, int]) -> None:
        for btn in self.buttons:
            btn.handle_motion(pos)

    def handle_click(self, pos: Tuple[int, int]) -> bool:
        for btn in self.buttons:
            if btn.handle_click(pos):
                return True
        return False


# ---------------------------------------------------------------------------
# Dialog overlays (Tier 3 — rounded, shadowed)
# ---------------------------------------------------------------------------


class DialogBase:
    """Base for modal dialog overlays with rounded corners and shadow."""

    def __init__(self, width: int = 500, height: int = 400) -> None:
        self.width = width
        self.height = height
        self.x = (WINDOW_WIDTH - width) // 2
        self.y = (WINDOW_HEIGHT - height) // 2
        self.result: Any = None
        self.done = False
        self._buttons: List[Button] = []
        self._text_inputs: List[TextInput] = []

    def draw(self, surface: pygame.Surface) -> None:
        # Darken overlay
        overlay = pygame.Surface(
            (WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA,
        )
        overlay.fill((0, 0, 0, DIALOG_OVERLAY_ALPHA))
        surface.blit(overlay, (0, 0))

        # Shadow
        shadow_rect = pygame.Rect(
            self.x + 4, self.y + 4, self.width, self.height,
        )
        _draw_rounded_rect(
            surface, (0, 0, 0, 80), shadow_rect, DIALOG_CORNER_RADIUS,
        )

        # Dialog box
        rect = pygame.Rect(self.x, self.y, self.width, self.height)
        _draw_rounded_rect(
            surface, DIALOG_BG, rect, DIALOG_CORNER_RADIUS,
        )
        _draw_rounded_rect(
            surface, DIALOG_BORDER, rect, DIALOG_CORNER_RADIUS, 2,
        )

        self._draw_content(surface)
        for btn in self._buttons:
            btn.draw(surface)
        for ti in self._text_inputs:
            ti.draw(surface)

    def _draw_content(self, surface: pygame.Surface) -> None:
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            for btn in self._buttons:
                btn.handle_motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for ti in self._text_inputs:
                ti.handle_click(event.pos)
            for btn in self._buttons:
                if btn.handle_click(event.pos):
                    return
        elif event.type == pygame.MOUSEBUTTONUP:
            for btn in self._buttons:
                btn.handle_release()
        elif event.type == pygame.KEYDOWN:
            for ti in self._text_inputs:
                ti.handle_key(event)
            if event.key == pygame.K_ESCAPE:
                self.done = True


# ---------------------------------------------------------------------------
# New Match dialog
# ---------------------------------------------------------------------------


class NewMatchDialog(DialogBase):
    def __init__(self) -> None:
        super().__init__(460, 340)
        self.result_mode: Optional[str] = None
        self.result_home_name: str = "Home"
        self.result_visitor_name: str = "Visitor"
        self.result_home_team: Optional[Team] = None
        self.result_visitor_team: Optional[Team] = None

        self._mode = MODE_CVC
        self._custom_home = False
        self._custom_vis = False

        bx = self.x + 20
        by = self.y + 18

        self._cvc_btn = Button(
            pygame.Rect(bx, by + 40, 200, 28),
            "Computer vs Computer",
            lambda: self._set_mode(MODE_CVC),
        )
        self._hvc_btn = Button(
            pygame.Rect(bx + 210, by + 40, 200, 28),
            "Human vs Computer",
            lambda: self._set_mode(MODE_HVC),
        )

        self._home_input = TextInput(
            pygame.Rect(bx + 150, by + 85, 260, 26),
            "Home",
            "Home team name",
        )
        self._vis_input = TextInput(
            pygame.Rect(bx + 150, by + 120, 260, 26),
            "Visitor",
            "Visitor team name",
        )

        self._gen_home_btn = Button(
            pygame.Rect(bx, by + 165, 200, 28),
            "[ ] Gen Home Team",
            self._toggle_gen_home,
        )
        self._gen_vis_btn = Button(
            pygame.Rect(bx + 210, by + 165, 200, 28),
            "[ ] Gen Visitor Team",
            self._toggle_gen_vis,
        )

        self._start_btn = Button(
            pygame.Rect(self.x + 120, self.y + 270, 100, 32),
            "Start Match",
            self._start,
        )
        self._cancel_btn = Button(
            pygame.Rect(self.x + 240, self.y + 270, 100, 32),
            "Cancel",
            self._cancel,
        )

        self._buttons = [
            self._cvc_btn, self._hvc_btn,
            self._gen_home_btn, self._gen_vis_btn,
            self._start_btn, self._cancel_btn,
        ]
        self._text_inputs = [self._home_input, self._vis_input]

    def _set_mode(self, mode: str) -> None:
        self._mode = mode

    def _toggle_gen_home(self) -> None:
        self._custom_home = not self._custom_home
        mark = "[X]" if self._custom_home else "[ ]"
        self._gen_home_btn.text = f"{mark} Gen Home Team"

    def _toggle_gen_vis(self) -> None:
        self._custom_vis = not self._custom_vis
        mark = "[X]" if self._custom_vis else "[ ]"
        self._gen_vis_btn.text = f"{mark} Gen Visitor Team"

    def _start(self) -> None:
        self.result_mode = self._mode
        self.result_home_name = self._home_input.text or "Home"
        self.result_visitor_name = self._vis_input.text or "Visitor"
        self.done = True

    def _cancel(self) -> None:
        self.result_mode = None
        self.done = True

    def _draw_content(self, surface: pygame.Surface) -> None:
        font = _font(FONT_SIZE_TITLE, bold=True)
        title = font.render("New Match Setup", True, TEXT_PRIMARY)
        surface.blit(title, (self.x + 20, self.y + 18))

        font_sm = _font(FONT_SIZE_BODY)
        mode_text = f"Selected: {self._mode}"
        mode_color = TEXT_HIGHLIGHT if self._mode == MODE_HVC else TEXT_ACCENT
        mt = font_sm.render(mode_text, True, mode_color)
        surface.blit(mt, (self.x + 20, self.y + 75))

        lbl_home = font_sm.render("Home Team:", True, TEXT_PRIMARY)
        surface.blit(lbl_home, (self.x + 20, self.y + 105))
        lbl_vis = font_sm.render("Visitor Team:", True, TEXT_PRIMARY)
        surface.blit(lbl_vis, (self.x + 20, self.y + 140))

    @property
    def wants_team_gen(self) -> Tuple[bool, bool]:
        return self._custom_home, self._custom_vis


# ---------------------------------------------------------------------------
# Team generation dialog
# ---------------------------------------------------------------------------


class TeamGenDialog(DialogBase):
    def __init__(self, side: TeamSide, existing_name: str = "") -> None:
        super().__init__(550, 500)
        self.side = side
        self.result_team: Optional[Team] = None

        self._name_input = TextInput(
            pygame.Rect(self.x + 120, self.y + 50, 300, 26),
            existing_name or f"Team {side.value.title()}",
            "Team name",
        )

        self._roll_btn = Button(
            pygame.Rect(self.x + 120, self.y + 440, 100, 30),
            "Roll Team",
            self._roll_team,
        )
        self._accept_btn = Button(
            pygame.Rect(self.x + 240, self.y + 440, 100, 30),
            "Accept",
            self._accept,
        )
        self._cancel_btn = Button(
            pygame.Rect(self.x + 360, self.y + 440, 100, 30),
            "Cancel",
            self._cancel,
        )

        self._buttons = [self._roll_btn, self._accept_btn, self._cancel_btn]
        self._text_inputs = [self._name_input]
        self._team: Optional[Team] = None
        self._preview_lines: List[str] = []
        self._roll_team()

    def _roll_team(self) -> None:
        name = self._name_input.text or f"Team {self.side.value.title()}"
        self._team = Team(self.side, name)
        self._team.generate_roster()
        self._preview_lines = [
            f"Team: {name}  (side: {self.side.value})",
            f"Building pts used: {6 - self._team.building_points}",
            "=" * 50,
        ]
        for fig in self._team.roster:
            ft = fig.figure_type.value.upper()[:7].ljust(7)
            self._preview_lines.append(
                f"  {ft}  SPD {fig.base_speed:2}  SKL {fig.base_skill:2}  "
                f"COM {fig.base_combat:2}  TGH {fig.base_toughness:2}  {fig.name}"
            )

    def _accept(self) -> None:
        self.result_team = self._team
        self.done = True

    def _cancel(self) -> None:
        self.done = True

    def _draw_content(self, surface: pygame.Surface) -> None:
        font = _font(FONT_SIZE_TITLE, bold=True)
        title = font.render(
            f"Team Generation \u2014 {self.side.value.title()}",
            True,
            TEXT_PRIMARY,
        )
        surface.blit(title, (self.x + 20, self.y + 18))

        font_sm = _font(FONT_SIZE_BODY)
        lbl = font_sm.render("Team Name:", True, TEXT_PRIMARY)
        surface.blit(lbl, (self.x + 20, self.y + 54))

        preview_rect = pygame.Rect(
            self.x + 20, self.y + 90, self.width - 40, 330,
        )
        _draw_rounded_rect(
            surface, (14, 20, 35), preview_rect, PANEL_CORNER_RADIUS,
        )
        _draw_rounded_rect(
            surface, PANEL_BORDER, preview_rect, PANEL_CORNER_RADIUS, 1,
        )

        mono = _mono(FONT_SIZE_SMALL)
        line_h = mono.get_linesize()
        cy = preview_rect.y + 4
        for line in self._preview_lines:
            if cy + line_h > preview_rect.bottom:
                break
            txt = mono.render(line, True, TEXT_PRIMARY)
            surface.blit(txt, (preview_rect.x + 8, cy))
            cy += line_h


# ---------------------------------------------------------------------------
# Combat target dialog
# ---------------------------------------------------------------------------


class CombatTargetDialog(DialogBase):
    def __init__(self, attacker: Any, opponents: List[Any]) -> None:
        super().__init__(450, 300)
        self.attacker = attacker
        self.opponents = opponents
        self._selected_idx = 0
        self.result: Optional[Any] = None

        self._attack_btn = Button(
            pygame.Rect(self.x + 100, self.y + 250, 100, 30),
            "Attack",
            self._select,
        )
        self._ai_btn = Button(
            pygame.Rect(self.x + 220, self.y + 250, 120, 30),
            "AI Default",
            self._cancel,
        )
        self._buttons = [self._attack_btn, self._ai_btn]

    def _select(self) -> None:
        if self.opponents:
            self.result = self.opponents[self._selected_idx]
        self.done = True

    def _cancel(self) -> None:
        self.result = None
        self.done = True

    def handle_event(self, event: pygame.event.Event) -> None:
        super().handle_event(event)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP and self._selected_idx > 0:
                self._selected_idx -= 1
            elif (
                event.key == pygame.K_DOWN
                and self._selected_idx < len(self.opponents) - 1
            ):
                self._selected_idx += 1
            elif event.key == pygame.K_RETURN:
                self._select()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            list_y = self.y + 60
            mono = _mono(FONT_SIZE_BODY)
            lh = mono.get_linesize()
            for i in range(len(self.opponents)):
                item_rect = pygame.Rect(
                    self.x + 20, list_y + i * lh, self.width - 40, lh,
                )
                if item_rect.collidepoint(event.pos):
                    self._selected_idx = i
                    break

    def _draw_content(self, surface: pygame.Surface) -> None:
        font = _font(FONT_SIZE_TITLE, bold=True)
        title = font.render(
            f"{self.attacker.name} can attack:", True, TEXT_PRIMARY,
        )
        surface.blit(title, (self.x + 20, self.y + 18))

        mono = _mono(FONT_SIZE_BODY)
        lh = mono.get_linesize()
        list_y = self.y + 60
        for i, opp in enumerate(self.opponents):
            status = opp.status.value if hasattr(opp, "status") else "?"
            text = (
                f"{opp.name}  COM {opp.combat}  TGH {opp.toughness}  [{status}]"
            )
            if i == self._selected_idx:
                bg_rect = pygame.Rect(
                    self.x + 20, list_y + i * lh, self.width - 40, lh,
                )
                _draw_rounded_rect(
                    surface, (50, 60, 80), bg_rect, 3,
                )
            color = TEXT_HIGHLIGHT if i == self._selected_idx else TEXT_PRIMARY
            txt = mono.render(text, True, color)
            surface.blit(txt, (self.x + 28, list_y + i * lh))


# ---------------------------------------------------------------------------
# Escalate dialog
# ---------------------------------------------------------------------------


class EscalateDialog(DialogBase):
    def __init__(self, figure: Any, opponent: Any) -> None:
        super().__init__(400, 200)
        self.result: bool = False

        self._yes_btn = Button(
            pygame.Rect(self.x + 60, self.y + 140, 140, 30),
            "Man-to-Man",
            self._yes,
        )
        self._no_btn = Button(
            pygame.Rect(self.x + 220, self.y + 140, 120, 30),
            "Disengage",
            self._no,
        )
        self._buttons = [self._yes_btn, self._no_btn]
        self._figure = figure
        self._opponent = opponent

    def _yes(self) -> None:
        self.result = True
        self.done = True

    def _no(self) -> None:
        self.result = False
        self.done = True

    def _draw_content(self, surface: pygame.Surface) -> None:
        font = _font(FONT_SIZE_TITLE, bold=True)
        title = font.render("Escalate to Man-to-Man?", True, TEXT_PRIMARY)
        surface.blit(title, (self.x + 20, self.y + 18))

        font_sm = _font(FONT_SIZE_BODY)
        desc = font_sm.render(
            f"Brawl: {self._figure.name} vs {self._opponent.name} \u2014 INDECISIVE",
            True,
            TEXT_SECONDARY,
        )
        surface.blit(desc, (self.x + 20, self.y + 60))
        prompt = font_sm.render(
            "Escalate to man-to-man combat?", True, TEXT_ACCENT,
        )
        surface.blit(prompt, (self.x + 20, self.y + 90))


# ---------------------------------------------------------------------------
# Tow bar dialog
# ---------------------------------------------------------------------------


class TowBarDialog(DialogBase):
    def __init__(self, biker: Any, candidates: List[Any]) -> None:
        super().__init__(450, 320)
        self.biker = biker
        self.candidates = candidates
        self._checks: List[bool] = [False] * len(candidates)
        current_towing = len(getattr(biker, "towing", []))
        self._max = 3 - current_towing
        self.result: Optional[List[Any]] = None

        self._attach_btn = Button(
            pygame.Rect(self.x + 100, self.y + 270, 130, 30),
            "Attach Selected",
            self._select,
        )
        self._none_btn = Button(
            pygame.Rect(self.x + 250, self.y + 270, 130, 30),
            "None / AI",
            self._none,
        )
        self._buttons = [self._attach_btn, self._none_btn]

    def _select(self) -> None:
        chosen = [c for c, v in zip(self.candidates, self._checks) if v]
        self.result = chosen[: self._max]
        self.done = True

    def _none(self) -> None:
        self.result = []
        self.done = True

    def handle_event(self, event: pygame.event.Event) -> None:
        super().handle_event(event)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mono = _mono(FONT_SIZE_BODY)
            lh = mono.get_linesize()
            list_y = self.y + 70
            for i in range(len(self.candidates)):
                item_rect = pygame.Rect(
                    self.x + 20, list_y + i * lh, self.width - 40, lh,
                )
                if item_rect.collidepoint(event.pos):
                    self._checks[i] = not self._checks[i]
                    break

    def _draw_content(self, surface: pygame.Surface) -> None:
        font = _font(FONT_SIZE_TITLE, bold=True)
        title = font.render(
            f"{self.biker.name} \u2014 Tow Bar (max {self._max} more)",
            True,
            TEXT_PRIMARY,
        )
        surface.blit(title, (self.x + 20, self.y + 18))

        mono = _mono(FONT_SIZE_BODY)
        lh = mono.get_linesize()
        list_y = self.y + 70
        for i, fig in enumerate(self.candidates):
            mark = "[X]" if self._checks[i] else "[ ]"
            text = f"{mark} {fig.name}  SPD {fig.speed}  SKL {fig.skill}"
            color = TEXT_HIGHLIGHT if self._checks[i] else TEXT_PRIMARY
            txt = mono.render(text, True, color)
            surface.blit(txt, (self.x + 28, list_y + i * lh))


# ---------------------------------------------------------------------------
# Scoring dialog
# ---------------------------------------------------------------------------


class ScoringDialog(DialogBase):
    def __init__(
        self, shooter: Any, modifiers: List[Tuple[str, int]],
    ) -> None:
        super().__init__(400, 280)
        self.result: bool = True
        self._shooter = shooter
        self._modifiers = modifiers

        self._shoot_btn = Button(
            pygame.Rect(self.x + 60, self.y + 230, 120, 30),
            "Shoot!",
            self._shoot,
        )
        self._hold_btn = Button(
            pygame.Rect(self.x + 200, self.y + 230, 140, 30),
            "Hold \u2014 circle",
            self._hold,
        )
        self._buttons = [self._shoot_btn, self._hold_btn]

    def _shoot(self) -> None:
        self.result = True
        self.done = True

    def _hold(self) -> None:
        self.result = False
        self.done = True

    def _draw_content(self, surface: pygame.Surface) -> None:
        font = _font(FONT_SIZE_TITLE, bold=True)
        title = font.render(
            f"{self._shooter.name} in the goal square!",
            True,
            TEXT_PRIMARY,
        )
        surface.blit(title, (self.x + 20, self.y + 18))

        font_sm = _font(FONT_SIZE_BODY)
        total = sum(v for _, v in self._modifiers)
        sign = "+" if total >= 0 else ""
        stats = font_sm.render(
            f"Skill: {self._shooter.skill}  |  Mod: {sign}{total}  |  "
            f"Target: {self._shooter.skill + total}",
            True,
            TEXT_ACCENT,
        )
        surface.blit(stats, (self.x + 20, self.y + 55))

        mono = _mono(FONT_SIZE_SMALL)
        cy = self.y + 85
        for name, val in self._modifiers:
            sign = "+" if val >= 0 else ""
            txt = mono.render(
                f"  {name}: {sign}{val}", True, TEXT_SECONDARY,
            )
            surface.blit(txt, (self.x + 28, cy))
            cy += mono.get_linesize()


# ---------------------------------------------------------------------------
# Pack formation dialog
# ---------------------------------------------------------------------------


class PackFormationDialog(DialogBase):
    def __init__(self, packs: List[List[Any]]) -> None:
        super().__init__(450, 300)
        self.packs = packs
        self._checks: List[bool] = [True] * len(packs)
        self.result: Optional[List[int]] = None

        self._form_btn = Button(
            pygame.Rect(self.x + 100, self.y + 250, 130, 30),
            "Form Selected",
            self._select,
        )
        self._none_btn = Button(
            pygame.Rect(self.x + 250, self.y + 250, 100, 30),
            "No Packs",
            self._none,
        )
        self._buttons = [self._form_btn, self._none_btn]

    def _select(self) -> None:
        self.result = [i for i, v in enumerate(self._checks) if v]
        self.done = True

    def _none(self) -> None:
        self.result = []
        self.done = True

    def handle_event(self, event: pygame.event.Event) -> None:
        super().handle_event(event)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mono = _mono(FONT_SIZE_BODY)
            lh = mono.get_linesize()
            list_y = self.y + 70
            for i in range(len(self.packs)):
                item_rect = pygame.Rect(
                    self.x + 20, list_y + i * lh, self.width - 40, lh,
                )
                if item_rect.collidepoint(event.pos):
                    self._checks[i] = not self._checks[i]
                    break

    def _draw_content(self, surface: pygame.Surface) -> None:
        font = _font(FONT_SIZE_TITLE, bold=True)
        title = font.render("Pack Formation", True, TEXT_PRIMARY)
        surface.blit(title, (self.x + 20, self.y + 18))

        mono = _mono(FONT_SIZE_BODY)
        lh = mono.get_linesize()
        list_y = self.y + 70
        for i, pack in enumerate(self.packs):
            mark = "[X]" if self._checks[i] else "[ ]"
            names = ", ".join(getattr(f, "name", "?") for f in pack)
            text = f"{mark} Pack {i + 1}: {names}"
            color = TEXT_HIGHLIGHT if self._checks[i] else TEXT_PRIMARY
            txt = mono.render(text[:MAX_LOG_ENTRY_LENGTH], True, color)
            surface.blit(txt, (self.x + 28, list_y + i * lh))


# ---------------------------------------------------------------------------
# Game-over dialog
# ---------------------------------------------------------------------------


class GameOverDialog(DialogBase):
    def __init__(self, result: str, scores: Dict[str, int]) -> None:
        super().__init__(400, 200)
        self._result = result
        self._scores = scores
        self._ok_btn = Button(
            pygame.Rect(self.x + 150, self.y + 140, 100, 30),
            "OK",
            self._close,
        )
        self._buttons = [self._ok_btn]

    def _close(self) -> None:
        self.done = True

    def _draw_content(self, surface: pygame.Surface) -> None:
        font = _font(FONT_SIZE_TITLE + 4, bold=True)
        title = font.render("Game Over!", True, TEXT_ACCENT)
        surface.blit(title, (self.x + 20, self.y + 18))

        font_sm = _font(FONT_SIZE_BODY)
        if self._result == "Draw":
            result_text = "Match ended in a draw!"
        else:
            result_text = f"Winner: {self._result}!"
        rt = font_sm.render(result_text, True, TEXT_PRIMARY)
        surface.blit(rt, (self.x + 20, self.y + 65))

        score_text = " | ".join(
            f"{n}: {s}" for n, s in self._scores.items()
        )
        st = font_sm.render(score_text, True, TEXT_SECONDARY)
        surface.blit(st, (self.x + 20, self.y + 95))


# ---------------------------------------------------------------------------
# Message box
# ---------------------------------------------------------------------------


class MessageDialog(DialogBase):
    def __init__(self, title_text: str, message: str) -> None:
        super().__init__(400, 180)
        self._title_text = title_text
        self._message = message
        self._ok_btn = Button(
            pygame.Rect(self.x + 150, self.y + 130, 100, 30),
            "OK",
            self._close,
        )
        self._buttons = [self._ok_btn]

    def _close(self) -> None:
        self.done = True

    def _draw_content(self, surface: pygame.Surface) -> None:
        font = _font(FONT_SIZE_TITLE, bold=True)
        title = font.render(self._title_text, True, TEXT_ACCENT)
        surface.blit(title, (self.x + 20, self.y + 18))

        font_sm = _font(FONT_SIZE_BODY)
        msg = font_sm.render(self._message, True, TEXT_PRIMARY)
        surface.blit(msg, (self.x + 20, self.y + 65))
