from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .io import WORK_DIR, load_manifest, manifest_index, read_json, resolve_audio_asset, resolve_bgm_asset, resolve_effect_asset, resolve_foreground_asset, write_json
from .story_script import load_story_source


DEFAULT_VIDEO = {
    "width": 854,
    "height": 480,
    "fps": 12,
    "renderer": "pygame_2d",
    "subtitle_mode": "bottom",
    "tts_enabled": False,
    "video_codec": "libx264",
    "encoder_preset": "ultrafast",
    "crf": 26,
    "audio_bitrate": "64k",
    "actor_front_bias": 1.0,
    "actor_scale_base": 0.667,
    "frame_center_z": 0.78,
    "stage_layout": {
        "background_width": 14.0,
        "background_height": 7.2,
        "background_y": 8.0,
        "background_z": 0.98,
        "ground_width": 17.6,
        "ground_height": 12.6,
        "ground_y": 7.0,
        "ground_z": -1.2,
        "ground_pitch": -78.0,
        "ground_slope": 0.22,
    },
}

DEFAULT_CAMERA = {
    "type": "static",
    "x": 0.0,
    "z": 0.0,
    "zoom": 1.0,
    "to_x": 0.0,
    "to_z": 0.0,
    "to_zoom": 1.0,
    "ease": "linear",
}
DEFAULT_AUDIO = {"bgm": None, "sfx": []}
DEFAULT_NPC_AREA = {
    "x_min": -4.8,
    "x_max": 4.8,
    "front_min": -0.8,
    "front_max": 0.9,
}
NPC_BEHAVIORS = {
    "wander",
    "seek",
    "pursue",
    "evade",
    "guard",
}
MIN_DIALOGUE_DURATION_MS = 1100
DIALOGUE_GAP_MS = 160
SCENE_TAIL_MS = 500
ACTION_WINDOWS = [
    (3320, 4520),
    (4960, 6160),
    (6600, 7800),
    (8240, 9440),
    (9880, 11080),
    (11520, 12720),
]
ACTOR_LAYOUTS = {
    1: [0.0],
    2: [-2.2, 2.2],
    3: [-3.2, 0.0, 3.2],
    4: [-4.0, -1.3, 1.3, 4.0],
}
POSITION_ALIASES = {
    "left": -3.2,
    "center-left": -1.3,
    "center": 0.0,
    "center-right": 1.3,
    "right": 3.2,
}
BACKGROUND_ALIASES = {
    "temple": "temple-courtyard",
    "courtyard": "temple-courtyard",
    "cliff": "mountain-cliff",
    "mountain": "mountain-cliff",
    "inn": "inn-hall",
    "bridge": "night-bridge",
    "night": "night-bridge",
    "training": "training-ground",
}
PROP_ALIASES = {
    "drum": "training-drum",
    "lantern": "lantern",
    "rack": "weapon-rack",
}
MOTION_ALIASES = {
    "speak": "talk",
    "saying": "talk",
    "gesture": "point",
    "dragon palm": "dragon-palm",
    "dragon-palm": "dragon-palm",
    "降龙十八掌": "dragon-palm",
    "thunder": "thunder-strike",
    "雷击": "thunder-strike",
    "sword": "sword-arc",
    "剑气": "sword-arc",
    "flying kick": "flying-kick",
    "飞踢": "flying-kick",
    "double palm push": "double-palm-push",
    "double-palm-push": "double-palm-push",
    "双掌平推": "double-palm-push",
    "spin kick": "spin-kick",
    "spin-kick": "spin-kick",
    "侧旋踢": "spin-kick",
    "diagonal kick": "diagonal-kick",
    "diagonal-kick": "diagonal-kick",
    "平行斜踢": "diagonal-kick",
    "斜踢": "diagonal-kick",
    "hook punch": "hook-punch",
    "hook-punch": "hook-punch",
    "勾拳": "hook-punch",
    "swing punch": "swing-punch",
    "swing-punch": "swing-punch",
    "摆拳": "swing-punch",
    "straight punch": "straight-punch",
    "straight-punch": "straight-punch",
    "直拳": "straight-punch",
    "combo punch": "combo-punch",
    "combo-punch": "combo-punch",
    "组合拳": "combo-punch",
    "somersault": "somersault",
    "翻跟头": "somersault",
}
EFFECT_KEYWORDS = {
    "降龙十八掌": "dragon-palm",
    "dragon palm": "dragon-palm",
    "雷击": "thunder-strike",
    "thunder": "thunder-strike",
    "剑气": "sword-arc",
    "sword arc": "sword-arc",
}
DEFAULT_BACKGROUND_ID = "inn-hall"
DEFAULT_FLOOR_ID = "wood-plank"
EXPRESSION_ALIASES = {
    "neutral": "neutral",
    "default": "neutral",
    "talk": "neutral",
    "speaking": "neutral",
    "speak": "neutral",
    "smile": "smile",
    "smirk": "smile",
    "grin": "smile",
    "angry": "angry",
    "fierce": "angry",
    "furious": "angry",
    "thinking": "thinking",
    "explain": "thinking",
    "skeptical": "skeptical",
    "deadpan": "skeptical",
    "blank": "skeptical",
    "excited": "excited",
    "awkward": "excited",
    "nervous": "excited",
    "embarrassed": "excited",
    "hurt": "sad",
    "pain": "sad",
    "sad": "sad",
}


def is_canonical_story_package(payload: dict[str, Any]) -> bool:
    return {"meta", "video", "cast", "assets", "scenes"}.issubset(payload.keys())


def estimate_dialogue_duration_ms(text: str) -> int:
    compact = "".join((text or "").split())
    return max(MIN_DIALOGUE_DURATION_MS, min(5000, 800 + len(compact) * 120))


