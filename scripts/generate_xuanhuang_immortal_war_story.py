#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from storyboard import (
    BaseVideoScript,
    actor,
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
    "width": 960,
    "height": 540,
    "fps": 12,
    "renderer": "pygame_2d",
    "video_codec": "mpeg4",
    "encoder_preset": "ultrafast",
    "crf": 26,
    "subtitle_mode": "bottom",
    "tts_enabled": True,
    "stage_layout": {
        "effect_overlay_alpha": 0.9,
    },
}

CAST = [
    cast_member("lin_yuan", "林渊", "general-guard"),
    cast_member("su_li", "苏璃", "npc-girl"),
    cast_member("ye_jin", "叶烬", "detective-sleek"),
    cast_member("dao_xuan", "道玄上人", "farmer-old"),
    cast_member("mo_huang", "魔皇烬罗", "official-minister"),
    cast_member("jun_tian", "君天侯", "emperor-ming"),
    cast_member("crowd", "玄荒弟子", "npc-boy"),
]

SCENE_DURATION_MS = 15_200
DIALOGUE_WINDOWS = [
    (400, 3000),
    (3600, 6200),
    (7600, 10200),
    (11000, 14000),
]

FLOOR_BY_BACKGROUND = {
    "archive-library": "wood-plank",
    "inn-hall": "wood-plank",
    "mountain-cliff": "stone-court",
    "night-bridge": "dark-stage",
    "park-evening": "dark-stage",
    "room-day": "wood-plank",
    "street-day": "stone-court",
    "temple-courtyard": "stone-court",
    "theatre-stage": "dark-stage",
    "town-hall-records": "wood-plank",
    "training-ground": "stone-court",
}

FIST_AUDIO = "assets/audio/031_26_赤手空拳打斗的声音_爱给网_aigei_com.mp3"
METAL_AUDIO = "assets/audio/刀剑、金属碰撞（带回音）_爱给网_aigei_com.mp3"
BOOM_AUDIO = "assets/audio/音效 爆炸 爆破 爆发 战斗_爱给网_aigei_com.mp3"
HEART_AUDIO = "assets/audio/心脏怦怦跳.wav"

PROLOGUE_BGM = "assets/bgm/误入迷失森林-少年包青天.mp3"
MUSTER_BGM = "assets/bgm/御剑飞行.mp3"
WAR_BGM = "assets/bgm/杀破狼.mp3"
CRISIS_BGM = "assets/bgm/观音降临-高潮版.mp3"
RESOLVE_BGM = "assets/bgm/最后之战-热血-卢冠廷.mp3"
EPILOGUE_BGM = "assets/bgm/仙剑情缘.mp3"


DialogueLine = tuple[str, str]


@dataclass(frozen=True)
class SceneSpec:
    scene_id: str
    background: str
    summary: str
    actors: list[dict]
    props: list[dict]
    lines: list[DialogueLine]
    extra_beats: list[dict] = field(default_factory=list)
    effects: list[dict] = field(default_factory=list)
    foregrounds: list[dict] = field(default_factory=list)
    audio: dict = field(default_factory=scene_audio)
    camera: dict | None = None
    music_mode: str = "prologue"


def line(speaker_id: str, text: str) -> DialogueLine:
    return (speaker_id, text)


def front_actor(actor_id: str, x: float, *, facing: str, scale: float = 1.0, z: float = 0.0) -> dict:
    return actor(actor_id, x, z=z, facing=facing, scale=scale)


def mid_actor(actor_id: str, x: float, *, facing: str, scale: float = 0.94, z: float = -0.14) -> dict:
    return actor(actor_id, x, z=z, facing=facing, scale=scale, layer="mid")


def back_actor(actor_id: str, x: float, *, facing: str, scale: float = 0.88, z: float = -0.72) -> dict:
    return actor(actor_id, x, z=z, facing=facing, scale=scale, layer="back")


def infer_expression(text: str) -> str:
    if any(token in text for token in ("杀", "斩", "破", "魔", "阵", "封", "轰", "退", "战")):
        return "angry"
    if any(token in text for token in ("快", "立刻", "跟上", "稳住", "冲", "上空")):
        return "excited"
    if any(token in text for token in ("阵眼", "禁制", "灵脉", "剑阵", "虚空", "破绽")):
        return "thinking"
    if any(token in text for token in ("赢了", "守住", "回城", "放心")):
        return "smile"
    return "neutral"


def build_dialogue_bundle(lines: Sequence[DialogueLine]) -> tuple[list[dict], list[dict], list[dict]]:
    dialogue_items: list[dict] = []
    talk_beats: list[dict] = []
    expressions_track: list[dict] = []
    for (start_ms, end_ms), (speaker_id, text) in zip(DIALOGUE_WINDOWS, lines):
        dialogue_items.append(dialogue(start_ms, end_ms, speaker_id, text))
        talk_beats.append(beat(start_ms, end_ms, speaker_id, "talk", emotion="focused"))
        expressions_track.append(expression(speaker_id, start_ms, end_ms, infer_expression(text)))
    return dialogue_items, talk_beats, expressions_track


def trim_talk_beats_for_actions(talk_beats: Sequence[dict], action_beats: Sequence[dict]) -> list[dict]:
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


