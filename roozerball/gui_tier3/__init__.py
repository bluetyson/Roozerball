"""Roozerball Tier 3 GUI — Enhanced Pygame with scene-graph architecture.

Key Tier 3 enhancements over Tier 2:
  * Scene-graph node system — figures, ball, markers, and UI as individual nodes
  * Radial grid with per-tile incline gradients and glow effects
  * Enhanced animations — smooth interpolation, run cycles, combat sequences
  * Shader-like effects — ball heat glow, speed lines, goal-flash, ring gradients
  * Advanced particle system — trails, motorcycle exhaust, confetti, dust clouds
  * Themed UI — rounded panels, animated transitions, dice-roll popups
  * Isometric perspective option — pseudo-3D banked track view
"""

__all__ = ["launch", "Tier3App"]


def __getattr__(name: str):
    if name in {"launch", "Tier3App"}:
        from roozerball.gui_tier3.app import Tier3App, launch

        return {"launch": launch, "Tier3App": Tier3App}[name]
    raise AttributeError(name)
