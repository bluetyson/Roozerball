"""Minimal Tk GUI for the Roozerball engine."""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from roozerball.engine.constants import FigureStatus, FigureType, Ring, SQUARES_PER_RING, TeamSide
from roozerball.engine.game import Game
from roozerball.engine.team import Team

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
    tk = None
    ttk = None
    filedialog = None
    messagebox = None
    _TK_ERROR = exc
else:
    _TK_ERROR = None

TEAM_COLORS = {
    "home": "#1f77b4",
    "visitor": "#d62728",
}

FIGURE_LABELS = {
    "bruiser": "B",
    "speeder": "S",
    "catcher": "C",
    "biker": "K",
}

RING_RADII = {
    Ring.FLOOR: (40, 90),
    Ring.LOWER: (90, 150),
    Ring.MIDDLE: (150, 220),
    Ring.UPPER: (220, 300),
    Ring.CANNON: (300, 340),
}

SLOT_OFFSETS = {
    4: [(-12, -10), (12, -10), (-12, 10), (12, 10)],
    6: [(-18, -10), (0, -10), (18, -10), (-18, 10), (0, 10), (18, 10)],
}
COMBAT_KEYWORDS = ("Brawl:", "Assault:", "Swoop:")
MAX_COMBAT_LINES_DISPLAYED = 3
MAX_DICE_LOG = 20

# Modes (GUI14)
MODE_CVC = "Computer vs Computer"
MODE_HVC = "Human vs Computer"


# ---------------------------------------------------------------------------
# GUI7 helper — dice roll log
# ---------------------------------------------------------------------------

_dice_log: List[str] = []


def _log_dice(label: str, result: Any) -> None:
    _dice_log.append(f"{label}: {result}")
    if len(_dice_log) > MAX_DICE_LOG:
        _dice_log.pop(0)


# ---------------------------------------------------------------------------
# Team generation dialog (GUI15)
# ---------------------------------------------------------------------------

class TeamGenDialog(tk.Toplevel if tk is not None else object):
    """Dialog for creating / viewing teams (Rule H6-H9)."""

    def __init__(self, parent: Any, side: TeamSide, existing_name: str = "") -> None:
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title(f"Team Generation — {side.value.title()}")
        self.resizable(False, False)

        self.side = side
        self.result_team: Optional[Team] = None

        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="Team Name:").grid(row=0, column=0, sticky="w")
        self._name_var = tk.StringVar(value=existing_name or f"Team {side.value.title()}")
        ttk.Entry(main, textvariable=self._name_var, width=24).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self._preview_text = tk.Text(main, width=60, height=20, state="disabled",
                                     font=("Courier", 9))
        self._preview_text.grid(row=1, column=0, columnspan=2, pady=8)

        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=2, column=0, columnspan=2)
        ttk.Button(btn_frame, text="Roll Team", command=self._roll_team).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Accept", command=self._accept).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=4)

        self._team: Optional[Team] = None
        self._roll_team()
        self.wait_window(self)

    def _roll_team(self) -> None:
        name = self._name_var.get() or f"Team {self.side.value.title()}"
        self._team = Team(self.side, name)
        self._team.generate_roster()

        lines = [f"Team: {name}  (side: {self.side.value})",
                 f"Building points used: {6 - self._team.building_points}",
                 "=" * 55]
        for fig in self._team.roster:
            ft = fig.figure_type.value.upper()[:7].ljust(7)
            lines.append(
                f"  {ft}  SPD {fig.base_speed:2}  SKL {fig.base_skill:2}  "
                f"COM {fig.base_combat:2}  TGH {fig.base_toughness:2}  {fig.name}"
            )
        self._preview_text.configure(state="normal")
        self._preview_text.delete("1.0", "end")
        self._preview_text.insert("end", "\n".join(lines))
        self._preview_text.configure(state="disabled")

    def _accept(self) -> None:
        self.result_team = self._team
        self.destroy()


# ---------------------------------------------------------------------------
# Mode selection dialog (GUI14)
# ---------------------------------------------------------------------------

