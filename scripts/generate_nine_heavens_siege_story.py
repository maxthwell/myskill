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
    cast_member("qin_ye", "秦夜", "general-guard"),
    cast_member("lan_shu", "岚书", "npc-girl"),
    cast_member("mo_xing", "墨行", "detective-sleek"),
    cast_member("old_master", "苍岚真人", "farmer-old"),
    cast_member("ye_huang", "夜皇", "official-minister"),
    cast_member("prince", "晏昭太子", "emperor-ming"),
    cast_member("crowd", "九天守军", "npc-boy"),
]

SCENE_DURATION_MS = 14_800
DIALOGUE_WINDOWS = [
    (400, 2900),
    (3500, 6100),
    (7400, 10000),
    (10900, 13700),
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

OMEN_BGM = "assets/bgm/误入迷失森林-少年包青天.mp3"
MARCH_BGM = "assets/bgm/御剑飞行.mp3"
WAR_BGM = "assets/bgm/杀破狼.mp3"
CRISIS_BGM = "assets/bgm/观音降临-高潮版.mp3"
FINAL_BGM = "assets/bgm/最后之战-热血-卢冠廷.mp3"
DAWN_BGM = "assets/bgm/仙剑情缘.mp3"


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


def mid_actor(actor_id: str, x: float, *, facing: str, scale: float = 0.94, z: float = -0.14) -> dict:
    return actor(actor_id, x, z=z, facing=facing, scale=scale, layer="mid")


def back_actor(actor_id: str, x: float, *, facing: str, scale: float = 0.88, z: float = -0.72) -> dict:
    return actor(actor_id, x, z=z, facing=facing, scale=scale, layer="back")


def infer_expression(text: str) -> str:
    if any(token in text for token in ("杀", "斩", "冲", "破", "战", "守", "封", "轰", "退", "阵")):
        return "angry"
    if any(token in text for token in ("快", "立刻", "跟上", "别停", "马上", "升空")):
        return "excited"
    if any(token in text for token in ("阵眼", "禁制", "图卷", "灵脉", "破绽", "钥匙")):
        return "thinking"
    if any(token in text for token in ("活下来了", "守住", "天亮", "回来")):
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
        return camera_pan(x=-0.30, z=0.07, zoom=1.12, to_x=0.26, to_z=0.02, to_zoom=1.22, ease="ease-in-out")
    if battle:
        return camera_pan(x=-0.24 + 0.05 * (scene_index % 3), z=0.04, zoom=1.08, to_x=0.18, to_z=0.0, to_zoom=1.16, ease="ease-in-out")
    if scene_index in {0, 14, 29}:
        return camera_static(x=0.0, z=0.03, zoom=1.08)
    return camera_pan(x=-0.16, z=0.02, zoom=1.0, to_x=0.12, to_z=0.0, to_zoom=1.06, ease="ease-in-out")


def city_props(scene_index: int, *, interior: bool = False, night: bool = False, ritual: bool = False) -> list[dict]:
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
            prop("weapon-rack" if scene_index % 2 == 0 else "training-drum", 0.0, -1.02, scale=0.90, layer="mid"),
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


def story_audio(*, metal: bool = False, boom: bool = False, heart: bool = False, inferno: bool = False, crowd: bool = False) -> dict:
    sfx = [
        {"asset_path": FIST_AUDIO, "start_ms": 3900, "volume": 0.84, "loop": False},
        {"asset_path": FIST_AUDIO, "start_ms": 7600, "volume": 0.82, "loop": False},
    ]
    if metal:
        sfx.append({"asset_path": METAL_AUDIO, "start_ms": 5600, "volume": 0.76, "loop": False})
        sfx.append({"asset_path": METAL_AUDIO, "start_ms": 9800, "volume": 0.72, "loop": False})
    if boom:
        sfx.append({"asset_path": BOOM_AUDIO, "start_ms": 6800, "volume": 0.72, "loop": False})
        sfx.append({"asset_path": BOOM_AUDIO, "start_ms": 11100, "volume": 0.66, "loop": False})
    if heart:
        sfx.append({"asset_path": HEART_AUDIO, "start_ms": 2200, "volume": 0.62, "loop": False})
    if inferno:
        sfx.append({"asset_path": BOOM_AUDIO, "start_ms": 2600, "volume": 0.52, "loop": False})
    if crowd:
        sfx.append({"asset_path": FIST_AUDIO, "start_ms": 11800, "volume": 0.60, "loop": False})
    return scene_audio(sfx=sfx)


def scene_bgm(scene_index: int) -> dict:
    if scene_index <= 4:
        path, volume = OMEN_BGM, 0.50
    elif scene_index <= 9:
        path, volume = MARCH_BGM, 0.56
    elif scene_index <= 17:
        path, volume = WAR_BGM, 0.64
    elif scene_index <= 23:
        path, volume = CRISIS_BGM, 0.60
    elif scene_index <= 28:
        path, volume = FINAL_BGM, 0.66
    else:
        path, volume = DAWN_BGM, 0.50
    return {"asset_path": path, "start_ms": 0, "volume": volume, "loop": True}


def default_foregrounds(scene_index: int, background: str) -> list[dict]:
    if background in {"temple-courtyard", "theatre-stage"}:
        return [foreground("敞开的红色帘子-窗帘或床帘皆可", asset_path="assets/foreground/敞开的红色帘子-窗帘或床帘皆可.webp", x=-0.02, y=-0.04, width=1.04, height=1.08, opacity=1.0)]
    if background in {"room-day", "archive-library", "town-hall-records", "inn-hall"}:
        fg_id = "开着门的室内" if scene_index % 2 == 0 else "古典木门木窗-有点日式风格"
        fg_path = "assets/foreground/开着门的室内.webp" if fg_id == "开着门的室内" else "assets/foreground/古典木门木窗-有点日式风格.webp"
        return [foreground(fg_id, asset_path=fg_path, x=-0.01, y=-0.02, width=1.02, height=1.06, opacity=1.0)]
    if background in {"night-bridge", "park-evening", "street-day", "training-ground", "mountain-cliff"}:
        return [foreground("中式古典大门", asset_path="assets/foreground/中式古典大门.webp", x=-0.01, y=-0.02, width=1.02, height=1.06, opacity=1.0)]
    return []


def duel_beats(left_id: str, right_id: str, *, left_x: float, right_x: float, airborne: bool = False, heavy: bool = False) -> list[dict]:
    jump_z = 0.16 if airborne else 0.04
    return [
        beat(3300, 4500, left_id, "straight-punch", x0=left_x, x1=left_x + 0.45, z0=0.0, z1=jump_z, facing="right", effect="hit"),
        beat(4700, 5900, right_id, "hook-punch", x0=right_x, x1=right_x - 0.38, z0=0.0, z1=jump_z, facing="left", effect="hit"),
        beat(6400, 7700, left_id, "combo-punch" if heavy else "swing-punch", x0=left_x + 0.22, x1=left_x + 0.80, z0=jump_z, z1=0.02, facing="right", effect="dragon-palm" if heavy else "hit"),
        beat(8200, 9400, right_id, "diagonal-kick" if airborne else "spin-kick", x0=right_x - 0.14, x1=right_x - 0.76, z0=jump_z, z1=0.02, facing="left", effect="thunder-strike"),
        beat(10000, 11300, left_id, "double-palm-push", x0=left_x + 0.40, x1=left_x + 0.98, z0=0.0, z1=0.0, facing="right", effect="sword-arc"),
    ]


def flight_combo(actor_id: str, *, start_x: float, facing: str) -> list[dict]:
    direction = 1.0 if facing == "right" else -1.0
    return [
        beat(3600, 4900, actor_id, "flying-kick", x0=start_x, x1=start_x + 0.9 * direction, z0=0.02, z1=0.22, facing=facing, effect="thunder-strike"),
        beat(5300, 6600, actor_id, "spin-kick", x0=start_x + 0.8 * direction, x1=start_x + 1.3 * direction, z0=0.18, z1=0.08, facing=facing, effect="hit"),
        beat(7600, 9000, actor_id, "double-palm-push", x0=start_x + 1.0 * direction, x1=start_x + 1.7 * direction, z0=0.06, z1=0.10, facing=facing, effect="sword-arc"),
    ]


SCENE_SPECS = [
    SceneSpec("scene-001", "mountain-cliff", "九天城外雷海翻卷，秦夜在崖顶看到黑环压城，知道围城大战终于开始。", [front_actor("old_master", -2.4, facing="right"), front_actor("qin_ye", 0.4, facing="left"), back_actor("crowd", 3.4, facing="left")], city_props(0, night=True), [line("old_master", "看见那道黑环没有，它不是云，是夜皇拿来锁城的天阙。"), line("qin_ye", "锁得再紧也要劈开，不然今夜城里的人一个都活不了。"), line("lan_shu", "东南天幕也亮了，魔军不是围一面，是四门同压。"), line("qin_ye", "那就从最窄的那道口子杀出去，把他们的环先崩掉。")], effects=[effect("黑洞旋转", start_ms=2600, end_ms=14500, alpha=0.18, playback_speed=0.88), effect("风起云涌", start_ms=300, end_ms=2200, alpha=0.16, playback_speed=0.92)], audio=story_audio(heart=True)),
    SceneSpec("scene-002", "temple-courtyard", "太子晏昭在祭天台召集守军，宣布九天城从此刻起全城戒严。", [front_actor("prince", -2.2, facing="right"), front_actor("lan_shu", 0.2, facing="left"), mid_actor("qin_ye", 2.8, facing="left"), back_actor("crowd", 3.9, facing="left")], city_props(1, ritual=True), [line("prince", "四门封禁，百姓下地窖，守军全部上墙。"), line("lan_shu", "符炮营、御剑营和城防弩都已归位，只等你一句话。"), line("qin_ye", "别等命令落第二遍，谁守哪一段，自己心里该有数。"), line("prince", "今夜若天塌，先砸我头上，但城不能先丢。")], effects=[effect("风起云涌", start_ms=1000, end_ms=3400, alpha=0.16, playback_speed=0.92)], audio=story_audio(crowd=True)),
    SceneSpec("scene-003", "archive-library", "墨行在藏经楼翻出旧图，发现黑环真正锁的是城底九曜石柱。", [front_actor("mo_xing", -2.3, facing="right"), front_actor("old_master", 0.6, facing="left"), back_actor("lan_shu", 3.1, facing="left")], city_props(2, interior=True), [line("mo_xing", "图卷在这，夜皇不是冲城墙来的，他冲的是九曜石柱。"), line("old_master", "石柱一断，城上结界会自己崩。"), line("lan_shu", "那我们就得有人守城，也得有人下地宫。"), line("mo_xing", "对，今夜打的不是一处，是上天入地两条战线。")], effects=[effect("黑洞旋转", start_ms=3800, end_ms=7600, alpha=0.14, playback_speed=0.90)], audio=story_audio(heart=True)),
    SceneSpec("scene-004", "inn-hall", "秦夜与岚书在客栈密谈，决定把最精锐的一队人送去地宫。", [front_actor("qin_ye", -2.0, facing="right"), front_actor("lan_shu", 2.0, facing="left"), back_actor("mo_xing", 0.0, facing="left", scale=0.9)], city_props(3, interior=True), [line("qin_ye", "地宫那一路你去，我在上面顶最重的冲锋。"), line("lan_shu", "你每次都把最险的地方留给自己，这回轮到我先下去。"), line("mo_xing", "别争，你们两个都得活，不然这局到了后半段没人收。"), line("qin_ye", "好，你下地宫，我守城门，谁先打穿谁就去接对方。")], audio=story_audio()),
    SceneSpec("scene-005", "training-ground", "校场誓师，守军知道今夜之后，九天城要么存要么灭。", [front_actor("qin_ye", -2.1, facing="right"), front_actor("prince", 0.5, facing="left"), back_actor("crowd", 3.4, facing="left")], city_props(4, ritual=True), [line("qin_ye", "今日不求你们人人不死，只求你们死也站着死。"), line("prince", "守军听令，四门不退，地宫不断，九曜不灭。"), line("crowd", "死守九天，死守九天！"), line("qin_ye", "好，把这句话喊到天亮，让外头的人先怕。")], effects=[effect("风起云涌", start_ms=700, end_ms=2800, alpha=0.16, playback_speed=0.92), effect("绚烂的烟花", start_ms=11600, end_ms=14200, alpha=0.12, playback_speed=0.96)], audio=story_audio(crowd=True)),
    SceneSpec("scene-006", "night-bridge", "城南夜桥先迎敌，第一支魔骑像黑潮一样撞上桥面。", [front_actor("qin_ye", -2.2, facing="right"), front_actor("crowd", 0.8, facing="left", scale=0.96), mid_actor("ye_huang", 3.1, facing="left")], city_props(5, night=True), [line("crowd", "桥头黑影到了，至少三阵，后面还有更大的！"), line("qin_ye", "先把桥口钉住，他们挤不进来，后面的阵就全废。"), line("ye_huang", "一座桥也敢守，秦夜，你这是把命交给河风。"), line("qin_ye", "交给风总比交给你强，想过桥，先把头递过来。")], extra_beats=duel_beats("qin_ye", "ye_huang", left_x=-2.0, right_x=3.0, heavy=True), effects=[effect("千军万马冲杀", start_ms=1200, end_ms=14500, alpha=0.18, playback_speed=0.90), effect("爆炸特效", start_ms=6900, end_ms=8200, alpha=0.18, playback_speed=0.92)], audio=story_audio(metal=True, boom=True)),
    SceneSpec("scene-007", "street-day", "外街被撞开一线，守军边退边打，把百姓往内城推。", [front_actor("lan_shu", -2.1, facing="right"), front_actor("crowd", 0.5, facing="left"), back_actor("prince", 3.1, facing="left")], city_props(6, night=False), [line("lan_shu", "人往里退，阵石往后抬，别在街心堵成一团。"), line("crowd", "西街已经起火，再退就退进民宅了！"), line("prince", "把水符送过去，先保住街心那道分流墙。"), line("lan_shu", "墙要守，人也要活，跟我把火线往前压。")], extra_beats=[beat(5200, 6500, "lan_shu", "flying-kick", x0=-2.0, x1=-1.0, z0=0.0, z1=0.22, facing="right", effect="thunder-strike"), beat(8000, 9300, "lan_shu", "straight-punch", x0=-1.2, x1=-0.4, z0=0.08, z1=0.0, facing="right", effect="hit")], effects=[effect("熊熊大火", start_ms=400, end_ms=14600, alpha=0.16, playback_speed=0.90), effect("火烧赤壁", start_ms=3600, end_ms=10800, alpha=0.14, playback_speed=0.92)], audio=story_audio(boom=True, inferno=True)),
    SceneSpec("scene-008", "room-day", "地宫入口被打开，墨行带小队冲入石廊，抢在魔兵前面寻找九曜石柱。", [front_actor("mo_xing", -2.1, facing="right"), front_actor("lan_shu", 0.7, facing="left"), back_actor("crowd", 3.2, facing="left")], city_props(7, interior=True), [line("mo_xing", "脚下这层空声不对，前面有暗门，别一口气全冲进去。"), line("lan_shu", "你探机关，我挡前排，先把石柱区找出来。"), line("crowd", "前面有铁链声，他们已经在动柱子了！"), line("mo_xing", "那就快，今晚最要命的不是天上，是脚底。")], effects=[effect("激光剑对战", start_ms=7600, end_ms=11200, alpha=0.14, playback_speed=0.96)], audio=story_audio(metal=True)),
    SceneSpec("scene-009", "park-evening", "第一轮空战爆发，岚书和御剑营从城墙上空俯冲而下。", [front_actor("lan_shu", -2.2, facing="right"), front_actor("qin_ye", 0.4, facing="left"), back_actor("crowd", 3.6, facing="left")], city_props(8, night=True), [line("lan_shu", "御剑营随我上云层，先剪掉他们外圈黑翼。"), line("qin_ye", "你从上面压，我在下面接，不让他们靠近内城。"), line("crowd", "天上全亮了，像一整条白河在往下砸。"), line("lan_shu", "别看，盯住你的箭位，我会把最前面的都打散。")], extra_beats=flight_combo("lan_shu", start_x=-2.2, facing="right"), effects=[effect("御剑飞行", start_ms=200, end_ms=10300, alpha=0.18, playback_speed=0.94), effect("飞踢", start_ms=5200, end_ms=6700, alpha=0.18, playback_speed=0.95)], audio=story_audio(metal=True, boom=True), camera=scene_camera(8, battle=True, aerial=True)),
    SceneSpec("scene-010", "town-hall-records", "晏昭太子在军府重新布令，把守城、地宫和空战三线时间压成一条。", [front_actor("prince", -2.2, facing="right"), front_actor("mo_xing", 0.1, facing="left"), front_actor("qin_ye", 2.6, facing="left", scale=0.94)], city_props(9, interior=True), [line("prince", "现在起所有军令只看一件事，哪一路先打出空隙。"), line("mo_xing", "地宫再给我一刻，石柱的锁环我已经看见了。"), line("qin_ye", "我把桥头和西街再顶两轮，你只管快。"), line("prince", "好，谁先破局，谁就去救另外两路。")], audio=story_audio(heart=True)),
    SceneSpec("scene-011", "archive-library", "墨行发现古卷里夹着一张旧城图，图上记着一条通向主柱背面的废廊。", [front_actor("mo_xing", -2.2, facing="right"), front_actor("old_master", 0.3, facing="left"), back_actor("lan_shu", 3.0, facing="left")], city_props(10, interior=True), [line("mo_xing", "找到了，主柱背后有废廊，夜皇的人未必知道。"), line("old_master", "那条廊是旧年封死的，进去的人多半回不来。"), line("lan_shu", "回不来总比等死强，把图给我，我从侧面插进去。"), line("mo_xing", "行，我带两个人绕后，你继续守地面那道口。")], effects=[effect("黑洞旋转", start_ms=4100, end_ms=7600, alpha=0.14, playback_speed=0.90)], audio=story_audio(heart=True)),
    SceneSpec("scene-012", "inn-hall", "伤兵和百姓在客栈里暂避，秦夜抽空回来交代后路，却不肯真正休息。", [front_actor("qin_ye", -2.0, facing="right"), front_actor("lan_shu", 2.1, facing="left"), back_actor("prince", 0.2, facing="left", scale=0.9)], city_props(11, interior=True), [line("lan_shu", "你肩上已经见血，再不包扎，后半夜手会发抖。"), line("qin_ye", "抖也得抬刀，桥头那边还在往里涌。"), line("prince", "我不是来劝你退，是来告诉你，内城百姓都知道你还站着。"), line("qin_ye", "那就更不能倒，我还没把今夜最狠的那一刀送出去。")], audio=story_audio()),
    SceneSpec("scene-013", "training-ground", "夜皇派出黑甲先锋压校场，秦夜带精锐与之硬碰硬。", [front_actor("qin_ye", -2.2, facing="right"), front_actor("ye_huang", 2.1, facing="left"), back_actor("crowd", 3.7, facing="left")], city_props(12, ritual=True), [line("ye_huang", "你的城墙都开始掉灰了，还想守到几时。"), line("qin_ye", "守到你的人先躺满校场，再问我几时。"), line("crowd", "统领，黑甲先锋进场了，后面还有两层！"), line("qin_ye", "那就拿这里做坟场，谁也别让他们越线。")], extra_beats=duel_beats("qin_ye", "ye_huang", left_x=-2.1, right_x=2.0, heavy=True), effects=[effect("千军万马冲杀", start_ms=900, end_ms=5200, alpha=0.16, playback_speed=0.92), effect("命中特效", start_ms=10300, end_ms=11800, alpha=0.18, playback_speed=0.92)], audio=story_audio(metal=True, boom=True, crowd=True)),
    SceneSpec("scene-014", "theatre-stage", "夜皇在旧戏台上张开幻阵，试图用假天幕把御剑营全部引偏。", [front_actor("lan_shu", -2.2, facing="right"), front_actor("ye_huang", 2.0, facing="left"), back_actor("crowd", 0.0, facing="left", scale=0.9)], city_props(13, ritual=True), [line("ye_huang", "看清楚了，真正的门在你背后，你每冲一次都在帮我分你的兵。"), line("lan_shu", "幻阵吓得住别人，吓不住我，我只认风向和杀意。"), line("crowd", "苏统领，台上台下全在晃，分不清哪边是真的！"), line("lan_shu", "那就别分，跟着我往最亮的地方冲，假的自己会碎。")], extra_beats=[beat(4200, 5500, "lan_shu", "spin-kick", x0=-2.1, x1=-1.2, z0=0.0, z1=0.18, facing="right", effect="hit"), beat(7600, 9000, "lan_shu", "double-palm-push", x0=-1.0, x1=0.0, z0=0.08, z1=0.12, facing="right", effect="sword-arc")], effects=[effect("激光剑对战", start_ms=3000, end_ms=9400, alpha=0.16, playback_speed=0.95), effect("风起云涌", start_ms=9600, end_ms=12000, alpha=0.16, playback_speed=0.92)], audio=story_audio(metal=True, boom=True)),
    SceneSpec("scene-015", "room-day", "地宫主柱露出真形，墨行发现石柱外还有一层血锁，必须用活人的真气反冲。", [front_actor("mo_xing", -2.2, facing="right"), front_actor("old_master", 0.5, facing="left"), back_actor("lan_shu", 3.0, facing="left")], city_props(14, interior=True), [line("mo_xing", "主柱到了，可外面这层血锁不是机关，是活阵。"), line("old_master", "要破它，得有人贴上去硬顶，阵会反咬人。"), line("lan_shu", "那就我来，反正上面那口气也迟早要还。"), line("mo_xing", "别急，先把锁环转开一半，不然你送进去的命会全白费。")], effects=[effect("启动大招特效", start_ms=7200, end_ms=9400, alpha=0.16, playback_speed=0.92)], audio=story_audio(heart=True)),
    SceneSpec("scene-016", "street-day", "西街第二次被冲开，夜皇放出的骑兵从火里穿出来，守军几乎被截成两段。", [front_actor("qin_ye", -2.0, facing="right"), front_actor("crowd", 0.9, facing="left"), back_actor("ye_huang", 3.2, facing="left")], city_props(15, night=False), [line("crowd", "火里还有骑兵，他们从火墙后面直接撞出来了！"), line("qin_ye", "别慌，先打腿，再打马，街太窄，他们跑不起来。"), line("ye_huang", "你的街、你的火、你的守军，现在都在帮我绞死你。"), line("qin_ye", "你再近一点，我连你这张嘴一起钉在墙上。")], extra_beats=[beat(5000, 6300, "qin_ye", "hook-punch", x0=-1.9, x1=-1.1, z0=0.0, z1=0.08, facing="right", effect="hit"), beat(7600, 9000, "qin_ye", "flying-kick", x0=-1.2, x1=-0.2, z0=0.04, z1=0.22, facing="right", effect="thunder-strike"), beat(9800, 11200, "qin_ye", "double-palm-push", x0=-0.3, x1=0.8, z0=0.10, z1=0.04, facing="right", effect="dragon-palm")], effects=[effect("骑兵冲杀", start_ms=900, end_ms=12800, alpha=0.18, playback_speed=0.90), effect("熊熊大火", start_ms=300, end_ms=14500, alpha=0.14, playback_speed=0.92)], audio=story_audio(boom=True, inferno=True, crowd=True)),
    SceneSpec("scene-017", "night-bridge", "夜皇站上桥拱高处，第一次抬起死光，整段桥身被照得像要融开。", [front_actor("ye_huang", -2.1, facing="right"), front_actor("qin_ye", 0.8, facing="left"), back_actor("crowd", 3.4, facing="left")], city_props(16, night=True), [line("ye_huang", "看见了吗，死光一落，桥和城门会一起化掉。"), line("crowd", "统领，桥面在发红，再不退人会和石头一起烂掉！"), line("qin_ye", "桥不能让，桥一丢，内城全见光。"), line("ye_huang", "那你就守着它一起死吧。")], effects=[effect("死亡光线特效", start_ms=3000, end_ms=9800, alpha=0.18, playback_speed=0.96), effect("爆炸特效", start_ms=10100, end_ms=11800, alpha=0.18, playback_speed=0.92)], audio=story_audio(boom=True, heart=True)),
    SceneSpec("scene-018", "park-evening", "岚书率御剑营从死光上方斜切而下，硬把空中的黑翼群撕开一道裂缝。", [front_actor("lan_shu", -2.1, facing="right"), front_actor("crowd", 0.7, facing="left"), back_actor("ye_huang", 3.1, facing="left")], city_props(17, night=True), [line("lan_shu", "所有人抬高半层，从死光上沿切进去，别正面对冲。"), line("crowd", "上方风暴太乱了，再高一点就会被卷散！"), line("lan_shu", "散也得上，下面的人正替我们拿命顶桥。"), line("ye_huang", "你这一群飞剑，能救几个？我一束光就够。")], extra_beats=flight_combo("lan_shu", start_x=-2.0, facing="right"), effects=[effect("御剑飞行", start_ms=300, end_ms=11000, alpha=0.18, playback_speed=0.95), effect("死亡光线特效", start_ms=8200, end_ms=10800, alpha=0.16, playback_speed=0.96), effect("飞踢", start_ms=5200, end_ms=6900, alpha=0.18, playback_speed=0.95)], audio=story_audio(metal=True, boom=True), camera=scene_camera(17, battle=True, aerial=True)),
    SceneSpec("scene-019", "temple-courtyard", "三线汇总后，太子在祭台上做最后一次调兵，把所有可动之兵全压向终局。", [front_actor("prince", -2.1, facing="right"), front_actor("mo_xing", 0.2, facing="left"), front_actor("qin_ye", 2.7, facing="left", scale=0.94)], city_props(18, ritual=True), [line("prince", "地宫还差最后一扣，桥头还差最后一断，空战还差最后一压。"), line("mo_xing", "主柱背廊已经打开，我这边快要碰到锁心。"), line("qin_ye", "给我最能冲的那一队，我去夜皇身边把死光掐掉。"), line("prince", "去吧，今夜不再讲退路，只讲哪一口气先断。")], effects=[effect("风起云涌", start_ms=900, end_ms=2900, alpha=0.16, playback_speed=0.92)], audio=story_audio(crowd=True)),
    SceneSpec("scene-020", "town-hall-records", "墨行在军府旧图上找到夜皇真正的落脚点，原来他把本体藏在天门阴影里。", [front_actor("mo_xing", -2.2, facing="right"), front_actor("old_master", 0.4, facing="left"), back_actor("prince", 3.0, facing="left")], city_props(19, interior=True), [line("mo_xing", "找到了，夜皇每次抬光都不离这片阴影，他本体就在这。"), line("old_master", "难怪他一直像打不死，原来你们一直只是在碰影子。"), line("prince", "把位置送给秦夜，告诉他别再跟光拼，要跟人拼。"), line("mo_xing", "好，只要他能靠近那片影子，今夜就有翻盘的口子。")], effects=[effect("黑洞旋转", start_ms=4300, end_ms=7600, alpha=0.14, playback_speed=0.90)], audio=story_audio(heart=True)),
    SceneSpec("scene-021", "archive-library", "岚书在废廊口与黑翼统领遭遇，必须先清掉这层守卫，地宫才有时间完成封锁。", [front_actor("lan_shu", -2.2, facing="right"), front_actor("ye_huang", 2.0, facing="left"), back_actor("crowd", 3.4, facing="left")], city_props(20, interior=True), [line("lan_shu", "你守在这里，说明墨行走的路没错。"), line("ye_huang", "你们走得再对，也只会走到死门。"), line("crowd", "苏统领，后面的人快压上来了！"), line("lan_shu", "那就把这条门槛打穿，谁也别想越过我。")], extra_beats=duel_beats("lan_shu", "ye_huang", left_x=-2.0, right_x=2.0, heavy=False), effects=[effect("激光剑对战", start_ms=3600, end_ms=10400, alpha=0.15, playback_speed=0.95)], audio=story_audio(metal=True, boom=True)),
    SceneSpec("scene-022", "room-day", "旧廊尽头终于看见主柱锁心，墨行和老真人一同抬手，以真气反顶血锁。", [front_actor("mo_xing", -2.0, facing="right"), front_actor("old_master", 0.8, facing="left"), back_actor("crowd", 3.0, facing="left")], city_props(21, interior=True), [line("mo_xing", "锁心就在这，若这一下顶不住，我们前面所有命都白搭。"), line("old_master", "别怕反噬，老夫替你吃第一口，你只管把锁心转开。"), line("crowd", "柱子在响，像是在往回吸血！"), line("mo_xing", "吸就让它吸，先把这层血门给我撬开。")], effects=[effect("启动大招特效", start_ms=3300, end_ms=5600, alpha=0.16, playback_speed=0.92), effect("龟派气功", start_ms=5900, end_ms=10900, alpha=0.16, playback_speed=0.94)], audio=story_audio(heart=True, boom=True)),
    SceneSpec("scene-023", "street-day", "九天城最狠的一轮火雨砸下，整片中街像被扔进熔炉，守军却还在往前顶。", [front_actor("qin_ye", -2.0, facing="right"), front_actor("crowd", 0.8, facing="left"), back_actor("prince", 3.0, facing="left")], city_props(22, night=False), [line("crowd", "天火又下来了，再这样下去连石路都要炸裂！"), line("qin_ye", "裂就裂，裂了也要往前，别让他们看见一丝回头。"), line("prince", "水符阵已经推到街口，再撑半刻，地宫那边就能完成最后一扣。"), line("qin_ye", "好，半刻也够我杀到夜皇脚下了。")], extra_beats=[beat(5300, 6500, "qin_ye", "straight-punch", x0=-1.8, x1=-1.0, z0=0.0, z1=0.06, facing="right", effect="hit"), beat(7600, 9000, "qin_ye", "combo-punch", x0=-1.0, x1=0.1, z0=0.08, z1=0.04, facing="right", effect="thunder-strike")], effects=[effect("熊熊大火", start_ms=200, end_ms=14500, alpha=0.16, playback_speed=0.90), effect("火烧赤壁", start_ms=2600, end_ms=11400, alpha=0.16, playback_speed=0.92), effect("爆炸特效", start_ms=10800, end_ms=12800, alpha=0.18, playback_speed=0.92)], audio=story_audio(boom=True, inferno=True, crowd=True)),
    SceneSpec("scene-024", "training-ground", "校场上空和地面同时崩开，秦夜终于看到夜皇本体藏身的黑影。", [front_actor("qin_ye", -2.1, facing="right"), front_actor("ye_huang", 2.0, facing="left"), back_actor("crowd", 3.5, facing="left")], city_props(23, ritual=True), [line("qin_ye", "终于看见你了，原来你一直把自己躲在光后面。"), line("ye_huang", "看见也没用，你到不了我脚下。"), line("crowd", "统领，桥头的人已经压到这边来了！"), line("qin_ye", "来得正好，今晚所有人都看着你从天上掉下来。")], extra_beats=duel_beats("qin_ye", "ye_huang", left_x=-2.0, right_x=1.9, airborne=True, heavy=True), effects=[effect("死亡光线特效", start_ms=6300, end_ms=9800, alpha=0.18, playback_speed=0.96), effect("命中特效", start_ms=10300, end_ms=11800, alpha=0.18, playback_speed=0.92)], audio=story_audio(metal=True, boom=True, heart=True)),
    SceneSpec("scene-025", "park-evening", "岚书携最后一节锁环升空，把它送向天门阴影，准备替秦夜打开终局窗口。", [front_actor("lan_shu", -2.1, facing="right"), front_actor("mo_xing", 0.2, facing="left"), back_actor("crowd", 3.2, facing="left")], city_props(24, night=True), [line("lan_shu", "锁环在我手里，秦夜只要看见光断，就知道该往哪一刀落。"), line("mo_xing", "别丢，这一环一旦偏了，主柱和天门都锁不住。"), line("crowd", "上方还有黑翼追着你，他们已经贴近了！"), line("lan_shu", "那就让他们再近一点，我正好一起带过去。")], extra_beats=flight_combo("lan_shu", start_x=-2.0, facing="right"), effects=[effect("御剑飞行", start_ms=200, end_ms=11400, alpha=0.18, playback_speed=0.95), effect("风起云涌", start_ms=11200, end_ms=13800, alpha=0.16, playback_speed=0.92)], audio=story_audio(metal=True, boom=True), camera=scene_camera(24, battle=True, aerial=True)),
    SceneSpec("scene-026", "mountain-cliff", "天门阴影被锁环咬住，黑环开始颤动，夜皇终于失去最稳的落脚点。", [front_actor("qin_ye", -1.8, facing="right"), front_actor("ye_huang", 2.0, facing="left"), back_actor("lan_shu", 3.4, facing="left")], city_props(25, night=True), [line("lan_shu", "锁环咬住了，黑影在抖，秦夜就是现在！"), line("ye_huang", "你们以为晃一下就能把我扯下来？"), line("qin_ye", "晃一下就够了，我只要你失手这一瞬。"), line("ye_huang", "那你就来，看你这一瞬能换到什么。")], extra_beats=[beat(3600, 4900, "qin_ye", "flying-kick", x0=-1.7, x1=-0.8, z0=0.02, z1=0.22, facing="right", effect="thunder-strike"), beat(5200, 6600, "qin_ye", "hook-punch", x0=-0.9, x1=-0.1, z0=0.18, z1=0.10, facing="right", effect="hit"), beat(7600, 9200, "qin_ye", "double-palm-push", x0=0.0, x1=1.0, z0=0.06, z1=0.12, facing="right", effect="dragon-palm")], effects=[effect("黑洞旋转", start_ms=200, end_ms=6200, alpha=0.18, playback_speed=0.88), effect("御剑飞行", start_ms=2400, end_ms=10200, alpha=0.14, playback_speed=0.95)], audio=story_audio(metal=True, boom=True), camera=scene_camera(25, battle=True, aerial=True)),
    SceneSpec("scene-027", "theatre-stage", "夜皇被逼到旧戏台前，秦夜用连招一路追进去，把他从幻幕里硬轰出来。", [front_actor("qin_ye", -1.9, facing="right"), front_actor("ye_huang", 1.9, facing="left"), back_actor("crowd", 3.2, facing="left")], city_props(26, ritual=True), [line("qin_ye", "你不是爱躲戏幕和影子么，我就连幕一起撕。"), line("ye_huang", "你越往里追，只会越深地落进我的场。"), line("crowd", "统领，台上的影子在塌，他真的被打出来了！"), line("qin_ye", "好，那就别让他再回去。")], extra_beats=[beat(3300, 4600, "qin_ye", "straight-punch", x0=-1.8, x1=-1.0, z0=0.0, z1=0.08, facing="right", effect="hit"), beat(4700, 6000, "qin_ye", "hook-punch", x0=-1.0, x1=-0.2, z0=0.08, z1=0.12, facing="right", effect="dragon-palm"), beat(6100, 7400, "qin_ye", "swing-punch", x0=-0.2, x1=0.7, z0=0.12, z1=0.08, facing="right", effect="sword-arc"), beat(7700, 9200, "qin_ye", "combo-punch", x0=0.6, x1=1.4, z0=0.08, z1=0.02, facing="right", effect="thunder-strike")], effects=[effect("激光剑对战", start_ms=3600, end_ms=9800, alpha=0.15, playback_speed=0.95), effect("命中特效", start_ms=9800, end_ms=11500, alpha=0.18, playback_speed=0.92)], audio=story_audio(metal=True, boom=True)),
    SceneSpec("scene-028", "mountain-cliff", "终局决战在天门外彻底爆开，秦夜与夜皇一招接一招，直到整道黑环被震裂。", [front_actor("qin_ye", -1.8, facing="right"), front_actor("ye_huang", 2.0, facing="left"), back_actor("lan_shu", 3.5, facing="left")], city_props(27, night=True), [line("ye_huang", "你就算赢这一场，也赢不了天外那一整片夜。"), line("qin_ye", "我不管天外有多大，我先把压在城上的这一片砍掉。"), line("lan_shu", "秦夜，锁心已经闭合，主柱那边稳住了！"), line("qin_ye", "那就够了，今夜最后这一刀，轮到我来收。")], extra_beats=[beat(3300, 4600, "qin_ye", "straight-punch", x0=-1.7, x1=-0.8, z0=0.0, z1=0.10, facing="right", effect="hit"), beat(4700, 6000, "qin_ye", "hook-punch", x0=-0.9, x1=-0.1, z0=0.08, z1=0.14, facing="right", effect="dragon-palm"), beat(6100, 7400, "qin_ye", "swing-punch", x0=-0.1, x1=0.8, z0=0.12, z1=0.10, facing="right", effect="sword-arc"), beat(7700, 9200, "qin_ye", "combo-punch", x0=0.7, x1=1.5, z0=0.10, z1=0.02, facing="right", effect="thunder-strike"), beat(9800, 11200, "ye_huang", "diagonal-kick", x0=2.0, x1=1.1, z0=0.12, z1=0.0, facing="left", effect="死亡光线特效"), beat(11400, 12800, "qin_ye", "double-palm-push", x0=1.0, x1=1.9, z0=0.0, z1=0.06, facing="right", effect="dragon-palm")], effects=[effect("黑洞旋转", start_ms=200, end_ms=5600, alpha=0.18, playback_speed=0.88), effect("龟派气功", start_ms=5600, end_ms=9200, alpha=0.16, playback_speed=0.94), effect("死亡光线特效", start_ms=9400, end_ms=11100, alpha=0.18, playback_speed=0.96), effect("爆炸特效", start_ms=11600, end_ms=13900, alpha=0.18, playback_speed=0.92)], audio=story_audio(metal=True, boom=True, heart=True), camera=scene_camera(28, battle=True, aerial=True)),
    SceneSpec("scene-029", "temple-courtyard", "黑环碎散，守军和百姓从地窖、街巷和城墙上走出来，整座城第一次真正松气。", [front_actor("prince", -2.2, facing="right"), front_actor("lan_shu", 0.4, facing="left"), back_actor("crowd", 3.4, facing="left")], city_props(28, ritual=True), [line("crowd", "天亮了，真的天亮了，城顶那圈黑影全散了！"), line("prince", "先别欢呼，把受伤的人抬出来，把火和塌墙都清开。"), line("lan_shu", "秦夜还没回来，但他那一刀已经替整座城回来了。"), line("prince", "好，留一队接他，其余人全去救人。")], effects=[effect("风起云涌", start_ms=500, end_ms=2300, alpha=0.14, playback_speed=0.92), effect("绚烂的烟花", start_ms=10800, end_ms=14000, alpha=0.14, playback_speed=0.96)], audio=story_audio(crowd=True)),
    SceneSpec("scene-030", "mountain-cliff", "破晓照上崖顶，秦夜和众人望着重归平静的九天城，知道这一夜终于过去。", [front_actor("lan_shu", -2.2, facing="right", scale=0.94), front_actor("qin_ye", 0.3, facing="left"), back_actor("prince", 2.7, facing="left"), back_actor("crowd", 3.7, facing="left")], city_props(29, night=False), [line("lan_shu", "风终于顺了，昨夜听上去像要裂开的天，现在也只剩一点余响。"), line("qin_ye", "裂过一次也好，至少城里的人知道，命不是跪着求来的。"), line("prince", "九天城还残着，但它已经守住了自己最难的这一夜。"), line("qin_ye", "回去吧，把活着的人都带回灯下，天亮以后还有新的城要修。")], effects=[effect("风起云涌", start_ms=200, end_ms=2000, alpha=0.12, playback_speed=0.92)], audio=story_audio()),
]


class NineHeavensSiegeVideo(BaseVideoScript):
    def get_title(self) -> str:
        return "九天围城"

    def get_theme(self) -> str:
        return "玄幻守城、三线作战、空战地宫、终局围杀、长篇热血"

    def get_cast(self) -> list[dict]:
        return CAST

    def get_video_options(self) -> dict:
        return VIDEO

    def has_tts(self) -> bool:
        return True

    def get_notes(self) -> dict:
        return {
            "scene_count": len(SCENE_SPECS),
            "format": "nine-heavens-siege",
            "bgm_assets": [OMEN_BGM, MARCH_BGM, WAR_BGM, CRISIS_BGM, FINAL_BGM, DAWN_BGM],
            "featured_effects": [
                "黑洞旋转",
                "御剑飞行",
                "死亡光线特效",
                "激光剑对战",
                "龟派气功",
                "千军万马冲杀",
                "熊熊大火",
                "火烧赤壁",
                "飞踢",
                "骑兵冲杀",
            ],
        }

    def get_default_output(self) -> str:
        return "outputs/nine_heavens_siege.mp4"

    def get_description(self) -> str:
        return "Render a 30-scene fantasy siege with coherent story beats, varied materials, rich combat, story-driven BGM, effects, sound design, and TTS."

    def get_scenes(self) -> list[dict]:
        scenes: list[dict] = []
        for scene_index, spec in enumerate(SCENE_SPECS):
            dialogue_items, talk_beats, expressions_track = build_dialogue_bundle(spec.lines)
            talk_beats = trim_talk_beats_for_actions(talk_beats, spec.extra_beats)
            beats = sorted([*talk_beats, *spec.extra_beats], key=lambda item: (item["start_ms"], item["actor_id"]))
            expressions_sorted = sorted(expressions_track, key=lambda item: (item["start_ms"], item["actor_id"]))
            battle = bool(spec.extra_beats or spec.effects)
            aerial = any((item.get("type") in {"御剑飞行", "黑洞旋转", "死亡光线特效"}) for item in spec.effects)
            audio_payload = scene_audio(bgm=scene_bgm(scene_index), sfx=list(spec.audio.get("sfx", [])))
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


SCRIPT = NineHeavensSiegeVideo()


def build_story() -> dict:
    return SCRIPT.build_story()


def main() -> int:
    return SCRIPT()


if __name__ == "__main__":
    raise SystemExit(main())
