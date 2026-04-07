from __future__ import annotations

import json
import hashlib
import os
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from typing import Any, Optional
from PIL import Image, UnidentifiedImageError


ROOT_DIR = Path(__file__).resolve().parents[2]
ASSETS_DIR = ROOT_DIR / "assets"
BACKGROUNDS_DIR = ASSETS_DIR / "backgrounds"
BGM_ASSETS_DIR = ASSETS_DIR / "bgm"
CHARACTERS_DIR = ASSETS_DIR / "characters"
EFFECTS_DIR = ASSETS_DIR / "effects"
FLOORS_DIR = ASSETS_DIR / "floors"
FOREGROUNDS_DIR = ASSETS_DIR / "foreground"
MANIFESTS_DIR = ASSETS_DIR / "manifests"
PROPS_DIR = ASSETS_DIR / "props"
AUDIO_ASSETS_DIR = ASSETS_DIR / "audio"
WORK_DIR = ROOT_DIR / "work"
TMP_DIR = Path(os.environ.get("PANDAVIDEO_TMP_DIR", str(ROOT_DIR / "tmp")))
OUTPUTS_DIR = ROOT_DIR / "outputs"
FRAMES_DIR = TMP_DIR / "frames"
AUDIO_DIR = TMP_DIR / "audio"
REMOTE_ASSETS_DIR = TMP_DIR / "remote_assets"
BACKGROUND_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")
BACKGROUND_FLOOR_DEFAULTS = {
    "archive-library": "wood-plank",
    "bank-lobby": "wood-plank",
    "cafe-night": "wood-plank",
    "hotel-lobby": "wood-plank",
    "inn-hall": "wood-plank",
    "mountain-cliff": "stone-court",
    "museum-gallery": "wood-plank",
    "night-bridge": "dark-stage",
    "park-evening": "dark-stage",
    "restaurant-booth": "wood-plank",
    "room-day": "wood-plank",
    "school-yard": "stone-court",
    "shop-row": "stone-court",
    "street-day": "stone-court",
    "temple-courtyard": "stone-court",
    "theatre-stage": "dark-stage",
    "town-hall-records": "wood-plank",
    "training-ground": "stone-court",
}


