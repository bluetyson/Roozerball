"""Tier 3 particle system — advanced effects with trails and typed emitters.

Supports multiple particle types: sparks, confetti, exhaust, dust, trails.
Each particle can leave a fading trail behind it for richer visuals.
"""
from __future__ import annotations

import math
import random as _rng
from typing import List, Optional, Tuple

import pygame

from roozerball.gui_tier3.constants import (
    PARTICLE_COUNT_CANNON,
    PARTICLE_COUNT_CRASH,
    PARTICLE_COUNT_DUST,
    PARTICLE_COUNT_EXHAUST,
    PARTICLE_COUNT_GOAL,
    PARTICLE_DEFAULT_COLORS,
    PARTICLE_LIFETIME_MS,
    PARTICLE_TRAIL_LENGTH,
)


class Particle:
    """A single particle with optional trail history."""

    __slots__ = (
        "x", "y", "vx", "vy", "color", "size", "life", "max_life",
        "gravity", "drag", "trail", "trail_max", "shape",
    )

    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        color: Tuple[int, int, int],
        size: float,
        lifetime: float,
        gravity: float = 0.12,
        drag: float = 0.99,
        trail_length: int = 0,
        shape: str = "circle",
    ) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.life = lifetime
        self.max_life = lifetime
        self.gravity = gravity
        self.drag = drag
        self.trail: List[Tuple[float, float]] = []
        self.trail_max = trail_length
        self.shape = shape


class ParticleSystem:
    """Multi-type particle manager with trail support."""

    def __init__(self) -> None:
        self._particles: List[Particle] = []

    def emit(
        self,
        x: float,
        y: float,
        count: int,
        *,
        colors: Optional[List[Tuple[int, int, int]]] = None,
        speed_range: Tuple[float, float] = (1.0, 4.0),
        size_range: Tuple[float, float] = (2.0, 5.0),
        lifetime: float = PARTICLE_LIFETIME_MS,
        gravity: float = 0.12,
        drag: float = 0.99,
        trail_length: int = 0,
        shape: str = "circle",
        spread: float = 2 * math.pi,
        direction: float = 0.0,
    ) -> None:
        """Emit *count* particles from (*x*, *y*)."""
        if colors is None:
            colors = list(PARTICLE_DEFAULT_COLORS)
        half_spread = spread / 2
        for _ in range(count):
            angle = direction + _rng.uniform(-half_spread, half_spread)
            speed = _rng.uniform(*speed_range)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            self._particles.append(
                Particle(
                    x, y, vx, vy,
                    _rng.choice(colors),
                    _rng.uniform(*size_range),
                    lifetime,
                    gravity=gravity,
                    drag=drag,
                    trail_length=trail_length,
                    shape=shape,
                )
            )

    # ------------------------------------------------------------------
    # Convenience emitters for specific game events
    # ------------------------------------------------------------------

    def emit_cannon(self, x: float, y: float) -> None:
        self.emit(
            x, y, PARTICLE_COUNT_CANNON,
            colors=[(255, 80, 10), (255, 150, 20), (255, 220, 50), (255, 255, 200)],
            speed_range=(2.5, 7.0),
            size_range=(2.0, 6.0),
            trail_length=4,
            gravity=0.08,
        )

    def emit_crash(self, x: float, y: float) -> None:
        self.emit(
            x, y, PARTICLE_COUNT_CRASH,
            colors=[(240, 70, 70), (255, 125, 30), (255, 200, 50)],
            speed_range=(1.0, 4.0),
            size_range=(1.5, 4.5),
            trail_length=2,
        )

    def emit_goal(self, x: float, y: float) -> None:
        self.emit(
            x, y, PARTICLE_COUNT_GOAL,
            colors=[
                (50, 210, 100), (65, 140, 255), (255, 170, 25),
                (240, 80, 160), (255, 255, 255),
            ],
            speed_range=(3.0, 9.0),
            size_range=(2.5, 7.0),
            lifetime=1200,
            trail_length=PARTICLE_TRAIL_LENGTH,
            shape="square",
            gravity=0.10,
        )

    def emit_exhaust(self, x: float, y: float, direction: float) -> None:
        """Motorcycle exhaust puff."""
        self.emit(
            x, y, PARTICLE_COUNT_EXHAUST,
            colors=[(80, 80, 100), (100, 100, 120), (60, 60, 80)],
            speed_range=(0.5, 1.5),
            size_range=(2.0, 4.0),
            lifetime=400,
            gravity=-0.03,
            drag=0.96,
            direction=direction + math.pi,
            spread=0.8,
        )

    def emit_dust(self, x: float, y: float) -> None:
        """Dust cloud on falls."""
        self.emit(
            x, y, PARTICLE_COUNT_DUST,
            colors=[(160, 140, 100), (140, 120, 80), (120, 100, 70)],
            speed_range=(0.3, 1.5),
            size_range=(3.0, 6.0),
            lifetime=500,
            gravity=-0.02,
            drag=0.95,
        )

    # ------------------------------------------------------------------
    # Update & draw
    # ------------------------------------------------------------------

    def update(self, dt_ms: float) -> None:
        alive: List[Particle] = []
        for p in self._particles:
            p.life -= dt_ms
            if p.life <= 0:
                continue
            # Record trail position before moving
            if p.trail_max > 0:
                p.trail.append((p.x, p.y))
                if len(p.trail) > p.trail_max:
                    p.trail.pop(0)
            p.x += p.vx
            p.y += p.vy
            p.vy += p.gravity
            p.vx *= p.drag
            p.vy *= p.drag
            alive.append(p)
        self._particles = alive

    def draw(self, surface: pygame.Surface) -> None:
        for p in self._particles:
            alpha = max(0.0, p.life / p.max_life)
            size = max(1, int(p.size * alpha))
            r, g, b = p.color
            fr = min(255, int(r * alpha))
            fg = min(255, int(g * alpha))
            fb = min(255, int(b * alpha))
            color = (fr, fg, fb)

            ix, iy = int(p.x), int(p.y)

            # Draw trail
            if p.trail:
                trail_len = len(p.trail)
                for i, (tx, ty) in enumerate(p.trail):
                    t_alpha = (i + 1) / (trail_len + 1) * alpha
                    t_size = max(1, int(size * t_alpha * 0.6))
                    tr = min(255, int(r * t_alpha * 0.5))
                    tg = min(255, int(g * t_alpha * 0.5))
                    tb = min(255, int(b * t_alpha * 0.5))
                    pygame.draw.circle(
                        surface, (tr, tg, tb), (int(tx), int(ty)), t_size,
                    )

            # Draw main particle
            if size < 1:
                continue
            if p.shape == "square":
                pygame.draw.rect(
                    surface, color,
                    (ix - size, iy - size, size * 2, size * 2),
                )
            else:
                pygame.draw.circle(surface, color, (ix, iy), size)

    def clear(self) -> None:
        self._particles.clear()

    @property
    def active(self) -> bool:
        return bool(self._particles)
