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
        "effect_overlay_alpha": 0.88,
    },
}

CAST = [
    cast_member("yun_che", "云澈", "general-guard"),
    cast_member("ning_yue", "宁月", "npc-girl"),
    cast_member("xuanji", "玄玑子", "farmer-old"),
    cast_member("xue_luo", "血罗天", "official-minister"),
    cast_member("ye_cang", "夜苍", "detective-sleek"),
    cast_member("cheng_zhu", "澄主", "emperor-ming"),
    cast_member("crowd", "众修士", "npc-boy"),
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

DIALOGUE_BGM = "assets/bgm/仙剑情缘.mp3"
TRAVEL_BGM = "assets/bgm/御剑飞行.mp3"
SUSPENSE_BGM = "assets/bgm/误入迷失森林-少年包青天.mp3"
BATTLE_BGM = "assets/bgm/杀破狼.mp3"
CLIMAX_BGM = "assets/bgm/观音降临-高潮版.mp3"
EPILOGUE_BGM = "assets/bgm/莫失莫忘.mp3"
STORY_BGM = DIALOGUE_BGM


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
    music_mode: str = "dialogue"


def line(speaker_id: str, text: str) -> DialogueLine:
    return (speaker_id, text)


def front_actor(actor_id: str, x: float, *, facing: str, scale: float = 1.0, z: float = 0.0) -> dict:
    return actor(actor_id, x, z=z, facing=facing, scale=scale)


def mid_actor(actor_id: str, x: float, *, facing: str, scale: float = 0.94, z: float = -0.14) -> dict:
    return actor(actor_id, x, z=z, facing=facing, scale=scale, layer="mid")


def back_actor(actor_id: str, x: float, *, facing: str, scale: float = 0.88, z: float = -0.72) -> dict:
    return actor(actor_id, x, z=z, facing=facing, scale=scale, layer="back")


def infer_expression(text: str) -> str:
    if any(token in text for token in ("杀", "斩", "掌", "破", "劫", "血", "退", "阵", "封", "毁")):
        return "angry"
    if any(token in text for token in ("快", "立刻", "小心", "稳住", "撑住", "跟上")):
        return "excited"
    if any(token in text for token in ("阵眼", "星图", "真元", "剑意", "路数", "禁制", "因果")):
        return "thinking"
    if any(token in text for token in ("果然", "还好", "终于", "放心")):
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


def scene_camera(scene_index: int, *, battle: bool, climax: bool = False) -> dict:
    if climax:
        return camera_pan(
            x=-0.34,
            z=0.06,
            zoom=1.12,
            to_x=0.26,
            to_z=0.0,
            to_zoom=1.22,
            ease="ease-in-out",
        )
    if battle:
        return camera_pan(
            x=-0.28 + 0.06 * (scene_index % 3),
            z=0.05,
            zoom=1.06,
            to_x=0.22 - 0.05 * (scene_index % 2),
            to_z=0.0,
            to_zoom=1.15,
            ease="ease-in-out",
        )
    if scene_index in {0, 9, 19}:
        return camera_static(x=0.0, z=0.03, zoom=1.08)
    return camera_pan(
        x=-0.22 + 0.04 * (scene_index % 2),
        z=0.03,
        zoom=1.0,
        to_x=0.18 - 0.03 * (scene_index % 3),
        to_z=0.0,
        to_zoom=1.08,
        ease="ease-in-out",
    )


def xianxia_props(scene_index: int, *, interior: bool = False, night: bool = False, ritual: bool = False) -> list[dict]:
    if ritual:
        return [
            prop("training-drum", -3.4, -1.06, scale=0.92, layer="back"),
            prop("weapon-rack", 3.5, -1.0, scale=0.94, layer="mid"),
            prop("lantern", -0.2, -0.90, scale=1.0, layer="front"),
        ]
    if interior:
        return [
            prop("wall-window", -3.8, -1.0, scale=0.92, layer="back"),
            prop("wall-door", 3.8, -1.02, scale=0.92, layer="back"),
            prop("weapon-rack" if scene_index % 2 == 0 else "training-drum", 0.0, -1.02, scale=0.90, layer="mid"),
            prop("lantern", 3.2, -0.92, scale=0.94, layer="front"),
        ]
    items = [prop("house", 0.0, -1.08, scale=0.98, layer="back")]
    if night:
        items.extend(
            [
                prop("moon", 3.7, -0.42, scale=0.76, layer="back"),
                prop("star", -3.7, -0.54, scale=0.56, layer="back"),
                prop("lantern", -3.4, -0.92, scale=0.94, layer="front"),
            ]
        )
    else:
        items.extend(
            [
                prop("horse", -3.7, -0.92, scale=0.80, layer="front"),
                prop("wall-door", 3.8, -1.02, scale=0.90, layer="back"),
            ]
        )
    if scene_index % 2 == 0:
        items.append(prop("weapon-rack", 0.9, -1.0, scale=0.88, layer="mid"))
    return items


def xianxia_audio(*, metal: bool = False, boom: bool = False, heart: bool = False, extra_boom: bool = False) -> dict:
    sfx = [
        {"asset_path": FIST_AUDIO, "start_ms": 4000, "volume": 0.72, "loop": False},
        {"asset_path": FIST_AUDIO, "start_ms": 8400, "volume": 0.74, "loop": False},
    ]
    if metal:
        sfx.append({"asset_path": METAL_AUDIO, "start_ms": 6200, "volume": 0.66, "loop": False})
    if boom:
        sfx.append({"asset_path": BOOM_AUDIO, "start_ms": 10800, "volume": 0.60, "loop": False})
    if extra_boom:
        sfx.append({"asset_path": BOOM_AUDIO, "start_ms": 7200, "volume": 0.50, "loop": False})
    if heart:
        sfx.append({"asset_path": HEART_AUDIO, "start_ms": 2400, "volume": 0.62, "loop": False})
    return scene_audio(sfx=sfx)


def scene_bgm(mode: str) -> dict:
    del mode
    return {"asset_path": STORY_BGM, "start_ms": 0, "volume": 0.56, "loop": True}


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
        return [
            foreground(
                fg_id,
                asset_path=(
                    "assets/foreground/开着门的室内.webp"
                    if fg_id == "开着门的室内"
                    else "assets/foreground/古典木门木窗-有点日式风格.webp"
                ),
                x=-0.01,
                y=-0.02,
                width=1.02,
                height=1.06,
                opacity=1.0,
            )
        ]
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


SCENE_SPECS = [
    SceneSpec(
        scene_id="scene-001",
        background="mountain-cliff",
        summary="天渊裂口在绝壁上空翻卷，玄玑子带云澈登临观星台，告诉他三百年前被封的血月剑劫今夜就要重开。",
        actors=[
            front_actor("xuanji", -2.4, facing="right"),
            front_actor("yun_che", 0.5, facing="left"),
            back_actor("crowd", 3.4, facing="left"),
        ],
        props=xianxia_props(0, night=True),
        lines=[
            line("xuanji", "看天渊裂口，云火倒卷，血月剑劫已经提前醒了。"),
            line("yun_che", "师父，你让我守山十年，就是为了等今晚这一场天劫？"),
            line("xuanji", "不止是等天劫，更是等能把它重新压回去的人。"),
            line("yun_che", "若真到了该出剑的时候，我不会再退。"),
        ],
        effects=[
            effect("英雄出场", start_ms=160, end_ms=2500, alpha=0.18, playback_speed=0.90),
            effect("启动大招特效", start_ms=180, end_ms=2600, alpha=0.20, playback_speed=0.86),
        ],
        audio=xianxia_audio(heart=True),
        music_mode="suspense",
    ),
    SceneSpec(
        scene_id="scene-002",
        background="room-day",
        summary="宁月在藏剑阁内摊开残破星图，发现血月剑劫的阵眼并不在山门，而在云州城下的旧祭坛。",
        actors=[
            front_actor("ning_yue", -2.5, facing="right", scale=0.94),
            front_actor("yun_che", 0.2, facing="left"),
            front_actor("xuanji", 2.6, facing="left", scale=0.92),
        ],
        props=xianxia_props(1, interior=True),
        lines=[
            line("ning_yue", "我把星图上的破口拼出来了，阵眼不在山上，在云州城地底。"),
            line("yun_che", "难怪近月来城里一直死人，原来有人在借凡人的魂火养阵。"),
            line("xuanji", "血罗天要的不是一城生灵，他要借这一城打开天渊。"),
            line("ning_yue", "那我们就先他一步进城，把阵眼挖出来。"),
        ],
    ),
    SceneSpec(
        scene_id="scene-003",
        background="night-bridge",
        summary="二人下山路过寒桥，夜苍率黑衣修士横桥截杀，试图先废掉云澈的执剑手。",
        actors=[
            front_actor("yun_che", -2.4, facing="right"),
            front_actor("ning_yue", -0.6, facing="right", scale=0.92),
            front_actor("ye_cang", 2.2, facing="left"),
            back_actor("crowd", 3.6, facing="left"),
        ],
        props=xianxia_props(2, night=True),
        lines=[
            line("ye_cang", "云澈，城门还没到，你的命先得留在这座桥上。"),
            line("yun_che", "夜苍，你倒是比你的主子先沉不住气。"),
            line("ning_yue", "桥风里有锁魂砂，他想逼你先出重剑。"),
            line("ye_cang", "看出来也晚了，今夜我要你连拔剑的手都抬不起来。"),
        ],
        extra_beats=[
            beat(4100, 7400, "ye_cang", "sword-arc", x0=2.0, x1=0.7, facing="left", effect="sword-arc"),
            beat(7700, 10800, "yun_che", "dragon-palm", x0=-2.0, x1=0.3, facing="right", effect="dragon-palm"),
        ],
        effects=[
            effect("银河旋转特效", start_ms=4040, end_ms=7420, alpha=0.24, playback_speed=0.90),
            effect("命中特效", start_ms=7700, end_ms=10000, alpha=0.22, playback_speed=0.90),
        ],
        audio=xianxia_audio(metal=True, boom=True),
        music_mode="battle",
    ),
    SceneSpec(
        scene_id="scene-004",
        background="street-day",
        summary="云州城白日看似太平，实则街巷里家家门口都挂着引魂灯，整座城像一口缓慢发热的炉。",
        actors=[
            front_actor("yun_che", -2.4, facing="right"),
            front_actor("ning_yue", 0.2, facing="left", scale=0.92),
            front_actor("cheng_zhu", 2.6, facing="left"),
            back_actor("crowd", 3.7, facing="left"),
        ],
        props=xianxia_props(3),
        lines=[
            line("cheng_zhu", "二位若真是来救城，就别再遮掩了，今夜子时之后，城下会响第二声钟。"),
            line("yun_che", "第一声钟响了什么？"),
            line("cheng_zhu", "第一声之后，城中每一盏灯都开始吸魂，我已经压不住了。"),
            line("ning_yue", "那就把城门封住，别再让血罗天往阵里添活人。"),
        ],
        effects=[effect("启动大招特效", start_ms=9200, end_ms=11200, alpha=0.18, playback_speed=0.92)],
        audio=xianxia_audio(),
        music_mode="dialogue",
    ),
    SceneSpec(
        scene_id="scene-005",
        background="town-hall-records",
        summary="城府密档中记着三百年前的封印经过，宁月发现血罗天其实是当年护阵人血裔，难怪能反向调动禁制。",
        actors=[
            front_actor("ning_yue", -2.4, facing="right", scale=0.94),
            front_actor("yun_che", 0.2, facing="left"),
            front_actor("cheng_zhu", 2.5, facing="left"),
        ],
        props=xianxia_props(4, interior=True),
        lines=[
            line("ning_yue", "旧档里写得很清楚，护阵人血裔可以逆改封印，这就是他敢开阵的底气。"),
            line("yun_che", "也就是说，若不先断他血脉牵引，封印补多少次都没用。"),
            line("cheng_zhu", "城下祭坛分成三层，最里一层只有护阵血裔能进去。"),
            line("ning_yue", "那就逼他自己进去，再在里面斩断这条线。"),
        ],
        music_mode="suspense",
    ),
    SceneSpec(
        scene_id="scene-006",
        background="archive-library",
        summary="玄玑子在藏经楼翻出最后一卷《太玄御剑图》，告诉云澈只有把剑意升到听雷境，才能在天渊裂口里稳住心神。",
        actors=[
            front_actor("xuanji", -2.2, facing="right"),
            front_actor("yun_che", 0.3, facing="left"),
            front_actor("ning_yue", 2.6, facing="left", scale=0.92),
        ],
        props=xianxia_props(5, interior=True),
        lines=[
            line("xuanji", "御剑图最后一页不是剑招，是守心法。天渊最怕的不是火，是人的念头先乱。"),
            line("yun_che", "我若在裂口里稳不住，整柄剑都会被它拖进去。"),
            line("ning_yue", "那今晚的每一步都要替你留住这口气，我来替你守后背。"),
            line("xuanji", "记住，先守心，再出剑，剑意一乱，天渊就会认你做祭品。"),
        ],
        music_mode="dialogue",
    ),
    SceneSpec(
        scene_id="scene-007",
        background="training-ground",
        summary="山门试剑坪上，云澈与宁月演练双人合阵，一人开路，一人锁风，准备在城下祭坛对血月剑潮硬开生门。",
        actors=[
            front_actor("yun_che", -2.3, facing="right"),
            front_actor("ning_yue", 2.2, facing="left", scale=0.92),
            back_actor("xuanji", 3.6, facing="left", scale=0.88),
        ],
        props=xianxia_props(6),
        lines=[
            line("ning_yue", "你一旦往前冲，我就从侧后切第二道风墙，把剑潮压窄。"),
            line("yun_che", "若我被血月引偏，你别犹豫，直接断我的剑路。"),
            line("xuanji", "你们两个要记住，合阵不是并肩往前，是一前一后互相托命。"),
            line("ning_yue", "托得住，你就敢往更深处去。"),
        ],
        extra_beats=[
            beat(4200, 7200, "yun_che", "sword-arc", x0=-1.9, x1=0.2, facing="right", effect="sword-arc"),
            beat(7600, 10800, "ning_yue", "dragon-palm", x0=2.0, x1=0.2, facing="left", effect="dragon-palm"),
        ],
        effects=[
            effect("御剑飞行", start_ms=220, end_ms=2200, alpha=0.18, playback_speed=0.92),
            effect("银河旋转特效", start_ms=4140, end_ms=7280, alpha=0.26, playback_speed=0.90),
            effect("金龙飞旋特效-适合降龙十八掌", start_ms=7600, end_ms=10500, alpha=0.24, playback_speed=0.92),
        ],
        audio=xianxia_audio(metal=True),
        music_mode="travel",
    ),
    SceneSpec(
        scene_id="scene-008",
        background="inn-hall",
        summary="夜深之后，城中幸存修士躲进客栈，玄玑子决定独自去封城北魂井，好替云澈和宁月争出一条下祭坛的时间。",
        actors=[
            front_actor("xuanji", -2.4, facing="right"),
            front_actor("yun_che", 0.1, facing="left"),
            front_actor("ning_yue", 2.5, facing="left", scale=0.92),
            back_actor("crowd", 3.7, facing="left"),
        ],
        props=xianxia_props(7, interior=True),
        lines=[
            line("xuanji", "城北魂井必须有人去堵，不然你们下到第二层时，整城魂火都会灌进去。"),
            line("yun_che", "我去堵魂井，你和宁月下去。"),
            line("xuanji", "你走的是生门，你不能换。若今晚非要有人留在外面，那个人该是我。"),
            line("ning_yue", "前辈，子时前我们一定回头接你。"),
        ],
        music_mode="suspense",
    ),
    SceneSpec(
        scene_id="scene-009",
        background="park-evening",
        summary="城北魂井先一步爆开，夜苍率人围剿玄玑子，逼他把最后一张镇魂符提前烧掉。",
        actors=[
            front_actor("xuanji", -2.3, facing="right"),
            front_actor("ye_cang", 2.4, facing="left"),
            back_actor("crowd", 3.6, facing="left"),
        ],
        props=xianxia_props(8, night=True),
        lines=[
            line("ye_cang", "老东西，镇魂符只剩一张了，你烧了它，祭坛里那两个就再也没有退路。"),
            line("xuanji", "我这一辈子守的是人，不是符，你想过桥，先从我尸骨上跨。"),
            line("ye_cang", "那我就把你这根老骨头拆给云澈看。"),
            line("xuanji", "好，来试试看，是你的刀快，还是我的命更硬。"),
        ],
        extra_beats=[
            beat(4100, 7200, "ye_cang", "sword-arc", x0=2.0, x1=0.7, facing="left", effect="sword-arc"),
            beat(7600, 10800, "xuanji", "thunder-strike", x0=-2.0, x1=0.2, facing="right", effect="thunder-strike"),
        ],
        effects=[
            effect("旋风龙卷风特效", start_ms=7580, end_ms=11000, alpha=0.26, playback_speed=0.88),
            effect("命中特效", start_ms=4200, end_ms=9800, alpha=0.22, playback_speed=0.92),
        ],
        audio=xianxia_audio(metal=True, boom=True),
        music_mode="battle",
    ),
    SceneSpec(
        scene_id="scene-010",
        background="archive-library",
        summary="云澈和宁月从密道坠入祭坛第一层，四壁全是活的符纹，血光跟着他们的呼吸一明一灭。",
        actors=[
            front_actor("yun_che", -2.2, facing="right"),
            front_actor("ning_yue", 2.2, facing="left", scale=0.92),
        ],
        props=xianxia_props(9, interior=True),
        lines=[
            line("ning_yue", "听见没有，墙上的符纹在跟着我们呼吸，它们已经把我们当成阵里的两盏灯了。"),
            line("yun_che", "别去看光，沿脚下青纹走，真正的路藏在最暗那一线。"),
            line("ning_yue", "第二层入口被封了，得有人硬开。"),
            line("yun_che", "我开门，你盯住背后，别让这些活符缠上来。"),
        ],
        effects=[
            effect("启动大招特效", start_ms=5600, end_ms=8200, alpha=0.20, playback_speed=0.88),
            effect("命中特效", start_ms=8800, end_ms=11000, alpha=0.18, playback_speed=0.90),
        ],
        audio=xianxia_audio(heart=True),
        music_mode="suspense",
    ),
    SceneSpec(
        scene_id="scene-011",
        background="temple-courtyard",
        summary="祭坛第二层的青铜门前，血罗天第一次现身。他并不急着杀人，只想看云澈有没有资格替他推开最后一层。",
        actors=[
            front_actor("yun_che", -2.2, facing="right"),
            front_actor("ning_yue", -0.4, facing="right", scale=0.92),
            front_actor("xue_luo", 2.4, facing="left"),
        ],
        props=xianxia_props(10, ritual=True),
        lines=[
            line("xue_luo", "云澈，我等了你十年，不是为了杀你，是为了让你替我把天门最后一锁砍断。"),
            line("yun_che", "你用一城人的命养出今天这一刻，也配提天门两个字。"),
            line("ning_yue", "别听他说，他在故意拖时辰，第三声钟快响了。"),
            line("xue_luo", "拖又如何，等钟响之后，你们站的位置本来就是祭台中央。"),
        ],
        effects=[effect("启动大招特效", start_ms=10200, end_ms=13600, alpha=0.22, playback_speed=0.86)],
        audio=xianxia_audio(),
        music_mode="climax",
    ),
    SceneSpec(
        scene_id="scene-012",
        background="temple-courtyard",
        summary="夜苍和云澈在青铜门前展开正面死斗，宁月一边挡住反扑的符潮，一边替云澈抢出破门角度。",
        actors=[
            front_actor("yun_che", -2.3, facing="right"),
            front_actor("ye_cang", 2.2, facing="left"),
            mid_actor("ning_yue", 0.2, facing="left", scale=0.92),
        ],
        props=xianxia_props(11, ritual=True),
        lines=[
            line("ye_cang", "你要进门，就先从我这条命上踏过去。"),
            line("yun_che", "那我就成全你，把你这条命也一并送进门里。"),
            line("ning_yue", "云澈，左三步，那边的符潮最薄，我给你压住它。"),
            line("ye_cang", "你们还真当自己能在祭坛里讲配合。"),
        ],
        extra_beats=[
            beat(3800, 7000, "ye_cang", "sword-arc", x0=2.0, x1=0.6, facing="left", effect="sword-arc"),
            beat(7200, 10400, "yun_che", "combo-punch", x0=-1.8, x1=0.7, facing="right"),
            beat(10600, 13600, "ning_yue", "dragon-palm", x0=0.6, x1=-0.2, facing="left", effect="dragon-palm"),
        ],
        effects=[
            effect("银河旋转特效", start_ms=3820, end_ms=7120, alpha=0.24, playback_speed=0.90),
            effect("命中特效", start_ms=7240, end_ms=10300, alpha=0.22, playback_speed=0.92),
            effect("金龙飞旋特效-适合降龙十八掌", start_ms=10620, end_ms=13600, alpha=0.24, playback_speed=0.90),
        ],
        audio=xianxia_audio(metal=True, boom=True),
        music_mode="battle",
    ),
    SceneSpec(
        scene_id="scene-013",
        background="night-bridge",
        summary="桥外忽然传来第三声钟，玄玑子把魂井硬封住，却也被血气反噬。云澈从祭坛深处听见钟声，心里第一次乱了一瞬。",
        actors=[
            front_actor("xuanji", -2.3, facing="right"),
            front_actor("crowd", 2.5, facing="left"),
            back_actor("ye_cang", 3.6, facing="left"),
        ],
        props=xianxia_props(12, night=True),
        lines=[
            line("xuanji", "第三声钟到了，好，老夫这一口命，就拿来给你们两个换一炷香。"),
            line("crowd", "前辈，魂井下面全是火，别再往前了。"),
            line("xuanji", "退一步，后头就是满城百姓，我这把老骨头今天本来就该钉在这儿。"),
            line("xuanji", "云澈，别回头，往最亮的地方去。"),
        ],
        effects=[
            effect("熊熊大火", start_ms=3600, end_ms=11200, alpha=0.24, playback_speed=0.88),
            effect("爆炸特效", start_ms=9800, end_ms=12800, alpha=0.20, playback_speed=0.90),
        ],
        audio=xianxia_audio(boom=True, extra_boom=True, heart=True),
        music_mode="climax",
    ),
    SceneSpec(
        scene_id="scene-014",
        background="room-day",
        summary="玄玑子的声音从符灯里传回祭坛，宁月强行稳住云澈心神，要他把这一口怒火全压进剑里，而不是压进胸口。",
        actors=[
            front_actor("yun_che", -2.2, facing="right"),
            front_actor("ning_yue", 2.2, facing="left", scale=0.92),
        ],
        props=xianxia_props(13, interior=True),
        lines=[
            line("yun_che", "师父出事了，我听见了。"),
            line("ning_yue", "你现在乱一步，他刚替我们换来的那一炷香就全白搭。"),
            line("yun_che", "我知道，可我胸口像被人生生撕开了一块。"),
            line("ning_yue", "那就把这块痛也压进剑里，别让它先把你压垮。"),
        ],
        music_mode="epilogue",
    ),
    SceneSpec(
        scene_id="scene-015",
        background="training-ground",
        summary="云澈在祭坛空隙里临时破境，剑意自听雷直入照心，周身真元开始与血月阵潮正面相抗。",
        actors=[
            front_actor("yun_che", -1.9, facing="right"),
            front_actor("ning_yue", 2.2, facing="left", scale=0.92),
        ],
        props=xianxia_props(14),
        lines=[
            line("yun_che", "原来不是我去压住天渊，是我先把自己心里的那道裂口缝上。"),
            line("ning_yue", "你的剑势变了，别停，继续把这一口气顶上去。"),
            line("yun_che", "宁月，替我守三息，三息之后，我来拆他的最后一层阵。"),
            line("ning_yue", "三息我守得住，你只管把剑送到最里面。"),
        ],
        extra_beats=[
            beat(4200, 7600, "yun_che", "thunder-strike", x0=-1.8, x1=0.3, facing="right", effect="thunder-strike"),
            beat(8000, 10800, "ning_yue", "dragon-palm", x0=2.0, x1=0.4, facing="left", effect="dragon-palm"),
        ],
        effects=[
            effect("英雄出场", start_ms=4200, end_ms=6900, alpha=0.20, playback_speed=0.90),
            effect("旋风龙卷风特效", start_ms=4220, end_ms=7600, alpha=0.26, playback_speed=0.88),
            effect("金龙飞旋特效-适合降龙十八掌", start_ms=8020, end_ms=10840, alpha=0.24, playback_speed=0.90),
        ],
        audio=xianxia_audio(boom=True),
        music_mode="climax",
    ),
    SceneSpec(
        scene_id="scene-016",
        background="street-day",
        summary="澄主带城中修士逆行入阵，把残存魂灯全部推倒，血月大阵外层终于出现第一次明显松动。",
        actors=[
            front_actor("cheng_zhu", -2.3, facing="right"),
            front_actor("crowd", 0.4, facing="left"),
            back_actor("ning_yue", 3.6, facing="left", scale=0.88),
        ],
        props=xianxia_props(15),
        lines=[
            line("cheng_zhu", "全城听令，今夜谁都别再跪着等死，把灯砸了，把魂火从他阵里抢回来。"),
            line("crowd", "砸灯，砸灯，把这条街一盏不留。"),
            line("cheng_zhu", "云澈，你在下面若还能听见，就知道城里还没塌。"),
            line("crowd", "我们把外层给你撕开，你只管往最深处杀。"),
        ],
        effects=[
            effect("热烈鼓掌", start_ms=2600, end_ms=5200, alpha=0.16, playback_speed=0.92),
            effect("爆炸特效", start_ms=8800, end_ms=12000, alpha=0.18, playback_speed=0.92),
        ],
        audio=xianxia_audio(boom=True),
        music_mode="battle",
    ),
    SceneSpec(
        scene_id="scene-017",
        background="temple-courtyard",
        summary="血罗天被迫亲自踏进最后一层阵眼，他想借云澈破门的瞬间吞并其剑骨，两人终于站到同一座狭窄祭台上。",
        actors=[
            front_actor("yun_che", -2.2, facing="right"),
            front_actor("xue_luo", 2.2, facing="left"),
            mid_actor("ning_yue", -0.2, facing="right", scale=0.92),
        ],
        props=xianxia_props(16, ritual=True),
        lines=[
            line("xue_luo", "很好，你果然把门劈开了。接下来只要你这身剑骨归我，天渊就会听我的。"),
            line("yun_che", "你想借我进门，我也一样想借你把最后一层血脉牵引彻底斩断。"),
            line("ning_yue", "阵眼已经浮出来了，就在他脚下那圈最亮的血纹里。"),
            line("xue_luo", "看见又如何，看见的人，往往死得更快。"),
        ],
        effects=[effect("启动大招特效", start_ms=9600, end_ms=13400, alpha=0.22, playback_speed=0.86)],
        audio=xianxia_audio(),
        music_mode="climax",
    ),
    SceneSpec(
        scene_id="scene-018",
        background="temple-courtyard",
        summary="宁月替云澈吃下血罗天一记反噬重击，身形被掀进阵边。云澈第一次完全放开剑意，祭台上空开始落下真正的天雷。",
        actors=[
            front_actor("yun_che", -2.1, facing="right"),
            front_actor("ning_yue", 0.4, facing="left", scale=0.92),
            front_actor("xue_luo", 2.4, facing="left"),
        ],
        props=xianxia_props(17, ritual=True),
        lines=[
            line("xue_luo", "你护得住他一次，护不住第二次。"),
            line("ning_yue", "我能替他扛到这一刻，就已经够了，剩下的路让他自己去斩。"),
            line("yun_che", "宁月，别闭眼，等我一剑回来。"),
            line("xue_luo", "来，给我看看你到底能把这一剑抬到多高。"),
        ],
        extra_beats=[
            beat(4200, 7600, "xue_luo", "thunder-strike", x0=2.1, x1=0.7, facing="left", effect="thunder-strike"),
            beat(8200, 11000, "yun_che", "sword-arc", x0=-1.8, x1=0.8, facing="right", effect="sword-arc"),
        ],
        effects=[
            effect("死亡光线特效", start_ms=4200, end_ms=7600, alpha=0.22, playback_speed=0.90),
            effect("旋风龙卷风特效", start_ms=4200, end_ms=7600, alpha=0.28, playback_speed=0.88),
            effect("银河旋转特效", start_ms=8220, end_ms=11200, alpha=0.26, playback_speed=0.90),
        ],
        audio=xianxia_audio(metal=True, boom=True),
        music_mode="climax",
    ),
    SceneSpec(
        scene_id="scene-019",
        background="mountain-cliff",
        summary="祭台被一剑掀进高空，云澈与血罗天在裂口边缘展开最后空战，满天雷火像是把整座山都劈成了流动的青银色。",
        actors=[
            front_actor("yun_che", -2.1, facing="right"),
            front_actor("xue_luo", 2.2, facing="left"),
            back_actor("ning_yue", -3.6, facing="right", scale=0.84),
        ],
        props=xianxia_props(18, night=True),
        lines=[
            line("xue_luo", "你看见没有，这才是真正的天门，凡人哪配把它关回去。"),
            line("yun_che", "天门若只肯收你这种人，那它就不配立在天上。"),
            line("ning_yue", "云澈，阵眼已经全亮了，现在就是最后一剑。"),
            line("xue_luo", "那就来，让我看看你这一剑能不能穿过天渊。"),
        ],
        extra_beats=[
            beat(3600, 6800, "xue_luo", "thunder-strike", x0=2.0, x1=0.6, facing="left", effect="thunder-strike"),
            beat(7000, 10000, "yun_che", "dragon-palm", x0=-1.8, x1=0.1, facing="right", effect="dragon-palm"),
            beat(10200, 13800, "yun_che", "sword-arc", x0=0.1, x1=1.1, facing="right", effect="sword-arc"),
        ],
        effects=[
            effect("御剑飞行", start_ms=260, end_ms=2400, alpha=0.18, playback_speed=0.92),
            effect("死亡光线特效", start_ms=3600, end_ms=6900, alpha=0.22, playback_speed=0.90),
            effect("旋风龙卷风特效", start_ms=3600, end_ms=6900, alpha=0.28, playback_speed=0.86),
            effect("金龙飞旋特效-适合降龙十八掌", start_ms=7020, end_ms=10000, alpha=0.26, playback_speed=0.88),
            effect("银河旋转特效", start_ms=10200, end_ms=13800, alpha=0.28, playback_speed=0.90),
            effect("爆炸特效", start_ms=11200, end_ms=13800, alpha=0.20, playback_speed=0.92),
        ],
        audio=xianxia_audio(metal=True, boom=True, extra_boom=True),
        music_mode="climax",
    ),
    SceneSpec(
        scene_id="scene-020",
        background="mountain-cliff",
        summary="最后一剑穿过血罗天与阵眼，天渊裂口终于缓慢合拢。天光落回山崖，宁月等到云澈从余火里走出来，这场剑劫也随之落幕。",
        actors=[
            front_actor("ning_yue", -2.4, facing="right", scale=0.92),
            front_actor("yun_che", 0.4, facing="left"),
            back_actor("cheng_zhu", 2.8, facing="left"),
            back_actor("crowd", 3.7, facing="left"),
        ],
        props=xianxia_props(19, night=False),
        lines=[
            line("ning_yue", "云澈，你总算肯从火里走出来了。"),
            line("yun_che", "裂口已经合了，师父替我们撑住的那一口气，我总算没辜负。"),
            line("cheng_zhu", "云州城记住的不会只是这一夜的火，也会记住是谁把天重新按回了原位。"),
            line("yun_che", "天是按回去了，可该走的路还长，我们下山去，把剩下的乱局一点点收干净。"),
        ],
        effects=[
            effect("启动大招特效", start_ms=200, end_ms=2200, alpha=0.16, playback_speed=0.92),
            effect("热烈鼓掌", start_ms=11800, end_ms=14500, alpha=0.16, playback_speed=0.92),
        ],
        audio=xianxia_audio(),
        music_mode="epilogue",
    ),
]


class TianyuanSwordTribulationVideo(BaseVideoScript):
    def get_title(self) -> str:
        return "天渊剑劫"

    def get_theme(self) -> str:
        return "仙侠、剑劫、血月、封印、御剑、宿命、热血、救城"

    def get_cast(self) -> list[dict]:
        return CAST

    def get_video_options(self) -> dict:
        return VIDEO

    def has_tts(self) -> bool:
        return True

    def get_notes(self) -> dict:
        return {
            "scene_count": len(SCENE_SPECS),
            "format": "tianyuan-sword-tribulation",
            "bgm_assets": [STORY_BGM],
        }

    def get_default_output(self) -> str:
        return "outputs/tianyuan_sword_tribulation.mp4"

    def get_description(self) -> str:
        return "Render a 20-scene xianxia epic with TTS, looping BGM, layered effects, and dense battle sound design."

    def get_scenes(self) -> list[dict]:
        scenes: list[dict] = []
        for scene_index, spec in enumerate(SCENE_SPECS):
            dialogue_items, talk_beats, expressions_track = build_dialogue_bundle(spec.lines)
            talk_beats = trim_talk_beats_for_actions(talk_beats, spec.extra_beats)
            beats = sorted([*talk_beats, *spec.extra_beats], key=lambda item: (item["start_ms"], item["actor_id"]))
            expressions_sorted = sorted(expressions_track, key=lambda item: (item["start_ms"], item["actor_id"]))
            battle = bool(spec.extra_beats or spec.effects)
            climax = spec.music_mode == "climax"
            audio_payload = scene_audio(
                bgm=scene_bgm(spec.music_mode),
                sfx=list(spec.audio.get("sfx", [])),
            )
            scenes.append(
                scene(
                    spec.scene_id,
                    background=spec.background,
                    floor=FLOOR_BY_BACKGROUND[spec.background],
                    duration_ms=SCENE_DURATION_MS,
                    summary=spec.summary,
                    camera=spec.camera or scene_camera(scene_index, battle=battle, climax=climax),
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


SCRIPT = TianyuanSwordTribulationVideo()


def build_story() -> dict:
    return SCRIPT.build_story()


def main() -> int:
    return SCRIPT()


if __name__ == "__main__":
    raise SystemExit(main())
