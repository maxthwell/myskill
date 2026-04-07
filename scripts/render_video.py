#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import os
import shutil
import subprocess
import sys
import time
import wave
from pathlib import Path

from common.io import FRAMES_DIR, ROOT_DIR, TMP_DIR, ensure_runtime_dirs, read_json, write_json
from common.panda_renderer import PandaSceneRenderer
from common.panda_true3d_renderer import PandaTrue3DRenderer
from common.pygame_renderer import PygameSceneRenderer


def _delegate_to_desktop_user_if_needed(prefer_gpu: bool) -> None:
    if not prefer_gpu:
        return
    if os.environ.get("PANDA_GPU_DELEGATED") == "1":
        return
    if os.geteuid() != 0:
        return
    if not Path("/mnt/wslg/runtime-dir").exists():
        return

    target_user = os.environ.get("PANDA_GPU_USER", "bob")
    command = [
        "runuser",
        "-u",
        target_user,
        "--",
        "env",
        "PANDA_GPU_DELEGATED=1",
        f"DISPLAY={os.environ.get('DISPLAY', ':0')}",
        f"XDG_RUNTIME_DIR={os.environ.get('XDG_RUNTIME_DIR', '/mnt/wslg/runtime-dir')}",
        f"WAYLAND_DISPLAY={os.environ.get('WAYLAND_DISPLAY', 'wayland-0')}",
        f"PULSE_SERVER={os.environ.get('PULSE_SERVER', 'unix:/mnt/wslg/PulseServer')}",
        "python3",
        *sys.argv,
    ]
    raise SystemExit(subprocess.call(command))


def _desktop_user_command(command: list[str], prefer_gpu: bool) -> list[str]:
    if not prefer_gpu:
        return command
    if os.environ.get("PANDA_GPU_DELEGATED") == "1":
        return command
    if os.geteuid() != 0:
        return command
    if not Path("/mnt/wslg/runtime-dir").exists():
        return command
    target_user = os.environ.get("PANDA_GPU_USER", "bob")
    return [
        "runuser",
        "-u",
        target_user,
        "--",
        "env",
        "PANDA_GPU_DELEGATED=1",
        f"DISPLAY={os.environ.get('DISPLAY', ':0')}",
        f"XDG_RUNTIME_DIR={os.environ.get('XDG_RUNTIME_DIR', '/mnt/wslg/runtime-dir')}",
        f"WAYLAND_DISPLAY={os.environ.get('WAYLAND_DISPLAY', 'wayland-0')}",
        f"PULSE_SERVER={os.environ.get('PULSE_SERVER', 'unix:/mnt/wslg/PulseServer')}",
        f"PANDAVIDEO_TMP_DIR={os.environ.get('PANDAVIDEO_TMP_DIR', str(TMP_DIR))}",
        *command,
    ]


def _clear_output(*, preserve_dialogue_manifest: bool = False) -> None:
    if FRAMES_DIR.exists():
        for item in FRAMES_DIR.glob("*.png"):
            try:
                item.unlink()
            except FileNotFoundError:
                pass
    video_only = TMP_DIR / "video_only.mp4"
    try:
        video_only.unlink()
    except FileNotFoundError:
        pass
    if not preserve_dialogue_manifest:
        audio_manifest = TMP_DIR / "dialogue_audio_manifest.json"
        try:
            audio_manifest.unlink()
        except FileNotFoundError:
            pass
    scene_jobs_dir = TMP_DIR / "scene_jobs"
    if scene_jobs_dir.exists():
        for item in scene_jobs_dir.iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink()
            except FileNotFoundError:
                pass
    scene_audio_dir = TMP_DIR / "scene_audio"
    if scene_audio_dir.exists():
        shutil.rmtree(scene_audio_dir, ignore_errors=True)


def _scene_frame_count(scene: dict, fps: int) -> int:
    duration_ms = int(scene.get("duration_ms", 0) or 0)
    return max(1, round(duration_ms * fps / 1000))


def _scene_offsets(story: dict) -> dict[str, int]:
    offsets: dict[str, int] = {}
    cursor = 0
    for scene in story.get("scenes", []):
        scene_id = str(scene.get("id") or "")
        if scene_id:
            offsets[scene_id] = cursor
        cursor += int(scene.get("duration_ms", 0) or 0)
    return offsets


def _timings_path(output_path: Path) -> Path:
    if output_path.suffix:
        return output_path.with_suffix(".timings.json")
    return output_path.with_name(f"{output_path.name}.timings.json")


EFFECT_SFX_MAP = {
    "dragon-palm": {
        "path": str((ROOT_DIR / "assets" / "audio" / "031_26_赤手空拳打斗的声音_爱给网_aigei_com.mp3").resolve()),
        "offset_ms": 40,
        "volume": 1.85,
    },
    "sword-arc": {
        "path": str((ROOT_DIR / "assets" / "audio" / "刀剑、金属碰撞（带回音）_爱给网_aigei_com.mp3").resolve()),
        "offset_ms": 20,
        "volume": 1.95,
    },
    "thunder-strike": {
        "path": str((ROOT_DIR / "assets" / "audio" / "音效 爆炸 爆破 爆发 战斗_爱给网_aigei_com.mp3").resolve()),
        "offset_ms": 30,
        "volume": 2.25,
    },
}


