"""Roozerball Tier 4 GUI — Realistic Pygame with post-processing effects.

Key Tier 4 enhancements over Tier 3:
  * Procedural track textures — noise-based surface grain, lane markings, scuff marks
  * Post-processing pipeline — bloom/glow, vignette, screen shake, heat distortion
  * Multi-source dynamic lighting — stadium floodlights with soft penumbra shadows
  * Crowd silhouettes — animated spectator outlines in the stands
  * Atmospheric effects — ambient dust motes, haze, light shafts
  * Enhanced figure rendering — multi-layer body/limb sprites with specular highlights
  * Metallic ball — specular reflections, environment mapping, afterimage trail
  * Stadium environment — outer wall structure, floodlight rigs, sky gradient
  * Glass-morphism UI — frosted-glass panel effect with blur and transparency
  * Screen shake on impacts — camera trauma system for crashes and goals
"""

__all__ = ["launch", "Tier4App"]


def __getattr__(name: str):
    if name in {"launch", "Tier4App"}:
        from roozerball.gui_tier4.app import Tier4App, launch

        return {"launch": launch, "Tier4App": Tier4App}[name]
    raise AttributeError(name)
