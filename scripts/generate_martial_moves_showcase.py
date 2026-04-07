#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass

from storyboard import (
    BaseVideoScript,
    actor,
    audio_bgm,
    audio_sfx,
    beat,
    camera_pan,
    camera_static,
    cast_member,
    dialogue,
    effect,
    expression,
    foreground,
    prop,
    scene,
    scene_audio,
)


VIDEO = {
    "width": 854,
    "height": 480,
    "fps": 12,
    "renderer": "panda_card_fast",
    "video_codec": "libx264",
    "encoder_preset": "ultrafast",
    "crf": 26,
    "audio_bitrate": "64k",
    "subtitle_mode": "bottom",
    "tts_enabled": True,
    "stage_layout": {
        "effect_overlay_alpha": 0.86,
    },
}

CAST = [
    cast_member("host", "馆主", "master-monk"),
    cast_member("hero", "演武者", "young-hero"),
    cast_member("rival", "陪练", "general-guard"),
]

SCENE_DURATION_MS = 9_800
DIALOGUE_WINDOWS = [
    (400, 2200),
    (2700, 4700),
    (5200, 6900),
]

FLOOR_BY_BACKGROUND = {
    "inn-hall": "wood-plank",
    "mountain-cliff": "stone-court",
    "night-bridge": "dark-stage",
    "temple-courtyard": "stone-court",
    "theatre-stage": "dark-stage",
    "training-ground": "stone-court",
}

FIST_AUDIO = "assets/audio/031_26_赤手空拳打斗的声音_爱给网_aigei_com.mp3"
METAL_AUDIO = "assets/audio/刀剑、金属碰撞（带回音）_爱给网_aigei_com.mp3"
BOOM_AUDIO = "assets/audio/音效 爆炸 爆破 爆发 战斗_爱给网_aigei_com.mp3"
INTRO_BGM = "assets/bgm/历史的天空-古筝-纯音乐.mp3"
ACTION_BGM = "assets/bgm/男儿当自强.mp3"


@dataclass(frozen=True)
class MoveSpec:
    scene_id: str
    move_id: str
    title: str
    background: str
    foreground_id: str | None
    summary: str
    lines: list[tuple[str, str]]
    actor_start: float
    actor_end: float
    actor_facing: str
    rival_start: float
    rival_end: float
    rival_facing: str
    rival_motion: str
    overlay_effect: str
    overlay_start_ms: int
    overlay_end_ms: int
    sfx_path: str
    sfx_start_ms: int
    beat_start_ms: int = 7200
    beat_end_ms: int = 9100
    rival_beat_start_ms: int = 7700
    rival_beat_end_ms: int = 9300


def front_actor(actor_id: str, x: float, *, facing: str, scale: float = 1.0, z: float = 0.0) -> dict:
    return actor(actor_id, x, z=z, facing=facing, scale=scale)


def mid_actor(actor_id: str, x: float, *, facing: str, scale: float = 0.92, z: float = -0.18) -> dict:
    return actor(actor_id, x, z=z, facing=facing, scale=scale, layer="mid")


def infer_expression(text: str) -> str:
    if any(token in text for token in ("踢", "拳", "掌", "压", "冲", "打", "爆", "快")):
        return "angry"
    if any(token in text for token in ("稳", "收", "看", "重心", "发力", "路线")):
        return "thinking"
    if any(token in text for token in ("漂亮", "干净", "利落")):
        return "smile"
    return "neutral"


def build_dialogue_bundle(lines: list[tuple[str, str]]) -> tuple[list[dict], list[dict], list[dict]]:
    dialogue_items: list[dict] = []
    talk_beats: list[dict] = []
    expressions_track: list[dict] = []
    for (start_ms, end_ms), (speaker_id, text) in zip(DIALOGUE_WINDOWS, lines):
        dialogue_items.append(dialogue(start_ms, end_ms, speaker_id, text))
        talk_beats.append(beat(start_ms, end_ms, speaker_id, "talk", emotion="focused"))
        expressions_track.append(expression(speaker_id, start_ms, end_ms, infer_expression(text)))
    return dialogue_items, talk_beats, expressions_track


