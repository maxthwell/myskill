#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from common.io import TMP_DIR, ensure_runtime_dirs, write_json


OUTPUT_STORY = Path("outputs/effects_audio_showcase_story.json")
OUTPUT_AUDIO_MANIFEST = TMP_DIR / "dialogue_audio_manifest.json"


def _scene(
    scene_id: str,
    background: str,
    floor: str,
    summary: str,
    duration_ms: int,
    actors: list[dict],
    beats: list[dict],
) -> dict:
    return {
        "id": scene_id,
        "background": background,
        "floor": floor,
        "duration_ms": duration_ms,
        "summary": summary,
        "camera": {"type": "static", "zoom": 1.0},
        "effects": [],
        "props": [],
        "actors": actors,
        "npc_groups": [],
        "beats": beats,
        "expressions": [],
        "dialogues": [],
        "audio": {"bgm": None, "sfx": []},
        "notes": {},
    }


def _spawn(actor_id: str, x: float, z: float, facing: str, scale: float = 1.0, layer: str = "front") -> dict:
    return {
        "actor_id": actor_id,
        "spawn": {"x": x, "z": z},
        "scale": scale,
        "layer": layer,
        "facing": facing,
    }


def _beat(
    actor_id: str,
    motion: str,
    start_ms: int,
    end_ms: int,
    *,
    from_x: float | None = None,
    from_z: float | None = None,
    to_x: float | None = None,
    to_z: float | None = None,
    facing: str | None = None,
    emotion: str = "charged",
) -> dict:
    return {
        "start_ms": start_ms,
        "end_ms": end_ms,
        "actor_id": actor_id,
        "motion": motion,
        "from": None if from_x is None or from_z is None else {"x": from_x, "z": from_z},
        "to": None if to_x is None or to_z is None else {"x": to_x, "z": to_z},
        "facing": facing,
        "emotion": emotion,
    }


def build_story() -> dict:
    cast = [
        {"id": "hero", "display_name": "乔峰", "asset_id": "general-guard"},
        {"id": "monk", "display_name": "少林高僧", "asset_id": "master-monk"},
        {"id": "swordswoman", "display_name": "剑客", "asset_id": "swordswoman"},
        {"id": "strategist", "display_name": "谋士", "asset_id": "strategist"},
    ]

    scenes = [
        _scene(
            "scene-001",
            "temple-courtyard",
            "stone-court",
            "降龙十八掌展示，启动、金龙飞旋、命中特效完整出现。",
            6400,
            [
                _spawn("hero", -2.5, 0.0, "right", 1.05),
                _spawn("monk", 2.4, 0.0, "left", 1.0),
            ],
            [
                _beat("hero", "enter", 180, 980, from_x=-3.2, from_z=0.0, to_x=-2.5, to_z=0.0, facing="right"),
                _beat("hero", "dragon-palm", 1400, 3200, from_x=-2.5, from_z=0.0, to_x=-1.6, to_z=0.0, facing="right"),
                _beat("monk", "exit", 2500, 3900, from_x=2.4, from_z=0.0, to_x=3.0, to_z=0.0, facing="left"),
                _beat("monk", "point", 4200, 5400, from_x=2.1, from_z=0.0, to_x=2.3, to_z=0.0, facing="left"),
            ],
        ),
        _scene(
            "scene-002",
            "night-bridge",
            "dark-stage",
            "银河旋转配合剑弧，突出兵器碰撞音效。",
            6200,
            [
                _spawn("swordswoman", -2.2, 0.0, "right", 1.0),
                _spawn("strategist", 2.2, 0.0, "left", 0.98),
            ],
            [
                _beat("swordswoman", "sword-arc", 700, 2500, from_x=-2.2, from_z=0.0, to_x=-1.0, to_z=0.0, facing="right"),
                _beat("strategist", "sword-arc", 3000, 4700, from_x=2.2, from_z=0.0, to_x=1.1, to_z=0.0, facing="left"),
                _beat("swordswoman", "exit", 4900, 5900, from_x=-1.3, from_z=0.0, to_x=-1.9, to_z=0.0, facing="right"),
            ],
        ),
        _scene(
            "scene-003",
            "mountain-cliff",
            "stone-court",
            "雷击与爆炸特效展示，强调全屏震荡感。",
            6200,
            [
                _spawn("monk", -2.0, 0.0, "right", 1.0),
                _spawn("hero", 2.1, 0.0, "left", 1.04),
            ],
            [
                _beat("monk", "thunder-strike", 900, 2700, from_x=-2.0, from_z=0.0, to_x=-1.0, to_z=0.0, facing="right"),
                _beat("hero", "thunder-strike", 3200, 5000, from_x=2.1, from_z=0.0, to_x=1.0, to_z=0.0, facing="left"),
            ],
        ),
        _scene(
            "scene-004",
            "training-ground",
            "stone-court",
            "三类主特效连续切换，进入组合展示。",
            7600,
            [
                _spawn("hero", -2.9, 0.0, "right", 1.02),
                _spawn("swordswoman", -0.3, -0.12, "right", 0.96, "mid"),
                _spawn("monk", 2.7, 0.0, "left", 1.0),
            ],
            [
                _beat("hero", "dragon-palm", 500, 2100, from_x=-2.9, from_z=0.0, to_x=-1.7, to_z=0.0, facing="right"),
                _beat("swordswoman", "sword-arc", 2350, 3900, from_x=-0.3, from_z=-0.12, to_x=0.6, to_z=-0.12, facing="right"),
                _beat("monk", "thunder-strike", 4300, 6200, from_x=2.7, from_z=0.0, to_x=1.5, to_z=0.0, facing="left"),
            ],
        ),
        _scene(
            "scene-005",
            "inn-hall",
            "wood-plank",
            "室内混战展示，三种动作交替并叠加不同音效。",
            7600,
            [
                _spawn("hero", -2.7, 0.0, "right", 1.0),
                _spawn("strategist", 0.2, -0.12, "left", 0.95, "mid"),
                _spawn("swordswoman", 2.6, 0.0, "left", 0.98),
            ],
            [
                _beat("hero", "dragon-palm", 700, 2200, from_x=-2.7, from_z=0.0, to_x=-1.5, to_z=0.0, facing="right"),
                _beat("strategist", "thunder-strike", 2500, 4300, from_x=0.2, from_z=-0.12, to_x=-0.3, to_z=-0.12, facing="left"),
                _beat("swordswoman", "sword-arc", 4700, 6500, from_x=2.6, from_z=0.0, to_x=1.2, to_z=0.0, facing="left"),
            ],
        ),
        _scene(
            "scene-006",
            "temple-courtyard",
            "dark-stage",
            "终章总展示，六个视觉特效和三种音效全部回收。",
            8600,
            [
                _spawn("hero", -3.0, 0.0, "right", 1.04),
                _spawn("monk", 0.0, -0.16, "left", 0.92, "mid"),
                _spawn("swordswoman", 2.9, 0.0, "left", 0.98),
            ],
            [
                _beat("hero", "dragon-palm", 500, 2200, from_x=-3.0, from_z=0.0, to_x=-1.8, to_z=0.0, facing="right"),
                _beat("monk", "thunder-strike", 2550, 4550, from_x=0.0, from_z=-0.16, to_x=0.0, to_z=-0.16, facing="left"),
                _beat("swordswoman", "sword-arc", 4900, 7000, from_x=2.9, from_z=0.0, to_x=1.3, to_z=0.0, facing="left"),
            ],
        ),
    ]

    return {
        "meta": {
            "title": "特效音效总展示",
            "language": "zh-CN",
            "theme": "武侠特效、战斗音效、全屏攻击展示",
            "source_prompt": None,
        },
        "video": {
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
            "scene_workers": 4,
        },
        "cast": cast,
        "assets": {
            "backgrounds": ["temple-courtyard", "mountain-cliff", "inn-hall", "training-ground", "night-bridge"],
            "floors": ["stone-court", "wood-plank", "dark-stage"],
            "props": [],
            "motions": ["enter", "exit", "point", "dragon-palm", "thunder-strike", "sword-arc"],
            "effects": ["dragon-palm", "thunder-strike", "sword-arc"],
        },
        "scenes": scenes,
    }


