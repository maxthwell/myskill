from __future__ import annotations

from copy import deepcopy
from typing import Any

from .api import story_package


WUXIA_FAST_VIDEO = {
    "width": 960,
    "height": 540,
    "fps": 12,
    "renderer": "pygame_2d",
    "video_codec": "mpeg4",
    "mpeg4_qscale": 5,
    "encoder_preset": "ultrafast",
    "crf": 26,
    "subtitle_mode": "bottom",
    "tts_enabled": False,
}

WUXIA_TTS_VIDEO = {
    **WUXIA_FAST_VIDEO,
    "tts_enabled": True,
}


def wuxia_story(
    *,
    title: str,
    cast: list[dict[str, Any]],
    scenes: list[dict[str, Any]],
    theme: str,
    with_tts: bool = False,
    video_overrides: dict[str, Any] | None = None,
    notes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    video = deepcopy(WUXIA_TTS_VIDEO if with_tts else WUXIA_FAST_VIDEO)
    if video_overrides:
        for key, value in video_overrides.items():
            if key == "stage_layout" and isinstance(value, dict):
                current = deepcopy(video.get("stage_layout") or {})
                current.update(value)
                video[key] = current
            else:
                video[key] = value
    return story_package(
        title=title,
        cast=cast,
        scenes=scenes,
        theme=theme,
        video=video,
        notes=notes,
    )
