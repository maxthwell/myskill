#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

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
        "effect_overlay_alpha": 0.86,
    },
}

CAST = [
    cast_member("lin_ye", "林野", "young-hero"),
    cast_member("han_lei", "韩烈", "general-guard"),
    cast_member("bai_ya", "白鸦", "strategist"),
    cast_member("luo_yan", "罗焰", "official-minister"),
    cast_member("tie_jiu", "铁鹫", "detective-sleek"),
    cast_member("tang_shuang", "唐霜", "swordswoman"),
    cast_member("shen_guan", "沈馆主", "farmer-old"),
    cast_member("qin_boss", "秦老板", "emperor-ming"),
    cast_member("su_mo", "苏沫", "office-worker-modern"),
    cast_member("host", "主持人", "reporter-selfie"),
    cast_member("crowd", "观众", "npc-boy"),
]

SCENE_DURATION_MS = 15_200
DIALOGUE_WINDOWS = [
    (400, 3000),
    (3600, 6200),
    (7600, 10200),
    (11000, 14000),
]

FLOOR_BY_BACKGROUND = {
    "hotel-lobby": "wood-plank",
    "inn-hall": "wood-plank",
    "night-bridge": "dark-stage",
    "park-evening": "dark-stage",
    "room-day": "wood-plank",
    "school-yard": "stone-court",
    "shop-row": "stone-court",
    "street-day": "stone-court",
    "temple-courtyard": "stone-court",
    "theatre-stage": "dark-stage",
    "training-ground": "stone-court",
}

FIST_AUDIO = "assets/audio/031_26_赤手空拳打斗的声音_爱给网_aigei_com.mp3"
METAL_AUDIO = "assets/audio/刀剑、金属碰撞（带回音）_爱给网_aigei_com.mp3"
BOOM_AUDIO = "assets/audio/音效 爆炸 爆破 爆发 战斗_爱给网_aigei_com.mp3"
HEART_AUDIO = "assets/audio/心脏怦怦跳.wav"
DIALOGUE_BGM = "assets/bgm/只要有你-那英-孙楠-少年包青天.mp3"
SUSPENSE_BGM = "assets/bgm/误入迷失森林-少年包青天.mp3"
BATTLE_BGM = "assets/bgm/男儿当自强.mp3"

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


def line(speaker_id: str, text: str) -> DialogueLine:
    return (speaker_id, text)


def front_actor(actor_id: str, x: float, *, facing: str, scale: float = 1.0, z: float = 0.0) -> dict:
    return actor(actor_id, x, z=z, facing=facing, scale=scale)


def mid_actor(actor_id: str, x: float, *, facing: str, scale: float = 0.94, z: float = -0.16) -> dict:
    return actor(actor_id, x, z=z, facing=facing, scale=scale, layer="mid")


def back_actor(actor_id: str, x: float, *, facing: str, scale: float = 0.88, z: float = -0.74) -> dict:
    return actor(actor_id, x, z=z, facing=facing, scale=scale, layer="back")


def infer_expression(text: str) -> str:
    if any(token in text for token in ("打", "破", "砸", "压", "撑", "赢", "拳", "掌", "退", "冲")):
        return "angry"
    if any(token in text for token in ("快", "小心", "稳住", "立刻", "别停")):
        return "excited"
    if any(token in text for token in ("局", "机会", "算", "节奏", "路数", "回合", "规则")):
        return "thinking"
    if any(token in text for token in ("笑", "果然", "有趣", "体面")):
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


def scene_camera(scene_index: int, *, battle: bool) -> dict:
    if battle:
        return camera_pan(
            x=-0.30 + 0.06 * (scene_index % 3),
            z=0.04,
            zoom=1.06,
            to_x=0.24 - 0.05 * (scene_index % 2),
            to_z=0.01,
            to_zoom=1.15,
            ease="ease-in-out",
        )
    if scene_index in {1, 20, 31}:
        return camera_static(x=0.0, z=0.03, zoom=1.08)
    return camera_pan(
        x=-0.22 + 0.04 * (scene_index % 2),
        z=0.03,
        zoom=1.0,
        to_x=0.16 - 0.03 * (scene_index % 3),
        to_z=0.0,
        to_zoom=1.08,
        ease="ease-in-out",
    )


def arena_props(scene_index: int, *, interior: bool = False, stage: bool = False, night: bool = False) -> list[dict]:
    if stage:
        return [
            prop("star", -3.8, -0.54, scale=0.50, layer="back"),
            prop("moon", 3.8, -0.42, scale=0.70, layer="back"),
            prop("training-drum", -3.4, -1.06, scale=0.90, layer="back"),
            prop("weapon-rack", 3.4, -1.02, scale=0.92, layer="mid"),
        ]
    if interior:
        return [
            prop("wall-window", -3.8, -1.0, scale=0.92, layer="back"),
            prop("wall-door", 3.8, -1.02, scale=0.92, layer="back"),
            prop("weapon-rack" if scene_index % 2 == 0 else "training-drum", 0.0, -1.03, scale=0.90, layer="mid"),
            prop("lantern", 3.3, -0.92, scale=0.92, layer="front"),
        ]
    items = [prop("house", 0.0, -1.08, scale=0.98, layer="back")]
    if night:
        items.extend(
            [
                prop("moon", 3.8, -0.42, scale=0.74, layer="back"),
                prop("star", -3.8, -0.55, scale=0.56, layer="back"),
                prop("lantern", -3.5, -0.92, scale=0.94, layer="front"),
            ]
        )
    else:
        items.extend(
            [
                prop("horse", -3.7, -0.92, scale=0.82, layer="front"),
                prop("wall-door", 3.8, -1.02, scale=0.90, layer="back"),
            ]
        )
    if scene_index % 2 == 0:
        items.append(prop("weapon-rack", 0.8, -1.0, scale=0.88, layer="mid"))
    return items


