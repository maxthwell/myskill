#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common.story import normalize_story, save_story_package
from common.story_script import load_story_source


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize a Python story script into story_package.json.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--source-prompt", default=None)
    parser.add_argument("--with-tts", action="store_true")
    args = parser.parse_args()

    payload, _ = load_story_source(args.input)
    story = normalize_story(payload, source_prompt=args.source_prompt, tts_enabled=args.with_tts)
    target = save_story_package(story, args.output)
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
