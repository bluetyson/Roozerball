"""Tier 4 procedural texture generation.

Generates track surface textures with noise-based grain, lane markings,
scuff marks, and crowd silhouettes — all pre-baked to surfaces for
efficient per-frame blitting.
"""
from __future__ import annotations

import math
import random as _rng
from typing import List, Optional, Tuple

import pygame

from roozerball.gui_tier4.constants import (
    BOARD_CX,
    BOARD_CY,
    CROWD_DENSITY,
    CROWD_SILHOUETTE_COLORS,
    NUM_TRACK_SECTORS,
    RING_FILLS,
    RING_RADII,
    STADIUM_RAILING_COLOR,
    STADIUM_WALL_COLOR,
    STADIUM_WALL_HIGHLIGHT,
    TEXTURE_GRAIN_INTENSITY,
    TEXTURE_NOISE_SCALE,
    TEXTURE_SCUFF_COUNT,
    TEXTURE_SCUFF_SIZE_RANGE,
    TRACK_GRAIN_DARK,
    TRACK_GRAIN_LIGHT,
    TRACK_LANE_MARKING,
    TRACK_SCUFF_COLOR,
)
from roozerball.engine.constants import Ring


def _simple_noise(x: float, y: float, seed: int = 0) -> float:
    """Cheap hash-based pseudo-noise in [0, 1]."""
    n = int(x * 57 + y * 131 + seed * 17) & 0x7FFFFFFF
    n = (n >> 13) ^ n
    n = (n * (n * n * 15731 + 789221) + 1376312589) & 0x7FFFFFFF
    return n / 0x7FFFFFFF


def _fbm(x: float, y: float, octaves: int = 3, seed: int = 0) -> float:
    """Fractional Brownian motion (layered noise)."""
    value = 0.0
    amplitude = 1.0
    frequency = 1.0
    total_amp = 0.0
    for i in range(octaves):
        value += _simple_noise(x * frequency, y * frequency, seed + i * 37) * amplitude
        total_amp += amplitude
        amplitude *= 0.5
        frequency *= 2.0
    return value / total_amp if total_amp > 0 else 0.5