def scene_camera(scene_index: int, *, battle: bool, aerial: bool = False) -> dict:
    if aerial:
        return camera_pan(
            x=-0.32,
            z=0.07,
            zoom=1.12,
            to_x=0.28,
            to_z=0.02,
            to_zoom=1.2,
            ease="ease-in-out",
        )
    if battle:
        return camera_pan(
            x=-0.25 + 0.05 * (scene_index % 3),
            z=0.04,
            zoom=1.08,
            to_x=0.18 - 0.04 * (scene_index % 2),
            to_z=0.0,
            to_zoom=1.16,
            ease="ease-in-out",
        )
    if scene_index in {0, 10, 19}:
        return camera_static(x=0.0, z=0.03, zoom=1.08)
    return camera_pan(
        x=-0.16,
        z=0.02,
        zoom=1.0,
        to_x=0.12,
        to_z=0.0,
        to_zoom=1.06,
        ease="ease-in-out",
    )


def war_props(scene_index: int, *, interior: bool = False, night: bool = False, ritual: bool = False) -> list[dict]:
    if ritual:
        return [
            prop("training-drum", -3.6, -1.04, scale=0.94, layer="back"),
            prop("weapon-rack", 3.4, -1.0, scale=0.94, layer="mid"),
            prop("lantern", -0.3, -0.92, scale=1.02, layer="front"),
        ]
    if interior:
        return [
            prop("wall-window", -3.8, -1.0, scale=0.92, layer="back"),
            prop("wall-door", 3.8, -1.02, scale=0.92, layer="back"),
            prop("weapon-rack" if scene_index % 2 == 0 else "training-drum", 0.0, -1.02, scale=0.9, layer="mid"),
            prop("lantern", 3.1, -0.92, scale=0.94, layer="front"),
        ]
    props = [prop("house", 0.0, -1.08, scale=0.98, layer="back")]
    if night:
        props.extend(
            [
                prop("moon", 3.7, -0.44, scale=0.74, layer="back"),
                prop("star", -3.6, -0.56, scale=0.55, layer="back"),
                prop("lantern", -3.3, -0.92, scale=0.94, layer="front"),
            ]
        )
    else:
        props.extend(
            [
                prop("horse", -3.8, -0.94, scale=0.8, layer="front"),
                prop("wall-door", 3.8, -1.02, scale=0.9, layer="back"),
            ]
        )
    if scene_index % 2 == 0:
        props.append(prop("weapon-rack", 0.9, -1.0, scale=0.9, layer="mid"))
    return props


def war_audio(*, metal: bool = False, boom: bool = False, heart: bool = False, inferno: bool = False) -> dict:
    sfx = [
        {"asset_path": FIST_AUDIO, "start_ms": 3900, "volume": 0.86, "loop": False},
        {"asset_path": FIST_AUDIO, "start_ms": 7600, "volume": 0.84, "loop": False},
    ]
    if metal:
        sfx.append({"asset_path": METAL_AUDIO, "start_ms": 5600, "volume": 0.76, "loop": False})
        sfx.append({"asset_path": METAL_AUDIO, "start_ms": 9800, "volume": 0.72, "loop": False})
    if boom:
        sfx.append({"asset_path": BOOM_AUDIO, "start_ms": 6900, "volume": 0.74, "loop": False})
        sfx.append({"asset_path": BOOM_AUDIO, "start_ms": 11200, "volume": 0.66, "loop": False})
    if heart:
        sfx.append({"asset_path": HEART_AUDIO, "start_ms": 2200, "volume": 0.62, "loop": False})
    if inferno:
        sfx.append({"asset_path": BOOM_AUDIO, "start_ms": 2800, "volume": 0.52, "loop": False})
    return scene_audio(sfx=sfx)


def scene_bgm(scene_index: int) -> dict:
    if scene_index <= 2:
        path = PROLOGUE_BGM
        volume = 0.52
    elif scene_index <= 6:
        path = MUSTER_BGM
        volume = 0.58
    elif scene_index <= 9:
        path = WAR_BGM
        volume = 0.64
    elif scene_index <= 12:
        path = CRISIS_BGM
        volume = 0.6
    elif scene_index <= 18:
        path = RESOLVE_BGM
        volume = 0.66
    else:
        path = EPILOGUE_BGM
        volume = 0.52
    return {"asset_path": path, "start_ms": 0, "volume": volume, "loop": True}


def default_foregrounds(scene_index: int, background: str) -> list[dict]:
    if background in {"temple-courtyard", "theatre-stage"}:
        return [
            foreground(
                "敞开的红色帘子-窗帘或床帘皆可",
                asset_path="assets/foreground/敞开的红色帘子-窗帘或床帘皆可.webp",
                x=-0.02,
                y=-0.04,
                width=1.04,
                height=1.08,
                opacity=1.0,
            )
        ]
    if background in {"room-day", "archive-library", "town-hall-records", "inn-hall"}:
        fg_id = "开着门的室内" if scene_index % 2 == 0 else "古典木门木窗-有点日式风格"
        fg_path = "assets/foreground/开着门的室内.webp" if fg_id == "开着门的室内" else "assets/foreground/古典木门木窗-有点日式风格.webp"
        return [foreground(fg_id, asset_path=fg_path, x=-0.01, y=-0.02, width=1.02, height=1.06, opacity=1.0)]
    if background in {"night-bridge", "park-evening", "street-day"}:
        return [
            foreground(
                "中式古典大门",
                asset_path="assets/foreground/中式古典大门.webp",
                x=-0.01,
                y=-0.02,
                width=1.02,
                height=1.06,
                opacity=1.0,
            )
        ]
    return []