def fight_audio(
    *,
    metal: bool = False,
    boom: bool = False,
    heart: bool = False,
    extra_boom: bool = False,
) -> dict:
    sfx = [
        audio_sfx(FIST_AUDIO, start_ms=3800, volume=0.70),
        audio_sfx(FIST_AUDIO, start_ms=8200, volume=0.74),
    ]
    if metal:
        sfx.append(audio_sfx(METAL_AUDIO, start_ms=6200, volume=0.64))
    if boom:
        sfx.append(audio_sfx(BOOM_AUDIO, start_ms=10600, volume=0.58))
    if extra_boom:
        sfx.append(audio_sfx(BOOM_AUDIO, start_ms=7200, volume=0.48))
    if heart:
        sfx.append(audio_sfx(HEART_AUDIO, start_ms=2400, volume=0.62))
    return scene_audio(sfx=sfx)


def scene_bgm(scene_index: int, *, battle: bool) -> dict:
    if battle:
        path = BATTLE_BGM
        volume = 0.66
    elif scene_index in {2, 8, 9, 15, 16, 17, 18, 19, 20, 21, 26}:
        path = SUSPENSE_BGM
        volume = 0.54
    else:
        path = DIALOGUE_BGM
        volume = 0.48
    return audio_bgm(path, volume=volume, loop=True)


def default_foregrounds(scene_index: int, background: str) -> list[dict]:
    if background == "theatre-stage":
        return [
            foreground(
                "敞开的红色帘子-窗帘或床帘皆可",
                x=-0.02,
                y=-0.04,
                width=1.04,
                height=1.10,
                opacity=1.0,
            )
        ]
    if background in {"hotel-lobby", "inn-hall", "room-day"}:
        foreground_id = "开着门的室内" if scene_index % 2 == 0 else "古典木门木窗-有点日式风格"
        return [
            foreground(
                foreground_id,
                x=-0.01,
                y=-0.02,
                width=1.02,
                height=1.06,
                opacity=1.0,
            )
        ]
    if background in {"night-bridge", "park-evening"}:
        return [
            foreground(
                "中式古典大门",
                x=-0.01,
                y=-0.02,
                width=1.02,
                height=1.06,
                opacity=1.0,
            )
        ]
    return []


