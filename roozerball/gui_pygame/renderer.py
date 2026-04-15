"""Tier 2 renderer — Pygame-based board, sprites, particles, camera, and lighting.

Replaces the Tkinter canvas with hardware-accelerated Pygame surfaces.
Provides animated sprites, a camera system with smooth scrolling, incline
lighting with shadows, and a GPU-friendly particle system.
"""
from __future__ import annotations

import math
import random as _rng
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pygame

from roozerball.engine.constants import (
    FigureStatus,
    FigureType,
    Ring,
    SQUARES_PER_RING,
    TeamSide,
)
from roozerball.gui_pygame.constants import (
    ANIM_FRAME_DURATION_MS,
    ANIM_FRAMES_COMBAT,
    ANIM_FRAMES_IDLE,
    ANIM_FRAMES_MOVE,
    BALL_DEFAULT,
    BALL_GLOW_COLORS,
    BALL_GLOW_DEFAULT,
    BALL_TEMP_COLORS,
    BG_COLOR,
    BOARD_CX,
    BOARD_CY,
    CAMERA_LERP_SPEED,
    CAMERA_MAX_ZOOM,
    CAMERA_MIN_ZOOM,
    CAMERA_ZOOM_STEP,
    CENTRAL_FILL,
    CROWD_SHADES,
    FIGURE_LABELS,
    GOAL_HOME_FILL,
    GOAL_VISITOR_FILL,
    INITIATIVE_OUTLINE,
    INJURED_ACCENT,
    INJURED_FILL,
    LANE_LINE,
    PARTICLE_COUNT_CANNON,
    PARTICLE_COUNT_CRASH,
    PARTICLE_COUNT_GOAL,
    PARTICLE_LIFETIME_MS,
    RING_BRIGHTNESS,
    RING_FILLS,
    RING_RADII,
    SHADOW_LENGTH_FACTOR,
    SLOT_OFFSETS,
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


# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------


class Camera:
    """Smooth-scrolling camera with zoom and target following."""

    def __init__(self) -> None:
        self.x: float = 0.0
        self.y: float = 0.0
        self.zoom: float = 1.0
        self._target_x: float = 0.0
        self._target_y: float = 0.0
        self._target_zoom: float = 1.0
        self._following: Optional[Any] = None  # figure to follow
        self._locked_sector: Optional[int] = None

    def reset(self) -> None:
        self.x = self._target_x = 0.0
        self.y = self._target_y = 0.0
        self.zoom = self._target_zoom = 1.0
        self._following = None
        self._locked_sector = None

    def follow(self, figure: Optional[Any]) -> None:
        """Follow a specific figure (e.g. ball carrier)."""
        self._following = figure
        self._locked_sector = None

    def lock_sector(self, sector_index: Optional[int]) -> None:
        """Lock view to a sector."""
        self._locked_sector = sector_index
        self._following = None

    def zoom_in(self) -> None:
        self._target_zoom = min(CAMERA_MAX_ZOOM,
                                self._target_zoom + CAMERA_ZOOM_STEP)

    def zoom_out(self) -> None:
        self._target_zoom = max(CAMERA_MIN_ZOOM,
                                self._target_zoom - CAMERA_ZOOM_STEP)

    def pan(self, dx: float, dy: float) -> None:
        self._target_x += dx / self.zoom
        self._target_y += dy / self.zoom
        self._following = None
        self._locked_sector = None

    def update(self, board: Any = None) -> None:
        """Advance camera toward target (call once per frame)."""
        if self._following is not None and board is not None:
            sq = board.find_square_of_figure(self._following)
            if sq is not None:
                wx, wy = _square_center(sq)
                self._target_x = -(wx - BOARD_CX)
                self._target_y = -(wy - BOARD_CY)

        if self._locked_sector is not None:
            angle = -math.pi / 2 + self._locked_sector * (2 * math.pi / 12) + math.pi / 12
            dist = 200
            self._target_x = -(BOARD_CX + math.cos(angle) * dist - BOARD_CX)
            self._target_y = -(BOARD_CY + math.sin(angle) * dist - BOARD_CY)

        lerp = CAMERA_LERP_SPEED
        self.x += (self._target_x - self.x) * lerp
        self.y += (self._target_y - self.y) * lerp
        self.zoom += (self._target_zoom - self.zoom) * lerp

    def world_to_screen(self, wx: float, wy: float) -> Tuple[float, float]:
        """Transform a world coordinate to screen coordinate."""
        sx = (wx - BOARD_CX + self.x) * self.zoom + BOARD_CX
        sy = (wy - BOARD_CY + self.y) * self.zoom + BOARD_CY
        return sx, sy


# ---------------------------------------------------------------------------
# Particle system
# ---------------------------------------------------------------------------


class _Particle:
    __slots__ = ("x", "y", "vx", "vy", "color", "size", "life", "max_life")

    def __init__(self, x: float, y: float, vx: float, vy: float,
                 color: Tuple[int, int, int], size: float, lifetime: int) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.life = lifetime
        self.max_life = lifetime


class ParticleSystem:
    """Lightweight particle manager rendered onto a Pygame surface."""

    def __init__(self) -> None:
        self._particles: List[_Particle] = []

    def emit(self, x: float, y: float, count: int, *,
             colors: Optional[List[Tuple[int, int, int]]] = None,
             speed_range: Tuple[float, float] = (1.0, 4.0),
             size_range: Tuple[float, float] = (2.0, 5.0),
             lifetime: int = PARTICLE_LIFETIME_MS) -> None:
        if colors is None:
            colors = [(251, 191, 36), (249, 115, 22), (239, 68, 68), (255, 255, 255)]
        for _ in range(count):
            angle = _rng.uniform(0, 2 * math.pi)
            speed = _rng.uniform(*speed_range)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            color = _rng.choice(colors)
            size = _rng.uniform(*size_range)
            self._particles.append(_Particle(x, y, vx, vy, color, size, lifetime))

    def update(self, dt_ms: float) -> None:
        alive: List[_Particle] = []
        for p in self._particles:
            p.life -= dt_ms
            if p.life <= 0:
                continue
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.15  # gravity
            alive.append(p)
        self._particles = alive

    def draw(self, surface: pygame.Surface) -> None:
        for p in self._particles:
            alpha = max(0.0, p.life / p.max_life)
            size = max(1, int(p.size * alpha))
            if size < 1:
                continue
            r, g, b = p.color
            # Fade by reducing towards background
            fr = int(r * alpha)
            fg = int(g * alpha)
            fb = int(b * alpha)
            pygame.draw.circle(surface, (fr, fg, fb), (int(p.x), int(p.y)), size)

    def clear(self) -> None:
        self._particles.clear()

    @property
    def active(self) -> bool:
        return bool(self._particles)


# ---------------------------------------------------------------------------
# Animated sprite data
# ---------------------------------------------------------------------------


class SpriteAnimation:
    """Holds per-figure animation state for frame-by-frame cycling."""

    __slots__ = ("action", "frame", "timer", "total_frames")

    def __init__(self) -> None:
        self.action: str = "idle"  # idle, move, combat
        self.frame: int = 0
        self.timer: float = 0.0
        self.total_frames: int = ANIM_FRAMES_IDLE

    def set_action(self, action: str) -> None:
        if action == self.action:
            return
        self.action = action
        self.frame = 0
        self.timer = 0.0
        if action == "move":
            self.total_frames = ANIM_FRAMES_MOVE
        elif action == "combat":
            self.total_frames = ANIM_FRAMES_COMBAT
        else:
            self.total_frames = ANIM_FRAMES_IDLE

    def update(self, dt_ms: float) -> None:
        self.timer += dt_ms
        if self.timer >= ANIM_FRAME_DURATION_MS:
            self.timer -= ANIM_FRAME_DURATION_MS
            self.frame = (self.frame + 1) % self.total_frames


# ---------------------------------------------------------------------------
# Geometry helpers (module-level, shared)
# ---------------------------------------------------------------------------


def _square_center(square: Any) -> Tuple[float, float]:
    inner, outer = RING_RADII[square.ring]
    sector_span = 2 * math.pi / 12
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
    cx: float, cy: float,
    inner_r: float, outer_r: float,
    start: float, end: float,
) -> List[Tuple[float, float]]:
    return [
        (cx + math.cos(start) * inner_r, cy + math.sin(start) * inner_r),
        (cx + math.cos(start) * outer_r, cy + math.sin(start) * outer_r),
        (cx + math.cos(end) * outer_r,   cy + math.sin(end) * outer_r),
        (cx + math.cos(end) * inner_r,   cy + math.sin(end) * inner_r),
    ]


