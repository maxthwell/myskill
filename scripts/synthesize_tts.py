#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from common.io import AUDIO_DIR, TMP_DIR, ROOT_DIR, ensure_runtime_dirs, manifest_index, read_json, write_json


DEFAULT_VOICE_BY_GENDER = {
    "masculine": "zh-CN-YunxiNeural",
    "feminine": "zh-CN-XiaoxiaoNeural",
    "neutral": "zh-CN-YunjianNeural",
    "unspecified": "zh-CN-YunjianNeural",
}
TTS_CACHE_DIR = ROOT_DIR / "tmp" / "tts_cache"
BASE_TTS_RATE_PCT = 0
MIN_TTS_DURATION_MS = 1400
TTS_TAIL_PAD_MS = 220
VOICE_VARIANT_STRENGTH = 1.0 / 40.0
VOICE_PITCH_JITTER_RANGE = 0.004
VOICE_TEMPO_JITTER_RANGE = 0.0015
VOICE_SPEECH_RATE_JITTER_RANGE = 1.0
VOICE_HIGHPASS_JITTER_RANGE = 3
VOICE_LOWPASS_JITTER_RANGE = 20
VOICE_LOW_EQ_JITTER_RANGE = 0.15
VOICE_PRESENCE_EQ_JITTER_RANGE = 0.175
VOICE_GAIN_JITTER_RANGE = 0.075


def _edge_rate_string(rate_pct: int) -> str:
    rate_pct = int(max(-50, min(50, rate_pct)))
    return f"+{rate_pct}%" if rate_pct >= 0 else f"{rate_pct}%"


async def _synthesize_file(text: str, voice: str, output_path: Path, *, rate_pct: int = 0) -> bool:
    try:
        import edge_tts
    except ModuleNotFoundError:
        return False
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice or "zh-CN-XiaoxiaoNeural",
        rate=_edge_rate_string(rate_pct),
    )
    await communicate.save(str(output_path))
    return True