SCENE_SPECS = [
    SceneSpec(
        scene_id="scene-001",
        background="theatre-stage",
        summary="东关地下拳赛开场，主持人把整座旧戏台煽得沸腾，秦老板坐在高处等今晚的收成。",
        actors=[
            front_actor("host", -2.4, facing="right", scale=0.92),
            front_actor("qin_boss", 0.1, facing="left"),
            front_actor("crowd", 2.6, facing="left", scale=0.94),
            mid_actor("lin_ye", 3.8, facing="left", scale=0.88),
        ],
        props=arena_props(0, stage=True),
        lines=[
            line("host", "东关拳台今晚开门见血，三十六家盘口全压在这盏灯下，谁敢站到最后，谁就是今夜的新王。"),
            line("qin_boss", "别光喊热闹，我要看的不是气氛，是谁能把票房和人心一并砸出来。"),
            line("crowd", "林野上场，林野上场，听说他第一轮就要碰铁鹫。"),
            line("lin_ye", "场子越响，我心里越静，今晚我不是来陪人出戏的。"),
        ],
        effects=[effect("热烈鼓掌", start_ms=200, end_ms=3400, alpha=0.18, playback_speed=0.88)],
        audio=fight_audio(metal=True),
    ),
    SceneSpec(
        scene_id="scene-002",
        background="room-day",
        summary="赛前更衣室里，沈馆主和唐霜把林野最后一口气脉捋顺，不准他被外头的喧闹拖乱节奏。",
        actors=[
            front_actor("shen_guan", -2.3, facing="right"),
            front_actor("lin_ye", 0.2, facing="left"),
            front_actor("tang_shuang", 2.6, facing="left", scale=0.92),
            mid_actor("su_mo", 3.8, facing="left", scale=0.88),
        ],
        props=arena_props(1, interior=True),
        lines=[
            line("shen_guan", "你今晚要连打三关，靠蛮力撑不到最后，得把每一拳都打在该打的地方。"),
            line("lin_ye", "我记着，先夺中线，再逼节奏，谁急谁就先露空门。"),
            line("tang_shuang", "铁鹫开局会抢身位，罗焰爱压肋下，韩烈最麻烦，他会等你自己露破绽。"),
            line("su_mo", "我在外头盯着，谁要在手套和药水上动手，我第一时间回来告诉你。"),
        ],
    ),
    SceneSpec(
        scene_id="scene-003",
        background="hotel-lobby",
        summary="另一边的贵宾厅里，秦老板和白鸦早把今晚的每一轮都算进盘口，只等最值钱的一场爆掉。",
        actors=[
            front_actor("qin_boss", -2.1, facing="right"),
            front_actor("bai_ya", 2.0, facing="left"),
            mid_actor("host", 3.8, facing="left", scale=0.88),
        ],
        props=arena_props(2, interior=True),
        lines=[
            line("qin_boss", "林野太干净，韩烈太贵，我要的是一个刚好能把全场赌火点着的结果。"),
            line("bai_ya", "那就先让铁鹫磨他，再让罗焰砸他，等他硬撑到决赛，我再让灯灭一盏。"),
            line("host", "老板放心，我只负责把台词喊得漂亮，至于台下怎么翻盘，我什么都没看见。"),
            line("qin_boss", "很好，今夜最值钱的从来不是拳，是所有人以为自己看懂了拳。"),
        ],
    ),
    SceneSpec(
        scene_id="scene-004",
        background="theatre-stage",
        summary="卫冕拳王韩烈先出场，他只站了一会儿，全场便安静下来，所有人都知道真正的门槛在他身上。",
        actors=[
            front_actor("han_lei", -0.1, facing="left"),
            front_actor("host", -2.6, facing="right", scale=0.92),
            front_actor("crowd", 2.8, facing="left", scale=0.94),
        ],
        props=arena_props(3, stage=True),
        lines=[
            line("host", "卫冕拳王韩烈，八个月不败，七场终结，今晚继续坐镇最后一关。"),
            line("han_lei", "别替我喊威风，先把真正敢打的人送到我面前。"),
            line("crowd", "韩烈这口气还是这么硬，谁真能闯到他跟前，今晚才算没白来。"),
            line("host", "听见没有，拳王不要热闹，他要对手。"),
        ],
        audio=fight_audio(metal=True),
    ),
    SceneSpec(
        scene_id="scene-005",
        background="inn-hall",
        summary="登场通道里心跳声压过了喧哗，林野把绷带再次勒紧，只给自己留一条向前的路。",
        actors=[
            front_actor("lin_ye", -2.0, facing="right"),
            front_actor("tang_shuang", 0.4, facing="left", scale=0.92),
            front_actor("shen_guan", 2.6, facing="left"),
            mid_actor("su_mo", 3.8, facing="left", scale=0.86),
        ],
        props=arena_props(4, interior=True),
        lines=[
            line("tang_shuang", "别抬头找看台，今晚你只看对手肩膀和脚下，其他声音都当不存在。"),
            line("lin_ye", "我听见了，脚步、呼吸、灯架晃动，全比看台上的吼声有用。"),
            line("shen_guan", "你不是去跟全场打，你只需要把站在你对面的那一个一个打掉。"),
            line("su_mo", "心跳快是好事，说明身体知道今晚不是演习。"),
        ],
        audio=fight_audio(heart=True),
    ),
    SceneSpec(
        scene_id="scene-006",
        background="theatre-stage",
        summary="第一场开锣，铁鹫像野狗一样贴着边线绕圈，试图用步法先偷掉林野的重心。",
        actors=[
            front_actor("lin_ye", -2.1, facing="right"),
            front_actor("tie_jiu", 2.2, facing="left"),
            mid_actor("host", -3.7, facing="right", scale=0.88),
            mid_actor("crowd", 3.7, facing="left", scale=0.88),
        ],
        props=arena_props(5, stage=True),
        lines=[
            line("host", "第一场，林野对铁鹫，铃声一落，谁先退半步，谁今晚就得从最下面重新爬。"),
            line("tie_jiu", "新人，别想着打满回合，我最擅长第一波就把人腿打软。"),
            line("lin_ye", "你先摸得到我的腿，再谈把我打软。"),
            line("crowd", "别废话了，开打，先看谁敢抢第一步。"),
        ],
        extra_beats=[
            beat(3600, 7000, "tie_jiu", "big-jump", x0=2.2, x1=0.7, facing="left", emotion="charged"),
            beat(7600, 10800, "lin_ye", "somersault", x0=-2.0, x1=-0.4, facing="right", emotion="charged"),
        ],
        audio=fight_audio(heart=True, metal=True),
    ),
    SceneSpec(
        scene_id="scene-007",
        background="theatre-stage",
        summary="铁鹫上来就是一连串爆冲，林野却像钉在地上一样，只用半步半步把距离拆开。",
        actors=[
            front_actor("lin_ye", -2.2, facing="right"),
            front_actor("tie_jiu", 2.0, facing="left"),
            mid_actor("tang_shuang", -3.8, facing="right", scale=0.88),
        ],
        props=arena_props(6, stage=True),
        lines=[
            line("tie_jiu", "你不是稳，你是慢，我这一下再压进去，你就只能硬吃。"),
            line("lin_ye", "你冲得越满，回身就越慢，我等的就是你收不住脚。"),
            line("tang_shuang", "林野，别陪他转，压肩，断他的外摆。"),
            line("tie_jiu", "好，那我就不转了，直接砸穿你中路。"),
        ],
        extra_beats=[
            beat(3400, 6400, "tie_jiu", "thunder-strike", x0=1.9, x1=0.6, facing="left", effect="thunder-strike"),
            beat(7600, 10800, "lin_ye", "dragon-palm", x0=-1.8, x1=0.4, facing="right", effect="dragon-palm"),
        ],
        effects=[
            effect("thunder-strike", start_ms=3400, end_ms=6700, alpha=0.22, playback_speed=0.84),
            effect("dragon-palm", start_ms=7600, end_ms=11100, alpha=0.24, playback_speed=0.88),
        ],
        audio=fight_audio(boom=True, extra_boom=True),
    ),
    SceneSpec(
        scene_id="scene-008",
        background="theatre-stage",
        summary="第一场最后一轮，林野终于把铁鹫逼到了灯柱底下，一套连击直接把人打飞出去。",
        actors=[
            front_actor("lin_ye", -1.8, facing="right"),
            front_actor("tie_jiu", 1.9, facing="left"),
            mid_actor("host", -3.6, facing="right", scale=0.88),
            mid_actor("crowd", 3.7, facing="left", scale=0.88),
        ],
        props=arena_props(7, stage=True),
        lines=[
            line("host", "铁鹫被逼到底角了，林野这一轮的出手比前面整整快了一档。"),
            line("tie_jiu", "别以为压住我一次就算赢，我倒下之前你都不算过关。"),
            line("lin_ye", "那你就站稳，我这一下不打偏。"),
            line("crowd", "中了，中了，铁鹫真的飞出去了。"),
        ],
        extra_beats=[
            beat(3600, 6900, "lin_ye", "dragon-palm", x0=-1.7, x1=0.5, facing="right", effect="dragon-palm"),
            beat(7400, 11000, "tie_jiu", "exit", x0=1.8, x1=3.7, facing="right", emotion="hurt"),
        ],
        effects=[effect("dragon-palm", start_ms=3600, end_ms=7200, alpha=0.24, playback_speed=0.86)],
        audio=fight_audio(boom=True, metal=True, extra_boom=True),
    ),
    SceneSpec(
        scene_id="scene-009",
        background="room-day",
        summary="回到休息间，苏沫发现林野的手套缝线被人割过，说明今夜的局面远不止台上那么简单。",
        actors=[
            front_actor("su_mo", -2.2, facing="right", scale=0.94),
            front_actor("lin_ye", 0.2, facing="left"),
            front_actor("tang_shuang", 2.6, facing="left", scale=0.92),
            mid_actor("shen_guan", 3.8, facing="left", scale=0.88),
        ],
        props=arena_props(8, interior=True),
        lines=[
            line("su_mo", "看这里，缝线被人提前挑松了，你再多撑一场，护腕就会自己崩开。"),
            line("lin_ye", "所以台上的不是意外，台下也有人盯着我想让我慢慢耗光。"),
            line("tang_shuang", "我去找人，谁今晚想做手脚，我就把他的手先折了。"),
            line("shen_guan", "别乱，知道有人脏就够了，接下来每一步都得比他们更稳。"),
        ],
    ),
    SceneSpec(
        scene_id="scene-010",
        background="hotel-lobby",
        summary="半决赛对手罗焰站在走廊尽头，只看了林野一眼，那股压迫感就像铁块一样砸了过来。",
        actors=[
            front_actor("lin_ye", -2.2, facing="right"),
            front_actor("luo_yan", 2.2, facing="left"),
            mid_actor("bai_ya", 3.7, facing="left", scale=0.88),
        ],
        props=arena_props(9, interior=True),
        lines=[
            line("luo_yan", "我看完你第一场了，步子够稳，拳也够直，可惜半决赛不是看这些。"),
            line("lin_ye", "那看什么，看谁更能挨，还是看谁更愿意被老板买走。"),
            line("bai_ya", "两位别急，真正值钱的东西总要留到更靠后的回合才翻出来。"),
            line("luo_yan", "我不管谁值钱，我只管把挡在我前面的人一个一个砸掉。"),
        ],
    ),
    SceneSpec(
        scene_id="scene-011",
        background="training-ground",
        summary="半决赛前的最后练步，沈馆主要林野放掉硬顶的念头，用最短的路把罗焰的重拳卸空。",
        actors=[
            front_actor("shen_guan", -2.2, facing="right"),
            front_actor("lin_ye", 0.0, facing="left"),
            front_actor("tang_shuang", 2.5, facing="left", scale=0.92),
            mid_actor("su_mo", 3.8, facing="left", scale=0.88),
        ],
        props=arena_props(10),
        lines=[
            line("shen_guan", "罗焰的拳不是快，是重，你要是跟他硬碰，骨架先吃亏。"),
            line("lin_ye", "所以我不接满，只接一半，把他的力引到地上，再从空的那条线上回去。"),
            line("tang_shuang", "对，别站着当靶子，半步进，半步斜，再把回手塞进他肋下。"),
            line("su_mo", "你们说得轻巧，真挨那一下的人可是他，别让他真被打到。"),
        ],
    ),
    SceneSpec(
        scene_id="scene-012",
        background="theatre-stage",
        summary="半决赛登场，罗焰像一堵墙一样站进场心，主持人一句话没说完，两边的气势就已经撞上了。",
        actors=[
            front_actor("host", -3.2, facing="right", scale=0.92),
            front_actor("lin_ye", -1.5, facing="right"),
            front_actor("luo_yan", 1.7, facing="left"),
            mid_actor("crowd", 3.7, facing="left", scale=0.88),
        ],
        props=arena_props(11, stage=True),
        lines=[
            line("host", "第二场，林野对罗焰，一个速度正起，一个重拳压场，这一轮没有试探，只有谁先碎。"),
            line("luo_yan", "我不喜欢拖回合，铃一响，我就会往前走到你退无可退。"),
            line("lin_ye", "你尽管来，我也不打算给自己留退路。"),
            line("crowd", "这一场才像真的，站着不动都带响。"),
        ],
        audio=fight_audio(heart=True, metal=True),
    ),
    SceneSpec(
        scene_id="scene-013",
        background="theatre-stage",
        summary="罗焰第一波像铁锤一样砸下来，林野被逼得不断换位，整个台面都跟着震。",
        actors=[
            front_actor("lin_ye", -2.0, facing="right"),
            front_actor("luo_yan", 2.0, facing="left"),
            mid_actor("tang_shuang", -3.8, facing="right", scale=0.88),
        ],
        props=arena_props(12, stage=True),
        lines=[
            line("luo_yan", "给我站住，别把躲闪叫本事，正面吃我一拳再说。"),
            line("lin_ye", "能让你打空，就是本事，你脚跟越沉，转身就越慢。"),
            line("tang_shuang", "别退直线，切出去，别被他的肩撞锁死。"),
            line("luo_yan", "切得出去算你快，切不出去我就把你钉在地上。"),
        ],
        extra_beats=[
            beat(3600, 6800, "luo_yan", "thunder-strike", x0=1.9, x1=0.5, facing="left", effect="thunder-strike"),
            beat(7600, 10400, "lin_ye", "somersault", x0=-1.9, x1=-0.3, facing="right", emotion="charged"),
        ],
        effects=[effect("thunder-strike", start_ms=3600, end_ms=7000, alpha=0.22, playback_speed=0.82)],
        audio=fight_audio(boom=True, extra_boom=True),
    ),
    SceneSpec(
        scene_id="scene-014",
        background="theatre-stage",
        summary="中段回合林野被罗焰顶到角柱，几乎每一次呼吸都带着闷响，可他的眼神却越来越亮。",
        actors=[
            front_actor("lin_ye", -1.9, facing="right"),
            front_actor("luo_yan", 1.9, facing="left"),
            mid_actor("su_mo", -3.8, facing="right", scale=0.88),
        ],
        props=arena_props(13, stage=True),
        lines=[
            line("su_mo", "林野已经吃了两下硬的，再这么挤下去，他肋下会先扛不住。"),
            line("luo_yan", "看见没有，这就是硬度，你再快，也快不过我一拳落地。"),
            line("lin_ye", "不，你的拳已经慢下来了，你只是还没意识到。"),
            line("su_mo", "就是现在，别再给他第二次压肩。"),
        ],
        extra_beats=[
            beat(3400, 6600, "luo_yan", "big-jump", x0=1.8, x1=0.4, facing="left", emotion="charged"),
            beat(7600, 10900, "lin_ye", "dragon-palm", x0=-1.5, x1=0.7, facing="right", effect="dragon-palm"),
        ],
        effects=[effect("dragon-palm", start_ms=7600, end_ms=11200, alpha=0.24, playback_speed=0.88)],
        audio=fight_audio(metal=True, boom=True),
    ),
    SceneSpec(
        scene_id="scene-015",
        background="theatre-stage",
        summary="罗焰终于被林野从重心底下掀开，那记蓄了整场的反击像一道闷雷，把半决赛直接打穿。",
        actors=[
            front_actor("lin_ye", -1.7, facing="right"),
            front_actor("luo_yan", 1.8, facing="left"),
            mid_actor("host", -3.6, facing="right", scale=0.88),
            mid_actor("crowd", 3.8, facing="left", scale=0.88),
        ],
        props=arena_props(14, stage=True),
        lines=[
            line("host", "罗焰第一次被打开了，林野这一手不是硬拼，是把整整一场的节奏全借回来了。"),
            line("luo_yan", "你居然敢在我落拳的缝里顶进来。"),
            line("lin_ye", "因为我等的就是你这一缝。"),
            line("crowd", "倒了，罗焰真的倒了，今晚这个新人越打越大。"),
        ],
        extra_beats=[
            beat(3600, 7200, "lin_ye", "dragon-palm", x0=-1.5, x1=0.6, facing="right", effect="dragon-palm"),
            beat(7400, 11000, "luo_yan", "exit", x0=1.7, x1=3.8, facing="right", emotion="hurt"),
        ],
        effects=[
            effect("dragon-palm", start_ms=3600, end_ms=7400, alpha=0.24, playback_speed=0.86),
            effect("thunder-strike", start_ms=7200, end_ms=11000, alpha=0.20, playback_speed=0.80),
        ],
        audio=fight_audio(boom=True, extra_boom=True, metal=True),
    ),
    SceneSpec(
        scene_id="scene-016",
        background="hotel-lobby",
        summary="贵宾厅里气压骤降，秦老板发现林野连续过关，便想把最后的比赛彻底搅成一锅浑水。",
        actors=[
            front_actor("qin_boss", -2.0, facing="right"),
            front_actor("bai_ya", 0.8, facing="left"),
            front_actor("han_lei", 2.8, facing="left"),
        ],
        props=arena_props(15, interior=True),
        lines=[
            line("qin_boss", "林野要是真打到你面前，盘口会全翻，我不喜欢任何不按剧本走的东西。"),
            line("bai_ya", "我可以让剧本重新回到你手里，只要最后那盏灯按时灭掉。"),
            line("han_lei", "你们算账算你们的，别把我的决赛变成脏戏。"),
            line("qin_boss", "韩烈，台上你当然还是拳王，可台下很多灯不是你说亮就亮。"),
        ],
    ),
    SceneSpec(
        scene_id="scene-017",
        background="inn-hall",
        summary="林野回通道休息时，白鸦的人突然在走廊里截住他，想在决赛前先废掉他的腿。",
        actors=[
            front_actor("lin_ye", -2.2, facing="right"),
            front_actor("bai_ya", 1.8, facing="left"),
            mid_actor("crowd", 3.5, facing="left", scale=0.88),
            mid_actor("tang_shuang", -3.6, facing="right", scale=0.88),
        ],
        props=arena_props(16, interior=True),
        lines=[
            line("bai_ya", "打到这里已经够了，决赛是给韩烈和盘口准备的，不是给你做梦的。"),
            line("lin_ye", "所以你不敢等台上，非要挑通道和黑角落下手。"),
            line("crowd", "老板说过，留口气就行，腿先打断，剩下的明天再算。"),
            line("tang_shuang", "谁敢碰他一步，我今天就在这条走廊先拆谁。"),
        ],
        extra_beats=[
            beat(3600, 6900, "crowd", "enter", x0=3.5, x1=1.2, facing="left", emotion="charged"),
            beat(7600, 10800, "lin_ye", "dragon-palm", x0=-1.9, x1=0.4, facing="right", effect="dragon-palm"),
        ],
        effects=[
            effect("dragon-palm", start_ms=7600, end_ms=11100, alpha=0.22, playback_speed=0.86),
            effect("千军万马冲杀", start_ms=2600, end_ms=7200, alpha=0.14, playback_speed=0.82),
        ],
        audio=fight_audio(metal=True, boom=True),
    ),
    SceneSpec(
        scene_id="scene-018",
        background="night-bridge",
        summary="通道外的夜桥被一路追打成了第二个赛场，白鸦亲自下场，招式比台上的拳更阴。",
        actors=[
            front_actor("lin_ye", -2.2, facing="right"),
            front_actor("bai_ya", 2.0, facing="left"),
            mid_actor("crowd", 0.7, facing="left", scale=0.90),
            back_actor("tang_shuang", -3.6, facing="right", scale=0.86),
        ],
        props=arena_props(17, night=True),
        lines=[
            line("bai_ya", "台上讲回合，桥上不讲，你撑住一秒，我就多拆你一寸。"),
            line("lin_ye", "你这种人算得再准，也不敢跟人正面打一整场。"),
            line("crowd", "白先生，桥那头还有人过来，我们得快点把他压倒。"),
            line("bai_ya", "那就一起上，把他逼到桥栏，今晚让他自己掉下去。"),
        ],
        extra_beats=[
            beat(3400, 6600, "bai_ya", "sword-arc", x0=1.9, x1=0.5, facing="left", effect="sword-arc"),
            beat(7600, 10400, "lin_ye", "somersault", x0=-1.8, x1=-0.4, facing="right", emotion="charged"),
            beat(10600, 13600, "crowd", "exit", x0=0.8, x1=3.8, facing="right", emotion="hurt"),
        ],
        effects=[effect("sword-arc", start_ms=3400, end_ms=6900, alpha=0.22, playback_speed=0.92)],
        audio=fight_audio(metal=True, extra_boom=True),
    ),
    SceneSpec(
        scene_id="scene-019",
        background="night-bridge",
        summary="唐霜赶到后一前一后夹住白鸦，桥上的局面瞬间倒转，白鸦第一次真正露出急色。",
        actors=[
            front_actor("lin_ye", -2.0, facing="right"),
            front_actor("tang_shuang", 0.0, facing="right", scale=0.92),
            front_actor("bai_ya", 2.1, facing="left"),
        ],
        props=arena_props(18, night=True),
        lines=[
            line("tang_shuang", "你算人心很准，可你总忘了，人不是算出来的，是逼出来的。"),
            line("bai_ya", "有趣，两个人一起堵我，倒像是你们先急了。"),
            line("lin_ye", "我们不急，只是不想让你再有机会摸到台下的灯。"),
            line("tang_shuang", "说完了就打，这一桥风够大，正好把你那点花话吹散。"),
        ],
        extra_beats=[
            beat(3600, 6800, "tang_shuang", "sword-arc", x0=-0.2, x1=0.9, facing="right", effect="sword-arc"),
            beat(7600, 10800, "lin_ye", "dragon-palm", x0=-1.7, x1=0.5, facing="right", effect="dragon-palm"),
        ],
        effects=[
            effect("sword-arc", start_ms=3600, end_ms=7000, alpha=0.22, playback_speed=0.90),
            effect("dragon-palm", start_ms=7600, end_ms=11100, alpha=0.24, playback_speed=0.86),
            effect("命中特效", start_ms=10800, end_ms=13200, alpha=0.16, playback_speed=0.90),
        ],
        audio=fight_audio(boom=True, metal=True, extra_boom=True),
    ),
    SceneSpec(
        scene_id="scene-020",
        background="park-evening",
        summary="白鸦在退走前丢下一句真正的威胁，说决赛时会先灭灯，再灭掉所有人对公平的幻想。",
        actors=[
            front_actor("bai_ya", -2.1, facing="right"),
            front_actor("lin_ye", 0.3, facing="left"),
            front_actor("tang_shuang", 2.5, facing="left", scale=0.92),
        ],
        props=arena_props(19, night=True),
        lines=[
            line("bai_ya", "你们今晚赢的不是我，是我还没把最后一张牌翻开。"),
            line("lin_ye", "那你就尽快翻，我不想带着猜来打最后一场。"),
            line("tang_shuang", "他会动灯、动门、动台下的手，我们回去之前先把所有路摸清。"),
            line("bai_ya", "好，那就决赛见，等灯一灭，你们会发现拳台从来不站在你们这边。"),
        ],
    ),
    SceneSpec(
        scene_id="scene-021",
        background="training-ground",
        summary="韩烈主动来找林野，两个人第一次在没有灯和看台的地方说话，气氛反而比赛场更直。",
        actors=[
            front_actor("lin_ye", -2.2, facing="right"),
            front_actor("han_lei", 2.1, facing="left"),
            mid_actor("shen_guan", -3.8, facing="right", scale=0.88),
        ],
        props=arena_props(20),
        lines=[
            line("han_lei", "我听说桥上的事了，决赛我要打的是你，不是别人替我削过一遍的你。"),
            line("lin_ye", "那就看你能不能把台子守干净，别让你这拳王只是个站牌。"),
            line("han_lei", "我守不守得住，待会你就知道，但只要灯还亮着，我不会让脏手伸进回合。"),
            line("shen_guan", "这才像决赛该有的样子，先把人话说直，再把拳打满。"),
        ],
    ),
    SceneSpec(
        scene_id="scene-022",
        background="room-day",
        summary="决赛前最后一段沉默里，心跳、缠带和呼吸被放得极大，所有人都知道真正的重头戏终于到了。",
        actors=[
            front_actor("lin_ye", -2.0, facing="right"),
            front_actor("su_mo", 0.1, facing="left", scale=0.94),
            front_actor("tang_shuang", 2.4, facing="left", scale=0.92),
            mid_actor("shen_guan", 3.8, facing="left", scale=0.88),
        ],
        props=arena_props(21, interior=True),
        lines=[
            line("su_mo", "你的左肋已经青了，决赛要是再被压住这一侧，呼吸会先出问题。"),
            line("lin_ye", "我知道，所以第一回合不能被他读懂，只要被他读懂一次，后面每轮都会更难。"),
            line("tang_shuang", "别想着赢得漂亮，先把人逼进你的节奏，再谈最后怎么收。"),
            line("shen_guan", "记住，最后一场最难的不是打人，是在所有眼睛盯着你的时候，还能只看见自己该打的那一点。"),
        ],
        audio=fight_audio(heart=True),
    ),
    SceneSpec(
        scene_id="scene-023",
        background="theatre-stage",
        summary="决赛正式开始，整座旧戏台的灯火全部推满，秦老板的笑意和观众的吼声一同压下来。",
        actors=[
            front_actor("host", -3.1, facing="right", scale=0.92),
            front_actor("lin_ye", -1.6, facing="right"),
            front_actor("han_lei", 1.8, facing="left"),
            mid_actor("qin_boss", 3.8, facing="left", scale=0.88),
        ],
        props=arena_props(22, stage=True),
        lines=[
            line("host", "决赛，林野对韩烈，今晚的最后一盏灯，最后一口气，最后一场真正值钱的拳，全在这里。"),
            line("han_lei", "走到我面前不容易，既然来了，就别想着只拿个体面回去。"),
            line("lin_ye", "我来这里不是拿体面的，我来拿结果。"),
            line("qin_boss", "很好，全场都睁大眼睛，我要看的就是这种谁都不肯低头的样子。"),
        ],
        audio=fight_audio(heart=True, metal=True),
    ),
    SceneSpec(
        scene_id="scene-024",
        background="theatre-stage",
        summary="决赛第一回合没有急攻，林野和韩烈都只用最短的动作互相试探，可每一下都重得吓人。",
        actors=[
            front_actor("lin_ye", -2.0, facing="right"),
            front_actor("han_lei", 2.0, facing="left"),
            mid_actor("crowd", 3.8, facing="left", scale=0.88),
        ],
        props=arena_props(23, stage=True),
        lines=[
            line("han_lei", "好，脚下不虚，肩也不飘，你至少配得上我先看你一个回合。"),
            line("lin_ye", "你也没有传闻里那么高高在上，至少出手的时候还像个真正的拳手。"),
            line("crowd", "这两个人怎么打得这么静，可每一下听着都比前面更重。"),
            line("han_lei", "静才好，越静，越能听清谁先露怯。"),
        ],
        extra_beats=[
            beat(3600, 6600, "han_lei", "point", facing="left", emotion="charged"),
            beat(7600, 10500, "lin_ye", "enter", x0=-2.0, x1=-0.5, facing="right", emotion="charged"),
        ],
        audio=fight_audio(metal=True),
    ),
    SceneSpec(
        scene_id="scene-025",
        background="theatre-stage",
        summary="第一回合之后，韩烈确认林野真的能接住自己的压迫，两人言语反而比动作更锋利。",
        actors=[
            front_actor("lin_ye", -1.9, facing="right"),
            front_actor("han_lei", 1.9, facing="left"),
            mid_actor("host", -3.7, facing="right", scale=0.88),
        ],
        props=arena_props(24, stage=True),
        lines=[
            line("host", "这不是互相试手，这是互相逼着对方把最硬的那一面先掏出来。"),
            line("han_lei", "不错，你不是来碰运气的，你是真的想把我从这盏灯下赶下去。"),
            line("lin_ye", "你既然看出来了，就别再只用三分力站着试我。"),
            line("han_lei", "好，下一轮我不再试了。"),
        ],
        audio=fight_audio(heart=True),
    ),
    SceneSpec(
        scene_id="scene-026",
        background="theatre-stage",
        summary="决赛第二回合一开，两个人同时加速，整个戏台像被两股力从中间硬生生扯开。",
        actors=[
            front_actor("lin_ye", -1.8, facing="right"),
            front_actor("han_lei", 1.8, facing="left"),
            mid_actor("crowd", 3.8, facing="left", scale=0.88),
        ],
        props=arena_props(25, stage=True),
        lines=[
            line("han_lei", "来，别再留，今晚谁收拳，谁就不配站着。"),
            line("lin_ye", "正合我意，我也不想把最后一场打成慢戏。"),
            line("crowd", "太快了，这一下谁先碰到谁都像会把人直接打穿。"),
            line("han_lei", "再来，我看你到底还能顶几层。"),
        ],
        extra_beats=[
            beat(3400, 6600, "han_lei", "thunder-strike", x0=1.8, x1=0.4, facing="left", effect="thunder-strike"),
            beat(7000, 9800, "lin_ye", "dragon-palm", x0=-1.6, x1=0.5, facing="right", effect="dragon-palm"),
            beat(10000, 13600, "han_lei", "sword-arc", x0=0.5, x1=-0.3, facing="left", effect="sword-arc"),
        ],
        effects=[
            effect("thunder-strike", start_ms=3400, end_ms=6900, alpha=0.22, playback_speed=0.82),
            effect("dragon-palm", start_ms=7000, end_ms=10100, alpha=0.24, playback_speed=0.86),
            effect("sword-arc", start_ms=10000, end_ms=13600, alpha=0.22, playback_speed=0.90),
        ],
        audio=fight_audio(boom=True, metal=True, extra_boom=True),
    ),
    SceneSpec(
        scene_id="scene-027",
        background="hotel-lobby",
        summary="秦老板眼看比赛失控，当场示意手下去动总闸，要把决赛最精彩的回合直接切黑。",
        actors=[
            front_actor("qin_boss", -2.1, facing="right"),
            front_actor("bai_ya", 0.5, facing="left"),
            front_actor("host", 2.8, facing="left", scale=0.92),
        ],
        props=arena_props(26, interior=True),
        lines=[
            line("qin_boss", "够了，再让他们这么打下去，所有盘口都会被他们两个自己打碎。"),
            line("bai_ya", "我这就去总闸，灯一黑，谁还分得清决赛和意外。"),
            line("host", "老板，这么做台子以后就没法再立威了。"),
            line("qin_boss", "威不是靠规矩，是靠最后谁能把钱和恐惧一起捏在手里。"),
        ],
    ),
    SceneSpec(
        scene_id="scene-028",
        background="theatre-stage",
        summary="总灯骤灭，整座戏台只剩零散的侧灯和观众尖叫，白鸦趁黑闯进台心，局面瞬间爆炸。",
        actors=[
            front_actor("lin_ye", -1.8, facing="right"),
            front_actor("han_lei", 0.2, facing="left"),
            front_actor("bai_ya", 2.3, facing="left"),
            mid_actor("crowd", 3.7, facing="left", scale=0.88),
        ],
        props=arena_props(27, stage=True),
        lines=[
            line("crowd", "灯灭了，灯灭了，有人冲上台了，这不是回合，这是乱场。"),
            line("bai_ya", "现在终于公平了，谁也看不清，谁都只能听拳。"),
            line("han_lei", "滚下去，这是我和林野的决赛，不是你来捡尸的地方。"),
            line("lin_ye", "既然他自己送上来，那就先把这只脏手折了再继续。"),
        ],
        extra_beats=[
            beat(3200, 6200, "bai_ya", "sword-arc", x0=2.2, x1=0.9, facing="left", effect="sword-arc"),
            beat(7000, 9800, "han_lei", "thunder-strike", x0=0.2, x1=1.1, facing="right", effect="thunder-strike"),
            beat(10000, 13600, "lin_ye", "dragon-palm", x0=-1.6, x1=0.7, facing="right", effect="dragon-palm"),
        ],
        effects=[
            effect("sword-arc", start_ms=3200, end_ms=6400, alpha=0.22, playback_speed=0.90),
            effect("thunder-strike", start_ms=7000, end_ms=9900, alpha=0.20, playback_speed=0.84),
            effect("dragon-palm", start_ms=10000, end_ms=13600, alpha=0.24, playback_speed=0.86),
            effect("爆炸特效", start_ms=7200, end_ms=11200, alpha=0.18, playback_speed=0.84),
        ],
        audio=fight_audio(boom=True, metal=True, extra_boom=True),
    ),
    SceneSpec(
        scene_id="scene-029",
        background="theatre-stage",
        summary="短短一轮混战里，林野和韩烈第一次站到同一条线上，把白鸦从台心一路打到边角。",
        actors=[
            front_actor("lin_ye", -2.0, facing="right"),
            front_actor("han_lei", 0.0, facing="right"),
            front_actor("bai_ya", 2.3, facing="left"),
        ],
        props=arena_props(28, stage=True),
        lines=[
            line("han_lei", "左边给我，别让他再碰总闸和边线。"),
            line("lin_ye", "好，我压中路，你把他逼回灯柱。"),
            line("bai_ya", "真有意思，打到最后，你们两个倒像是同一边了。"),
            line("han_lei", "不是同一边，只是先把你这种东西清出去。"),
        ],
        extra_beats=[
            beat(3400, 6600, "han_lei", "thunder-strike", x0=0.0, x1=1.0, facing="right", effect="thunder-strike"),
            beat(7000, 9800, "lin_ye", "dragon-palm", x0=-1.8, x1=0.8, facing="right", effect="dragon-palm"),
            beat(10100, 13600, "bai_ya", "exit", x0=2.2, x1=3.9, facing="right", emotion="hurt"),
        ],
        effects=[
            effect("thunder-strike", start_ms=3400, end_ms=6800, alpha=0.20, playback_speed=0.82),
            effect("dragon-palm", start_ms=7000, end_ms=10000, alpha=0.24, playback_speed=0.86),
            effect("命中特效", start_ms=9800, end_ms=11800, alpha=0.16, playback_speed=0.90),
        ],
        audio=fight_audio(boom=True, metal=True, extra_boom=True),
    ),
    SceneSpec(
        scene_id="scene-030",
        background="theatre-stage",
        summary="白鸦被清走后，侧灯重新亮起，韩烈和林野都喘得很重，但谁也没提结束，决赛必须打完整。",
        actors=[
            front_actor("lin_ye", -1.8, facing="right"),
            front_actor("han_lei", 1.7, facing="left"),
            mid_actor("host", -3.7, facing="right", scale=0.88),
        ],
        props=arena_props(29, stage=True),
        lines=[
            line("host", "灯还亮着，台还在，人也都还站着，这场决赛就没理由半截收住。"),
            line("han_lei", "刚才那一轮不算，我要的是你正正当当把最后一拳打完。"),
            line("lin_ye", "我也一样，今晚走到这里，不是为了把终点让给混乱。"),
            line("han_lei", "那就继续，只剩你我。"),
        ],
        audio=fight_audio(heart=True),
    ),
    SceneSpec(
        scene_id="scene-031",
        background="theatre-stage",
        summary="最后一轮回到最纯粹的对打，林野和韩烈把全场喧哗都甩在身后，只剩彼此的脚步和拳路。",
        actors=[
            front_actor("lin_ye", -1.9, facing="right"),
            front_actor("han_lei", 1.9, facing="left"),
            mid_actor("crowd", 3.8, facing="left", scale=0.88),
        ],
        props=arena_props(30, stage=True),
        lines=[
            line("lin_ye", "来吧，这是今晚第一场没有杂音的回合。"),
            line("han_lei", "也是最重的一回合，谁能顶住最后这一下，谁才配拿走台上的名字。"),
            line("crowd", "别喊了，都别喊了，这种时候连叫都像多余。"),
            line("han_lei", "林野，出手。"),
        ],
        extra_beats=[
            beat(3400, 6400, "han_lei", "sword-arc", x0=1.8, x1=0.4, facing="left", effect="sword-arc"),
            beat(7200, 10400, "lin_ye", "dragon-palm", x0=-1.7, x1=0.8, facing="right", effect="dragon-palm"),
            beat(10400, 13600, "han_lei", "exit", x0=1.8, x1=3.4, facing="right", emotion="hurt"),
        ],
        effects=[
            effect("sword-arc", start_ms=3400, end_ms=6600, alpha=0.22, playback_speed=0.90),
            effect("dragon-palm", start_ms=7200, end_ms=10700, alpha=0.24, playback_speed=0.86),
        ],
        audio=fight_audio(boom=True, metal=True, extra_boom=True),
    ),
    SceneSpec(
        scene_id="scene-032",
        background="park-evening",
        summary="决赛落幕，韩烈承认林野赢下了今晚真正的一口气，而林野没有留下来享受掌声，只带着自己的人安静离场。",
        actors=[
            front_actor("lin_ye", -2.2, facing="right"),
            front_actor("han_lei", 0.2, facing="left"),
            front_actor("tang_shuang", 2.6, facing="left", scale=0.92),
            mid_actor("su_mo", 3.8, facing="left", scale=0.88),
        ],
        props=arena_props(31, night=True),
        lines=[
            line("han_lei", "今晚这盏灯下，最后站住的是你，拳台该记你的名字。"),
            line("lin_ye", "名字留给看台吧，我更在意的是以后再没人能轻易把灯关掉。"),
            line("tang_shuang", "走吧，今晚赢的不只是这一场，是你没被他们那套脏规矩拖进去。"),
            line("su_mo", "外头还在喊你，但你现在最该做的是先把伤处理了，再去听那些掌声。"),
        ],
        audio=fight_audio(heart=True),
    ),
]