def duel_beats(left_id: str, right_id: str, *, left_x: float, right_x: float, airborne: bool = False, heavy: bool = False) -> list[dict]:
    jump_z = 0.16 if airborne else 0.04
    return [
        beat(3300, 4500, left_id, "straight-punch", x0=left_x, x1=left_x + 0.45, z0=0.0, z1=jump_z, facing="right", effect="hit"),
        beat(4700, 5900, right_id, "hook-punch", x0=right_x, x1=right_x - 0.38, z0=0.0, z1=jump_z, facing="left", effect="hit"),
        beat(6400, 7700, left_id, "combo-punch" if heavy else "swing-punch", x0=left_x + 0.25, x1=left_x + 0.8, z0=jump_z, z1=0.02, facing="right", effect="dragon-palm" if heavy else "hit"),
        beat(8200, 9400, right_id, "diagonal-kick" if airborne else "spin-kick", x0=right_x - 0.18, x1=right_x - 0.76, z0=jump_z, z1=0.02, facing="left", effect="thunder-strike"),
        beat(10000, 11300, left_id, "double-palm-push", x0=left_x + 0.44, x1=left_x + 0.98, z0=0.0, z1=0.0, facing="right", effect="sword-arc"),
    ]


SCENE_SPECS = [
    SceneSpec(
        scene_id="scene-001",
        background="mountain-cliff",
        summary="玄荒边境雷海翻卷，林渊和苏璃在崖顶看到天外裂缝被黑色巨阵撕开，魔皇烬罗率先现身。",
        actors=[
            front_actor("dao_xuan", -2.5, facing="right"),
            front_actor("lin_yuan", 0.2, facing="left"),
            back_actor("crowd", 3.3, facing="left"),
        ],
        props=war_props(0, night=True),
        lines=[
            line("dao_xuan", "玄荒天门开了，今夜若守不住，整片仙域都会被魔潮吞进去。"),
            line("lin_yuan", "老前辈，守城可以，若要斩皇，我来做第一剑。"),
            line("su_li", "林渊，天上那道黑圈还在扩张，烬罗已经在借它抽走灵脉。"),
            line("lin_yuan", "那就从今夜开始，把他的路一寸寸砍断。"),
        ],
        effects=[
            effect("英雄出场", start_ms=200, end_ms=2400, alpha=0.18, playback_speed=0.92),
            effect("黑洞旋转", start_ms=2500, end_ms=14800, alpha=0.18, playback_speed=0.85),
        ],
        audio=war_audio(heart=True),
    ),
    SceneSpec(
        scene_id="scene-002",
        background="temple-courtyard",
        summary="君天侯在镇天殿召集诸宗修士，命所有御剑营、符阵营和城防军同时集结。",
        actors=[
            front_actor("jun_tian", -2.2, facing="right"),
            front_actor("su_li", 0.4, facing="left"),
            mid_actor("lin_yuan", 2.7, facing="left"),
            back_actor("crowd", 3.8, facing="left"),
        ],
        props=war_props(1, ritual=True),
        lines=[
            line("jun_tian", "今夜不是守一座城，是守玄荒万民的明日。"),
            line("su_li", "东城御剑营已经备好，天火符阵还能再撑两轮。"),
            line("lin_yuan", "把最好的灵箭留给北门，我去最危险的地方。"),
            line("jun_tian", "你去北天门，我给你城中最后一面战旗。"),
        ],
        effects=[
            effect("英雄出场", start_ms=900, end_ms=3200, alpha=0.17, playback_speed=0.92),
            effect("热烈鼓掌", start_ms=11800, end_ms=14600, alpha=0.15, playback_speed=0.95),
        ],
        audio=war_audio(),
    ),
    SceneSpec(
        scene_id="scene-003",
        background="archive-library",
        summary="叶烬在禁书楼里翻出远古战图，发现黑洞旋转的中心并不是天空，而是埋在城下的断龙骨。",
        actors=[
            front_actor("ye_jin", -2.3, facing="right"),
            front_actor("dao_xuan", 0.6, facing="left"),
            back_actor("su_li", 3.0, facing="left"),
        ],
        props=war_props(2, interior=True),
        lines=[
            line("ye_jin", "找到了，烬罗不是在借天门，是在借城底断龙骨反抽灵力。"),
            line("dao_xuan", "怪不得黑圈不往外走，反而一直对着北门压。"),
            line("su_li", "若断龙骨被抽空，整座城会从地心开始塌。"),
            line("ye_jin", "所以我们得有人上天断阵，也得有人下地护骨。"),
        ],
        effects=[
            effect("黑洞旋转", start_ms=2600, end_ms=7200, alpha=0.16, playback_speed=0.9),
        ],
        audio=war_audio(heart=True),
    ),
    SceneSpec(
        scene_id="scene-004",
        background="night-bridge",
        summary="苏璃带御剑营穿过夜桥抢占风口，先一步看到魔潮在河对岸集结成阵。",
        actors=[
            front_actor("su_li", -2.1, facing="right"),
            front_actor("lin_yuan", 0.2, facing="left"),
            back_actor("crowd", 3.5, facing="left"),
        ],
        props=war_props(3, night=True),
        lines=[
            line("su_li", "听这桥下的风声，魔骑至少三阵，他们想冲开北门直插皇城。"),
            line("lin_yuan", "先别让他们过桥，给我半炷香，我把桥头变成剑场。"),
            line("crowd", "林统领，西侧也有黑影，像是空骑！"),
            line("lin_yuan", "空中交给我，地上交给你们，今天谁都别往后退。"),
        ],
        effects=[
            effect("御剑飞行", start_ms=400, end_ms=3000, alpha=0.16, playback_speed=0.95),
            effect("千军万马冲杀", start_ms=7600, end_ms=14800, alpha=0.18, playback_speed=0.9),
        ],
        audio=war_audio(metal=True, boom=True),
    ),
    SceneSpec(
        scene_id="scene-005",
        background="street-day",
        summary="第一波魔骑冲入外街，玄荒弟子和城防军在长街鏖战，烟火和血雾一起卷上牌楼。",
        actors=[
            front_actor("lin_yuan", -2.0, facing="right"),
            front_actor("crowd", 0.8, facing="left", scale=0.96),
            mid_actor("mo_huang", 3.1, facing="left"),
        ],
        props=war_props(4, night=False),
        lines=[
            line("crowd", "他们冲进城了，街口的符灯全被撞碎！"),
            line("lin_yuan", "碎了就碎了，人还在，城就还在。"),
            line("mo_huang", "林渊，你们这点人挡不住万魔奔流，跪下我还能留你一魂。"),
            line("lin_yuan", "你来试试，看是你收魂快，还是我斩头快。"),
        ],
        extra_beats=duel_beats("lin_yuan", "mo_huang", left_x=-1.9, right_x=2.9, heavy=True),
        effects=[
            effect("千军万马冲杀", start_ms=900, end_ms=5200, alpha=0.17, playback_speed=0.95),
            effect("爆炸特效", start_ms=6400, end_ms=7600, alpha=0.18, playback_speed=0.96),
            effect("命中特效", start_ms=8200, end_ms=9400, alpha=0.18, playback_speed=0.96),
        ],
        audio=war_audio(metal=True, boom=True),
    ),
    SceneSpec(
        scene_id="scene-006",
        background="training-ground",
        summary="北门校场临时改成阵前决斗场，叶烬以激光剑阵试探魔皇护身罡罩的节奏。",
        actors=[
            front_actor("ye_jin", -2.2, facing="right"),
            front_actor("mo_huang", 1.9, facing="left"),
            back_actor("crowd", 3.8, facing="left"),
        ],
        props=war_props(5, ritual=True),
        lines=[
            line("ye_jin", "你的护罩每隔两息会空一次，我看见了。"),
            line("mo_huang", "看见不等于碰得到，凡人的眼，跟不上魔皇的刀。"),
            line("lin_yuan", "叶烬，逼他再开一次外罩，我来补最后那一剑。"),
            line("ye_jin", "好，那就让他先听一遍天裂的声音。"),
        ],
        extra_beats=duel_beats("ye_jin", "mo_huang", left_x=-2.1, right_x=2.0, airborne=True, heavy=True),
        effects=[
            effect("激光剑对战", start_ms=3200, end_ms=10800, alpha=0.18, playback_speed=0.96),
            effect("命中特效", start_ms=10800, end_ms=12200, alpha=0.18, playback_speed=0.92),
        ],
        audio=war_audio(metal=True, boom=True),
    ),
    SceneSpec(
        scene_id="scene-007",
        background="park-evening",
        summary="苏璃率御剑营从云层俯冲，第一次把整支空骑压回城外，天上满是剑痕与火雨。",
        actors=[
            front_actor("su_li", -2.3, facing="right"),
            front_actor("lin_yuan", 0.5, facing="left"),
            back_actor("crowd", 3.6, facing="left"),
        ],
        props=war_props(6, night=True),
        lines=[
            line("su_li", "御剑营随我下压，先扫掉他们最前面的黑翼骑。"),
            line("lin_yuan", "你把天路打开，我从下方接斩，别让他们靠近城心。"),
            line("crowd", "苏统领的剑光压住了，他们真的被逼退了！"),
            line("su_li", "别欢呼，第二波正在抬头，把高度再拉上去。"),
        ],
        extra_beats=[
            beat(3500, 4700, "su_li", "flying-kick", x0=-2.1, x1=-1.2, z0=0.0, z1=0.22, facing="right", effect="thunder-strike"),
            beat(5000, 6200, "lin_yuan", "double-palm-push", x0=0.1, x1=0.9, z0=0.0, z1=0.08, facing="right", effect="dragon-palm"),
            beat(7600, 8800, "su_li", "spin-kick", x0=-1.4, x1=-0.7, z0=0.18, z1=0.04, facing="right", effect="sword-arc"),
        ],
        effects=[
            effect("御剑飞行", start_ms=300, end_ms=9800, alpha=0.18, playback_speed=0.94),
            effect("英雄出场", start_ms=9800, end_ms=12200, alpha=0.16, playback_speed=0.92),
        ],
        audio=war_audio(metal=True, boom=True),
        camera=scene_camera(6, battle=True, aerial=True),
    ),
    SceneSpec(
        scene_id="scene-008",
        background="mountain-cliff",
        summary="魔皇烬罗在崖外抬起死亡光线，整条山脉都被照成赤白色，断壁一层层崩碎。",
        actors=[
            front_actor("mo_huang", -2.2, facing="right"),
            front_actor("lin_yuan", 0.8, facing="left"),
            back_actor("su_li", 3.2, facing="left"),
        ],
        props=war_props(7, night=True),
        lines=[
            line("mo_huang", "看清楚了，这才是魔域帝兵真正的光。"),
            line("su_li", "那束光在切山，不是在吓人，林渊快闪开！"),
            line("lin_yuan", "躲不开就斩开，给我把城中的防阵继续撑住。"),
            line("mo_huang", "你若真能斩断，就来试试我头顶这一轮死光。"),
        ],
        extra_beats=[
            beat(7600, 8900, "lin_yuan", "double-palm-push", x0=0.6, x1=1.1, z0=0.0, z1=0.0, facing="left", effect="dragon-palm"),
            beat(9400, 10800, "lin_yuan", "diagonal-kick", x0=0.9, x1=0.2, z0=0.0, z1=0.18, facing="left", effect="thunder-strike"),
        ],
        effects=[
            effect("死亡光线特效", start_ms=3200, end_ms=9800, alpha=0.18, playback_speed=0.96),
            effect("爆炸特效", start_ms=9800, end_ms=11600, alpha=0.18, playback_speed=0.92),
        ],
        audio=war_audio(boom=True, heart=True),
    ),
    SceneSpec(
        scene_id="scene-009",
        background="temple-courtyard",
        summary="道玄上人开启古塔中的灵炮核心，以龟派气功一般的白色洪流反轰高空死光。",
        actors=[
            front_actor("dao_xuan", -2.2, facing="right"),
            front_actor("jun_tian", 0.4, facing="left"),
            back_actor("crowd", 3.5, facing="left"),
        ],
        props=war_props(8, ritual=True),
        lines=[
            line("dao_xuan", "断龙骨不能再给他们抽了，老夫把最后一点元炁全推上去。"),
            line("jun_tian", "上人，你这一掌出去，就再没有回头的灵脉了。"),
            line("dao_xuan", "人活到我这岁数，本就该把最后一口气交在该交的地方。"),
            line("crowd", "白光上去了，死光被顶住了，北天门还没塌！"),
        ],
        extra_beats=[
            beat(4300, 5600, "dao_xuan", "double-palm-push", x0=-2.1, x1=-1.2, z0=0.0, z1=0.06, facing="right", effect="dragon-palm"),
            beat(6000, 7300, "dao_xuan", "double-palm-push", x0=-1.9, x1=-1.0, z0=0.0, z1=0.08, facing="right", effect="sword-arc"),
        ],
        effects=[
            effect("龟派气功", start_ms=3600, end_ms=10800, alpha=0.18, playback_speed=0.94),
            effect("启动大招特效", start_ms=2500, end_ms=4200, alpha=0.16, playback_speed=0.92),
        ],
        audio=war_audio(boom=True),
    ),
    SceneSpec(
        scene_id="scene-010",
        background="street-day",
        summary="城西火雨坠落，数条街同时起火，苏璃带人从火线上硬生生拖出伤员和符阵石。",
        actors=[
            front_actor("su_li", -2.0, facing="right"),
            front_actor("crowd", 0.9, facing="left", scale=0.96),
            back_actor("jun_tian", 3.1, facing="left"),
        ],
        props=war_props(9, night=False),
        lines=[
            line("crowd", "西街烧起来了，符阵石还没抬走！"),
            line("su_li", "先救人，再救阵石，谁还能走就跟我往火里冲。"),
            line("jun_tian", "我把后方水阵调来，你们只要给我守住一条路。"),
            line("su_li", "一条不够，今晚我要给整座城抢出第二条命。"),
        ],
        extra_beats=[
            beat(5200, 6500, "su_li", "flying-kick", x0=-2.0, x1=-1.0, z0=0.0, z1=0.22, facing="right", effect="thunder-strike"),
            beat(8000, 9300, "su_li", "straight-punch", x0=-1.2, x1=-0.5, z0=0.08, z1=0.0, facing="right", effect="hit"),
        ],
        effects=[
            effect("熊熊大火", start_ms=300, end_ms=14600, alpha=0.18, playback_speed=0.9),
            effect("火烧赤壁", start_ms=3400, end_ms=11200, alpha=0.16, playback_speed=0.92),
        ],
        audio=war_audio(boom=True, inferno=True),
    ),
    SceneSpec(
        scene_id="scene-011",
        background="town-hall-records",
        summary="叶烬和林渊在临时军帐里拼出新的破阵图，决定兵分三路去断黑洞、护龙骨、杀魔皇。",
        actors=[
            front_actor("ye_jin", -2.2, facing="right"),
            front_actor("lin_yuan", 0.6, facing="left"),
            back_actor("jun_tian", 3.0, facing="left"),
        ],
        props=war_props(10, interior=True),
        lines=[
            line("ye_jin", "黑洞旋转的核心被道玄上人拖慢了，现在正是最脆的时候。"),
            line("lin_yuan", "我去杀烬罗，苏璃去断空骑，你带人下地宫护龙骨。"),
            line("jun_tian", "若谁那一路先断，我就把剩下的兵全压过去。"),
            line("lin_yuan", "好，今夜不拼哪一路最难，只拼谁更快。"),
        ],
        effects=[
            effect("黑洞旋转", start_ms=4200, end_ms=8600, alpha=0.14, playback_speed=0.92),
        ],
        audio=war_audio(heart=True),
    ),
    SceneSpec(
        scene_id="scene-012",
        background="room-day",
        summary="地下龙骨殿内，叶烬带弟子与魔兵短兵相接，狭窄石道里全是拳脚和剑光的回声。",
        actors=[
            front_actor("ye_jin", -2.1, facing="right"),
            front_actor("crowd", 0.8, facing="left", scale=0.96),
            front_actor("mo_huang", 3.0, facing="left", scale=0.94),
        ],
        props=war_props(11, interior=True),
        lines=[
            line("ye_jin", "地宫太窄，别排阵，直接贴身打，把他们堵死在石阶上。"),
            line("crowd", "叶统领，他们从后门也压进来了！"),
            line("ye_jin", "那就前后一起砍，谁先倒下谁就永远埋在这。"),
            line("mo_huang", "你以为守住一截龙骨就有用？真正的刀在天上。"),
        ],
        extra_beats=duel_beats("ye_jin", "mo_huang", left_x=-2.0, right_x=2.8, heavy=False),
        effects=[
            effect("命中特效", start_ms=4300, end_ms=5400, alpha=0.18, playback_speed=0.92),
            effect("激光剑对战", start_ms=7600, end_ms=11600, alpha=0.16, playback_speed=0.96),
        ],
        audio=war_audio(metal=True, boom=True),
    ),
    SceneSpec(
        scene_id="scene-013",
        background="training-ground",
        summary="林渊独自回到校场中央，借最后一面战旗蓄势，准备从地面直冲高空黑洞。",
        actors=[
            front_actor("lin_yuan", -1.8, facing="right"),
            front_actor("dao_xuan", 0.9, facing="left"),
            back_actor("crowd", 3.7, facing="left"),
        ],
        props=war_props(12, ritual=True),
        lines=[
            line("dao_xuan", "林渊，这一冲你会先撞上黑洞，再撞上烬罗。"),
            line("lin_yuan", "那就都撞开，若连我都不敢上去，下面的人更没退路。"),
            line("crowd", "统领，战旗还在，它还在亮！"),
            line("lin_yuan", "亮就够了，借我一口气，我去把天门砸下来。"),
        ],
        extra_beats=[
            beat(4200, 5400, "lin_yuan", "double-palm-push", x0=-1.8, x1=-0.9, z0=0.0, z1=0.05, facing="right", effect="dragon-palm"),
            beat(6000, 7300, "lin_yuan", "flying-kick", x0=-1.3, x1=-0.3, z0=0.04, z1=0.22, facing="right", effect="thunder-strike"),
            beat(8000, 9300, "lin_yuan", "combo-punch", x0=-0.4, x1=0.5, z0=0.18, z1=0.0, facing="right", effect="sword-arc"),
        ],
        effects=[
            effect("启动大招特效", start_ms=2600, end_ms=5000, alpha=0.18, playback_speed=0.92),
            effect("英雄出场", start_ms=9300, end_ms=12000, alpha=0.16, playback_speed=0.9),
        ],
        audio=war_audio(boom=True),
    ),
    SceneSpec(
        scene_id="scene-014",
        background="night-bridge",
        summary="桥外第二波魔骑杀到，苏璃在低空斜掠，一边截杀空骑，一边把他们往河面压。",
        actors=[
            front_actor("su_li", -2.1, facing="right"),
            front_actor("crowd", 0.6, facing="left"),
            mid_actor("mo_huang", 3.0, facing="left"),
        ],
        props=war_props(13, night=True),
        lines=[
            line("su_li", "空骑别升太高，压他们贴着河面，让风把他们自己卷乱。"),
            line("crowd", "他们掉下来了，好几匹黑翼已经撞进水里！"),
            line("mo_huang", "一个女子，也敢在本皇头顶拉开空战。"),
            line("su_li", "你若真有本事，就别总躲在别人后面放光。"),
        ],
        extra_beats=[
            beat(3500, 4800, "su_li", "diagonal-kick", x0=-2.0, x1=-1.1, z0=0.0, z1=0.2, facing="right", effect="thunder-strike"),
            beat(5200, 6500, "su_li", "spin-kick", x0=-1.0, x1=-0.2, z0=0.16, z1=0.06, facing="right", effect="hit"),
            beat(8400, 9700, "su_li", "double-palm-push", x0=-0.7, x1=0.2, z0=0.0, z1=0.06, facing="right", effect="sword-arc"),
        ],
        effects=[
            effect("御剑飞行", start_ms=300, end_ms=9800, alpha=0.18, playback_speed=0.95),
            effect("飞踢", start_ms=5200, end_ms=6800, alpha=0.18, playback_speed=0.95),
        ],
        audio=war_audio(metal=True, boom=True),
        camera=scene_camera(13, battle=True, aerial=True),
    ),
    SceneSpec(
        scene_id="scene-015",
        background="mountain-cliff",
        summary="林渊冲进黑洞边缘，第一次和烬罗在天门前真正交手，剑气和魔焰把夜空割成两半。",
        actors=[
            front_actor("lin_yuan", -1.9, facing="right"),
            front_actor("mo_huang", 1.9, facing="left"),
            back_actor("su_li", 3.5, facing="left"),
        ],
        props=war_props(14, night=True),
        lines=[
            line("lin_yuan", "烬罗，地上的人你压不死，现在轮到我来压你。"),
            line("mo_huang", "你冲得上来，是因为我愿意让你看见真正的深渊。"),
            line("su_li", "林渊，他脚下那圈黑焰在吸你，不要跟他硬拼。"),
            line("lin_yuan", "不硬拼我就没机会了，今夜我只要一个破口。"),
        ],
        extra_beats=duel_beats("lin_yuan", "mo_huang", left_x=-1.8, right_x=1.9, airborne=True, heavy=True),
        effects=[
            effect("黑洞旋转", start_ms=200, end_ms=14600, alpha=0.18, playback_speed=0.86),
            effect("死亡光线特效", start_ms=6100, end_ms=9600, alpha=0.18, playback_speed=0.96),
            effect("激光剑对战", start_ms=9800, end_ms=12800, alpha=0.16, playback_speed=0.95),
        ],
        audio=war_audio(metal=True, boom=True, heart=True),
        camera=scene_camera(14, battle=True, aerial=True),
    ),
    SceneSpec(
        scene_id="scene-016",
        background="street-day",
        summary="城中百姓自发抬起残阵和水桶，配合守军压火守街，整座城在混战里反而越打越稳。",
        actors=[
            front_actor("jun_tian", -2.0, facing="right"),
            front_actor("crowd", 0.6, facing="left", scale=0.98),
            back_actor("su_li", 3.0, facing="left"),
        ],
        props=war_props(15, night=False),
        lines=[
            line("jun_tian", "不要只看天上，城里每守住一条街，就是给林渊多一口气。"),
            line("crowd", "殿下放心，北街没退，西街也不会退！"),
            line("su_li", "把剩下的灵水都拉来，我要让火线停在这条街口。"),
            line("jun_tian", "玄荒的城，今晚由所有还站着的人一起守。"),
        ],
        effects=[
            effect("熊熊大火", start_ms=300, end_ms=8000, alpha=0.16, playback_speed=0.9),
            effect("热烈鼓掌", start_ms=10400, end_ms=14400, alpha=0.14, playback_speed=0.96),
        ],
        audio=war_audio(boom=True, inferno=True),
    ),
    SceneSpec(
        scene_id="scene-017",
        background="inn-hall",
        summary="地宫出口终于被打通，叶烬带人抬着最后一节龙骨残片冲出火场，准备送上天门做封印钉。",
        actors=[
            front_actor("ye_jin", -2.0, facing="right"),
            front_actor("dao_xuan", 0.7, facing="left"),
            back_actor("crowd", 3.2, facing="left"),
        ],
        props=war_props(16, interior=True),
        lines=[
            line("ye_jin", "龙骨残片拿到了，只要把它送上去，黑洞就会自己闭一半。"),
            line("dao_xuan", "那就别再省了，把最后的御风符全烧掉。"),
            line("crowd", "外面的火还没灭，抬着龙骨冲出去会被看见！"),
            line("ye_jin", "看见就看见，今夜本来就该让所有人看见我们还没倒。"),
        ],
        effects=[
            effect("英雄出场", start_ms=900, end_ms=3200, alpha=0.16, playback_speed=0.92),
            effect("熊熊大火", start_ms=6400, end_ms=13800, alpha=0.16, playback_speed=0.9),
        ],
        audio=war_audio(boom=True, inferno=True),
    ),
    SceneSpec(
        scene_id="scene-018",
        background="park-evening",
        summary="叶烬御风把龙骨残片送上天门，苏璃在半空接应，二人和空骑群爆发一场最密的追击战。",
        actors=[
            front_actor("ye_jin", -2.3, facing="right"),
            front_actor("su_li", 0.2, facing="left"),
            back_actor("crowd", 3.4, facing="left"),
        ],
        props=war_props(17, night=True),
        lines=[
            line("ye_jin", "龙骨在我手里，谁想抢，就先把命给我留下。"),
            line("su_li", "你只管往上送，我替你把后面的黑翼全剪掉。"),
            line("crowd", "天上那团黑影追得太近了，他们要撞上来了！"),
            line("su_li", "那就让他们撞，我这一轮转身，专门等他们贴脸。"),
        ],
        extra_beats=[
            beat(3900, 5200, "su_li", "spin-kick", x0=0.0, x1=0.8, z0=0.08, z1=0.18, facing="right", effect="hit"),
            beat(5600, 6900, "ye_jin", "straight-punch", x0=-2.1, x1=-1.1, z0=0.0, z1=0.1, facing="right", effect="sword-arc"),
            beat(7600, 8900, "su_li", "flying-kick", x0=0.6, x1=1.3, z0=0.16, z1=0.24, facing="right", effect="thunder-strike"),
        ],
        effects=[
            effect("御剑飞行", start_ms=300, end_ms=13800, alpha=0.18, playback_speed=0.95),
            effect("飞踢", start_ms=7600, end_ms=9000, alpha=0.18, playback_speed=0.95),
            effect("命中特效", start_ms=9200, end_ms=10800, alpha=0.16, playback_speed=0.92),
        ],
        audio=war_audio(metal=True, boom=True),
        camera=scene_camera(18, battle=True, aerial=True),
    ),
    SceneSpec(
        scene_id="scene-019",
        background="theatre-stage",
        summary="龙骨残片刺入天门，林渊趁黑洞震荡的刹那发动终局连招，和烬罗在半空决出生死。",
        actors=[
            front_actor("lin_yuan", -1.8, facing="right"),
            front_actor("mo_huang", 2.0, facing="left"),
            back_actor("su_li", 3.6, facing="left"),
        ],
        props=war_props(18, ritual=True),
        lines=[
            line("lin_yuan", "就是现在，黑洞已经抖了，你再也吸不稳这片天。"),
            line("mo_huang", "就算抖，我也能拖着你们一起坠下去。"),
            line("su_li", "林渊，我把风口给你打开，所有空骑已经退开了！"),
            line("lin_yuan", "那就别再等了，玄荒这一剑，现在落。"),
        ],
        extra_beats=[
            beat(3300, 4600, "lin_yuan", "straight-punch", x0=-1.7, x1=-0.8, z0=0.0, z1=0.1, facing="right", effect="hit"),
            beat(4700, 6000, "lin_yuan", "hook-punch", x0=-0.9, x1=-0.1, z0=0.08, z1=0.12, facing="right", effect="dragon-palm"),
            beat(6100, 7400, "lin_yuan", "swing-punch", x0=-0.2, x1=0.8, z0=0.12, z1=0.08, facing="right", effect="sword-arc"),
            beat(7700, 9000, "lin_yuan", "combo-punch", x0=0.6, x1=1.5, z0=0.08, z1=0.02, facing="right", effect="thunder-strike"),
            beat(9600, 11100, "mo_huang", "diagonal-kick", x0=2.0, x1=1.0, z0=0.12, z1=0.0, facing="left", effect="死亡光线特效"),
            beat(11200, 12600, "lin_yuan", "double-palm-push", x0=1.0, x1=1.8, z0=0.0, z1=0.04, facing="right", effect="dragon-palm"),
        ],
        effects=[
            effect("黑洞旋转", start_ms=200, end_ms=6400, alpha=0.18, playback_speed=0.88),
            effect("龟派气功", start_ms=6400, end_ms=9200, alpha=0.18, playback_speed=0.94),
            effect("死亡光线特效", start_ms=9400, end_ms=11200, alpha=0.18, playback_speed=0.96),
            effect("爆炸特效", start_ms=11600, end_ms=13800, alpha=0.18, playback_speed=0.92),
        ],
        audio=war_audio(metal=True, boom=True, heart=True),
        camera=scene_camera(19, battle=True, aerial=True),
    ),
    SceneSpec(
        scene_id="scene-020",
        background="mountain-cliff",
        summary="黑洞彻底收缩，魔潮散尽，天边只剩缓慢飘回城中的碎光，众人站在破晓前的崖顶看着玄荒幸存下来。",
        actors=[
            front_actor("su_li", -2.2, facing="right", scale=0.94),
            front_actor("lin_yuan", 0.4, facing="left"),
            back_actor("jun_tian", 2.8, facing="left"),
            back_actor("crowd", 3.7, facing="left"),
        ],
        props=war_props(19, night=False),
        lines=[
            line("su_li", "天门合上了，风也安静了，原来真正安静下来会这么空。"),
            line("lin_yuan", "空是好事，说明今晚死死顶着的东西，终于不在了。"),
            line("jun_tian", "城还破着，可人还在，玄荒从今夜开始会是另一座城。"),
            line("lin_yuan", "那就回去吧，把剩下的火熄掉，把活着的人都带回家。"),
        ],
        effects=[
            effect("英雄出场", start_ms=200, end_ms=2200, alpha=0.14, playback_speed=0.92),
            effect("热烈鼓掌", start_ms=11200, end_ms=14400, alpha=0.14, playback_speed=0.96),
        ],
        audio=war_audio(),
    ),
]