def _normalize_audio_level(path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not path.exists():
        return
    fd, temp_name = tempfile.mkstemp(prefix="tts-norm-", suffix=path.suffix, dir=str(path.parent))
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        result = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(path),
                "-vn",
                "-af",
                "loudnorm=I=-14:LRA=7:TP=-1.0",
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "2",
                str(temp_path),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and temp_path.exists() and temp_path.stat().st_size > 0:
            temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _pad_tts_timing(path: Path, *, min_duration_ms: int = MIN_TTS_DURATION_MS, tail_pad_ms: int = TTS_TAIL_PAD_MS) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not path.exists():
        return
    current_ms = _probe_duration_ms(path)
    target_ms = max(int(min_duration_ms), int(current_ms) + int(tail_pad_ms))
    if target_ms <= current_ms:
        return
    fd, temp_name = tempfile.mkstemp(prefix="tts-pad-", suffix=path.suffix, dir=str(path.parent))
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        result = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(path),
                "-vn",
                "-af",
                f"apad=pad_dur={max(0.0, (target_ms - current_ms) / 1000.0):.3f}",
                "-t",
                f"{target_ms / 1000.0:.3f}",
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "2",
                str(temp_path),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and temp_path.exists() and temp_path.stat().st_size > 0:
            temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _tts_cache_key(text: str, voice: str, rate_pct: int) -> str:
    digest = hashlib.sha1()
    digest.update(b"edge-tts-v3\0")
    digest.update((voice or "").encode("utf-8"))
    digest.update(b"\0")
    digest.update(str(int(rate_pct)).encode("utf-8"))
    digest.update(b"\0")
    digest.update((text or "").encode("utf-8"))
    return digest.hexdigest()


def _variant_cache_key(text: str, voice: str, profile: dict[str, object]) -> str:
    digest = hashlib.sha1()
    digest.update(b"edge-tts-variant-v12\0")
    digest.update((voice or "").encode("utf-8"))
    digest.update(b"\0")
    digest.update((text or "").encode("utf-8"))
    digest.update(b"\0")
    digest.update(json.dumps(profile, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    return digest.hexdigest()


def _copy_audio(src: Path, dest: Path) -> None:
    if src.resolve() == dest.resolve():
        return
    shutil.copy2(src, dest)


def _stable_unit(value: str) -> float:
    digest = hashlib.sha1((value or "").encode("utf-8")).digest()
    number = int.from_bytes(digest[:8], "big")
    return number / float(2**64 - 1)


def _derive_voice_variant_profile(
    speaker_id: str,
    speaker_meta: dict[str, object],
    cast_item: dict[str, object],
    voice: str,
) -> dict[str, object]:
    asset_id = str(speaker_meta.get("asset_id") or "")
    asset_label = str(speaker_meta.get("label") or speaker_meta.get("display_name") or "")
    material_signature = {
        "body_color": speaker_meta.get("body_color"),
        "body_secondary_color": speaker_meta.get("body_secondary_color"),
        "head_color": speaker_meta.get("head_color"),
        "accent_color": speaker_meta.get("accent_color"),
        "patch_color": speaker_meta.get("patch_color"),
        "outfit_style": speaker_meta.get("outfit_style"),
    }
    fingerprint = "|".join(
        [
            asset_id or str(speaker_id or ""),
            asset_label,
            str(voice or ""),
            json.dumps(material_signature, ensure_ascii=False, sort_keys=True),
        ]
    )
    gender = _normalize_gender(speaker_meta.get("gender_presentation"))
    strength = VOICE_VARIANT_STRENGTH
    pitch_base_delta = (-0.002 if gender == "masculine" else 0.002 if gender == "feminine" else 0.0) * strength
    brightness_base = int(round((-7 if gender == "masculine" else 9 if gender == "feminine" else 0) * strength))
    pitch_jitter = (_stable_unit(fingerprint + ":pitch") - 0.5) * (VOICE_PITCH_JITTER_RANGE * 2.0) * strength
    tempo_jitter = (_stable_unit(fingerprint + ":tempo") - 0.5) * (VOICE_TEMPO_JITTER_RANGE * 2.0) * strength
    speech_rate_jitter = 0
    highpass_jitter = round(((_stable_unit(fingerprint + ":hp") - 0.5) * (VOICE_HIGHPASS_JITTER_RANGE * 2.0)) * strength)
    lowpass_jitter = round(((_stable_unit(fingerprint + ":lp") - 0.5) * (VOICE_LOWPASS_JITTER_RANGE * 2.0)) * strength)
    low_eq = round(((_stable_unit(fingerprint + ":loweq") - 0.5) * (VOICE_LOW_EQ_JITTER_RANGE * 2.0)) * strength, 2)
    presence_eq = round(((_stable_unit(fingerprint + ":presence") - 0.5) * (VOICE_PRESENCE_EQ_JITTER_RANGE * 2.0)) * strength, 2)
    gain_db = round(((_stable_unit(fingerprint + ":gain") - 0.5) * (VOICE_GAIN_JITTER_RANGE * 2.0)) * strength, 2)

    profile: dict[str, object] = {
        "fingerprint": fingerprint,
        "asset_id": asset_id or None,
        "pitch_ratio": round(max(0.994, min(1.006, 1.0 + pitch_base_delta + pitch_jitter)), 4),
        "tempo_ratio": 1.0,
        "speech_rate_pct": BASE_TTS_RATE_PCT + speech_rate_jitter,
        "highpass_hz": int(max(115, min(121, 118 + highpass_jitter))),
        "lowpass_hz": int(max(3270, min(3330, 3300 + brightness_base + lowpass_jitter))),
        "low_eq_db": low_eq,
        "presence_eq_db": presence_eq,
        "gain_db": gain_db,
    }
    override = cast_item.get("voice_variant")
    if isinstance(override, dict):
        for key in ("pitch_ratio", "tempo_ratio", "speech_rate_pct", "highpass_hz", "lowpass_hz", "low_eq_db", "presence_eq_db", "gain_db"):
            if key in override:
                profile[key] = override[key]
    return profile


def _voice_profile_is_neutral(profile: dict[str, object]) -> bool:
    return (
        abs(float(profile.get("pitch_ratio", 1.0) or 1.0) - 1.0) < 0.0001
        and abs(float(profile.get("tempo_ratio", 1.0) or 1.0) - 1.0) < 0.0001
        and int(profile.get("highpass_hz", 118) or 118) == 118
        and int(profile.get("lowpass_hz", 3300) or 3300) == 3300
        and abs(float(profile.get("low_eq_db", 0.0) or 0.0)) < 0.0001
        and abs(float(profile.get("presence_eq_db", 0.0) or 0.0)) < 0.0001
        and abs(float(profile.get("gain_db", 0.0) or 0.0)) < 0.0001
    )


def _apply_voice_variant(src: Path, dest: Path, profile: dict[str, object]) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not src.exists():
        return False
    if _voice_profile_is_neutral(profile):
        _copy_audio(src, dest)
        return True
    pitch_ratio = max(0.95, min(1.05, float(profile.get("pitch_ratio", 1.0) or 1.0)))
    tempo_ratio = max(0.992, min(1.008, float(profile.get("tempo_ratio", 1.0) or 1.0)))
    atempo = max(0.5, min(2.0, (1.0 / pitch_ratio) * tempo_ratio))
    highpass_hz = int(max(95, min(145, float(profile.get("highpass_hz", 118) or 118))))
    lowpass_hz = int(max(3000, min(3600, float(profile.get("lowpass_hz", 3300) or 3300))))
    low_eq_db = round(float(profile.get("low_eq_db", 0.0) or 0.0), 2)
    presence_eq_db = round(float(profile.get("presence_eq_db", 0.0) or 0.0), 2)
    gain_db = round(float(profile.get("gain_db", 0.0) or 0.0), 2)
    filter_chain = ",".join(
        [
            f"asetrate=48000*{pitch_ratio:.6f}",
            "aresample=48000",
            f"atempo={atempo:.6f}",
            f"highpass=f={highpass_hz}",
            f"lowpass=f={lowpass_hz}",
            f"equalizer=f=180:t=q:w=1.2:g={low_eq_db:.2f}",
            f"equalizer=f=2400:t=q:w=1.0:g={presence_eq_db:.2f}",
            f"volume={gain_db:.2f}dB",
        ]
    )
    fd, temp_name = tempfile.mkstemp(prefix="tts-variant-", suffix=dest.suffix, dir=str(dest.parent))
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        result = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(src),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "48000",
                "-af",
                filter_chain,
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "2",
                str(temp_path),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and temp_path.exists() and temp_path.stat().st_size > 0:
            temp_path.replace(dest)
            return True
        return False
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _probe_duration_ms(path: Path) -> int:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return 0
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return 0
    try:
        return max(0, round(float(result.stdout.strip()) * 1000))
    except ValueError:
        return 0


def _probe_non_silent_duration_ms(
    path: Path,
    *,
    noise_db: float = -38.0,
    min_silence_s: float = 0.08,
) -> int:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not path.exists():
        return 0
    result = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-i",
            str(path),
            "-af",
            f"silencedetect=n={noise_db}dB:d={min_silence_s:.2f}",
            "-f",
            "null",
            "-",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode not in {0, 255}:
        return 0
    total_duration_ms = _probe_duration_ms(path)
    if total_duration_ms <= 0:
        return 0

    trailing_start_ms = 0
    silence_start_prefix = "silence_start:"
    for line in result.stderr.splitlines():
        token = line.strip()
        if silence_start_prefix not in token:
            continue
        raw_value = token.split(silence_start_prefix, 1)[1].strip().split()[0]
        try:
            silence_start_ms = max(0, round(float(raw_value) * 1000))
        except ValueError:
            continue
        if silence_start_ms >= total_duration_ms - max(1200, int(min_silence_s * 1000)):
            trailing_start_ms = silence_start_ms
    if trailing_start_ms <= 0:
        return total_duration_ms
    return max(0, min(total_duration_ms, trailing_start_ms))


def _probe_spoken_duration_ms(
    output_path: Path,
    *,
    raw_cache_path: Path | None = None,
    pre_pad_duration_ms: int | None = None,
) -> int:
    if raw_cache_path is not None and raw_cache_path.exists():
        detected_ms = _probe_non_silent_duration_ms(raw_cache_path)
        if detected_ms > 0:
            return detected_ms
        raw_duration_ms = _probe_duration_ms(raw_cache_path)
        if raw_duration_ms > 0:
            return max(0, raw_duration_ms - 220)
    if pre_pad_duration_ms is not None and pre_pad_duration_ms > 0:
        return max(0, int(pre_pad_duration_ms) - 220)
    detected_ms = _probe_non_silent_duration_ms(output_path)
    if detected_ms > 0:
        return detected_ms
    duration_ms = _probe_duration_ms(output_path)
    return max(0, duration_ms - max(220, TTS_TAIL_PAD_MS))


def _normalize_gender(value: object) -> str:
    token = str(value or "").strip().lower()
    if token in {"male", "man", "masculine", "boy"}:
        return "masculine"
    if token in {"female", "woman", "feminine", "girl"}:
        return "feminine"
    if token in {"neutral", "androgynous", "nonbinary", "non-binary"}:
        return "neutral"
    return "unspecified"


def _default_voice_for_gender(gender: str) -> str:
    return DEFAULT_VOICE_BY_GENDER.get(_normalize_gender(gender), DEFAULT_VOICE_BY_GENDER["unspecified"])


async def _synthesize_dialogue_item(
    index: int,
    scene: dict,
    scene_dialogue_index: int,
    dialogue: dict,
    scene_offset_ms: int,
    cast_character_meta: dict[str, dict[str, str]],
    cast_voice_map: dict[str, str],
    cast_index: dict[str, dict[str, object]],
    semaphore: asyncio.Semaphore,
) -> dict | None:
    text = (dialogue.get("text") or "").strip()
    if not text:
        return None

    output_path = AUDIO_DIR / f"dialogue-{index:03d}.mp3"
    raw_output_path = AUDIO_DIR / f"dialogue-{index:03d}-raw.mp3"
    speaker_id = str(dialogue.get("speaker_id") or "")
    speaker_meta = cast_character_meta.get(
        speaker_id,
        {"asset_id": "", "gender_presentation": "unspecified", "tts_speaker_id": ""},
    )
    cast_item = cast_index.get(speaker_id, {})
    gender_presentation = _normalize_gender(speaker_meta.get("gender_presentation"))
    bound_voice = str(speaker_meta.get("tts_speaker_id") or "").strip()
    dialogue_voice = str(dialogue.get("voice") or "").strip()
    cast_voice = str(cast_voice_map.get(speaker_id, "") or "").strip()
    if bound_voice:
        voice = bound_voice
        voice_source = "character_asset"
    elif dialogue_voice:
        voice = dialogue_voice
        voice_source = "dialogue"
    elif cast_voice:
        voice = cast_voice
        voice_source = "cast"
    else:
        voice = _default_voice_for_gender(gender_presentation)
        voice_source = "gender_default"

    variant_profile = _derive_voice_variant_profile(speaker_id, speaker_meta, cast_item, voice)
    speech_rate_pct = int(variant_profile.get("speech_rate_pct", BASE_TTS_RATE_PCT) or BASE_TTS_RATE_PCT)
    raw_cache_key = _tts_cache_key(text, voice, speech_rate_pct)
    raw_cache_path = TTS_CACHE_DIR / f"{raw_cache_key}.mp3"
    cache_key = _variant_cache_key(text, voice, variant_profile)
    cache_path = TTS_CACHE_DIR / f"{cache_key}.mp3"
    cache_hit = cache_path.exists() and cache_path.stat().st_size > 0
    if cache_hit:
        try:
            _copy_audio(cache_path, output_path)
            output_path.chmod(0o644)
        except OSError:
            cache_hit = False
    pre_pad_duration_ms = None
    if not cache_hit:
        raw_cache_hit = raw_cache_path.exists() and raw_cache_path.stat().st_size > 0
        if raw_cache_hit:
            _copy_audio(raw_cache_path, raw_output_path)
        else:
            async with semaphore:
                succeeded = await _synthesize_file(text, voice, raw_output_path, rate_pct=speech_rate_pct)
            if not succeeded:
                return None
            raw_output_path.chmod(0o644)
            TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            temp_raw_cache_path = TTS_CACHE_DIR / f"{raw_cache_key}.tmp{raw_output_path.suffix}"
            _copy_audio(raw_output_path, temp_raw_cache_path)
            temp_raw_cache_path.replace(raw_cache_path)
            raw_cache_path.chmod(0o644)
        if not _apply_voice_variant(raw_output_path, output_path, variant_profile):
            _copy_audio(raw_output_path, output_path)
        _normalize_audio_level(output_path)
        pre_pad_duration_ms = _probe_duration_ms(output_path)
        _pad_tts_timing(output_path)
        output_path.chmod(0o644)
        TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        temp_cache_path = TTS_CACHE_DIR / f"{cache_key}.tmp{output_path.suffix}"
        _copy_audio(output_path, temp_cache_path)
        temp_cache_path.replace(cache_path)
        cache_path.chmod(0o644)
    raw_output_path.unlink(missing_ok=True)

    actual_duration_ms = _probe_duration_ms(output_path)
    spoken_duration_ms = _probe_spoken_duration_ms(
        output_path,
        raw_cache_path=raw_cache_path,
        pre_pad_duration_ms=pre_pad_duration_ms,
    )
    start_ms = int(dialogue["start_ms"])
    end_ms = int(dialogue["end_ms"])
    return {
        "scene_id": scene["id"],
        "dialogue_index": index,
        "scene_dialogue_index": scene_dialogue_index,
        "speaker_id": speaker_id,
        "character_asset_id": speaker_meta.get("asset_id") or None,
        "gender_presentation": gender_presentation,
        "tts_speaker_id": voice,
        "voice_source": voice_source,
        "cache_key": cache_key,
        "cache_hit": cache_hit,
        "voice_variant": variant_profile,
        "path": str(output_path),
        "text": text,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "absolute_start_ms": scene_offset_ms + start_ms,
        "actual_duration_ms": actual_duration_ms,
        "actual_end_ms": start_ms + actual_duration_ms if actual_duration_ms else end_ms,
        "spoken_duration_ms": spoken_duration_ms,
        "spoken_end_ms": start_ms + spoken_duration_ms if spoken_duration_ms else end_ms,
    }


async def _synthesize_all_dialogues(
    story: dict,
    cast_character_meta: dict[str, dict[str, str]],
    cast_voice_map: dict[str, str],
    cast_index: dict[str, dict[str, object]],
    tts_workers: int,
) -> tuple[list[dict], int]:
    semaphore = asyncio.Semaphore(max(1, tts_workers))
    tasks = []
    index = 0
    scene_offset_ms = 0
    expected_count = 0
    for scene in story.get("scenes", []):
        for scene_dialogue_index, dialogue in enumerate(scene.get("dialogues", [])):
            if not str(dialogue.get("text") or "").strip():
                continue
            expected_count += 1
            tasks.append(
                asyncio.create_task(
                    _synthesize_dialogue_item(
                        index,
                        scene,
                        scene_dialogue_index,
                        dialogue,
                        scene_offset_ms,
                        cast_character_meta,
                        cast_voice_map,
                        cast_index,
                        semaphore,
                    )
                )
            )
            index += 1
        scene_offset_ms += int(scene.get("duration_ms", 0) or 0)
    results = await asyncio.gather(*tasks) if tasks else []
    items = [item for item in results if item is not None]
    items.sort(key=lambda item: int(item.get("dialogue_index", 0)))
    return items, expected_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Optionally synthesize dialogue audio.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--require-tts", action="store_true")
    parser.add_argument("--tts-workers", type=int, default=0)
    args = parser.parse_args()

    ensure_runtime_dirs()
    TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    story = read_json(args.input)
    if not story.get("video", {}).get("tts_enabled"):
        write_json(TMP_DIR / "dialogue_audio_manifest.json", {"items": []})
        print("tts disabled")
        return 0

    character_index = manifest_index("characters")
    cast_index = {
        str(item.get("id")): item
        for item in story.get("cast", [])
        if item.get("id")
    }
    cast_voice_map = {
        str(item.get("id")): str(item.get("voice") or "")
        for item in story.get("cast", [])
        if item.get("id")
    }
    cast_character_meta: dict[str, dict[str, object]] = {}
    for actor_id, cast_item in cast_index.items():
        asset_id = str(cast_item.get("asset_id") or "")
        character_meta = character_index.get(asset_id, {}) if asset_id else {}
        gender_presentation = _normalize_gender(
            character_meta.get("gender_presentation") or cast_item.get("gender_presentation")
        )
        tts_speaker_id = str(character_meta.get("tts_speaker_id") or "").strip()
        merged_meta: dict[str, object] = dict(character_meta)
        merged_meta.update(
            {
            "asset_id": asset_id,
            "gender_presentation": gender_presentation,
            "tts_speaker_id": tts_speaker_id,
            }
        )
        cast_character_meta[actor_id] = merged_meta
    cpu_workers = os.cpu_count() or 4
    default_tts_workers = min(12, max(4, cpu_workers * 2))
    tts_workers = max(1, int(args.tts_workers or story.get("video", {}).get("tts_workers") or default_tts_workers))
    items, expected_count = asyncio.run(
        _synthesize_all_dialogues(story, cast_character_meta, cast_voice_map, cast_index, tts_workers)
    )

    if args.require_tts and len(items) != expected_count:
        print(f"tts requested but only synthesized {len(items)} of {expected_count} dialogue items")
        return 1
    if len(items) != expected_count:
        print(f"warning: synthesized {len(items)} of {expected_count} dialogue items")

    write_json(TMP_DIR / "dialogue_audio_manifest.json", {"items": items})
    print(TMP_DIR / "dialogue_audio_manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