def ensure_runtime_dirs() -> None:
    for path in (WORK_DIR, TMP_DIR, OUTPUTS_DIR, FRAMES_DIR, AUDIO_DIR, REMOTE_ASSETS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def _path_lookup_keys(value: str) -> tuple[str, str]:
    candidate = Path(value)
    name = candidate.name.lower()
    stem = candidate.stem.lower()
    return name, stem


@lru_cache(maxsize=None)
def _discover_local_media_files(directory: Path, suffixes: tuple[str, ...]) -> tuple[Path, ...]:
    if not directory.exists():
        return ()
    files: list[Path] = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        if path.name.endswith(":Zone.Identifier"):
            continue
        if path.suffix.lower() not in suffixes:
            continue
        files.append(path)
    return tuple(files)


def _resolve_local_media_asset(value: Any, directory: Path, suffixes: tuple[str, ...]) -> Optional[Path]:
    raw = str(value or "").strip()
    if not raw:
        return None
    candidate = Path(raw)
    direct_candidates = []
    if candidate.is_absolute():
        direct_candidates.append(candidate)
    else:
        direct_candidates.extend(
            [
                ROOT_DIR / candidate,
                ASSETS_DIR / candidate,
                directory / candidate,
            ]
        )
    for direct in direct_candidates:
        if direct.is_file() and direct.suffix.lower() in suffixes:
            return direct.resolve()

    raw_name, raw_stem = _path_lookup_keys(raw)
    discovered = _discover_local_media_files(directory, suffixes)
    exact_name_match = next((path for path in discovered if path.name.lower() == raw_name), None)
    if exact_name_match is not None:
        return exact_name_match
    exact_stem_match = next((path for path in discovered if path.stem.lower() == raw_stem), None)
    if exact_stem_match is not None:
        return exact_stem_match
    token_match = next(
        (
            path
            for path in discovered
            if raw_stem and (raw_stem in path.stem.lower() or path.stem.lower() in raw_stem)
        ),
        None,
    )
    return token_match


def resolve_audio_asset(value: Any) -> Optional[Path]:
    return _resolve_local_media_asset(
        value,
        AUDIO_ASSETS_DIR,
        (".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"),
    )


def resolve_bgm_asset(value: Any) -> Optional[Path]:
    return _resolve_local_media_asset(
        value,
        BGM_ASSETS_DIR,
        (".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"),
    )


def resolve_effect_asset(value: Any) -> Optional[Path]:
    return _resolve_local_media_asset(
        value,
        EFFECTS_DIR,
        (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"),
    )


def resolve_foreground_asset(value: Any) -> Optional[Path]:
    return _resolve_local_media_asset(
        value,
        FOREGROUNDS_DIR,
        (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"),
    )


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _normalize_color(value: Any, default: list[float]) -> list[float]:
    if not isinstance(value, (list, tuple)):
        return list(default)
    normalized = [float(item) for item in value[:4]]
    if any(item > 1.0 for item in normalized):
        normalized = [item / 255.0 for item in normalized]
    if len(normalized) == 3:
        normalized.append(1.0)
    while len(normalized) < 4:
        normalized.append(default[len(normalized)])
    return normalized[:4]


def _find_asset_file(directory: Path, stems: list[str]) -> Optional[Path]:
    for stem in stems:
        for suffix in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"):
            candidate = directory / f"{stem}{suffix}"
            if candidate.exists():
                return candidate
    return None


@lru_cache(maxsize=1)
def discover_wall_layer_asset() -> Optional[Path]:
    weighted_keywords = {
        "foreground": 12,
        "overlay": 14,
        "room": 18,
        "window": 20,
        "door": 20,
        "frame": 14,
        "interior": 18,
        "near": 12,
        "walllayer": 16,
        "wall_layer": 16,
        "qiang": 14,
        "fangjian": 18,
        "qianjing": 16,
        "jingjing": 12,
        "近景": 18,
        "前景": 18,
        "房间": 20,
        "室内": 20,
        "门窗": 22,
        "窗": 18,
        "门": 18,
        "透明": 16,
    }
    negative_keywords = {
        "curtain": 20,
        "drape": 20,
        "帘": 18,
        "窗帘": 22,
        "床帘": 22,
    }
    exclude_parts = {
        "characters",
        "props",
        "effects",
        "manifests",
        "_shared_skins",
        "floors",
        "backgrounds",
    }
    candidates: list[tuple[int, int, Path]] = []
    for path in ASSETS_DIR.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".png", ".webp", ".gif"}:
            continue
        parts = {part.lower() for part in path.parts}
        if exclude_parts & parts:
            continue
        stem = path.stem.lower()
        joined = str(path.relative_to(ASSETS_DIR)).lower()
        keyword_score = sum(weight for keyword, weight in weighted_keywords.items() if keyword in stem or keyword in joined)
        keyword_score -= sum(weight for keyword, weight in negative_keywords.items() if keyword in stem or keyword in joined)
        if keyword_score <= 0:
            continue
        try:
            with Image.open(path) as image:
                width, height = image.size
                if width < 320 or height < 180:
                    continue
                alpha_score = 0
                if image.mode in {"RGBA", "LA"}:
                    alpha = image.getchannel("A")
                    bbox = alpha.getbbox()
                    if bbox and bbox != (0, 0, width, height):
                        alpha_score = 40
                    elif bbox is None:
                        continue
                    else:
                        extrema = alpha.getextrema()
                        if extrema[0] < 255:
                            alpha_score = 30
                elif image.info.get("transparency") is not None:
                    alpha_score = 30
                else:
                    rgb = image.convert("RGB")
                    sample = rgb.resize((64, 64))
                    pixels = list(sample.getdata())
                    near_white = sum(1 for r, g, b in pixels if r >= 245 and g >= 245 and b >= 245)
                    if near_white < len(pixels) * 0.20:
                        continue
                    alpha_score = 18
                open_score = 0
                probe = image.convert("RGBA").resize((64, 64))
                center_pixels = []
                for y in range(16, 48):
                    for x in range(16, 48):
                        center_pixels.append(probe.getpixel((x, y)))
                if center_pixels:
                    open_pixels = 0
                    for r, g, b, a in center_pixels:
                        if a <= 8 or (r >= 245 and g >= 245 and b >= 245):
                            open_pixels += 1
                    open_ratio = open_pixels / len(center_pixels)
                    open_score = int(open_ratio * 60)
        except (UnidentifiedImageError, OSError, ValueError):
            continue
        size_score = min(40, (width * height) // 50000)
        candidates.append((keyword_score + alpha_score + size_score + open_score, width * height, path))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1], str(item[2])), reverse=True)
    return candidates[0][2]