def _apply_tts_timing(story: dict) -> dict:
    audio_manifest_path = TMP_DIR / "dialogue_audio_manifest.json"
    if not audio_manifest_path.exists():
        return story
    audio_manifest = read_json(audio_manifest_path)
    items = audio_manifest.get("items", [])
    if not items:
        return story

    scenes_by_id = {str(scene.get("id") or ""): scene for scene in story.get("scenes", [])}
    items_by_scene: dict[str, list[dict]] = {}
    for item in items:
        scene_id = str(item.get("scene_id") or "")
        if not scene_id:
            continue
        items_by_scene.setdefault(scene_id, []).append(item)

    for item in items:
        scene = scenes_by_id.get(str(item.get("scene_id") or ""))
        if not scene:
            continue
        dialogues = scene.get("dialogues", [])
        try:
            scene_dialogue_index = int(item.get("scene_dialogue_index"))
        except (TypeError, ValueError):
            scene_dialogue_index = -1
        if not (0 <= scene_dialogue_index < len(dialogues)):
            continue

        dialogue = dialogues[scene_dialogue_index]
        dialogue.setdefault("_original_start_ms", int(dialogue.get("start_ms", 0) or 0))
        dialogue.setdefault("_original_end_ms", int(dialogue.get("end_ms", 0) or 0))
        for beat in scene.get("beats", []):
            beat.setdefault("_original_start_ms", int(beat.get("start_ms", 0) or 0))
            beat.setdefault("_original_end_ms", int(beat.get("end_ms", 0) or 0))

    dialogue_gap_ms = 120
    scene_tail_ms = 360
    for scene_id, scene_items in items_by_scene.items():
        scene = scenes_by_id.get(scene_id)
        if not scene:
            continue
        dialogues = scene.get("dialogues", [])
        scene_items.sort(key=lambda item: int(item.get("scene_dialogue_index", -1)))
        previous_end_ms = -dialogue_gap_ms
        for item in scene_items:
            raw_scene_dialogue_index = item.get("scene_dialogue_index", -1)
            scene_dialogue_index = int(raw_scene_dialogue_index if raw_scene_dialogue_index is not None else -1)
            if not (0 <= scene_dialogue_index < len(dialogues)):
                continue
            dialogue = dialogues[scene_dialogue_index]
            original_start_ms = int(dialogue.get("_original_start_ms", dialogue.get("start_ms", 0)) or 0)
            original_end_ms = int(dialogue.get("_original_end_ms", dialogue.get("end_ms", 0)) or 0)
            actual_duration_ms = int(item.get("actual_duration_ms", 0) or max(1, original_end_ms - original_start_ms))
            spoken_duration_ms = int(item.get("spoken_duration_ms", 0) or actual_duration_ms or max(1, original_end_ms - original_start_ms))
            spoken_duration_ms = max(1, min(actual_duration_ms, spoken_duration_ms))
            scheduled_start_ms = max(original_start_ms, previous_end_ms + dialogue_gap_ms)
            scheduled_end_ms = scheduled_start_ms + actual_duration_ms
            scheduled_spoken_end_ms = scheduled_start_ms + spoken_duration_ms

            dialogue["start_ms"] = scheduled_start_ms
            dialogue["end_ms"] = scheduled_spoken_end_ms
            item["scheduled_start_ms"] = scheduled_start_ms
            item["scheduled_end_ms"] = scheduled_end_ms
            item["scheduled_spoken_end_ms"] = scheduled_spoken_end_ms

            for beat in scene.get("beats", []):
                if str(beat.get("actor_id") or "") != str(dialogue.get("speaker_id") or ""):
                    continue
                if int(beat.get("_original_start_ms", beat.get("start_ms", -1)) or -1) != original_start_ms:
                    continue
                if int(beat.get("_original_end_ms", beat.get("end_ms", -1)) or -1) != original_end_ms:
                    continue
                beat["start_ms"] = scheduled_start_ms
                beat["end_ms"] = scheduled_spoken_end_ms

            previous_end_ms = scheduled_end_ms

        if previous_end_ms >= 0:
            scene["duration_ms"] = max(int(scene.get("duration_ms", 0) or 0), previous_end_ms + scene_tail_ms)

    adjusted_scene_offsets = _scene_offsets(story)
    for item in items:
        scene_id = str(item.get("scene_id") or "")
        if item.get("scheduled_start_ms") is None:
            continue
        scene_offset = adjusted_scene_offsets.get(scene_id, 0)
        scheduled_start_ms = int(item.get("scheduled_start_ms") or 0)
        scheduled_end_ms = int(item.get("scheduled_end_ms") or scheduled_start_ms)
        scheduled_spoken_end_ms = int(item.get("scheduled_spoken_end_ms") or scheduled_end_ms)
        item["scheduled_absolute_start_ms"] = scene_offset + scheduled_start_ms
        item["scheduled_absolute_end_ms"] = scene_offset + scheduled_end_ms
        item["scheduled_absolute_spoken_end_ms"] = scene_offset + scheduled_spoken_end_ms

    write_json(audio_manifest_path, audio_manifest)
    return story


