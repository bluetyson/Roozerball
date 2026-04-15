"""Tier 4 post-processing effects pipeline.

Software-rendered post-processing for bloom/glow, vignette, screen shake,
and heat distortion — all running on Pygame surfaces without GPU shaders.
"""
from __future__ import annotations

import math
import random as _rng
from typing import Optional, Tuple

import pygame

from roozerball.gui_tier4.constants import (
    BLOOM_BLUR_PASSES,
    BLOOM_DOWNSCALE,
    BLOOM_ENABLED,
    BLOOM_INTENSITY,
    BLOOM_THRESHOLD,
    HEAT_DISTORTION_AMPLITUDE,
    HEAT_DISTORTION_ENABLED,
    HEAT_DISTORTION_FREQUENCY,
    HEAT_DISTORTION_RADIUS,
    SHAKE_DECAY,
    VIGNETTE_ENABLED,
    VIGNETTE_RADIUS,
    VIGNETTE_STRENGTH,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)


class ScreenShake:
    """Camera trauma system — applies decaying random offset on impacts."""

    def __init__(self) -> None:
        self._trauma: float = 0.0
        self._offset_x: float = 0.0
        self._offset_y: float = 0.0

    def add_trauma(self, magnitude: float, duration_ms: float = 300) -> None:
        """Add shake trauma (higher = stronger shake)."""
        self._trauma = min(self._trauma + magnitude, 15.0)

    def update(self, dt_ms: float) -> None:
        if self._trauma > 0.1:
            self._offset_x = _rng.uniform(-self._trauma, self._trauma)
            self._offset_y = _rng.uniform(-self._trauma, self._trauma)
            self._trauma *= SHAKE_DECAY
            if self._trauma < 0.1:
                self._trauma = 0.0
                self._offset_x = 0.0
                self._offset_y = 0.0
        else:
            self._offset_x = 0.0
            self._offset_y = 0.0

    @property
    def offset(self) -> Tuple[float, float]:
        return self._offset_x, self._offset_y

    @property
    def active(self) -> bool:
        return self._trauma > 0.1


