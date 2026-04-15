"""Tkinter GUI for the Roozerball engine.

Includes:
  * Full human-interactive play (movement confirmation, click-to-target
    combat, tow-bar controls, pack formation, scoring shot control)
  * Tier-1 graphics enhancements (procedural sprites, smooth animation,
    particle effects, track texture, zoom & pan)
"""
from __future__ import annotations

import math
import random as _rng
from typing import Any, Dict, List, Optional, Tuple

from roozerball.engine.constants import FigureStatus, FigureType, Ring, SQUARES_PER_RING, TeamSide
from roozerball.engine.game import Game
from roozerball.engine.scoring import calculate_scoring_modifiers
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

# ---------------------------------------------------------------------------
# Tier 1 graphics: colour palettes for procedural sprites
# ---------------------------------------------------------------------------
SPRITE_COLORS = {
    "bruiser": {"fill": "#3b82f6", "accent": "#1e3a5f"},
    "speeder": {"fill": "#06b6d4", "accent": "#164e63"},
    "catcher": {"fill": "#10b981", "accent": "#064e3b"},
    "biker": {"fill": "#8b5cf6", "accent": "#4c1d95"},
}
SPRITE_COLORS_VISITOR = {
    "bruiser": {"fill": "#ef4444", "accent": "#7f1d1d"},
    "speeder": {"fill": "#f97316", "accent": "#7c2d12"},
    "catcher": {"fill": "#f59e0b", "accent": "#78350f"},
    "biker": {"fill": "#ec4899", "accent": "#831843"},
}

# Animation timing
ANIM_STEP_MS = 30
ANIM_STEPS = 12

# Particle settings
PARTICLE_LIFETIME = 600  # ms
PARTICLE_COUNT_CANNON = 24
PARTICLE_COUNT_CRASH = 12
PARTICLE_COUNT_GOAL = 30

# Modes (GUI14)
MODE_CVC = "Computer vs Computer"
MODE_HVC = "Human vs Computer"

# Canvas scoreboard overlay geometry
_SCOREBOARD_RIGHT = 890
_SCOREBOARD_TOP = 12
_SCOREBOARD_WIDTH = 240
_SCOREBOARD_LINE_HEIGHT = 18
_SCOREBOARD_PADDING = 6


# ---------------------------------------------------------------------------
# GUI7 helper — dice roll log
# ---------------------------------------------------------------------------

_dice_log: List[str] = []


def _log_dice(label: str, result: Any) -> None:
    _dice_log.append(f"{label}: {result}")
    if len(_dice_log) > MAX_DICE_LOG:
        _dice_log.pop(0)


# ---------------------------------------------------------------------------
# Tier 1 — Particle system for canvas effects
# ---------------------------------------------------------------------------

class _Particle:
    """A single animated particle rendered on a Tk canvas."""

    __slots__ = ("x", "y", "vx", "vy", "color", "size", "life", "max_life", "canvas_id")

    def __init__(self, x: float, y: float, vx: float, vy: float,
                 color: str, size: float, lifetime: int) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.life = lifetime
        self.max_life = lifetime
        self.canvas_id: Optional[int] = None


class ParticleSystem:
    """Lightweight canvas-based particle manager (Tier 1 graphics)."""

    def __init__(self, canvas: "tk.Canvas") -> None:
        self._canvas = canvas
        self._particles: List[_Particle] = []
        self._running = False

    def emit(self, x: float, y: float, count: int, *,
             colors: Optional[List[str]] = None,
             speed_range: Tuple[float, float] = (1.0, 4.0),
             size_range: Tuple[float, float] = (2.0, 5.0),
             lifetime: int = PARTICLE_LIFETIME) -> None:
        if colors is None:
            colors = ["#fbbf24", "#f97316", "#ef4444", "#ffffff"]
        for _ in range(count):
            angle = _rng.uniform(0, 2 * math.pi)
            speed = _rng.uniform(*speed_range)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            color = _rng.choice(colors)
            size = _rng.uniform(*size_range)
            p = _Particle(x, y, vx, vy, color, size, lifetime)
            self._particles.append(p)
        if not self._running:
            self._running = True
            self._tick()

    def _tick(self) -> None:
        dt = ANIM_STEP_MS
        alive: List[_Particle] = []
        for p in self._particles:
            p.life -= dt
            if p.life <= 0:
                if p.canvas_id is not None:
                    self._canvas.delete(p.canvas_id)
                continue
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1  # gravity
            alpha = max(0.0, p.life / p.max_life)
            size = p.size * alpha
            if p.canvas_id is not None:
                self._canvas.delete(p.canvas_id)
            if size > 0.5:
                p.canvas_id = self._canvas.create_oval(
                    p.x - size, p.y - size, p.x + size, p.y + size,
                    fill=p.color, outline="",
                )
            alive.append(p)
        self._particles = alive
        if alive:
            self._canvas.after(dt, self._tick)
        else:
            self._running = False

    def clear(self) -> None:
        for p in self._particles:
            if p.canvas_id is not None:
                self._canvas.delete(p.canvas_id)
        self._particles.clear()
        self._running = False


# ---------------------------------------------------------------------------
# Tier 1 — Smooth animation helper
# ---------------------------------------------------------------------------

