"""Tier 4 particle system — enhanced with ambient effects, sparks, and embers.

Extends Tier 3 particles with atmospheric dust motes, persistent ambient
effects, and additional emitter types for a more realistic arena feel.
"""
from __future__ import annotations

import math
import random as _rng
from typing import List, Optional, Tuple

import pygame

from roozerball.gui_tier4.constants import (
    AMBIENT_PARTICLE_COLORS,
    AMBIENT_PARTICLE_COUNT,
    AMBIENT_PARTICLE_LIFETIME_MS,
    AMBIENT_PARTICLE_SIZE_RANGE,
    AMBIENT_PARTICLE_SPEED_RANGE,
    BOARD_CX,
    BOARD_CY,
    PARTICLE_COUNT_CANNON,
    PARTICLE_COUNT_CRASH,
    PARTICLE_COUNT_DUST,
    PARTICLE_COUNT_EMBERS,
    PARTICLE_COUNT_EXHAUST,
    PARTICLE_COUNT_GOAL,
    PARTICLE_COUNT_SPARKS,
    PARTICLE_DEFAULT_COLORS,
    PARTICLE_LIFETIME_MS,
    PARTICLE_TRAIL_LENGTH,
)


class Particle:
    """A single particle with optional trail history."""

    __slots__ = (
        "x", "y", "vx", "vy", "color", "size", "life", "max_life",
        "gravity", "drag", "trail", "trail_max", "shape", "rotation",
        "rotation_speed",
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
        self.rotation = _rng.uniform(0, math.pi * 2)
        self.rotation_speed = _rng.uniform(-0.05, 0.05)


class ParticleSystem:
    """Multi-type particle manager with ambient atmosphere support."""

    def __init__(self) -> None:
        self._particles: List[Particle] = []
        self._ambient_timer: float = 0.0
        self._ambient_interval: float = 200.0  # ms between ambient spawns

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
    # Convenience emitters
    # ------------------------------------------------------------------

    def emit_cannon(self, x: float, y: float) -> None:
        self.emit(
            x, y, PARTICLE_COUNT_CANNON,
            colors=[(255, 75, 8), (255, 145, 18), (255, 215, 45), (255, 255, 200)],
            speed_range=(2.5, 8.0),
            size_range=(2.0, 7.0),
            trail_length=5,
            gravity=0.08,
        )
        # Hot sparks
        self.emit(
            x, y, PARTICLE_COUNT_SPARKS,
            colors=[(255, 255, 180), (255, 240, 150)],
            speed_range=(4.0, 10.0),
            size_range=(1.0, 2.5),
            lifetime=500,
            trail_length=3,
            gravity=0.15,
            drag=0.97,
        )

    def emit_crash(self, x: float, y: float) -> None:
        self.emit(
            x, y, PARTICLE_COUNT_CRASH,
            colors=[(240, 65, 65), (255, 120, 28), (255, 195, 45)],
            speed_range=(1.0, 4.5),
            size_range=(1.5, 5.0),
            trail_length=3,
        )
        # Impact sparks
        self.emit(
            x, y, PARTICLE_COUNT_SPARKS,
            colors=[(255, 255, 200), (255, 220, 120)],
            speed_range=(3.0, 7.0),
            size_range=(1.0, 2.0),
            lifetime=350,
            trail_length=2,
            gravity=0.2,
            drag=0.96,
        )

    def emit_goal(self, x: float, y: float) -> None:
        self.emit(
            x, y, PARTICLE_COUNT_GOAL,
            colors=[
                (45, 205, 95), (60, 135, 255), (255, 165, 22),
                (235, 75, 155), (255, 255, 255),
            ],
            speed_range=(3.0, 10.0),
            size_range=(2.5, 8.0),
            lifetime=1400,
            trail_length=PARTICLE_TRAIL_LENGTH,
            shape="square",
            gravity=0.10,
        )
        # Golden confetti burst
        self.emit(
            x, y, 20,
            colors=[(255, 220, 60), (255, 200, 30), (255, 240, 100)],
            speed_range=(2.0, 6.0),
            size_range=(3.0, 6.0),
            lifetime=1800,
            gravity=0.06,
            drag=0.98,
            shape="square",
        )

    def emit_exhaust(self, x: float, y: float, direction: float) -> None:
        self.emit(
            x, y, PARTICLE_COUNT_EXHAUST,
            colors=[(75, 75, 95), (95, 95, 115), (55, 55, 75)],
            speed_range=(0.5, 1.8),
            size_range=(2.0, 4.5),
            lifetime=500,
            gravity=-0.03,
            drag=0.95,
            direction=direction + math.pi,
            spread=0.8,
        )

    def emit_dust(self, x: float, y: float) -> None:
        self.emit(
            x, y, PARTICLE_COUNT_DUST,
            colors=[(155, 135, 95), (135, 115, 75), (115, 95, 65)],
            speed_range=(0.3, 1.8),
            size_range=(3.0, 7.0),
            lifetime=600,
            gravity=-0.02,
            drag=0.94,
        )

    def emit_sparks(self, x: float, y: float) -> None:
        """Bright sparks for metal-on-metal impacts."""
        self.emit(
            x, y, PARTICLE_COUNT_SPARKS,
            colors=[(255, 255, 200), (255, 240, 150), (255, 200, 100)],
            speed_range=(3.0, 8.0),
            size_range=(1.0, 2.5),
            lifetime=400,
            trail_length=4,
            gravity=0.18,
            drag=0.96,
        )

    def emit_embers(self, x: float, y: float) -> None:
        """Floating embers rising from fire/explosion areas."""
        self.emit(
            x, y, PARTICLE_COUNT_EMBERS,
            colors=[(255, 130, 30), (255, 80, 10), (200, 60, 10)],
            speed_range=(0.2, 1.0),
            size_range=(1.5, 3.0),
            lifetime=1200,
            gravity=-0.05,
            drag=0.98,
        )

    # ------------------------------------------------------------------
    # Ambient atmosphere
    # ------------------------------------------------------------------

    def _spawn_ambient(self, board_w: int, board_h: int) -> None:
        """Spawn floating dust motes in the arena atmosphere."""
        for _ in range(2):
            x = _rng.uniform(50, board_w - 50)
            y = _rng.uniform(50, board_h - 50)
            # Very slow drift
            vx = _rng.uniform(*AMBIENT_PARTICLE_SPEED_RANGE) * _rng.choice([-1, 1])
            vy = _rng.uniform(*AMBIENT_PARTICLE_SPEED_RANGE) * _rng.choice([-1, 1])
            self._particles.append(
                Particle(
                    x, y, vx, vy,
                    _rng.choice(AMBIENT_PARTICLE_COLORS),
                    _rng.uniform(*AMBIENT_PARTICLE_SIZE_RANGE),
                    AMBIENT_PARTICLE_LIFETIME_MS,
                    gravity=0.0,
                    drag=0.999,
                    shape="circle",
                )
            )

    # ------------------------------------------------------------------
    # Update & draw
    # ------------------------------------------------------------------

    def update(self, dt_ms: float, board_w: int = 920, board_h: int = 900) -> None:
        # Ambient spawning
        self._ambient_timer += dt_ms
        if self._ambient_timer >= self._ambient_interval:
            self._ambient_timer -= self._ambient_interval
            # Keep ambient count reasonable
            ambient_count = sum(
                1 for p in self._particles
                if p.max_life >= AMBIENT_PARTICLE_LIFETIME_MS - 100
            )
            if ambient_count < AMBIENT_PARTICLE_COUNT:
                self._spawn_ambient(board_w, board_h)

        alive: List[Particle] = []
        for p in self._particles:
            p.life -= dt_ms
            if p.life <= 0:
                continue
            # Record trail
            if p.trail_max > 0:
                p.trail.append((p.x, p.y))
                if len(p.trail) > p.trail_max:
                    p.trail.pop(0)
            p.x += p.vx
            p.y += p.vy
            p.vy += p.gravity
            p.vx *= p.drag
            p.vy *= p.drag
            p.rotation += p.rotation_speed
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

            if size < 1:
                continue

            # Draw main particle
            if p.shape == "square":
                # Rotated square for confetti effect
                half = size
                cos_r = math.cos(p.rotation)
                sin_r = math.sin(p.rotation)
                pts = [
                    (ix + int(cos_r * (-half) - sin_r * (-half)),
                     iy + int(sin_r * (-half) + cos_r * (-half))),
                    (ix + int(cos_r * half - sin_r * (-half)),
                     iy + int(sin_r * half + cos_r * (-half))),
                    (ix + int(cos_r * half - sin_r * half),
                     iy + int(sin_r * half + cos_r * half)),
                    (ix + int(cos_r * (-half) - sin_r * half),
                     iy + int(sin_r * (-half) + cos_r * half)),
                ]
                if size >= 2:
                    pygame.draw.polygon(surface, color, pts)
                else:
                    pygame.draw.rect(
                        surface, color,
                        (ix - size, iy - size, size * 2, size * 2),
                    )
            else:
                pygame.draw.circle(surface, color, (ix, iy), size)
                # Soft glow for larger particles
                if size >= 3:
                    glow_surf = pygame.Surface(
                        (size * 4 + 4, size * 4 + 4), pygame.SRCALPHA,
                    )
                    glow_alpha = int(alpha * 20)
                    pygame.draw.circle(
                        glow_surf, (fr, fg, fb, glow_alpha),
                        (size * 2 + 2, size * 2 + 2), size * 2,
                    )
                    surface.blit(
                        glow_surf,
                        (ix - size * 2 - 2, iy - size * 2 - 2),
                        special_flags=pygame.BLEND_ADD,
                    )

    def clear(self) -> None:
        self._particles.clear()

    @property
    def active(self) -> bool:
        return bool(self._particles)