class ModeDialog(tk.Toplevel if tk is not None else object):
    """Dialog for choosing game mode and team names."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title("New Match Setup")
        self.resizable(False, False)

        self.result_mode: Optional[str] = None
        self.result_home_name: str = "Home"
        self.result_visitor_name: str = "Visitor"
        self.result_home_team: Optional[Team] = None
        self.result_visitor_team: Optional[Team] = None

        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="Game Mode:", font=("Helvetica", 11, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        self._mode_var = tk.StringVar(value=MODE_CVC)
        for col, mode in enumerate([MODE_CVC, MODE_HVC]):
            ttk.Radiobutton(main, text=mode, variable=self._mode_var, value=mode).grid(
                row=1, column=col, sticky="w", padx=8)

        sep = ttk.Separator(main, orient="horizontal")
        sep.grid(row=2, column=0, columnspan=2, sticky="ew", pady=8)

        ttk.Label(main, text="Home Team Name:").grid(row=3, column=0, sticky="w")
        self._home_var = tk.StringVar(value="Home")
        ttk.Entry(main, textvariable=self._home_var, width=20).grid(
            row=3, column=1, sticky="ew", padx=(6, 0))

        ttk.Label(main, text="Visitor Team Name:").grid(row=4, column=0, sticky="w")
        self._vis_var = tk.StringVar(value="Visitor")
        ttk.Entry(main, textvariable=self._vis_var, width=20).grid(
            row=4, column=1, sticky="ew", padx=(6, 0))

        sep2 = ttk.Separator(main, orient="horizontal")
        sep2.grid(row=5, column=0, columnspan=2, sticky="ew", pady=8)

        self._custom_home = tk.BooleanVar(value=False)
        self._custom_vis = tk.BooleanVar(value=False)
        ttk.Checkbutton(main, text="Generate home team (H6–H9)",
                        variable=self._custom_home).grid(row=6, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(main, text="Generate visitor team (H6–H9)",
                        variable=self._custom_vis).grid(row=7, column=0, columnspan=2, sticky="w")

        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=8, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(btn_frame, text="Start Match", command=self._start).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=4)

        self.wait_window(self)

    def _start(self) -> None:
        self.result_mode = self._mode_var.get()
        self.result_home_name = self._home_var.get() or "Home"
        self.result_visitor_name = self._vis_var.get() or "Visitor"
        if self._custom_home.get():
            dlg = TeamGenDialog(self, TeamSide.HOME, self.result_home_name)
            self.result_home_team = dlg.result_team
        if self._custom_vis.get():
            dlg = TeamGenDialog(self, TeamSide.VISITOR, self.result_visitor_name)
            self.result_visitor_team = dlg.result_team
        self.destroy()


# ---------------------------------------------------------------------------
# Main application window
# ---------------------------------------------------------------------------

class RoozerballApp(tk.Tk if tk is not None else object):
    """Desktop UI for stepping through the match."""

    def __init__(self, game: Optional[Game] = None) -> None:
        if tk is None:  # pragma: no cover - environment dependent
            raise RuntimeError("tkinter is not available in this environment") from _TK_ERROR
        super().__init__()
        self.title("Roozerball")
        self.geometry("1500x900")

        self.game = game or Game()
        self.game_mode: str = MODE_CVC
        self.selected_figure: Optional[Any] = None
        self.figure_lookup: Dict[str, Any] = {}

        _dice_log.clear()

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0, minsize=380)
        self.rowconfigure(1, weight=1)

        # ---- Top control bar ----
        controls = ttk.Frame(self, padding=8)
        controls.grid(row=0, column=0, columnspan=2, sticky="ew")
        controls.columnconfigure(5, weight=1)

        ttk.Button(controls, text="New Match", command=self.new_match_dialog).grid(
            row=0, column=0, padx=4)
        ttk.Button(controls, text="Next Phase", command=self.next_phase).grid(
            row=0, column=1, padx=4)
        ttk.Button(controls, text="Play Turn", command=self.play_turn).grid(
            row=0, column=2, padx=4)
        ttk.Button(controls, text="Gen Teams", command=self.open_team_gen).grid(
            row=0, column=3, padx=4)

        self._mode_label = ttk.Label(controls, text=f"Mode: {self.game_mode}",
                                     font=("Helvetica", 9), foreground="#6b7280")
        self._mode_label.grid(row=0, column=4, padx=12)

        # Top-right: scoreboard + last phase action
        top_right = ttk.Frame(controls)
        top_right.grid(row=0, column=5, sticky="e", padx=(8, 4))
        top_right.columnconfigure(0, weight=1)

        self._top_score_var = tk.StringVar(value="")
        ttk.Label(top_right, textvariable=self._top_score_var,
                  font=("Helvetica", 10, "bold"), foreground="#f9fafb").grid(
            row=0, column=0, sticky="e")

        self._last_action_var = tk.StringVar(value="")
        ttk.Label(top_right, textvariable=self._last_action_var,
                  font=("Helvetica", 9), foreground="#d1d5db",
                  wraplength=450, justify="right").grid(
            row=1, column=0, sticky="e")

        # ---- Right panel ----
        summary = ttk.Frame(self, padding=8)
        summary.grid(row=1, column=1, sticky="nsew")
        summary.columnconfigure(0, weight=1)
        summary.rowconfigure(5, weight=1)

        # Scoreboard
        scoreboard = ttk.LabelFrame(summary, text="Scoreboard", padding=8)
        scoreboard.grid(row=0, column=0, sticky="ew")
        self.score_var = tk.StringVar()
        self.phase_var = tk.StringVar()
        self.initiative_var = tk.StringVar()
        self.ball_var = tk.StringVar()
        ttk.Label(scoreboard, textvariable=self.score_var).grid(row=0, column=0, sticky="w")
        ttk.Label(scoreboard, textvariable=self.phase_var).grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Label(scoreboard, textvariable=self.initiative_var).grid(row=2, column=0, sticky="w")
        ttk.Label(scoreboard, textvariable=self.ball_var).grid(row=3, column=0, sticky="w")

        # Selected figure HUD
        selected = ttk.LabelFrame(summary, text="Selected Figure", padding=8)
        selected.grid(row=1, column=0, sticky="ew", pady=8)
        self.selected_var = tk.StringVar(value="No figure selected")
        ttk.Label(selected, textvariable=self.selected_var, justify="left").grid(
            row=0, column=0, sticky="w")

        # Penalty / Recovery Box
        penalty_box = ttk.LabelFrame(summary, text="Penalty / Recovery Box", padding=8)
        penalty_box.grid(row=2, column=0, sticky="ew")
        self.penalty_var = tk.StringVar()
        ttk.Label(penalty_box, textvariable=self.penalty_var, justify="left").grid(
            row=0, column=0, sticky="w")

        # Combat resolution overlay
        combat_frame = ttk.LabelFrame(summary, text="Combat Resolution", padding=8)
        combat_frame.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        self.combat_var = tk.StringVar(value="No combat resolved yet")
        ttk.Label(combat_frame, textvariable=self.combat_var, justify="left").grid(
            row=0, column=0, sticky="w")

        # GUI7: Dice roll log panel
        dice_frame = ttk.LabelFrame(summary, text="Dice Rolls (GUI7)", padding=8)
        dice_frame.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        dice_frame.columnconfigure(0, weight=1)
        self.dice_list = tk.Listbox(dice_frame, height=5, font=("Courier", 9))
        self.dice_list.grid(row=0, column=0, sticky="ew")
        dice_scroll = ttk.Scrollbar(dice_frame, orient="vertical", command=self.dice_list.yview)
        dice_scroll.grid(row=0, column=1, sticky="ns")
        self.dice_list.configure(yscrollcommand=dice_scroll.set)
        ttk.Button(dice_frame, text="Roll 2d6", command=self._manual_roll_2d6).grid(
            row=1, column=0, sticky="w", pady=(4, 0))

        # Replay log
        log_frame = ttk.LabelFrame(summary, text="Replay Log", padding=8)
        log_frame.grid(row=5, column=0, sticky="nsew", pady=(8, 0))
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log_list = tk.Listbox(log_frame, height=16, width=50, font=("Courier", 9))
        self.log_list.grid(row=0, column=0, sticky="nsew")
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_list.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.log_list.configure(yscrollcommand=log_scroll.set)
        ttk.Button(log_frame, text="Save Log", command=self._save_log).grid(
            row=1, column=0, sticky="w", pady=(4, 0))

        # ---- Board canvas ----
        board_frame = ttk.LabelFrame(self, text="Board", padding=8)
        board_frame.grid(row=1, column=0, sticky="nsew")
        board_frame.rowconfigure(0, weight=1)
        board_frame.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(board_frame, width=900, height=760,
                                background="#111827", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Button-1>", lambda _event: self.clear_selection())

    # -----------------------------------------------------------------------
    # GUI14: New Match dialog
    # -----------------------------------------------------------------------

    def new_match_dialog(self) -> None:
        dlg = ModeDialog(self)
        if dlg.result_mode is None:
            return
        self.game_mode = dlg.result_mode
        home_name = dlg.result_home_name
        vis_name = dlg.result_visitor_name
        self.game = Game(home_name=home_name, visitor_name=vis_name)
        # Apply custom rosters if generated
        if dlg.result_home_team is not None:
            self.game.home_team.roster = dlg.result_home_team.roster
            for f in self.game.home_team.roster:
                f.team = TeamSide.HOME
            self.game.home_team.select_starting_lineup()
        if dlg.result_visitor_team is not None:
            self.game.visitor_team.roster = dlg.result_visitor_team.roster
            for f in self.game.visitor_team.roster:
                f.team = TeamSide.VISITOR
            self.game.visitor_team.select_starting_lineup()
        self.game.setup_match()
        self.selected_figure = None
        self._mode_label.configure(text=f"Mode: {self.game_mode}")
        _dice_log.clear()
        self.refresh()

    def new_match(self) -> None:
        """Quick new match with defaults."""
        self.game = Game()
        self.selected_figure = None
        _dice_log.clear()
        self.refresh()

    # -----------------------------------------------------------------------
    # GUI15: Team generation shortcut
    # -----------------------------------------------------------------------

    def open_team_gen(self) -> None:
        dlg = TeamGenDialog(self, TeamSide.HOME, self.game.home_team.name)
        if dlg.result_team is not None:
            self.game.home_team.roster = dlg.result_team.roster
            for f in self.game.home_team.roster:
                f.team = TeamSide.HOME
            self.game.home_team.select_starting_lineup()
            self.game.setup_match()
            self.selected_figure = None
            self.refresh()

    # -----------------------------------------------------------------------
    # GUI7: Manual dice roll
    # -----------------------------------------------------------------------

    def _manual_roll_2d6(self) -> None:
        import random as _r
        r1 = _r.randint(1, 6)
        r2 = _r.randint(1, 6)
        result = r1 + r2
        _log_dice(f"Manual 2d6 [{r1}+{r2}]", result)
        self._refresh_dice_log()

    def _save_log(self) -> None:
        """Save the current replay log to a text file."""
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Replay Log",
        )
        if not path:
            return
        try:
            snapshot = self.game.snapshot()
            scores = snapshot["scores"]
            score_text = " | ".join(f"{name}: {score}" for name, score in scores.items())
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("Roozerball Game Replay Log\n")
                fh.write(
                    f"Period {snapshot['period']} · "
                    f"Time {snapshot['time_remaining']}:00 · "
                    f"Turn {snapshot['turn']}\n"
                )
                fh.write(f"Scores: {score_text}\n")
                fh.write("=" * 60 + "\n")
                for entry in self.game.log:
                    fh.write(entry + "\n")
            messagebox.showinfo("Saved", f"Log saved to:\n{path}")
        except OSError as exc:
            messagebox.showerror("Error", f"Could not save log:\n{exc}")

    # -----------------------------------------------------------------------
    # Phase controls
    # -----------------------------------------------------------------------

    def next_phase(self) -> None:
        self.game.advance_phase()
        self.refresh()

    def play_turn(self) -> None:
        self.game.play_turn()
        self.refresh()

    def clear_selection(self) -> None:
        self.selected_figure = None
        self.refresh()

    def select_figure(self, figure: Any) -> None:
        self.selected_figure = figure
        self.refresh()

    # -----------------------------------------------------------------------
    # Refresh
    # -----------------------------------------------------------------------

    def refresh(self) -> None:
        self._refresh_summary()
        self._refresh_log()
        self._refresh_dice_log()
        self._draw_board()

    def _refresh_summary(self) -> None:
        snapshot = self.game.snapshot()
        scores = snapshot["scores"]
        score_text = " | ".join(f"{name}: {score}" for name, score in scores.items())
        self.score_var.set(
            f"Period {snapshot['period']} · Time {snapshot['time_remaining']}:00 · Turn {snapshot['turn']}\n{score_text}"
        )
        self.phase_var.set(f"Phase: {snapshot['phase'].title()}")
        sector = snapshot["initiative_sector"]
        if sector is None:
            self.initiative_var.set("Initiative: —")
        else:
            self.initiative_var.set(f"Initiative: Sector {self.game.board.get_sector(sector).name}")
        self.ball_var.set(
            f"Ball: {snapshot['ball']['state']} · {snapshot['ball']['temperature']} · "
            f"speed {snapshot['ball']['speed']}"
        )

        if self.selected_figure is None:
            self.selected_var.set("No figure selected")
        else:
            square = self.game.board.find_square_of_figure(self.selected_figure)
            location = "off track"
            if square is not None:
                location = (
                    f"{self.game.board.get_sector(square.sector_index).name} / "
                    f"{square.ring.name.lower()} / {square.position + 1}"
                )
            tow_info = ""
            if getattr(self.selected_figure, 'is_towed', False):
                tow_info = f"\nTowed by: {getattr(self.selected_figure.towed_by, 'name', '?')}"
            elif getattr(self.selected_figure, 'towing', []):
                names = ", ".join(getattr(f, 'name', '?') for f in self.selected_figure.towing)
                tow_info = f"\nTowing: {names}"
            endurance_info = ""
            endurance_used = getattr(self.selected_figure, 'endurance_used', 0)
            if endurance_used:
                max_e = getattr(self.selected_figure, 'base_toughness', 7) + 3
                endurance_info = f"\nEndurance: {endurance_used}/{max_e}"
            self.selected_var.set(
                "\n".join(
                    [
                        self.selected_figure.name,
                        f"Type: {self.selected_figure.figure_type.value}",
                        f"Stats: SPD {self.selected_figure.speed} · SKL {self.selected_figure.skill} · "
                        f"COM {self.selected_figure.combat} · TGH {self.selected_figure.toughness}",
                        f"Status: {self.selected_figure.status.value}",
                        f"Location: {location}",
                    ]
                ) + tow_info + endurance_info
            )

        penalty_lines = []
        for team in self.game.teams:
            entries = []
            for figure in team.active_figures:
                if figure.is_ready_to_return():
                    continue
                if figure.penalty_time <= 0 and figure.shaken_time <= 0 and figure.rest_time <= 0:
                    continue
                timer = max(figure.penalty_time, figure.shaken_time, figure.rest_time)
                entries.append(f"{figure.name} ({timer}:00)")
            if entries:
                penalty_lines.append(f"{team.name}: " + ", ".join(entries))
        self.penalty_var.set("\n".join(penalty_lines) if penalty_lines else "No figures in the box")
        self.combat_var.set(self._latest_combat_summary())

        # Top-right scoreboard and last phase action
        self._top_score_var.set(score_text)
        result = self.game.last_phase_result
        if result is not None and result.messages:
            phase_name = result.phase.value.replace("_", " ").title()
            last_msg = result.messages[-1]
            self._last_action_var.set(f"[{phase_name}] {last_msg}")
        else:
            self._last_action_var.set("")

    def _refresh_log(self) -> None:
        self.log_list.delete(0, tk.END)
        for entry in self.game.log:
            self.log_list.insert(tk.END, entry)
        if self.game.log:
            self.log_list.yview_moveto(1.0)

    def _refresh_dice_log(self) -> None:
        """GUI7: Refresh dice roll log panel."""
        self.dice_list.delete(0, tk.END)
        for entry in _dice_log:
            self.dice_list.insert(tk.END, entry)
        if _dice_log:
            self.dice_list.yview_moveto(1.0)

    def _draw_board(self) -> None:
        self.canvas.delete("all")
        self.figure_lookup.clear()
        self._draw_squares()
        self._draw_highlights()
        self._draw_figures()
        self._draw_ball()

    def _draw_squares(self) -> None:
        cx, cy = 430, 380
        for sector_index, sector in enumerate(self.game.board.sectors):
            base_start = -math.pi / 2 + sector_index * (2 * math.pi / 12)
            sector_span = 2 * math.pi / 12
            for ring in Ring:
                inner_radius, outer_radius = RING_RADII[ring]
                square_count = SQUARES_PER_RING[ring]
                for position in range(square_count):
                    start = base_start + (sector_span / square_count) * position
                    end = start + (sector_span / square_count)
                    polygon = self._wedge_polygon(cx, cy, inner_radius, outer_radius, start, end)
                    fill = "#1f2937" if ring != Ring.CANNON else "#374151"
                    outline = "#4b5563"
                    width = 1
                    square = self.game.board.get_square(sector_index, ring, position)
                    if square.is_goal:
                        fill = "#14532d" if square.goal_side.value == "home" else "#7f1d1d"
                    if sector_index == self.game.current_initiative_sector:
                        outline = "#93c5fd"
                        width = 2
                    self.canvas.create_polygon(polygon, fill=fill, outline=outline, width=width)
            mid_angle = base_start + sector_span / 2
            self.canvas.create_text(
                cx + math.cos(mid_angle) * 355,
                cy + math.sin(mid_angle) * 355,
                text=sector.name,
                fill="#e5e7eb",
                font=("Helvetica", 10, "bold"),
            )

    def _draw_highlights(self) -> None:
        for figure in self.game.all_figures():
            square = self.game.board.find_square_of_figure(figure)
            if square is None:
                continue
            cx, cy = self._square_center(square)
            if figure.needs_stand_up:
                self.canvas.create_oval(cx - 20, cy - 20, cx + 20, cy + 20, outline="#f59e0b", width=3)
            if figure.status == FigureStatus.MAN_TO_MAN:
                self.canvas.create_rectangle(cx - 24, cy - 24, cx + 24, cy + 24, outline="#a855f7", width=2)
            if figure.has_moved:
                self.canvas.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, fill="#fef08a", outline="")
            # Tow bar indicator (E9-E14)
            if getattr(figure, 'is_towed', False):
                self.canvas.create_line(cx, cy, cx, cy - 12, fill="#22c55e", width=2)
            # Endurance warning (H3)
            endurance_used = getattr(figure, 'endurance_used', 0)
            max_e = getattr(figure, 'base_toughness', 7) + 3
            if endurance_used > max_e:
                self.canvas.create_text(cx + 14, cy - 14, text="E!", fill="#ef4444",
                                        font=("Helvetica", 8, "bold"))

        for sector in self.game.board.sectors:
            for square in sector.all_squares():
                if not square.has_obstacle and not square.is_on_fire:
                    continue
                cx, cy = self._square_center(square)
                marker = "⚠" if square.has_obstacle else "🔥"
                color = "#fbbf24" if square.has_obstacle else "#ef4444"
                self.canvas.create_text(cx, cy, text=marker, fill=color, font=("Helvetica", 14, "bold"))

        if self.selected_figure is None:
            return

        for square, cost in self.game.movement_options_with_costs(self.selected_figure):
            cx, cy = self._square_center(square)
            self.canvas.create_oval(cx - 26, cy - 26, cx + 26, cy + 26, outline="#22d3ee", width=2, dash=(4, 3))
            self.canvas.create_text(cx, cy + 22, text=str(cost), fill="#67e8f9", font=("Helvetica", 9, "bold"))

    def _draw_figures(self) -> None:
        for figure in self.game.all_figures():
            square = self.game.board.find_square_of_figure(figure)
            if square is None:
                continue
            x, y = self._slot_center(square, figure.slot_index or 0)
            color = TEAM_COLORS.get(figure.team.value, "#6b7280")
            figure_type = figure.figure_type.value
            fallback_label = figure_type[0].upper() if figure_type else "?"
            label = FIGURE_LABELS.get(figure_type, fallback_label)

            # Show injured/fallen with dim ring
            if figure.needs_stand_up or figure.status in (
                    FigureStatus.UNCONSCIOUS, FigureStatus.DEAD):
                color = "#4b5563"

            item = self.canvas.create_oval(x - 14, y - 14, x + 14, y + 14,
                                           fill=color, outline="white", width=2)
            self.canvas.create_text(x, y, text=label, fill="white", font=("Helvetica", 10, "bold"))
            # Ball indicator
            if figure.has_ball:
                self.canvas.create_oval(x + 8, y - 14, x + 20, y - 2,
                                        fill="#f97316", outline="#fff7ed", width=1)
            self.figure_lookup[str(item)] = figure
            self.canvas.tag_bind(item, "<Button-1>", self._on_figure_click)

    def _draw_ball(self) -> None:
        if self.game.ball.state.value == "not_in_play":
            return
        if self.game.ball.carrier is not None:
            square = self.game.board.find_square_of_figure(self.game.ball.carrier)
            if square is None:
                return
            x, y = self._slot_center(square, self.game.ball.carrier.slot_index or 0)
            x += 18
            y -= 18
        else:
            square = self.game.board.get_square(
                self.game.ball.sector_index,
                self.game.ball.ring,
                self.game.ball.position,
            )
            x, y = self._square_center(square)
        # Temperature colour
        temp_colors = {
            "very_hot": "#ff2020",
            "hot": "#ff8800",
            "warm": "#fbbf24",
            "cool": "#60a5fa",
        }
        ball_color = temp_colors.get(self.game.ball.temperature.value, "#f97316")
        self.canvas.create_oval(x - 8, y - 8, x + 8, y + 8,
                                fill=ball_color, outline="#fff7ed", width=2)

    def _on_figure_click(self, event: tk.Event[Any]) -> None:
        item = self.canvas.find_withtag("current")
        if not item:
            return
        figure = self.figure_lookup.get(str(item[0]))
        if figure is None:
            return
        self.selected_figure = figure
        self.refresh()

    def _square_center(self, square: Any) -> tuple[float, float]:
        cx, cy = 430, 380
        inner_radius, outer_radius = RING_RADII[square.ring]
        sector_span = 2 * math.pi / 12
        sector_start = -math.pi / 2 + square.sector_index * sector_span
        square_span = sector_span / SQUARES_PER_RING[square.ring]
        angle = sector_start + square_span * (square.position + 0.5)
        radius = (inner_radius + outer_radius) / 2
        return cx + math.cos(angle) * radius, cy + math.sin(angle) * radius

    def _slot_center(self, square: Any, slot_index: int) -> tuple[float, float]:
        x, y = self._square_center(square)
        offsets = SLOT_OFFSETS[len(square.slots)]
        dx, dy = offsets[min(slot_index, len(offsets) - 1)]
        return x + dx, y + dy

    def _latest_combat_summary(self) -> str:
        result = self.game.last_phase_result
        if result is not None and result.phase.value == "combat":
            combat_lines = [line for line in result.messages if line]
            if combat_lines:
                return "\n".join(combat_lines[-MAX_COMBAT_LINES_DISPLAYED:])
        recent = [entry for entry in reversed(self.game.log) if any(keyword in entry for keyword in COMBAT_KEYWORDS)]
        if recent:
            return recent[0]
        return "No combat resolved yet"

    @staticmethod
    def _wedge_polygon(
        cx: float,
        cy: float,
        inner_radius: float,
        outer_radius: float,
        start: float,
        end: float,
    ) -> list[float]:
        return [
            cx + math.cos(start) * inner_radius,
            cy + math.sin(start) * inner_radius,
            cx + math.cos(start) * outer_radius,
            cy + math.sin(start) * outer_radius,
            cx + math.cos(end) * outer_radius,
            cy + math.sin(end) * outer_radius,
            cx + math.cos(end) * inner_radius,
            cy + math.sin(end) * inner_radius,
        ]


def launch() -> None:
    if tk is None:  # pragma: no cover - environment dependent
        raise RuntimeError("tkinter is not available in this environment") from _TK_ERROR
    app = RoozerballApp()
    app.mainloop()


if __name__ == "__main__":
    launch()