class _AnimationManager:
    """Queues and plays smooth canvas-item translations (Tier 1)."""

    def __init__(self, canvas: "tk.Canvas") -> None:
        self._canvas = canvas
        self._queue: List[Tuple[int, float, float, float, float, int]] = []
        self._playing = False

    def animate_move(self, item_id: int,
                     x0: float, y0: float,
                     x1: float, y1: float,
                     steps: int = ANIM_STEPS) -> None:
        self._queue.append((item_id, x0, y0, x1, y1, steps))
        if not self._playing:
            self._playing = True
            self._play_next()

    def _play_next(self) -> None:
        if not self._queue:
            self._playing = False
            return
        item_id, x0, y0, x1, y1, total = self._queue.pop(0)
        self._step(item_id, x0, y0, x1, y1, 0, total)

    def _step(self, item_id: int, x0: float, y0: float,
              x1: float, y1: float, step: int, total: int) -> None:
        if step >= total:
            self._play_next()
            return
        t = (step + 1) / total
        nx = x0 + (x1 - x0) * t
        ny = y0 + (y1 - y0) * t
        px = x0 + (x1 - x0) * (step / total)
        py = y0 + (y1 - y0) * (step / total)
        self._canvas.move(item_id, nx - px, ny - py)
        self._canvas.after(ANIM_STEP_MS, self._step,
                           item_id, x0, y0, x1, y1, step + 1, total)


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
# Human-interactive dialogs
# ---------------------------------------------------------------------------

class CombatTargetDialog(tk.Toplevel if tk is not None else object):
    """Let the human player pick which opposing figure to attack."""

    def __init__(self, parent: Any, attacker: Any, opponents: List[Any]) -> None:
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title("Choose Combat Target")
        self.resizable(False, False)
        self.result: Optional[Any] = None

        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text=f"{attacker.name} can attack:",
                  font=("Helvetica", 11, "bold")).pack(anchor="w", pady=(0, 6))

        self._listbox = tk.Listbox(main, height=min(8, len(opponents)),
                                   font=("Courier", 10), width=50)
        self._listbox.pack(fill="x")
        self._opponents = opponents
        for opp in opponents:
            status = opp.status.value if hasattr(opp, 'status') else '?'
            self._listbox.insert(tk.END,
                                 f"{opp.name}  COM {opp.combat}  "
                                 f"TGH {opp.toughness}  [{status}]")
        if opponents:
            self._listbox.selection_set(0)

        btn = ttk.Frame(main)
        btn.pack(pady=(8, 0))
        ttk.Button(btn, text="Attack", command=self._select).pack(side="left", padx=4)
        ttk.Button(btn, text="AI Default", command=self.destroy).pack(side="left", padx=4)
        self.wait_window(self)

    def _select(self) -> None:
        sel = self._listbox.curselection()
        if sel:
            self.result = self._opponents[sel[0]]
        self.destroy()


class EscalateDialog(tk.Toplevel if tk is not None else object):
    """Ask whether to escalate a marginal brawl to man-to-man."""

    def __init__(self, parent: Any, figure: Any, opponent: Any) -> None:
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title("Escalate to Man-to-Man?")
        self.resizable(False, False)
        self.result: bool = False

        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text=f"Brawl between {figure.name} and {opponent.name} "
                             f"was INDECISIVE.",
                  wraplength=350).pack(pady=(0, 8))
        ttk.Label(main, text="Escalate to man-to-man combat?",
                  font=("Helvetica", 10, "bold")).pack()

        btn = ttk.Frame(main)
        btn.pack(pady=(8, 0))
        ttk.Button(btn, text="Yes — Man-to-Man",
                   command=self._yes).pack(side="left", padx=4)
        ttk.Button(btn, text="No — Disengage",
                   command=self.destroy).pack(side="left", padx=4)
        self.wait_window(self)

    def _yes(self) -> None:
        self.result = True
        self.destroy()


class TowBarDialog(tk.Toplevel if tk is not None else object):
    """Let the human player pick which skaters grab a biker's tow bar."""

    def __init__(self, parent: Any, biker: Any, candidates: List[Any]) -> None:
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title("Tow Bar — Select Skaters")
        self.resizable(False, False)
        self.result: Optional[List[Any]] = None

        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)

        current_towing = len(getattr(biker, 'towing', []))
        max_attach = 3 - current_towing
        ttk.Label(main, text=f"{biker.name} can tow up to {max_attach} more skater(s):",
                  font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(0, 6))

        self._vars: List[tk.BooleanVar] = []
        self._candidates = candidates
        for fig in candidates:
            var = tk.BooleanVar(value=False)
            self._vars.append(var)
            ttk.Checkbutton(main, text=f"{fig.name}  SPD {fig.speed}  SKL {fig.skill}",
                            variable=var).pack(anchor="w")

        self._max = max_attach
        btn = ttk.Frame(main)
        btn.pack(pady=(8, 0))
        ttk.Button(btn, text="Attach Selected", command=self._select).pack(side="left", padx=4)
        ttk.Button(btn, text="None / AI Default", command=self._none).pack(side="left", padx=4)
        self.wait_window(self)

    def _select(self) -> None:
        chosen = [c for c, v in zip(self._candidates, self._vars) if v.get()]
        self.result = chosen[:self._max]
        self.destroy()

    def _none(self) -> None:
        self.result = []
        self.destroy()


class ScoringDialog(tk.Toplevel if tk is not None else object):
    """Ask the human player whether to attempt a scoring shot."""

    def __init__(self, parent: Any, shooter: Any,
                 modifiers: List[Tuple[str, int]]) -> None:
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title("Scoring Attempt")
        self.resizable(False, False)
        self.result: bool = True  # default to shoot

        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text=f"{shooter.name} is in the goal square!",
                  font=("Helvetica", 11, "bold")).pack(anchor="w", pady=(0, 6))

        total = sum(v for _, v in modifiers)
        ttk.Label(main, text=f"Skill: {shooter.skill}  |  Total modifier: "
                             f"{'+' if total >= 0 else ''}{total}  |  "
                             f"Target: {shooter.skill + total}",
                  font=("Courier", 10)).pack(anchor="w")

        if modifiers:
            detail = ttk.Frame(main)
            detail.pack(fill="x", pady=4)
            for name, val in modifiers:
                sign = "+" if val >= 0 else ""
                ttk.Label(detail, text=f"  {name}: {sign}{val}",
                          font=("Courier", 9), foreground="#6b7280").pack(anchor="w")

        btn = ttk.Frame(main)
        btn.pack(pady=(8, 0))
        ttk.Button(btn, text="🏀 Shoot!", command=self._shoot).pack(side="left", padx=4)
        ttk.Button(btn, text="Hold — keep circling", command=self._hold).pack(side="left", padx=4)
        self.wait_window(self)

    def _shoot(self) -> None:
        self.result = True
        self.destroy()

    def _hold(self) -> None:
        self.result = False
        self.destroy()