class EastGateFightStormVideo(BaseVideoScript):
    def get_title(self) -> str:
        return "东关拳台风暴"

    def get_theme(self) -> str:
        return "格斗、擂台、地下拳赛、逆袭、总决赛、热血"

    def get_cast(self) -> list[dict]:
        return CAST

    def get_video_options(self) -> dict:
        return VIDEO

    def has_tts(self) -> bool:
        return True

    def get_notes(self) -> dict:
        return {
            "scene_count": len(SCENE_SPECS),
            "format": "east-gate-fight-storm",
            "bgm_assets": [DIALOGUE_BGM, SUSPENSE_BGM, BATTLE_BGM],
        }

    def get_default_output(self) -> str:
        return "outputs/east_gate_fight_storm.mp4"

    def get_description(self) -> str:
        return "Render a dialogue-heavy fighting story with a 32-scene arena arc, rich TTS, BGM, effects, and dense sound design."

    def get_scenes(self) -> list[dict]:
        scenes: list[dict] = []
        for scene_index, spec in enumerate(SCENE_SPECS):
            dialogue_items, talk_beats, expressions_track = build_dialogue_bundle(spec.lines)
            talk_beats = trim_talk_beats_for_actions(talk_beats, spec.extra_beats)
            beats = sorted(
                [*talk_beats, *spec.extra_beats],
                key=lambda item: (item["start_ms"], item["actor_id"]),
            )
            expressions_sorted = sorted(
                expressions_track,
                key=lambda item: (item["start_ms"], item["actor_id"]),
            )
            battle = bool(spec.extra_beats or spec.effects)
            audio_payload = scene_audio(
                bgm=scene_bgm(scene_index, battle=battle),
                sfx=list(spec.audio.get("sfx", [])),
            )
            scenes.append(
                scene(
                    spec.scene_id,
                    background=spec.background,
                    floor=FLOOR_BY_BACKGROUND[spec.background],
                    duration_ms=SCENE_DURATION_MS,
                    summary=spec.summary,
                    camera=spec.camera or scene_camera(scene_index, battle=battle),
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


SCRIPT = EastGateFightStormVideo()


def build_story() -> dict:
    return SCRIPT.build_story()


def main() -> int:
    return SCRIPT()


if __name__ == "__main__":
    raise SystemExit(main())
