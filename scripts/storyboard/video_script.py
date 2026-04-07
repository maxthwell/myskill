from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
from pathlib import Path
from typing import Any, Sequence

from .api import story_package
from .presets import build_direct_render_parser, render_story_payload


class BaseVideoScript(ABC):
    def get_description(self) -> str:
        return f"Render {self.get_title()}."

    def get_default_output(self) -> str:
        return "outputs/story.mp4"

    def has_tts(self) -> bool:
        return False

    def get_notes(self) -> dict[str, Any]:
        return {}

    def get_video_options(self) -> dict[str, Any]:
        return {}

    @abstractmethod
    def get_title(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_theme(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_cast(self) -> Sequence[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_scenes(self) -> Sequence[dict[str, Any]]:
        raise NotImplementedError

    def build_story(self) -> dict[str, Any]:
        video = deepcopy(self.get_video_options())
        video["tts_enabled"] = bool(self.has_tts())
        return story_package(
            title=self.get_title(),
            cast=list(self.get_cast()),
            scenes=list(self.get_scenes()),
            theme=self.get_theme(),
            video=video,
            notes=deepcopy(self.get_notes()),
        )

    def build_cli_parser(self):
        return build_direct_render_parser(
            description=self.get_description(),
            default_output=self.get_default_output(),
        )

    def render(self, *, output: Path, cpu: bool, scene_workers: int, tts_workers: int, require_tts: bool, allow_missing_tts: bool, no_parallel: bool) -> int:
        return render_story_payload(
            self.build_story(),
            output=output,
            cpu=cpu,
            scene_workers=scene_workers,
            tts_workers=tts_workers,
            require_tts=require_tts,
            allow_missing_tts=allow_missing_tts,
            no_parallel=no_parallel,
        )

    def __call__(self, argv: Sequence[str] | None = None) -> int:
        parser = self.build_cli_parser()
        args = parser.parse_args(list(argv) if argv is not None else None)
        return self.render(
            output=args.output,
            cpu=args.cpu,
            scene_workers=args.scene_workers,
            tts_workers=args.tts_workers,
            require_tts=args.require_tts,
            allow_missing_tts=args.allow_missing_tts,
            no_parallel=args.no_parallel,
        )
