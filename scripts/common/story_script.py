from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


def is_story_script(path: Path) -> bool:
    return path.suffix.lower() == ".py"


def _load_module_from_path(path: Path) -> ModuleType:
    module_name = f"_story_script_{path.stem}_{abs(hash(path.resolve()))}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"unable to load story script: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def load_story_source(path: Path) -> tuple[dict[str, Any], str]:
    if not is_story_script(path):
        raise ValueError(f"only Python story scripts are supported on the mainline: {path}")

    module = _load_module_from_path(path)
    if hasattr(module, "SCRIPT") and hasattr(module.SCRIPT, "build_story") and callable(module.SCRIPT.build_story):
        payload = module.SCRIPT.build_story()
        kind = "video-script-instance"
    elif hasattr(module, "VIDEO_SCRIPT") and hasattr(module.VIDEO_SCRIPT, "build_story") and callable(module.VIDEO_SCRIPT.build_story):
        payload = module.VIDEO_SCRIPT.build_story()
        kind = "video-script-instance"
    elif hasattr(module, "build_story") and callable(module.build_story):
        payload = module.build_story()
        kind = "script-function"
    elif hasattr(module, "STORY"):
        payload = getattr(module, "STORY")
        kind = "script-constant"
    else:
        raise ValueError(f"story script must expose SCRIPT/VIDEO_SCRIPT, build_story(), or STORY: {path}")

    if not isinstance(payload, dict):
        raise ValueError(f"story script must return a dict payload: {path}")
    return payload, kind
