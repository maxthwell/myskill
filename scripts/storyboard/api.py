from __future__ import annotations

from copy import deepcopy
from typing import Any


def cast_member(actor_id: str, display_name: str, asset_id: str, *, voice: str | None = None, **extra: Any) -> dict[str, Any]:
    item = {
        "id": actor_id,
        "display_name": display_name,
        "asset_id": asset_id,
    }
    if voice:
        item["voice"] = voice
    item.update(extra)
    return item


def actor(
    actor_id: str,
    x: float,
    z: float = 0.0,
    *,
    facing: str,
    scale: float = 1.0,
    layer: str = "front",
) -> dict[str, Any]:
    return {
        "actor_id": actor_id,
        "spawn": {"x": x, "z": z},
        "scale": scale,
        "layer": layer,
        "facing": facing,
    }


def prop(
    prop_id: str,
    x: float,
    z: float,
    *,
    scale: float = 1.0,
    layer: str = "front",
    mount: str | None = None,
    category: str | None = None,
    image_url: str | None = None,
) -> dict[str, Any]:
    item = {
        "prop_id": prop_id,
        "x": x,
        "z": z,
        "scale": scale,
        "layer": layer,
    }
    if mount is not None:
        item["mount"] = mount
    if category is not None:
        item["category"] = category
    if image_url is not None:
        item["image_url"] = image_url
    return item


def npc_group(
    group_id: str,
    *,
    count: int,
    asset_ids: list[str],
    behavior: str = "guard",
    layer: str = "back",
    watch: bool = True,
    anchor_x: float = 0.0,
    anchor_frontness: float = 0.0,
    area: dict[str, float] | None = None,
    scale_min: float = 0.72,
    scale_max: float = 0.88,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "id": group_id,
        "count": count,
        "asset_ids": list(asset_ids),
        "behavior": behavior,
        "layer": layer,
        "watch": watch,
        "anchor": {"x": anchor_x, "frontness": anchor_frontness},
        "area": area or {"x_min": -4.8, "x_max": 4.8, "front_min": -0.8, "front_max": 0.9},
        "scale_min": scale_min,
        "scale_max": scale_max,
        **extra,
    }


def dialogue(start_ms: int, end_ms: int, speaker_id: str, text: str, *, voice: str | None = None, bubble: bool = False) -> dict[str, Any]:
    return {
        "start_ms": start_ms,
        "end_ms": end_ms,
        "speaker_id": speaker_id,
        "text": text,
        "subtitle": text,
        "voice": voice,
        "bubble": bubble,
    }


def expression(actor_id: str, start_ms: int, end_ms: int, expression_name: str) -> dict[str, Any]:
    return {
        "actor_id": actor_id,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "expression": expression_name,
    }


def beat(
    start_ms: int,
    end_ms: int,
    actor_id: str,
    motion: str,
    *,
    x0: float | None = None,
    x1: float | None = None,
    z0: float = 0.0,
    z1: float = 0.0,
    facing: str | None = None,
    effect: str | None = None,
    emotion: str = "charged",
) -> dict[str, Any]:
    item = {
        "start_ms": start_ms,
        "end_ms": end_ms,
        "actor_id": actor_id,
        "motion": motion,
        "from": None if x0 is None else {"x": x0, "z": z0},
        "to": None if x1 is None else {"x": x1, "z": z1},
        "facing": facing,
        "emotion": emotion,
    }
    if effect is not None:
        item["effect"] = effect
    return item


def effect(
    effect_type: str | None = None,
    *,
    start_ms: int = 0,
    end_ms: int | None = None,
    alpha: float = 1.0,
    playback_speed: float = 1.0,
    asset_path: str | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "start_ms": start_ms,
        "alpha": alpha,
        "playback_speed": playback_speed,
    }
    if end_ms is not None:
        item["end_ms"] = end_ms
    if effect_type is not None:
        item["type"] = effect_type
    if asset_path is not None:
        item["asset_path"] = asset_path
    return item


def foreground(
    foreground_id: str | None = None,
    *,
    x: float = 0.0,
    y: float = 0.0,
    width: float = 1.0,
    height: float = 1.0,
    opacity: float = 1.0,
    asset_path: str | None = None,
    motion_period_ms: int = 1400,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "opacity": opacity,
        "motion_period_ms": motion_period_ms,
    }
    if foreground_id is not None:
        item["foreground_id"] = foreground_id
    if asset_path is not None:
        item["asset_path"] = asset_path
    return item


def audio_bgm(path: str, *, start_ms: int = 0, end_ms: int | None = None, volume: float = 1.0, loop: bool = True) -> dict[str, Any]:
    item = {"path": path, "start_ms": start_ms, "volume": volume, "loop": loop}
    if end_ms is not None:
        item["end_ms"] = end_ms
    return item


