"""Tier 3 scene-graph system — lightweight node hierarchy.

Each visual element (figure, ball, marker, UI panel) is a ``SceneNode``
with a local transform, children, and an optional draw callback.
The root node is traversed each frame; the camera transform is applied
at the top level so every child inherits it automatically.
"""
from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Optional, Tuple

import pygame


class Transform:
    """2-D affine transform: position + scale + rotation."""

    __slots__ = ("x", "y", "scale_x", "scale_y", "rotation")

    def __init__(
        self,
        x: float = 0.0,
        y: float = 0.0,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
        rotation: float = 0.0,
    ) -> None:
        self.x = x
        self.y = y
        self.scale_x = scale_x
        self.scale_y = scale_y
        self.rotation = rotation

    def apply(self, wx: float, wy: float) -> Tuple[float, float]:
        """Apply this transform to a world point."""
        # Scale first, then rotate, then translate
        sx = wx * self.scale_x
        sy = wy * self.scale_y
        if self.rotation != 0.0:
            c = math.cos(self.rotation)
            s = math.sin(self.rotation)
            rx = sx * c - sy * s
            ry = sx * s + sy * c
            return rx + self.x, ry + self.y
        return sx + self.x, sy + self.y

    def compose(self, parent: "Transform") -> "Transform":
        """Return a new transform that is this transform applied within *parent*."""
        px, py = parent.apply(self.x, self.y)
        return Transform(
            px,
            py,
            self.scale_x * parent.scale_x,
            self.scale_y * parent.scale_y,
            self.rotation + parent.rotation,
        )


class SceneNode:
    """A node in the 2-D scene graph.

    Nodes form a tree; each node has a local ``Transform`` and an optional
    ``draw_fn(surface, world_transform)`` callback that is invoked during
    the draw traversal.
    """

    def __init__(
        self,
        name: str = "",
        transform: Optional[Transform] = None,
        draw_fn: Optional[Callable[[pygame.Surface, Transform], None]] = None,
        z_order: int = 0,
        visible: bool = True,
    ) -> None:
        self.name = name
        self.transform = transform or Transform()
        self.draw_fn = draw_fn
        self.z_order = z_order
        self.visible = visible
        self.children: List[SceneNode] = []
        self.parent: Optional[SceneNode] = None
        self.data: Dict[str, Any] = {}  # arbitrary per-node data

    def add_child(self, child: "SceneNode") -> "SceneNode":
        child.parent = self
        self.children.append(child)
        return child

    def remove_child(self, child: "SceneNode") -> None:
        child.parent = None
        self.children = [c for c in self.children if c is not child]

    def clear_children(self) -> None:
        for c in self.children:
            c.parent = None
        self.children.clear()

    def draw(self, surface: pygame.Surface,
             parent_transform: Optional[Transform] = None) -> None:
        """Recursively draw this node and all children."""
        if not self.visible:
            return

        if parent_transform is not None:
            world = self.transform.compose(parent_transform)
        else:
            world = self.transform

        if self.draw_fn is not None:
            self.draw_fn(surface, world)

        # Sort children by z_order for correct layering
        sorted_children = sorted(self.children, key=lambda c: c.z_order)
        for child in sorted_children:
            child.draw(surface, world)

    def find(self, name: str) -> Optional["SceneNode"]:
        """Find a descendant node by name (depth-first)."""
        if self.name == name:
            return self
        for child in self.children:
            found = child.find(name)
            if found is not None:
                return found
        return None


class AnimationController:
    """Manages per-node animation state with smooth interpolation."""

    __slots__ = (
        "action", "frame", "timer", "total_frames", "frame_duration",
        "wobble", "pulse", "flash_timer", "flash_duration",
    )

    def __init__(self, total_frames: int = 3,
                 frame_duration: float = 120.0) -> None:
        self.action: str = "idle"
        self.frame: int = 0
        self.timer: float = 0.0
        self.total_frames: int = total_frames
        self.frame_duration: float = frame_duration
        self.wobble: float = 0.0
        self.pulse: float = 0.0
        self.flash_timer: float = 0.0
        self.flash_duration: float = 0.0

    def set_action(self, action: str, total_frames: int) -> None:
        if action == self.action:
            return
        self.action = action
        self.frame = 0
        self.timer = 0.0
        self.total_frames = max(1, total_frames)

    def trigger_flash(self, duration_ms: float) -> None:
        """Trigger a one-shot flash effect."""
        self.flash_timer = duration_ms
        self.flash_duration = duration_ms

    def update(self, dt_ms: float) -> None:
        self.timer += dt_ms
        if self.timer >= self.frame_duration:
            self.timer -= self.frame_duration
            self.frame = (self.frame + 1) % self.total_frames

        # Compute wobble based on action
        phase = self.frame / max(1, self.total_frames)
        if self.action == "move":
            self.wobble = math.sin(phase * math.pi * 2) * 2.5
            self.pulse = 0.0
        elif self.action == "combat":
            self.wobble = math.sin(phase * math.pi * 2) * 3.5
            self.pulse = abs(math.sin(phase * math.pi)) * 0.3
        elif self.action == "stand_up":
            self.wobble = math.sin(phase * math.pi) * 1.5
            self.pulse = 0.0
        else:  # idle
            self.wobble = math.sin(phase * math.pi * 2) * 0.5
            self.pulse = abs(math.sin(phase * math.pi * 2)) * 0.08

        # Flash decay
        if self.flash_timer > 0:
            self.flash_timer = max(0.0, self.flash_timer - dt_ms)

    @property
    def flash_alpha(self) -> float:
        """0.0-1.0 flash intensity (decays over duration)."""
        if self.flash_duration <= 0 or self.flash_timer <= 0:
            return 0.0
        return self.flash_timer / self.flash_duration
