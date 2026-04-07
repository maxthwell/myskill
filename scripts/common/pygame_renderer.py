from __future__ import annotations

import hashlib
import math
import os
from pathlib import Path
from typing import Any
from io import BytesIO

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from PIL import Image

from .io import ROOT_DIR, _cached_remote_asset, discover_attack_effect_asset, discover_effect_assets, discover_wall_layer_asset, manifest_index

MAX_EFFECT_ALPHA = 230
MIN_EFFECT_ALPHA = 120
EFFECT_BRIGHTNESS_ADD = 42


class PygameSceneRenderer:
    def __init__(self, story: dict[str, Any], prefer_gpu: bool = True):
        del prefer_gpu
        if not pygame.get_init():
            pygame.init()
        if not pygame.font.get_init():
            pygame.font.init()
        if not pygame.display.get_init():
            pygame.display.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1, 1), flags=pygame.HIDDEN)

        self.story = story
        self.video = story["video"]
        self.width = int(self.video["width"])
        self.height = int(self.video["height"])
        self.surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA, 32)
        self.pipe_name = "pygame"

        self.backgrounds = manifest_index("backgrounds")
        self.characters = manifest_index("characters")
        self.floors = manifest_index("floors")
        self.props = manifest_index("props")
        self.effects = manifest_index("effects")
        self.foregrounds = manifest_index("foregrounds")
        self.effect_assets = discover_effect_assets()
        self.attack_effect_asset = discover_attack_effect_asset()
        self.cast = {str(item["id"]): item for item in story.get("cast", [])}

        self._image_cache: dict[str, list[pygame.Surface]] = {}
        self._frame_duration_cache: dict[str, list[int]] = {}
        self._scaled_cache: dict[tuple[str, int, int, bool], pygame.Surface] = {}
        self._background_cache: dict[str, pygame.Surface] = {}
        self._wall_layer_cache: dict[str, pygame.Surface] = {}
        self._wall_opening_mask_cache: dict[str, pygame.Surface] = {}
        self._font_cache: dict[int, pygame.font.Font] = {}
        self._font_path = self._find_font_path()
        stage_layout = self.video.get("stage_layout") or {}
        self._floor_top_ratio = float(stage_layout.get("floor_top_ratio", 0.77) or 0.77)
        self._backdrop_top_ratio = float(stage_layout.get("backdrop_top_ratio", 0.0) or 0.0)
        self._effect_overlay_alpha = float(stage_layout.get("effect_overlay_alpha", 0.86) or 0.86)

    def _find_font_path(self) -> str | None:
        candidates = (
            "Noto Sans CJK SC",
            "Noto Sans SC",
            "WenQuanYi Zen Hei",
            "Microsoft YaHei",
            "SimHei",
            "Arial Unicode MS",
            "PingFang SC",
        )
        for name in candidates:
            path = pygame.font.match_font(name)
            if path:
                return path
        return None

    def _font(self, size: int) -> pygame.font.Font:
        key = max(12, int(size))
        font = self._font_cache.get(key)
        if font is None:
            font = pygame.font.Font(self._font_path, key)
            self._font_cache[key] = font
        return font

    @staticmethod
    def _rgba(color: Any, alpha_override: int | None = None) -> tuple[int, int, int, int]:
        if not isinstance(color, (list, tuple)):
            rgba = [255, 255, 255, 255]
        else:
            rgba = [float(item) for item in color[:4]]
            if any(item > 1.0 for item in rgba):
                rgba = [max(0.0, min(255.0, item)) for item in rgba]
            else:
                rgba = [max(0.0, min(1.0, item)) * 255.0 for item in rgba]
            while len(rgba) < 4:
                rgba.append(255.0)
        if alpha_override is not None:
            rgba[3] = float(alpha_override)
        return tuple(int(round(max(0.0, min(255.0, item)))) for item in rgba[:4])

    def _load_frames(self, path_value: str | None) -> list[pygame.Surface]:
        if not path_value:
            return []
        cached = self._image_cache.get(path_value)
        if cached is not None:
            return cached

        path = Path(path_value)
        if not path.exists():
            self._image_cache[path_value] = []
            self._frame_duration_cache[path_value] = []
            return []

        frames: list[pygame.Surface] = []
        frame_durations: list[int] = []
        try:
            with Image.open(path) as image:
                frame_count = getattr(image, "n_frames", 1)
                for index in range(frame_count):
                    image.seek(index)
                    duration_ms = int(image.info.get("duration", 0) or 0)
                    frame_durations.append(max(20, duration_ms or 100))
                    rgba = image.convert("RGBA")
                    frame = pygame.image.fromstring(rgba.tobytes(), rgba.size, "RGBA").convert_alpha()
                    frames.append(frame)
        except Exception:
            frames = []
            frame_durations = []
        self._image_cache[path_value] = frames
        self._frame_duration_cache[path_value] = frame_durations[: len(frames)]
        return frames

    def _scaled_surface(self, cache_key: str, source: pygame.Surface, width: int, height: int, flip_x: bool = False) -> pygame.Surface:
        safe_w = max(1, int(round(width)))
        safe_h = max(1, int(round(height)))
        key = (cache_key, safe_w, safe_h, flip_x)
        cached = self._scaled_cache.get(key)
        if cached is not None:
            return cached
        surface = pygame.transform.smoothscale(source, (safe_w, safe_h))
        if flip_x:
            surface = pygame.transform.flip(surface, True, False)
        self._scaled_cache[key] = surface
        return surface

    @staticmethod
    def _trim_transparent_bounds(source: pygame.Surface, min_alpha: int = 1) -> pygame.Surface:
        try:
            bounds = source.get_bounding_rect(min_alpha=min_alpha)
        except TypeError:
            bounds = source.get_bounding_rect()
        if bounds.width <= 0 or bounds.height <= 0:
            return source
        if bounds.size == source.get_size() and bounds.topleft == (0, 0):
            return source
        return source.subsurface(bounds).copy()

    @staticmethod
    def _key_wall_layer_background(source: pygame.Surface, threshold: int = 245) -> pygame.Surface:
        converted = source.convert_alpha()
        width, height = converted.get_size()
        # Only chroma-key near-white backgrounds when the image has no meaningful alpha of its own.
        try:
            bounds = converted.get_bounding_rect(min_alpha=1)
        except TypeError:
            bounds = converted.get_bounding_rect()
        if bounds.width <= 0 or bounds.height <= 0:
            return converted
        if bounds.size != converted.get_size() or bounds.topleft != (0, 0):
            return converted
        keyed = converted.copy()
        changed = 0
        total = max(1, width * height)
        for y in range(height):
            for x in range(width):
                r, g, b, a = keyed.get_at((x, y))
                if a == 0:
                    continue
                if r >= threshold and g >= threshold and b >= threshold:
                    keyed.set_at((x, y), (r, g, b, 0))
                    changed += 1
        if changed < total * 0.12:
            return converted
        return keyed

    @staticmethod
    def _content_bounds(source: pygame.Surface, min_alpha: int = 1) -> pygame.Rect:
        try:
            bounds = source.get_bounding_rect(min_alpha=min_alpha)
        except TypeError:
            bounds = source.get_bounding_rect()
        if bounds.width <= 0 or bounds.height <= 0:
            return pygame.Rect(0, 0, source.get_width(), source.get_height())
        return bounds

    def _frame_durations(self, path_value: str | None, frame_count: int) -> list[int]:
        if not path_value or frame_count <= 0:
            return []
        if path_value not in self._frame_duration_cache:
            self._load_frames(path_value)
        durations = list(self._frame_duration_cache.get(path_value, []))
        if len(durations) < frame_count:
            durations.extend([100] * (frame_count - len(durations)))
        return durations[:frame_count]

    def _animation_timeline_ms(self, path_value: str | None, frame_count: int, period_ms: int | None = None) -> list[int]:
        durations = self._frame_durations(path_value, frame_count)
        if not durations:
            return []
        total_native_ms = sum(durations)
        if total_native_ms <= 0:
            return [100] * frame_count
        target_total_ms = total_native_ms
        if period_ms is not None:
            requested_total_ms = max(1, int(period_ms))
            if requested_total_ms != 1400:
                target_total_ms = requested_total_ms
        if target_total_ms == total_native_ms:
            return durations

        scaled: list[int] = []
        accumulated = 0
        for index, duration_ms in enumerate(durations):
            if index == frame_count - 1:
                scaled_duration = max(1, target_total_ms - accumulated)
            else:
                scaled_duration = max(1, int(round(duration_ms / total_native_ms * target_total_ms)))
                remaining_min = frame_count - index - 1
                scaled_duration = min(scaled_duration, max(1, target_total_ms - accumulated - remaining_min))
            scaled.append(scaled_duration)
            accumulated += scaled_duration
        return scaled

    @staticmethod
    def _timeline_frame_index(durations: list[int], position_ms: float) -> int:
        if not durations:
            return 0
        elapsed = 0.0
        for index, duration_ms in enumerate(durations):
            elapsed += max(1, duration_ms)
            if position_ms < elapsed:
                return index
        return len(durations) - 1

    def _pick_frame(
        self,
        frames: list[pygame.Surface],
        time_ms: int,
        period_ms: int | None = None,
        *,
        path_value: str | None = None,
    ) -> pygame.Surface | None:
        if not frames:
            return None
        if len(frames) == 1:
            return frames[0]
        durations = self._animation_timeline_ms(path_value, len(frames), period_ms=period_ms)
        timeline_total_ms = max(1, sum(durations) if durations else int(period_ms or 900))
        position_ms = int(time_ms) % timeline_total_ms
        fallback = [max(1, timeline_total_ms // max(1, len(frames)))] * len(frames)
        frame_index = self._timeline_frame_index(durations or fallback, position_ms)
        return frames[frame_index % len(frames)]

    def _frame_index_for_time(
        self,
        path_value: str | None,
        frame_count: int,
        time_ms: int,
        *,
        period_ms: int | None = None,
    ) -> int:
        if frame_count <= 1:
            return 0
        durations = self._animation_timeline_ms(path_value, frame_count, period_ms=period_ms)
        timeline_total_ms = max(1, sum(durations) if durations else int(period_ms or 900))
        position_ms = int(time_ms) % timeline_total_ms
        fallback = [max(1, timeline_total_ms // max(1, frame_count))] * frame_count
        return self._timeline_frame_index(durations or fallback, position_ms)

    def _frame_index_for_progress(
        self,
        path_value: str | None,
        frame_count: int,
        progress: float,
        *,
        playback_speed: float = 1.0,
        period_ms: int | None = None,
    ) -> int:
        if frame_count <= 1:
            return 0
        durations = self._animation_timeline_ms(path_value, frame_count, period_ms=period_ms)
        timeline_total_ms = max(1, sum(durations) if durations else int(period_ms or 900))
        # One-shot effects should play through at least one full native cycle.
        # Higher playback_speed values can drive additional cycles, but lower values
        # no longer truncate the animation before one pass completes.
        cycle_count = max(1.0, float(playback_speed or 1.0))
        adjusted_progress = max(0.0, self._clamp_ratio(progress) * cycle_count)
        position_ms = min(timeline_total_ms - 1, adjusted_progress * timeline_total_ms)
        fallback = [max(1, timeline_total_ms // max(1, frame_count))] * frame_count
        return self._timeline_frame_index(durations or fallback, position_ms)

    def _layout_metrics(self) -> dict[str, Any]:
        floor_top = max(1, min(self.height - 1, int(round(self.height * self._floor_top_ratio))))
        backdrop_top = max(0, min(floor_top - 1, int(round(self.height * self._backdrop_top_ratio))))
        backdrop_rect = pygame.Rect(0, backdrop_top, self.width, floor_top - backdrop_top)
        floor_rect = pygame.Rect(0, floor_top, self.width, self.height - floor_top)
        return {
            "backdrop_rect": backdrop_rect,
            "floor_rect": floor_rect,
            "floor_top": floor_top,
        }

    def _background_surface(self, scene: dict[str, Any], time_ms: int, rect: pygame.Rect | None = None) -> pygame.Surface:
        background_id = str(scene.get("background") or "")
        target_rect = rect or pygame.Rect(0, 0, self.width, self.height)
        background = self.backgrounds.get(background_id, {})
        background_asset_path = str(background.get("asset_path") or "")
        background_frames = self._load_frames(background_asset_path)
        background_period_override = scene.get("background_motion_period_ms")
        background_period_ms = int(background_period_override or background.get("motion_period_ms", 1400) or 1400)
        if len(background_frames) <= 1:
            scene_id = f"{scene.get('id') or 'scene'}:{background_id}:{target_rect.width}x{target_rect.height}"
            cached = self._background_cache.get(scene_id)
            if cached is not None:
                return cached
        else:
            frame_index = self._frame_index_for_time(
                background_asset_path,
                len(background_frames),
                time_ms,
                period_ms=background_period_ms,
            )
            scene_id = f"{scene.get('id') or 'scene'}:{background_id}:{target_rect.width}x{target_rect.height}:frame:{frame_index}"
            cached = self._background_cache.get(scene_id)
            if cached is not None:
                return cached

        surface = pygame.Surface((target_rect.width, target_rect.height), pygame.SRCALPHA, 32)
        self._paint_background(surface, background, scene_id, time_ms=time_ms)
        self._background_cache[scene_id] = surface
        return surface

    def _paint_background(
        self,
        surface: pygame.Surface,
        background: dict[str, Any],
        cache_key: str,
        dest_rect: pygame.Rect | None = None,
        *,
        time_ms: int = 0,
    ) -> None:
        rect = dest_rect or surface.get_rect()
        image = self._pick_frame(
            self._load_frames(background.get("asset_path")),
            time_ms,
            period_ms=int(background.get("motion_period_ms", 1400) or 1400),
            path_value=str(background.get("asset_path") or ""),
        )
        if image is not None:
            scaled = self._scaled_surface(f"bg:{cache_key}", image, rect.width, rect.height)
            surface.blit(scaled, rect.topleft)
        else:
            background_id = str(background.get("id") or "")
            sky = self._rgba(background.get("sky_color") or [0.72, 0.78, 0.84, 1.0])
            ground = self._rgba(background.get("ground_color") or [0.44, 0.40, 0.34, 1.0])
            accent = self._rgba(background.get("accent_color") or [0.80, 0.48, 0.24, 1.0])
            horizon = int(background.get("horizon_y") or rect.height * 0.58)
            self._fill_vertical_gradient(surface, sky, (*accent[:3], 255), rect.top, rect.top + horizon, x0=rect.left, x1=rect.right)
            self._fill_vertical_gradient(surface, (*accent[:3], 200), ground, rect.top + horizon, rect.bottom, x0=rect.left, x1=rect.right)
            pygame.draw.circle(surface, (*accent[:3], 64), (int(rect.left + rect.width * 0.18), int(rect.top + rect.height * 0.24)), int(rect.height * 0.18))
            self._paint_background_details(surface, rect, background_id, sky, ground, accent, horizon)
            mountain = [
                (rect.left, rect.top + horizon + int(rect.height * 0.06)),
                (rect.left + int(rect.width * 0.16), rect.top + horizon - int(rect.height * 0.04)),
                (rect.left + int(rect.width * 0.31), rect.top + horizon + int(rect.height * 0.02)),
                (rect.left + int(rect.width * 0.47), rect.top + horizon - int(rect.height * 0.10)),
                (rect.left + int(rect.width * 0.63), rect.top + horizon + int(rect.height * 0.01)),
                (rect.left + int(rect.width * 0.79), rect.top + horizon - int(rect.height * 0.07)),
                (rect.right, rect.top + horizon + int(rect.height * 0.04)),
                (rect.right, rect.top + horizon + int(rect.height * 0.20)),
                (rect.left, rect.top + horizon + int(rect.height * 0.20)),
            ]
            pygame.draw.polygon(surface, (*ground[:3], 180), mountain)

    def _paint_background_details(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        background_id: str,
        sky: tuple[int, int, int, int],
        ground: tuple[int, int, int, int],
        accent: tuple[int, int, int, int],
        horizon: int,
    ) -> None:
        if background_id in {"mountain-cliff", "park-evening"}:
            self._draw_mountain_layers(surface, rect, horizon, ground, accent)
            self._draw_cloud_bands(surface, rect, sky, accent, horizon)
        elif background_id in {"night-bridge"}:
            self._draw_star_field(surface, rect, accent)
            self._draw_bridge_silhouette(surface, rect, horizon, ground, accent)
        elif background_id in {"temple-courtyard", "training-ground"}:
            self._draw_roofline(surface, rect, horizon, ground, accent)
            self._draw_banner_rows(surface, rect, horizon, accent)
        elif background_id in {"archive-library", "town-hall-records"}:
            self._draw_interior_panels(surface, rect, horizon, ground, accent, shelves=True)
        elif background_id in {"inn-hall", "room-day"}:
            self._draw_interior_panels(surface, rect, horizon, ground, accent, shelves=False)
        elif background_id in {"street-day", "shop-row"}:
            self._draw_city_row(surface, rect, horizon, ground, accent)
        elif background_id in {"theatre-stage"}:
            self._draw_stage_backdrop(surface, rect, horizon, ground, accent)
        else:
            self._draw_cloud_bands(surface, rect, sky, accent, horizon)

    def _draw_cloud_bands(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        sky: tuple[int, int, int, int],
        accent: tuple[int, int, int, int],
        horizon: int,
    ) -> None:
        cloud_color = (
            min(255, sky[0] + 28),
            min(255, sky[1] + 24),
            min(255, sky[2] + 18),
            42,
        )
        for index, ratio in enumerate((0.16, 0.28, 0.38)):
            y = rect.top + int(rect.height * ratio)
            radius_y = int(rect.height * (0.035 + index * 0.01))
            for cluster in range(4):
                cx = rect.left + int(rect.width * (0.12 + cluster * 0.24 + (index % 2) * 0.04))
                pygame.draw.ellipse(
                    surface,
                    cloud_color,
                    pygame.Rect(cx - int(rect.width * 0.08), y - radius_y, int(rect.width * 0.16), radius_y * 2),
                )
        haze = pygame.Surface((rect.width, max(1, horizon // 4)), pygame.SRCALPHA, 32)
        haze.fill((accent[0], accent[1], accent[2], 18))
        surface.blit(haze, (rect.left, rect.top + horizon - haze.get_height()))

    def _draw_star_field(self, surface: pygame.Surface, rect: pygame.Rect, accent: tuple[int, int, int, int]) -> None:
        star_color = (255, 246, min(255, accent[2] + 40), 170)
        for index in range(26):
            unit = self._stable_unit(f"star:{rect.width}:{rect.height}:{index}")
            unit2 = self._stable_unit(f"star-y:{rect.width}:{rect.height}:{index}")
            x = rect.left + int(rect.width * (0.06 + unit * 0.88))
            y = rect.top + int(rect.height * (0.04 + unit2 * 0.34))
            radius = 1 + (index % 2)
            pygame.draw.circle(surface, star_color, (x, y), radius)

    def _draw_mountain_layers(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        horizon: int,
        ground: tuple[int, int, int, int],
        accent: tuple[int, int, int, int],
    ) -> None:
        far = (max(0, ground[0] - 40), max(0, ground[1] - 34), max(0, ground[2] - 22), 110)
        mid = (max(0, ground[0] - 18), max(0, ground[1] - 12), max(0, ground[2] - 8), 158)
        ridge_specs = [
            (far, 0.02, 0.09, 0.12),
            (mid, 0.08, 0.14, 0.18),
        ]
        for color, rise, peak, depth in ridge_specs:
            ridge = [
                (rect.left, rect.top + horizon + int(rect.height * rise)),
                (rect.left + int(rect.width * 0.12), rect.top + horizon - int(rect.height * peak * 0.6)),
                (rect.left + int(rect.width * 0.28), rect.top + horizon + int(rect.height * rise * 0.3)),
                (rect.left + int(rect.width * 0.44), rect.top + horizon - int(rect.height * peak)),
                (rect.left + int(rect.width * 0.61), rect.top + horizon + int(rect.height * rise * 0.4)),
                (rect.left + int(rect.width * 0.78), rect.top + horizon - int(rect.height * peak * 0.7)),
                (rect.right, rect.top + horizon + int(rect.height * rise)),
                (rect.right, rect.top + horizon + int(rect.height * depth)),
                (rect.left, rect.top + horizon + int(rect.height * depth)),
            ]
            pygame.draw.polygon(surface, color, ridge)
        snow = (min(255, accent[0] + 20), min(255, accent[1] + 20), min(255, accent[2] + 20), 85)
        pygame.draw.polygon(
            surface,
            snow,
            [
                (rect.left + int(rect.width * 0.40), rect.top + horizon - int(rect.height * 0.10)),
                (rect.left + int(rect.width * 0.44), rect.top + horizon - int(rect.height * 0.16)),
                (rect.left + int(rect.width * 0.49), rect.top + horizon - int(rect.height * 0.09)),
            ],
        )

    def _draw_bridge_silhouette(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        horizon: int,
        ground: tuple[int, int, int, int],
        accent: tuple[int, int, int, int],
    ) -> None:
        river_rect = pygame.Rect(rect.left, rect.top + horizon, rect.width, rect.bottom - (rect.top + horizon))
        river = pygame.Surface(river_rect.size, pygame.SRCALPHA, 32)
        self._fill_vertical_gradient(river, (18, 28, 54, 150), (10, 16, 30, 220), 0, river_rect.height)
        for idx in range(5):
            y = int(river_rect.height * (0.12 + idx * 0.16))
            pygame.draw.line(river, (accent[0], accent[1], accent[2], 22), (0, y), (river_rect.width, y + 10), 2)
        surface.blit(river, river_rect.topleft)
        deck_y = rect.top + horizon + int(rect.height * 0.06)
        arch_rect = pygame.Rect(rect.left + int(rect.width * 0.16), deck_y - int(rect.height * 0.16), int(rect.width * 0.68), int(rect.height * 0.26))
        pygame.draw.arc(surface, (ground[0], ground[1], ground[2], 220), arch_rect, math.pi, math.tau, 8)
        pygame.draw.line(surface, (ground[0], ground[1], ground[2], 220), (arch_rect.left, deck_y), (arch_rect.right, deck_y), 8)
        for ratio in (0.24, 0.36, 0.50, 0.64, 0.78):
            x = rect.left + int(rect.width * ratio)
            pygame.draw.line(surface, (accent[0], accent[1], accent[2], 120), (x, deck_y - 22), (x, deck_y + 4), 2)

    def _draw_roofline(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        horizon: int,
        ground: tuple[int, int, int, int],
        accent: tuple[int, int, int, int],
    ) -> None:
        base_y = rect.top + horizon + int(rect.height * 0.02)
        roof_color = (max(0, ground[0] - 20), max(0, ground[1] - 24), max(0, ground[2] - 12), 220)
        body_color = (ground[0], ground[1], ground[2], 165)
        left = rect.left + int(rect.width * 0.12)
        right = rect.right - int(rect.width * 0.12)
        pygame.draw.polygon(
            surface,
            roof_color,
            [
                (left, base_y + 16),
                (left + 70, base_y - 18),
                (rect.centerx, base_y - 40),
                (right - 70, base_y - 18),
                (right, base_y + 16),
            ],
        )
        pygame.draw.rect(surface, body_color, pygame.Rect(left + 28, base_y + 18, right - left - 56, int(rect.height * 0.12)))
        for ratio in (0.22, 0.38, 0.62, 0.78):
            x = rect.left + int(rect.width * ratio)
            pygame.draw.rect(surface, (accent[0], accent[1], accent[2], 105), pygame.Rect(x, base_y + 24, 10, int(rect.height * 0.11)))

    def _draw_banner_rows(self, surface: pygame.Surface, rect: pygame.Rect, horizon: int, accent: tuple[int, int, int, int]) -> None:
        pole_y = rect.top + horizon + int(rect.height * 0.02)
        for ratio in (0.18, 0.31, 0.69, 0.82):
            x = rect.left + int(rect.width * ratio)
            pygame.draw.line(surface, (72, 46, 28, 170), (x, pole_y + 54), (x, pole_y - 28), 3)
            pygame.draw.polygon(
                surface,
                (accent[0], max(0, accent[1] - 40), max(0, accent[2] - 60), 160),
                [(x, pole_y - 26), (x + 42, pole_y - 14), (x, pole_y - 2)],
            )

    def _draw_interior_panels(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        horizon: int,
        ground: tuple[int, int, int, int],
        accent: tuple[int, int, int, int],
        *,
        shelves: bool,
    ) -> None:
        wall_color = (max(0, ground[0] + 10), max(0, ground[1] + 2), max(0, ground[2] + 2), 145)
        trim_color = (accent[0], accent[1], accent[2], 105)
        panel_top = rect.top + int(rect.height * 0.10)
        panel_height = int(rect.height * 0.54)
        for ratio in (0.10, 0.38, 0.66):
            x = rect.left + int(rect.width * ratio)
            panel = pygame.Rect(x, panel_top, int(rect.width * 0.22), panel_height)
            pygame.draw.rect(surface, wall_color, panel, border_radius=8)
            pygame.draw.rect(surface, trim_color, panel, width=3, border_radius=8)
            if shelves:
                for shelf_ratio in (0.22, 0.46, 0.70):
                    y = panel.top + int(panel.height * shelf_ratio)
                    pygame.draw.line(surface, (70, 46, 28, 160), (panel.left + 10, y), (panel.right - 10, y), 3)
                    for book in range(6):
                        bx = panel.left + 14 + book * int(panel.width * 0.13)
                        bh = 18 + ((book + int(ratio * 10)) % 3) * 10
                        pygame.draw.rect(surface, (accent[0], max(0, accent[1] - 30), max(0, accent[2] - 60), 145), pygame.Rect(bx, y - bh, 10, bh))
            else:
                inner = panel.inflate(-28, -36)
                pygame.draw.rect(surface, (126, 82, 44, 120), inner, border_radius=6)

    def _draw_city_row(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        horizon: int,
        ground: tuple[int, int, int, int],
        accent: tuple[int, int, int, int],
    ) -> None:
        base_y = rect.top + horizon + int(rect.height * 0.03)
        widths = (0.12, 0.16, 0.14, 0.18, 0.13)
        cursor = rect.left + int(rect.width * 0.06)
        for index, width_ratio in enumerate(widths):
            width = int(rect.width * width_ratio)
            height = int(rect.height * (0.14 + (index % 3) * 0.03))
            house = pygame.Rect(cursor, base_y - height, width, height)
            pygame.draw.rect(surface, (ground[0], ground[1], ground[2], 150), house)
            pygame.draw.polygon(
                surface,
                (max(0, ground[0] - 20), max(0, ground[1] - 16), max(0, ground[2] - 8), 170),
                [(house.left - 8, house.top + 8), (house.centerx, house.top - 18), (house.right + 8, house.top + 8)],
            )
            for row in range(2):
                for col in range(3):
                    wx = house.left + 12 + col * int(width * 0.24)
                    wy = house.top + 12 + row * int(height * 0.32)
                    pygame.draw.rect(surface, (accent[0], accent[1], accent[2], 85), pygame.Rect(wx, wy, 10, 12))
            cursor += width + int(rect.width * 0.03)

    def _draw_stage_backdrop(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        horizon: int,
        ground: tuple[int, int, int, int],
        accent: tuple[int, int, int, int],
    ) -> None:
        center_rect = pygame.Rect(rect.left + int(rect.width * 0.18), rect.top + int(rect.height * 0.12), int(rect.width * 0.64), int(rect.height * 0.46))
        pygame.draw.rect(surface, (28, 24, 32, 150), center_rect, border_radius=16)
        pygame.draw.rect(surface, (accent[0], max(0, accent[1] - 30), max(0, accent[2] - 60), 150), center_rect, width=6, border_radius=16)
        pygame.draw.circle(surface, (accent[0], accent[1], accent[2], 90), center_rect.center, int(center_rect.height * 0.24), width=10)
        for ratio in (0.22, 0.78):
            x = rect.left + int(rect.width * ratio)
            pygame.draw.rect(surface, (ground[0], ground[1], ground[2], 145), pygame.Rect(x, rect.top + int(rect.height * 0.10), 18, int(rect.height * 0.54)))

    def _fill_vertical_gradient(
        self,
        surface: pygame.Surface,
        top: tuple[int, int, int, int],
        bottom: tuple[int, int, int, int],
        y0: int,
        y1: int,
        *,
        x0: int = 0,
        x1: int | None = None,
    ) -> None:
        x1 = self.width if x1 is None else x1
        span = max(1, y1 - y0)
        for offset in range(span):
            ratio = offset / span
            color = tuple(int(round(top[index] + (bottom[index] - top[index]) * ratio)) for index in range(4))
            pygame.draw.line(surface, color, (x0, y0 + offset), (x1, y0 + offset))

    @staticmethod
    def _ease(name: str, ratio: float) -> float:
        ratio = max(0.0, min(1.0, ratio))
        if name == "ease-in":
            return ratio * ratio
        if name == "ease-out":
            return 1.0 - (1.0 - ratio) * (1.0 - ratio)
        if name == "ease-in-out":
            return 0.5 - 0.5 * math.cos(math.pi * ratio)
        return ratio

    def _camera(self, scene: dict[str, Any], time_ms: int) -> tuple[float, float, float]:
        camera = scene.get("camera") or {}
        duration_ms = max(1, int(scene.get("duration_ms", 1) or 1))
        ratio = self._ease(str(camera.get("ease") or "linear"), time_ms / duration_ms)
        cx = float(camera.get("x", 0.0) or 0.0) + (float(camera.get("to_x", 0.0) or 0.0) - float(camera.get("x", 0.0) or 0.0)) * ratio
        cz = float(camera.get("z", 0.0) or 0.0) + (float(camera.get("to_z", 0.0) or 0.0) - float(camera.get("z", 0.0) or 0.0)) * ratio
        zoom = float(camera.get("zoom", 1.0) or 1.0) + (float(camera.get("to_zoom", 1.0) or 1.0) - float(camera.get("zoom", 1.0) or 1.0)) * ratio
        return cx, cz, max(0.4, zoom)

    @staticmethod
    def _stable_unit(value: str) -> float:
        digest = hashlib.sha1((value or "").encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big") / float(2**64 - 1)

    def _default_actor_depth(self, scene: dict[str, Any], actor: dict[str, Any]) -> float:
        actor_id = str(actor.get("actor_id") or "")
        scene_id = str(scene.get("id") or "")
        layer = str(actor.get("layer") or "front")
        spawn = actor.get("spawn") or {}
        base_x = float(spawn.get("x", 0.0) or 0.0)
        fingerprint = f"{scene_id}:{actor_id}:{layer}:{base_x:.3f}"
        unit = self._stable_unit(fingerprint)
        depth_range = {
            "front": (-1.18, -0.36),
            "mid": (-1.34, -0.58),
            "back": (-1.52, -0.78),
        }.get(layer, (-1.20, -0.42))
        depth = depth_range[0] + (depth_range[1] - depth_range[0]) * unit
        x_bias = max(-0.10, min(0.10, abs(base_x) * 0.025 - 0.02))
        return depth + x_bias

    def _stage_point(self, x: float, z: float, cx: float, cz: float, zoom: float) -> tuple[int, int]:
        layout = self._layout_metrics()
        unit_x = self.width * 0.085 * zoom
        unit_z = self.height * 0.092 * zoom
        sx = int(round(self.width * 0.5 + (x - cx) * unit_x))
        sy = int(round(layout["floor_top"] + (-z + cz) * unit_z))
        return sx, sy

    def _depth_scale(self, z: float, layer: str, zoom: float) -> float:
        layer_bias = {"back": -0.18, "mid": -0.06, "front": 0.10}.get(layer, 0.0)
        return max(0.45, zoom * (1.0 + (-z * 0.08) + layer_bias))

    def _active_beat(self, scene: dict[str, Any], actor_id: str, time_ms: int) -> dict[str, Any] | None:
        for beat in scene.get("beats", []):
            if str(beat.get("actor_id") or "") != actor_id:
                continue
            if int(beat.get("start_ms", -1) or -1) <= time_ms <= int(beat.get("end_ms", -1) or -1):
                return beat
        return None

    def _anchored_actor_transform(
        self,
        scene: dict[str, Any],
        actor_id: str,
        base_x: float,
        base_z: float,
        facing: str,
        time_ms: int,
    ) -> tuple[float, float, str]:
        x = base_x
        z = base_z
        resolved_facing = facing
        for beat in scene.get("beats", []):
            if str(beat.get("actor_id") or "") != actor_id:
                continue
            beat_start = int(beat.get("start_ms", -1) or -1)
            if beat_start > time_ms:
                break
            origin = beat.get("from") or {}
            target = beat.get("to") or {}
            if beat.get("from") or beat.get("to"):
                from_x = float(origin.get("x", x) or x)
                from_z = float(origin.get("z", z) or z)
                to_x = float(target.get("x", from_x) or from_x)
                to_z = float(target.get("z", from_z) or from_z)
                beat_end = int(beat.get("end_ms", beat_start) or beat_start)
                if time_ms <= beat_end:
                    span = max(1, beat_end - beat_start)
                    progress = max(0.0, min(1.0, (time_ms - beat_start) / span))
                    x = from_x + (to_x - from_x) * progress
                    z = from_z + (to_z - from_z) * progress
                    if beat.get("facing"):
                        resolved_facing = str(beat["facing"])
                    return x, z, resolved_facing
                x = to_x
                z = to_z
            if beat.get("facing"):
                resolved_facing = str(beat["facing"])
        return x, z, resolved_facing

    def _active_dialogue(self, scene: dict[str, Any], time_ms: int) -> dict[str, Any] | None:
        for dialogue in scene.get("dialogues", []):
            if int(dialogue.get("start_ms", -1) or -1) <= time_ms <= int(dialogue.get("end_ms", -1) or -1):
                return dialogue
        return None

    def _expression_for_actor(self, scene: dict[str, Any], actor_id: str, time_ms: int, beat: dict[str, Any] | None) -> str:
        for item in scene.get("expressions", []):
            if str(item.get("actor_id") or "") != actor_id:
                continue
            if int(item.get("start_ms", -1) or -1) <= time_ms <= int(item.get("end_ms", -1) or -1):
                return str(item.get("expression") or "neutral")
        if beat and beat.get("expression"):
            return str(beat.get("expression"))
        return "neutral"

    def _face_candidates(self, expression: str, talking: bool, time_ms: int = 0) -> list[str]:
        canonical = {
            "neutral": "neutral",
            "smile": "smile",
            "angry": "angry",
            "thinking": "thinking",
            "excited": "excited",
            "skeptical": "skeptical",
            "sad": "thinking",
        }
        base = canonical.get(expression, "neutral")
        if talking:
            talking_names = []
            mouth = "open" if (time_ms // 120) % 2 == 0 else "closed"
            talking_names.extend([f"talk_{base}_{mouth}", f"talk_{base}_open", f"talk_{base}_closed"])
            if base != "neutral":
                talking_names.extend([f"talk_neutral_{mouth}", "talk_neutral_open", "talk_neutral_closed"])
            return talking_names + [base, "neutral"]
        return [base, "neutral"]

    def _character_skin(self, actor_id: str, expression: str, talking: bool, time_ms: int) -> tuple[pygame.Surface | None, pygame.Surface | None, dict[str, Any]]:
        cast = self.cast.get(actor_id, {})
        asset_id = str(cast.get("asset_id") or "")
        meta = self.characters.get(asset_id, {})
        character_dir = Path(str(meta.get("character_dir") or "")).resolve() if meta.get("character_dir") else ROOT_DIR / "assets" / "characters" / asset_id
        skin_dir = character_dir / "skins"
        if not skin_dir.exists():
            skin_dir = ROOT_DIR / "assets" / "characters" / "_shared_skins"

        outfit = None
        outfit_names = ["outfit", f"outfit_{meta.get('outfit_style')}", f"outfit_{meta.get('garment')}"]
        for name in outfit_names:
            if not name or name == "outfit_None":
                continue
            outfit_path = str(skin_dir / f"{name}.png")
            frames = self._load_frames(outfit_path)
            outfit = self._pick_frame(frames, time_ms, path_value=outfit_path)
            if outfit is not None:
                break

        face = None
        for name in self._face_candidates(expression, talking, time_ms):
            for ext in ("png", "webp"):
                face_path = str(skin_dir / f"face_{name}.{ext}")
                frames = self._load_frames(face_path)
                face = self._pick_frame(frames, time_ms, path_value=face_path)
                if face is not None:
                    break
            if face is not None:
                break
        return outfit, face, meta

    def _actor_state(self, actor: dict[str, Any], scene: dict[str, Any], time_ms: int) -> dict[str, Any]:
        actor_id = str(actor.get("actor_id") or "")
        spawn = actor.get("spawn") or {}
        base_x = float(spawn.get("x", 0.0) or 0.0)
        base_z = float(spawn.get("z", 0.0) or 0.0)
        if abs(base_z) < 0.001:
            base_z = self._default_actor_depth(scene, actor)
        facing = str(actor.get("facing") or ("right" if base_x <= 0 else "left"))
        layer = str(actor.get("layer") or "front")
        beat = self._active_beat(scene, actor_id, time_ms)
        x, z, facing = self._anchored_actor_transform(scene, actor_id, base_x, base_z, facing, time_ms)
        bob = 0.0
        jump = 0.0
        rotation = 0.0
        pulse = 1.0
        draw_dx = 0.0
        draw_dy = 0.0
        body_lean = 0.0
        torso_shift_x = 0.0
        torso_shift_y = 0.0
        head_shift_x = 0.0
        head_shift_y = 0.0
        shoulder_shift_x = 0.0
        shoulder_shift_y = 0.0
        hip_shift_x = 0.0
        hip_shift_y = 0.0
        waist_bend_x = 0.0
        waist_bend_y = 0.0
        head_rotation = 0.0

        if beat:
            start_ms = int(beat.get("start_ms", time_ms) or time_ms)
            end_ms = max(start_ms + 1, int(beat.get("end_ms", time_ms + 1) or (time_ms + 1)))
            progress = max(0.0, min(1.0, (time_ms - start_ms) / max(1, end_ms - start_ms)))
            motion_progress = progress
            motion = str(beat.get("motion") or "")
            effect_motion = str(beat.get("effect") or "")
            direction = -1.0 if facing == "left" else 1.0
            martial_motion = motion in {
                "flying-kick",
                "double-palm-push",
                "spin-kick",
                "diagonal-kick",
                "hook-punch",
                "swing-punch",
                "straight-punch",
                "combo-punch",
                "somersault",
                "big-jump",
                "dunk",
            }
            if effect_motion in {"dragon-palm", "thunder-strike", "sword-arc"}:
                motion_progress = self._effect_motion_progress(effect_motion, progress)
                motion = self._effect_combo_motion(effect_motion, motion_progress)
            elif martial_motion:
                motion_progress = self._martial_motion_progress(motion, progress)
            if beat.get("facing"):
                facing = str(beat["facing"])
                direction = -1.0 if facing == "left" else 1.0
            if motion == "talk":
                bob = math.sin(motion_progress * math.tau * 2.2) * 1.6
                head_rotation = math.sin(motion_progress * math.tau * 2.0) * 6.0
            elif motion == "point":
                bob = math.sin(motion_progress * math.pi) * 1.8
                pulse = 1.01
                head_rotation = direction * -5.0
            elif motion in {"somersault", "big-jump", "dunk"}:
                rise = self._phase_peak(motion_progress, 0.00, 0.34, 0.62)
                snap = self._phase_peak(motion_progress, 0.22, 0.56, 0.86)
                recover = self._phase_peak(motion_progress, 0.78, 0.92, 1.00)
                jump = 14.0 * rise + 22.0 * snap
                bob = math.sin(motion_progress * math.tau * 3.2) * 1.2
                draw_dx = direction * (-8.0 * rise + 12.0 * snap - 4.0 * recover)
                torso_shift_x = direction * (-5.0 * rise + 6.0 * snap)
                torso_shift_y = -10.0 * rise - 5.0 * snap
                head_shift_x = torso_shift_x * 0.6
                head_shift_y = torso_shift_y * 0.5
                shoulder_shift_x = direction * (-8.0 * rise + 10.0 * snap)
                shoulder_shift_y = -8.0 * rise - 4.0 * snap
                hip_shift_x = direction * (-2.0 * rise + 6.0 * snap)
                hip_shift_y = -4.0 * rise - 2.0 * snap
                body_lean = direction * (-14.0 * rise + 10.0 * snap - 6.0 * recover)
                rotation = (210.0 if motion == "somersault" else 170.0) * motion_progress * direction
                pulse = 1.05 + 0.02 * snap
            elif motion == "flying-kick":
                windup = self._phase_peak(motion_progress, 0.00, 0.18, 0.34)
                strike = self._phase_peak(motion_progress, 0.22, 0.52, 0.78)
                recover = self._phase_peak(motion_progress, 0.70, 0.88, 1.00)
                jump = 22.0 * windup + 40.0 * strike
                bob = math.sin(motion_progress * math.tau * 4.2) * 2.4
                draw_dx = direction * (-16.0 * windup + 42.0 * strike - 10.0 * recover)
                draw_dy = -12.0 * strike
                torso_shift_x = direction * (-10.0 * windup + 18.0 * strike)
                torso_shift_y = -16.0 * windup - 16.0 * strike
                head_shift_x = torso_shift_x * 0.65
                head_shift_y = torso_shift_y * 0.48
                shoulder_shift_x = direction * (-18.0 * windup + 22.0 * strike - 6.0 * recover)
                shoulder_shift_y = -10.0 * windup - 8.0 * strike
                hip_shift_x = direction * (-4.0 * windup + 16.0 * strike - 4.0 * recover)
                hip_shift_y = -7.0 * windup - 6.0 * strike
                waist_bend_x = direction * (-10.0 * windup + 18.0 * strike - 6.0 * recover)
                waist_bend_y = 8.0 * windup - 10.0 * strike + 2.0 * recover
                head_rotation = direction * (-8.0 * windup + 12.0 * strike - 4.0 * recover)
                body_lean = direction * (-30.0 * windup + 34.0 * strike - 10.0 * recover)
                rotation = direction * (-4.0 * windup + 16.0 * strike - 4.0 * recover)
                pulse = 1.10 + 0.04 * strike
            elif motion == "double-palm-push":
                windup = self._phase_peak(motion_progress, 0.00, 0.22, 0.40)
                strike = self._phase_peak(motion_progress, 0.28, 0.58, 0.88)
                recover = self._phase_peak(motion_progress, 0.84, 0.94, 1.00)
                bob = math.sin(motion_progress * math.pi * 2.2) * 1.8
                draw_dx = direction * (-10.0 * windup + 24.0 * strike - 10.0 * recover)
                torso_shift_x = direction * (-12.0 * windup + 20.0 * strike)
                torso_shift_y = -8.0 * windup - 3.0 * strike
                head_shift_x = torso_shift_x * 0.62
                head_shift_y = torso_shift_y * 0.36
                shoulder_shift_x = direction * (-16.0 * windup + 26.0 * strike - 8.0 * recover)
                shoulder_shift_y = -6.0 * windup - 3.0 * strike
                hip_shift_x = direction * (-5.0 * windup + 12.0 * strike)
                hip_shift_y = 2.0 * windup - 2.0 * strike
                waist_bend_x = direction * (-12.0 * windup + 14.0 * strike - 4.0 * recover)
                waist_bend_y = 10.0 * windup - 6.0 * strike + 2.0 * recover
                head_rotation = direction * (-6.0 * windup + 8.0 * strike - 2.0 * recover)
                body_lean = direction * (-18.0 * windup + 24.0 * strike - 10.0 * recover)
                pulse = 1.07 + 0.02 * strike
            elif motion == "spin-kick":
                lift = self._phase_peak(motion_progress, 0.10, 0.40, 0.74)
                strike = self._phase_peak(motion_progress, 0.28, 0.56, 0.82)
                recover = self._phase_peak(motion_progress, 0.74, 0.90, 1.00)
                jump = 8.0 * lift + 18.0 * strike
                bob = math.sin(motion_progress * math.tau * 4.0) * 1.6
                draw_dx = direction * (-6.0 * lift + 14.0 * strike - 6.0 * recover)
                torso_shift_x = direction * (-4.0 * lift + 5.0 * strike)
                torso_shift_y = -5.0 * lift - 4.0 * strike
                head_shift_x = torso_shift_x * 0.55
                head_shift_y = torso_shift_y * 0.45
                shoulder_shift_x = direction * (-10.0 * lift + 12.0 * strike)
                shoulder_shift_y = -5.0 * lift - 4.0 * strike
                hip_shift_x = direction * (6.0 * lift - 8.0 * strike)
                hip_shift_y = -4.0 * lift
                body_lean = direction * (-8.0 * lift + 12.0 * strike)
                rotation = 320.0 * motion_progress * direction
                pulse = 1.07 + 0.02 * strike
            elif motion == "diagonal-kick":
                windup = self._phase_peak(motion_progress, 0.00, 0.22, 0.40)
                strike = self._phase_peak(motion_progress, 0.30, 0.60, 0.90)
                recover = self._phase_peak(motion_progress, 0.86, 0.95, 1.00)
                jump = 12.0 * windup + 22.0 * strike
                bob = math.sin(motion_progress * math.tau * 2.4) * 1.2
                draw_dx = direction * (-10.0 * windup + 24.0 * strike - 8.0 * recover)
                torso_shift_x = direction * (-8.0 * windup + 18.0 * strike)
                torso_shift_y = -10.0 * windup - 14.0 * strike
                head_shift_x = torso_shift_x * 0.58
                head_shift_y = torso_shift_y * 0.44
                shoulder_shift_x = direction * (-16.0 * windup + 24.0 * strike - 6.0 * recover)
                shoulder_shift_y = -8.0 * windup - 7.0 * strike
                hip_shift_x = direction * (-3.0 * windup + 14.0 * strike - 5.0 * recover)
                hip_shift_y = -6.0 * windup - 5.0 * strike
                waist_bend_x = direction * (-12.0 * windup + 16.0 * strike - 5.0 * recover)
                waist_bend_y = 10.0 * windup - 8.0 * strike + 2.0 * recover
                head_rotation = direction * (-6.0 * windup + 10.0 * strike - 3.0 * recover)
                body_lean = direction * (-26.0 * windup + 62.0 * strike - 14.0 * recover)
                rotation = direction * (-10.0 * windup + 84.0 * strike - 14.0 * recover)
                pulse = 1.07 + 0.02 * strike
            elif motion == "hook-punch":
                load = self._phase_peak(motion_progress, 0.00, 0.16, 0.30)
                snap = self._phase_peak(motion_progress, 0.18, 0.40, 0.58)
                recover = self._phase_peak(motion_progress, 0.56, 0.82, 1.00)
                bob = math.sin(motion_progress * math.tau * 3.2) * 1.0
                jump = 9.0 * snap
                draw_dx = direction * (-22.0 * load + 34.0 * snap - 10.0 * recover)
                draw_dy = 16.0 * load - 18.0 * snap + 4.0 * recover
                torso_shift_x = direction * (-16.0 * load + 20.0 * snap)
                torso_shift_y = 14.0 * load - 18.0 * snap + 4.0 * recover
                head_shift_x = torso_shift_x * 0.55
                head_shift_y = -8.0 * load - 14.0 * snap
                shoulder_shift_x = direction * (-28.0 * load + 34.0 * snap - 8.0 * recover)
                shoulder_shift_y = 8.0 * load - 24.0 * snap + 3.0 * recover
                hip_shift_x = direction * (-10.0 * load + 24.0 * snap - 6.0 * recover)
                hip_shift_y = 16.0 * load - 6.0 * snap
                waist_bend_x = direction * (-24.0 * load + 18.0 * snap - 5.0 * recover)
                waist_bend_y = 22.0 * load - 12.0 * snap + 3.0 * recover
                head_rotation = direction * (-18.0 * load + 14.0 * snap - 4.0 * recover)
                body_lean = direction * (-40.0 * load + 32.0 * snap - 12.0 * recover)
                rotation = direction * (-16.0 * load + 18.0 * snap - 4.0 * recover)
                pulse = 1.07 + 0.03 * snap
            elif motion == "swing-punch":
                load = self._phase_peak(motion_progress, 0.00, 0.18, 0.34)
                whip = self._phase_peak(motion_progress, 0.24, 0.48, 0.74)
                recover = self._phase_peak(motion_progress, 0.70, 0.88, 1.00)
                bob = math.sin(motion_progress * math.tau * 2.8) * 0.9
                jump = 8.0 * whip
                draw_dx = direction * (-26.0 * load + 40.0 * whip - 12.0 * recover)
                draw_dy = 18.0 * load - 18.0 * whip + 4.0 * recover
                torso_shift_x = direction * (-18.0 * load + 24.0 * whip)
                torso_shift_y = 14.0 * load - 16.0 * whip + 4.0 * recover
                head_shift_x = torso_shift_x * 0.6
                head_shift_y = -10.0 * load - 12.0 * whip
                shoulder_shift_x = direction * (-34.0 * load + 42.0 * whip - 10.0 * recover)
                shoulder_shift_y = 10.0 * load - 22.0 * whip + 3.0 * recover
                hip_shift_x = direction * (-12.0 * load + 28.0 * whip - 8.0 * recover)
                hip_shift_y = 18.0 * load - 8.0 * whip
                waist_bend_x = direction * (-30.0 * load + 22.0 * whip - 6.0 * recover)
                waist_bend_y = 24.0 * load - 14.0 * whip + 3.0 * recover
                head_rotation = direction * (-24.0 * load + 18.0 * whip - 5.0 * recover)
                body_lean = direction * (-48.0 * load + 30.0 * whip - 12.0 * recover)
                rotation = direction * (-24.0 * load + 30.0 * whip - 8.0 * recover)
                pulse = 1.07 + 0.02 * whip
            elif motion == "straight-punch":
                load = self._phase_peak(motion_progress, 0.00, 0.14, 0.26)
                snap = self._phase_peak(motion_progress, 0.18, 0.34, 0.52)
                recover = self._phase_peak(motion_progress, 0.50, 0.74, 1.00)
                bob = math.sin(motion_progress * math.tau * 3.6) * 0.9
                jump = 8.0 * snap
                draw_dx = direction * (-18.0 * load + 52.0 * snap - 14.0 * recover)
                draw_dy = 14.0 * load - 16.0 * snap + 3.0 * recover
                torso_shift_x = direction * (-14.0 * load + 30.0 * snap)
                torso_shift_y = 10.0 * load - 16.0 * snap + 3.0 * recover
                head_shift_x = torso_shift_x * 0.52
                head_shift_y = -8.0 * load - 14.0 * snap
                shoulder_shift_x = direction * (-24.0 * load + 38.0 * snap - 10.0 * recover)
                shoulder_shift_y = 6.0 * load - 22.0 * snap + 3.0 * recover
                hip_shift_x = direction * (-8.0 * load + 22.0 * snap - 6.0 * recover)
                hip_shift_y = 16.0 * load - 6.0 * snap
                waist_bend_x = direction * (-20.0 * load + 18.0 * snap - 5.0 * recover)
                waist_bend_y = 18.0 * load - 10.0 * snap + 3.0 * recover
                head_rotation = direction * (-14.0 * load + 12.0 * snap - 4.0 * recover)
                body_lean = direction * (-32.0 * load + 40.0 * snap - 10.0 * recover)
                rotation = direction * (-14.0 * load + 18.0 * snap - 4.0 * recover)
                pulse = 1.09 + 0.02 * snap
            elif motion == "combo-punch":
                straight = self._phase_peak(motion_progress, 0.00, 0.16, 0.34)
                hook = self._phase_peak(motion_progress, 0.33, 0.50, 0.67)
                swing = self._phase_peak(motion_progress, 0.66, 0.83, 0.98)
                reset = self._phase_peak(motion_progress, 0.94, 0.98, 1.00)
                bob = math.sin(motion_progress * math.tau * 2.0) * 0.8
                jump = 7.0 * straight + 9.0 * hook + 9.0 * swing
                draw_dx = direction * (28.0 * straight + 22.0 * hook + 30.0 * swing - 8.0 * reset)
                draw_dy = -10.0 * straight + 10.0 * hook + 14.0 * swing - 3.0 * reset
                torso_shift_x = direction * (20.0 * straight + 16.0 * hook + 20.0 * swing)
                torso_shift_y = -14.0 * straight + 10.0 * hook + 14.0 * swing - 3.0 * reset
                head_shift_x = torso_shift_x * 0.55
                head_shift_y = -16.0 * straight - 14.0 * hook - 16.0 * swing
                shoulder_shift_x = direction * (34.0 * straight + 30.0 * hook + 40.0 * swing - 8.0 * reset)
                shoulder_shift_y = -18.0 * straight - 16.0 * hook - 18.0 * swing + 3.0 * reset
                hip_shift_x = direction * (14.0 * straight + 20.0 * hook + 24.0 * swing - 6.0 * reset)
                hip_shift_y = 10.0 * straight + 16.0 * hook + 16.0 * swing - 1.0 * reset
                waist_bend_x = direction * (-16.0 * straight - 26.0 * hook - 30.0 * swing + 8.0 * reset)
                waist_bend_y = 16.0 * straight + 22.0 * hook + 24.0 * swing - 3.0 * reset
                head_rotation = direction * (12.0 * straight - 18.0 * hook - 24.0 * swing + 5.0 * reset)
                body_lean = direction * (28.0 * straight - 22.0 * hook + 20.0 * swing + 2.0 * reset)
                rotation = direction * (12.0 * straight - 20.0 * hook + 26.0 * swing - 5.0 * reset)
                pulse = 1.08 + 0.02 * max(straight, hook, swing)
            elif motion == "handstand-walk":
                bob = math.sin(motion_progress * math.tau * 2.0) * 2.0
                rotation = 180.0
            elif motion in {"dragon-palm", "thunder-strike", "sword-arc"}:
                bob = math.sin(motion_progress * math.tau * 3.0) * 1.8
                pulse = 1.03 + 0.03 * math.sin(motion_progress * math.pi)

        return {
            "actor_id": actor_id,
            "x": x,
            "z": z,
            "layer": layer,
            "facing": facing,
            "scale": float(actor.get("scale", 1.0) or 1.0) * pulse,
            "bob": bob,
            "jump": jump,
            "rotation": rotation,
            "draw_dx": draw_dx,
            "draw_dy": draw_dy,
            "body_lean": body_lean,
            "torso_shift_x": torso_shift_x,
            "torso_shift_y": torso_shift_y,
            "head_shift_x": head_shift_x,
            "head_shift_y": head_shift_y,
            "shoulder_shift_x": shoulder_shift_x,
            "shoulder_shift_y": shoulder_shift_y,
            "hip_shift_x": hip_shift_x,
            "hip_shift_y": hip_shift_y,
            "waist_bend_x": waist_bend_x,
            "waist_bend_y": waist_bend_y,
            "head_rotation": head_rotation,
            "beat": beat,
            "motion": motion if beat else "idle",
            "motion_progress": motion_progress if beat else 0.0,
        }

    def _draw_floor(self, scene: dict[str, Any], cx: float, cz: float, zoom: float) -> None:
        layout = self._layout_metrics()
        floor_rect = layout["floor_rect"]
        floor = self.floors.get(str(scene.get("floor") or ""), {})
        background = self.backgrounds.get(str(scene.get("background") or ""), {})
        floor_color = self._rgba(floor.get("color") or background.get("ground_color") or [0.44, 0.42, 0.38, 1.0])
        accent_color = self._rgba(floor.get("accent_color") or background.get("accent_color") or [0.62, 0.52, 0.42, 1.0], alpha_override=120)
        ground_y = floor_rect.top + int(cz * self.height * 0.04)
        polygon = [(0, ground_y), (self.width, ground_y), (self.width, self.height), (0, self.height)]
        pygame.draw.polygon(self.surface, floor_color, polygon)
        for index in range(1, 9):
            y = ground_y + index * int((self.height - ground_y) / 9)
            pygame.draw.line(self.surface, accent_color, (0, y), (self.width, y), 1)
        for index in range(-5, 6):
            x, _ = self._stage_point(float(index) * 1.45, 0.0, cx, cz, zoom)
            pygame.draw.line(self.surface, accent_color, (x, ground_y), (int(self.width * 0.5 + (x - self.width * 0.5) * 1.8), self.height), 1)

    def _draw_room_box(self, scene: dict[str, Any]) -> None:
        box = scene.get("box")
        if not isinstance(box, dict):
            return
        back = self._rgba(box.get("back_wall_color") or box.get("wall_color") or [0.90, 0.90, 0.88, 1.0], alpha_override=210)
        side = self._rgba(box.get("left_wall_color") or box.get("wall_color") or [0.82, 0.82, 0.80, 1.0], alpha_override=170)
        ceiling = self._rgba(box.get("ceiling_color") or [0.96, 0.96, 0.94, 1.0], alpha_override=120)
        back_rect = pygame.Rect(int(self.width * 0.14), int(self.height * 0.16), int(self.width * 0.72), int(self.height * 0.44))
        pygame.draw.rect(self.surface, back, back_rect, border_radius=24)
        pygame.draw.polygon(self.surface, side, [(0, int(self.height * 0.24)), (back_rect.left, back_rect.top), (back_rect.left, back_rect.bottom), (0, int(self.height * 0.86))])
        pygame.draw.polygon(self.surface, side, [(self.width, int(self.height * 0.24)), (back_rect.right, back_rect.top), (back_rect.right, back_rect.bottom), (self.width, int(self.height * 0.86))])
        pygame.draw.polygon(self.surface, ceiling, [(back_rect.left, back_rect.top), (back_rect.right, back_rect.top), (self.width, int(self.height * 0.24)), (0, int(self.height * 0.24))])

    def _prop_rect(self, prop: dict[str, Any], mount: str, cx: float, cz: float, zoom: float, asset: dict[str, Any]) -> pygame.Rect:
        width_px = max(26, int((asset.get("base_width") or 160) * float(prop.get("scale", 1.0) or 1.0) * zoom))
        height_px = max(26, int((asset.get("base_height") or 120) * float(prop.get("scale", 1.0) or 1.0) * zoom))
        if mount == "back-wall":
            center_x = int(self.width * 0.5 + (float(prop.get("x", 0.0) or 0.0) - cx) * self.width * 0.045 * zoom)
            center_y = int(self.height * 0.38 + (float(prop.get("z", 0.0) or 0.0) + cz) * self.height * 0.022 * zoom)
        elif mount in {"outside-back", "between-backgrounds"}:
            center_x = int(self.width * 0.5 + (float(prop.get("x", 0.0) or 0.0) - cx * 0.35) * self.width * 0.042 * zoom)
            center_y = int(self.height * 0.39 + (float(prop.get("z", 0.0) or 0.0) + cz * 0.25) * self.height * 0.020 * zoom)
            width_px = int(width_px * 0.92)
            height_px = int(height_px * 0.92)
        elif mount == "left-wall":
            center_x = int(self.width * 0.20)
            center_y = int(self.height * 0.42)
        elif mount == "right-wall":
            center_x = int(self.width * 0.80)
            center_y = int(self.height * 0.42)
        else:
            center_x, center_y = self._stage_point(float(prop.get("x", 0.0) or 0.0), float(prop.get("z", 0.0) or 0.0), cx, cz, zoom)
            height_px = int(height_px * self._depth_scale(float(prop.get("z", 0.0) or 0.0), str(prop.get("layer") or "front"), zoom))
            width_px = int(width_px * self._depth_scale(float(prop.get("z", 0.0) or 0.0), str(prop.get("layer") or "front"), zoom))
        anchor = asset.get("anchor") or [0.5, 1.0]
        x = int(center_x - width_px * float(anchor[0] if len(anchor) > 0 else 0.5))
        y = int(center_y - height_px * float(anchor[1] if len(anchor) > 1 else 1.0))
        return pygame.Rect(x, y, width_px, height_px)

    def _draw_structural_prop(self, rect: pygame.Rect, asset: dict[str, Any], target: pygame.Surface | None = None) -> None:
        canvas = target or self.surface
        render_style = str(asset.get("render_style") or "")
        frame_color = self._rgba(asset.get("frame_color") or [0.4, 0.3, 0.2, 1.0])
        glass_color = self._rgba(asset.get("glass_color") or [0.76, 0.88, 0.96, 0.20])
        mat_color = self._rgba(asset.get("mat_color") or [0.94, 0.92, 0.88, 1.0])
        padding = max(4, int(min(rect.width, rect.height) * float(asset.get("frame_padding", 0.1) or 0.1)))
        inner = rect.inflate(-padding * 2, -padding * 2)
        if render_style == "frame":
            pygame.draw.rect(canvas, frame_color, rect, border_radius=10)
            pygame.draw.rect(canvas, mat_color, inner, border_radius=8)
            return
        pygame.draw.rect(canvas, frame_color, rect, width=max(3, padding), border_radius=10)
        opening = inner.inflate(-padding, -padding)
        pygame.draw.rect(canvas, frame_color, opening, width=max(2, padding // 3), border_radius=6)
        if render_style == "window":
            tint = (*glass_color[:3], min(18, glass_color[3]))
            pygame.draw.rect(canvas, tint, opening, border_radius=6)
            pygame.draw.line(canvas, frame_color, (opening.centerx, opening.top), (opening.centerx, opening.bottom), max(2, padding // 3))
            pygame.draw.line(canvas, frame_color, (opening.left, opening.centery), (opening.right, opening.centery), max(2, padding // 3))
        elif render_style == "double-door":
            leaf_w = max(8, int(opening.width * 0.12))
            left_leaf = pygame.Rect(opening.left, opening.top, leaf_w, opening.height)
            right_leaf = pygame.Rect(opening.right - leaf_w, opening.top, leaf_w, opening.height)
            pygame.draw.rect(canvas, (*frame_color[:3], 72), left_leaf, border_radius=4)
            pygame.draw.rect(canvas, (*frame_color[:3], 72), right_leaf, border_radius=4)
            pygame.draw.line(canvas, frame_color, (opening.centerx, opening.top), (opening.centerx, opening.bottom), max(2, padding // 3))
        elif render_style == "door":
            leaf_w = max(8, int(opening.width * 0.12))
            leaf = pygame.Rect(opening.left, opening.top, leaf_w, opening.height)
            pygame.draw.rect(canvas, (*frame_color[:3], 76), leaf, border_radius=4)
            knob = (leaf.right - max(2, padding // 4), leaf.centery)
            pygame.draw.circle(canvas, frame_color, knob, max(2, padding // 4))

    def _draw_prop(self, prop: dict[str, Any], time_ms: int, cx: float, cz: float, zoom: float, target: pygame.Surface | None = None) -> None:
        canvas = target or self.surface
        asset = self.props.get(str(prop.get("prop_id") or ""), {})
        mount = str(prop.get("mount") or asset.get("default_mount") or "free")
        rect = self._prop_rect(prop, mount, cx, cz, zoom, asset)
        render_style = str(asset.get("render_style") or "sprite")
        if render_style in {"window", "door", "double-door", "frame"}:
            self._draw_structural_prop(rect, asset, target=canvas)
            return

        asset_path = str(asset.get("asset_path") or "")
        frame = self._pick_frame(
            self._load_frames(asset_path),
            time_ms,
            period_ms=int(asset.get("motion_period_ms", 1400) or 1400),
            path_value=asset_path,
        )
        if frame is not None:
            scaled = self._scaled_surface(f"prop:{asset.get('id') or prop.get('prop_id')}", frame, rect.width, rect.height)
            canvas.blit(scaled, rect.topleft)
            return
        color = self._rgba(asset.get("color") or [0.84, 0.82, 0.78, 1.0])
        pygame.draw.rect(canvas, color, rect, border_radius=16)

    def _wall_layer(self, scene: dict[str, Any]) -> dict[str, Any] | None:
        raw = scene.get("wall_layer")
        auto_asset = discover_wall_layer_asset()
        if not isinstance(raw, dict):
            if auto_asset is None:
                return None
            raw = {
                "x": 0.0,
                "y": 0.0,
                "width": 1.0,
                "height": 1.0,
                "asset_path": str(auto_asset),
                "opacity": 1.0,
            }
        box = scene.get("box") or {}
        asset_path = str(raw.get("asset_path") or raw.get("image_path") or "").strip()
        image_url = str(raw.get("image_url") or "").strip()
        background_id = str(raw.get("background_id") or raw.get("texture_background") or "").strip()
        if not asset_path and not image_url and not background_id and auto_asset is not None:
            asset_path = str(auto_asset)
        return {
            "x": float(raw.get("x", 0.0) or 0.0),
            "y": float(raw.get("y", 0.0) or 0.0),
            "width": float(raw.get("width", 1.0) or 1.0),
            "height": float(raw.get("height", 1.0) or 1.0),
            "color": raw.get("color") or box.get("back_wall_color") or box.get("wall_color") or [0.90, 0.90, 0.88, 0.92],
            "trim_color": raw.get("trim_color") or box.get("wall_color") or [0.60, 0.48, 0.34, 1.0],
            "border_radius": int(raw.get("border_radius", 24) or 24),
            "border_width": int(raw.get("border_width", 4) or 4),
            "background_id": background_id,
            "image_url": image_url,
            "asset_path": asset_path,
            "opacity": max(0.0, min(1.0, float(raw.get("opacity", 1.0) or 1.0))),
        }

    def _wall_rect(self, wall_layer: dict[str, Any]) -> pygame.Rect:
        backdrop_rect = self._layout_metrics()["backdrop_rect"]
        return pygame.Rect(
            int(backdrop_rect.left + backdrop_rect.width * wall_layer["x"]),
            int(backdrop_rect.top + backdrop_rect.height * wall_layer["y"]),
            max(32, int(backdrop_rect.width * wall_layer["width"])),
            max(32, int(backdrop_rect.height * wall_layer["height"])),
        )

    def _wall_layer_surface(self, scene: dict[str, Any]) -> pygame.Surface | None:
        wall_layer = self._wall_layer(scene)
        if wall_layer is None:
            return None
        wall_rect = self._wall_rect(wall_layer)
        wall_asset_path = wall_layer["asset_path"]
        if wall_layer["image_url"]:
            cached = _cached_remote_asset(wall_layer["image_url"], "wall_layers")
            if cached is not None:
                wall_asset_path = str(cached)
        cache_key = ":".join(
            [
                str(scene.get("id") or "scene"),
                str(wall_rect.left),
                str(wall_rect.top),
                str(wall_rect.width),
                str(wall_rect.height),
                wall_asset_path,
                str(wall_layer["background_id"]),
                str(wall_layer["opacity"]),
            ]
        )
        cached_surface = self._wall_layer_cache.get(cache_key)
        if cached_surface is not None:
            return cached_surface

        wall_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA, 32)
        if wall_asset_path:
            image = self._pick_frame(self._load_frames(wall_asset_path), 0)
            if image is not None:
                overlay_source = self._key_wall_layer_background(image)
                overlay = self._scaled_surface(f"wall-layer:{scene.get('id')}:{wall_asset_path}", overlay_source, wall_rect.width, wall_rect.height)
                if wall_layer["opacity"] < 1.0:
                    overlay = overlay.copy()
                    overlay.set_alpha(int(255 * wall_layer["opacity"]))
                content_bounds = self._content_bounds(overlay_source)
                bottom_margin_ratio = max(0.0, (overlay_source.get_height() - content_bounds.bottom) / max(1, overlay_source.get_height()))
                y_shift = int(round(bottom_margin_ratio * wall_rect.height))
                wall_surface.blit(overlay, (wall_rect.left, wall_rect.top + y_shift))
        elif wall_layer["background_id"] and wall_layer["background_id"] in self.backgrounds:
            background_id = wall_layer["background_id"]
            self._paint_background(wall_surface, self.backgrounds[background_id], f"wall:{scene.get('id')}:{background_id}", dest_rect=wall_rect)
            overlay = pygame.Surface((wall_rect.width, wall_rect.height), pygame.SRCALPHA, 32)
            overlay.fill((*self._rgba(wall_layer["color"])[:3], int(214 * wall_layer["opacity"])))
            wall_surface.blit(overlay, wall_rect.topleft)
        else:
            fill = self._rgba(wall_layer["color"], alpha_override=int(255 * wall_layer["opacity"]))
            pygame.draw.rect(wall_surface, fill, wall_rect, border_radius=wall_layer["border_radius"])
            pygame.draw.rect(
                wall_surface,
                self._rgba(wall_layer["trim_color"]),
                wall_rect,
                width=max(1, wall_layer["border_width"]),
                border_radius=wall_layer["border_radius"],
            )
        self._wall_layer_cache[cache_key] = wall_surface
        return wall_surface

    def _wall_opening_mask(self, scene: dict[str, Any]) -> pygame.Surface | None:
        wall_surface = self._wall_layer_surface(scene)
        if wall_surface is None:
            return None
        scene_id = str(scene.get("id") or "scene")
        cached_mask = self._wall_opening_mask_cache.get(scene_id)
        if cached_mask is not None:
            return cached_mask

        layout = self._layout_metrics()
        backdrop_rect = layout["backdrop_rect"]
        opaque_mask = pygame.mask.from_surface(wall_surface, threshold=1)
        opening_mask = opaque_mask.to_surface(
            setcolor=(0, 0, 0, 0),
            unsetcolor=(255, 255, 255, 255),
        ).convert_alpha()
        clipped_mask = pygame.Surface((self.width, self.height), pygame.SRCALPHA, 32)
        clipped_mask.set_clip(backdrop_rect)
        clipped_mask.blit(opening_mask, (0, 0))
        clipped_mask.set_clip(None)
        self._wall_opening_mask_cache[scene_id] = clipped_mask
        return clipped_mask

    def _draw_wall_layer(self, scene: dict[str, Any]) -> None:
        wall_surface = self._wall_layer_surface(scene)
        if wall_surface is None:
            return
        self.surface.blit(wall_surface, (0, 0))

    @staticmethod
    def _point_from(origin: tuple[float, float], length: float, angle_deg: float) -> tuple[float, float]:
        angle = math.radians(angle_deg)
        return (origin[0] + math.cos(angle) * length, origin[1] + math.sin(angle) * length)

    @staticmethod
    def _polygon_bounds(points: list[tuple[int, int]]) -> pygame.Rect:
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        left = min(xs)
        top = min(ys)
        return pygame.Rect(left, top, max(1, max(xs) - left), max(1, max(ys) - top))

    @staticmethod
    def _inset_quad(points: list[tuple[int, int]], top_inset: int, bottom_inset: int, y_inset: int) -> list[tuple[int, int]]:
        if len(points) != 4:
            return points
        top_left, top_right, bottom_right, bottom_left = points
        return [
            (top_left[0] + top_inset, top_left[1] + y_inset),
            (top_right[0] - top_inset, top_right[1] + y_inset),
            (bottom_right[0] - bottom_inset, bottom_right[1] - y_inset),
            (bottom_left[0] + bottom_inset, bottom_left[1] - y_inset),
        ]

    def _blit_surface_to_polygon(
        self,
        target: pygame.Surface,
        cache_key: str,
        source: pygame.Surface,
        points: list[tuple[int, int]],
    ) -> None:
        bounds = self._polygon_bounds(points)
        if bounds.width <= 0 or bounds.height <= 0:
            return
        scaled = self._scaled_surface(cache_key, source, bounds.width, bounds.height)
        layer = pygame.Surface(target.get_size(), pygame.SRCALPHA, 32)
        layer.blit(scaled, bounds.topleft)
        mask = pygame.Surface(target.get_size(), pygame.SRCALPHA, 32)
        pygame.draw.polygon(mask, (255, 255, 255, 255), points)
        layer.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        target.blit(layer, (0, 0))

    def _blit_surface_to_rounded_rect(
        self,
        target: pygame.Surface,
        cache_key: str,
        source: pygame.Surface,
        rect: pygame.Rect,
        *,
        border_radius: int,
    ) -> None:
        if rect.width <= 0 or rect.height <= 0:
            return
        scaled = self._scaled_surface(cache_key, source, rect.width, rect.height)
        layer = pygame.Surface(target.get_size(), pygame.SRCALPHA, 32)
        layer.blit(scaled, rect.topleft)
        mask = pygame.Surface(target.get_size(), pygame.SRCALPHA, 32)
        pygame.draw.rect(mask, (255, 255, 255, 255), rect, border_radius=max(0, border_radius))
        layer.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        target.blit(layer, (0, 0))

    @staticmethod
    def _scale_polygon(
        points: list[tuple[int, int]],
        center: tuple[float, float],
        scale_x: float,
        scale_y: float,
    ) -> list[tuple[int, int]]:
        return [
            (
                int(center[0] + (point[0] - center[0]) * scale_x),
                int(center[1] + (point[1] - center[1]) * scale_y),
            )
            for point in points
        ]

    def _draw_tapered_segment(
        self,
        surface: pygame.Surface,
        start: tuple[float, float],
        end: tuple[float, float],
        start_width: float,
        end_width: float,
        color: tuple[int, int, int, int],
    ) -> None:
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = math.hypot(dx, dy)
        if length <= 0.001:
            pygame.draw.circle(surface, color, (int(start[0]), int(start[1])), max(2, int(start_width * 0.5)))
            return
        nx = -dy / length
        ny = dx / length
        sw = max(2.0, start_width * 0.5)
        ew = max(2.0, end_width * 0.5)
        points = [
            (int(start[0] + nx * sw), int(start[1] + ny * sw)),
            (int(end[0] + nx * ew), int(end[1] + ny * ew)),
            (int(end[0] - nx * ew), int(end[1] - ny * ew)),
            (int(start[0] - nx * sw), int(start[1] - ny * sw)),
        ]
        pygame.draw.polygon(surface, color, points)
        pygame.draw.circle(surface, color, (int(start[0]), int(start[1])), max(2, int(sw)))
        pygame.draw.circle(surface, color, (int(end[0]), int(end[1])), max(2, int(ew)))

    def _draw_segmented_limb(
        self,
        surface: pygame.Surface,
        start: tuple[float, float],
        mid: tuple[float, float],
        end: tuple[float, float],
        color: tuple[int, int, int, int],
        upper_width: int,
        lower_width: int,
        joint_radius: int,
        end_radius: int,
        end_color: tuple[int, int, int, int],
        foot_angle: float | None = None,
        foot_length: float = 0.0,
    ) -> None:
        self._draw_tapered_segment(surface, start, mid, upper_width, max(upper_width * 0.78, lower_width), color)
        self._draw_tapered_segment(surface, mid, end, lower_width, max(lower_width * 0.68, end_radius * 1.6), color)
        pygame.draw.circle(surface, color, (int(start[0]), int(start[1])), max(2, joint_radius))
        pygame.draw.circle(surface, color, (int(mid[0]), int(mid[1])), max(2, joint_radius))
        if foot_angle is None:
            hand_width = max(3, int(end_radius * 1.5))
            hand_height = max(4, int(end_radius * 2.0))
            hand_rect = pygame.Rect(0, 0, hand_width, hand_height)
            hand_rect.center = (int(end[0]), int(end[1]))
            pygame.draw.ellipse(surface, end_color, hand_rect)
        else:
            heel = self._point_from(end, foot_length * 0.18, foot_angle + 180.0)
            foot_tip = self._point_from(end, foot_length, foot_angle)
            sole_half = max(2.0, end_radius * 0.72)
            heel_upper = self._point_from(heel, sole_half, foot_angle - 90.0)
            heel_lower = self._point_from(heel, sole_half, foot_angle + 90.0)
            toe_upper = self._point_from(foot_tip, sole_half * 0.86, foot_angle - 90.0)
            toe_lower = self._point_from(foot_tip, sole_half * 0.86, foot_angle + 90.0)
            pygame.draw.polygon(
                surface,
                end_color,
                [
                    (int(heel_upper[0]), int(heel_upper[1])),
                    (int(toe_upper[0]), int(toe_upper[1])),
                    (int(toe_lower[0]), int(toe_lower[1])),
                    (int(heel_lower[0]), int(heel_lower[1])),
                ],
            )
            pygame.draw.circle(surface, end_color, (int(end[0]), int(end[1])), max(2, int(end_radius * 0.8)))

    def _default_hairstyle(self, meta: dict[str, Any], actor_id: str) -> str:
        asset_id = str(self.cast.get(actor_id, {}).get("asset_id") or "")
        hairstyle = str(meta.get("hairstyle") or "").strip().lower()
        if hairstyle:
            return hairstyle
        if asset_id in {"general-guard", "young-hero"}:
            return "topknot"
        if asset_id in {"official-minister", "strategist", "detective-sleek", "trump"}:
            return "side_part"
        if asset_id in {"npc-girl", "office-worker-modern", "reporter-selfie", "swordswoman", "witness-strolling"}:
            return "bob"
        if asset_id == "master-monk":
            return "monk"
        return "short"

    def _draw_head_style(
        self,
        sprite: pygame.Surface,
        head_center: tuple[int, int],
        head_radius: int,
        patch: tuple[int, int, int, int],
        actor_id: str,
        meta: dict[str, Any],
        accent: tuple[int, int, int, int],
    ) -> None:
        ear_radius = max(5, int(head_radius * 0.32))
        left_ear = (int(head_center[0] - head_radius * 0.62), int(head_center[1] - head_radius * 0.78))
        right_ear = (int(head_center[0] + head_radius * 0.62), int(head_center[1] - head_radius * 0.78))
        pygame.draw.circle(sprite, patch, left_ear, ear_radius)
        pygame.draw.circle(sprite, patch, right_ear, ear_radius)

        hair_style = self._default_hairstyle(meta, actor_id)
        if hair_style == "topknot":
            pygame.draw.ellipse(sprite, patch, pygame.Rect(head_center[0] - int(head_radius * 0.55), head_center[1] - int(head_radius * 0.78), int(head_radius * 1.1), int(head_radius * 0.42)))
            pygame.draw.circle(sprite, patch, (head_center[0], int(head_center[1] - head_radius * 0.95)), max(4, int(head_radius * 0.18)))
            pygame.draw.circle(sprite, accent, (head_center[0], int(head_center[1] - head_radius * 0.95)), max(2, int(head_radius * 0.08)))
        elif hair_style == "side_part":
            pygame.draw.arc(
                sprite,
                patch,
                pygame.Rect(head_center[0] - int(head_radius * 0.86), head_center[1] - int(head_radius * 0.92), int(head_radius * 1.7), int(head_radius * 0.95)),
                math.radians(192),
                math.radians(358),
                max(4, int(head_radius * 0.18)),
            )
            pygame.draw.line(
                sprite,
                patch,
                (int(head_center[0] + head_radius * 0.08), int(head_center[1] - head_radius * 0.72)),
                (int(head_center[0] - head_radius * 0.18), int(head_center[1] - head_radius * 0.25)),
                max(2, int(head_radius * 0.12)),
            )
        elif hair_style == "bob":
            pygame.draw.ellipse(sprite, patch, pygame.Rect(head_center[0] - int(head_radius * 0.82), head_center[1] - int(head_radius * 0.86), int(head_radius * 1.64), int(head_radius * 0.62)))
            pygame.draw.arc(
                sprite,
                patch,
                pygame.Rect(head_center[0] - int(head_radius * 0.92), head_center[1] - int(head_radius * 0.22), int(head_radius * 1.84), int(head_radius * 0.96)),
                math.radians(198),
                math.radians(342),
                max(4, int(head_radius * 0.18)),
            )
        elif hair_style == "monk":
            pygame.draw.arc(
                sprite,
                patch,
                pygame.Rect(head_center[0] - int(head_radius * 0.82), head_center[1] - int(head_radius * 0.82), int(head_radius * 1.64), int(head_radius * 0.74)),
                math.radians(206),
                math.radians(334),
                max(2, int(head_radius * 0.12)),
            )
        else:
            pygame.draw.arc(
                sprite,
                patch,
                pygame.Rect(head_center[0] - int(head_radius * 0.82), head_center[1] - int(head_radius * 0.84), int(head_radius * 1.64), int(head_radius * 0.82)),
                math.radians(196),
                math.radians(344),
                max(4, int(head_radius * 0.16)),
            )

    @staticmethod
    def _ease_out_cubic(progress: float) -> float:
        progress = max(0.0, min(1.0, progress))
        return 1.0 - pow(1.0 - progress, 3.0)

    @staticmethod
    def _phase_peak(progress: float, start: float, peak: float, end: float) -> float:
        progress = max(0.0, min(1.0, progress))
        if progress <= start or progress >= end:
            return 0.0
        if progress <= peak:
            return (progress - start) / max(0.001, peak - start)
        return 1.0 - (progress - peak) / max(0.001, end - peak)

    def _martial_motion_progress(self, motion: str, progress: float) -> float:
        factor = {
            "flying-kick": 1.10,
            "double-palm-push": 1.02,
            "spin-kick": 1.26,
            "diagonal-kick": 1.10,
            "hook-punch": 1.06,
            "swing-punch": 1.02,
            "straight-punch": 1.04,
            "combo-punch": 1.00,
            "somersault": 1.20,
            "big-jump": 1.16,
            "dunk": 1.18,
        }.get(str(motion or ""), 1.0)
        if factor <= 1.0:
            return max(0.0, min(1.0, progress))
        return self._ease_out_cubic(progress ** (1.0 / factor))

    def _pose_angles(self, motion: str, progress: float) -> dict[str, float]:
        walk = math.sin(progress * math.tau)
        talk = math.sin(progress * math.tau * 2.0)
        pose = {
            "front_upper_arm": 78 + talk * 2,
            "front_lower_arm": 94 + talk * 4,
            "back_upper_arm": 102 - talk * 2,
            "back_lower_arm": 94 - talk * 3,
            "front_upper_leg": 88 - walk * 7,
            "front_lower_leg": 98 + walk * 5,
            "back_upper_leg": 98 + walk * 7,
            "back_lower_leg": 94 - walk * 5,
            "front_foot": 5,
            "back_foot": -5,
        }
        if motion == "point":
            pose.update({"front_upper_arm": 16, "front_lower_arm": -2, "back_upper_arm": 110, "back_lower_arm": 92, "front_upper_leg": 86, "back_upper_leg": 101})
        elif motion == "dragon-palm":
            pose.update({"front_upper_arm": 8 + progress * 10, "front_lower_arm": 10 + progress * 6, "back_upper_arm": 128, "back_lower_arm": 102, "front_upper_leg": 82, "front_lower_leg": 100, "back_upper_leg": 106, "back_lower_leg": 92, "front_foot": 2, "back_foot": -10})
        elif motion == "sword-arc":
            pose.update({"front_upper_arm": -18 + progress * 34, "front_lower_arm": -24 + progress * 44, "back_upper_arm": 142, "back_lower_arm": 112, "front_upper_leg": 84, "front_lower_leg": 96, "back_upper_leg": 104, "back_lower_leg": 90})
        elif motion == "thunder-strike":
            pose.update({"front_upper_arm": -28, "front_lower_arm": -18, "back_upper_arm": 156, "back_lower_arm": 132, "front_upper_leg": 86, "front_lower_leg": 98, "back_upper_leg": 100, "back_lower_leg": 92})
        elif motion == "flying-kick":
            windup = self._phase_peak(progress, 0.00, 0.14, 0.30)
            strike = self._phase_peak(progress, 0.22, 0.48, 0.76)
            recover = self._phase_peak(progress, 0.72, 0.88, 1.00)
            pose.update(
                {
                    "front_upper_arm": 162 - windup * 26 - strike * 54 + recover * 18,
                    "front_lower_arm": 138 - windup * 20 - strike * 70 + recover * 24,
                    "back_upper_arm": 26 + windup * 30 + strike * 26 - recover * 10,
                    "back_lower_arm": 54 + windup * 16 + strike * 16,
                    "front_upper_leg": 72 - windup * 62 - strike * 74 + recover * 30,
                    "front_lower_leg": 84 - windup * 76 - strike * 108 + recover * 50,
                    "back_upper_leg": 132 + windup * 20 - strike * 18 - recover * 10,
                    "back_lower_leg": 150 + windup * 16 + strike * 20 - recover * 16,
                    "front_foot": 18 + strike * 22,
                    "back_foot": -12 - windup * 10,
                }
            )
        elif motion == "double-palm-push":
            windup = self._phase_peak(progress, 0.00, 0.16, 0.34)
            strike = self._phase_peak(progress, 0.24, 0.44, 0.70)
            recover = self._phase_peak(progress, 0.66, 0.86, 1.00)
            pose.update(
                {
                    "front_upper_arm": 94 - windup * 78 - strike * 98 + recover * 34,
                    "front_lower_arm": 102 - windup * 62 - strike * 118 + recover * 40,
                    "back_upper_arm": 96 - windup * 72 - strike * 104 + recover * 30,
                    "back_lower_arm": 94 - windup * 56 - strike * 116 + recover * 36,
                    "front_upper_leg": 86 + windup * 12 - strike * 18 + recover * 6,
                    "front_lower_leg": 100 + windup * 8 - strike * 10,
                    "back_upper_leg": 104 + windup * 26 - strike * 32 + recover * 12,
                    "back_lower_leg": 94 + windup * 12 - strike * 6,
                    "front_foot": 4 + strike * 6,
                    "back_foot": -6 - windup * 12,
                }
            )
        elif motion == "spin-kick":
            sweep = math.sin(progress * math.tau * 1.35)
            lift = self._phase_peak(progress, 0.12, 0.42, 0.76)
            recoil = self._phase_peak(progress, 0.68, 0.84, 1.00)
            pose.update(
                {
                    "front_upper_arm": 94 + sweep * 38 - recoil * 14,
                    "front_lower_arm": 102 + sweep * 24 - recoil * 8,
                    "back_upper_arm": 96 - sweep * 42 + recoil * 10,
                    "back_lower_arm": 90 - sweep * 26 + recoil * 8,
                    "front_upper_leg": 84 - lift * 68 + recoil * 18,
                    "front_lower_leg": 96 - lift * 86 + recoil * 30,
                    "back_upper_leg": 102 + lift * 18 - recoil * 10,
                    "back_lower_leg": 94 + lift * 54 - recoil * 24,
                    "front_foot": 10 + lift * 16,
                    "back_foot": -10 - lift * 12,
                }
            )
        elif motion == "diagonal-kick":
            windup = self._phase_peak(progress, 0.00, 0.18, 0.34)
            strike = self._phase_peak(progress, 0.24, 0.46, 0.72)
            recover = self._phase_peak(progress, 0.70, 0.88, 1.00)
            pose.update(
                {
                    "front_upper_arm": 126 - windup * 18 - strike * 24 + recover * 16,
                    "front_lower_arm": 116 - windup * 14 - strike * 26 + recover * 14,
                    "back_upper_arm": 62 + windup * 18 + strike * 12 - recover * 6,
                    "back_lower_arm": 76 + windup * 10 + strike * 12,
                    "front_upper_leg": 82 - windup * 44 - strike * 72 + recover * 30,
                    "front_lower_leg": 98 - windup * 52 - strike * 86 + recover * 36,
                    "back_upper_leg": 94 - windup * 38 - strike * 68 + recover * 26,
                    "back_lower_leg": 108 - windup * 46 - strike * 80 + recover * 34,
                    "front_foot": 20 + strike * 12,
                    "back_foot": 12 + strike * 10,
                }
            )
        elif motion == "hook-punch":
            load = self._phase_peak(progress, 0.00, 0.14, 0.28)
            snap = self._phase_peak(progress, 0.20, 0.38, 0.58)
            recoil = self._phase_peak(progress, 0.56, 0.80, 1.00)
            pose.update(
                {
                    "front_upper_arm": 122 + load * 74 - snap * 152 + recoil * 52,
                    "front_lower_arm": 122 + load * 46 - snap * 160 + recoil * 64,
                    "back_upper_arm": 170 + load * 48 - snap * 34 - recoil * 28,
                    "back_lower_arm": 120 + load * 30 - snap * 12 - recoil * 16,
                    "front_upper_leg": 94 + load * 14 - snap * 28 + recoil * 8,
                    "front_lower_leg": 114 + load * 24 - snap * 40 + recoil * 12,
                    "back_upper_leg": 118 + load * 32 - snap * 26,
                    "back_lower_leg": 112 + load * 16 - snap * 10,
                    "front_foot": 4,
                    "back_foot": -10 - load * 10,
                }
            )
        elif motion == "swing-punch":
            load = self._phase_peak(progress, 0.00, 0.18, 0.34)
            whip = self._phase_peak(progress, 0.24, 0.48, 0.74)
            recover = self._phase_peak(progress, 0.70, 0.88, 1.00)
            pose.update(
                {
                    "front_upper_arm": 178 + load * 52 - whip * 168 + recover * 58,
                    "front_lower_arm": 154 + load * 36 - whip * 120 + recover * 42,
                    "back_upper_arm": -8 + load * 28 + whip * 84 - recover * 24,
                    "back_lower_arm": 32 + load * 24 + whip * 60 - recover * 16,
                    "front_upper_leg": 92 + load * 10 - whip * 18 - recover * 4,
                    "front_lower_leg": 110 + load * 18 - whip * 18 - recover * 6,
                    "back_upper_leg": 120 + load * 30 - whip * 32 + recover * 12,
                    "back_lower_leg": 108 + load * 12 - whip * 10,
                    "front_foot": 10 + whip * 12,
                    "back_foot": -12 - load * 12,
                }
            )
        elif motion == "straight-punch":
            load = self._phase_peak(progress, 0.00, 0.14, 0.26)
            snap = self._phase_peak(progress, 0.18, 0.34, 0.52)
            recover = self._phase_peak(progress, 0.50, 0.74, 1.00)
            pose.update(
                {
                    "front_upper_arm": 108 + load * 34 - snap * 154 + recover * 48,
                    "front_lower_arm": 110 + load * 24 - snap * 178 + recover * 58,
                    "back_upper_arm": 162 + load * 48 - snap * 28 - recover * 24,
                    "back_lower_arm": 120 + load * 34 - snap * 10 - recover * 16,
                    "front_upper_leg": 92 + load * 12 - snap * 20 + recover * 6,
                    "front_lower_leg": 110 + load * 18 - snap * 24 + recover * 8,
                    "back_upper_leg": 118 + load * 28 - snap * 20,
                    "back_lower_leg": 108 + load * 14 - snap * 10,
                    "front_foot": 4,
                    "back_foot": -10 - load * 8,
                }
            )
        elif motion == "combo-punch":
            straight = self._phase_peak(progress, 0.00, 0.16, 0.34)
            hook = self._phase_peak(progress, 0.33, 0.50, 0.67)
            swing = self._phase_peak(progress, 0.66, 0.83, 0.98)
            reset = self._phase_peak(progress, 0.94, 0.98, 1.00)
            pose.update(
                {
                    "front_upper_arm": 110 - straight * 154 - hook * 148 - swing * 132 + reset * 42,
                    "front_lower_arm": 112 - straight * 178 - hook * 166 - swing * 146 + reset * 52,
                    "back_upper_arm": 162 + straight * 30 + hook * 54 - swing * 142 + reset * 20,
                    "back_lower_arm": 120 + straight * 24 + hook * 34 - swing * 150 + reset * 14,
                    "front_upper_leg": 92 + straight * 10 + hook * 14 + swing * 10 - reset * 4,
                    "front_lower_leg": 110 + straight * 14 + hook * 18 + swing * 12 - reset * 2,
                    "back_upper_leg": 120 + straight * 26 + hook * 34 + swing * 30 - reset * 8,
                    "back_lower_leg": 108 + straight * 14 + hook * 18 + swing * 16 - reset * 4,
                    "front_foot": 4 + straight * 8 + hook * 6,
                    "back_foot": -8 - swing * 10,
                }
            )
        elif motion in {"enter", "exit"}:
            swing = math.sin(progress * math.tau * 1.4)
            pose.update({"front_upper_arm": 78 + swing * 10, "front_lower_arm": 94 + swing * 6, "back_upper_arm": 102 - swing * 10, "back_lower_arm": 94 - swing * 6, "front_upper_leg": 84 - swing * 18, "front_lower_leg": 96 + swing * 7, "back_upper_leg": 102 + swing * 18, "back_lower_leg": 92 - swing * 7})
        elif motion == "big-jump":
            tuck = math.sin(progress * math.pi)
            pose.update({"front_upper_arm": 6, "front_lower_arm": 18, "back_upper_arm": 132, "back_lower_arm": 116, "front_upper_leg": 56 + tuck * 10, "front_lower_leg": 42, "back_upper_leg": 126 - tuck * 10, "back_lower_leg": 144})
        elif motion == "somersault":
            tuck = math.sin(progress * math.pi)
            pose.update({"front_upper_arm": 34, "front_lower_arm": 88, "back_upper_arm": 146, "back_lower_arm": 100, "front_upper_leg": 60 + tuck * 10, "front_lower_leg": 34, "back_upper_leg": 122 - tuck * 10, "back_lower_leg": 148})
        elif motion == "handstand-walk":
            swing = math.sin(progress * math.tau * 3.0)
            pose.update({"front_upper_arm": 82 - swing * 10, "front_lower_arm": 94 - swing * 6, "back_upper_arm": 98 + swing * 10, "back_lower_arm": 88 + swing * 6, "front_upper_leg": 52 + swing * 16, "front_lower_leg": 28, "back_upper_leg": 128 - swing * 16, "back_lower_leg": 146})
        elif motion == "talk":
            pose.update({"front_upper_arm": 68 + talk * 7, "front_lower_arm": 84 + talk * 5, "back_upper_arm": 108 - talk * 2, "back_lower_arm": 96 - talk * 2})
        return pose

    def _draw_actor(self, scene: dict[str, Any], actor: dict[str, Any], time_ms: int, cx: float, cz: float, zoom: float) -> None:
        state = self._actor_state(actor, scene, time_ms)
        beat = state["beat"]
        active_dialogue = self._active_dialogue(scene, time_ms)
        talking = bool(active_dialogue and str(active_dialogue.get("speaker_id") or "") == state["actor_id"])
        expression = self._expression_for_actor(scene, state["actor_id"], time_ms, beat)
        outfit, face, meta = self._character_skin(state["actor_id"], expression, talking, time_ms)
        center_x, center_y = self._stage_point(state["x"], state["z"], cx, cz, zoom)
        scale = self._depth_scale(state["z"], state["layer"], zoom) * float(state["scale"])

        sprite_w = max(32, int(110 * scale))
        sprite_h = max(56, int(166 * scale))
        sprite = pygame.Surface((sprite_w, sprite_h), pygame.SRCALPHA, 32)

        bone = self._rgba(meta.get("bone_color") or [0.10, 0.10, 0.11, 1.0])
        body = self._rgba(meta.get("body_color") or [0.18, 0.28, 0.38, 1.0])
        body_secondary = self._rgba(meta.get("body_secondary_color") or [0.82, 0.82, 0.82, 1.0])
        accent = self._rgba(meta.get("accent_color") or [0.84, 0.42, 0.18, 1.0])
        patch = self._rgba(meta.get("patch_color") or [0.08, 0.08, 0.09, 1.0])
        blush = self._rgba(meta.get("blush_color") or [0.96, 0.71, 0.74, 0.30])
        mouth = self._rgba(meta.get("mouth_color") or [0.66, 0.28, 0.30, 1.0])
        head_color = self._rgba(meta.get("head_color") or [0.97, 0.97, 0.95, 1.0])

        head_radius = int(sprite_w * 0.29)
        waist_bend_x = float(state.get("waist_bend_x", 0.0) or 0.0)
        waist_bend_y = float(state.get("waist_bend_y", 0.0) or 0.0)
        head_rotation = float(state.get("head_rotation", 0.0) or 0.0)
        head_center = (
            sprite_w // 2 + int(float(state.get("head_shift_x", 0.0) or 0.0) + waist_bend_x * 0.82),
            int(sprite_h * 0.24 + float(state.get("head_shift_y", 0.0) or 0.0) + waist_bend_y * 0.86),
        )
        torso_shift_x = float(state.get("torso_shift_x", 0.0) or 0.0)
        torso_shift_y = float(state.get("torso_shift_y", 0.0) or 0.0)
        shoulder_shift_x = float(state.get("shoulder_shift_x", 0.0) or 0.0)
        shoulder_shift_y = float(state.get("shoulder_shift_y", 0.0) or 0.0)
        hip_shift_x = float(state.get("hip_shift_x", 0.0) or 0.0)
        hip_shift_y = float(state.get("hip_shift_y", 0.0) or 0.0)
        chest_rect = pygame.Rect(
            int(sprite_w * 0.34 + torso_shift_x * 0.55 + shoulder_shift_x * 0.42 + waist_bend_x * 0.44),
            int(sprite_h * 0.45 + torso_shift_y + shoulder_shift_y * 0.50 + waist_bend_y * 0.44),
            max(14, int(sprite_w * 0.32)),
            max(12, int(sprite_h * 0.15)),
        )
        chest_radius = max(5, int(min(chest_rect.width, chest_rect.height) * 0.36))
        abdomen_rect = pygame.Rect(
            int(sprite_w * 0.37 + torso_shift_x * 0.58 + shoulder_shift_x * 0.16 + hip_shift_x * 0.22 + waist_bend_x * 0.22),
            int(sprite_h * 0.57 + torso_shift_y * 0.85 + shoulder_shift_y * 0.12 + hip_shift_y * 0.18 + waist_bend_y * 0.24),
            max(12, int(sprite_w * 0.26)),
            max(10, int(sprite_h * 0.12)),
        )
        pelvis_rect = pygame.Rect(
            int(sprite_w * 0.33 + torso_shift_x * 0.30 + hip_shift_x * 0.54),
            int(sprite_h * 0.68 + torso_shift_y * 0.34 + hip_shift_y * 0.42),
            max(14, int(sprite_w * 0.34)),
            max(12, int(sprite_h * 0.13)),
        )
        torso_center = (
            sprite_w * 0.50 + torso_shift_x * 0.45 + shoulder_shift_x * 0.20 + hip_shift_x * 0.20 + waist_bend_x * 0.14,
            sprite_h * 0.60 + torso_shift_y * 0.60 + shoulder_shift_y * 0.18 + hip_shift_y * 0.18 + waist_bend_y * 0.18,
        )
        torso_points = [
            (int(sprite_w * 0.32 + torso_shift_x * 0.68 + shoulder_shift_x * 0.62 + waist_bend_x * 0.58), int(sprite_h * 0.44 + torso_shift_y + shoulder_shift_y * 0.74 + waist_bend_y * 0.62)),
            (int(sprite_w * 0.68 + torso_shift_x * 0.68 + shoulder_shift_x * 0.62 + waist_bend_x * 0.58), int(sprite_h * 0.44 + torso_shift_y + shoulder_shift_y * 0.74 + waist_bend_y * 0.62)),
            (int(sprite_w * 0.63 + torso_shift_x * 0.62 + shoulder_shift_x * 0.56 + hip_shift_x * 0.10 + waist_bend_x * 0.42), int(sprite_h * 0.52 + torso_shift_y * 0.92 + shoulder_shift_y * 0.54 + hip_shift_y * 0.08 + waist_bend_y * 0.40)),
            (int(sprite_w * 0.60 + torso_shift_x * 0.58 + shoulder_shift_x * 0.28 + hip_shift_x * 0.18), int(sprite_h * 0.64 + torso_shift_y * 0.78 + shoulder_shift_y * 0.20 + hip_shift_y * 0.16)),
            (int(sprite_w * 0.65 + torso_shift_x * 0.40 + hip_shift_x * 0.46), int(sprite_h * 0.73 + torso_shift_y * 0.54 + hip_shift_y * 0.40)),
            (int(sprite_w * 0.56 + torso_shift_x * 0.22 + hip_shift_x * 0.56), int(sprite_h * 0.80 + torso_shift_y * 0.32 + hip_shift_y * 0.54)),
            (int(sprite_w * 0.44 + torso_shift_x * 0.22 + hip_shift_x * 0.56), int(sprite_h * 0.80 + torso_shift_y * 0.32 + hip_shift_y * 0.54)),
            (int(sprite_w * 0.35 + torso_shift_x * 0.40 + hip_shift_x * 0.46), int(sprite_h * 0.73 + torso_shift_y * 0.54 + hip_shift_y * 0.40)),
            (int(sprite_w * 0.40 + torso_shift_x * 0.58 + shoulder_shift_x * 0.28 + hip_shift_x * 0.18), int(sprite_h * 0.64 + torso_shift_y * 0.78 + shoulder_shift_y * 0.20 + hip_shift_y * 0.16)),
            (int(sprite_w * 0.37 + torso_shift_x * 0.62 + shoulder_shift_x * 0.56 + hip_shift_x * 0.10 + waist_bend_x * 0.42), int(sprite_h * 0.52 + torso_shift_y * 0.92 + shoulder_shift_y * 0.54 + hip_shift_y * 0.08 + waist_bend_y * 0.40)),
        ]
        neck_points = [
            (int(sprite_w * 0.46 + torso_shift_x * 0.70 + shoulder_shift_x * 0.64 + waist_bend_x * 0.72), int(sprite_h * 0.38 + torso_shift_y + shoulder_shift_y * 0.78 + waist_bend_y * 0.76)),
            (int(sprite_w * 0.54 + torso_shift_x * 0.70 + shoulder_shift_x * 0.64 + waist_bend_x * 0.72), int(sprite_h * 0.38 + torso_shift_y + shoulder_shift_y * 0.78 + waist_bend_y * 0.76)),
            (int(sprite_w * 0.57 + torso_shift_x * 0.64 + shoulder_shift_x * 0.56 + waist_bend_x * 0.66), int(sprite_h * 0.45 + torso_shift_y * 0.96 + shoulder_shift_y * 0.74 + waist_bend_y * 0.62)),
            (int(sprite_w * 0.43 + torso_shift_x * 0.64 + shoulder_shift_x * 0.56 + waist_bend_x * 0.66), int(sprite_h * 0.45 + torso_shift_y * 0.96 + shoulder_shift_y * 0.74 + waist_bend_y * 0.62)),
        ]
        front_shoulder = (
            sprite_w * 0.60 + torso_shift_x * 0.72 + shoulder_shift_x * 0.78 + waist_bend_x * 0.74,
            sprite_h * 0.47 + torso_shift_y * 0.90 + shoulder_shift_y * 0.84 + waist_bend_y * 0.76,
        )
        back_shoulder = (
            sprite_w * 0.40 + torso_shift_x * 0.72 + shoulder_shift_x * 0.58 + waist_bend_x * 0.58,
            sprite_h * 0.47 + torso_shift_y * 0.90 + shoulder_shift_y * 0.66 + waist_bend_y * 0.62,
        )
        front_hip = (
            sprite_w * 0.56 + torso_shift_x * 0.34 + hip_shift_x * 0.68,
            sprite_h * 0.73 + torso_shift_y * 0.44 + hip_shift_y * 0.78,
        )
        back_hip = (
            sprite_w * 0.44 + torso_shift_x * 0.34 + hip_shift_x * 0.52,
            sprite_h * 0.73 + torso_shift_y * 0.44 + hip_shift_y * 0.62,
        )

        pose = self._pose_angles(state["motion"], state["motion_progress"])
        upper_arm = sprite_h * 0.15
        lower_arm = sprite_h * 0.14
        upper_leg = sprite_h * 0.15
        lower_leg = sprite_h * 0.17

        front_elbow = self._point_from(front_shoulder, upper_arm, pose["front_upper_arm"])
        front_hand = self._point_from(front_elbow, lower_arm, pose["front_lower_arm"])
        back_elbow = self._point_from(back_shoulder, upper_arm, pose["back_upper_arm"])
        back_hand = self._point_from(back_elbow, lower_arm, pose["back_lower_arm"])
        front_knee = self._point_from(front_hip, upper_leg, pose["front_upper_leg"])
        front_foot = self._point_from(front_knee, lower_leg, pose["front_lower_leg"])
        back_knee = self._point_from(back_hip, upper_leg, pose["back_upper_leg"])
        back_foot = self._point_from(back_knee, lower_leg, pose["back_lower_leg"])

        self._draw_segmented_limb(sprite, back_hip, back_knee, back_foot, bone, max(6, sprite_w // 15), max(5, sprite_w // 17), max(4, sprite_w // 22), max(4, sprite_w // 22), patch, pose["back_foot"], foot_length=sprite_w * 0.17)
        self._draw_segmented_limb(sprite, front_hip, front_knee, front_foot, bone, max(6, sprite_w // 15), max(5, sprite_w // 17), max(4, sprite_w // 22), max(4, sprite_w // 22), patch, pose["front_foot"], foot_length=sprite_w * 0.17)

        pygame.draw.polygon(sprite, body_secondary, neck_points)
        pygame.draw.polygon(sprite, body, torso_points)
        pygame.draw.ellipse(sprite, body_secondary, chest_rect)
        pygame.draw.rect(sprite, (*patch[:3], 62), chest_rect, width=max(1, sprite_w // 34), border_radius=chest_radius)
        pygame.draw.ellipse(sprite, body_secondary, abdomen_rect)
        pygame.draw.ellipse(sprite, accent, pelvis_rect)
        pygame.draw.line(
            sprite,
            (*patch[:3], 110),
            (int(sprite_w * 0.38), int(sprite_h * 0.50)),
            (int(sprite_w * 0.62), int(sprite_h * 0.50)),
            max(2, sprite_w // 32),
        )
        pygame.draw.circle(sprite, body_secondary, (int(back_shoulder[0]), int(back_shoulder[1])), max(3, sprite_w // 18))
        pygame.draw.circle(sprite, body_secondary, (int(front_shoulder[0]), int(front_shoulder[1])), max(3, sprite_w // 18))
        pygame.draw.circle(sprite, accent, (int(back_hip[0]), int(back_hip[1])), max(3, sprite_w // 18))
        pygame.draw.circle(sprite, accent, (int(front_hip[0]), int(front_hip[1])), max(3, sprite_w // 18))
        if outfit is not None:
            garment_points = self._scale_polygon(
                torso_points,
                torso_center,
                0.92,
                0.95,
            )
            self._blit_surface_to_polygon(
                sprite,
                f"outfit:{state['actor_id']}",
                outfit,
                garment_points,
            )
        head_layer_size = max(24, head_radius * 4)
        head_layer = pygame.Surface((head_layer_size, head_layer_size), pygame.SRCALPHA, 32)
        local_head_center = (head_layer_size // 2, head_layer_size // 2)
        self._draw_head_style(head_layer, local_head_center, head_radius, patch, state["actor_id"], meta, accent)
        pygame.draw.circle(head_layer, head_color, local_head_center, head_radius)

        if face is not None:
            head_anchor = meta.get("head_anchor") or {}
            offset = head_anchor.get("offset") or [0, 0]
            face_scale = float(head_anchor.get("scale", 1.0) or 1.0)
            face_w = int(sprite_w * 0.56 * face_scale)
            face_h = int(sprite_w * 0.56 * face_scale)
            mouth_phase = (time_ms // 120) % 2 if talking else 0
            face_surface = self._scaled_surface(f"face:{state['actor_id']}:{expression}:{talking}:{mouth_phase}", face, face_w, face_h)
            fx = int(local_head_center[0] - face_w / 2 + float(offset[0] if len(offset) > 0 else 0) * scale * 0.15)
            fy = int(local_head_center[1] - face_h / 2 + float(offset[1] if len(offset) > 1 else 0) * scale * 0.15)
            face_layer = pygame.Surface((head_layer_size, head_layer_size), pygame.SRCALPHA, 32)
            face_layer.blit(face_surface, (fx, fy))
            head_mask = pygame.Surface((head_layer_size, head_layer_size), pygame.SRCALPHA, 32)
            pygame.draw.circle(head_mask, (255, 255, 255, 255), local_head_center, max(1, head_radius - 1))
            face_layer.blit(head_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            head_layer.blit(face_layer, (0, 0))
        else:
            eye_radius = max(2, int(sprite_w * 0.035))
            eye_y = int(local_head_center[1] - sprite_w * 0.020)
            eye_dx = int(sprite_w * 0.080)
            mouth_open = talking and (time_ms // 120) % 2 == 0
            pygame.draw.circle(head_layer, patch, (local_head_center[0] - eye_dx, eye_y), eye_radius * 2)
            pygame.draw.circle(head_layer, patch, (local_head_center[0] + eye_dx, eye_y), eye_radius * 2)
            pygame.draw.circle(head_layer, (255, 255, 255, 255), (local_head_center[0] - eye_dx, eye_y), eye_radius)
            pygame.draw.circle(head_layer, (255, 255, 255, 255), (local_head_center[0] + eye_dx, eye_y), eye_radius)
            pygame.draw.circle(head_layer, patch, (local_head_center[0] - eye_dx, eye_y), max(1, eye_radius // 2))
            pygame.draw.circle(head_layer, patch, (local_head_center[0] + eye_dx, eye_y), max(1, eye_radius // 2))
            pygame.draw.ellipse(head_layer, patch, pygame.Rect(local_head_center[0] - int(sprite_w * 0.15), local_head_center[1] - int(sprite_w * 0.21), int(sprite_w * 0.13), int(sprite_w * 0.05)))
            pygame.draw.ellipse(head_layer, patch, pygame.Rect(local_head_center[0] + int(sprite_w * 0.02), local_head_center[1] - int(sprite_w * 0.21), int(sprite_w * 0.13), int(sprite_w * 0.05)))
            if mouth_open:
                pygame.draw.ellipse(
                    head_layer,
                    mouth,
                    pygame.Rect(
                        local_head_center[0] - int(sprite_w * 0.045),
                        local_head_center[1] + int(sprite_w * 0.07),
                        int(sprite_w * 0.09),
                        int(sprite_w * 0.07),
                    ),
                )
            else:
                pygame.draw.arc(
                    head_layer,
                    mouth,
                    pygame.Rect(local_head_center[0] - int(sprite_w * 0.07), local_head_center[1] + int(sprite_w * 0.07), int(sprite_w * 0.14), int(sprite_w * 0.08)),
                    math.radians(20),
                    math.radians(160),
                    max(2, eye_radius // 2),
                )
            pygame.draw.circle(head_layer, blush, (local_head_center[0] - int(sprite_w * 0.13), local_head_center[1] + int(sprite_w * 0.09)), eye_radius + 2)
            pygame.draw.circle(head_layer, blush, (local_head_center[0] + int(sprite_w * 0.13), local_head_center[1] + int(sprite_w * 0.09)), eye_radius + 2)

        if abs(head_rotation) >= 0.01:
            head_layer = pygame.transform.rotate(head_layer, head_rotation)
        sprite.blit(head_layer, (int(head_center[0] - head_layer.get_width() / 2), int(head_center[1] - head_layer.get_height() / 2)))

        arm_width = max(6, sprite_w // 16)
        forearm_width = max(5, sprite_w // 18)
        joint_radius = max(4, sprite_w // 22)
        hand_radius = max(4, sprite_w // 22)
        self._draw_segmented_limb(sprite, back_shoulder, back_elbow, back_hand, bone, arm_width, forearm_width, joint_radius, hand_radius, accent)
        self._draw_segmented_limb(sprite, front_shoulder, front_elbow, front_hand, bone, arm_width, forearm_width, joint_radius, hand_radius, accent)

        total_rotation = float(state.get("rotation", 0.0) or 0.0) + float(state.get("body_lean", 0.0) or 0.0)
        if total_rotation:
            sprite = pygame.transform.rotate(sprite, total_rotation)
        if state["facing"] == "left":
            sprite = pygame.transform.flip(sprite, True, False)

        draw_x = int(center_x - sprite.get_width() / 2 + float(state.get("draw_dx", 0.0) or 0.0))
        draw_y = int(center_y - sprite.get_height() + state["bob"] - state["jump"] + float(state.get("draw_dy", 0.0) or 0.0))
        self.surface.blit(sprite, (draw_x, draw_y))

    def _draw_npc_groups(self, scene: dict[str, Any], time_ms: int, cx: float, cz: float, zoom: float) -> None:
        del scene, time_ms, cx, cz, zoom
        return

    def _effect_color(self, effect_id: str) -> tuple[int, int, int, int]:
        return self._rgba(self.effects.get(effect_id, {}).get("color") or [1.0, 0.4, 0.2, 0.9])

    @staticmethod
    def _clamp_ratio(value: float) -> float:
        return max(0.0, min(1.0, value))

    def _effect_alpha_value(self, alpha_ratio: float) -> int:
        clamped = self._clamp_ratio(alpha_ratio)
        if clamped <= 0.0:
            return 0
        return max(MIN_EFFECT_ALPHA, min(MAX_EFFECT_ALPHA, int(255 * clamped)))

    @staticmethod
    def _brighten_effect_surface(surface: pygame.Surface) -> pygame.Surface:
        if EFFECT_BRIGHTNESS_ADD <= 0:
            return surface
        surface.fill(
            (EFFECT_BRIGHTNESS_ADD, EFFECT_BRIGHTNESS_ADD, EFFECT_BRIGHTNESS_ADD, 0),
            special_flags=pygame.BLEND_RGB_ADD,
        )
        return surface

    def _effect_alpha(self, alpha_ratio: float) -> float:
        raw_alpha = (0.72 + 0.28 * self._clamp_ratio(alpha_ratio)) * self._clamp_ratio(self._effect_overlay_alpha)
        return self._effect_alpha_value(raw_alpha) / 255.0

    @staticmethod
    def _fade_in_out_alpha(progress: float, fade_ratio: float = 0.22) -> float:
        progress = max(0.0, min(1.0, progress))
        fade_ratio = max(0.05, min(0.45, fade_ratio))
        if progress < fade_ratio:
            return progress / fade_ratio
        if progress > 1.0 - fade_ratio:
            return (1.0 - progress) / fade_ratio
        return 1.0

    def _draw_effect_sprite(
        self,
        asset_path: Path | None,
        cache_prefix: str,
        progress: float,
        center_x: float,
        center_y: float,
        width: int,
        height: int,
        *,
        alpha_ratio: float = 1.0,
        flip_x: bool = False,
        playback_speed: float = 1.0,
    ) -> None:
        if asset_path is None:
            return
        asset_path_str = str(asset_path)
        frames = self._load_frames(asset_path_str)
        if not frames:
            return
        frame_index = self._frame_index_for_progress(
            asset_path_str,
            len(frames),
            progress,
            playback_speed=playback_speed,
        )
        frame = frames[frame_index]
        if frame is None:
            return
        overlay = self._scaled_surface(
            f"{cache_prefix}:{asset_path}:{frame_index}",
            frame,
            max(24, int(width)),
            max(24, int(height)),
            flip_x=flip_x,
        ).copy()
        overlay = self._brighten_effect_surface(overlay)
        overlay.set_alpha(self._effect_alpha_value(alpha_ratio))
        self.surface.blit(overlay, (int(center_x - overlay.get_width() / 2), int(center_y - overlay.get_height() / 2)))

    def _draw_fullscreen_effect(
        self,
        asset_path: Path | None,
        cache_prefix: str,
        progress: float,
        *,
        alpha_ratio: float,
        playback_speed: float = 0.5,
    ) -> None:
        self._draw_effect_sprite(
            asset_path,
            cache_prefix,
            progress,
            self.width / 2,
            self.height / 2,
            self.width,
            self.height,
            alpha_ratio=self._effect_alpha(alpha_ratio),
            flip_x=False,
            playback_speed=playback_speed,
        )

    @staticmethod
    def _effect_combo_motion(effect_id: str, progress: float) -> str:
        effect_id = str(effect_id or "")
        progress = max(0.0, min(1.0, progress))
        if effect_id == "dragon-palm":
            if progress < 0.12:
                return "point"
            if progress < 0.26:
                return "combo-punch"
            if progress < 0.54:
                return "double-palm-push"
            if progress < 0.82:
                return "flying-kick"
            return "talk"
        if effect_id == "thunder-strike":
            if progress < 0.10:
                return "point"
            if progress < 0.28:
                return "somersault"
            if progress < 0.54:
                return "spin-kick"
            if progress < 0.80:
                return "hook-punch"
            return "talk"
        if effect_id == "sword-arc":
            if progress < 0.11:
                return "point"
            if progress < 0.38:
                return "diagonal-kick"
            if progress < 0.70:
                return "swing-punch"
            return "talk"
        return effect_id

    @staticmethod
    def _effect_motion_progress(effect_id: str, progress: float) -> float:
        del effect_id
        progress = max(0.0, min(1.0, progress))
        # Speed up the visible strike animation while keeping actor travel timing intact.
        return max(0.0, min(1.0, progress * 2.15))

    def _effect_asset_for_type(self, effect_type: str, asset_path: str | None = None) -> Path | None:
        if asset_path:
            candidate = Path(asset_path)
            if candidate.exists():
                return candidate
        effect_meta = self.effects.get(str(effect_type or ""))
        if effect_meta and effect_meta.get("asset_path"):
            candidate = Path(str(effect_meta["asset_path"]))
            if candidate.exists():
                return candidate
        key = {
            "dragon-palm": "dragon",
            "thunder-strike": "vortex",
            "sword-arc": "galaxy",
            "launch": "launch",
            "hit": "hit",
            "explosion": "explosion",
        }.get(str(effect_type or ""))
        if key:
            return self.effect_assets.get(key)
        return None

    def _draw_foregrounds(self, scene: dict[str, Any], time_ms: int) -> None:
        backdrop_rect = self._layout_metrics()["backdrop_rect"]
        for index, item in enumerate(scene.get("foregrounds", []), start=1):
            if not isinstance(item, dict):
                continue
            asset_path = str(item.get("asset_path") or "").strip()
            if not asset_path:
                continue
            frame = self._pick_frame(
                self._load_frames(asset_path),
                time_ms,
                period_ms=int(item.get("motion_period_ms", 1400) or 1400),
                path_value=asset_path,
            )
            if frame is None:
                continue
            rect = pygame.Rect(
                int(backdrop_rect.left + backdrop_rect.width * float(item.get("x", 0.0) or 0.0)),
                int(backdrop_rect.top + backdrop_rect.height * float(item.get("y", 0.0) or 0.0)),
                max(8, int(backdrop_rect.width * float(item.get("width", 1.0) or 1.0))),
                max(8, int(backdrop_rect.height * float(item.get("height", 1.0) or 1.0))),
            )
            scaled = self._scaled_surface(f"foreground:{index}:{asset_path}", frame, rect.width, rect.height)
            self.surface.blit(scaled, rect.topleft)

    def _draw_attack_launch_effect(
        self,
        source: dict[str, Any],
        target: dict[str, Any],
        effect_id: str,
        cx: float,
        cz: float,
        zoom: float,
    ) -> None:
        del target, effect_id, cx, cz, zoom
        if self.attack_effect_asset is None:
            return
        progress = float(source.get("motion_progress", 0.0) or 0.0)
        if progress > 0.4:
            return
        normalized = progress / 0.4
        self._draw_fullscreen_effect(
            self.attack_effect_asset,
            "attack-launch-fullscreen",
            normalized,
            alpha_ratio=self._fade_in_out_alpha(normalized, 0.24),
            playback_speed=0.5,
        )

    def _draw_attack_travel_effect(
        self,
        source: dict[str, Any],
        target: dict[str, Any],
        effect_id: str,
        cx: float,
        cz: float,
        zoom: float,
    ) -> None:
        del target, cx, cz, zoom
        travel_key = {"dragon-palm": "dragon", "thunder-strike": "vortex", "sword-arc": "galaxy"}.get(effect_id)
        asset_path = self.effect_assets.get(travel_key or "")
        if asset_path is None:
            return
        progress = float(source.get("motion_progress", 0.0) or 0.0)
        if progress < 0.2 or progress > 0.82:
            return
        normalized = (progress - 0.2) / 0.62
        self._draw_fullscreen_effect(
            asset_path,
            f"attack-travel-fullscreen:{effect_id}",
            normalized,
            alpha_ratio=self._fade_in_out_alpha(normalized, 0.22),
            playback_speed=0.5,
        )

    def _draw_attack_impact_effect(
        self,
        source: dict[str, Any],
        target: dict[str, Any],
        effect_id: str,
        cx: float,
        cz: float,
        zoom: float,
    ) -> None:
        del target, cx, cz, zoom
        impact_key = "explosion" if effect_id == "thunder-strike" else "hit"
        asset_path = self.effect_assets.get(impact_key)
        if asset_path is None:
            return
        progress = float(source.get("motion_progress", 0.0) or 0.0)
        if progress < 0.58:
            return
        normalized = (progress - 0.58) / 0.42
        self._draw_fullscreen_effect(
            asset_path,
            f"attack-impact-fullscreen:{effect_id}",
            normalized,
            alpha_ratio=self._fade_in_out_alpha(normalized, 0.28),
            playback_speed=0.5,
        )

    def _draw_scene_effect_overlays(self, scene: dict[str, Any], time_ms: int) -> None:
        scene_duration_ms = max(1, int(scene.get("duration_ms", 0) or 1))
        for index, effect in enumerate(scene.get("effects", []), start=1):
            if not isinstance(effect, dict):
                continue
            start_ms = max(0, int(effect.get("start_ms", 0) or 0))
            end_ms = max(start_ms + 1, int(effect.get("end_ms", scene_duration_ms) or scene_duration_ms))
            if not (start_ms <= time_ms <= end_ms):
                continue
            asset_path = self._effect_asset_for_type(str(effect.get("type") or ""), effect.get("asset_path"))
            if asset_path is None:
                continue
            progress = (time_ms - start_ms) / max(1, end_ms - start_ms)
            alpha_ratio = self._fade_in_out_alpha(progress, 0.24) * self._clamp_ratio(effect.get("alpha", 1.0))
            playback_speed = max(0.05, float(effect.get("playback_speed", 1.0) or 1.0)) * 0.5
            effect_key = str(effect.get("type") or asset_path)
            self._draw_fullscreen_effect(
                asset_path,
                f"scene-effect:{index}:{effect_key}",
                progress,
                alpha_ratio=alpha_ratio,
                playback_speed=playback_speed,
            )

    def _draw_effects(self, scene: dict[str, Any], time_ms: int, cx: float, cz: float, zoom: float) -> None:
        self._draw_scene_effect_overlays(scene, time_ms)
        actors = {str(actor.get("actor_id") or ""): self._actor_state(actor, scene, time_ms) for actor in scene.get("actors", [])}
        actor_list = list(scene.get("actors", []))
        for actor in actor_list:
            actor_id = str(actor.get("actor_id") or "")
            beat = actors.get(actor_id, {}).get("beat")
            if not beat:
                continue
            effect_id = str(beat.get("effect") or beat.get("motion") or "")
            if effect_id not in {"dragon-palm", "thunder-strike", "sword-arc"}:
                continue
            source = actors[actor_id]
            targets = [state for other_id, state in actors.items() if other_id != actor_id]
            target = targets[0] if targets else source
            self._draw_attack_launch_effect(source, target, effect_id, cx, cz, zoom)
            self._draw_attack_travel_effect(source, target, effect_id, cx, cz, zoom)
            self._draw_attack_impact_effect(source, target, effect_id, cx, cz, zoom)

    def _draw_subtitle(self, scene: dict[str, Any], time_ms: int) -> None:
        dialogue = self._active_dialogue(scene, time_ms)
        if not dialogue:
            return
        text = str(dialogue.get("subtitle") or dialogue.get("text") or "").strip()
        if not text:
            return
        font = self._font(max(22, self.width // 28))
        text_surface = font.render(text, True, (255, 255, 255))
        max_width = int(self.width * 0.86)
        if text_surface.get_width() > max_width:
            scale = max_width / max(1, text_surface.get_width())
            text_surface = pygame.transform.smoothscale(text_surface, (int(text_surface.get_width() * scale), int(text_surface.get_height() * scale)))
        pad_x = 18
        pad_y = 12
        box = pygame.Surface((text_surface.get_width() + pad_x * 2, text_surface.get_height() + pad_y * 2), pygame.SRCALPHA)
        pygame.draw.rect(box, (0, 0, 0, 176), box.get_rect(), border_radius=16)
        box.blit(text_surface, (pad_x, pad_y))
        x = (self.width - box.get_width()) // 2
        y = self.height - box.get_height() - 22
        self.surface.blit(box, (x, y))

    def _layered_props(self, scene: dict[str, Any]) -> list[dict[str, Any]]:
        def has_visual(prop: dict[str, Any]) -> bool:
            asset = self.props.get(str(prop.get("prop_id") or ""), {})
            return bool(asset.get("asset_path"))

        def sort_key(prop: dict[str, Any]) -> tuple[int, float]:
            layer = str(prop.get("layer") or self.props.get(str(prop.get("prop_id") or ""), {}).get("default_layer") or "front")
            layer_order = {"back": 0, "mid": 1, "front": 2}.get(layer, 1)
            return layer_order, float(prop.get("z", 0.0) or 0.0)

        return sorted([prop for prop in scene.get("props", []) if has_visual(prop)], key=sort_key)

    def _draw_scene(self, scene: dict[str, Any], time_ms: int) -> None:
        cx, cz, zoom = self._camera(scene, time_ms)
        layout = self._layout_metrics()
        backdrop_rect = layout["backdrop_rect"]
        self.surface.blit(self._background_surface(scene, time_ms, backdrop_rect), backdrop_rect.topleft)
        has_wall_layer = self._wall_layer(scene) is not None
        if not has_wall_layer:
            self._draw_room_box(scene)
        self._draw_floor(scene, cx, cz, zoom)

        props = self._layered_props(scene)
        if has_wall_layer:
            back_prop_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA, 32)
            back_prop_surface.set_clip(backdrop_rect)
        for prop in props:
            asset = self.props.get(str(prop.get("prop_id") or ""), {})
            mount = str(prop.get("mount") or asset.get("default_mount") or "free")
            render_style = str(asset.get("render_style") or "")
            if mount in {"outside-back", "between-backgrounds"} or render_style in {"window", "door", "double-door"}:
                continue
            if mount in {"back-wall", "left-wall", "right-wall"} or str(prop.get("layer") or "front") == "back":
                target = back_prop_surface if has_wall_layer else self.surface
                self._draw_prop(prop, time_ms, cx, cz, zoom, target=target)
        if has_wall_layer:
            back_prop_surface.set_clip(None)
            opening_mask = self._wall_opening_mask(scene)
            if opening_mask is not None:
                back_prop_surface.blit(opening_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            self.surface.blit(back_prop_surface, (0, 0))

        if has_wall_layer:
            # A wall-layer asset is treated as the scene-covering set piece:
            # it sits above the procedural floor/backdrop but below actors.
            self._draw_wall_layer(scene)

        # Foreground set dressing should use only its intrinsic alpha and sit behind actors;
        # otherwise fullscreen overlays make characters look unnaturally transparent.
        self._draw_foregrounds(scene, time_ms)
        self._draw_npc_groups(scene, time_ms, cx, cz, zoom)

        actor_states = [self._actor_state(actor, scene, time_ms) for actor in scene.get("actors", [])]
        actor_lookup = {state["actor_id"]: state for state in actor_states}

        def actor_sort_key(item: dict[str, Any]) -> tuple[float, float]:
            state = actor_lookup[str(item.get("actor_id") or "")]
            _, foot_y = self._stage_point(float(state["x"]), float(state["z"]), cx, cz, zoom)
            layer_bias = {"back": -10.0, "mid": 0.0, "front": 10.0}.get(str(state.get("layer") or "front"), 0.0)
            # Draw farther actors first based on actual floor position; layer only nudges ties.
            return foot_y + layer_bias, float(state["x"])

        for actor in sorted(scene.get("actors", []), key=actor_sort_key):
            self._draw_actor(scene, actor, time_ms, cx, cz, zoom)

        for prop in props:
            asset = self.props.get(str(prop.get("prop_id") or ""), {})
            mount = str(prop.get("mount") or asset.get("default_mount") or "free")
            render_style = str(asset.get("render_style") or "")
            if mount in {"outside-back", "between-backgrounds"} or render_style in {"window", "door", "double-door"}:
                continue
            if mount not in {"back-wall", "left-wall", "right-wall"} and str(prop.get("layer") or "front") != "back":
                self._draw_prop(prop, time_ms, cx, cz, zoom)

        self._draw_effects(scene, time_ms, cx, cz, zoom)
        self._draw_subtitle(scene, time_ms)

    def capture_scene_frame(self, scene: dict[str, Any], time_ms: int, *, raw_rgb: bool = False) -> bytes:
        self.surface.fill((0, 0, 0, 0))
        self._draw_scene(scene, time_ms)
        if raw_rgb:
            return pygame.image.tostring(self.surface, "RGB")
        rgba = pygame.image.tostring(self.surface, "RGBA")
        image = Image.frombytes("RGBA", (self.width, self.height), rgba)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    def close(self) -> None:
        self._scaled_cache.clear()
        self._background_cache.clear()
