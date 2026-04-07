#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys

from common.io import asset_catalog


def main() -> int:
    parser = argparse.ArgumentParser(description="List discoverable story assets so an agent can choose from actual local materials.")
    parser.add_argument(
        "--category",
        choices=["backgrounds", "floors", "characters", "props", "motions", "effects", "foregrounds", "audio", "bgm"],
        default=None,
        help="Return only one category when set.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()

    catalog = asset_catalog()
    payload = catalog if args.category is None else {args.category: catalog[args.category]}
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2 if args.pretty else None)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