@lru_cache(maxsize=1)
def discover_effect_assets() -> dict[str, Path]:
    if not EFFECTS_DIR.exists():
        return {}
    files = [path for path in sorted(EFFECTS_DIR.iterdir()) if path.is_file() and path.suffix.lower() in {".png", ".webp", ".gif"}]
    if not files:
        return {}

    groups: dict[str, tuple[str, ...]] = {
        "launch": ("启动大招特效", "大招特效", "attack_launch", "launch_effect"),
        "hit": ("命中", "hit", "impact"),
        "explosion": ("爆炸", "explosion", "burst"),
        "dragon": ("金龙飞旋", "降龙十八掌", "dragon", "golden_dragon"),
        "vortex": ("旋风龙卷风", "龙卷风", "vortex", "tornado", "whirlwind"),
        "galaxy": ("银河旋转", "银河", "galaxy", "cosmic", "spiral"),
    }
    discovered: dict[str, Path] = {}
    for group_name, keywords in groups.items():
        for keyword in keywords:
            for path in files:
                if keyword.lower() in path.stem.lower():
                    discovered[group_name] = path
                    break
            if group_name in discovered:
                break
    if "launch" not in discovered:
        for path in files:
            if "hit" not in path.stem.lower():
                discovered["launch"] = path
                break
    return discovered


@lru_cache(maxsize=1)
def discover_attack_effect_asset() -> Optional[Path]:
    return discover_effect_assets().get("launch")


def _load_bgm_assets() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in _discover_local_media_files(BGM_ASSETS_DIR, (".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac")):
        rel_path = path.relative_to(ROOT_DIR)
        items.append(
            {
                "id": path.stem,
                "label": path.name,
                "asset_path": str(path),
                "path": str(rel_path),
                "ext": path.suffix.lower(),
            }
        )
    return items