class XuanhuangImmortalWarVideo(BaseVideoScript):
    def get_title(self) -> str:
        return "玄荒仙域大战"

    def get_theme(self) -> str:
        return "玄幻、仙域群战、御剑空战、黑洞天门、魔潮攻城、守城反击"

    def get_cast(self) -> list[dict]:
        return CAST

    def get_video_options(self) -> dict:
        return VIDEO

    def has_tts(self) -> bool:
        return True

    def get_notes(self) -> dict:
        return {
            "scene_count": len(SCENE_SPECS),
            "format": "xuanhuang-immortal-war",
            "bgm_assets": [PROLOGUE_BGM, MUSTER_BGM, WAR_BGM, CRISIS_BGM, RESOLVE_BGM, EPILOGUE_BGM],
            "featured_effects": [
                "黑洞旋转",
                "御剑飞行",
                "死亡光线特效",
                "激光剑对战",
                "龟派气功",
                "千军万马冲杀",
                "熊熊大火",
                "英雄出场",
                "飞踢",
            ],
        }

    def get_default_output(self) -> str:
        return "outputs/xuanhuang_immortal_war.mp4"

    def get_description(self) -> str:
        return "Render a dense 20-scene fantasy war with story-driven BGM progression, refreshed effects, foregrounds, TTS, and heavy combat audio."

    def get_scenes(self) -> list[dict]:
        scenes: list[dict] = []
        for scene_index, spec in enumerate(SCENE_SPECS):
            dialogue_items, talk_beats, expressions_track = build_dialogue_bundle(spec.lines)
            talk_beats = trim_talk_beats_for_actions(talk_beats, spec.extra_beats)
            beats = sorted([*talk_beats, *spec.extra_beats], key=lambda item: (item["start_ms"], item["actor_id"]))
            expressions_sorted = sorted(expressions_track, key=lambda item: (item["start_ms"], item["actor_id"]))
            battle = bool(spec.extra_beats or spec.effects)
            aerial = any((item.get("type") in {"御剑飞行", "黑洞旋转", "死亡光线特效"}) for item in spec.effects)
            audio_payload = scene_audio(
                bgm=scene_bgm(scene_index),
                sfx=list(spec.audio.get("sfx", [])),
            )
            scenes.append(
                scene(
                    spec.scene_id,
                    background=spec.background,
                    floor=FLOOR_BY_BACKGROUND[spec.background],
                    duration_ms=SCENE_DURATION_MS,
                    summary=spec.summary,
                    camera=spec.camera or scene_camera(scene_index, battle=battle, aerial=aerial),
                    effects=spec.effects,
                    foregrounds=[*default_foregrounds(scene_index, spec.background), *spec.foregrounds],
                    props=spec.props,
                    actors=spec.actors,
                    beats=beats,
                    expressions=expressions_sorted,
                    dialogues=dialogue_items,
                    audio=audio_payload,
                )
            )
        return scenes


SCRIPT = XuanhuangImmortalWarVideo()


def build_story() -> dict:
    return SCRIPT.build_story()


def main() -> int:
    return SCRIPT()


if __name__ == "__main__":
    raise SystemExit(main())
