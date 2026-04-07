#!/usr/bin/env python3
from __future__ import annotations

import importlib
import os
import shutil
import sys
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from common.io import ROOT_DIR, asset_catalog
from common.story import load_and_normalize_story, validate_story_package


EXAMPLE_SCRIPT = Path("scripts/generate_hanjiang_night_escort_story.py")


def _check_modules() -> list[str]:
    missing: list[str] = []
    for module_name in ("pygame", "PIL"):
        try:
            importlib.import_module(module_name)
        except ModuleNotFoundError:
            missing.append(module_name)
    if shutil.which("ffmpeg") is None:
        missing.append("ffmpeg")
    return missing


def main() -> int:
    print(f"root={ROOT_DIR}")
    print(f"ready_script={Path(__file__).resolve()}")

    missing = _check_modules()
    if missing:
        print(f"status=not-ready missing={','.join(missing)}")
        return 1

    catalog = asset_catalog()
    required_counts = {
        "backgrounds": len(catalog.get("backgrounds", [])),
        "characters": len(catalog.get("characters", [])),
        "effects": len(catalog.get("effects", [])),
        "bgm": len(catalog.get("bgm", [])),
    }
    print("assets=" + " ".join(f"{key}:{value}" for key, value in required_counts.items()))

    example_path = ROOT_DIR / EXAMPLE_SCRIPT
    story = load_and_normalize_story(example_path, tts_enabled=False)
    errors = validate_story_package(story)
    if errors:
        print(f"status=not-ready example={EXAMPLE_SCRIPT} error_count={len(errors)}")
        for error in errors[:5]:
            print(f"error={error}")
        return 1

    print(f"example={EXAMPLE_SCRIPT} scene_count={len(story.get('scenes', []))} title={story.get('meta', {}).get('title', '')}")
    print("status=ready")
    print("next=python3 scripts/list_assets.py --pretty")
    print(f"next=python3 {EXAMPLE_SCRIPT} --cpu --output outputs/preview.mp4")
    return 0


if __name__ == "__main__":
    sys.exit(main())
