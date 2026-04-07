#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common.io import read_json
from common.story import validate_story_package


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a canonical story package.")
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()

    payload = read_json(args.input)
    errors = validate_story_package(payload)
    if errors:
        for error in errors:
            print(error)
        return 1

    print("story package is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