def _open_ffmpeg_stream(story: dict, output_path: Path):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to encode the final video")
    video = story["video"]
    fps = int(video["fps"])
    renderer_kind = str(video.get("renderer") or "pygame_2d")
    is_fast_renderer = renderer_kind not in {"true_3d", "panda_legacy_2_5d", "panda_card_fast"}
    requested_preset = video.get("encoder_preset")
    requested_crf = video.get("crf")
    codec = str(video.get("video_codec") or "libx264")
    preset = str(requested_preset or ("ultrafast" if is_fast_renderer else "medium"))
    crf = str(requested_crf if requested_crf is not None else (26 if is_fast_renderer else 23))
    if is_fast_renderer and preset in {"medium", "fast"}:
        preset = "ultrafast"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{int(story['video']['width'])}x{int(story['video']['height'])}",
        "-r",
        str(fps),
        "-i",
        "-",
    ]
    if codec == "mpeg4":
        qscale = str(video.get("mpeg4_qscale") or 5)
        command.extend(
            [
                "-c:v",
                "mpeg4",
                "-q:v",
                qscale,
                "-pix_fmt",
                "yuv420p",
            ]
        )
    elif codec == "libx264rgb":
        command.extend(
            [
                "-c:v",
                "libx264rgb",
                "-preset",
                preset,
                "-crf",
                crf,
            ]
        )
    else:
        command.extend(
            [
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-preset",
                preset,
                "-crf",
                crf,
            ]
        )
    command.append(str(output_path))
    return subprocess.Popen(command, stdin=subprocess.PIPE)


def _scene_job_story(story: dict, scene_index: int) -> dict:
    scene = dict(story["scenes"][scene_index])
    job_story = dict(story)
    job_story["scenes"] = [scene]
    return job_story


def _renderer_cls(renderer_kind: str):
    normalized = str(renderer_kind or "").strip().lower()
    if normalized == "true_3d":
        return PandaTrue3DRenderer
    if normalized == "panda_card_fast":
        return PandaTrue3DRenderer
    if normalized == "panda_legacy_2_5d":
        return PandaSceneRenderer
    return PygameSceneRenderer


def _render_scene_segment_serial(story: dict, scene_index: int, output_path: Path, prefer_gpu: bool) -> None:
    renderer_kind = str(story.get("video", {}).get("renderer") or "pygame_2d")
    renderer_cls = _renderer_cls(renderer_kind)
    renderer = renderer_cls(story, prefer_gpu=prefer_gpu)
    ffmpeg_proc = _open_ffmpeg_stream(story, output_path)
    fps = int(story["video"]["fps"])
    scene = story["scenes"][scene_index]
    frame_count = _scene_frame_count(scene, fps)
    try:
        for scene_frame_index in range(frame_count):
            time_ms = round(scene_frame_index * 1000 / fps)
            frame_bytes = renderer.capture_scene_frame(scene, time_ms, raw_rgb=True)
            assert ffmpeg_proc.stdin is not None
            ffmpeg_proc.stdin.write(frame_bytes)
    finally:
        if ffmpeg_proc.stdin is not None:
            ffmpeg_proc.stdin.close()
        return_code = ffmpeg_proc.wait()
        renderer.close()
    if return_code != 0:
        raise RuntimeError(f"ffmpeg exited with code {return_code}")


def _render_scene_segment_subprocess(story_path: Path, output_path: Path, prefer_gpu: bool, tts_enabled: bool) -> None:
    job_stem = story_path.stem
    job_tmp_dir = TMP_DIR / "scene_jobs" / f"{job_stem}-tmp"
    job_tmp_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PANDAVIDEO_TMP_DIR"] = str(job_tmp_dir)

    if tts_enabled:
        subprocess.run(
            [
                sys.executable,
                str((Path(__file__).resolve().parent / "synthesize_tts.py").resolve()),
                "--input",
                str(story_path),
                "--require-tts",
            ],
            check=True,
            env=env,
        )

    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--input",
        str(story_path),
        "--output",
        str(output_path),
        "--no-parallel",
    ]
    if not tts_enabled:
        command.extend(["--video-only", "--skip-tts-timing"])
    if not prefer_gpu:
        command.append("--cpu")
    subprocess.run(command, check=True, env=env)


