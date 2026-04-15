"""Tier 3 renderer — scene-graph-driven board with advanced effects.

Enhancements over Tier 2:
  * Scene-graph node architecture for figures, ball, markers
  * Radial grid with per-tile incline gradients
  * Ball heat glow with shimmer animation
  * Speed lines on fast-moving figures
  * Goal-flash celebration overlay
  * Isometric perspective option (pseudo-3D banked track)
  * Enhanced shadows with soft edges
  * Ring-incline gradient overlays
"""
from __future__ import annotations

import math
import random as _rng
from typing import Any, Dict, List, Optional, Tuple

import pygame

from roozerball.engine.constants import (
    FigureStatus,
    FigureType,
    Ring,
    SQUARES_PER_RING,
    TeamSide,
)
from roozerball.gui_tier3.constants import (
    ANIM_FRAME_DURATION_MS,
    ANIM_FRAMES_COMBAT,
    ANIM_FRAMES_FALL,
    ANIM_FRAMES_IDLE,
    ANIM_FRAMES_MOVE,
    ANIM_FRAMES_STAND_UP,
    AMBIENT_GLOW_ALPHA,
    BALL_DEFAULT,
    BALL_GLOW_COLORS,
    BALL_GLOW_DEFAULT,
    BALL_SHIMMER_COLORS,
    BALL_TEMP_COLORS,
    BG_COLOR,
    BOARD_CX,
    BOARD_CY,
    CAMERA_LERP_SPEED,
    CAMERA_MAX_ZOOM,
    CAMERA_MIN_ZOOM,
    CAMERA_ZOOM_STEP,
    CENTRAL_FILL,
    CENTRAL_GLOW,
    CROWD_SHADES,
    FIGURE_LABELS,
    GOAL_FLASH_ALPHA_MAX,
    GOAL_FLASH_COLOR,
    GOAL_FLASH_DURATION_MS,
    GOAL_HOME_FILL,
    GOAL_HOME_GLOW,
    GOAL_VISITOR_FILL,
    GOAL_VISITOR_GLOW,
    INITIATIVE_GLOW,
    INITIATIVE_OUTLINE,
    INJURED_ACCENT,
    INJURED_FILL,
    INJURED_GLOW,
    ISO_ENABLED_DEFAULT,
    ISO_HEIGHT_PER_RING,
    ISO_TILT,
    LANE_LINE,
    LANE_LINE_BRIGHT,
    NUM_TRACK_SECTORS,
    RING_BRIGHTNESS,
    RING_FILLS,
    RING_GRADIENT_INNER,
    RING_RADII,
    SHADOW_LENGTH_FACTOR,
    SHIMMER_AMPLITUDE,
    SHIMMER_BASELINE,
    SHIMMER_FREQUENCY,
    SLOT_OFFSETS,
    SPEED_LINE_ALPHA,
    SPEED_LINE_COUNT,
    SPEED_LINE_LENGTH,
    SPEED_LINE_THRESHOLD,
    SPOTLIGHT_ALPHA,
    SPOTLIGHT_RADIUS,
    SPRITE_COLORS_HOME,
    SPRITE_COLORS_VISITOR,
    SQUARES_PER_RING_MAP,
    TEXT_ACCENT,
    TEXT_HIGHLIGHT,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from roozerball.gui_tier3.particles import ParticleSystem
from roozerball.gui_tier3.scene import AnimationController, SceneNode, Transform


# ---------------------------------------------------------------------------
# Camera (enhanced with smooth easing)
# ---------------------------------------------------------------------------


class Camera:
    """Smooth-scrolling camera with zoom and eased target following."""

    def __init__(self) -> None:
        self.x: float = 0.0
        self.y: float = 0.0
        self.zoom: float = 1.0
        self._target_x: float = 0.0
        self._target_y: float = 0.0
        self._target_zoom: float = 1.0
        self._following: Optional[Any] = None
        self._locked_sector: Optional[int] = None

    def reset(self) -> None:
        self.x = self._target_x = 0.0
        self.y = self._target_y = 0.0
        self.zoom = self._target_zoom = 1.0
        self._following = None
        self._locked_sector = None

    def follow(self, figure: Optional[Any]) -> None:
        self._following = figure
        self._locked_sector = None

    def lock_sector(self, sector_index: Optional[int]) -> None:
        self._locked_sector = sector_index
        self._following = None

    def zoom_in(self) -> None:
        self._target_zoom = min(CAMERA_MAX_ZOOM, self._target_zoom + CAMERA_ZOOM_STEP)

    def zoom_out(self) -> None:
        self._target_zoom = max(CAMERA_MIN_ZOOM, self._target_zoom - CAMERA_ZOOM_STEP)

    def pan(self, dx: float, dy: float) -> None:
        self._target_x += dx / max(self.zoom, 0.1)
        self._target_y += dy / max(self.zoom, 0.1)
        self._following = None
        self._locked_sector = None

    def update(self, board: Any = None) -> None:
        if self._following is not None and board is not None:
            sq = board.find_square_of_figure(self._following)
            if sq is not None:
                wx, wy = _square_center(sq)
                self._target_x = -(wx - BOARD_CX)
                self._target_y = -(wy - BOARD_CY)

        if self._locked_sector is not None:
            angle = (
                -math.pi / 2
                + self._locked_sector * (2 * math.pi / NUM_TRACK_SECTORS)
                + math.pi / NUM_TRACK_SECTORS
            )
            dist = 200
            self._target_x = -(BOARD_CX + math.cos(angle) * dist - BOARD_CX)
            self._target_y = -(BOARD_CY + math.sin(angle) * dist - BOARD_CY)

        lerp = CAMERA_LERP_SPEED
        self.x += (self._target_x - self.x) * lerp
        self.y += (self._target_y - self.y) * lerp
        self.zoom += (self._target_zoom - self.zoom) * lerp

    def world_to_screen(self, wx: float, wy: float) -> Tuple[float, float]:
        sx = (wx - BOARD_CX + self.x) * self.zoom + BOARD_CX
        sy = (wy - BOARD_CY + self.y) * self.zoom + BOARD_CY
        return sx, sy


# ---------------------------------------------------------------------------
# Geometry helpers (module-level, shared)
# ---------------------------------------------------------------------------


def _square_center(square: Any) -> Tuple[float, float]:
    inner, outer = RING_RADII[square.ring]
    sector_span = 2 * math.pi / NUM_TRACK_SECTORS
    sector_start = -math.pi / 2 + square.sector_index * sector_span
    square_span = sector_span / SQUARES_PER_RING[square.ring]
    angle = sector_start + square_span * (square.position + 0.5)
    radius = (inner + outer) / 2
    return BOARD_CX + math.cos(angle) * radius, BOARD_CY + math.sin(angle) * radius


def _slot_center(square: Any, slot_index: int) -> Tuple[float, float]:
    x, y = _square_center(square)
    offsets = SLOT_OFFSETS[len(square.slots)]
    dx, dy = offsets[min(slot_index, len(offsets) - 1)]
    return x + dx, y + dy


def _wedge_points(
    cx: float,
    cy: float,
    inner_r: float,
    outer_r: float,
    start: float,
    end: float,
) -> List[Tuple[float, float]]:
    return [
        (cx + math.cos(start) * inner_r, cy + math.sin(start) * inner_r),
        (cx + math.cos(start) * outer_r, cy + math.sin(start) * outer_r),
        (cx + math.cos(end) * outer_r, cy + math.sin(end) * outer_r),
        (cx + math.cos(end) * inner_r, cy + math.sin(end) * inner_r),
    ]


def _apply_brightness(
    color: Tuple[int, int, int], factor: float,
) -> Tuple[int, int, int]:
    return (
        min(255, int(color[0] * factor)),
        min(255, int(color[1] * factor)),
        min(255, int(color[2] * factor)),
    )


def _lerp_color(
    c1: Tuple[int, int, int], c2: Tuple[int, int, int], t: float,
) -> Tuple[int, int, int]:
    """Linearly interpolate between two colours."""
    return (
        min(255, max(0, int(c1[0] + (c2[0] - c1[0]) * t))),
        min(255, max(0, int(c1[1] + (c2[1] - c1[1]) * t))),
        min(255, max(0, int(c1[2] + (c2[2] - c1[2]) * t))),
    )


# ---------------------------------------------------------------------------
# Board renderer (Tier 3)
# ---------------------------------------------------------------------------


class BoardRenderer:
    """Draws the circular track, figures, ball, lighting, and effects.

    Uses the scene-graph for per-figure node management and an advanced
    particle system with trail support.
    """

    def __init__(self) -> None:
        self.camera = Camera()
        self.particles = ParticleSystem()
        self._animations: Dict[int, AnimationController] = {}
        self.figure_rects: Dict[int, Tuple[pygame.Rect, Any]] = {}
        self._move_option_rects: List[Tuple[pygame.Rect, Any]] = []
        self._font_cache: Dict[Tuple[int, bool], pygame.font.Font] = {}

        # Scene graph root
        self.scene_root = SceneNode("root")
        self._track_node = self.scene_root.add_child(SceneNode("track", z_order=0))
        self._highlights_node = self.scene_root.add_child(
            SceneNode("highlights", z_order=1)
        )
        self._shadows_node = self.scene_root.add_child(SceneNode("shadows", z_order=2))
        self._figures_node = self.scene_root.add_child(SceneNode("figures", z_order=3))
        self._ball_node = self.scene_root.add_child(SceneNode("ball", z_order=4))
        self._overlay_node = self.scene_root.add_child(SceneNode("overlay", z_order=5))

        # Goal flash state
        self._goal_flash_timer: float = 0.0
        self._time_accum: float = 0.0  # for shimmer effects

        # Isometric perspective toggle
        self.isometric = ISO_ENABLED_DEFAULT

    def _font(self, size: int, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        if key not in self._font_cache:
            self._font_cache[key] = pygame.font.SysFont(
                "arial,helvetica,sans-serif", size, bold=bold,
            )
        return self._font_cache[key]

    def get_anim(self, figure: Any) -> AnimationController:
        fid = id(figure)
        if fid not in self._animations:
            self._animations[fid] = AnimationController(
                ANIM_FRAMES_IDLE, ANIM_FRAME_DURATION_MS,
            )
        return self._animations[fid]

    def update(self, dt_ms: float, game: Any) -> None:
        self.camera.update(game.board if game else None)
        self.particles.update(dt_ms)
        self._time_accum += dt_ms
        if self._goal_flash_timer > 0:
            self._goal_flash_timer = max(0.0, self._goal_flash_timer - dt_ms)

        for fig in game.all_figures():
            anim = self.get_anim(fig)
            if fig.has_moved:
                anim.set_action("move", ANIM_FRAMES_MOVE)
            elif fig.status == FigureStatus.MAN_TO_MAN:
                anim.set_action("combat", ANIM_FRAMES_COMBAT)
            elif fig.needs_stand_up:
                anim.set_action("stand_up", ANIM_FRAMES_STAND_UP)
            else:
                anim.set_action("idle", ANIM_FRAMES_IDLE)
            anim.update(dt_ms)

    def _w2s(self, wx: float, wy: float) -> Tuple[float, float]:
        return self.camera.world_to_screen(wx, wy)

    def draw(
        self,
        surface: pygame.Surface,
        game: Any,
        selected_figure: Optional[Any] = None,
        move_options: Optional[List[Tuple[Any, int]]] = None,
    ) -> None:
        board_rect = pygame.Rect(0, 0, 920, surface.get_height())
        surface.fill(BG_COLOR, board_rect)

        self.figure_rects.clear()
        self._move_option_rects.clear()

        self._draw_track_texture(surface)
        self._draw_squares(surface, game)
        self._draw_ring_gradient_overlay(surface)
        self._draw_lighting(surface, game)
        self._draw_highlights(surface, game)
        self._draw_shadows(surface, game)
        self._draw_figures(surface, game)
        self._draw_speed_lines(surface, game)
        self._draw_ball(surface, game)
        if selected_figure is not None and move_options:
            self._draw_move_options(surface, move_options)
        self._draw_goal_flash(surface)
        self._draw_canvas_scoreboard(surface, game)
        self.particles.draw(surface)

    # --- Track texture (enhanced with subtle gradients) ---

    def _draw_track_texture(self, surface: pygame.Surface) -> None:
        cx, cy = self._w2s(BOARD_CX, BOARD_CY)
        z = self.camera.zoom
        icx, icy = int(cx), int(cy)

        # Crowd / stands with gradient
        for i in range(len(CROWD_SHADES) - 1, -1, -1):
            r = int((370 + i * 14) * z)
            if r < 1:
                continue
            pygame.draw.circle(surface, CROWD_SHADES[i], (icx, icy), r)

        # Ring fills
        for ring in [Ring.CANNON, Ring.UPPER, Ring.MIDDLE, Ring.LOWER, Ring.FLOOR]:
            _, outer = RING_RADII[ring]
            ro = int(outer * z)
            if ro < 1:
                continue
            pygame.draw.circle(surface, RING_FILLS[ring], (icx, icy), ro)

        # Central area with subtle glow
        floor_inner = int(RING_RADII[Ring.FLOOR][0] * z)
        if floor_inner > 0:
            pygame.draw.circle(surface, CENTRAL_FILL, (icx, icy), floor_inner)
            # Glow ring at center edge
            glow_r = floor_inner + int(3 * z)
            if glow_r > floor_inner:
                glow_surf = pygame.Surface(
                    (glow_r * 2 + 4, glow_r * 2 + 4), pygame.SRCALPHA,
                )
                pygame.draw.circle(
                    glow_surf,
                    (*CENTRAL_GLOW, 40),
                    (glow_r + 2, glow_r + 2),
                    glow_r,
                    max(1, int(3 * z)),
                )
                surface.blit(
                    glow_surf,
                    (icx - glow_r - 2, icy - glow_r - 2),
                    special_flags=pygame.BLEND_ADD,
                )
            pygame.draw.circle(surface, LANE_LINE, (icx, icy), floor_inner, 1)

        # Lane divider lines (brighter on inner edge)
        for ring in Ring:
            inner, outer = RING_RADII[ring]
            ri = int(inner * z)
            ro = int(outer * z)
            if ro > 1:
                pygame.draw.circle(surface, LANE_LINE, (icx, icy), ro, 1)
            if ri > 1:
                pygame.draw.circle(surface, LANE_LINE_BRIGHT, (icx, icy), ri, 1)

    # --- Squares ---

    def _draw_squares(self, surface: pygame.Surface, game: Any) -> None:
        z = self.camera.zoom
        for sector_index, sector in enumerate(game.board.sectors):
            base_start = -math.pi / 2 + sector_index * (2 * math.pi / NUM_TRACK_SECTORS)
            sector_span = 2 * math.pi / NUM_TRACK_SECTORS
            for ring in Ring:
                inner_r, outer_r = RING_RADII[ring]
                sq_count = SQUARES_PER_RING[ring]
                for position in range(sq_count):
                    start = base_start + (sector_span / sq_count) * position
                    end = start + (sector_span / sq_count)
                    raw_pts = _wedge_points(
                        BOARD_CX, BOARD_CY, inner_r, outer_r, start, end,
                    )
                    screen_pts = [self._w2s(p[0], p[1]) for p in raw_pts]
                    int_pts = [(int(x), int(y)) for x, y in screen_pts]

                    sq = game.board.get_square(sector_index, ring, position)
                    fill = RING_FILLS.get(ring, (31, 41, 55))
                    if ring == Ring.CANNON:
                        fill = (45, 55, 72)
                    if sq.is_goal:
                        if sq.goal_side.value == "home":
                            fill = GOAL_HOME_FILL
                        else:
                            fill = GOAL_VISITOR_FILL
                    brightness = RING_BRIGHTNESS.get(ring, 1.0)
                    fill = _apply_brightness(fill, brightness)

                    if len(int_pts) >= 3:
                        pygame.draw.polygon(surface, fill, int_pts)
                        outline = LANE_LINE
                        width = 1
                        if sector_index == game.current_initiative_sector:
                            outline = INITIATIVE_OUTLINE
                            width = 2
                        pygame.draw.polygon(surface, outline, int_pts, width)

            # Sector label
            mid_angle = base_start + sector_span / 2
            lx = BOARD_CX + math.cos(mid_angle) * 362
            ly = BOARD_CY + math.sin(mid_angle) * 362
            slx, sly = self._w2s(lx, ly)
            font = self._font(max(7, int(10 * z)), bold=True)
            label_surf = font.render(sector.name, True, TEXT_PRIMARY)
            surface.blit(
                label_surf,
                (int(slx) - label_surf.get_width() // 2,
                 int(sly) - label_surf.get_height() // 2),
            )

    # --- Ring gradient overlay (Tier 3) ---

    def _draw_ring_gradient_overlay(self, surface: pygame.Surface) -> None:
        """Subtle gradient overlay on each ring to simulate incline lighting."""
        cx, cy = self._w2s(BOARD_CX, BOARD_CY)
        z = self.camera.zoom
        icx, icy = int(cx), int(cy)

        for ring in Ring:
            inner, outer = RING_RADII[ring]
            ri = int(inner * z)
            ro = int(outer * z)
            mid_r = (ri + ro) // 2
            if mid_r < 2:
                continue

            grad_surf = pygame.Surface(
                (ro * 2 + 4, ro * 2 + 4), pygame.SRCALPHA,
            )
            # Draw a subtle radial brightness boost on the inner edge
            alpha = AMBIENT_GLOW_ALPHA
            grad_color = RING_GRADIENT_INNER.get(ring, (40, 50, 70))
            pygame.draw.circle(
                grad_surf,
                (*grad_color, alpha),
                (ro + 2, ro + 2),
                mid_r,
                max(1, (ro - ri) // 2),
            )
            surface.blit(
                grad_surf,
                (icx - ro - 2, icy - ro - 2),
                special_flags=pygame.BLEND_ADD,
            )

    # --- Lighting (enhanced spotlight with soft edge) ---

    def _draw_lighting(self, surface: pygame.Surface, game: Any) -> None:
        if game.ball.carrier is None:
            return
        sq = game.board.find_square_of_figure(game.ball.carrier)
        if sq is None:
            return
        wx, wy = _slot_center(sq, game.ball.carrier.slot_index or 0)
        sx, sy = self._w2s(wx, wy)
        r = int(SPOTLIGHT_RADIUS * self.camera.zoom)
        if r < 5:
            return
        spotlight = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        # Multi-layer soft spotlight
        for i in range(r, 0, -2):
            frac = i / r
            alpha = int(SPOTLIGHT_ALPHA * frac * frac)
            pygame.draw.circle(
                spotlight, (255, 240, 200, alpha), (r, r), i,
            )
        surface.blit(
            spotlight,
            (int(sx) - r, int(sy) - r),
            special_flags=pygame.BLEND_ADD,
        )

    # --- Shadows (enhanced with soft edges) ---

    def _draw_shadows(self, surface: pygame.Surface, game: Any) -> None:
        z = self.camera.zoom
        for fig in game.all_figures():
            sq = game.board.find_square_of_figure(fig)
            if sq is None:
                continue
            shadow_len = SHADOW_LENGTH_FACTOR.get(sq.ring, 0.0)
            if shadow_len < 0.5:
                continue
            wx, wy = _slot_center(sq, fig.slot_index or 0)
            sx, sy = self._w2s(wx, wy)
            sr = int(14 * z)
            sh = int(shadow_len * z)
            w = sr * 2 + 6
            h = sh + sr + 6
            if w < 2 or h < 2:
                continue
            shadow_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            # Soft shadow ellipse
            for layer in range(3):
                expand = layer * 2
                alpha = max(5, 35 - layer * 12)
                pygame.draw.ellipse(
                    shadow_surf,
                    (0, 0, 0, alpha),
                    (3 - expand, sh - expand, sr * 2 + expand * 2, sr + expand * 2),
                )
            surface.blit(shadow_surf, (int(sx) - sr - 3, int(sy) - 3))

    # --- Highlights (status markers) ---

    def _draw_highlights(self, surface: pygame.Surface, game: Any) -> None:
        z = self.camera.zoom
        for fig in game.all_figures():
            sq = game.board.find_square_of_figure(fig)
            if sq is None:
                continue
            wx, wy = _square_center(sq)
            sx, sy = self._w2s(wx, wy)
            isx, isy = int(sx), int(sy)
            r20 = int(20 * z)
            r24 = int(24 * z)
            r6 = int(6 * z)

            if fig.needs_stand_up:
                pygame.draw.circle(
                    surface, (245, 165, 20), (isx, isy),
                    max(1, r20), max(1, int(3 * z)),
                )
            if fig.status == FigureStatus.MAN_TO_MAN:
                pygame.draw.rect(
                    surface,
                    (175, 90, 255),
                    (isx - r24, isy - r24, r24 * 2, r24 * 2),
                    max(1, int(2 * z)),
                )
            if fig.has_moved:
                if r6 > 0:
                    pygame.draw.circle(surface, (254, 242, 145), (isx, isy), r6)

            # Tow bar indicator
            if getattr(fig, "is_towed", False):
                biker = getattr(fig, "towed_by", None)
                if biker is not None:
                    bsq = game.board.find_square_of_figure(biker)
                    if bsq is not None:
                        bwx, bwy = _square_center(bsq)
                        bsx, bsy = self._w2s(bwx, bwy)
                        # Glowing tow line
                        pygame.draw.line(
                            surface,
                            (40, 210, 100),
                            (isx, isy),
                            (int(bsx), int(bsy)),
                            max(1, int(3 * z)),
                        )
                        # Thin bright center line
                        pygame.draw.line(
                            surface,
                            (120, 255, 160),
                            (isx, isy),
                            (int(bsx), int(bsy)),
                            max(1, int(1 * z)),
                        )

            # Endurance warning
            endurance_used = getattr(fig, "endurance_used", 0)
            max_e = getattr(fig, "base_toughness", 7) + 3
            if endurance_used > max_e:
                font = self._font(max(6, int(9 * z)), bold=True)
                warn = font.render("E!", True, (255, 80, 80))
                surface.blit(warn, (int(sx + 15 * z), int(sy - 15 * z)))

        # Obstacles and fire
        for sector in game.board.sectors:
            for sq in sector.all_squares():
                if not sq.has_obstacle and not sq.is_on_fire:
                    continue
                wx, wy = _square_center(sq)
                sx, sy = self._w2s(wx, wy)
                marker = "!" if sq.has_obstacle else "*"
                color = (255, 200, 50) if sq.has_obstacle else (255, 80, 80)
                font = self._font(max(8, int(14 * z)), bold=True)
                txt = font.render(marker, True, color)
                surface.blit(
                    txt,
                    (int(sx) - txt.get_width() // 2,
                     int(sy) - txt.get_height() // 2),
                )

    # --- Figures (Tier 3 animated sprites with glow) ---

    def _draw_figures(self, surface: pygame.Surface, game: Any) -> None:
        z = self.camera.zoom
        for fig in game.all_figures():
            sq = game.board.find_square_of_figure(fig)
            if sq is None:
                continue
            wx, wy = _slot_center(sq, fig.slot_index or 0)
            sx, sy = self._w2s(wx, wy)
            isx, isy = int(sx), int(sy)

            ftype = fig.figure_type.value
            team_side = fig.team.value
            label = FIGURE_LABELS.get(
                ftype, ftype[0].upper() if ftype else "?",
            )

            if team_side == "home":
                pal = SPRITE_COLORS_HOME.get(
                    ftype,
                    {"fill": (65, 140, 255), "accent": (30, 60, 100), "glow": (100, 170, 255)},
                )
            else:
                pal = SPRITE_COLORS_VISITOR.get(
                    ftype,
                    {"fill": (245, 75, 75), "accent": (130, 30, 30), "glow": (255, 120, 120)},
                )
            fill = pal["fill"]
            accent = pal["accent"]
            glow = pal.get("glow", fill)

            if fig.needs_stand_up or fig.status in (
                FigureStatus.UNCONSCIOUS,
                FigureStatus.DEAD,
            ):
                fill = INJURED_FILL
                accent = INJURED_ACCENT
                glow = INJURED_GLOW

            brightness = RING_BRIGHTNESS.get(sq.ring, 1.0)
            fill = _apply_brightness(fill, brightness)
            accent = _apply_brightness(accent, brightness)
            glow = _apply_brightness(glow, brightness)

            r = int(14 * z)
            sr = int(10 * z)

            anim = self.get_anim(fig)
            wobble = anim.wobble * z
            pulse_scale = 1.0 + anim.pulse

            draw_x = isx + int(wobble)
            draw_y = isy
            draw_r = int(r * pulse_scale)

            if draw_r < 2:
                continue

            # Glow halo (Tier 3)
            glow_r = int(draw_r * 1.6)
            if glow_r > 2:
                glow_surf = pygame.Surface(
                    (glow_r * 2 + 4, glow_r * 2 + 4), pygame.SRCALPHA,
                )
                pygame.draw.circle(
                    glow_surf,
                    (*glow, 25),
                    (glow_r + 2, glow_r + 2),
                    glow_r,
                )
                surface.blit(
                    glow_surf,
                    (draw_x - glow_r - 2, draw_y - glow_r - 2),
                    special_flags=pygame.BLEND_ADD,
                )

            # Type-specific shape
            if ftype == "biker":
                pts = [
                    (draw_x, draw_y - draw_r),
                    (draw_x + draw_r, draw_y),
                    (draw_x, draw_y + draw_r),
                    (draw_x - draw_r, draw_y),
                ]
                pygame.draw.polygon(surface, fill, pts)
                pygame.draw.polygon(
                    surface, (255, 255, 255), pts, max(1, int(2 * z)),
                )
                inner_pts = [
                    (draw_x, draw_y - sr),
                    (draw_x + sr, draw_y),
                    (draw_x, draw_y + sr),
                    (draw_x - sr, draw_y),
                ]
                if sr > 1:
                    pygame.draw.polygon(surface, accent, inner_pts)
            elif ftype == "catcher":
                rect = pygame.Rect(
                    draw_x - draw_r,
                    draw_y - int(draw_r * 0.8),
                    draw_r * 2,
                    int(draw_r * 1.6),
                )
                pygame.draw.ellipse(surface, fill, rect)
                pygame.draw.ellipse(
                    surface, (255, 255, 255), rect, max(1, int(2 * z)),
                )
                inner_rect = pygame.Rect(
                    draw_x - int(draw_r * 0.5),
                    draw_y - int(draw_r * 0.5),
                    draw_r,
                    draw_r,
                )
                pygame.draw.ellipse(surface, accent, inner_rect)
            elif ftype == "speeder":
                pts = [
                    (draw_x, draw_y - draw_r),
                    (draw_x + int(draw_r * 0.9), draw_y + int(draw_r * 0.7)),
                    (draw_x - int(draw_r * 0.9), draw_y + int(draw_r * 0.7)),
                ]
                pygame.draw.polygon(surface, fill, pts)
                pygame.draw.polygon(
                    surface, (255, 255, 255), pts, max(1, int(2 * z)),
                )
                pygame.draw.line(
                    surface,
                    accent,
                    (draw_x - int(draw_r * 0.6), draw_y + int(draw_r * 0.3)),
                    (draw_x + int(draw_r * 0.6), draw_y + int(draw_r * 0.3)),
                    max(1, int(z)),
                )
            else:  # bruiser
                pygame.draw.circle(surface, fill, (draw_x, draw_y), draw_r)
                pygame.draw.circle(
                    surface,
                    (255, 255, 255),
                    (draw_x, draw_y),
                    draw_r,
                    max(1, int(2 * z)),
                )
                inner_r = int(sr * 0.6)
                if inner_r > 0:
                    pygame.draw.circle(
                        surface, accent, (draw_x, draw_y), inner_r,
                    )

            # Type label
            font = self._font(max(7, int(10 * z)), bold=True)
            lbl = font.render(label, True, (255, 255, 255))
            surface.blit(
                lbl,
                (draw_x - lbl.get_width() // 2, draw_y - lbl.get_height() // 2),
            )

            # Ball indicator
            if fig.has_ball:
                br = int(6 * z)
                bx = draw_x + int(draw_r * 0.6)
                by = draw_y - draw_r
                if br > 0:
                    # Ball glow
                    bg_r = int(br * 1.8)
                    if bg_r > 0:
                        g_surf = pygame.Surface(
                            (bg_r * 2 + 4, bg_r * 2 + 4), pygame.SRCALPHA,
                        )
                        pygame.draw.circle(
                            g_surf,
                            (255, 180, 50, 40),
                            (bg_r + 2, bg_r + 2),
                            bg_r,
                        )
                        surface.blit(
                            g_surf,
                            (bx + br - bg_r - 2, by + br - bg_r - 2),
                            special_flags=pygame.BLEND_ADD,
                        )
                    pygame.draw.circle(
                        surface, (255, 130, 30), (bx + br, by + br), br,
                    )
                    pygame.draw.circle(
                        surface,
                        (255, 250, 240),
                        (bx + br, by + br),
                        br,
                        max(1, int(z)),
                    )

            # Store rect for click detection
            hit_rect = pygame.Rect(
                draw_x - draw_r, draw_y - draw_r, draw_r * 2, draw_r * 2,
            )
            self.figure_rects[id(fig)] = (hit_rect, fig)

    # --- Speed lines (Tier 3 effect) ---

    def _draw_speed_lines(self, surface: pygame.Surface, game: Any) -> None:
        z = self.camera.zoom
        for fig in game.all_figures():
            if not fig.has_moved:
                continue
            if fig.speed < SPEED_LINE_THRESHOLD:
                continue
            sq = game.board.find_square_of_figure(fig)
            if sq is None:
                continue
            wx, wy = _slot_center(sq, fig.slot_index or 0)
            sx, sy = self._w2s(wx, wy)

            # Direction based on sector angle (counter-clockwise movement)
            sector_angle = (
                -math.pi / 2
                + sq.sector_index * (2 * math.pi / NUM_TRACK_SECTORS)
                + math.pi / NUM_TRACK_SECTORS
            )
            trail_angle = sector_angle + math.pi  # behind the figure

            line_len = int(SPEED_LINE_LENGTH * z * (fig.speed / 8.0))
            line_surf = pygame.Surface(
                (line_len * 2 + 20, line_len * 2 + 20), pygame.SRCALPHA,
            )
            center = line_len + 10
            for i in range(SPEED_LINE_COUNT):
                offset_angle = trail_angle + (i - 1) * 0.15
                ex = center + math.cos(offset_angle) * line_len
                ey = center + math.sin(offset_angle) * line_len
                alpha = max(20, SPEED_LINE_ALPHA - i * 25)
                color = (200, 220, 255, alpha)
                pygame.draw.line(
                    line_surf,
                    color,
                    (center, center),
                    (int(ex), int(ey)),
                    max(1, int(z)),
                )
            surface.blit(
                line_surf,
                (int(sx) - center, int(sy) - center),
                special_flags=pygame.BLEND_ADD,
            )

    # --- Ball (Tier 3 with heat glow and shimmer) ---

    def _draw_ball(self, surface: pygame.Surface, game: Any) -> None:
        z = self.camera.zoom
        if game.ball.state.value == "not_in_play":
            return

        if game.ball.carrier is not None:
            sq = game.board.find_square_of_figure(game.ball.carrier)
            if sq is None:
                return
            wx, wy = _slot_center(sq, game.ball.carrier.slot_index or 0)
            wx += 18
            wy -= 18
        else:
            sq = game.board.get_square(
                game.ball.sector_index,
                game.ball.ring,
                game.ball.position,
            )
            wx, wy = _square_center(sq)

        sx, sy = self._w2s(wx, wy)
        isx, isy = int(sx), int(sy)

        temp_val = game.ball.temperature.value
        ball_color = BALL_TEMP_COLORS.get(temp_val, BALL_DEFAULT)
        glow_color = BALL_GLOW_COLORS.get(temp_val, BALL_GLOW_DEFAULT)
        shimmer_color = BALL_SHIMMER_COLORS.get(temp_val, glow_color)

        r = int(9 * z)
        gr = int(r * 2.2)
        if r < 1:
            return

        # Heat shimmer (Tier 3) — animated glow that pulses
        shimmer_phase = math.sin(self._time_accum * SHIMMER_FREQUENCY) * SHIMMER_AMPLITUDE + SHIMMER_BASELINE
        shimmer_r = int(gr * (1.0 + shimmer_phase * 0.2))
        if shimmer_r > 2:
            shimmer_surf = pygame.Surface(
                (shimmer_r * 2 + 4, shimmer_r * 2 + 4), pygame.SRCALPHA,
            )
            shimmer_alpha = int(30 * shimmer_phase)
            pygame.draw.circle(
                shimmer_surf,
                (*shimmer_color, shimmer_alpha),
                (shimmer_r + 2, shimmer_r + 2),
                shimmer_r,
            )
            surface.blit(
                shimmer_surf,
                (isx - shimmer_r - 2, isy - shimmer_r - 2),
                special_flags=pygame.BLEND_ADD,
            )

        # Glow ring
        if gr > 1:
            pygame.draw.circle(
                surface, glow_color, (isx, isy), gr, max(1, int(2 * z)),
            )
        # Ball body
        pygame.draw.circle(surface, ball_color, (isx, isy), r)
        pygame.draw.circle(
            surface, (255, 250, 240), (isx, isy), r, max(1, int(2 * z)),
        )
        # Highlight spot
        hr = max(1, r // 3)
        pygame.draw.circle(
            surface, (255, 255, 255), (isx - r // 3, isy - r // 3), hr,
        )

    # --- Movement options overlay ---

    def _draw_move_options(
        self, surface: pygame.Surface, options: List[Tuple[Any, int]],
    ) -> None:
        z = self.camera.zoom
        self._move_option_rects.clear()
        for sq, cost in options:
            wx, wy = _square_center(sq)
            sx, sy = self._w2s(wx, wy)
            isx, isy = int(sx), int(sy)
            r = int(22 * z)
            if r < 2:
                continue

            # Glow ring
            glow_surf = pygame.Surface(
                (r * 2 + 8, r * 2 + 8), pygame.SRCALPHA,
            )
            pygame.draw.circle(
                glow_surf, (50, 220, 255, 35), (r + 4, r + 4), r + 2,
            )
            surface.blit(
                glow_surf,
                (isx - r - 4, isy - r - 4),
                special_flags=pygame.BLEND_ADD,
            )

            pygame.draw.circle(
                surface, TEXT_HIGHLIGHT, (isx, isy), r, max(1, int(3 * z)),
            )
            fill_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(fill_surf, (50, 220, 255, 25), (r, r), r)
            surface.blit(fill_surf, (isx - r, isy - r))

            font = self._font(max(7, int(9 * z)), bold=True)
            cost_surf = font.render(str(cost), True, (110, 235, 255))
            surface.blit(
                cost_surf,
                (isx - cost_surf.get_width() // 2, isy + r + 4),
            )

            hit_rect = pygame.Rect(isx - r, isy - r, r * 2, r * 2)
            self._move_option_rects.append((hit_rect, sq))

    # --- Goal flash overlay (Tier 3) ---

    def _draw_goal_flash(self, surface: pygame.Surface) -> None:
        if self._goal_flash_timer <= 0:
            return
        frac = self._goal_flash_timer / GOAL_FLASH_DURATION_MS
        alpha = int(GOAL_FLASH_ALPHA_MAX * frac * frac)
        if alpha < 1:
            return
        flash_surf = pygame.Surface((920, surface.get_height()), pygame.SRCALPHA)
        flash_surf.fill((*GOAL_FLASH_COLOR, alpha))
        surface.blit(flash_surf, (0, 0))

    # --- Canvas scoreboard overlay ---

    def _draw_canvas_scoreboard(
        self, surface: pygame.Surface, game: Any,
    ) -> None:
        snapshot = game.snapshot()
        scores = snapshot["scores"]
        names = list(scores.keys())
        score_text = "  |  ".join(f"{n}: {scores[n]}" for n in names)
        clock_text = (
            f"Period {snapshot['period']}  \u00b7  "
            f"Turn {snapshot['turn']}  \u00b7  "
            f"{snapshot['time_remaining']}:00"
        )

        status_text = ""
        if game.game_over:
            result = game.match_result()
            status_text = "DRAW" if result == "Draw" else f"WINNER: {result}"

        font_big = self._font(12, bold=True)
        font_sm = self._font(9)
        font_st = self._font(10, bold=True)

        lines_count = 2 + (1 if status_text else 0)
        line_h = 18
        pad = 8
        box_w = 255
        box_h = lines_count * line_h + pad * 2
        right = 895
        top = 14

        # Rounded scoreboard box
        box_rect = pygame.Rect(right - box_w, top - pad, box_w + 4, box_h)
        box_surf = pygame.Surface(
            (box_rect.width, box_rect.height), pygame.SRCALPHA,
        )
        box_surf.fill((22, 30, 46, 200))
        surface.blit(box_surf, box_rect.topleft)
        pygame.draw.rect(surface, (80, 100, 135), box_rect, 1)

        cx_text = right - box_w // 2
        score_surf = font_big.render(score_text, True, TEXT_PRIMARY)
        surface.blit(
            score_surf,
            (cx_text - score_surf.get_width() // 2, top + 2),
        )
        clock_surf = font_sm.render(clock_text, True, TEXT_SECONDARY)
        surface.blit(
            clock_surf,
            (cx_text - clock_surf.get_width() // 2, top + line_h + 2),
        )
        if status_text:
            st_surf = font_st.render(status_text, True, TEXT_ACCENT)
            surface.blit(
                st_surf,
                (cx_text - st_surf.get_width() // 2, top + line_h * 2 + 2),
            )

    # --- Particle effect helpers ---

    def emit_cannon_particles(self) -> None:
        cx, cy = self._w2s(BOARD_CX, BOARD_CY - 305)
        self.particles.emit_cannon(cx, cy)

    def emit_crash_particles(self, wx: float, wy: float) -> None:
        sx, sy = self._w2s(wx, wy)
        self.particles.emit_crash(sx, sy)

    def emit_goal_particles(self) -> None:
        cx, cy = self._w2s(BOARD_CX, BOARD_CY)
        self.particles.emit_goal(cx, cy)
        self._goal_flash_timer = GOAL_FLASH_DURATION_MS

    def emit_exhaust_particles(
        self, wx: float, wy: float, direction: float,
    ) -> None:
        sx, sy = self._w2s(wx, wy)
        self.particles.emit_exhaust(sx, sy, direction)

    def emit_dust_particles(self, wx: float, wy: float) -> None:
        sx, sy = self._w2s(wx, wy)
        self.particles.emit_dust(sx, sy)

    # --- Hit testing ---

    def figure_at(self, screen_x: int, screen_y: int) -> Optional[Any]:
        for _fid, (rect, fig) in self.figure_rects.items():
            if rect.collidepoint(screen_x, screen_y):
                return fig
        return None

    def move_option_at(self, screen_x: int, screen_y: int) -> Optional[Any]:
        for rect, sq in self._move_option_rects:
            if rect.collidepoint(screen_x, screen_y):
                return sq
        return None
