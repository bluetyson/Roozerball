#!/usr/bin/env python3
"""Godot ↔ Python engine bridge.

Communicates with the Godot front-end via JSON files:
  --cmd-file   : Godot writes commands here (the bridge polls it)
  --state-file : Bridge writes game state here after each command
  --error-file : Bridge writes crash details here on startup failure

Run by the Godot ``GameBridge`` autoload, or manually for testing::

    python roozerball/godot_bridge.py --cmd-file /tmp/cmd.json --state-file /tmp/state.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure the repo root is on sys.path so ``roozerball.engine`` is importable.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


class GodotBridge:
    """Wraps a :class:`Game` and serialises its state as JSON."""

    def __init__(self) -> None:
        self.game = Game()
        self._seq = 0  # Sequence counter so Godot can detect changes.

    # ── command dispatch ─────────────────────────────────────────────

    def handle_command(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Process one command dictionary and return the updated state."""
        action = cmd.get("action", "")
        phase_result: Optional[Dict[str, Any]] = None

        if action == "advance_phase":
            result = self.game.advance_phase()
            phase_result = self._serialise_phase_result(result)

        elif action == "play_turn":
            results = self.game.play_turn()
            phase_result = {
                "phases": [self._serialise_phase_result(r) for r in results],
            }

        elif action == "new_game":
            home = cmd.get("home", "Home")
            visitor = cmd.get("visitor", "Visitor")
            self.game = Game(home, visitor)

        elif action == "board_state":
            pass  # Just return the current full state.

        self._seq += 1
        state = self._full_state()
        if phase_result is not None:
            state["phase_result"] = phase_result
        return state

    # ── serialisation ────────────────────────────────────────────────

    def _full_state(self) -> Dict[str, Any]:
        """Return the complete game state as a JSON-friendly dict."""
        snap = self.game.snapshot()
        snap["_seq"] = self._seq
        snap["game_over"] = self.game.game_over

        # Scores (already in snapshot but let's be explicit).
        snap["scores"] = {
            self.game.home_team.name: self.game.home_team.score,
            self.game.visitor_team.name: self.game.visitor_team.score,
        }

        # Full board: figures per square.
        snap["board"] = self._serialise_board()

        # Team rosters.
        snap["home_team"] = self._serialise_team(self.game.home_team)
        snap["visitor_team"] = self._serialise_team(self.game.visitor_team)

        # Penalty boxes.
        snap["penalty_box"] = {
            "home": [self._serialise_figure(f) for f in self.game.home_team.penalty_box],
            "visitor": [self._serialise_figure(f) for f in self.game.visitor_team.penalty_box],
        }

        # Log.
        snap["log"] = list(self.game.log[-60:])

        return snap

    def _serialise_board(self) -> List[Dict[str, Any]]:
        """Return a flat list of occupied squares with their figures."""
        entries: List[Dict[str, Any]] = []
        board = self.game.board
        for sector in board.sectors:
            for ring in Ring:
                if ring == Ring.CANNON:
                    continue  # Cannon track is internal.
                for sq in sector.rings.get(ring, []):
                    figs = sq.figures_in_square()
                    entry: Dict[str, Any] = {
                        "sector": sector.index,
                        "sector_name": sector.name,
                        "ring": ring.name.lower(),
                        "ring_value": ring.value,
                        "position": sq.position,
                        "is_goal": sq.is_goal,
                        "goal_side": sq.goal_side.value if sq.goal_side else None,
                        "is_on_fire": sq.is_on_fire,
                        "has_obstacle": sq.is_obstacle_square(),
                        "controlling_team": sq.controlling_team().value if sq.controlling_team() else None,
                        "figures": [self._serialise_figure(f) for f in figs],
                    }
                    entries.append(entry)
        return entries

    def _serialise_figure(self, fig: Any) -> Dict[str, Any]:
        """Serialise a single figure to JSON-friendly dict."""
        return {
            "name": fig.name,
            "type": fig.figure_type.value,
            "team": fig.team.value if isinstance(fig.team, TeamSide) else str(fig.team),
            "status": fig.status.value,
            "speed": fig.speed,
            "skill": fig.skill,
            "combat": fig.combat,
            "toughness": fig.toughness,
            "has_ball": getattr(fig, "has_ball", False),
            "can_score": getattr(fig, "can_score", False),
            "sector_index": fig.sector_index,
            "ring": fig.ring.name.lower() if fig.ring is not None else None,
            "ring_value": fig.ring.value if fig.ring is not None else None,
            "square_position": fig.square_position,
            "slot_index": fig.slot_index,
            "laps_completed": getattr(fig, "laps_completed", 0),
            "injuries": list(getattr(fig, "injuries", [])),
            "penalty_count": getattr(fig, "penalty_count", 0),
            "is_towed": getattr(fig, "is_towed", False),
            "man_to_man_partner": getattr(
                getattr(fig, "man_to_man_partner", None), "name", None
            ),
        }

    def _serialise_team(self, team: Any) -> Dict[str, Any]:
        return {
            "name": team.name,
            "side": team.side.value,
            "score": team.score,
            "active": [self._serialise_figure(f) for f in team.active_figures],
            "bench": [self._serialise_figure(f) for f in team.bench],
            "injured_out": [self._serialise_figure(f) for f in team.injured_out],
        }

    @staticmethod
    def _serialise_phase_result(result: Any) -> Dict[str, Any]:
        return {
            "phase": result.phase.value,
            "messages": list(result.messages),
        }


# ── file-based event loop ────────────────────────────────────────────