def _normalize_token(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").replace("-", " ").split())


def _resolve_id(requested: Any, index: dict[str, dict[str, Any]], aliases: dict[str, str], fallback: str) -> str:
    raw = str(requested or "").strip()
    if not raw:
        return fallback
    if raw in index:
        return raw
    normalized = _normalize_token(raw)
    hyphenated = normalized.replace(" ", "-")
    if hyphenated in index:
        return hyphenated
    aliased = aliases.get(normalized)
    if aliased in index:
        return aliased
    for token, target in aliases.items():
        if token in normalized and target in index:
            return target
    return fallback


def _pick_effect_from_text(*values: Any) -> str | None:
    corpus = " ".join(_normalize_token(value) for value in values if value).strip()
    for token, effect_id in EFFECT_KEYWORDS.items():
        if _normalize_token(token) in corpus:
            return effect_id
    return None


def _line_to_dialogue(raw: Any) -> dict[str, Any]:
    if isinstance(raw, list) and len(raw) >= 2:
        return {"speaker_id": raw[0], "text": raw[1]}
    if isinstance(raw, dict):
        speaker_id = raw.get("speaker_id") or raw.get("speaker") or raw.get("actor_id")
        text = raw.get("text") or raw.get("subtitle") or ""
        return {
            "speaker_id": speaker_id,
            "text": text,
            "effect": raw.get("effect"),
        }
    raise ValueError(f"Unsupported dialogue line: {raw!r}")


def _scene_actor_ids(scene: dict[str, Any]) -> list[str]:
    actor_values = scene.get("actors") or scene.get("actor_ids") or []
    actor_ids: list[str] = []
    for item in actor_values:
        if isinstance(item, str):
            actor_ids.append(item)
        elif isinstance(item, dict) and item.get("actor_id"):
            actor_ids.append(str(item["actor_id"]))
    return actor_ids


def _actor_layout(actor_ids: list[str]) -> list[dict[str, Any]]:
    if len(actor_ids) == 0:
        return []
    if len(actor_ids) > 4:
        raise ValueError("v1 supports at most 4 active actors per scene")
    xs = ACTOR_LAYOUTS[len(actor_ids)]
    actors: list[dict[str, Any]] = []
    for actor_id, x in zip(actor_ids, xs):
        actors.append(
            {
                "actor_id": actor_id,
                "spawn": {"x": x, "z": 0.0},
                "scale": 1.0,
                "layer": "front",
                "facing": "right" if x < 0 else "left",
            }
        )
    return actors


def _normalize_props(scene_props: list[Any] | None, prop_index: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    props: list[dict[str, Any]] = []
    items = scene_props or []
    default_xs = [-3.6, -1.1, 1.1, 3.6]
    for idx, item in enumerate(items):
        if isinstance(item, str):
            prop_id = _resolve_id(item, prop_index, PROP_ALIASES, next(iter(prop_index)))
            props.append(
                {
                    "prop_id": prop_id,
                    "x": default_xs[idx % len(default_xs)],
                    "z": -1.4 if idx % 2 == 0 else -0.9,
                    "scale": 1.0,
                    "layer": "back" if idx % 2 == 0 else "front",
                    "mount": prop_index.get(prop_id, {}).get("default_mount", "free"),
                    "category": prop_index.get(prop_id, {}).get("category"),
                }
            )
        elif isinstance(item, dict):
            prop_id = _resolve_id(item.get("prop_id") or item.get("id"), prop_index, PROP_ALIASES, next(iter(prop_index)))
            props.append(
                {
                    "prop_id": prop_id,
                    "x": float(item.get("x", default_xs[idx % len(default_xs)])),
                    "z": float(item.get("z", -1.0)),
                    "scale": float(item.get("scale", 1.0)),
                    "layer": item.get("layer", "front"),
                    "mount": item.get("mount", prop_index.get(prop_id, {}).get("default_mount", "free")),
                    "category": item.get("category", prop_index.get(prop_id, {}).get("category")),
                    "image_url": item.get("image_url"),
                }
            )
    return props


def _canonical_effects(raw_effects: list[Any] | None, effect_index: dict[str, dict[str, Any]], summary: str) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in raw_effects or []:
        if isinstance(item, str):
            effect_id = _resolve_id(item, effect_index, MOTION_ALIASES, item)
            if effect_id in effect_index:
                normalized.append({"type": effect_id})
        elif isinstance(item, dict) and item.get("type") in effect_index:
            normalized.append({"type": str(item["type"])})
    inferred = _pick_effect_from_text(summary)
    if inferred and not any(effect["type"] == inferred for effect in normalized):
        normalized.append({"type": inferred})
    return normalized


def _normalize_scene_effects(
    raw_effects: list[Any] | None,
    effect_index: dict[str, dict[str, Any]],
    summary: str,
    scene_duration_hint: int,
) -> list[dict[str, Any]]:
    del summary
    normalized: list[dict[str, Any]] = []
    default_end_ms = max(1, int(scene_duration_hint or 1))
    for item in raw_effects or []:
        if isinstance(item, str):
            effect_type = _resolve_id(item, effect_index, MOTION_ALIASES, item)
            if effect_type not in effect_index:
                continue
            normalized.append(
                {
                    "type": effect_type,
                    "start_ms": 0,
                    "end_ms": default_end_ms,
                    "alpha": 1.0,
                    "playback_speed": 1.0,
                }
            )
            continue
        if not isinstance(item, dict):
            continue
        requested_type = item.get("type") or item.get("effect") or item.get("effect_id")
        effect_type = None
        if requested_type:
            resolved = _resolve_id(requested_type, effect_index, MOTION_ALIASES, str(requested_type))
            if resolved in effect_index:
                effect_type = resolved
        asset_path = resolve_effect_asset(
            item.get("asset_path") or item.get("image_path") or item.get("path") or item.get("image_url")
        )
        if effect_type is None and asset_path is None:
            continue
        start_ms = max(0, int(item.get("start_ms", 0) or 0))
        end_ms = int(item.get("end_ms", default_end_ms) or default_end_ms)
        normalized_effect: dict[str, Any] = {
            "start_ms": start_ms,
            "end_ms": max(start_ms + 1, end_ms),
            "alpha": max(0.0, min(1.0, float(item.get("alpha", item.get("opacity", 1.0)) or 1.0))),
            "playback_speed": max(0.05, float(item.get("playback_speed", item.get("speed", 1.0)) or 1.0)),
        }
        if effect_type is not None:
            normalized_effect["type"] = effect_type
        if asset_path is not None:
            normalized_effect["asset_path"] = str(asset_path)
        replaced = False
        for index, existing in enumerate(normalized):
            if (
                effect_type
                and existing.get("type") == effect_type
                and int(existing.get("start_ms", 0) or 0) == 0
                and int(existing.get("end_ms", 0) or 0) == default_end_ms
            ):
                normalized[index] = {**existing, **normalized_effect}
                replaced = True
                break
        if not replaced:
            normalized.append(normalized_effect)
    return normalized


def _normalize_audio_cue(raw_audio: Any, scene_duration_hint: int, *, default_loop: bool) -> dict[str, Any] | None:
    if isinstance(raw_audio, str):
        raw_audio = {"path": raw_audio}
    if not isinstance(raw_audio, dict):
        return None
    asset_path = resolve_audio_asset(
        raw_audio.get("asset_path")
        or raw_audio.get("audio_path")
        or raw_audio.get("path")
        or raw_audio.get("src")
        or raw_audio.get("file")
        or raw_audio.get("url")
    )
    if asset_path is None:
        asset_path = resolve_bgm_asset(
            raw_audio.get("asset_path")
            or raw_audio.get("audio_path")
            or raw_audio.get("path")
            or raw_audio.get("src")
            or raw_audio.get("file")
            or raw_audio.get("url")
        )
    if asset_path is None:
        return None
    start_ms = max(0, int(raw_audio.get("start_ms", 0) or 0))
    end_ms = raw_audio.get("end_ms")
    normalized = {
        "asset_path": str(asset_path),
        "start_ms": start_ms,
        "volume": max(0.0, min(3.0, float(raw_audio.get("volume", raw_audio.get("gain", 1.0)) or 1.0))),
        "loop": bool(raw_audio.get("loop", default_loop)),
    }
    if end_ms is not None:
        normalized["end_ms"] = max(start_ms + 1, int(end_ms))
    elif default_loop and scene_duration_hint > 0:
        normalized["end_ms"] = max(start_ms + 1, int(scene_duration_hint))
    return normalized


def _normalize_audio(raw_audio: Any, scene_duration_hint: int) -> dict[str, Any]:
    normalized = deepcopy(DEFAULT_AUDIO)
    if not isinstance(raw_audio, dict):
        return normalized
    bgm = _normalize_audio_cue(raw_audio.get("bgm"), scene_duration_hint, default_loop=True)
    if bgm is not None:
        normalized["bgm"] = bgm
    sfx_items = raw_audio.get("sfx") or []
    if isinstance(sfx_items, (str, dict)):
        sfx_items = [sfx_items]
    normalized["sfx"] = [
        cue
        for cue in (_normalize_audio_cue(item, scene_duration_hint, default_loop=False) for item in sfx_items)
        if cue is not None
    ]
    return normalized


def _normalize_dialogues(scene: dict[str, Any], scene_duration_hint: int, effect_index: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    dialogues: list[dict[str, Any]] = []
    beats: list[dict[str, Any]] = []
    cursor = 500
    raw_lines = scene.get("dialogues") or scene.get("lines") or []
    for raw_line in raw_lines:
        parsed = _line_to_dialogue(raw_line)
        text = str(parsed.get("text") or "").strip()
        start_ms = int(parsed.get("start_ms", cursor))
        end_ms = int(parsed.get("end_ms", start_ms + estimate_dialogue_duration_ms(text)))
        effect_id = parsed.get("effect") or _pick_effect_from_text(text, scene.get("summary"))
        dialogue = {
            "start_ms": start_ms,
            "end_ms": end_ms,
            "speaker_id": str(parsed["speaker_id"]),
            "text": text,
            "subtitle": text,
            "voice": parsed.get("voice"),
            "bubble": False,
        }
        dialogues.append(dialogue)
        beat = {
            "start_ms": start_ms,
            "end_ms": end_ms,
            "actor_id": dialogue["speaker_id"],
            "motion": "talk",
            "from": None,
            "to": None,
            "facing": None,
            "emotion": "focused",
        }
        if effect_id and effect_id in effect_index:
            beat["motion"] = effect_id
            beat["effect"] = effect_id
            beat["emotion"] = "charged"
        beats.append(beat)
        cursor = end_ms + DIALOGUE_GAP_MS
    duration_ms = max(scene_duration_hint, cursor + SCENE_TAIL_MS)
    return dialogues, beats, duration_ms


def _trim_beats_for_actions(talk_beats: list[dict[str, Any]], action_beats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    trimmed: list[dict[str, Any]] = []
    for talk in talk_beats:
        segments = [(int(talk.get("start_ms", 0) or 0), int(talk.get("end_ms", 0) or 0))]
        for action in action_beats:
            if action.get("actor_id") != talk.get("actor_id"):
                continue
            action_start = int(action.get("start_ms", 0) or 0)
            action_end = int(action.get("end_ms", 0) or 0)
            next_segments: list[tuple[int, int]] = []
            for seg_start, seg_end in segments:
                if action_end <= seg_start or action_start >= seg_end:
                    next_segments.append((seg_start, seg_end))
                    continue
                if action_start > seg_start:
                    next_segments.append((seg_start, action_start))
                if action_end < seg_end:
                    next_segments.append((action_end, seg_end))
            segments = next_segments
            if not segments:
                break
        for seg_start, seg_end in segments:
            if seg_end - seg_start < 220:
                continue
            trimmed.append({**talk, "start_ms": seg_start, "end_ms": seg_end})
    return trimmed


def _normalize_action_beats(
    raw_scene: dict[str, Any],
    motion_index: dict[str, dict[str, Any]],
    effect_index: dict[str, dict[str, Any]],
    scene_duration_hint: int,
) -> list[dict[str, Any]]:
    raw_items = raw_scene.get("actions")
    if raw_items is None:
        raw_items = raw_scene.get("beats")
    if raw_items is None:
        return []
    if isinstance(raw_items, (str, dict)):
        raw_items = [raw_items]
    if not isinstance(raw_items, list):
        return []

    actor_ids = _scene_actor_ids(raw_scene)
    default_actor_id = actor_ids[0] if actor_ids else None
    default_end_ms = max(1, int(scene_duration_hint or 1))
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(raw_items):
        if isinstance(item, str):
            item = {"motion": item}
        elif isinstance(item, (list, tuple)):
            if len(item) == 2:
                item = {"actor_id": item[0], "motion": item[1]}
            elif len(item) >= 3:
                item = {"actor_id": item[0], "motion": item[1], "effect": item[2]}
            else:
                continue
        if not isinstance(item, dict):
            continue

        actor_id = str(item.get("actor_id") or item.get("speaker_id") or default_actor_id or "").strip()
        if not actor_id:
            continue
        requested_motion = item.get("motion") or item.get("action") or item.get("type")
        motion_id = _resolve_id(requested_motion, motion_index, MOTION_ALIASES, "")
        if motion_id not in motion_index:
            continue

        default_start_ms, default_end_ms_window = ACTION_WINDOWS[index % len(ACTION_WINDOWS)]
        start_ms = max(0, int(item.get("start_ms", default_start_ms) or default_start_ms))
        end_ms = int(item.get("end_ms", default_end_ms_window) or default_end_ms_window)
        end_ms = min(max(start_ms + 1, end_ms), default_end_ms)

        beat_item: dict[str, Any] = {
            "start_ms": start_ms,
            "end_ms": end_ms,
            "actor_id": actor_id,
            "motion": motion_id,
            "from": None,
            "to": None,
            "facing": item.get("facing"),
            "emotion": str(item.get("emotion") or "charged"),
        }

        if item.get("x0") is not None or item.get("from_x") is not None:
            beat_item["from"] = {
                "x": float(item.get("x0", item.get("from_x", 0.0)) or 0.0),
                "z": float(item.get("z0", item.get("from_z", 0.0)) or 0.0),
            }
        if item.get("x1") is not None or item.get("to_x") is not None:
            beat_item["to"] = {
                "x": float(item.get("x1", item.get("to_x", 0.0)) or 0.0),
                "z": float(item.get("z1", item.get("to_z", 0.0)) or 0.0),
            }

        requested_effect = item.get("effect") or _pick_effect_from_text(requested_motion, item.get("note"), item.get("label"))
        if requested_effect:
            effect_id = _resolve_id(requested_effect, effect_index, MOTION_ALIASES, "")
            if effect_id in effect_index:
                beat_item["effect"] = effect_id
        elif motion_id in effect_index:
            beat_item["effect"] = motion_id

        normalized.append(beat_item)
    return normalized


def _normalize_expression_name(value: Any) -> str:
    normalized = _normalize_token(value)
    return EXPRESSION_ALIASES.get(normalized, normalized.replace(" ", "-"))


def _normalize_expressions(raw_scene: dict[str, Any], scene_duration_hint: int) -> list[dict[str, Any]]:
    items = raw_scene.get("expressions") or raw_scene.get("expression_cues") or []
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        actor_id = item.get("actor_id") or item.get("speaker_id")
        expression = _normalize_expression_name(item.get("expression") or item.get("face"))
        if not actor_id or not expression:
            continue
        start_ms = int(item.get("start_ms", 0) or 0)
        end_ms = int(item.get("end_ms", scene_duration_hint or 0) or 0)
        normalized.append(
            {
                "actor_id": str(actor_id),
                "start_ms": start_ms,
                "end_ms": end_ms,
                "expression": expression,
            }
        )
    return normalized


def _normalize_camera(raw_camera: Any) -> dict[str, Any]:
    if not isinstance(raw_camera, dict):
        return deepcopy(DEFAULT_CAMERA)
    normalized = deepcopy(DEFAULT_CAMERA)
    camera_type = str(raw_camera.get("type") or "static")
    normalized["type"] = camera_type
    normalized["x"] = float(raw_camera.get("x", raw_camera.get("from_x", 0.0)) or 0.0)
    normalized["z"] = float(raw_camera.get("z", raw_camera.get("from_z", 0.0)) or 0.0)
    normalized["zoom"] = max(0.4, float(raw_camera.get("zoom", raw_camera.get("from_zoom", 1.0)) or 1.0))
    normalized["to_x"] = float(raw_camera.get("to_x", normalized["x"]) or normalized["x"])
    normalized["to_z"] = float(raw_camera.get("to_z", normalized["z"]) or normalized["z"])
    normalized["to_zoom"] = max(0.4, float(raw_camera.get("to_zoom", normalized["zoom"]) or normalized["zoom"]))
    normalized["ease"] = str(raw_camera.get("ease") or "linear")
    return normalized


def _normalize_npc_area(raw_area: Any) -> dict[str, float]:
    if not isinstance(raw_area, dict):
        return deepcopy(DEFAULT_NPC_AREA)
    normalized = deepcopy(DEFAULT_NPC_AREA)
    for key in ("x_min", "x_max", "front_min", "front_max"):
        value = raw_area.get(key)
        if value is not None:
            normalized[key] = float(value)
    if normalized["x_min"] > normalized["x_max"]:
        normalized["x_min"], normalized["x_max"] = normalized["x_max"], normalized["x_min"]
    if normalized["front_min"] > normalized["front_max"]:
        normalized["front_min"], normalized["front_max"] = normalized["front_max"], normalized["front_min"]
    return normalized


def _normalize_npc_groups(raw_scene: dict[str, Any], character_index: dict[str, dict[str, Any]], default_character: str) -> list[dict[str, Any]]:
    raw_groups = raw_scene.get("npc_groups") or []
    normalized_groups: list[dict[str, Any]] = []
    for index, item in enumerate(raw_groups):
        if not isinstance(item, dict):
            continue
        requested_asset_ids = item.get("asset_ids") or []
        if item.get("asset_id"):
            requested_asset_ids = [item.get("asset_id"), *requested_asset_ids]
        asset_ids = [
            _resolve_id(asset_id, character_index, {}, default_character)
            for asset_id in requested_asset_ids
            if asset_id
        ]
        if not asset_ids:
            asset_ids = [default_character]
        behavior = _normalize_token(item.get("behavior") or "wander").replace(" ", "-")
        if behavior == "follow":
            behavior = "seek"
        elif behavior == "chase":
            behavior = "pursue"
        elif behavior == "run-away":
            behavior = "evade"
        elif behavior == "watch":
            behavior = "guard"
        scale_value = item.get("scale")
        scale_min = float(item.get("scale_min", scale_value if scale_value is not None else 0.72) or 0.72)
        scale_max = float(item.get("scale_max", scale_value if scale_value is not None else 0.88) or 0.88)
        if scale_min > scale_max:
            scale_min, scale_max = scale_max, scale_min
        anchor = item.get("anchor") or {}
        normalized_groups.append(
            {
                "id": str(item.get("id") or f"npc-group-{index+1:02d}"),
                "count": max(1, min(24, int(item.get("count", 1) or 1))),
                "asset_ids": asset_ids,
                "behavior": behavior,
                "target_actor_id": str(item.get("target_actor_id") or item.get("focus_actor_id") or "").strip() or None,
                "layer": str(item.get("layer") or "mid"),
                "speed": max(0.4, float(item.get("speed", 1.0) or 1.0)),
                "arrival_distance": max(0.2, float(item.get("arrival_distance", 0.65) or 0.65)),
                "evade_distance": max(0.8, float(item.get("evade_distance", 1.8) or 1.8)),
                "relax_distance": max(1.0, float(item.get("relax_distance", 2.8) or 2.8)),
                "wander_radius": max(0.4, float(item.get("wander_radius", 0.9) or 0.9)),
                "wander_aoi": max(15.0, float(item.get("wander_aoi", 65.0) or 65.0)),
                "seek_weight": max(0.1, float(item.get("seek_weight", 1.0) or 1.0)),
                "area": _normalize_npc_area(item.get("area")),
                "anchor": {
                    "x": float(anchor.get("x", item.get("anchor_x", 0.0)) or 0.0),
                    "frontness": float(anchor.get("frontness", item.get("anchor_frontness", 0.0)) or 0.0),
                },
                "scale_min": scale_min,
                "scale_max": scale_max,
                "watch": bool(item.get("watch", True)),
            }
        )
    return normalized_groups


def _normalize_box(raw_scene: dict[str, Any]) -> dict[str, Any] | None:
    raw_box = raw_scene.get("box")
    if not isinstance(raw_box, dict):
        return None
    normalized: dict[str, Any] = {}
    for key in (
        "wall_image_url",
        "back_wall_image_url",
        "left_wall_image_url",
        "right_wall_image_url",
        "floor_image_url",
        "ceiling_image_url",
        "outside_image_url",
        "outside_back_image_url",
        "outside_left_image_url",
        "outside_right_image_url",
    ):
        value = raw_box.get(key)
        if value is not None:
            normalized[key] = str(value)
    for key in (
        "wall_color",
        "back_wall_color",
        "left_wall_color",
        "right_wall_color",
        "floor_color",
        "ceiling_color",
    ):
        value = raw_box.get(key)
        if isinstance(value, (list, tuple)):
            normalized[key] = list(value)
    for key in ("width", "height", "depth"):
        value = raw_box.get(key)
        if value is not None:
            normalized[key] = float(value)
    return normalized or None


def _normalize_wall_layer(raw_scene: dict[str, Any], background_index: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    raw = raw_scene.get("wall_layer")
    if not isinstance(raw, dict):
        return None
    normalized: dict[str, Any] = {}
    for key in ("x", "y", "width", "height"):
        value = raw.get(key)
        if value is not None:
            normalized[key] = float(value)
    for key in ("border_radius", "border_width"):
        value = raw.get(key)
        if value is not None:
            normalized[key] = int(value)
    for key in ("color", "trim_color"):
        value = raw.get(key)
        if isinstance(value, (list, tuple)):
            normalized[key] = list(value)
    for key in ("image_url", "asset_path", "image_path"):
        value = raw.get(key)
        if value is not None:
            normalized["asset_path" if key == "image_path" else key] = str(value)
    opacity = raw.get("opacity")
    if opacity is not None:
        normalized["opacity"] = max(0.0, min(1.0, float(opacity)))
    background_id = raw.get("background_id") or raw.get("texture_background")
    if background_id is not None:
        normalized["background_id"] = _resolve_id(background_id, background_index, BACKGROUND_ALIASES, next(iter(background_index)))
    return normalized or None


def _normalize_foregrounds(raw_scene: dict[str, Any], foreground_index: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    raw_items = raw_scene.get("foregrounds")
    if raw_items is None:
        raw_items = raw_scene.get("foreground_layers")
    if raw_items is None and raw_scene.get("foreground") is not None:
        raw_items = [raw_scene.get("foreground")]
    elif isinstance(raw_items, (str, dict)):
        raw_items = [raw_items]
    if not isinstance(raw_items, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in raw_items:
        if isinstance(item, str):
            item = {"foreground_id": item}
        if not isinstance(item, dict):
            continue
        requested_id = str(item.get("foreground_id") or item.get("id") or item.get("asset_id") or "").strip()
        asset_path = None
        if requested_id:
            asset_meta = foreground_index.get(requested_id)
            if asset_meta and asset_meta.get("asset_path"):
                asset_path = Path(str(asset_meta["asset_path"]))
        if asset_path is None:
            asset_path = resolve_foreground_asset(
                item.get("asset_path") or item.get("image_path") or item.get("path") or item.get("image_url") or requested_id
            )
        if asset_path is None:
            continue
        normalized.append(
            {
                "asset_path": str(asset_path),
                "x": float(item.get("x", 0.0) or 0.0),
                "y": float(item.get("y", 0.0) or 0.0),
                "width": float(item.get("width", 1.0) or 1.0),
                "height": float(item.get("height", 1.0) or 1.0),
                "opacity": max(0.0, min(1.0, float(item.get("opacity", item.get("alpha", 1.0)) or 1.0))),
                "motion_period_ms": max(60, int(item.get("motion_period_ms", 1400) or 1400)),
            }
        )
    return normalized


def _normalize_video_options(raw_video: Any, tts_enabled: bool) -> dict[str, Any]:
    source = deepcopy(raw_video) if isinstance(raw_video, dict) else {}
    stage_layout = {
        **deepcopy(DEFAULT_VIDEO["stage_layout"]),
        **(source.get("stage_layout") or {}),
    }
    normalized = {**DEFAULT_VIDEO, **source}
    normalized["stage_layout"] = stage_layout
    normalized["tts_enabled"] = bool(normalized.get("tts_enabled", tts_enabled))
    return normalized


def normalize_story(payload: dict[str, Any], source_prompt: str | None = None, tts_enabled: bool = False) -> dict[str, Any]:
    if is_canonical_story_package(payload):
        canonical = deepcopy(payload)
        canonical["video"] = _normalize_video_options(canonical.get("video"), tts_enabled)
        background_index = manifest_index("backgrounds")
        floor_index = manifest_index("floors")
        foreground_index = manifest_index("foregrounds")
        default_background = DEFAULT_BACKGROUND_ID if DEFAULT_BACKGROUND_ID in background_index else next(iter(background_index))
        default_floor = DEFAULT_FLOOR_ID if DEFAULT_FLOOR_ID in floor_index else (next(iter(floor_index)) if floor_index else None)
        for scene in canonical.get("scenes", []):
            duration_ms = int(scene.get("duration_ms", 0) or 0)
            scene.setdefault("background", default_background)
            if not scene.get("floor"):
                background_floor_id = background_index.get(str(scene.get("background") or ""), {}).get("floor_id")
                if background_floor_id and str(background_floor_id) in floor_index:
                    scene["floor"] = str(background_floor_id)
                elif default_floor is not None:
                    scene["floor"] = default_floor
            scene.setdefault("npc_groups", [])
            scene["effects"] = _normalize_scene_effects(
                scene.get("effects"),
                manifest_index("effects"),
                str(scene.get("summary") or ""),
                duration_ms,
            )
            scene["foregrounds"] = _normalize_foregrounds(scene, foreground_index)
            scene["audio"] = _normalize_audio(scene.get("audio"), duration_ms)
            if scene.get("wall_layer") is not None:
                scene["wall_layer"] = _normalize_wall_layer(scene, background_index)
            if "expressions" in scene:
                for item in scene.get("expressions", []):
                    if isinstance(item, dict) and item.get("expression") is not None:
                        item["expression"] = _normalize_expression_name(item.get("expression"))
            for beat in scene.get("beats", []):
                if isinstance(beat, dict) and beat.get("expression") is not None:
                    beat["expression"] = _normalize_expression_name(beat.get("expression"))
        return canonical

    background_index = manifest_index("backgrounds")
    character_index = manifest_index("characters")
    floor_index = manifest_index("floors")
    foreground_index = manifest_index("foregrounds")
    prop_index = manifest_index("props")
    motion_index = manifest_index("motions")
    effect_index = manifest_index("effects")
    default_background = DEFAULT_BACKGROUND_ID if DEFAULT_BACKGROUND_ID in background_index else next(iter(background_index))
    default_floor = DEFAULT_FLOOR_ID if DEFAULT_FLOOR_ID in floor_index else (next(iter(floor_index)) if floor_index else None)
    default_character = next(iter(character_index))

    cast = []
    for item in payload.get("cast", []):
        actor_asset_id = _resolve_id(item.get("asset_id"), character_index, {}, default_character)
        cast.append(
            {
                "id": str(item["id"]),
                "display_name": item.get("display_name") or item["id"],
                "asset_id": actor_asset_id,
                "voice": item.get("voice"),
            }
        )
    cast_ids = {item["id"] for item in cast}

    scenes: list[dict[str, Any]] = []
    for raw_scene in payload.get("scenes", []):
        actor_ids = [actor_id for actor_id in _scene_actor_ids(raw_scene) if actor_id in cast_ids]
        actors = _actor_layout(actor_ids)
        background = _resolve_id(raw_scene.get("background"), background_index, BACKGROUND_ALIASES, default_background)
        requested_floor = raw_scene.get("floor")
        floor = None
        if requested_floor:
            floor = _resolve_id(requested_floor, floor_index, {}, default_floor or "")
        elif background_index.get(background, {}).get("floor_id"):
            default_floor_id = str(background_index[background]["floor_id"])
            floor = default_floor_id if default_floor_id in floor_index else None
        elif default_floor is not None:
            floor = default_floor
        props = _normalize_props(raw_scene.get("props"), prop_index)
        dialogues, talk_beats, duration_ms = _normalize_dialogues(raw_scene, int(raw_scene.get("duration_ms", 0) or 0), effect_index)
        action_beats = _normalize_action_beats(raw_scene, motion_index, effect_index, duration_ms)
        beats = sorted(
            [*_trim_beats_for_actions(talk_beats, action_beats), *action_beats],
            key=lambda item: (int(item.get("start_ms", 0) or 0), str(item.get("actor_id") or "")),
        )
        effects = _normalize_scene_effects(raw_scene.get("effects"), effect_index, str(raw_scene.get("summary") or ""), duration_ms)
        expressions = _normalize_expressions(raw_scene, duration_ms)
        npc_groups = _normalize_npc_groups(raw_scene, character_index, default_character)
        motions = [beat["motion"] for beat in beats if beat.get("motion") in motion_index]
        scenes.append(
            {
                "id": str(raw_scene.get("id") or f"scene-{len(scenes)+1:03d}"),
                "background": background,
                "floor": floor,
                "box": _normalize_box(raw_scene),
                "wall_layer": _normalize_wall_layer(raw_scene, background_index),
                "foregrounds": _normalize_foregrounds(raw_scene, foreground_index),
                "duration_ms": duration_ms,
                "summary": raw_scene.get("summary", ""),
                "camera": _normalize_camera(raw_scene.get("camera")),
                "effects": effects,
                "props": props,
                "actors": actors,
                "npc_groups": npc_groups,
                "beats": beats,
                "expressions": expressions,
                "dialogues": dialogues,
                "audio": _normalize_audio(raw_scene.get("audio"), duration_ms),
                "notes": {"inferred_motions": motions},
            }
        )

    video_options = _normalize_video_options(payload.get("video"), tts_enabled)
    return {
        "meta": {
            "title": payload.get("title", "Untitled Story"),
            "language": payload.get("language", "zh-CN"),
            "theme": payload.get("theme", ""),
            "source_prompt": source_prompt,
        },
        "video": video_options,
        "cast": cast,
        "assets": {
            "backgrounds": sorted(background_index.keys()),
            "floors": sorted(floor_index.keys()),
            "props": sorted(prop_index.keys()),
            "motions": sorted(motion_index.keys()),
            "effects": sorted(effect_index.keys()),
            "foregrounds": sorted(foreground_index.keys()),
        },
        "scenes": scenes,
    }


def validate_story_package(story: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not is_canonical_story_package(story):
        return ["payload is not a canonical story package"]

    background_index = manifest_index("backgrounds")
    character_index = manifest_index("characters")
    floor_index = manifest_index("floors")
    foreground_index = manifest_index("foregrounds")
    prop_index = manifest_index("props")
    motion_index = manifest_index("motions")
    effect_index = manifest_index("effects")
    cast_ids = {item["id"] for item in story.get("cast", [])}
    actor_asset_ids = {item.get("asset_id") for item in story.get("cast", [])}

    for asset_id in actor_asset_ids:
        if asset_id not in character_index:
            errors.append(f"unknown character asset_id: {asset_id}")

    video = story.get("video", {})
    if int(video.get("width", 0) or 0) <= 0:
        errors.append("video.width must be positive")
    if int(video.get("height", 0) or 0) <= 0:
        errors.append("video.height must be positive")
    if int(video.get("fps", 0) or 0) <= 0:
        errors.append("video.fps must be positive")

    for scene in story.get("scenes", []):
        duration_ms = int(scene.get("duration_ms", 0) or 0)
        if duration_ms <= 0:
            errors.append(f"{scene.get('id')}: duration_ms must be positive")
        if scene.get("background") not in background_index:
            errors.append(f"{scene.get('id')}: unknown background {scene.get('background')}")
        wall_layer = scene.get("wall_layer")
        if wall_layer is not None:
            if not isinstance(wall_layer, dict):
                errors.append(f"{scene.get('id')}: wall_layer must be an object when present")
            elif wall_layer.get("background_id") and wall_layer.get("background_id") not in background_index:
                errors.append(f"{scene.get('id')}: unknown wall_layer background {wall_layer.get('background_id')}")
        floor_id = scene.get("floor")
        if floor_id and floor_id not in floor_index:
            errors.append(f"{scene.get('id')}: unknown floor {floor_id}")
        box = scene.get("box")
        if box is not None and not isinstance(box, dict):
            errors.append(f"{scene.get('id')}: box must be an object when present")
        if len(scene.get("actors", [])) > 4:
            errors.append(f"{scene.get('id')}: more than 4 active actors is not supported")
        npc_groups = scene.get("npc_groups", [])
        if npc_groups is not None and not isinstance(npc_groups, list):
            errors.append(f"{scene.get('id')}: npc_groups must be a list when present")

        beat_windows: dict[str, list[tuple[int, int]]] = {}
        dialogue_windows: list[tuple[int, int]] = []

        for actor in scene.get("actors", []):
            actor_id = actor.get("actor_id")
            if actor_id not in cast_ids:
                errors.append(f"{scene.get('id')}: actor_id {actor_id} missing from cast")

        for prop in scene.get("props", []):
            if prop.get("prop_id") not in prop_index:
                errors.append(f"{scene.get('id')}: unknown prop {prop.get('prop_id')}")

        for npc_group in npc_groups or []:
            behavior = str(npc_group.get("behavior") or "")
            if behavior not in NPC_BEHAVIORS:
                errors.append(f"{scene.get('id')}: unsupported npc behavior {behavior}")
            target_actor_id = npc_group.get("target_actor_id")
            if target_actor_id and target_actor_id not in cast_ids:
                errors.append(f"{scene.get('id')}: npc target_actor_id {target_actor_id} missing from cast")
            if int(npc_group.get("count", 0) or 0) <= 0:
                errors.append(f"{scene.get('id')}: npc group {npc_group.get('id')} must have positive count")
            for asset_id in npc_group.get("asset_ids", []):
                if asset_id not in character_index:
                    errors.append(f"{scene.get('id')}: npc group {npc_group.get('id')} unknown asset_id {asset_id}")
            area = npc_group.get("area") or {}
            if float(area.get("x_min", 0.0) or 0.0) > float(area.get("x_max", 0.0) or 0.0):
                errors.append(f"{scene.get('id')}: npc group {npc_group.get('id')} area x_min must be <= x_max")
            if float(area.get("front_min", 0.0) or 0.0) > float(area.get("front_max", 0.0) or 0.0):
                errors.append(f"{scene.get('id')}: npc group {npc_group.get('id')} area front_min must be <= front_max")

        for effect in scene.get("effects", []):
            effect_type = effect.get("type")
            start_ms = int(effect.get("start_ms", -1) or -1)
            end_ms = int(effect.get("end_ms", -1) or -1)
            if effect_type is not None and effect_type not in effect_index and not effect.get("asset_path"):
                errors.append(f"{scene.get('id')}: unknown effect {effect.get('type')}")
            if not (0 <= start_ms < end_ms <= duration_ms):
                errors.append(f"{scene.get('id')}: invalid effect window {start_ms}-{end_ms}")
            asset_path = effect.get("asset_path")
            if asset_path and not Path(str(asset_path)).exists():
                errors.append(f"{scene.get('id')}: missing effect asset {asset_path}")

        for index, item in enumerate(scene.get("foregrounds", []), start=1):
            if not isinstance(item, dict):
                errors.append(f"{scene.get('id')}: foregrounds[{index}] must be an object")
                continue
            asset_path = item.get("asset_path")
            if not asset_path or not Path(str(asset_path)).exists():
                errors.append(f"{scene.get('id')}: missing foreground asset {asset_path}")
            for key in ("width", "height"):
                if float(item.get(key, 0.0) or 0.0) <= 0.0:
                    errors.append(f"{scene.get('id')}: foregrounds[{index}] {key} must be positive")

        for beat in scene.get("beats", []):
            actor_id = beat.get("actor_id")
            start_ms = int(beat.get("start_ms", -1))
            end_ms = int(beat.get("end_ms", -1))
            if actor_id not in cast_ids:
                errors.append(f"{scene.get('id')}: beat actor_id {actor_id} missing from cast")
            if beat.get("motion") not in motion_index:
                errors.append(f"{scene.get('id')}: unknown motion {beat.get('motion')}")
            if beat.get("expression") is not None and _normalize_expression_name(beat.get("expression")) not in set(EXPRESSION_ALIASES.values()):
                errors.append(f"{scene.get('id')}: unknown beat expression {beat.get('expression')}")
            if not (0 <= start_ms < end_ms <= duration_ms):
                errors.append(f"{scene.get('id')}: invalid beat window {start_ms}-{end_ms}")
            beat_windows.setdefault(str(actor_id), []).append((start_ms, end_ms))

        for actor_id, windows in beat_windows.items():
            ordered = sorted(windows)
            for prev, curr in zip(ordered, ordered[1:]):
                if curr[0] < prev[1]:
                    errors.append(f"{scene.get('id')}: overlapping beats for actor {actor_id}")

        for dialogue in scene.get("dialogues", []):
            speaker_id = dialogue.get("speaker_id")
            start_ms = int(dialogue.get("start_ms", -1))
            end_ms = int(dialogue.get("end_ms", -1))
            if speaker_id not in cast_ids:
                errors.append(f"{scene.get('id')}: speaker_id {speaker_id} missing from cast")
            if not (0 <= start_ms < end_ms <= duration_ms):
                errors.append(f"{scene.get('id')}: invalid dialogue window {start_ms}-{end_ms}")
            dialogue_windows.append((start_ms, end_ms))

        ordered_dialogues = sorted(dialogue_windows)
        for prev, curr in zip(ordered_dialogues, ordered_dialogues[1:]):
            if curr[0] < prev[1]:
                errors.append(f"{scene.get('id')}: overlapping dialogue windows")

        expression_windows: dict[str, list[tuple[int, int]]] = {}
        for item in scene.get("expressions", []):
            actor_id = item.get("actor_id")
            start_ms = int(item.get("start_ms", -1))
            end_ms = int(item.get("end_ms", -1))
            expression = _normalize_expression_name(item.get("expression"))
            if actor_id not in cast_ids:
                errors.append(f"{scene.get('id')}: expression actor_id {actor_id} missing from cast")
            if expression not in set(EXPRESSION_ALIASES.values()):
                errors.append(f"{scene.get('id')}: unknown expression {item.get('expression')}")
            if not (0 <= start_ms < end_ms <= duration_ms):
                errors.append(f"{scene.get('id')}: invalid expression window {start_ms}-{end_ms}")
            expression_windows.setdefault(str(actor_id), []).append((start_ms, end_ms))

        for actor_id, windows in expression_windows.items():
            ordered = sorted(windows)
            for prev, curr in zip(ordered, ordered[1:]):
                if curr[0] < prev[1]:
                    errors.append(f"{scene.get('id')}: overlapping expressions for actor {actor_id}")

        audio = scene.get("audio", {})
        if not isinstance(audio, dict):
            errors.append(f"{scene.get('id')}: audio must be an object")
        else:
            bgm = audio.get("bgm")
            if bgm is not None:
                if not isinstance(bgm, dict):
                    errors.append(f"{scene.get('id')}: audio.bgm must be an object when present")
                else:
                    asset_path = bgm.get("asset_path")
                    if not asset_path or not Path(str(asset_path)).exists():
                        errors.append(f"{scene.get('id')}: missing bgm asset {asset_path}")
            sfx_items = audio.get("sfx", [])
            if not isinstance(sfx_items, list):
                errors.append(f"{scene.get('id')}: audio.sfx must be a list")
            else:
                for index, cue in enumerate(sfx_items, start=1):
                    if not isinstance(cue, dict):
                        errors.append(f"{scene.get('id')}: audio.sfx[{index}] must be an object")
                        continue
                    asset_path = cue.get("asset_path")
                    if not asset_path or not Path(str(asset_path)).exists():
                        errors.append(f"{scene.get('id')}: missing sfx asset {asset_path}")
                    start_ms = int(cue.get("start_ms", -1) or -1)
                    if start_ms < 0 or start_ms > duration_ms:
                        errors.append(f"{scene.get('id')}: invalid sfx start {start_ms}")
                    if cue.get("end_ms") is not None:
                        end_ms = int(cue.get("end_ms", -1) or -1)
                        if not (0 <= start_ms < end_ms):
                            errors.append(f"{scene.get('id')}: invalid sfx window {start_ms}-{end_ms}")

    return errors


def load_and_normalize_story(path: Path, source_prompt: str | None = None, tts_enabled: bool = False) -> dict[str, Any]:
    payload, _ = load_story_source(path)
    story = normalize_story(payload, source_prompt=source_prompt, tts_enabled=tts_enabled)
    errors = validate_story_package(story)
    if errors:
        raise ValueError("\n".join(errors))
    return story


def save_story_package(story: dict[str, Any], output: Path | None = None) -> Path:
    target = output or (WORK_DIR / "story_package.json")
    write_json(target, story)
    return target