class BloomEffect:
    """Software bloom — extracts bright pixels, blurs, and composites.

    Uses downscaled surfaces for performance. The effect brightens
    areas above the luminance threshold.
    """

    def __init__(self) -> None:
        self._enabled = BLOOM_ENABLED
        self._bright_surf: Optional[pygame.Surface] = None
        self._blur_surf: Optional[pygame.Surface] = None

    def apply(self, surface: pygame.Surface) -> None:
        """Apply bloom effect in-place to *surface*."""
        if not self._enabled:
            return

        w, h = surface.get_size()
        ds = BLOOM_DOWNSCALE
        small_w = max(1, w // ds)
        small_h = max(1, h // ds)

        # Downscale
        small = pygame.transform.smoothscale(surface, (small_w, small_h))

        # Threshold: darken pixels below threshold
        threshold_surf = pygame.Surface((small_w, small_h))
        threshold_surf.fill((BLOOM_THRESHOLD, BLOOM_THRESHOLD, BLOOM_THRESHOLD))
        small.blit(threshold_surf, (0, 0), special_flags=pygame.BLEND_RGB_SUB)

        # Blur passes (box blur via scale-down-up)
        blur = small
        for _ in range(BLOOM_BLUR_PASSES):
            tiny_w = max(1, blur.get_width() // 2)
            tiny_h = max(1, blur.get_height() // 2)
            blur = pygame.transform.smoothscale(blur, (tiny_w, tiny_h))
            blur = pygame.transform.smoothscale(blur, (small_w, small_h))

        # Upscale back
        bloom = pygame.transform.smoothscale(blur, (w, h))

        # Composite with intensity control
        intensity_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        bloom.set_alpha(int(255 * BLOOM_INTENSITY))
        intensity_surface.blit(bloom, (0, 0))

        surface.blit(intensity_surface, (0, 0), special_flags=pygame.BLEND_RGB_ADD)


class VignetteEffect:
    """Darkened edges for cinematic framing."""

    def __init__(self) -> None:
        self._enabled = VIGNETTE_ENABLED
        self._cached: Optional[pygame.Surface] = None
        self._cached_size: Optional[Tuple[int, int]] = None

    def apply(self, surface: pygame.Surface) -> None:
        """Apply vignette in-place to *surface*."""
        if not self._enabled:
            return

        w, h = surface.get_size()
        size = (w, h)

        if self._cached is None or self._cached_size != size:
            self._cached = self._generate(w, h)
            self._cached_size = size

        surface.blit(self._cached, (0, 0))

    def _generate(self, w: int, h: int) -> pygame.Surface:
        """Generate the vignette overlay surface."""
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        cx, cy = w / 2, h / 2
        max_dist = math.sqrt(cx * cx + cy * cy)
        radius_threshold = max_dist * VIGNETTE_RADIUS

        # Draw concentric darkening rings
        steps = 20
        for i in range(steps):
            frac = (i + 1) / steps
            ring_dist = radius_threshold + (max_dist - radius_threshold) * frac
            alpha = int(255 * VIGNETTE_STRENGTH * frac * frac)
            alpha = min(255, alpha)
            if alpha < 2:
                continue

            r = int(ring_dist)
            if r < 1:
                continue

            ring_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            ring_surf.fill((0, 0, 0, alpha))
            # Cut out inner portion
            inner_r = int(radius_threshold + (max_dist - radius_threshold) * ((i) / steps))
            if inner_r > 0:
                pygame.draw.circle(ring_surf, (0, 0, 0, 0), (int(cx), int(cy)), inner_r)
            surf.blit(ring_surf, (0, 0))

        return surf


class HeatDistortion:
    """Localised heat shimmer near the ball."""

    def __init__(self) -> None:
        self._enabled = HEAT_DISTORTION_ENABLED

    def apply(
        self,
        surface: pygame.Surface,
        ball_screen_pos: Optional[Tuple[int, int]],
        time_ms: float,
    ) -> None:
        """Apply subtle heat distortion around the ball position."""
        if not self._enabled or ball_screen_pos is None:
            return

        bx, by = ball_screen_pos
        r = HEAT_DISTORTION_RADIUS
        amp = HEAT_DISTORTION_AMPLITUDE
        freq = HEAT_DISTORTION_FREQUENCY

        w, h = surface.get_size()

        # Only affect a small region around the ball
        x1 = max(0, bx - r)
        y1 = max(0, by - r)
        x2 = min(w, bx + r)
        y2 = min(h, by + r)

        if x2 <= x1 or y2 <= y1:
            return

        region_w = x2 - x1
        region_h = y2 - y1

        # Capture the region
        region = surface.subsurface((x1, y1, region_w, region_h)).copy()

        # Create a distorted version by shifting rows
        distorted = region.copy()
        for row in range(region_h):
            abs_y = y1 + row
            dy = abs_y - by
            dist = math.sqrt((0) ** 2 + dy ** 2)  # simplified distance
            if dist > r:
                continue
            falloff = 1.0 - (dist / r)
            shift = int(math.sin(abs_y * 0.1 + time_ms * freq) * amp * falloff)
            if shift == 0:
                continue

            # Shift the row horizontally
            row_surf = pygame.Surface((region_w, 1), pygame.SRCALPHA)
            src_rect = pygame.Rect(0, row, region_w, 1)
            row_surf.blit(region, (0, 0), src_rect)

            dst_x = max(0, min(region_w - 1, shift))
            distorted.blit(row_surf, (dst_x, row))

        surface.blit(distorted, (x1, y1))


class PostProcessor:
    """Orchestrates all post-processing effects."""

    def __init__(self) -> None:
        self.bloom = BloomEffect()
        self.vignette = VignetteEffect()
        self.heat_distortion = HeatDistortion()
        self.screen_shake = ScreenShake()

    def update(self, dt_ms: float) -> None:
        self.screen_shake.update(dt_ms)

    def apply(
        self,
        surface: pygame.Surface,
        ball_screen_pos: Optional[Tuple[int, int]] = None,
        time_ms: float = 0.0,
    ) -> None:
        """Apply all post-processing passes to *surface*."""
        self.bloom.apply(surface)
        self.heat_distortion.apply(surface, ball_screen_pos, time_ms)
        self.vignette.apply(surface)
