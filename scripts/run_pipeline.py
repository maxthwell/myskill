#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from common.io import ROOT_DIR, WORK_DIR, ensure_runtime_dirs


def _run(args: list[str]) -> None:
    subprocess.run(args, cwd=ROOT_DIR, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate, normalize, optionally synthesize TTS, and render from a Python story script.")
    parser.add_argument("--input", type=Path, required=True, help="Python story script exposing SCRIPT/VIDEO_SCRIPT or build_story().")
    parser.add_argument("--output", type=Path, default=ROOT_DIR / "outputs" / "story.mp4")
    parser.add_argument("--with-tts", action="store_true")
    parser.add_argument("--require-tts", action="store_true")
    parser.add_argument("--tts-workers", type=int, default=0, help="Max concurrent TTS synthesis workers.")
    parser.add_argument("--scene-workers", type=int, default=0, help="Max concurrent scene render workers.")
    parser.add_argument("--cpu", action="store_true", help="Force CPU rendering instead of requesting GPU.")
    parser.add_argument("--no-parallel", action="store_true", help="Disable scene-parallel render.")
    args = parser.parse_args()

    ensure_runtime_dirs()
    story_package = WORK_DIR / "story_package.json"
    _run([sys.executable, str(ROOT_DIR / "scripts" / "check_story_input.py"), "--input", str(args.input), *([] if not args.with_tts else ["--with-tts"])])
    _run([sys.executable, str(ROOT_DIR / "scripts" / "normalize_story.py"), "--input", str(args.input), "--output", str(story_package), *([] if not args.with_tts else ["--with-tts"])])
    _run([sys.executable, str(ROOT_DIR / "scripts" / "validate_story.py"), "--input", str(story_package)])
    synth_args = [sys.executable, str(ROOT_DIR / "scripts" / "synthesize_tts.py"), "--input", str(story_package)]
    if args.require_tts:
        synth_args.append("--require-tts")
    if args.tts_workers:
        synth_args.extend(["--tts-workers", str(args.tts_workers)])
    _run(synth_args)

    render_args = [sys.executable, str(ROOT_DIR / "scripts" / "render_video.py"), "--input", str(story_package), "--output", str(args.output)]
    if args.scene_workers:
        render_args.extend(["--scene-workers", str(args.scene_workers)])
    if args.cpu:
        render_args.append("--cpu")
    if args.no_parallel:
        render_args.append("--no-parallel")
    _run(render_args)
    print(args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