def build_audio_manifest() -> dict:
    base = Path("assets/audio")
    fist = base / "031_26_赤手空拳打斗的声音_爱给网_aigei_com.mp3"
    metal = base / "刀剑、金属碰撞（带回音）_爱给网_aigei_com.mp3"
    boom = base / "音效 爆炸 爆破 爆发 战斗_爱给网_aigei_com.mp3"
    items = [
        {"scene_id": "scene-001", "path": str(fist), "start_ms": 1650},
        {"scene_id": "scene-001", "path": str(fist), "start_ms": 2480},
        {"scene_id": "scene-002", "path": str(metal), "start_ms": 820},
        {"scene_id": "scene-002", "path": str(metal), "start_ms": 3180},
        {"scene_id": "scene-003", "path": str(boom), "start_ms": 1380},
        {"scene_id": "scene-003", "path": str(boom), "start_ms": 3640},
        {"scene_id": "scene-004", "path": str(fist), "start_ms": 720},
        {"scene_id": "scene-004", "path": str(metal), "start_ms": 2580},
        {"scene_id": "scene-004", "path": str(boom), "start_ms": 4720},
        {"scene_id": "scene-005", "path": str(fist), "start_ms": 950},
        {"scene_id": "scene-005", "path": str(boom), "start_ms": 3120},
        {"scene_id": "scene-005", "path": str(metal), "start_ms": 5160},
        {"scene_id": "scene-006", "path": str(fist), "start_ms": 740},
        {"scene_id": "scene-006", "path": str(boom), "start_ms": 3040},
        {"scene_id": "scene-006", "path": str(metal), "start_ms": 5520},
    ]
    return {"items": items}


def main() -> None:
    ensure_runtime_dirs()
    write_json(OUTPUT_STORY, build_story())
    write_json(OUTPUT_AUDIO_MANIFEST, build_audio_manifest())
    print(OUTPUT_STORY)
    print(OUTPUT_AUDIO_MANIFEST)


if __name__ == "__main__":
    main()