class PackFormationDialog(tk.Toplevel if tk is not None else object):
    """Let the human player choose which detected packs to form."""

    def __init__(self, parent: Any, packs: List[List[Any]]) -> None:
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title("Pack Formation")
        self.resizable(False, False)
        self.result: Optional[List[int]] = None

        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="Detected packs — select which to form:",
                  font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(0, 6))

        self._vars: List[tk.BooleanVar] = []
        for i, pack in enumerate(packs):
            names = ", ".join(getattr(f, 'name', '?') for f in pack)
            var = tk.BooleanVar(value=True)
            self._vars.append(var)
            ttk.Checkbutton(main, text=f"Pack {i + 1}: {names}",
                            variable=var).pack(anchor="w")

        btn = ttk.Frame(main)
        btn.pack(pady=(8, 0))
        ttk.Button(btn, text="Form Selected", command=self._select).pack(side="left", padx=4)
        ttk.Button(btn, text="No Packs", command=self._none).pack(side="left", padx=4)
        self.wait_window(self)

    def _select(self) -> None:
        self.result = [i for i, v in enumerate(self._vars) if v.get()]
        self.destroy()

    def _none(self) -> None:
        self.result = []
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

        # Human-interactive state
        self._pending_movement: Optional[dict] = None  # {figure, square, options}
        self._move_option_lookup: Dict[str, Any] = {}  # canvas item → Square
        self._interaction_mode: Optional[str] = None  # 'movement', 'tow_attach', 'tow_detach'
        self._tow_selected_biker: Optional[Any] = None

        # Tier 1 graphics state
        self._zoom_level: float = 1.0
        self._pan_offset: List[float] = [0.0, 0.0]
        self._drag_start: Optional[Tuple[float, float]] = None

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
        controls.columnconfigure(8, weight=1)

        ttk.Button(controls, text="New Match", command=self.new_match_dialog).grid(
            row=0, column=0, padx=4)
        ttk.Button(controls, text="Next Phase", command=self.next_phase).grid(
            row=0, column=1, padx=4)
        ttk.Button(controls, text="Play Turn", command=self.play_turn).grid(
            row=0, column=2, padx=4)
        ttk.Button(controls, text="Gen Teams", command=self.open_team_gen).grid(
            row=0, column=3, padx=4)

        # Human-interactive buttons
        ttk.Separator(controls, orient="vertical").grid(row=0, column=4, sticky="ns", padx=4)
        ttk.Button(controls, text="Grab Tow", command=self._start_tow_attach).grid(
            row=0, column=5, padx=2)
        ttk.Button(controls, text="Release Tow", command=self._start_tow_detach).grid(
            row=0, column=6, padx=2)

        self._mode_label = ttk.Label(controls, text=f"Mode: {self.game_mode}",
                                     font=("Helvetica", 9), foreground="#6b7280")
        self._mode_label.grid(row=0, column=7, padx=12)

        # Interaction status label
        self._interaction_var = tk.StringVar(value="")
        self._interaction_label = ttk.Label(
            controls, textvariable=self._interaction_var,
            font=("Helvetica", 9, "italic"), foreground="#f59e0b")
        self._interaction_label.grid(row=1, column=0, columnspan=7, sticky="w", pady=(2, 0))

        # Top-right: scoreboard + last phase action
        top_right = ttk.Frame(controls)
        top_right.grid(row=0, column=8, sticky="e", padx=(8, 4))
        top_right.columnconfigure(0, weight=1)

        self._top_score_var = tk.StringVar(value="")
        ttk.Label(top_right, textvariable=self._top_score_var,
                  font=("Helvetica", 10, "bold")).grid(
            row=0, column=0, sticky="e")

        self._last_action_var = tk.StringVar(value="")
        ttk.Label(top_right, textvariable=self._last_action_var,
                  font=("Helvetica", 9), foreground="#555555",
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
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        # Tier 1: zoom & pan bindings
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)       # Windows/macOS
        self.canvas.bind("<Button-4>", self._on_mouse_wheel)          # Linux scroll up
        self.canvas.bind("<Button-5>", self._on_mouse_wheel)          # Linux scroll down
        self.canvas.bind("<ButtonPress-2>", self._on_pan_start)       # Middle-click drag
        self.canvas.bind("<B2-Motion>", self._on_pan_motion)
        self.canvas.bind("<ButtonRelease-2>", self._on_pan_end)
        self.canvas.bind("<ButtonPress-3>", self._on_pan_start)       # Right-click drag
        self.canvas.bind("<B3-Motion>", self._on_pan_motion)
        self.canvas.bind("<ButtonRelease-3>", self._on_pan_end)

        # Tier 1: initialise particle system and animation manager
        self._particles = ParticleSystem(self.canvas)
        self._animator = _AnimationManager(self.canvas)

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
        self._zoom_level = 1.0
        self._pan_offset = [0.0, 0.0]

        # Install human-interactive callbacks for HvC mode
        self._install_callbacks()

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
    # Human-interactive callback installation
    # -----------------------------------------------------------------------

    def _install_callbacks(self) -> None:
        """Install or clear interactive callbacks based on game mode."""
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

    # -----------------------------------------------------------------------
    # Human-interactive callbacks (Movement Confirmation)
    # -----------------------------------------------------------------------

    def _human_movement_cb(self, figure: Any, current_square: Any,
                           options: List[tuple]) -> Optional[Any]:
        """Show movement options and let the player click to confirm.

        Returns the chosen destination ``Square`` or ``None`` to skip.
        The implementation uses a modal approach: it highlights options
        on the canvas and enters a local event loop until the player
        clicks a destination or presses Escape to skip.
        """
        if not options:
            return None

        # Store pending state and draw options
        result_holder: List[Optional[Any]] = [None]

        # Draw movement option markers the player can click
        self._draw_board()  # redraw base board
        self._draw_movement_options(figure, options, result_holder)

        # Update interaction label
        self._interaction_var.set(
            f"⟐ Click a destination for {figure.name} (SPD {figure.speed}) "
            f"or press Esc to skip"
        )

        # Wait for result — local event loop
        self._wait_for_result(result_holder)
        self._interaction_var.set("")
        return result_holder[0]

    def _draw_movement_options(self, figure: Any,
                               options: List[tuple],
                               result_holder: List) -> None:
        """Overlay clickable destination markers on the canvas."""
        self._move_option_lookup.clear()
        for square, cost in options:
            cx, cy = self._square_center(square)
            cx, cy = self._apply_transform(cx, cy)
            r = 22 * self._zoom_level
            item = self.canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                outline="#22d3ee", width=3, dash=(5, 3),
                fill="#22d3ee", stipple="gray12",
            )
            self.canvas.create_text(
                cx, cy + r + 8,
                text=str(cost), fill="#67e8f9",
                font=("Helvetica", max(7, int(9 * self._zoom_level)), "bold"),
                tags="move_cost_label",
            )
            self._move_option_lookup[str(item)] = square
            self.canvas.tag_bind(item, "<Button-1>",
                                 lambda _e, sq=square: self._resolve_movement(sq, result_holder))

        # Escape to skip
        self.canvas.bind("<Escape>",
                         lambda _e: self._resolve_movement(None, result_holder))
        self.bind("<Escape>",
                  lambda _e: self._resolve_movement(None, result_holder))

    def _resolve_movement(self, square: Optional[Any],
                          result_holder: List) -> None:
        """Set the result and break the local event loop."""
        result_holder[0] = square
        result_holder.append("done")  # sentinel to break wait loop

    def _wait_for_result(self, result_holder: List) -> None:
        """Spin the Tk event loop until result_holder has > 1 item."""
        while len(result_holder) <= 1:
            self.update()

    # -----------------------------------------------------------------------
    # Human-interactive callbacks (Click-to-target combat)
    # -----------------------------------------------------------------------

    def _human_combat_target_cb(self, attacker: Any,
                                opponents: List[Any]) -> Optional[Any]:
        """Open a dialog for the player to pick a combat target."""
        if not opponents:
            return None
        dlg = CombatTargetDialog(self, attacker, opponents)
        return dlg.result

    def _human_escalate_cb(self, figure: Any, opponent: Any) -> bool:
        """Ask whether to escalate a marginal brawl to man-to-man."""
        dlg = EscalateDialog(self, figure, opponent)
        return dlg.result

    # -----------------------------------------------------------------------
    # Human-interactive callbacks (Tow bar controls)
    # -----------------------------------------------------------------------

    def _human_tow_bar_cb(self, biker: Any,
                          candidates: List[Any]) -> Optional[List[Any]]:
        """Open a dialog for the player to pick skaters for tow bar."""
        if not candidates:
            return []
        dlg = TowBarDialog(self, biker, candidates)
        return dlg.result

    def _start_tow_attach(self) -> None:
        """GUI button: begin tow-bar attach interaction.

        The player first clicks a biker (home team), then a skater.
        """
        if self.game_mode != MODE_HVC:
            messagebox.showinfo("Tow Bar", "Tow bar controls are only available in Human vs Computer mode.")
            return
        self._interaction_mode = "tow_attach"
        self._interaction_var.set("🔗 Click a HOME biker to attach a tow bar…")

    def _start_tow_detach(self) -> None:
        """GUI button: release a tow bar by clicking a towed skater."""
        if self.game_mode != MODE_HVC:
            messagebox.showinfo("Tow Bar", "Tow bar controls are only available in Human vs Computer mode.")
            return
        self._interaction_mode = "tow_detach"
        self._interaction_var.set("✂ Click a towed HOME skater to release tow bar…")

    def _handle_tow_click(self, figure: Any) -> None:
        """Process clicks during tow-bar interaction modes."""
        if self._interaction_mode == "tow_attach":
            if self._tow_selected_biker is None:
                # First click: select biker
                if not getattr(figure, 'is_biker', False):
                    self._interaction_var.set("⚠ Please click a BIKER first.")
                    return
                if getattr(figure, 'team', None) != TeamSide.HOME:
                    self._interaction_var.set("⚠ Please click a HOME biker.")
                    return
                self._tow_selected_biker = figure
                self._interaction_var.set(
                    f"🔗 Now click a skater to attach to {figure.name}'s tow bar…"
                )
            else:
                # Second click: select skater to attach
                if not getattr(figure, 'is_skater', False):
                    self._interaction_var.set("⚠ Please click a SKATER.")
                    return
                if getattr(figure, 'team', None) != TeamSide.HOME:
                    self._interaction_var.set("⚠ Please click a HOME skater.")
                    return
                msgs = self.game.attach_tow_bar(self._tow_selected_biker, figure)
                for m in msgs:
                    self.game.log.append(m)
                self._tow_selected_biker = None
                self._interaction_mode = None
                self._interaction_var.set("")
                self.refresh()

        elif self._interaction_mode == "tow_detach":
            if not getattr(figure, 'is_towed', False):
                self._interaction_var.set("⚠ That figure is not being towed.")
                return
            if getattr(figure, 'team', None) != TeamSide.HOME:
                self._interaction_var.set("⚠ Please click a HOME figure.")
                return
            msgs = self.game.detach_tow_bar(figure)
            for m in msgs:
                self.game.log.append(m)
            self._interaction_mode = None
            self._interaction_var.set("")
            self.refresh()

    # -----------------------------------------------------------------------
    # Human-interactive callbacks (Scoring shot control)
    # -----------------------------------------------------------------------

    def _human_scoring_cb(self, shooter: Any,
                          modifiers: List[Tuple[str, int]]) -> bool:
        """Open a dialog for the player to decide whether to shoot."""
        dlg = ScoringDialog(self, shooter, modifiers)
        return dlg.result

    # -----------------------------------------------------------------------
    # Human-interactive callbacks (Pack formation builder)
    # -----------------------------------------------------------------------

    def _human_pack_cb(self, packs: List[List[Any]]) -> Optional[List[int]]:
        """Open a dialog for the player to choose which packs to form."""
        if not packs:
            return []
        dlg = PackFormationDialog(self, packs)
        return dlg.result

    # -----------------------------------------------------------------------
    # Canvas click dispatcher
    # -----------------------------------------------------------------------

    def _on_canvas_click(self, event: "tk.Event[Any]") -> None:
        """Dispatch left-click on the canvas."""
        # If in tow interaction mode, ignore non-figure clicks
        if self._interaction_mode in ("tow_attach", "tow_detach"):
            # Check if clicked a figure
            item = self.canvas.find_closest(event.x, event.y)
            if item:
                figure = self.figure_lookup.get(str(item[0]))
                if figure is not None:
                    self._handle_tow_click(figure)
                    return
            # Click on empty space cancels tow mode
            self._interaction_mode = None
            self._tow_selected_biker = None
            self._interaction_var.set("")
            return
        # Default: clear selection
        self.clear_selection()

    # -----------------------------------------------------------------------
    # Tier 1 graphics: Zoom & Pan
    # -----------------------------------------------------------------------

    def _on_mouse_wheel(self, event: "tk.Event[Any]") -> None:
        """Zoom in/out on mouse wheel."""
        if hasattr(event, 'delta'):
            # Windows/macOS
            factor = 1.1 if event.delta > 0 else 0.9
        elif event.num == 4:
            factor = 1.1
        else:
            factor = 0.9
        new_zoom = max(0.3, min(3.0, self._zoom_level * factor))
        if new_zoom != self._zoom_level:
            self._zoom_level = new_zoom
            self._draw_board()

    def _on_pan_start(self, event: "tk.Event[Any]") -> None:
        self._drag_start = (event.x, event.y)

    def _on_pan_motion(self, event: "tk.Event[Any]") -> None:
        if self._drag_start is None:
            return
        dx = event.x - self._drag_start[0]
        dy = event.y - self._drag_start[1]
        self._pan_offset[0] += dx
        self._pan_offset[1] += dy
        self._drag_start = (event.x, event.y)
        self._draw_board()

    def _on_pan_end(self, _event: "tk.Event[Any]") -> None:
        self._drag_start = None

    def _apply_transform(self, x: float, y: float) -> Tuple[float, float]:
        """Apply zoom and pan to a board coordinate."""
        cx, cy = 430, 380  # board centre
        tx = (x - cx) * self._zoom_level + cx + self._pan_offset[0]
        ty = (y - cy) * self._zoom_level + cy + self._pan_offset[1]
        return tx, ty

    # -----------------------------------------------------------------------
    # Tier 1 graphics: particle effect helpers
    # -----------------------------------------------------------------------

    def _emit_cannon_particles(self) -> None:
        """Fire particles from the cannon area."""
        cx, cy = self._apply_transform(430, 380)
        self._particles.emit(cx, cy - 300 * self._zoom_level,
                             PARTICLE_COUNT_CANNON,
                             colors=["#ff4500", "#ff8c00", "#ffd700", "#ffffff"],
                             speed_range=(2.0, 6.0))

    def _emit_crash_particles(self, x: float, y: float) -> None:
        """Emit crash/impact particles at a board position."""
        tx, ty = self._apply_transform(x, y)
        self._particles.emit(tx, ty, PARTICLE_COUNT_CRASH,
                             colors=["#ef4444", "#f97316", "#fbbf24"],
                             speed_range=(1.0, 3.0),
                             size_range=(1.5, 4.0))

    def _emit_goal_particles(self) -> None:
        """Celebrate a goal with confetti particles."""
        cx, cy = self._apply_transform(430, 380)
        self._particles.emit(cx, cy, PARTICLE_COUNT_GOAL,
                             colors=["#22c55e", "#3b82f6", "#f59e0b",
                                     "#ec4899", "#ffffff"],
                             speed_range=(3.0, 8.0),
                             size_range=(2.0, 6.0),
                             lifetime=1000)

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

    def _announce_game_over(self) -> None:
        """Show a game-over popup with the final result and scores."""
        result = self.game.match_result()
        scores = self.game.snapshot()["scores"]
        score_text = " | ".join(f"{name}: {score}" for name, score in scores.items())
        if result == "Draw":
            messagebox.showinfo("Game Over", f"Match ended in a draw!\n\n{score_text}")
        else:
            messagebox.showinfo("Game Over", f"Winner: {result}!\n\n{score_text}")

    def _check_and_announce_game_over(self) -> None:
        """If the game just ended, show the game-over popup."""
        if self.game.game_over:
            self._announce_game_over()

    def _warn_already_over(self) -> bool:
        """Warn the user if the match is already finished. Returns True if over."""
        if self.game.game_over:
            messagebox.showinfo("Game Over", "The match has ended. Start a new match.")
            return True
        return False

    def next_phase(self) -> None:
        if self._warn_already_over():
            return
        old_scores = dict(self.game.snapshot()["scores"])
        result = self.game.advance_phase()
        self.refresh()
        self._trigger_phase_effects(result, old_scores)
        self._check_and_announce_game_over()

    def play_turn(self) -> None:
        if self._warn_already_over():
            return
        old_scores = dict(self.game.snapshot()["scores"])
        results = self.game.play_turn()
        self.refresh()
        for result in results:
            self._trigger_phase_effects(result, old_scores)
        self._check_and_announce_game_over()

    def _trigger_phase_effects(self, result: Any, old_scores: Dict[str, int]) -> None:
        """Emit Tier 1 particle effects based on phase outcomes."""
        if result is None:
            return
        for msg in result.messages:
            lower = msg.lower()
            if "cannon" in lower and "fire" in lower:
                self._emit_cannon_particles()
            if "crashes" in lower or "thrown" in lower or "falls" in lower:
                # Find a crash position for particles
                for fig in self.game.all_figures():
                    if fig.name in msg:
                        sq = self.game.board.find_square_of_figure(fig)
                        if sq is not None:
                            x, y = self._square_center(sq)
                            self._emit_crash_particles(x, y)
                        break
        # Goal celebration
        new_scores = self.game.snapshot()["scores"]
        for name in new_scores:
            if new_scores.get(name, 0) > old_scores.get(name, 0):
                self._emit_goal_particles()
                break

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
        self._move_option_lookup.clear()
        self._draw_track_texture()
        self._draw_squares()
        self._draw_highlights()
        self._draw_figures()
        self._draw_ball()
        self._draw_canvas_scoreboard()

    # -----------------------------------------------------------------------
    # Tier 1 graphics: Track texture
    # -----------------------------------------------------------------------

    def _draw_track_texture(self) -> None:
        """Draw a pre-rendered background for the inclined circular track.

        Creates concentric shaded rings to simulate concrete banking with
        painted lane lines and a crowd gradient behind the outer wall.
        """
        bcx, bcy = 430, 380
        cx, cy = self._apply_transform(bcx, bcy)
        z = self._zoom_level

        # Crowd / stands gradient (beyond cannon track)
        for i in range(5):
            r = (360 + i * 15) * z
            shade = min(255, 25 + i * 8)
            color = f"#{shade:02x}{shade // 2:02x}{shade // 3:02x}"
            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                    fill=color, outline="", width=0)

        # Ring shading (concrete banking — darker = higher incline)
        ring_fills = {
            Ring.CANNON: "#2d3748",
            Ring.UPPER: "#1a2332",
            Ring.MIDDLE: "#1e293b",
            Ring.LOWER: "#1f2d3d",
            Ring.FLOOR: "#1c2431",
        }
        for ring in [Ring.CANNON, Ring.UPPER, Ring.MIDDLE, Ring.LOWER, Ring.FLOOR]:
            inner, outer = RING_RADII[ring]
            ri = inner * z
            ro = outer * z
            self.canvas.create_oval(cx - ro, cy - ro, cx + ro, cy + ro,
                                    fill=ring_fills[ring], outline="")

        # Central area
        floor_inner = RING_RADII[Ring.FLOOR][0] * z
        self.canvas.create_oval(cx - floor_inner, cy - floor_inner,
                                cx + floor_inner, cy + floor_inner,
                                fill="#0f172a", outline="#374151", width=1)

        # Painted lane divider lines
        for ring in Ring:
            _, outer = RING_RADII[ring]
            r = outer * z
            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                    fill="", outline="#374151", width=1, dash=(3, 6))

    def _draw_canvas_scoreboard(self) -> None:
        """Draw a score/clock overlay in the top-right corner of the canvas."""
        snapshot = self.game.snapshot()
        scores = snapshot["scores"]
        names = list(scores.keys())
        score_parts = [f"{name}: {scores[name]}" for name in names]
        score_text = "  |  ".join(score_parts)
        clock_text = (
            f"Period {snapshot['period']}  ·  "
            f"Turn {snapshot['turn']}  ·  "
            f"{snapshot['time_remaining']}:00"
        )
        if self.game.game_over:
            result = self.game.match_result()
            status_text = "DRAW" if result == "Draw" else f"WINNER: {result}"
        else:
            status_text = ""

        lines = 2 + (1 if status_text else 0)
        box_h = lines * _SCOREBOARD_LINE_HEIGHT + _SCOREBOARD_PADDING * 2

        right = _SCOREBOARD_RIGHT
        top = _SCOREBOARD_TOP
        box_w = _SCOREBOARD_WIDTH

        self.canvas.create_rectangle(
            right - box_w, top - _SCOREBOARD_PADDING, right + 4, top + box_h,
            fill="#1f2937", outline="#6b7280", width=1,
        )
        cx = right - box_w // 2
        self.canvas.create_text(
            cx, top + _SCOREBOARD_LINE_HEIGHT * 0 + 8,
            text=score_text, fill="#f9fafb",
            font=("Helvetica", 11, "bold"), anchor="center",
        )
        self.canvas.create_text(
            cx, top + _SCOREBOARD_LINE_HEIGHT * 1 + 8,
            text=clock_text, fill="#9ca3af",
            font=("Helvetica", 9), anchor="center",
        )
        if status_text:
            self.canvas.create_text(
                cx, top + _SCOREBOARD_LINE_HEIGHT * 2 + 8,
                text=status_text, fill="#fbbf24",
                font=("Helvetica", 10, "bold"), anchor="center",
            )

    def _draw_squares(self) -> None:
        cx, cy = 430, 380
        z = self._zoom_level
        for sector_index, sector in enumerate(self.game.board.sectors):
            base_start = -math.pi / 2 + sector_index * (2 * math.pi / 12)
            sector_span = 2 * math.pi / 12
            for ring in Ring:
                inner_radius, outer_radius = RING_RADII[ring]
                square_count = SQUARES_PER_RING[ring]
                for position in range(square_count):
                    start = base_start + (sector_span / square_count) * position
                    end = start + (sector_span / square_count)
                    polygon = self._wedge_polygon_transformed(
                        cx, cy, inner_radius * z, outer_radius * z, start, end)
                    fill = "#1f2937" if ring != Ring.CANNON else "#374151"
                    outline = "#4b5563"
                    width = 1
                    square = self.game.board.get_square(sector_index, ring, position)
                    if square.is_goal:
                        fill = "#14532d" if square.goal_side.value == "home" else "#7f1d1d"
                    if sector_index == self.game.current_initiative_sector:
                        outline = "#93c5fd"
                        width = 2
                    self.canvas.create_polygon(polygon, fill=fill, outline=outline,
                                               width=width, stipple="gray50")
            mid_angle = base_start + sector_span / 2
            lx = cx + math.cos(mid_angle) * 355
            ly = cy + math.sin(mid_angle) * 355
            lx, ly = self._apply_transform(lx, ly)
            self.canvas.create_text(
                lx, ly,
                text=sector.name,
                fill="#e5e7eb",
                font=("Helvetica", max(7, int(10 * z)), "bold"),
            )

    def _draw_highlights(self) -> None:
        z = self._zoom_level
        for figure in self.game.all_figures():
            square = self.game.board.find_square_of_figure(figure)
            if square is None:
                continue
            cx, cy = self._square_center(square)
            cx, cy = self._apply_transform(cx, cy)
            r20 = 20 * z
            r24 = 24 * z
            r6 = 6 * z
            if figure.needs_stand_up:
                self.canvas.create_oval(cx - r20, cy - r20, cx + r20, cy + r20,
                                        outline="#f59e0b", width=max(1, int(3 * z)))
            if figure.status == FigureStatus.MAN_TO_MAN:
                self.canvas.create_rectangle(cx - r24, cy - r24, cx + r24, cy + r24,
                                             outline="#a855f7", width=max(1, int(2 * z)))
            if figure.has_moved:
                self.canvas.create_oval(cx - r6, cy - r6, cx + r6, cy + r6,
                                        fill="#fef08a", outline="")
            # Tow bar indicator (E9-E14) — green line showing tow connection
            if getattr(figure, 'is_towed', False):
                biker = getattr(figure, 'towed_by', None)
                if biker is not None:
                    bsq = self.game.board.find_square_of_figure(biker)
                    if bsq is not None:
                        bx, by = self._square_center(bsq)
                        bx, by = self._apply_transform(bx, by)
                        self.canvas.create_line(cx, cy, bx, by,
                                                fill="#22c55e", width=max(1, int(2 * z)),
                                                dash=(4, 2))
                else:
                    self.canvas.create_line(cx, cy, cx, cy - 12 * z,
                                            fill="#22c55e", width=max(1, int(2 * z)))
            # Endurance warning (H3)
            endurance_used = getattr(figure, 'endurance_used', 0)
            max_e = getattr(figure, 'base_toughness', 7) + 3
            if endurance_used > max_e:
                self.canvas.create_text(cx + 14 * z, cy - 14 * z, text="E!",
                                        fill="#ef4444",
                                        font=("Helvetica", max(6, int(8 * z)), "bold"))

        for sector in self.game.board.sectors:
            for square in sector.all_squares():
                if not square.has_obstacle and not square.is_on_fire:
                    continue
                cx, cy = self._square_center(square)
                cx, cy = self._apply_transform(cx, cy)
                marker = "⚠" if square.has_obstacle else "🔥"
                color = "#fbbf24" if square.has_obstacle else "#ef4444"
                self.canvas.create_text(cx, cy, text=marker, fill=color,
                                        font=("Helvetica", max(8, int(14 * z)), "bold"))

        if self.selected_figure is None:
            return

        for square, cost in self.game.movement_options_with_costs(self.selected_figure):
            cx, cy = self._square_center(square)
            cx, cy = self._apply_transform(cx, cy)
            r26 = 26 * z
            self.canvas.create_oval(cx - r26, cy - r26, cx + r26, cy + r26,
                                    outline="#22d3ee", width=max(1, int(2 * z)), dash=(4, 3))
            self.canvas.create_text(cx, cy + 22 * z, text=str(cost), fill="#67e8f9",
                                    font=("Helvetica", max(7, int(9 * z)), "bold"))

    def _draw_figures(self) -> None:
        """Draw figures as Tier 1 procedural sprites with type-specific shapes."""
        z = self._zoom_level
        for figure in self.game.all_figures():
            square = self.game.board.find_square_of_figure(figure)
            if square is None:
                continue
            x, y = self._slot_center(square, figure.slot_index or 0)
            x, y = self._apply_transform(x, y)

            figure_type = figure.figure_type.value
            team_side = figure.team.value
            fallback_label = figure_type[0].upper() if figure_type else "?"
            label = FIGURE_LABELS.get(figure_type, fallback_label)

            # Choose sprite colours based on team and type
            if team_side == "home":
                palette = SPRITE_COLORS.get(figure_type, {"fill": "#3b82f6", "accent": "#1e3a5f"})
            else:
                palette = SPRITE_COLORS_VISITOR.get(figure_type,
                                                     {"fill": "#ef4444", "accent": "#7f1d1d"})
            fill = palette["fill"]
            accent = palette["accent"]

            # Show injured/fallen with dim colours
            if figure.needs_stand_up or figure.status in (
                    FigureStatus.UNCONSCIOUS, FigureStatus.DEAD):
                fill = "#4b5563"
                accent = "#374151"

            r = 14 * z
            sr = 10 * z  # inner shape radius

            # Draw type-specific sprite shape
            if figure_type == "biker":
                # Diamond / rhombus shape for bikers
                pts = [x, y - r, x + r, y, x, y + r, x - r, y]
                item = self.canvas.create_polygon(
                    pts, fill=fill, outline="white", width=max(1, int(2 * z)))
                # Inner accent diamond
                self.canvas.create_polygon(
                    [x, y - sr, x + sr, y, x, y + sr, x - sr, y],
                    fill=accent, outline="")
            elif figure_type == "catcher":
                # Rounded hexagon for catchers (approximated by oval + lines)
                item = self.canvas.create_oval(
                    x - r, y - r * 0.8, x + r, y + r * 0.8,
                    fill=fill, outline="white", width=max(1, int(2 * z)))
                # Catch mitt indicator — small arcs
                self.canvas.create_arc(
                    x - r * 0.5, y - r * 0.5, x + r * 0.5, y + r * 0.5,
                    start=0, extent=180, fill=accent, outline="")
            elif figure_type == "speeder":
                # Triangle / arrow shape for speeders
                pts = [x, y - r, x + r * 0.9, y + r * 0.7, x - r * 0.9, y + r * 0.7]
                item = self.canvas.create_polygon(
                    pts, fill=fill, outline="white", width=max(1, int(2 * z)))
                # Speed lines
                self.canvas.create_line(x - r * 0.6, y + r * 0.3,
                                        x + r * 0.6, y + r * 0.3,
                                        fill=accent, width=max(1, int(z)))
            else:
                # Circle for bruisers (default)
                item = self.canvas.create_oval(
                    x - r, y - r, x + r, y + r,
                    fill=fill, outline="white", width=max(1, int(2 * z)))
                # Inner accent circle
                self.canvas.create_oval(
                    x - sr * 0.6, y - sr * 0.6, x + sr * 0.6, y + sr * 0.6,
                    fill=accent, outline="")

            # Type label
            self.canvas.create_text(x, y, text=label, fill="white",
                                    font=("Helvetica", max(7, int(10 * z)), "bold"))

            # Ball indicator — orange dot
            if figure.has_ball:
                br = 6 * z
                self.canvas.create_oval(x + r * 0.6, y - r,
                                        x + r * 0.6 + br * 2, y - r + br * 2,
                                        fill="#f97316", outline="#fff7ed",
                                        width=max(1, int(z)))

            self.figure_lookup[str(item)] = figure
            self.canvas.tag_bind(item, "<Button-1>", self._on_figure_click)

    def _draw_ball(self) -> None:
        z = self._zoom_level
        if self.game.ball.state.value == "not_in_play":
            return
        if self.game.ball.carrier is not None:
            square = self.game.board.find_square_of_figure(self.game.ball.carrier)
            if square is None:
                return
            x, y = self._slot_center(square, self.game.ball.carrier.slot_index or 0)
            x, y = self._apply_transform(x, y)
            x += 18 * z
            y -= 18 * z
        else:
            square = self.game.board.get_square(
                self.game.ball.sector_index,
                self.game.ball.ring,
                self.game.ball.position,
            )
            x, y = self._square_center(square)
            x, y = self._apply_transform(x, y)
        # Temperature colour + glow
        temp_colors = {
            "very_hot": "#ff2020",
            "hot": "#ff8800",
            "warm": "#fbbf24",
            "cool": "#60a5fa",
        }
        glow_colors = {
            "very_hot": "#ff6060",
            "hot": "#ffaa44",
            "warm": "#fde68a",
            "cool": "#93c5fd",
        }
        ball_color = temp_colors.get(self.game.ball.temperature.value, "#f97316")
        glow_color = glow_colors.get(self.game.ball.temperature.value, "#fbbf24")
        r = 8 * z
        # Glow ring (Tier 1 enhancement)
        gr = r * 1.8
        self.canvas.create_oval(x - gr, y - gr, x + gr, y + gr,
                                fill="", outline=glow_color, width=max(1, int(2 * z)),
                                dash=(2, 2))
        self.canvas.create_oval(x - r, y - r, x + r, y + r,
                                fill=ball_color, outline="#fff7ed",
                                width=max(1, int(2 * z)))

    def _on_figure_click(self, event: "tk.Event[Any]") -> None:
        item = self.canvas.find_withtag("current")
        if not item:
            return
        figure = self.figure_lookup.get(str(item[0]))
        if figure is None:
            return
        # If in tow interaction mode, handle that first
        if self._interaction_mode in ("tow_attach", "tow_detach"):
            self._handle_tow_click(figure)
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

    def _wedge_polygon_transformed(
        self,
        cx: float,
        cy: float,
        inner_radius: float,
        outer_radius: float,
        start: float,
        end: float,
    ) -> list[float]:
        """Like _wedge_polygon but applies zoom/pan transform."""
        raw = [
            (cx + math.cos(start) * inner_radius, cy + math.sin(start) * inner_radius),
            (cx + math.cos(start) * outer_radius, cy + math.sin(start) * outer_radius),
            (cx + math.cos(end) * outer_radius, cy + math.sin(end) * outer_radius),
            (cx + math.cos(end) * inner_radius, cy + math.sin(end) * inner_radius),
        ]
        result: list[float] = []
        for rx, ry in raw:
            tx, ty = self._apply_transform(rx, ry)
            result.extend([tx, ty])
        return result


def launch() -> None:
    if tk is None:  # pragma: no cover - environment dependent
        raise RuntimeError("tkinter is not available in this environment") from _TK_ERROR
    app = RoozerballApp()
    app.mainloop()


if __name__ == "__main__":
    launch()