def _concat_scene_segments(story: dict, segment_paths: list[Path], output_path: Path) -> None:
    if len(segment_paths) == 1:
        shutil.copy2(segment_paths[0], output_path)
        return
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to encode the final video")
    transition_s = 0.18
    durations = [_probe_media_duration(path) for path in segment_paths]
    valid_durations = [duration for duration in durations if duration > 0.0]
    if len(valid_durations) != len(segment_paths):
        concat_list = TMP_DIR / "scene_jobs" / "concat.txt"
        concat_list.parent.mkdir(parents=True, exist_ok=True)
        concat_list.write_text(
            "".join(f"file '{path.resolve().as_posix()}'\n" for path in segment_paths),
            encoding="utf-8",
        )
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-c",
                "copy",
                str(output_path),
            ],
            check=True,
        )
        return

    video = story.get("video", {})
    codec = str(video.get("video_codec") or "libx264")
    preset = str(video.get("encoder_preset") or "ultrafast")
    crf = str(video.get("crf") if video.get("crf") is not None else 26)
    command = [ffmpeg, "-y"]
    for path in segment_paths:
        command.extend(["-i", str(path)])

    filter_parts: list[str] = []
    concat_inputs: list[str] = []
    for index, duration in enumerate(durations):
        fade_duration = min(transition_s, max(0.08, duration * 0.08))
        fade_out_start = max(0.0, duration - fade_duration)
        label = f"[vf{index}]"
        filter_parts.append(
            f"[{index}:v]fade=t=in:st=0:d={fade_duration:.3f},fade=t=out:st={fade_out_start:.3f}:d={fade_duration:.3f}{label}"
        )
        concat_inputs.append(label)

    filter_parts.append("".join(concat_inputs) + f"concat=n={len(segment_paths)}:v=1:a=0[vout]")
    command.extend(
        [
            "-filter_complex",
            ";".join(filter_parts),
            "-map",
            "[vout]",
            "-an",
        ]
    )
    if codec == "mpeg4":
        command.extend(
            [
                "-c:v",
                "mpeg4",
                "-q:v",
                str(video.get("mpeg4_qscale") or 4),
            ]
        )
    elif codec == "libx264rgb":
        command.extend(
            [
                "-c:v",
                "libx264rgb",
                "-preset",
                preset,
                "-crf",
                crf,
            ]
        )
    else:
        command.extend(
            [
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-preset",
                preset,
                "-crf",
                crf,
            ]
        )
    command.append(str(output_path))
    subprocess.run(command, check=True)