def trim_talk_beats_for_actions(talk_beats: list[dict], action_beats: list[dict]) -> list[dict]:
    trimmed: list[dict] = []
    for talk in talk_beats:
        segments = [(talk["start_ms"], talk["end_ms"])]
        for action in action_beats:
            if action["actor_id"] != talk["actor_id"]:
                continue
            next_segments: list[tuple[int, int]] = []
            for seg_start, seg_end in segments:
                if action["end_ms"] <= seg_start or action["start_ms"] >= seg_end:
                    next_segments.append((seg_start, seg_end))
                    continue
                if action["start_ms"] > seg_start:
                    next_segments.append((seg_start, action["start_ms"]))
                if action["end_ms"] < seg_end:
                    next_segments.append((action["end_ms"], seg_end))
            segments = next_segments
            if not segments:
                break
        for seg_start, seg_end in segments:
            if seg_end - seg_start < 220:
                continue
            trimmed.append(
                beat(
                    seg_start,
                    seg_end,
                    talk["actor_id"],
                    talk["motion"],
                    facing=talk.get("facing"),
                    emotion=talk.get("emotion", "focused"),
                )
            )
    return trimmed


def default_props(background: str) -> list[dict]:
    if background == "theatre-stage":
        return [
            prop("training-drum", -3.3, -1.00, scale=0.92, layer="mid"),
            prop("weapon-rack", 3.2, -1.02, scale=0.92, layer="mid"),
            prop("star", -4.0, -0.54, scale=0.50, layer="back"),
            prop("moon", 3.8, -0.42, scale=0.68, layer="back"),
        ]
    if background == "inn-hall":
        return [
            prop("wall-window", -3.8, -1.0, scale=0.92, layer="back"),
            prop("wall-door", 3.8, -1.02, scale=0.92, layer="back"),
            prop("weapon-rack", 0.0, -1.02, scale=0.88, layer="mid"),
        ]
    if background == "night-bridge":
        return [
            prop("moon", 3.7, -0.40, scale=0.74, layer="back"),
            prop("star", -3.8, -0.54, scale=0.56, layer="back"),
            prop("lantern", -3.4, -0.92, scale=0.94, layer="front"),
        ]
    return [
        prop("house", 0.0, -1.08, scale=0.98, layer="back"),
        prop("training-drum", -3.5, -1.02, scale=0.88, layer="back"),
        prop("weapon-rack", 3.3, -1.0, scale=0.90, layer="mid"),
    ]


def default_foregrounds(background: str) -> list[dict]:
    if background == "theatre-stage":
        return [foreground("敞开的红色帘子-窗帘或床帘皆可")]
    if background == "inn-hall":
        return [foreground("开着门的室内")]
    if background == "night-bridge":
        return [foreground("中式古典大门")]
    return []


def scene_camera(scene_index: int, *, finale: bool = False) -> dict:
    if finale:
        return camera_pan(
            x=-0.30,
            z=0.03,
            zoom=1.06,
            to_x=0.26,
            to_z=0.0,
            to_zoom=1.16,
            ease="ease-in-out",
        )
    if scene_index == 1:
        return camera_static(x=0.0, z=0.03, zoom=1.08)
    return camera_pan(
        x=-0.20 + 0.04 * (scene_index % 2),
        z=0.03,
        zoom=1.02,
        to_x=0.18 - 0.04 * (scene_index % 3),
        to_z=0.0,
        to_zoom=1.10,
        ease="ease-in-out",
    )


def bgm_for_scene(scene_index: int) -> dict:
    if scene_index == 1:
        return audio_bgm(INTRO_BGM, volume=0.52, loop=True)
    return audio_bgm(ACTION_BGM, volume=0.56, loop=True)


