#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common.io import WORK_DIR, write_json
from common.story import load_and_normalize_story
from common.story_script import load_story_source


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Python story script before rendering.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--prompt", default=None)
    parser.add_argument("--with-tts", action="store_true")
    args = parser.parse_args()

    try:
        _, source_kind = load_story_source(args.input)
        story = load_and_normalize_story(args.input, source_prompt=args.prompt, tts_enabled=args.with_tts)
    except ValueError as exc:
        print(str(exc))
        return 1

    write_json(WORK_DIR / "story_package.json", story)
    print(f"kind={source_kind}")
    print(f"scene_count={len(story.get('scenes', []))}")
    print(f"title={story.get('meta', {}).get('title', '')}")
    print(WORK_DIR / "story_package.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