def _apply_brightness(color: Tuple[int, int, int],
                       factor: float) -> Tuple[int, int, int]:
    return (
        min(255, int(color[0] * factor)),
        min(255, int(color[1] * factor)),
        min(255, int(color[2] * factor)),
    )


# ---------------------------------------------------------------------------
# Board renderer
# ---------------------------------------------------------------------------


class BoardRenderer:
    """Draws the circular track, figures, ball, lighting, and effects."""

    def __init__(self) -> None:
        self.camera = Camera()
        self.particles = ParticleSystem()
        self._animations: Dict[int, SpriteAnimation] = {}  # figure id → anim
        self.figure_rects: Dict[int, Tuple[pygame.Rect, Any]] = {}  # rect → figure
        self._move_option_rects: List[Tuple[pygame.Rect, Any]] = []
        self._font_cache: Dict[Tuple[int, bool], pygame.font.Font] = {}

    def _font(self, size: int, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        if key not in self._font_cache:
            self._font_cache[key] = pygame.font.SysFont(
                "arial,helvetica,sans-serif", size, bold=bold)
        return self._font_cache[key]

    def get_anim(self, figure: Any) -> SpriteAnimation:
        fid = id(figure)
        if fid not in self._animations:
            self._animations[fid] = SpriteAnimation()
        return self._animations[fid]

    def update(self, dt_ms: float, game: Any) -> None:
        """Per-frame update for camera, particles, and sprite animations."""
        self.camera.update(game.board if game else None)
        self.particles.update(dt_ms)
        for fig in game.all_figures():
            anim = self.get_anim(fig)
            if fig.has_moved:
                anim.set_action("move")
            elif fig.status == FigureStatus.MAN_TO_MAN:
                anim.set_action("combat")
            else:
                anim.set_action("idle")
            anim.update(dt_ms)

    def _w2s(self, wx: float, wy: float) -> Tuple[float, float]:
        """Shortcut for world-to-screen."""
        return self.camera.world_to_screen(wx, wy)

    def draw(self, surface: pygame.Surface, game: Any,
             selected_figure: Optional[Any] = None,
             move_options: Optional[List[Tuple[Any, int]]] = None) -> None:
        """Render the full board onto *surface*."""
        # Clear board area
        board_rect = pygame.Rect(0, 0, 920, surface.get_height())
        surface.fill(BG_COLOR, board_rect)

        self.figure_rects.clear()
        self._move_option_rects.clear()

        self._draw_track_texture(surface)
        self._draw_squares(surface, game)
        self._draw_lighting(surface, game)
        self._draw_highlights(surface, game)
        self._draw_shadows(surface, game)
        self._draw_figures(surface, game)
        self._draw_ball(surface, game)
        if selected_figure is not None and move_options:
            self._draw_move_options(surface, move_options)
        self._draw_canvas_scoreboard(surface, game)
        self.particles.draw(surface)

    # --- Track texture ---

    def _draw_track_texture(self, surface: pygame.Surface) -> None:
        cx, cy = self._w2s(BOARD_CX, BOARD_CY)
        z = self.camera.zoom
        icx, icy = int(cx), int(cy)

        # Crowd / stands gradient
        for i in range(4, -1, -1):
            r = int((360 + i * 15) * z)
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

        # Central area
        floor_inner = int(RING_RADII[Ring.FLOOR][0] * z)
        if floor_inner > 0:
            pygame.draw.circle(surface, CENTRAL_FILL, (icx, icy), floor_inner)
            pygame.draw.circle(surface, LANE_LINE, (icx, icy), floor_inner, 1)

        # Lane divider lines
        for ring in Ring:
            _, outer = RING_RADII[ring]
            ro = int(outer * z)
            if ro > 1:
                pygame.draw.circle(surface, LANE_LINE, (icx, icy), ro, 1)

    # --- Squares ---

    def _draw_squares(self, surface: pygame.Surface, game: Any) -> None:
        z = self.camera.zoom
        for sector_index, sector in enumerate(game.board.sectors):
            base_start = -math.pi / 2 + sector_index * (2 * math.pi / 12)
            sector_span = 2 * math.pi / 12
            for ring in Ring:
                inner_r, outer_r = RING_RADII[ring]
                sq_count = SQUARES_PER_RING[ring]
                for position in range(sq_count):
                    start = base_start + (sector_span / sq_count) * position
                    end = start + (sector_span / sq_count)
                    raw_pts = _wedge_points(BOARD_CX, BOARD_CY,
                                            inner_r, outer_r, start, end)
                    screen_pts = [self._w2s(p[0], p[1]) for p in raw_pts]
                    int_pts = [(int(x), int(y)) for x, y in screen_pts]

                    sq = game.board.get_square(sector_index, ring, position)
                    fill = RING_FILLS.get(ring, (31, 41, 55))
                    if ring == Ring.CANNON:
                        fill = (55, 65, 81)
                    if sq.is_goal:
                        fill = (GOAL_HOME_FILL if sq.goal_side.value == "home"
                                else GOAL_VISITOR_FILL)
                    # Apply incline brightness
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
            lx = BOARD_CX + math.cos(mid_angle) * 355
            ly = BOARD_CY + math.sin(mid_angle) * 355
            slx, sly = self._w2s(lx, ly)
            font = self._font(max(7, int(10 * z)), bold=True)
            label_surf = font.render(sector.name, True, TEXT_PRIMARY)
            surface.blit(label_surf,
                         (int(slx) - label_surf.get_width() // 2,
                          int(sly) - label_surf.get_height() // 2))

    # --- Lighting (Tier 2 enhancement) ---

    def _draw_lighting(self, surface: pygame.Surface, game: Any) -> None:
        """Draw spotlight on ball carrier (Tier 2 lighting)."""
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
        for i in range(r, 0, -1):
            alpha = int(SPOTLIGHT_ALPHA * (i / r))
            pygame.draw.circle(spotlight, (255, 240, 200, alpha),
                               (r, r), i)
        surface.blit(spotlight, (int(sx) - r, int(sy) - r),
                     special_flags=pygame.BLEND_ADD)

    # --- Shadows (Tier 2 enhancement) ---

    def _draw_shadows(self, surface: pygame.Surface, game: Any) -> None:
        """Draw incline-based shadows beneath figures."""
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
            shadow_surf = pygame.Surface((sr * 2 + 4, sh + sr + 4), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_surf, (0, 0, 0, 40),
                                (2, sh, sr * 2, sr))
            surface.blit(shadow_surf,
                         (int(sx) - sr - 2, int(sy) - 2))

    # --- Highlights ---

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
                pygame.draw.circle(surface, (245, 158, 11), (isx, isy),
                                   max(1, r20), max(1, int(3 * z)))
            if fig.status == FigureStatus.MAN_TO_MAN:
                pygame.draw.rect(surface, (168, 85, 247),
                                 (isx - r24, isy - r24, r24 * 2, r24 * 2),
                                 max(1, int(2 * z)))
            if fig.has_moved:
                if r6 > 0:
                    pygame.draw.circle(surface, (254, 240, 138), (isx, isy), r6)

            # Tow bar indicator
            if getattr(fig, 'is_towed', False):
                biker = getattr(fig, 'towed_by', None)
                if biker is not None:
                    bsq = game.board.find_square_of_figure(biker)
                    if bsq is not None:
                        bwx, bwy = _square_center(bsq)
                        bsx, bsy = self._w2s(bwx, bwy)
                        pygame.draw.line(surface, (34, 197, 94),
                                         (isx, isy), (int(bsx), int(bsy)),
                                         max(1, int(2 * z)))

            # Endurance warning
            endurance_used = getattr(fig, 'endurance_used', 0)
            max_e = getattr(fig, 'base_toughness', 7) + 3
            if endurance_used > max_e:
                font = self._font(max(6, int(8 * z)), bold=True)
                warn = font.render("E!", True, (239, 68, 68))
                surface.blit(warn, (int(sx + 14 * z), int(sy - 14 * z)))

        # Obstacles and fire
        for sector in game.board.sectors:
            for sq in sector.all_squares():
                if not sq.has_obstacle and not sq.is_on_fire:
                    continue
                wx, wy = _square_center(sq)
                sx, sy = self._w2s(wx, wy)
                marker = "!" if sq.has_obstacle else "*"
                color = (251, 191, 36) if sq.has_obstacle else (239, 68, 68)
                font = self._font(max(8, int(14 * z)), bold=True)
                txt = font.render(marker, True, color)
                surface.blit(txt, (int(sx) - txt.get_width() // 2,
                                   int(sy) - txt.get_height() // 2))

    # --- Figures (Tier 2 animated sprites) ---

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
            label = FIGURE_LABELS.get(ftype, ftype[0].upper() if ftype else "?")

            if team_side == "home":
                pal = SPRITE_COLORS_HOME.get(ftype, {"fill": (59, 130, 246), "accent": (30, 58, 95)})
            else:
                pal = SPRITE_COLORS_VISITOR.get(ftype, {"fill": (239, 68, 68), "accent": (127, 29, 29)})
            fill = pal["fill"]
            accent = pal["accent"]

            if fig.needs_stand_up or fig.status in (FigureStatus.UNCONSCIOUS, FigureStatus.DEAD):
                fill = INJURED_FILL
                accent = INJURED_ACCENT

            # Apply ring brightness
            brightness = RING_BRIGHTNESS.get(sq.ring, 1.0)
            fill = _apply_brightness(fill, brightness)
            accent = _apply_brightness(accent, brightness)

            r = int(14 * z)
            sr = int(10 * z)

            # Animation wobble for movement
            anim = self.get_anim(fig)
            wobble = 0.0
            if anim.action == "move":
                wobble = math.sin(anim.frame * math.pi / 2) * 2 * z
            elif anim.action == "combat":
                wobble = math.sin(anim.frame * math.pi) * 3 * z

            draw_x = isx + int(wobble)
            draw_y = isy

            if r < 2:
                continue

            # Draw type-specific shape
            if ftype == "biker":
                pts = [(draw_x, draw_y - r), (draw_x + r, draw_y),
                       (draw_x, draw_y + r), (draw_x - r, draw_y)]
                pygame.draw.polygon(surface, fill, pts)
                pygame.draw.polygon(surface, (255, 255, 255), pts, max(1, int(2 * z)))
                inner_pts = [(draw_x, draw_y - sr), (draw_x + sr, draw_y),
                             (draw_x, draw_y + sr), (draw_x - sr, draw_y)]
                if sr > 1:
                    pygame.draw.polygon(surface, accent, inner_pts)
            elif ftype == "catcher":
                rect = pygame.Rect(draw_x - r, draw_y - int(r * 0.8),
                                   r * 2, int(r * 1.6))
                pygame.draw.ellipse(surface, fill, rect)
                pygame.draw.ellipse(surface, (255, 255, 255), rect, max(1, int(2 * z)))
                inner_rect = pygame.Rect(draw_x - int(r * 0.5), draw_y - int(r * 0.5),
                                         r, r)
                pygame.draw.ellipse(surface, accent, inner_rect)
            elif ftype == "speeder":
                pts = [(draw_x, draw_y - r),
                       (draw_x + int(r * 0.9), draw_y + int(r * 0.7)),
                       (draw_x - int(r * 0.9), draw_y + int(r * 0.7))]
                pygame.draw.polygon(surface, fill, pts)
                pygame.draw.polygon(surface, (255, 255, 255), pts, max(1, int(2 * z)))
                # Speed line
                pygame.draw.line(surface, accent,
                                 (draw_x - int(r * 0.6), draw_y + int(r * 0.3)),
                                 (draw_x + int(r * 0.6), draw_y + int(r * 0.3)),
                                 max(1, int(z)))
            else:  # bruiser
                pygame.draw.circle(surface, fill, (draw_x, draw_y), r)
                pygame.draw.circle(surface, (255, 255, 255), (draw_x, draw_y),
                                   r, max(1, int(2 * z)))
                if int(sr * 0.6) > 0:
                    pygame.draw.circle(surface, accent, (draw_x, draw_y), int(sr * 0.6))

            # Type label
            font = self._font(max(7, int(10 * z)), bold=True)
            lbl = font.render(label, True, (255, 255, 255))
            surface.blit(lbl, (draw_x - lbl.get_width() // 2,
                               draw_y - lbl.get_height() // 2))

            # Ball indicator
            if fig.has_ball:
                br = int(6 * z)
                bx = draw_x + int(r * 0.6)
                by = draw_y - r
                if br > 0:
                    pygame.draw.circle(surface, (249, 115, 22), (bx + br, by + br), br)
                    pygame.draw.circle(surface, (255, 247, 237), (bx + br, by + br),
                                       br, max(1, int(z)))

            # Store rect for click detection
            hit_rect = pygame.Rect(draw_x - r, draw_y - r, r * 2, r * 2)
            self.figure_rects[id(fig)] = (hit_rect, fig)

    # --- Ball ---

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

        r = int(8 * z)
        gr = int(r * 1.8)
        if r < 1:
            return

        # Glow ring
        if gr > 1:
            pygame.draw.circle(surface, glow_color, (isx, isy), gr, max(1, int(2 * z)))
        pygame.draw.circle(surface, ball_color, (isx, isy), r)
        pygame.draw.circle(surface, (255, 247, 237), (isx, isy), r, max(1, int(2 * z)))

    # --- Movement options overlay ---

    def _draw_move_options(self, surface: pygame.Surface,
                           options: List[Tuple[Any, int]]) -> None:
        z = self.camera.zoom
        self._move_option_rects.clear()
        for sq, cost in options:
            wx, wy = _square_center(sq)
            sx, sy = self._w2s(wx, wy)
            isx, isy = int(sx), int(sy)
            r = int(22 * z)
            if r < 2:
                continue

            # Dashed circle approximation
            pygame.draw.circle(surface, TEXT_HIGHLIGHT, (isx, isy),
                               r, max(1, int(3 * z)))
            # Semi-transparent fill
            fill_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(fill_surf, (34, 211, 238, 30), (r, r), r)
            surface.blit(fill_surf, (isx - r, isy - r))

            # Cost label
            font = self._font(max(7, int(9 * z)), bold=True)
            cost_surf = font.render(str(cost), True, (103, 232, 249))
            surface.blit(cost_surf, (isx - cost_surf.get_width() // 2,
                                     isy + r + 4))

            hit_rect = pygame.Rect(isx - r, isy - r, r * 2, r * 2)
            self._move_option_rects.append((hit_rect, sq))

    # --- Canvas scoreboard overlay ---

    def _draw_canvas_scoreboard(self, surface: pygame.Surface, game: Any) -> None:
        snapshot = game.snapshot()
        scores = snapshot["scores"]
        names = list(scores.keys())
        score_text = "  |  ".join(f"{n}: {scores[n]}" for n in names)
        clock_text = (f"Period {snapshot['period']}  ·  "
                      f"Turn {snapshot['turn']}  ·  "
                      f"{snapshot['time_remaining']}:00")

        status_text = ""
        if game.game_over:
            result = game.match_result()
            status_text = "DRAW" if result == "Draw" else f"WINNER: {result}"

        font_big = self._font(11, bold=True)
        font_sm = self._font(9)
        font_st = self._font(10, bold=True)

        lines_count = 2 + (1 if status_text else 0)
        line_h = 18
        pad = 6
        box_w = 240
        box_h = lines_count * line_h + pad * 2
        right = 890
        top = 12

        pygame.draw.rect(surface, (31, 41, 55),
                         (right - box_w, top - pad, box_w + 4, box_h))
        pygame.draw.rect(surface, (107, 114, 128),
                         (right - box_w, top - pad, box_w + 4, box_h), 1)

        cx_text = right - box_w // 2
        score_surf = font_big.render(score_text, True, TEXT_PRIMARY)
        surface.blit(score_surf,
                     (cx_text - score_surf.get_width() // 2, top + 2))
        clock_surf = font_sm.render(clock_text, True, TEXT_SECONDARY)
        surface.blit(clock_surf,
                     (cx_text - clock_surf.get_width() // 2, top + line_h + 2))
        if status_text:
            st_surf = font_st.render(status_text, True, TEXT_ACCENT)
            surface.blit(st_surf,
                         (cx_text - st_surf.get_width() // 2, top + line_h * 2 + 2))

    # --- Particle effect helpers ---

    def emit_cannon_particles(self) -> None:
        cx, cy = self._w2s(BOARD_CX, BOARD_CY - 300)
        self.particles.emit(cx, cy, PARTICLE_COUNT_CANNON,
                            colors=[(255, 69, 0), (255, 140, 0),
                                    (255, 215, 0), (255, 255, 255)],
                            speed_range=(2.0, 6.0))

    def emit_crash_particles(self, wx: float, wy: float) -> None:
        sx, sy = self._w2s(wx, wy)
        self.particles.emit(sx, sy, PARTICLE_COUNT_CRASH,
                            colors=[(239, 68, 68), (249, 115, 22), (251, 191, 36)],
                            speed_range=(1.0, 3.0), size_range=(1.5, 4.0))

    def emit_goal_particles(self) -> None:
        cx, cy = self._w2s(BOARD_CX, BOARD_CY)
        self.particles.emit(cx, cy, PARTICLE_COUNT_GOAL,
                            colors=[(34, 197, 94), (59, 130, 246), (245, 158, 11),
                                    (236, 72, 153), (255, 255, 255)],
                            speed_range=(3.0, 8.0), size_range=(2.0, 6.0),
                            lifetime=1000)

    # --- Hit testing ---

    def figure_at(self, screen_x: int, screen_y: int) -> Optional[Any]:
        """Return the figure under screen position, or None."""
        for fid, (rect, fig) in self.figure_rects.items():
            if rect.collidepoint(screen_x, screen_y):
                return fig
        return None

    def move_option_at(self, screen_x: int, screen_y: int) -> Optional[Any]:
        """Return the move-option Square under screen position, or None."""
        for rect, sq in self._move_option_rects:
            if rect.collidepoint(screen_x, screen_y):
                return sq
        return None
