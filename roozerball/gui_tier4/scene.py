"""Tier 4 scene graph — re-exports the Tier 3 scene-graph system.

The scene-graph architecture (Transform, SceneNode, AnimationController)
is shared unchanged between Tier 3 and Tier 4.
"""
from roozerball.gui_tier3.scene import AnimationController, SceneNode, Transform

__all__ = ["Transform", "SceneNode", "AnimationController"]