def _load_foreground_assets() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in _discover_local_media_files(FOREGROUNDS_DIR, (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")):
        rel_path = path.relative_to(ROOT_DIR)
        items.append(
            {
                "id": path.stem,
                "label": path.stem,
                "asset_path": str(path),
                "path": str(rel_path),
                "ext": path.suffix.lower(),
            }
        )
    return items


def _load_effect_assets() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in _discover_local_media_files(EFFECTS_DIR, (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")):
        rel_path = path.relative_to(ROOT_DIR)
        items.append(
            {
                "id": path.stem,
                "label": path.stem,
                "asset_path": str(path),
                "path": str(rel_path),
                "ext": path.suffix.lower(),
            }
        )
    grouped = discover_effect_assets()
    alias_map = {
        "aura": grouped.get("launch"),
        "launch": grouped.get("launch"),
        "hit": grouped.get("hit"),
        "explosion": grouped.get("explosion"),
        "dragon-palm": grouped.get("dragon"),
        "thunder-strike": grouped.get("vortex"),
        "sword-arc": grouped.get("galaxy"),
    }
    for effect_id, asset_path in alias_map.items():
        if asset_path is None:
            continue
        items.append(
            {
                "id": effect_id,
                "label": effect_id,
                "asset_path": str(asset_path),
                "path": str(asset_path.relative_to(ROOT_DIR)),
                "ext": asset_path.suffix.lower(),
            }
        )
    return items


def _cached_remote_asset(url: Any, namespace: str) -> Optional[Path]:
    raw = str(url or "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    suffix = Path(parsed.path).suffix.lower() or ".img"
    cache_name = f"{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:20]}{suffix}"
    target_dir = REMOTE_ASSETS_DIR / namespace
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / cache_name
    if target.exists() and target.stat().st_size > 0:
        try:
            with Image.open(target) as image:
                image.verify()
            return target
        except Exception:
            target.unlink(missing_ok=True)
    request = Request(raw, headers={"User-Agent": "panda3d-video/1.0"})
    content_type = ""
    try:
        with urlopen(request, timeout=20) as response:
            content_type = (response.headers.get("Content-Type") or "").lower()
            data = response.read()
    except Exception:
        return None
    if not data:
        return None
    if content_type.startswith("text/") or data[:32].lstrip().startswith(b"<"):
        return None
    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        return None
    target.write_bytes(data)
    return target


def _load_background_assets() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not BACKGROUNDS_DIR.exists():
        return items
    for path in _discover_local_media_files(BACKGROUNDS_DIR, BACKGROUND_IMAGE_SUFFIXES):
        asset_id = path.stem
        items.append(
            {
                "id": asset_id,
                "label": asset_id.replace("-", " ").title(),
                "floor_id": BACKGROUND_FLOOR_DEFAULTS.get(asset_id),
                "asset_path": str(path),
                "path": str(path.relative_to(ROOT_DIR)),
            }
        )
    return items


def _load_floor_assets() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not FLOORS_DIR.exists():
        return items
    for path in sorted(FLOORS_DIR.glob("*.json")):
        payload = read_json(path)
        asset_id = str(payload.get("id") or path.stem)
        items.append(
            {
                "id": asset_id,
                "label": payload.get("display_name") or payload.get("label") or asset_id,
                "color": _normalize_color(payload.get("color"), [0.46, 0.46, 0.46, 1.0]),
                "accent_color": _normalize_color(payload.get("accent_color"), [0.58, 0.58, 0.58, 1.0]),
            }
        )
    return items


def _load_prop_assets() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not PROPS_DIR.exists():
        return items
    for directory in sorted(PROPS_DIR.iterdir()):
        if not directory.is_dir() or directory.name.startswith(("_", ".")):
            continue
        meta_path = directory / "prop.json"
        payload = read_json(meta_path) if meta_path.exists() else {}
        image_path = _find_asset_file(directory, ["asset", "sprite", "image", "preview"])
        if image_path is None:
            image_path = _cached_remote_asset(payload.get("image_url"), "props")
        items.append(
            {
                "id": directory.name,
                "label": payload.get("display_name") or payload.get("label") or directory.name,
                "width": float(payload.get("width", 0.0) or 0.0),
                "height": float(payload.get("height", 0.0) or 0.0),
                "color": _normalize_color(payload.get("color"), [1.0, 1.0, 1.0, 1.0]),
                "asset_path": str(image_path) if image_path else None,
                "image_url": payload.get("image_url"),
                "base_width": int(payload.get("base_width", 160) or 160),
                "base_height": int(payload.get("base_height", 120) or 120),
                "category": payload.get("category"),
                "anchor": list(payload.get("anchor", [0.5, 1.0])),
                "default_layer": payload.get("default_layer", "front"),
                "default_mount": payload.get("default_mount", "free"),
                "render_style": payload.get("render_style", "sprite"),
                "frame_color": _normalize_color(payload.get("frame_color"), [0.36, 0.24, 0.12, 1.0]),
                "mat_color": _normalize_color(payload.get("mat_color"), [0.94, 0.92, 0.88, 1.0]),
                "glass_color": _normalize_color(payload.get("glass_color"), [0.78, 0.90, 1.0, 0.26]),
                "frame_padding": float(payload.get("frame_padding", 0.10) or 0.10),
                "animated": bool(payload.get("animated", False)),
                "motion": payload.get("motion"),
                "motion_x": float(payload.get("motion_x", 0.0) or 0.0),
                "motion_y": float(payload.get("motion_y", 0.0) or 0.0),
                "motion_period_ms": int(payload.get("motion_period_ms", 1400) or 1400),
                "shadow_alpha": int(payload.get("shadow_alpha", 0) or 0),
            }
        )
    return items


def _load_character_assets() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not CHARACTERS_DIR.exists():
        return items
    for directory in sorted(CHARACTERS_DIR.iterdir()):
        if not directory.is_dir() or directory.name.startswith(("_", ".")):
            continue
        meta_path = directory / "character.json"
        payload = read_json(meta_path) if meta_path.exists() else {}
        item: dict[str, Any] = {
            "id": directory.name,
            "character_dir": str(directory),
            "body_color": _normalize_color(payload.get("body_color"), [0.18, 0.28, 0.38, 1.0]),
            "body_secondary_color": _normalize_color(payload.get("trim_color"), [0.82, 0.82, 0.82, 1.0]),
            "head_color": _normalize_color(payload.get("skin_color"), [0.97, 0.97, 0.95, 1.0]),
            "accent_color": _normalize_color(payload.get("accent_color"), [0.82, 0.34, 0.20, 1.0]),
            "bone_color": _normalize_color(payload.get("bone_color"), [0.10, 0.10, 0.11, 1.0]),
            "patch_color": _normalize_color(payload.get("hair_color"), [0.10, 0.10, 0.11, 1.0]),
            "blush_color": _normalize_color(payload.get("blush_color"), [0.96, 0.71, 0.74, 0.30]),
            "mouth_color": _normalize_color(payload.get("mouth_color"), [0.66, 0.28, 0.30, 1.0]),
            "head_anchor": payload.get("head_anchor") or {"offset": [0, 0], "scale": 1.0},
        }
        label = payload.get("display_name") or payload.get("label")
        if label:
            item["label"] = label
        gender = payload.get("gender_presentation") or payload.get("gender")
        if gender:
            item["gender_presentation"] = str(gender)
        tts_speaker_id = payload.get("tts_speaker_id") or payload.get("voice_default")
        if tts_speaker_id:
            item["tts_speaker_id"] = tts_speaker_id
        if "show_bones" in payload:
            item["show_bones"] = payload.get("show_bones")
        if payload.get("outfit_style"):
            item["outfit_style"] = payload.get("outfit_style")
        if payload.get("garment"):
            item["garment"] = payload.get("garment")
        items.append(item)
    return items


def _load_audio_assets() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in _discover_local_media_files(AUDIO_ASSETS_DIR, (".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac")):
        rel_path = path.relative_to(ROOT_DIR)
        items.append(
            {
                "id": path.stem,
                "label": path.name,
                "path": str(rel_path),
                "ext": path.suffix.lower(),
            }
        )
    return items


def load_manifest(name: str) -> list[dict[str, Any]]:
    manifest_path = MANIFESTS_DIR / f"{name}.json"
    manifest_items = read_json(manifest_path) if manifest_path.exists() else []
    if name == "backgrounds":
        discovered = _load_background_assets()
    elif name == "floors":
        discovered = _load_floor_assets()
    elif name == "props":
        discovered = _load_prop_assets()
    elif name == "characters":
        discovered = _load_character_assets()
    elif name == "effects":
        discovered = _load_effect_assets()
    elif name == "foregrounds":
        discovered = _load_foreground_assets()
    elif name == "bgm":
        discovered = _load_bgm_assets()
    else:
        discovered = []

    if not discovered:
        return manifest_items

    merged = {item["id"]: item for item in manifest_items}
    for item in discovered:
        base = merged.get(item["id"], {})
        merged[item["id"]] = {**base, **item}
    return list(merged.values())


def manifest_index(name: str) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in load_manifest(name)}


def asset_catalog() -> dict[str, list[dict[str, Any]]]:
    categories = ("backgrounds", "floors", "characters", "props", "motions", "effects", "foregrounds", "audio", "bgm")
    catalog: dict[str, list[dict[str, Any]]] = {}
    for name in categories:
        if name == "audio":
            catalog[name] = _load_audio_assets()
            continue
        if name == "bgm":
            catalog[name] = [
                {
                    "id": item.get("id"),
                    "label": item.get("label") or item.get("id"),
                    "path": item.get("path"),
                    "ext": item.get("ext"),
                }
                for item in load_manifest(name)
            ]
            continue
        items = []
        for item in load_manifest(name):
            summary = {
                "id": item.get("id"),
                "label": item.get("label") or item.get("display_name") or item.get("id"),
            }
            if name == "backgrounds":
                summary["has_image"] = bool(item.get("asset_path"))
                summary["asset_path"] = (
                    str(Path(str(item["asset_path"])).relative_to(ROOT_DIR)) if item.get("asset_path") else None
                )
                if item.get("floor_id"):
                    summary["default_floor"] = item.get("floor_id")
            elif name == "floors":
                summary["has_image"] = False
            elif name == "characters":
                summary["has_face_skins"] = bool(item.get("character_dir"))
                if item.get("outfit_style"):
                    summary["outfit_style"] = item.get("outfit_style")
                if item.get("gender_presentation"):
                    summary["gender_presentation"] = item.get("gender_presentation")
                if item.get("tts_speaker_id"):
                    summary["tts_speaker_id"] = item.get("tts_speaker_id")
            elif name == "props":
                summary["has_image"] = bool(item.get("asset_path") or item.get("image_url"))
                summary["default_layer"] = item.get("default_layer")
                summary["default_mount"] = item.get("default_mount")
            elif name == "effects":
                summary["asset_path"] = item.get("path") or (
                    str(Path(str(item["asset_path"])).relative_to(ROOT_DIR)) if item.get("asset_path") else None
                )
            elif name == "foregrounds":
                summary["has_image"] = bool(item.get("asset_path"))
                summary["asset_path"] = item.get("path") or (
                    str(Path(str(item["asset_path"])).relative_to(ROOT_DIR)) if item.get("asset_path") else None
                )
            items.append(summary)
        catalog[name] = sorted(items, key=lambda item: str(item.get("id") or ""))
    return catalog
