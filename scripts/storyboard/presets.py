from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Iterable

from common.io import ROOT_DIR, WORK_DIR, ensure_runtime_dirs
from common.story import normalize_story, save_story_package, validate_story_package

from .api import beat, camera_pan, dialogue, expression, prop


DIALOGUE_WINDOWS_6 = [
    (300, 1500),
    (1850, 3050),
    (5150, 6350),
    (6700, 7900),
    (9950, 11150),
    (11450, 12650),
]

ACTION_WINDOWS_3 = [
    (3320, 4720),
    (8140, 9540),
    (12950, 14400),
]


def simple_expression_for_text(text: str) -> str:
    if any(token in text for token in ("掌", "闯", "拦", "退", "阵", "打", "逼", "拿下", "偷袭", "杀", "战")):
        return "angry"
    if any(token in text for token in ("求", "信", "法度", "慈悲", "交代", "理", "问清")):
        return "thinking"
    if any(token in text for token in ("伤", "死", "撑不住", "生机", "疼", "痛")):
        return "thinking"
    if any(token in text for token in ("笑", "体面", "漂亮话", "得意")):
        return "smile"
    if any(token in text for token in ("疑", "怕", "未必", "敢", "当真")):
        return "skeptical"
    return "neutral"


def motion_expression(motion: str) -> str:
    if motion in {
        "dragon-palm",
        "thunder-strike",
        "sword-arc",
        "flying-kick",
        "double-palm-push",
        "spin-kick",
        "diagonal-kick",
        "hook-punch",
        "swing-punch",
        "straight-punch",
        "combo-punch",
    }:
        return "angry"
    if motion in {"enter", "exit", "talk"}:
        return "neutral"
    if motion in {"point"}:
        return "excited"
    return "neutral"


def dialogue_block(
    lines: Iterable[tuple[str, str]],
    *,
    windows: list[tuple[int, int]] | None = None,
    expression_for_text: Callable[[str], str] = simple_expression_for_text,
    talk_motion: str = "talk",
    talk_emotion: str = "focused",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    dialogue_items: list[dict[str, Any]] = []
    beat_items: list[dict[str, Any]] = []
    expression_items: list[dict[str, Any]] = []
    selected_windows = windows or DIALOGUE_WINDOWS_6
    for (start_ms, end_ms), (speaker_id, text) in zip(selected_windows, lines):
        dialogue_items.append(dialogue(start_ms, end_ms, speaker_id, text))
        beat_items.append(beat(start_ms, end_ms, speaker_id, talk_motion, emotion=talk_emotion))
        expression_items.append(expression(speaker_id, start_ms, end_ms, expression_for_text(text)))
    return dialogue_items, beat_items, expression_items


def simple_camera_pan(scene_index: int, *, zoom_base: float = 1.0, zoom_step: float = 0.03, to_zoom: float = 1.08) -> dict[str, Any]:
    return camera_pan(
        x=-0.28 + 0.06 * (scene_index % 3),
        z=0.03,
        zoom=zoom_base + zoom_step * (scene_index % 2),
        to_x=0.22 - 0.05 * (scene_index % 2),
        to_z=0.01,
        to_zoom=to_zoom,
        ease="ease-in-out",
    )


def three_prop_layout(
    prop_ids: list[str],
    scene_index: int,
    *,
    xs: tuple[float, float, float] = (-4.1, 0.0, 4.0),
    zs: tuple[float, float, float] = (-1.08, -0.90, -1.00),
    layers: tuple[str, str, str] = ("back", "mid", "front"),
    scale_base: float = 0.88,
    scale_step: float = 0.06,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for idx, prop_id in enumerate(prop_ids[:3]):
        items.append(
            prop(
                prop_id,
                xs[idx],
                zs[idx],
                scale=scale_base + scale_step * ((scene_index + idx) % 2),
                layer=layers[idx],
            )
        )
    return items


def cli_main(build_story: Callable[[], dict[str, Any]], *, description: str, default_output: str) -> int:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--output", type=Path, default=Path(default_output))
    args = parser.parse_args()
    story = build_story()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(story, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    if isinstance(story.get("scenes"), list):
        print(f"scene_count={len(story['scenes'])}")
    return 0


def build_direct_render_parser(*, description: str, default_output: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--output", type=Path, default=Path(default_output))
    parser.add_argument("--cpu", action="store_true", help="Force CPU rendering.")
    parser.add_argument("--scene-workers", type=int, default=0, help="Concurrent scene render workers.")
    parser.add_argument("--tts-workers", type=int, default=0, help="Concurrent TTS workers.")
    parser.add_argument("--require-tts", action="store_true", help="Fail if TTS cannot be synthesized.")
    parser.add_argument(
        "--allow-missing-tts",
        action="store_true",
        help="Allow rendering to continue without dialogue TTS even when the story requests TTS.",
    )
    parser.add_argument("--no-parallel", action="store_true", help="Disable scene-parallel rendering.")
    return parser


def render_story_payload(
    story_raw: dict[str, Any],
    *,
    output: Path,
    cpu: bool = False,
    scene_workers: int = 0,
    tts_workers: int = 0,
    require_tts: bool = False,
    allow_missing_tts: bool = False,
    no_parallel: bool = False,
) -> int:
    ensure_runtime_dirs()
    story_tts_enabled = bool(story_raw.get("video", {}).get("tts_enabled"))
    story = normalize_story(story_raw, tts_enabled=story_tts_enabled)
    errors = validate_story_package(story)
    if errors:
        for error in errors:
            print(error)
        return 1

    output.parent.mkdir(parents=True, exist_ok=True)
    package_path = WORK_DIR / f"{output.stem}.story_package.json"
    save_story_package(story, package_path)
    runtime_tmp_dir = ROOT_DIR / "tmp" / "direct_runs" / output.stem
    runtime_tmp_dir.mkdir(parents=True, exist_ok=True)
    runtime_env = os.environ.copy()
    runtime_env["PANDAVIDEO_TMP_DIR"] = str(runtime_tmp_dir)

    synth_args = [sys.executable, str(ROOT_DIR / "scripts" / "synthesize_tts.py"), "--input", str(package_path)]
    must_require_tts = bool(require_tts or (story_tts_enabled and not allow_missing_tts))
    if must_require_tts:
        synth_args.append("--require-tts")
    if tts_workers:
        synth_args.extend(["--tts-workers", str(tts_workers)])
    subprocess.run(synth_args, cwd=ROOT_DIR, check=True, env=runtime_env)

    render_args = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "render_video.py"),
        "--input",
        str(package_path),
        "--output",
        str(output),
    ]
    if scene_workers:
        render_args.extend(["--scene-workers", str(scene_workers)])
    if cpu:
        render_args.append("--cpu")
    if no_parallel:
        render_args.append("--no-parallel")
    subprocess.run(render_args, cwd=ROOT_DIR, check=True, env=runtime_env)

    print(output)
    return 0


def direct_render_main(build_story: Callable[[], dict[str, Any]], *, description: str, default_output: str) -> int:
    parser = build_direct_render_parser(description=description, default_output=default_output)
    args = parser.parse_args()
    story_raw = build_story()
    return render_story_payload(
        story_raw,
        output=args.output,
        cpu=args.cpu,
        scene_workers=args.scene_workers,
        tts_workers=args.tts_workers,
        require_tts=args.require_tts,
        allow_missing_tts=args.allow_missing_tts,
        no_parallel=args.no_parallel,
    )
