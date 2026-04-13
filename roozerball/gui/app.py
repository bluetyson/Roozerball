"""Minimal Tk GUI for the Roozerball engine."""
from __future__ import annotations

import math
from typing import Any, Dict, Optional

from roozerball.engine.constants import FigureStatus, Ring, SQUARES_PER_RING
from roozerball.engine.game import Game

try:
    import tkinter as tk
    from tkinter import ttk
except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
    tk = None
    ttk = None
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


class RoozerballApp(tk.Tk if tk is not None else object):
    """Small desktop UI for stepping through the match."""

    def __init__(self, game: Optional[Game] = None) -> None:
        if tk is None:  # pragma: no cover - environment dependent
            raise RuntimeError("tkinter is not available in this environment") from _TK_ERROR
        super().__init__()
        self.title("Roozerball")
        self.geometry("1400x860")

        self.game = game or Game()
        self.selected_figure: Optional[Any] = None
        self.figure_lookup: Dict[str, Any] = {}

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)
        self.rowconfigure(1, weight=1)

        controls = ttk.Frame(self, padding=8)
        controls.grid(row=0, column=0, columnspan=2, sticky="ew")
        controls.columnconfigure(3, weight=1)

        ttk.Button(controls, text="Next Phase", command=self.next_phase).grid(row=0, column=0, padx=4)
        ttk.Button(controls, text="Play Turn", command=self.play_turn).grid(row=0, column=1, padx=4)
        ttk.Button(controls, text="New Match", command=self.new_match).grid(row=0, column=2, padx=4)

        summary = ttk.Frame(self, padding=8)
        summary.grid(row=1, column=1, sticky="nsew")
        summary.columnconfigure(0, weight=1)
        summary.rowconfigure(3, weight=1)

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

        selected = ttk.LabelFrame(summary, text="Selected Figure", padding=8)
        selected.grid(row=1, column=0, sticky="ew", pady=8)
        self.selected_var = tk.StringVar(value="No figure selected")
        ttk.Label(selected, textvariable=self.selected_var, justify="left").grid(row=0, column=0, sticky="w")

        penalty_box = ttk.LabelFrame(summary, text="Penalty / Recovery Box", padding=8)
        penalty_box.grid(row=2, column=0, sticky="ew")
        self.penalty_var = tk.StringVar()
        ttk.Label(penalty_box, textvariable=self.penalty_var, justify="left").grid(row=0, column=0, sticky="w")

        log_frame = ttk.LabelFrame(summary, text="Replay Log", padding=8)
        log_frame.grid(row=3, column=0, sticky="nsew", pady=(8, 0))
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log_list = tk.Listbox(log_frame, height=20)
        self.log_list.grid(row=0, column=0, sticky="nsew")
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_list.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.log_list.configure(yscrollcommand=log_scroll.set)

        board_frame = ttk.LabelFrame(self, text="Board", padding=8)
        board_frame.grid(row=1, column=0, sticky="nsew")
        board_frame.rowconfigure(0, weight=1)
        board_frame.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(board_frame, width=900, height=760, background="#111827", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Button-1>", lambda _event: self.clear_selection())

    def new_match(self) -> None:
        self.game = Game()
        self.selected_figure = None
        self.refresh()

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

    def refresh(self) -> None:
        self._refresh_summary()
        self._refresh_log()
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
                )
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

    def _refresh_log(self) -> None:
        self.log_list.delete(0, tk.END)
        for entry in self.game.log:
            self.log_list.insert(tk.END, entry)
        if self.game.log:
            self.log_list.yview_moveto(1.0)

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
            if figure.status == FigureStatus.FALLEN:
                self.canvas.create_oval(cx - 20, cy - 20, cx + 20, cy + 20, outline="#f59e0b", width=3)
            if figure.status == FigureStatus.MAN_TO_MAN:
                self.canvas.create_rectangle(cx - 24, cy - 24, cx + 24, cy + 24, outline="#a855f7", width=2)
            if figure.has_moved:
                self.canvas.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, fill="#fef08a", outline="")

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

            item = self.canvas.create_oval(x - 14, y - 14, x + 14, y + 14, fill=color, outline="white", width=2)
            self.canvas.create_text(x, y, text=label, fill="white", font=("Helvetica", 10, "bold"))
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
        self.canvas.create_oval(x - 8, y - 8, x + 8, y + 8, fill="#f97316", outline="#fff7ed", width=2)

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