def _probe_audio_stats(audio_path: Path) -> tuple[float | None, float | None]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not audio_path.exists():
        return None, None
    result = subprocess.run(
        [ffmpeg, "-i", str(audio_path), "-af", "volumedetect", "-f", "null", "-"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    mean_volume = None
    max_volume = None
    for line in result.stderr.splitlines():
        if "mean_volume:" in line:
            try:
                mean_volume = float(line.split("mean_volume:", 1)[1].split(" dB", 1)[0].strip())
            except ValueError:
                pass
        elif "max_volume:" in line:
            try:
                max_volume = float(line.split("max_volume:", 1)[1].split(" dB", 1)[0].strip())
            except ValueError:
                pass
    return mean_volume, max_volume


def _probe_media_duration(media_path: Path) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe or not media_path.exists():
        return 0.0
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(media_path),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        return max(0.0, float(result.stdout.strip()))
    except ValueError:
        return 0.0


def _build_scene_audio_tracks(story: dict, items: list[dict]) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to encode the final audio")

    scene_audio_dir = TMP_DIR / "scene_audio"
    if scene_audio_dir.exists():
        shutil.rmtree(scene_audio_dir, ignore_errors=True)
    scene_audio_dir.mkdir(parents=True, exist_ok=True)

    items_by_scene: dict[str, list[dict]] = {}
    for item in items:
        scene_id = str(item.get("scene_id") or "")
        if scene_id:
            items_by_scene.setdefault(scene_id, []).append(item)

    raw_tracks: list[Path] = []
    scene_stats: list[tuple[float | None, float | None]] = []
    for scene in story.get("scenes", []):
        scene_id = str(scene.get("id") or "")
        scene_duration_ms = int(scene.get("duration_ms", 0) or 0)
        scene_duration_s = max(scene_duration_ms / 1000.0, 0.05)
        scene_items = sorted(
            items_by_scene.get(scene_id, []),
            key=lambda item: int(
                item.get("scheduled_start_ms")
                or item.get("start_ms")
                or 0
            ),
        )
        raw_track = scene_audio_dir / f"{scene_id}.wav"
        raw_tracks.append(raw_track)

        if not scene_items:
            subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "anullsrc=channel_layout=mono:sample_rate=48000",
                    "-t",
                    f"{scene_duration_s:.3f}",
                    "-c:a",
                    "pcm_s16le",
                    str(raw_track),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            scene_stats.append((None, None))
            continue

        command = [ffmpeg, "-y"]
        command.extend(
            [
                "-f",
                "lavfi",
                "-t",
                f"{scene_duration_s:.3f}",
                "-i",
                "anullsrc=channel_layout=mono:sample_rate=48000",
            ]
        )
        filter_parts: list[str] = []
        mix_inputs: list[str] = ["[0:a]"]
        for index, item in enumerate(scene_items, start=1):
            command.extend(["-i", str(item["path"])])
            delay = int(item.get("scheduled_start_ms") or item.get("start_ms") or 0)
            end_ms_raw = item.get("scheduled_end_ms", item.get("end_ms"))
            end_ms = int(end_ms_raw) if end_ms_raw is not None else scene_duration_ms
            duration_s = max(0.05, (max(delay + 1, min(scene_duration_ms, end_ms)) - delay) / 1000.0)
            filter_chain = [f"[{index}:a]aresample=48000"]
            if item.get("loop"):
                filter_chain.append(f"apad=whole_dur={duration_s:.3f}")
            filter_chain.append(f"atrim=0:{duration_s:.3f}")
            volume = float(item.get("volume", 1.0) or 1.0)
            is_dialogue_item = (
                item.get("kind") == "dialogue"
                or item.get("speaker_id") is not None
                or item.get("scene_dialogue_index") is not None
            )
            is_effect_sfx_item = item.get("kind") in {"sfx", "effect-sfx"}
            if is_dialogue_item:
                # Older ffmpeg amix builds average by input count, which can bury dialogue.
                # Compensate dialogue tracks by the scene mix width so speech remains audible.
                volume *= max(1.0, float(len(scene_items)))
            elif is_effect_sfx_item:
                # Give scene effects and hand-authored SFX enough headroom to survive the scene-wide amix averaging.
                volume *= max(1.0, float(len(scene_items)) * 0.9)
            if abs(volume - 1.0) >= 0.001:
                filter_chain.append(f"volume={volume:.3f}")
            filter_chain.append(f"adelay={delay}|{delay}")
            filter_chain.append(f"asetpts=N/SR/TB[a{index}]")
            filter_parts.append(",".join(filter_chain))
            mix_inputs.append(f"[a{index}]")
        filter_parts.append(
            f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)},"
            f"atrim=0:{scene_duration_s:.3f},asetpts=N/SR/TB[aout]"
        )
        command.extend(
            [
                "-filter_complex",
                ";".join(filter_parts),
                "-map",
                "[aout]",
                "-c:a",
                "pcm_s16le",
                str(raw_track),
            ]
        )
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        scene_stats.append(_probe_audio_stats(raw_track))

    reference_mean = None
    reference_max = None
    for mean_volume, max_volume in reversed(scene_stats):
        if mean_volume is not None and max_volume is not None:
            reference_mean = mean_volume
            reference_max = max_volume
            break
    if reference_mean is None or reference_max is None:
        reference_mean = -16.0
        reference_max = -1.0

    normalized_tracks: list[Path] = []
    for raw_track, (mean_volume, max_volume) in zip(raw_tracks, scene_stats):
        normalized_track = scene_audio_dir / f"{raw_track.stem}-norm.wav"
        normalized_tracks.append(normalized_track)
        filters: list[str] = []
        if mean_volume is not None and max_volume is not None:
            gain_by_mean = reference_mean - mean_volume
            gain_by_peak = reference_max - max_volume
            gain_db = min(gain_by_mean, gain_by_peak)
            if abs(gain_db) >= 0.1:
                filters.append(f"volume={gain_db:.3f}dB")
                filters.append("alimiter=limit=0.97")
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(raw_track),
                *(["-af", ",".join(filters)] if filters else []),
                "-ac",
                "1",
                "-ar",
                "48000",
                "-c:a",
                "pcm_s16le",
                str(normalized_track),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    final_audio = scene_audio_dir / "story_audio.wav"
    with wave.open(str(normalized_tracks[0]), "rb") as first_wav:
        params = first_wav.getparams()
        format_signature = (params.nchannels, params.sampwidth, params.framerate, params.comptype, params.compname)
        with wave.open(str(final_audio), "wb") as out_wav:
            out_wav.setparams(params)
            out_wav.writeframes(first_wav.readframes(first_wav.getnframes()))
            for track in normalized_tracks[1:]:
                with wave.open(str(track), "rb") as in_wav:
                    in_params = in_wav.getparams()
                    in_signature = (
                        in_params.nchannels,
                        in_params.sampwidth,
                        in_params.framerate,
                        in_params.comptype,
                        in_params.compname,
                    )
                    if in_signature != format_signature:
                        raise RuntimeError(f"incompatible scene audio format: {track}")
                    out_wav.writeframes(in_wav.readframes(in_wav.getnframes()))
    return final_audio