def move_scene(scene_index: int, spec: MoveSpec) -> dict:
    dialogue_items, talk_beats, expressions_track = build_dialogue_bundle(spec.lines)
    action_beats = [
        beat(spec.beat_start_ms, spec.beat_end_ms, "hero", spec.move_id, x0=spec.actor_start, x1=spec.actor_end, facing=spec.actor_facing, emotion="charged"),
        beat(spec.rival_beat_start_ms, spec.rival_beat_end_ms, "rival", spec.rival_motion, x0=spec.rival_start, x1=spec.rival_end, facing=spec.rival_facing, emotion="hurt"),
        beat(7050, 7600, "host", "point", facing="right", emotion="focused"),
    ]
    beats = [*trim_talk_beats_for_actions(talk_beats, action_beats), *action_beats]
    return scene(
        spec.scene_id,
        background=spec.background,
        floor=FLOOR_BY_BACKGROUND[spec.background],
        duration_ms=SCENE_DURATION_MS,
        summary=spec.summary,
        camera=scene_camera(scene_index),
        props=default_props(spec.background),
        foregrounds=default_foregrounds(spec.background)
        + ([foreground(spec.foreground_id)] if spec.foreground_id and spec.foreground_id not in {item.get("foreground_id") for item in default_foregrounds(spec.background)} else []),
        actors=[
            mid_actor("host", -3.2, facing="right", scale=0.90, z=-0.28),
            front_actor("hero", -1.5, facing="right", scale=1.04),
            front_actor("rival", 1.8, facing="left", scale=0.98),
        ],
        beats=beats,
        expressions=expressions_track,
        dialogues=dialogue_items,
        effects=[
            effect(spec.overlay_effect, start_ms=spec.overlay_start_ms, end_ms=spec.overlay_end_ms, alpha=0.20, playback_speed=0.90),
        ],
        audio=scene_audio(
            bgm=bgm_for_scene(scene_index),
            sfx=[
                audio_sfx(spec.sfx_path, start_ms=spec.sfx_start_ms, volume=0.90),
                audio_sfx(FIST_AUDIO, start_ms=8800, volume=1.05),
            ],
        ),
    )