def audio_sfx(path: str, *, start_ms: int = 0, end_ms: int | None = None, volume: float = 1.0, loop: bool = False) -> dict[str, Any]:
    item = {"path": path, "start_ms": start_ms, "volume": volume, "loop": loop}
    if end_ms is not None:
        item["end_ms"] = end_ms
    return item


def scene_audio(*, bgm: dict[str, Any] | None = None, sfx: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"bgm": deepcopy(bgm), "sfx": deepcopy(sfx or [])}


def camera_static(*, x: float = 0.0, z: float = 0.0, zoom: float = 1.0, ease: str = "linear") -> dict[str, Any]:
    return {
        "type": "static",
        "x": x,
        "z": z,
        "zoom": zoom,
        "to_x": x,
        "to_z": z,
        "to_zoom": zoom,
        "ease": ease,
    }


def camera_pan(
    *,
    x: float,
    z: float,
    zoom: float,
    to_x: float,
    to_z: float,
    to_zoom: float,
    ease: str = "inout",
) -> dict[str, Any]:
    return {
        "type": "pan",
        "x": x,
        "z": z,
        "zoom": zoom,
        "to_x": to_x,
        "to_z": to_z,
        "to_zoom": to_zoom,
        "ease": ease,
    }


def scene(
    scene_id: str,
    *,
    background: str,
    floor: str | None,
    duration_ms: int,
    summary: str,
    camera: dict[str, Any] | None = None,
    effects: list[dict[str, Any]] | None = None,
    props: list[dict[str, Any]] | None = None,
    actors: list[dict[str, Any]] | None = None,
    npc_groups: list[dict[str, Any]] | None = None,
    beats: list[dict[str, Any]] | None = None,
    expressions: list[dict[str, Any]] | None = None,
    dialogues: list[dict[str, Any]] | None = None,
    audio: dict[str, Any] | None = None,
    box: dict[str, Any] | None = None,
    wall_layer: dict[str, Any] | None = None,
    foregrounds: list[dict[str, Any]] | None = None,
    notes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    item = {
        "id": scene_id,
        "background": background,
        "floor": floor,
        "duration_ms": duration_ms,
        "summary": summary,
        "camera": deepcopy(camera) if camera is not None else camera_static(),
        "effects": deepcopy(effects or []),
        "props": deepcopy(props or []),
        "actors": deepcopy(actors or []),
        "npc_groups": deepcopy(npc_groups or []),
        "beats": deepcopy(beats or []),
        "expressions": deepcopy(expressions or []),
        "dialogues": deepcopy(dialogues or []),
        "audio": deepcopy(audio or scene_audio()),
        "foregrounds": deepcopy(foregrounds or []),
    }
    if box is not None:
        item["box"] = deepcopy(box)
    if wall_layer is not None:
        item["wall_layer"] = deepcopy(wall_layer)
    if notes is not None:
        item["notes"] = deepcopy(notes)
    return item


def _infer_scene_assets(scenes: list[dict[str, Any]]) -> dict[str, list[str]]:
    backgrounds: set[str] = set()
    floors: set[str] = set()
    props: set[str] = set()
    motions: set[str] = set()
    effects: set[str] = set()
    foregrounds: set[str] = set()
    for item in scenes:
        background = item.get("background")
        floor = item.get("floor")
        if background:
            backgrounds.add(str(background))
        if floor:
            floors.add(str(floor))
        for prop_item in item.get("props", []):
            prop_id = prop_item.get("prop_id")
            if prop_id:
                props.add(str(prop_id))
        for beat_item in item.get("beats", []):
            motion = beat_item.get("motion")
            if motion:
                motions.add(str(motion))
            effect_id = beat_item.get("effect")
            if effect_id:
                effects.add(str(effect_id))
        for effect_item in item.get("effects", []):
            effect_id = effect_item.get("type")
            if effect_id:
                effects.add(str(effect_id))
        for foreground_item in item.get("foregrounds", []):
            foreground_id = foreground_item.get("foreground_id") or foreground_item.get("id")
            if foreground_id:
                foregrounds.add(str(foreground_id))
    return {
        "backgrounds": sorted(backgrounds),
        "floors": sorted(floors),
        "props": sorted(props),
        "motions": sorted(motions),
        "effects": sorted(effects),
        "foregrounds": sorted(foregrounds),
    }


def story_package(
    *,
    title: str,
    cast: list[dict[str, Any]],
    scenes: list[dict[str, Any]],
    theme: str = "",
    video: dict[str, Any] | None = None,
    assets: dict[str, list[str]] | None = None,
    language: str = "zh-CN",
    source_prompt: str | None = None,
    notes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    package = {
        "meta": {
            "title": title,
            "language": language,
            "theme": theme,
            "source_prompt": source_prompt,
        },
        "video": deepcopy(video or {}),
        "cast": deepcopy(cast),
        "assets": deepcopy(assets or _infer_scene_assets(scenes)),
        "scenes": deepcopy(scenes),
    }
    if notes is not None:
        package["notes"] = deepcopy(notes)
    return package