def _story_bgm_items(story: dict) -> list[dict]:
    scene_offsets = _scene_offsets(story)
    items: list[dict] = []
    for scene in story.get("scenes", []):
        scene_id = str(scene.get("id") or "")
        scene_duration_ms = int(scene.get("duration_ms", 0) or 0)
        scene_start_ms = int(scene_offsets.get(scene_id, 0) or 0)
        scene_audio = scene.get("audio") or {}
        if not isinstance(scene_audio, dict):
            continue
        bgm = scene_audio.get("bgm")
        if not isinstance(bgm, dict) or not bgm.get("asset_path"):
            continue
        start_ms = scene_start_ms + int(bgm.get("start_ms", 0) or 0)
        if bool(bgm.get("loop", True)):
            end_ms = scene_start_ms + scene_duration_ms
        else:
            end_ms = scene_start_ms + int(bgm.get("end_ms", scene_duration_ms) or scene_duration_ms)
        if end_ms <= start_ms:
            continue
        item = {
            "path": str(bgm["asset_path"]),
            "start_ms": start_ms,
            "end_ms": end_ms,
            "volume": float(bgm.get("volume", 1.0) or 1.0),
            "loop": bool(bgm.get("loop", True)),
            "kind": "bgm",
        }
        previous = items[-1] if items else None
        if (
            previous
            and previous.get("path") == item["path"]
            and bool(previous.get("loop")) == item["loop"]
            and abs(float(previous.get("volume", 1.0)) - float(item["volume"])) < 0.001
            and int(previous.get("end_ms", -1)) == start_ms
        ):
            previous["end_ms"] = end_ms
        else:
            items.append(item)
    return [item for item in items if Path(str(item.get("path") or "")).exists()]


def _effect_sfx_items(scene: dict) -> list[dict]:
    scene_id = str(scene.get("id") or "")
    scene_duration_ms = int(scene.get("duration_ms", 0) or 0)
    items: list[dict] = []
    seen: set[tuple[str, int]] = set()
    for beat in scene.get("beats", []):
        if not isinstance(beat, dict):
            continue
        effect_id = str(beat.get("effect") or beat.get("motion") or "")
        spec = EFFECT_SFX_MAP.get(effect_id)
        if spec is None:
            continue
        start_ms = int(beat.get("start_ms", 0) or 0) + int(spec["offset_ms"])
        start_ms = max(0, min(scene_duration_ms, start_ms))
        dedupe_key = (effect_id, start_ms)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        items.append(
            {
                "scene_id": scene_id,
                "path": str(spec["path"]),
                "start_ms": start_ms,
                "volume": float(spec["volume"]),
                "loop": False,
                "kind": "effect-sfx",
            }
        )
    return [item for item in items if Path(str(item.get("path") or "")).exists()]


def _story_audio_items(story: dict, tts_items: list[dict]) -> list[dict]:
    items = [dict(item) for item in tts_items]
    for scene in story.get("scenes", []):
        scene_id = str(scene.get("id") or "")
        scene_audio = scene.get("audio") or {}
        if not isinstance(scene_audio, dict):
            continue
        for cue in scene_audio.get("sfx", []):
            if not isinstance(cue, dict) or not cue.get("asset_path"):
                continue
            item = {
                "scene_id": scene_id,
                "path": str(cue["asset_path"]),
                "start_ms": int(cue.get("start_ms", 0) or 0),
                "volume": float(cue.get("volume", 1.0) or 1.0),
                "loop": bool(cue.get("loop", False)),
                "kind": "sfx",
            }
            if cue.get("end_ms") is not None:
                item["end_ms"] = int(cue.get("end_ms") or 0)
            items.append(item)
        items.extend(_effect_sfx_items(scene))
    return [item for item in items if Path(str(item.get("path") or "")).exists()]


def _mix_story_bgm(base_audio: Path, bgm_items: list[dict]) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not base_audio.exists() or not bgm_items:
        return base_audio

    mixed_audio = base_audio.with_name(f"{base_audio.stem}-with-bgm{base_audio.suffix}")
    total_duration_s = max(0.05, _probe_media_duration(base_audio))
    command = [ffmpeg, "-y", "-i", str(base_audio)]
    filter_parts: list[str] = []
    mix_width = max(1, 1 + len(bgm_items))
    base_chain = ["[0:a]aresample=48000"]
    if mix_width > 1:
        base_chain.append(f"volume={float(mix_width):.3f}")
    base_chain.append("asetpts=N/SR/TB[base0]")
    filter_parts.append(",".join(base_chain))
    mix_inputs: list[str] = ["[base0]"]

    for index, item in enumerate(bgm_items, start=1):
        if item.get("loop", True):
            command.extend(["-stream_loop", "-1"])
        command.extend(["-i", str(item["path"])])
        start_ms = int(item.get("start_ms", 0) or 0)
        end_ms = int(item.get("end_ms", start_ms) or start_ms)
        duration_s = max(0.05, (end_ms - start_ms) / 1000.0)
        filter_chain = [f"[{index}:a]aresample=48000", f"atrim=0:{duration_s:.3f}"]
        volume = float(item.get("volume", 1.0) or 1.0) * float(mix_width)
        if abs(volume - 1.0) >= 0.001:
            filter_chain.append(f"volume={volume:.3f}")
        if start_ms > 0:
            filter_chain.append(f"adelay={start_ms}|{start_ms}")
        filter_chain.append(f"asetpts=N/SR/TB[a{index}]")
        filter_parts.append(",".join(filter_chain))
        mix_inputs.append(f"[a{index}]")

    filter_parts.append(
        f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=longest,"
        f"atrim=0:{total_duration_s:.3f},asetpts=N/SR/TB[aout]"
    )
    command.extend(
        [
            "-filter_complex",
            ";".join(filter_parts),
            "-map",
            "[aout]",
            "-ac",
            "1",
            "-ar",
            "48000",
            "-c:a",
            "pcm_s16le",
            str(mixed_audio),
        ]
    )
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return mixed_audio