class TrackTextureGenerator:
    """Generates a pre-baked track surface texture with realistic details."""

    def __init__(self, width: int = 860, height: int = 920) -> None:
        self.width = width
        self.height = height
        self._surface: Optional[pygame.Surface] = None
        self._crowd_seed = _rng.randint(0, 10000)
        self._scuff_positions: List[Tuple[float, float, float, float]] = []

    def _generate_scuffs(self) -> None:
        """Pre-generate random scuff mark positions on the track."""
        self._scuff_positions.clear()
        for _ in range(TEXTURE_SCUFF_COUNT):
            # Random position within track area
            angle = _rng.uniform(0, 2 * math.pi)
            # Place scuffs mainly on lower/middle rings where action happens
            radius = _rng.uniform(80, 310)
            x = BOARD_CX + math.cos(angle) * radius
            y = BOARD_CY + math.sin(angle) * radius
            size = _rng.uniform(*TEXTURE_SCUFF_SIZE_RANGE)
            rot = _rng.uniform(0, math.pi)
            self._scuff_positions.append((x, y, size, rot))

    def generate(self) -> pygame.Surface:
        """Build the full track texture surface."""
        if self._surface is not None:
            return self._surface

        self._generate_scuffs()
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))

        # 1. Noise-based grain overlay for track rings
        self._paint_track_grain(surf)

        # 2. Lane markings (dashed lines along ring boundaries)
        self._paint_lane_markings(surf)

        # 3. Scuff marks
        self._paint_scuffs(surf)

        # 4. Sector boundary tick marks
        self._paint_sector_ticks(surf)

        self._surface = surf
        return surf

    def _paint_track_grain(self, surf: pygame.Surface) -> None:
        """Apply noise-based grain to the track surface."""
        scale = TEXTURE_NOISE_SCALE
        intensity = TEXTURE_GRAIN_INTENSITY

        # Sample at sparse grid points for performance
        step = 4
        for py in range(0, self.height, step):
            for px in range(0, self.width, step):
                dx = px - BOARD_CX
                dy = py - BOARD_CY
                dist = math.sqrt(dx * dx + dy * dy)

                # Only within track area
                if dist < 40 or dist > 350:
                    continue

                noise_val = _fbm(px / (scale * 40), py / (scale * 40), 3)
                # Map to brightness offset
                offset = int((noise_val - 0.5) * intensity * 2)

                if offset > 0:
                    color = (*TRACK_GRAIN_LIGHT, min(255, offset * 4))
                else:
                    color = (*TRACK_GRAIN_DARK, min(255, abs(offset) * 4))

                pygame.draw.rect(surf, color, (px, py, step, step))

    def _paint_lane_markings(self, surf: pygame.Surface) -> None:
        """Draw dashed lane divider lines along ring boundaries."""
        for ring in Ring:
            inner, outer = RING_RADII[ring]
            for radius in (inner, outer):
                dash_count = int(2 * math.pi * radius / 12)
                if dash_count < 10:
                    dash_count = 10
                for i in range(0, dash_count, 2):
                    angle_start = (2 * math.pi / dash_count) * i
                    angle_end = (2 * math.pi / dash_count) * (i + 1)
                    x1 = BOARD_CX + math.cos(angle_start) * radius
                    y1 = BOARD_CY + math.sin(angle_start) * radius
                    x2 = BOARD_CX + math.cos(angle_end) * radius
                    y2 = BOARD_CY + math.sin(angle_end) * radius
                    pygame.draw.line(
                        surf, (*TRACK_LANE_MARKING, 30),
                        (int(x1), int(y1)), (int(x2), int(y2)), 1,
                    )

    def _paint_scuffs(self, surf: pygame.Surface) -> None:
        """Draw scuff/wear marks on the track."""
        for x, y, size, rot in self._scuff_positions:
            scuff_surf = pygame.Surface(
                (int(size * 4) + 4, int(size * 2) + 4), pygame.SRCALPHA,
            )
            cx = scuff_surf.get_width() // 2
            cy = scuff_surf.get_height() // 2
            pygame.draw.ellipse(
                scuff_surf, (*TRACK_SCUFF_COLOR, 25),
                (2, 2, scuff_surf.get_width() - 4, scuff_surf.get_height() - 4),
            )
            rotated = pygame.transform.rotate(scuff_surf, math.degrees(rot))
            surf.blit(
                rotated,
                (int(x) - rotated.get_width() // 2,
                 int(y) - rotated.get_height() // 2),
            )

    def _paint_sector_ticks(self, surf: pygame.Surface) -> None:
        """Draw short tick marks at sector boundaries."""
        for i in range(NUM_TRACK_SECTORS):
            angle = -math.pi / 2 + i * (2 * math.pi / NUM_TRACK_SECTORS)
            inner_r = RING_RADII[Ring.FLOOR][0]
            outer_r = RING_RADII[Ring.CANNON][1]
            x1 = BOARD_CX + math.cos(angle) * inner_r
            y1 = BOARD_CY + math.sin(angle) * inner_r
            x2 = BOARD_CX + math.cos(angle) * outer_r
            y2 = BOARD_CY + math.sin(angle) * outer_r
            pygame.draw.line(
                surf, (*TRACK_LANE_MARKING, 40),
                (int(x1), int(y1)), (int(x2), int(y2)), 1,
            )


class CrowdGenerator:
    """Generates crowd silhouette data for the stadium stands."""

    def __init__(self) -> None:
        self._silhouettes: List[Tuple[float, float, int, int, Tuple[int, int, int]]] = []
        self._generated = False

    def generate(self) -> None:
        """Pre-generate crowd silhouette positions."""
        if self._generated:
            return
        self._silhouettes.clear()

        outer_r = RING_RADII[Ring.CANNON][1]
        for sector_idx in range(NUM_TRACK_SECTORS):
            sector_start = -math.pi / 2 + sector_idx * (2 * math.pi / NUM_TRACK_SECTORS)
            sector_span = 2 * math.pi / NUM_TRACK_SECTORS

            for _ in range(CROWD_DENSITY):
                angle = sector_start + _rng.uniform(0.05, 0.95) * sector_span
                radius = outer_r + _rng.uniform(8, 55)
                x = BOARD_CX + math.cos(angle) * radius
                y = BOARD_CY + math.sin(angle) * radius
                height = _rng.randint(4, 8)
                width = _rng.randint(3, 5)
                color = _rng.choice(CROWD_SILHOUETTE_COLORS)
                self._silhouettes.append((x, y, width, height, color))

        self._generated = True

    def draw(
        self,
        surface: pygame.Surface,
        camera_w2s: callable,
        time_ms: float,
        zoom: float,
    ) -> None:
        """Draw crowd silhouettes with subtle bobbing animation."""
        from roozerball.gui_tier4.constants import CROWD_BOB_AMPLITUDE, CROWD_BOB_SPEED

        if not self._generated:
            self.generate()

        for i, (wx, wy, w, h, color) in enumerate(self._silhouettes):
            sx, sy = camera_w2s(wx, wy)
            # Subtle bob animation (staggered per silhouette)
            bob = math.sin(time_ms * CROWD_BOB_SPEED + i * 0.7) * CROWD_BOB_AMPLITUDE * zoom

            ix = int(sx)
            iy = int(sy + bob)
            sw = max(1, int(w * zoom))
            sh = max(1, int(h * zoom))

            if sw < 1 or sh < 1:
                continue

            # Head (circle)
            head_r = max(1, sw // 2)
            pygame.draw.circle(surface, color, (ix, iy - sh), head_r)
            # Body (small rect)
            pygame.draw.rect(
                surface, color,
                (ix - sw // 2, iy - sh + head_r, sw, sh),
            )


class StadiumRenderer:
    """Draws stadium environment: outer walls, railing, floodlight rigs."""

    def draw_walls(
        self,
        surface: pygame.Surface,
        camera_w2s: callable,
        zoom: float,
    ) -> None:
        """Draw the outer stadium wall ring."""
        cx, cy = camera_w2s(BOARD_CX, BOARD_CY)
        icx, icy = int(cx), int(cy)

        # Outer wall (thick ring beyond the stands)
        wall_inner = int(375 * zoom)
        wall_outer = int(395 * zoom)
        if wall_outer < 2:
            return

        # Wall body
        if wall_outer > 0:
            pygame.draw.circle(surface, STADIUM_WALL_COLOR, (icx, icy), wall_outer)
        if wall_inner > 0:
            # Clear interior (will be drawn over by track)
            pass

        # Highlight on top edge
        if wall_outer > 2:
            highlight_surf = pygame.Surface(
                (wall_outer * 2 + 4, wall_outer * 2 + 4), pygame.SRCALPHA,
            )
            pygame.draw.circle(
                highlight_surf,
                (*STADIUM_WALL_HIGHLIGHT, 40),
                (wall_outer + 2, wall_outer + 2),
                wall_outer,
                max(1, int(2 * zoom)),
            )
            surface.blit(
                highlight_surf,
                (icx - wall_outer - 2, icy - wall_outer - 2),
                special_flags=pygame.BLEND_ADD,
            )

        # Railing
        railing_r = int(355 * zoom)
        if railing_r > 2:
            pygame.draw.circle(
                surface, STADIUM_RAILING_COLOR, (icx, icy),
                railing_r, max(1, int(2 * zoom)),
            )

    def draw_floodlights(
        self,
        surface: pygame.Surface,
        camera_w2s: callable,
        zoom: float,
        time_ms: float,
    ) -> None:
        """Draw floodlight rigs above the track."""
        from roozerball.gui_tier4.constants import (
            FLOODLIGHT_COLOR,
            FLOODLIGHT_POSITIONS,
            STADIUM_LIGHT_RIG_COLOR,
        )

        cx, cy = camera_w2s(BOARD_CX, BOARD_CY)

        for fx, fy in FLOODLIGHT_POSITIONS:
            lx = int(cx + fx * 380 * zoom)
            ly = int(cy + fy * 380 * zoom)

            # Light rig structure (small rectangle)
            rig_w = max(2, int(18 * zoom))
            rig_h = max(1, int(6 * zoom))
            pygame.draw.rect(
                surface, STADIUM_LIGHT_RIG_COLOR,
                (lx - rig_w // 2, ly - rig_h // 2, rig_w, rig_h),
            )

            # Light cone (soft glow pointing toward center)
            cone_r = int(50 * zoom)
            if cone_r > 3:
                # Subtle flicker
                flicker = 0.95 + 0.05 * math.sin(time_ms * 0.003 + fx * 100)
                alpha = int(20 * flicker)
                cone_surf = pygame.Surface(
                    (cone_r * 2 + 4, cone_r * 2 + 4), pygame.SRCALPHA,
                )
                pygame.draw.circle(
                    cone_surf,
                    (*FLOODLIGHT_COLOR, alpha),
                    (cone_r + 2, cone_r + 2),
                    cone_r,
                )
                surface.blit(
                    cone_surf,
                    (lx - cone_r - 2, ly - cone_r - 2),
                    special_flags=pygame.BLEND_ADD,
                )

            # Small bright point
            pygame.draw.circle(
                surface, (255, 252, 245), (lx, ly), max(1, int(3 * zoom)),
            )