class MartialMovesShowcaseVideo(BaseVideoScript):
    def get_title(self) -> str:
        return "九式演武图鉴"

    def get_theme(self) -> str:
        return "武术动作介绍、演示与拆解"

    def has_tts(self) -> bool:
        return True

    def get_default_output(self) -> str:
        return "outputs/martial_moves_showcase.mp4"

    def get_video_options(self) -> dict:
        return VIDEO

    def get_notes(self) -> dict:
        return {
            "focus": "martial-moves-showcase",
            "moves": [
                "flying-kick",
                "somersault",
                "double-palm-push",
                "spin-kick",
                "diagonal-kick",
                "hook-punch",
                "swing-punch",
                "straight-punch",
                "combo-punch",
            ],
            "bgm_assets": [INTRO_BGM, ACTION_BGM],
        }

    def get_cast(self) -> list[dict]:
        return CAST

    def get_scenes(self) -> list[dict]:
        scenes: list[dict] = []

        intro_dialogues, intro_talk, intro_expressions = build_dialogue_bundle(
            [
                ("host", "今日演武，只讲九个最实用也最能出镜的动作。"),
                ("host", "从飞踢到直拳、再到组合拳，每一式都看路线、重心和收势。"),
                ("hero", "我来演，陪练来吃招，你只管看清楚。"),
            ]
        )
        intro_beats = [
            *intro_talk,
            beat(7200, 7900, "host", "point", facing="right", emotion="charged"),
            beat(7700, 9300, "hero", "enter", x0=-2.5, x1=-1.3, facing="right", emotion="charged"),
            beat(7900, 9400, "rival", "enter", x0=3.0, x1=1.8, facing="left", emotion="tense"),
        ]
        scenes.append(
            scene(
                "scene-001",
                background="theatre-stage",
                floor=FLOOR_BY_BACKGROUND["theatre-stage"],
                duration_ms=SCENE_DURATION_MS,
                summary="开场总览，介绍九套动作的演武路线。",
                camera=scene_camera(1),
                props=default_props("theatre-stage"),
                foregrounds=default_foregrounds("theatre-stage"),
                actors=[
                    mid_actor("host", -3.0, facing="right", scale=0.92, z=-0.28),
                    front_actor("hero", -1.6, facing="right", scale=1.04),
                    front_actor("rival", 1.8, facing="left", scale=0.98),
                ],
                beats=intro_beats,
                expressions=intro_expressions,
                dialogues=intro_dialogues,
                effects=[effect("启动大招特效", start_ms=7600, end_ms=9300, alpha=0.18, playback_speed=0.90)],
                audio=scene_audio(
                    bgm=bgm_for_scene(1),
                    sfx=[
                        audio_sfx(FIST_AUDIO, start_ms=8040, volume=0.84),
                        audio_sfx(METAL_AUDIO, start_ms=8580, volume=0.66),
                    ],
                ),
            )
        )

        move_specs = [
            MoveSpec(
                "scene-002",
                "flying-kick",
                "飞踢",
                "training-ground",
                None,
                "飞踢展示，突出腾空后的直线穿透感。",
                [
                    ("host", "第一式，飞踢。起跳快，送胯更要快。"),
                    ("host", "膝先提，腿再甩，目标锁在胸腹正中。"),
                    ("rival", "这一脚进得直，压迫感会非常强。"),
                ],
                -2.2,
                -0.1,
                "right",
                1.9,
                2.4,
                "left",
                "exit",
                "命中特效",
                8080,
                9300,
                FIST_AUDIO,
                8160,
            ),
            MoveSpec(
                "scene-003",
                "somersault",
                "翻跟头",
                "night-bridge",
                "中式古典大门",
                "翻跟头展示，强调腾空翻转与落点控制。",
                [
                    ("host", "第二式，翻跟头。不是乱翻，要翻出完整弧线。"),
                    ("host", "起身那一下靠收腹，落地那一下靠脚掌找地。"),
                    ("hero", "翻过去之后，人要立刻能接下一个动作。"),
                ],
                -2.0,
                0.6,
                "right",
                1.9,
                1.2,
                "left",
                "point",
                "启动大招特效",
                7420,
                8620,
                BOOM_AUDIO,
                8040,
            ),
            MoveSpec(
                "scene-004",
                "double-palm-push",
                "双掌平推",
                "temple-courtyard",
                None,
                "双掌平推展示，重心前送，发力短促而集中。",
                [
                    ("host", "第三式，双掌平推。腰背要先成一条线。"),
                    ("host", "脚跟压住地面，双掌像墙一样整块推出去。"),
                    ("rival", "这一招最怕手先出去，身子没跟上。"),
                ],
                -1.8,
                -0.3,
                "right",
                1.7,
                2.5,
                "left",
                "exit",
                "龟派气功",
                7760,
                9200,
                BOOM_AUDIO,
                8200,
            ),
            MoveSpec(
                "scene-005",
                "spin-kick",
                "侧旋踢",
                "mountain-cliff",
                None,
                "侧旋踢展示，旋转借力，腿线完整扫过目标面。",
                [
                    ("host", "第四式，侧旋踢。先转肩，再转胯，最后送腿。"),
                    ("host", "转身不是炫，是为了把整条腿的离心力带出来。"),
                    ("hero", "你看脚跟这条线，扫过去像一把横刀。"),
                ],
                -1.4,
                0.4,
                "right",
                1.9,
                2.7,
                "left",
                "big-jump",
                "爆炸特效",
                8060,
                9360,
                BOOM_AUDIO,
                8240,
            ),
            MoveSpec(
                "scene-006",
                "diagonal-kick",
                "平行斜踢",
                "inn-hall",
                "开着门的室内",
                "平行斜踢展示，身体近乎平躺，攻击线斜切而出。",
                [
                    ("host", "第五式，平行斜踢。身体侧过去，腿从斜线切进来。"),
                    ("host", "这招漂亮不在高，而在出腿的角度够刁。"),
                    ("rival", "只要角度卡住，护架也会被直接劈开。"),
                ],
                -1.9,
                0.2,
                "right",
                1.8,
                2.3,
                "left",
                "exit",
                "激光剑对战",
                8120,
                9400,
                METAL_AUDIO,
                8160,
            ),
            MoveSpec(
                "scene-007",
                "hook-punch",
                "勾拳",
                "training-ground",
                None,
                "勾拳展示，短距离发力，强调贴身爆点。",
                [
                    ("host", "第六式，勾拳。动作不大，但劲要从地上拧上来。"),
                    ("host", "手臂只是一段弧，真正把人抬起来的是腰胯。"),
                    ("hero", "贴身时这一拳最狠，出得短，进得深。"),
                ],
                -1.3,
                0.1,
                "right",
                1.7,
                2.2,
                "left",
                "somersault",
                "命中特效",
                8140,
                9280,
                FIST_AUDIO,
                8200,
            ),
            MoveSpec(
                "scene-008",
                "swing-punch",
                "摆拳",
                "night-bridge",
                "中式古典大门",
                "摆拳展示，横向鞭打，强调肩线与转体同步。",
                [
                    ("host", "第七式，摆拳。拳是横向抽出去，不是整个人翻过去。"),
                    ("host", "前脚带肩，肩带拳，上身只做横甩，不做倒栽。"),
                    ("rival", "这一拳一旦甩满，边线空间会全部吃掉。"),
                ],
                -1.6,
                0.3,
                "right",
                1.7,
                2.4,
                "left",
                "big-jump",
                "命中特效",
                8100,
                9320,
                FIST_AUDIO,
                8180,
            ),
            MoveSpec(
                "scene-009",
                "straight-punch",
                "直拳",
                "training-ground",
                None,
                "直拳展示，路线最短，出拳和回收都要干净。",
                [
                    ("host", "第八式，直拳。最短的路线，最直接的穿透。"),
                    ("host", "前肩微收，拳锋一路直送，打完立刻回线。"),
                    ("hero", "直拳不花，但准、快、狠，最适合接在连招末段。"),
                ],
                -1.4,
                0.4,
                "right",
                1.8,
                2.5,
                "left",
                "exit",
                "命中特效",
                8080,
                9280,
                FIST_AUDIO,
                8160,
            ),
            MoveSpec(
                "scene-010",
                "combo-punch",
                "组合拳",
                "theatre-stage",
                "敞开的红色帘子-窗帘或床帘皆可",
                "组合拳展示，按直拳、勾拳、摆拳三段连续追击。",
                [
                    ("host", "第九式，组合拳。这里不是乱打，是直、勾、摆三连。"),
                    ("host", "先用直拳把线打直，再用勾拳掀底，最后摆拳横着收走。"),
                    ("hero", "三拳都要完整打满，每一拳都得让人看清。"),
                ],
                -1.8,
                0.6,
                "right",
                1.8,
                2.8,
                "left",
                "exit",
                "千军万马冲杀",
                7900,
                9400,
                FIST_AUDIO,
                8040,
                beat_start_ms=6300,
                beat_end_ms=9600,
                rival_beat_start_ms=6800,
                rival_beat_end_ms=9700,
            ),
        ]

        for index, spec in enumerate(move_specs, start=2):
            scenes.append(move_scene(index, spec))

        finale_dialogues, finale_talk, finale_expressions = build_dialogue_bundle(
            [
                ("host", "九式看完，关键都一样：路线清、重心稳、收势快。"),
                ("host", "现在把动作连起来，你会更清楚每一式的节奏差别。"),
                ("hero", "最后一轮，连招收尾。"),
            ]
        )
        finale_action_beats = [
            beat(7000, 7600, "host", "point", facing="right", emotion="charged"),
            beat(7200, 7900, "hero", "flying-kick", x0=-2.0, x1=-0.4, facing="right", emotion="charged"),
            beat(7900, 8500, "hero", "double-palm-push", x0=-0.4, x1=0.1, facing="right", emotion="charged"),
            beat(8500, 9050, "hero", "hook-punch", x0=0.1, x1=0.5, facing="right", emotion="charged"),
            beat(9050, 9550, "hero", "straight-punch", x0=0.5, x1=0.9, facing="right", emotion="charged"),
            beat(7200, 9400, "rival", "exit", x0=1.9, x1=3.1, facing="left", emotion="hurt"),
        ]
        scenes.append(
            scene(
                "scene-011",
                background="temple-courtyard",
                floor=FLOOR_BY_BACKGROUND["temple-courtyard"],
                duration_ms=SCENE_DURATION_MS,
                summary="收束场景，将飞踢、双掌平推、勾拳和直拳串成一段连招展示。",
                camera=scene_camera(11, finale=True),
                props=default_props("temple-courtyard"),
                foregrounds=default_foregrounds("temple-courtyard"),
                actors=[
                    mid_actor("host", -3.1, facing="right", scale=0.90, z=-0.28),
                    front_actor("hero", -1.8, facing="right", scale=1.05),
                    front_actor("rival", 1.9, facing="left", scale=1.0),
                ],
                beats=[*trim_talk_beats_for_actions(finale_talk, finale_action_beats), *finale_action_beats],
                expressions=finale_expressions,
                dialogues=finale_dialogues,
                effects=[
                    effect("热烈鼓掌", start_ms=200, end_ms=1800, alpha=0.18, playback_speed=0.90),
                    effect("命中特效", start_ms=7600, end_ms=9400, alpha=0.20, playback_speed=0.92),
                ],
                audio=scene_audio(
                    bgm=bgm_for_scene(11),
                    sfx=[
                        audio_sfx(FIST_AUDIO, start_ms=7600, volume=0.96),
                        audio_sfx(FIST_AUDIO, start_ms=8260, volume=1.04),
                        audio_sfx(FIST_AUDIO, start_ms=9180, volume=1.06),
                        audio_sfx(BOOM_AUDIO, start_ms=8860, volume=0.82),
                    ],
                ),
            )
        )

        return scenes


SCRIPT = MartialMovesShowcaseVideo()


def build_story() -> dict:
    return SCRIPT.build_story()


def main() -> int:
    return SCRIPT()


if __name__ == "__main__":
    raise SystemExit(main())