def _render_video_stream(story: dict, prefer_gpu: bool, video_output_path: Path | None = None) -> tuple[int, str, dict]:
    fps = int(story["video"]["fps"])
    renderer_kind = str(story.get("video", {}).get("renderer") or "pygame_2d")
    renderer_cls = _renderer_cls(renderer_kind)
    renderer = renderer_cls(story, prefer_gpu=prefer_gpu)
    video_only = video_output_path or (TMP_DIR / "video_only.mp4")
    ffmpeg_proc = _open_ffmpeg_stream(story, video_only)
    frame_index = 0
    scene_timings: list[dict[str, float | int | str]] = []
    render_started = time.perf_counter()
    try:
        for scene in story.get("scenes", []):
            frame_count = _scene_frame_count(scene, fps)
            scene_started = time.perf_counter()
            for scene_frame_index in range(frame_count):
                time_ms = round(scene_frame_index * 1000 / fps)
                frame_bytes = renderer.capture_scene_frame(scene, time_ms, raw_rgb=True)
                assert ffmpeg_proc.stdin is not None
                ffmpeg_proc.stdin.write(frame_bytes)
                frame_index += 1
            scene_timings.append(
                {
                    "scene_id": str(scene.get("id") or ""),
                    "frame_count": frame_count,
                    "render_s": round(time.perf_counter() - scene_started, 4),
                }
            )
    finally:
        if ffmpeg_proc.stdin is not None:
            ffmpeg_proc.stdin.close()
        return_code = ffmpeg_proc.wait()
        renderer.close()
    if return_code != 0:
        raise RuntimeError(f"ffmpeg exited with code {return_code}")
    timings = {
        "video_render_s": round(time.perf_counter() - render_started, 4),
        "scene_render_s": scene_timings,
    }
    return frame_index, renderer.pipe_name, timings


def _render_video_stream_parallel(story: dict, input_path: Path, prefer_gpu: bool, scene_workers: int) -> tuple[int, str, dict]:
    scene_jobs_dir = TMP_DIR / "scene_jobs"
    scene_jobs_dir.mkdir(parents=True, exist_ok=True)
    segment_paths = [scene_jobs_dir / f"scene-{index:03d}.mp4" for index, _ in enumerate(story.get("scenes", []))]
    job_story_paths = [scene_jobs_dir / f"scene-{index:03d}.json" for index, _ in enumerate(story.get("scenes", []))]
    pipe_name = "parallel-scene-render"
    parallel_started = time.perf_counter()
    for scene_index, job_story_path in enumerate(job_story_paths):
        write_json(job_story_path, _scene_job_story(story, scene_index))
    tts_enabled = bool(story.get("video", {}).get("tts_enabled"))
    if len(segment_paths) == 1:
        if tts_enabled:
            _render_scene_segment_subprocess(job_story_paths[0], segment_paths[0], prefer_gpu=prefer_gpu, tts_enabled=True)
        else:
            _render_scene_segment_serial(story, 0, segment_paths[0], prefer_gpu=prefer_gpu)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=scene_workers) as executor:
            futures = [
                executor.submit(
                    _render_scene_segment_subprocess,
                    job_story_path,
                    segment_path,
                    prefer_gpu,
                    tts_enabled,
                )
                for job_story_path, segment_path in zip(job_story_paths, segment_paths)
            ]
            for future in concurrent.futures.as_completed(futures):
                future.result()
    video_only = TMP_DIR / "video_only.mp4"
    concat_started = time.perf_counter()
    _concat_scene_segments(story, segment_paths, video_only)
    concat_s = time.perf_counter() - concat_started
    total_frames = sum(_scene_frame_count(scene, int(story["video"]["fps"])) for scene in story.get("scenes", []))
    scene_timings: list[dict[str, Any]] = []
    for segment_path in segment_paths:
        timing_path = _timings_path(segment_path)
        if timing_path.exists():
            scene_timings.append(read_json(timing_path))
    timings = {
        "parallel_render_wall_s": round(time.perf_counter() - parallel_started, 4),
        "concat_s": round(concat_s, 4),
        "scene_jobs": scene_timings,
    }
    return total_frames, pipe_name, timings