def run_file_bridge(cmd_path: str, state_path: str, *, error_path: str = "") -> None:
    """Poll *cmd_path* for commands, write responses to *state_path*."""
    import traceback as _traceback

    try:
        # Import engine modules here (inside try/except) so that any
        # ImportError or other startup failure is caught and written to the
        # state file.  Godot reads that file before checking the process exit
        # code, so this ensures a human-readable error is always displayed
        # instead of the generic "process exited unexpectedly" message.
        global BallState, FigureStatus, FigureType, Phase, Ring, TeamSide
        global SECTORS, SQUARES_PER_RING, Game
        from roozerball.engine.constants import (
            BallState,
            FigureStatus,
            FigureType,
            Phase,
            Ring,
            TeamSide,
            SECTORS,
            SQUARES_PER_RING,
        )
        from roozerball.engine.game import Game

        bridge = GodotBridge()
        # Write initial state so Godot knows the engine is ready.
        _write_json(state_path, bridge._full_state())
    except Exception as exc:  # noqa: BLE001
        tb_text = _traceback.format_exc()
        # Write an error payload so Godot can display the real Python traceback.
        _write_json(state_path, {
            "_startup_error": str(exc),
            "_startup_traceback": tb_text,
        })
        # Also write to the dedicated error file for belt-and-suspenders.
        if error_path:
            _write_error_log(error_path, tb_text)
        raise

    last_mtime: float = 0.0
    while True:
        try:
            if os.path.exists(cmd_path):
                mtime = os.path.getmtime(cmd_path)
                if mtime > last_mtime:
                    last_mtime = mtime
                    with open(cmd_path, "r", encoding="utf-8") as fh:
                        raw = fh.read().strip()
                    if raw:
                        cmd = json.loads(raw)
                        result = bridge.handle_command(cmd)
                        _write_json(state_path, result)
            time.sleep(0.02)  # 50 Hz poll
        except KeyboardInterrupt:
            break
        except json.JSONDecodeError:
            continue  # Partial write; retry next tick.
        except Exception as exc:  # noqa: BLE001 – keep bridge alive
            err_state = bridge._full_state()
            err_state["_error"] = str(exc)
            _write_json(state_path, err_state)


def _write_json(path: str, data: Dict[str, Any]) -> None:
    # Ensure the target directory exists (Godot user-data dir may not exist yet).
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    os.replace(tmp, path)


# ── CLI entry point ──────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Roozerball Godot ↔ Python bridge")
    parser.add_argument("--cmd-file", required=True, help="Path Godot writes commands to")
    parser.add_argument("--state-file", required=True, help="Path bridge writes state to")
    parser.add_argument(
        "--error-file",
        default="",
        help="Path for crash/error details (Godot reads this on failure)",
    )
    args = parser.parse_args()
    run_file_bridge(args.cmd_file, args.state_file, error_path=args.error_file)


def _write_error_log(error_path: str, text: str) -> None:
    """Best-effort write of *text* to *error_path*."""
    try:
        parent = os.path.dirname(error_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(error_path, "w", encoding="utf-8") as fh:
            fh.write(text)
    except Exception:  # noqa: BLE001 – last-resort handler; must not raise
        pass


if __name__ == "__main__":
    # ------------------------------------------------------------------
    # Top-level error wrapper.
    #
    # OS.create_process() in Godot gives us no access to Python's stderr,
    # so if the process crashes before run_file_bridge() writes its error
    # payload (e.g. bad CLI args, script-level SyntaxError, or a failure
    # inside _write_json itself) the error is completely invisible.
    #
    # This block catches *everything* and writes the traceback to both
    # the --error-file (always) and the --state-file (best-effort) so
    # Godot can display the real cause instead of "process exited
    # unexpectedly".
    # ------------------------------------------------------------------

    # Peek at argv to find file paths before argparse runs (argparse
    # itself might fail, so we can't rely on it).
    _state_path: Optional[str] = None
    _error_path: Optional[str] = None
    for _i, _arg in enumerate(sys.argv):
        if _arg == "--state-file" and _i + 1 < len(sys.argv):
            _state_path = sys.argv[_i + 1]
        elif _arg == "--error-file" and _i + 1 < len(sys.argv):
            _error_path = sys.argv[_i + 1]

    # If no explicit --error-file, derive one from --state-file.
    if not _error_path and _state_path:
        _error_path = _state_path + ".error"

    # Redirect stderr to the error file so that even Python's own
    # unhandled-exception output (which normally goes to stderr) is
    # captured for Godot to read.
    # The file handle is intentionally never closed — it replaces stderr
    # for the remaining lifetime of the process.
    if _error_path:
        try:
            _err_dir = os.path.dirname(_error_path)
            if _err_dir:
                os.makedirs(_err_dir, exist_ok=True)
            sys.stderr = open(_error_path, "w", encoding="utf-8")  # noqa: SIM115
        except Exception:  # noqa: BLE001
            pass  # Fall back to normal stderr.

    try:
        main()
    except SystemExit:
        raise  # Let argparse --help / error exits propagate normally.
    except Exception:
        import traceback as _tb
        _full_tb = _tb.format_exc()

        # 1. Write to the dedicated error file.
        if _error_path:
            _write_error_log(_error_path, _full_tb)

        # 2. Also try to write an error payload to the state file so the
        #    existing _poll_for_ready() logic in game_bridge.gd picks it up.
        if _state_path:
            try:
                _lines = _full_tb.splitlines() if _full_tb else []
                _write_json(_state_path, {
                    "_startup_error": _lines[-1] if _lines else "unknown",
                    "_startup_traceback": _full_tb,
                })
            except Exception:  # noqa: BLE001
                pass

        # Re-raise so the process exits with a non-zero code.
        raise