def _mux_audio(story: dict, output_path: Path) -> dict:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to encode the final video")
    video_only = TMP_DIR / "video_only.mp4"
    audio_manifest_path = TMP_DIR / "dialogue_audio_manifest.json"
    items: list[dict] = []
    if audio_manifest_path.exists():
        audio_manifest = read_json(audio_manifest_path)
        items = audio_manifest.get("items", [])
    items = _story_audio_items(story, items)
    bgm_items = _story_bgm_items(story)
    if not items and not bgm_items:
        shutil.copy2(video_only, output_path)
        return {"scene_audio_build_s": 0.0, "bgm_mix_s": 0.0, "mux_s": 0.0, "audio_passthrough": True}
    audio_build_started = time.perf_counter()
    final_audio = _build_scene_audio_tracks(story, items)
    audio_build_s = time.perf_counter() - audio_build_started
    bgm_mix_s = 0.0
    if bgm_items:
        bgm_started = time.perf_counter()
        final_audio = _mix_story_bgm(final_audio, bgm_items)
        bgm_mix_s = time.perf_counter() - bgm_started
    video_duration = _probe_media_duration(video_only)
    mux_started = time.perf_counter()
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(video_only),
            "-i",
            str(final_audio),
            "-t",
            f"{video_duration:.3f}",
            "-filter:a",
            "apad",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            str(story.get("video", {}).get("audio_bitrate") or "64k"),
            str(output_path),
        ],
        check=True,
    )
    return {
        "scene_audio_build_s": round(audio_build_s, 4),
        "bgm_mix_s": round(bgm_mix_s, 4),
        "mux_s": round(time.perf_counter() - mux_started, 4),
        "audio_passthrough": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a canonical story package to MP4.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cpu", action="store_true", help="Force TinyDisplay software rendering instead of requesting GPU first.")
    parser.add_argument("--no-parallel", action="store_true", help="Disable scene-parallel rendering and force serial mode.")
    parser.add_argument("--video-only", action="store_true", help="Render video frames only and skip audio mux.")
    parser.add_argument("--scene-index", type=int, default=None, help="Internal: render only a single scene by index.")
    parser.add_argument("--scene-workers", type=int, default=0, help="Max concurrent scene render workers.")
    parser.add_argument("--skip-tts-timing", action="store_true", help="Internal: trust the input story timing and skip shared TTS manifest adjustments.")
    args = parser.parse_args()
    total_started = time.perf_counter()

    _delegate_to_desktop_user_if_needed(prefer_gpu=not args.cpu)
    ensure_runtime_dirs()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    prepare_started = time.perf_counter()
    raw_story = read_json(args.input)
    story = raw_story if args.skip_tts_timing else _apply_tts_timing(raw_story)
    if args.scene_index is not None:
        scene_index = int(args.scene_index)
        if not (0 <= scene_index < len(story.get("scenes", []))):
            raise SystemExit(f"scene index out of range: {scene_index}")
        story = _scene_job_story(story, scene_index)
    if args.scene_index is None and not args.skip_tts_timing:
        _clear_output(preserve_dialogue_manifest=bool(raw_story.get("video", {}).get("tts_enabled")))
    cpu_workers = os.cpu_count() or 4
    default_scene_workers = min(4, max(1, len(story.get("scenes", []))), max(1, cpu_workers))
    scene_workers = max(1, int(args.scene_workers or story.get("video", {}).get("scene_workers") or default_scene_workers))
    can_parallel = (
        not args.no_parallel
        and args.scene_index is None
        and len(story.get("scenes", [])) > 1
        and scene_workers > 1
    )
    stage_timings: dict[str, Any] = {
        "prepare_story_s": round(time.perf_counter() - prepare_started, 4),
    }
    if can_parallel:
        _, pipe_name, render_timings = _render_video_stream_parallel(story, args.input, prefer_gpu=not args.cpu, scene_workers=scene_workers)
    else:
        direct_video_output = args.output if args.video_only else None
        _, pipe_name, render_timings = _render_video_stream(story, prefer_gpu=not args.cpu, video_output_path=direct_video_output)
    stage_timings["render"] = render_timings
    if args.video_only:
        if not can_parallel:
            pass
        else:
            copy_started = time.perf_counter()
            video_only = TMP_DIR / "video_only.mp4"
            shutil.copy2(video_only, args.output)
            stage_timings["video_copy_s"] = round(time.perf_counter() - copy_started, 4)
    else:
        stage_timings["audio"] = _mux_audio(story, args.output)
    stage_timings["total_s"] = round(time.perf_counter() - total_started, 4)
    stage_timings["renderer"] = str(story.get("video", {}).get("renderer") or "pygame_2d")
    stage_timings["pipe"] = pipe_name
    stage_timings["parallel"] = bool(can_parallel)
    stage_timings["scene_count"] = len(story.get("scenes", []))
    if args.output.exists():
        stage_timings["output_size_bytes"] = args.output.stat().st_size
    write_json(
        _timings_path(args.output),
        {
            "input": str(args.input),
            "output": str(args.output),
            "cpu": bool(args.cpu),
            "video_only": bool(args.video_only),
            "scene_workers": scene_workers,
            "timings": stage_timings,
        },
    )
    print(f"pipe={pipe_name}")
    print(args.output)
    print(_timings_path(args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
