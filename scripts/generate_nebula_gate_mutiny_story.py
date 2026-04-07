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
        "effect_overlay_alpha": 0.90,
    },
}

CAST = [
    cast_member("luo_han", "罗汉", "general-guard"),
    cast_member("ye_lan", "叶岚", "office-worker-modern"),
    cast_member("mo_jin", "墨烬", "detective-sleek"),
    cast_member("chief_qiao", "乔执政", "official-minister"),
    cast_member("marshal_kuang", "匡元帅", "emperor-ming"),
    cast_member("doctor_xu", "许博士", "farmer-old"),
    cast_member("crowd", "舰城人群", "npc-boy"),
]

SCENE_DURATION_MS = 14_800
DIALOGUE_WINDOWS = [
    (400, 3000),
    (3600, 6300),
    (7400, 10300),
    (11100, 13900),
]

FLOOR_BY_BACKGROUND = {
    "archive-library": "wood-plank",
    "bank-lobby": "wood-plank",
    "cafe-night": "wood-plank",
    "museum-gallery": "wood-plank",
    "night-bridge": "dark-stage",
    "park-evening": "dark-stage",
    "room-day": "wood-plank",
    "沙漠星夜": "dark-stage",
    "school-yard": "stone-court",
    "street-day": "stone-court",
    "theatre-stage": "dark-stage",
    "town-hall-records": "wood-plank",
    "training-ground": "stone-court",
}

FIST_AUDIO = "assets/audio/031_26_赤手空拳打斗的声音_爱给网_aigei_com.mp3"
METAL_AUDIO = "assets/audio/刀剑、金属碰撞（带回音）_爱给网_aigei_com.mp3"
BOOM_AUDIO = "assets/audio/音效 爆炸 爆破 爆发 战斗_爱给网_aigei_com.mp3"
THUNDER_AUDIO = "assets/audio/打雷闪电.wav"
HEART_AUDIO = "assets/audio/心脏怦怦跳.wav"

SUSPENSE_BGM = "assets/bgm/误入迷失森林-少年包青天.mp3"
INVESTIGATION_BGM = "assets/bgm/倩女幽魂-张国荣.mp3"
ASCENT_BGM = "assets/bgm/御剑飞行.mp3"
WAR_BGM = "assets/bgm/杀破狼.mp3"
CRISIS_BGM = "assets/bgm/观音降临-高潮版.mp3"
FINAL_BGM = "assets/bgm/最后之战-热血-卢冠廷.mp3"
AFTERMATH_BGM = "assets/bgm/仙剑情缘.mp3"

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
    if any(token in text for token in ("杀", "炸", "毁", "断", "封", "抢", "滚", "开火", "死", "砸", "打")):
        return "angry"
    if any(token in text for token in ("快", "立刻", "马上", "冲", "升空", "撤", "压")):
        return "excited"
    if any(token in text for token in ("坐标", "密钥", "星门", "轨道", "阵列", "信标", "核心", "黑匣")):
        return "thinking"
    if any(token in text for token in ("活下来", "守住", "回来", "亮了")):
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
        return camera_pan(x=-0.28, z=0.06, zoom=1.12, to_x=0.24, to_z=0.0, to_zoom=1.22, ease="ease-in-out")
    if battle:
        return camera_pan(x=-0.24 + 0.04 * (scene_index % 3), z=0.04, zoom=1.07, to_x=0.18, to_z=0.01, to_zoom=1.16, ease="ease-in-out")
    if scene_index in {0, 9, 20}:
        return camera_static(x=0.0, z=0.03, zoom=1.08)
    return camera_pan(x=-0.16, z=0.02, zoom=1.0, to_x=0.12, to_z=0.0, to_zoom=1.06, ease="ease-in-out")


def sci_props(scene_index: int, *, command: bool = False, bridge: bool = False, desert: bool = False, launch: bool = False) -> list[dict]:
    if command:
        return [
            prop("wall-window", -3.8, -1.0, scale=0.92, layer="back"),
            prop("wall-door", 3.8, -1.02, scale=0.92, layer="back"),
            prop("star", -2.9, -0.58, scale=0.54, layer="back"),
            prop("moon", 2.8, -0.44, scale=0.62, layer="back"),
        ]
    if bridge:
        return [
            prop("moon", 3.8, -0.42, scale=0.76, layer="back"),
            prop("star", -3.8, -0.56, scale=0.56, layer="back"),
            prop("airplane", 0.0, -0.92, scale=0.84, layer="mid"),
        ]
    if desert:
        return [
            prop("airplane", -0.4, -0.94, scale=0.90, layer="mid"),
            prop("star", -3.6, -0.58, scale=0.52, layer="back"),
            prop("moon", 3.6, -0.42, scale=0.68, layer="back"),
        ]
    if launch:
        return [
            prop("airplane", 0.0, -0.98, scale=0.96, layer="mid"),
            prop("training-drum", -3.2, -1.02, scale=0.86, layer="back"),
            prop("weapon-rack", 3.3, -1.0, scale=0.88, layer="mid"),
        ]
    items = [prop("house", 0.0, -1.08, scale=0.96, layer="back")]
    if scene_index % 2 == 0:
        items.append(prop("wall-door", 3.8, -1.02, scale=0.90, layer="back"))
    return items


def story_audio(*, metal: bool = False, boom: bool = False, thunder: bool = False, heart: bool = False, pressure: bool = False) -> dict:
    sfx = [
        audio_sfx(FIST_AUDIO, start_ms=3900, volume=0.78),
        audio_sfx(FIST_AUDIO, start_ms=7900, volume=0.80),
    ]
    if metal:
        sfx.append(audio_sfx(METAL_AUDIO, start_ms=5600, volume=0.72))
        sfx.append(audio_sfx(METAL_AUDIO, start_ms=10100, volume=0.70))
    if boom:
        sfx.append(audio_sfx(BOOM_AUDIO, start_ms=6800, volume=0.72))
        sfx.append(audio_sfx(BOOM_AUDIO, start_ms=11100, volume=0.68))
    if thunder:
        sfx.append(audio_sfx(THUNDER_AUDIO, start_ms=2400, volume=0.76))
        sfx.append(audio_sfx(THUNDER_AUDIO, start_ms=9600, volume=0.70))
    if heart:
        sfx.append(audio_sfx(HEART_AUDIO, start_ms=2300, volume=0.64))
    if pressure:
        sfx.append(audio_sfx(BOOM_AUDIO, start_ms=3200, volume=0.46))
    return scene_audio(sfx=sfx)


def scene_bgm(scene_index: int, *, battle: bool, endgame: bool = False) -> dict:
    if scene_index <= 2:
        path, volume = SUSPENSE_BGM, 0.50
    elif scene_index <= 5:
        path, volume = INVESTIGATION_BGM, 0.48
    elif scene_index <= 8:
        path, volume = ASCENT_BGM, 0.56
    elif scene_index <= 14:
        path, volume = WAR_BGM, 0.64
    elif endgame:
        path, volume = FINAL_BGM, 0.68
    elif scene_index <= 18:
        path, volume = CRISIS_BGM, 0.62
    else:
        path, volume = AFTERMATH_BGM, 0.50
    if battle and path == INVESTIGATION_BGM:
        path, volume = WAR_BGM, 0.62
    return audio_bgm(path, volume=volume, loop=True)


def default_foregrounds(scene_index: int, background: str) -> list[dict]:
    if background in {"bank-lobby", "museum-gallery", "archive-library", "room-day", "town-hall-records"}:
        fg_id = "开着门的室内" if scene_index % 2 == 0 else "古典木门木窗-有点日式风格"
        return [foreground(fg_id, x=-0.01, y=-0.02, width=1.02, height=1.06, opacity=1.0)]
    if background in {"night-bridge", "park-evening", "street-day", "沙漠星夜", "training-ground", "school-yard"}:
        return [foreground("中式古典大门", x=-0.01, y=-0.02, width=1.02, height=1.06, opacity=1.0)]
    if background == "theatre-stage":
        return [foreground("敞开的红色帘子-窗帘或床帘皆可", x=-0.02, y=-0.04, width=1.04, height=1.10, opacity=1.0)]
    return []


def corridor_duel(left_id: str, right_id: str, *, left_x: float, right_x: float, heavy: bool = False) -> list[dict]:
    return [
        beat(3400, 4700, left_id, "straight-punch", x0=left_x, x1=left_x + 0.55, z0=0.0, z1=0.08, facing="right", effect="直拳特效" if heavy else "hit"),
        beat(5000, 6300, right_id, "hook-punch", x0=right_x, x1=right_x - 0.45, z0=0.04, z1=0.12, facing="left", effect="hit"),
        beat(7000, 8400, left_id, "combo-punch" if heavy else "swing-punch", x0=left_x + 0.32, x1=left_x + 1.05, z0=0.10, z1=0.02, facing="right", effect="dragon-palm" if heavy else "hit"),
        beat(9000, 10400, right_id, "spin-kick", x0=right_x - 0.14, x1=right_x - 0.80, z0=0.10, z1=0.0, facing="left", effect="thunder-strike"),
        beat(10900, 12400, left_id, "double-palm-push", x0=left_x + 0.82, x1=left_x + 1.48, z0=0.02, z1=0.06, facing="right", effect="sword-arc"),
    ]


def air_combo(actor_id: str, *, start_x: float, facing: str) -> list[dict]:
    direction = 1.0 if facing == "right" else -1.0
    return [
        beat(3400, 4800, actor_id, "flying-kick", x0=start_x, x1=start_x + 0.90 * direction, z0=0.02, z1=0.24, facing=facing, effect="thunder-strike"),
        beat(5200, 6700, actor_id, "spin-kick", x0=start_x + 0.84 * direction, x1=start_x + 1.35 * direction, z0=0.22, z1=0.10, facing=facing, effect="hit"),
        beat(7600, 9300, actor_id, "double-palm-push", x0=start_x + 1.20 * direction, x1=start_x + 1.85 * direction, z0=0.08, z1=0.14, facing=facing, effect="死亡光线特效"),
    ]


SCENE_SPECS = [
    SceneSpec(
        "scene-001",
        "night-bridge",
        "轨道舰城“苍穹九号”的外环天桥正在检修，罗汉却在星夜里看见一束不该亮起的门脉红光。",
        [front_actor("luo_han", -2.2, facing="right"), front_actor("ye_lan", 0.5, facing="left"), back_actor("crowd", 3.4, facing="left")],
        sci_props(0, bridge=True),
        [
            line("luo_han", "检修灯不是这个颜色，这一条红光是有人在私启星门。"),
            line("ye_lan", "我刚从中控下来，今晚根本没有启门排程，谁在拿整座舰城试火。"),
            line("crowd", "外环温度在升，桥骨开始发颤，再拖就要整段断开了。"),
            line("luo_han", "别喊了，先切断联桥，把偷开门的人堵在里面。"),
        ],
        effects=[effect("电闪雷鸣", start_ms=500, end_ms=2600, alpha=0.18, playback_speed=0.94), effect("风起云涌", start_ms=2600, end_ms=7600, alpha=0.16, playback_speed=0.92)],
        audio=story_audio(thunder=True, heart=True),
    ),
    SceneSpec(
        "scene-002",
        "bank-lobby",
        "舰城执政厅玻璃穹顶下，乔执政强行压住消息，想把这次异常当成一次普通系统抖动。",
        [front_actor("chief_qiao", -2.2, facing="right"), front_actor("ye_lan", 0.3, facing="left"), front_actor("luo_han", 2.8, facing="left", scale=0.94)],
        sci_props(1, command=True),
        [
            line("chief_qiao", "谁都不许对外说星门失控，今晚要是先乱的是人心，苍穹九号就算还在飞也是一具空壳。"),
            line("ye_lan", "这不是抖动，是有人用军用密钥改写了门脉权限，再压消息等于陪他把门彻底拉开。"),
            line("luo_han", "我只问一句，调钥匙的人是不是还在城里。"),
            line("chief_qiao", "在，甚至可能就站在你我上面那层楼里。"),
        ],
        audio=story_audio(pressure=True),
    ),
    SceneSpec(
        "scene-003",
        "archive-library",
        "墨烬在旧档案层翻出被删掉的黑匣日志，发现匡元帅早在三个月前就做过一次禁门试验。",
        [front_actor("mo_jin", -2.2, facing="right"), front_actor("doctor_xu", 0.6, facing="left"), back_actor("ye_lan", 3.1, facing="left")],
        sci_props(2, command=True),
        [
            line("mo_jin", "黑匣日志被清过，但删得太急，时间戳还挂在这儿，匡元帅三个月前就碰过禁门。"),
            line("doctor_xu", "我就知道他不会甘心只守轨道，他一直想把苍穹九号变成一把能插进月轨的刀。"),
            line("ye_lan", "所以今晚不是事故，是他终于决定下手。"),
            line("mo_jin", "对，而且他要的不是通行权，他要的是把整座舰城一起拖进门里。"),
        ],
        effects=[effect("黑洞旋转", start_ms=4100, end_ms=7800, alpha=0.16, playback_speed=0.90)],
        audio=story_audio(heart=True),
    ),
    SceneSpec(
        "scene-004",
        "museum-gallery",
        "匡元帅在舰城纪念廊公开露面，语气平静得像在报时，却字字都在逼人站队。",
        [front_actor("marshal_kuang", -2.2, facing="right"), front_actor("chief_qiao", 0.4, facing="left"), back_actor("crowd", 3.2, facing="left")],
        sci_props(3, command=True),
        [
            line("marshal_kuang", "门已经开了一半，今天谁要拦我，不是在拦一场实验，是在拦苍穹九号下一百年的出路。"),
            line("chief_qiao", "你拿整座城做筹码，也配叫出路。"),
            line("crowd", "元帅，外环都在抖，底层舱室已经有人被震伤了。"),
            line("marshal_kuang", "伤几百个，总好过再当几代人的笼中虫。"),
        ],
        effects=[effect("奥特曼出场", start_ms=900, end_ms=3200, alpha=0.16, playback_speed=0.96)],
        audio=story_audio(pressure=True),
    ),
    SceneSpec(
        "scene-005",
        "cafe-night",
        "罗汉和叶岚在停业咖啡站短促碰头，决定一边抢回中控，一边去沙海信标站拔掉外部引导。",
        [front_actor("luo_han", -2.1, facing="right"), front_actor("ye_lan", 2.0, facing="left"), back_actor("mo_jin", 0.2, facing="left", scale=0.90)],
        sci_props(4),
        [
            line("luo_han", "你回中控抢权限，我去外面砍信标，不然门会一直朝错误坐标涨。"),
            line("ye_lan", "你一个人去沙海就是送命，匡元帅肯定把最硬的火力压在那边。"),
            line("mo_jin", "我跟他去，外头的假坐标是我先看出来的，我得把它亲手抹掉。"),
            line("luo_han", "好，内外两线一起走，谁先打穿，谁就回头接另一边。"),
        ],
        audio=story_audio(),
    ),
    SceneSpec(
        "scene-006",
        "training-ground",
        "机库战备区被强行征用成临时发射场，乔执政终于撕掉斯文，命罗汉立刻抢船出城。",
        [front_actor("chief_qiao", -2.1, facing="right"), front_actor("luo_han", 0.5, facing="left"), front_actor("ye_lan", 2.8, facing="left", scale=0.94)],
        sci_props(5, launch=True),
        [
            line("chief_qiao", "我不跟他讲道理了，你现在就带船出去，把沙海信标给我掀了。"),
            line("luo_han", "给我一条能冲出外环的航道，剩下的我自己拿拳头和火去开。"),
            line("ye_lan", "中控那边我来顶，哪怕权限一层一层掉，我也会给你把发射窗撑住。"),
            line("chief_qiao", "去吧，今夜要是输，苍穹九号以后就只剩一座坟的名字。"),
        ],
        effects=[effect("启动大招特效", start_ms=10600, end_ms=13200, alpha=0.18, playback_speed=0.92)],
        audio=story_audio(boom=True),
    ),
    SceneSpec(
        "scene-007",
        "沙漠星夜",
        "罗汉和墨烬抵达荒漠信标站，头顶的门脉像一只正在合上的红色眼睛，把沙海照得惨亮。",
        [front_actor("luo_han", -2.2, facing="right"), front_actor("mo_jin", 0.4, facing="left"), back_actor("crowd", 3.3, facing="left")],
        sci_props(6, desert=True),
        [
            line("mo_jin", "看上面，那不是天，是门脉在往下压，信标再不拔，整片沙海都会被卷进去。"),
            line("luo_han", "前面那座塔就是喂门的嘴，今天它吃进去多少能量，我就从它身上打回来多少。"),
            line("crowd", "外围炮塔已经亮了，前面不是一座信标，是一整圈守门机甲。"),
            line("luo_han", "那就把机甲先打烂，别让它们有第二轮开火的机会。"),
        ],
        effects=[effect("死亡光线特效", start_ms=3000, end_ms=8200, alpha=0.16, playback_speed=0.96), effect("风起云涌", start_ms=8400, end_ms=13800, alpha=0.16, playback_speed=0.92)],
        audio=story_audio(boom=True, thunder=True),
    ),
    SceneSpec(
        "scene-008",
        "沙漠星夜",
        "第一波守门机甲压上来，罗汉顶着正面火线直冲，墨烬在侧翼抢黑匣控制杆。",
        [front_actor("luo_han", -2.1, facing="right"), front_actor("mo_jin", 0.2, facing="left"), back_actor("marshal_kuang", 3.2, facing="left")],
        sci_props(7, desert=True),
        [
            line("marshal_kuang", "我就知道你会来，可你来晚了，信标已经和门脉锁死。"),
            line("luo_han", "锁死也能砸开，你别把机械当神。"),
            line("mo_jin", "控制杆在塔腹，我只要进去十秒，你就能看见这玩意自己熄火。"),
            line("marshal_kuang", "十秒？我连你们三秒都不想给。"),
        ],
        extra_beats=corridor_duel("luo_han", "marshal_kuang", left_x=-2.0, right_x=3.0, heavy=True),
        effects=[effect("激光剑对战", start_ms=3600, end_ms=10400, alpha=0.16, playback_speed=0.95), effect("爆炸特效", start_ms=10800, end_ms=12600, alpha=0.18, playback_speed=0.92)],
        audio=story_audio(metal=True, boom=True, thunder=True),
    ),
    SceneSpec(
        "scene-009",
        "bank-lobby",
        "与此同时，叶岚闯进中控主塔，发现整层权限早被改写成一条只认匡元帅的死命令。",
        [front_actor("ye_lan", -2.1, facing="right"), front_actor("chief_qiao", 0.3, facing="left"), back_actor("crowd", 3.2, facing="left")],
        sci_props(8, command=True),
        [
            line("ye_lan", "权限树全被换了，门控、能源、炮阵，全都只听匡元帅一个声纹。"),
            line("chief_qiao", "那就把声纹库整个烧掉，我宁可系统盲十分钟，也不能让他继续拿全城当刀把。"),
            line("crowd", "主塔下面有人往上冲，他们不是来守塔，是来断你们的手。"),
            line("ye_lan", "让他们上来，我正缺一扇能狠狠干上的门。"),
        ],
        effects=[effect("启动大招特效", start_ms=7900, end_ms=10300, alpha=0.16, playback_speed=0.92)],
        audio=story_audio(heart=True, pressure=True),
    ),
    SceneSpec(
        "scene-010",
        "town-hall-records",
        "叶岚从旧系统里翻出一段隐藏后门，发现匡元帅真正想打开的不是通道，而是月轨武库。",
        [front_actor("ye_lan", -2.2, facing="right"), front_actor("doctor_xu", 0.6, facing="left"), back_actor("chief_qiao", 3.0, facing="left")],
        sci_props(9, command=True),
        [
            line("ye_lan", "找到了，他不是想穿门，他是想把门对准月轨武库，把那一整层旧武备拖进来。"),
            line("doctor_xu", "疯子，他一旦成功，苍穹九号会直接变成一根点着的枪管。"),
            line("chief_qiao", "把这个坐标送出去，告诉罗汉，外面那座信标必须立刻塌。"),
            line("ye_lan", "我送，而且我要把这条后门反着插回去，让匡元帅自己吃回路。"),
        ],
        effects=[effect("黑洞旋转", start_ms=4200, end_ms=7600, alpha=0.14, playback_speed=0.90)],
        audio=story_audio(heart=True),
    ),
    SceneSpec(
        "scene-011",
        "night-bridge",
        "外环二次震荡爆发，桥面上挤满逃离下层的人，乔执政顶着骂声也要把人流往内区扯。",
        [front_actor("chief_qiao", -2.2, facing="right"), front_actor("crowd", 0.4, facing="left"), back_actor("ye_lan", 3.0, facing="left")],
        sci_props(10, bridge=True),
        [
            line("crowd", "你们不是说没事吗，现在连桥都在掉火花，我们往哪儿逃。"),
            line("chief_qiao", "往我后面退，别往下看，下面已经不是路，是要把人活吞进去的门风。"),
            line("ye_lan", "再给我七分钟，我把主塔权限砸开，你们就能看到那条红光往回缩。"),
            line("chief_qiao", "七分钟太久也得撑，谁今天敢踩着别人逃，我先亲手把他按回桥上。"),
        ],
        effects=[effect("电闪雷鸣", start_ms=1000, end_ms=3900, alpha=0.18, playback_speed=0.94), effect("死亡光线特效", start_ms=8800, end_ms=11600, alpha=0.14, playback_speed=0.96)],
        audio=story_audio(thunder=True, pressure=True),
    ),
    SceneSpec(
        "scene-012",
        "沙漠星夜",
        "墨烬钻进信标塔腹，靠近黑匣的一瞬间才发现匡元帅早把塔芯改成了会自爆的诱饵。",
        [front_actor("mo_jin", -2.1, facing="right"), front_actor("luo_han", 0.6, facing="left"), back_actor("marshal_kuang", 3.0, facing="left")],
        sci_props(11, desert=True),
        [
            line("mo_jin", "黑匣是假的，塔芯下面埋的是反冲炸药，他想连塔带人一起扬了。"),
            line("luo_han", "那就别拆箱，直接连底座一起拔。"),
            line("marshal_kuang", "你们终于看明白了，可看明白也来不及，倒计时已经起了。"),
            line("mo_jin", "来不及也得来，今天我要让你的每一步算计全变成回火。"),
        ],
        extra_beats=[beat(3600, 5000, "luo_han", "flying-kick", x0=-1.9, x1=-0.9, z0=0.02, z1=0.24, facing="right", effect="飞踢"), beat(5600, 7200, "luo_han", "straight-punch", x0=-0.8, x1=0.0, z0=0.16, z1=0.02, facing="right", effect="直拳特效"), beat(8400, 10200, "mo_jin", "double-palm-push", x0=0.1, x1=1.0, z0=0.02, z1=0.08, facing="right", effect="龟派气功")],
        effects=[effect("飞踢", start_ms=3400, end_ms=5200, alpha=0.18, playback_speed=0.94), effect("龟派气功", start_ms=8200, end_ms=11200, alpha=0.16, playback_speed=0.94), effect("爆炸特效", start_ms=11400, end_ms=13000, alpha=0.18, playback_speed=0.92)],
        audio=story_audio(boom=True, thunder=True, metal=True),
    ),
    SceneSpec(
        "scene-013",
        "theatre-stage",
        "主塔权限争夺演变成近身厮打，叶岚在半层高的维护台上和叛军指挥官狠狠干到贴脸。",
        [front_actor("ye_lan", -2.1, facing="right"), front_actor("marshal_kuang", 2.0, facing="left"), back_actor("crowd", 3.2, facing="left")],
        sci_props(12, launch=True),
        [
            line("ye_lan", "我今天不是来跟你们讲流程的，我是来抢回这座塔的脖子。"),
            line("marshal_kuang", "抢？你连站在这儿都靠别人替你流血。"),
            line("crowd", "维护台要塌了，再打两下你们会一起摔到下层机井里。"),
            line("ye_lan", "塌就塌，我先把他脑子里那句死命令打碎。"),
        ],
        extra_beats=corridor_duel("ye_lan", "marshal_kuang", left_x=-2.0, right_x=2.0, heavy=False),
        effects=[effect("激光剑对战", start_ms=3200, end_ms=9600, alpha=0.16, playback_speed=0.95), effect("命中特效", start_ms=9800, end_ms=11600, alpha=0.18, playback_speed=0.92)],
        audio=story_audio(metal=True, boom=True),
    ),
    SceneSpec(
        "scene-014",
        "museum-gallery",
        "乔执政亲自打开旧武备柜，把封存多年的轨道防卫阵图抬出来，准备和匡元帅做最后一轮权限对撞。",
        [front_actor("chief_qiao", -2.1, facing="right"), front_actor("doctor_xu", 0.4, facing="left"), back_actor("ye_lan", 3.0, facing="left")],
        sci_props(13, command=True),
        [
            line("chief_qiao", "我早就说过，防卫阵图不该留给一个把野心装成未来的人。"),
            line("doctor_xu", "现在说这个晚了，阵图一旦升起，要么把门压回去，要么把主塔一起烧穿。"),
            line("ye_lan", "那就烧，我宁可烧塔，也不让那道门继续对着活人张嘴。"),
            line("chief_qiao", "好，权限对撞开始，这一轮我亲自跟他赌。"),
        ],
        effects=[effect("启动大招特效", start_ms=8800, end_ms=11200, alpha=0.16, playback_speed=0.92)],
        audio=story_audio(pressure=True, heart=True),
    ),
    SceneSpec(
        "scene-015",
        "沙漠星夜",
        "信标塔终于开始松动，可头顶黑门却趁势扩大，整片夜空像被撕成一个缓缓下压的洞。",
        [front_actor("luo_han", -2.2, facing="right"), front_actor("mo_jin", 0.4, facing="left"), back_actor("marshal_kuang", 3.1, facing="left")],
        sci_props(14, desert=True),
        [
            line("mo_jin", "塔芯松了，可门在吃回流，它在拿自己的扩张速度跟我们换命。"),
            line("luo_han", "那就别跟它慢慢拽，我现在就把整座塔连根拔翻。"),
            line("marshal_kuang", "你越用力，门就越快看见你们这点可怜的挣扎。"),
            line("luo_han", "让它看，看完以后我正好一拳把它眼珠子砸灭。"),
        ],
        extra_beats=[beat(3600, 5200, "luo_han", "hook-punch", x0=-2.0, x1=-1.2, z0=0.0, z1=0.10, facing="right", effect="hit"), beat(5900, 7600, "luo_han", "swing-punch", x0=-1.1, x1=-0.2, z0=0.10, z1=0.12, facing="right", effect="dragon-palm"), beat(8600, 10300, "luo_han", "double-palm-push", x0=-0.1, x1=1.0, z0=0.08, z1=0.02, facing="right", effect="爆炸特效")],
        effects=[effect("黑洞旋转", start_ms=300, end_ms=13200, alpha=0.18, playback_speed=0.88), effect("死亡光线特效", start_ms=8200, end_ms=11200, alpha=0.16, playback_speed=0.96)],
        audio=story_audio(boom=True, thunder=True, metal=True),
    ),
    SceneSpec(
        "scene-016",
        "night-bridge",
        "权限对撞成功了一半，红光短暂回缩，叶岚立刻在桥上传出狠话，要把匡元帅逼到彻底翻脸。",
        [front_actor("ye_lan", -2.1, facing="right"), front_actor("marshal_kuang", 2.0, facing="left"), back_actor("crowd", 3.2, facing="left")],
        sci_props(15, bridge=True),
        [
            line("ye_lan", "红光缩了，说明你也不是神，你那点权限只要被掀掉一角，门就会先摇。"),
            line("marshal_kuang", "摇一下有什么用，我只要在它彻底关上前，把武库拖进来一次就够。"),
            line("crowd", "他在升压，桥下整段门风又开始拉人了！"),
            line("ye_lan", "那我就继续骂到你失手，今夜你别想体面地下台。"),
        ],
        effects=[effect("死亡光线特效", start_ms=9600, end_ms=12200, alpha=0.16, playback_speed=0.96)],
        audio=story_audio(thunder=True, pressure=True),
    ),
    SceneSpec(
        "scene-017",
        "park-evening",
        "外层飞梭从舰城上空掠过，罗汉借着短暂打开的回传窗直冲返城航道，准备回头斩主门。",
        [front_actor("luo_han", -2.1, facing="right"), front_actor("mo_jin", 0.5, facing="left"), back_actor("crowd", 3.3, facing="left")],
        sci_props(16, bridge=True),
        [
            line("mo_jin", "信标已经歪了，回传窗只开这一小会儿，你现在不走就得和我一起埋在沙里。"),
            line("luo_han", "我回去砍主门，你留在这儿把最后一层假坐标擦干净。"),
            line("crowd", "飞梭就在头顶，门风在拽它，再慢一点整艘都会被卷裂。"),
            line("luo_han", "那就让它贴着风飞，我今天就是踩着这股风回去要人命的。"),
        ],
        extra_beats=air_combo("luo_han", start_x=-2.0, facing="right"),
        effects=[effect("御剑飞行", start_ms=300, end_ms=11000, alpha=0.18, playback_speed=0.95), effect("风起云涌", start_ms=8800, end_ms=13600, alpha=0.16, playback_speed=0.92)],
        audio=story_audio(boom=True, thunder=True),
        camera=scene_camera(16, battle=True, aerial=True),
    ),
    SceneSpec(
        "scene-018",
        "theatre-stage",
        "主塔最顶层彻底失火，叶岚和匡元帅隔着崩裂的维护桥狠狠干到只剩一步之距。",
        [front_actor("ye_lan", -2.0, facing="right"), front_actor("marshal_kuang", 2.0, facing="left"), back_actor("chief_qiao", 3.3, facing="left")],
        sci_props(17, launch=True),
        [
            line("marshal_kuang", "你们这群守成的人，骨子里连赌一场新世界的胆都没有。"),
            line("ye_lan", "新世界不是你拿活人往门里填出来的，它该踩着地，不该踩着尸体。"),
            line("chief_qiao", "叶岚，主桥还能撑最后一轮，把他逼出声纹台。"),
            line("ye_lan", "听见没有，你的台子快没了，你人也一样。"),
        ],
        extra_beats=[beat(3500, 4900, "ye_lan", "straight-punch", x0=-1.9, x1=-1.0, z0=0.0, z1=0.08, facing="right", effect="直拳特效"), beat(5200, 6600, "marshal_kuang", "hook-punch", x0=1.9, x1=1.1, z0=0.06, z1=0.12, facing="left", effect="hit"), beat(7400, 9000, "ye_lan", "combo-punch", x0=-0.8, x1=0.3, z0=0.10, z1=0.06, facing="right", effect="thunder-strike"), beat(9800, 11400, "ye_lan", "double-palm-push", x0=0.2, x1=1.2, z0=0.04, z1=0.10, facing="right", effect="爆炸特效")],
        effects=[effect("熊熊大火", start_ms=200, end_ms=14600, alpha=0.16, playback_speed=0.90), effect("爆炸特效", start_ms=9800, end_ms=11800, alpha=0.18, playback_speed=0.92)],
        audio=story_audio(boom=True, metal=True, thunder=True),
    ),
    SceneSpec(
        "scene-019",
        "night-bridge",
        "罗汉回到舰城主门外侧，整道门脉已经像心脏一样抽搐，他知道这一拳要么封门，要么一起坠毁。",
        [front_actor("luo_han", -2.0, facing="right"), front_actor("ye_lan", 0.5, facing="left"), back_actor("marshal_kuang", 3.1, facing="left")],
        sci_props(18, bridge=True),
        [
            line("ye_lan", "主门脉就在你前面三层，我把门压慢了八秒，这八秒就是全城给你的命。"),
            line("luo_han", "八秒够了，我今天不需要天长地久，我只要这一口够狠。"),
            line("marshal_kuang", "来啊，看看是你的拳硬，还是整座门的坠力硬。"),
            line("luo_han", "我不跟门比，我跟你比，看谁先跪。"),
        ],
        extra_beats=corridor_duel("luo_han", "marshal_kuang", left_x=-1.9, right_x=3.0, heavy=True),
        effects=[effect("黑洞旋转", start_ms=200, end_ms=6400, alpha=0.18, playback_speed=0.88), effect("死亡光线特效", start_ms=6600, end_ms=9800, alpha=0.16, playback_speed=0.96), effect("龟派气功", start_ms=10400, end_ms=13200, alpha=0.16, playback_speed=0.94)],
        audio=story_audio(boom=True, thunder=True, metal=True, heart=True),
        camera=scene_camera(18, battle=True, aerial=True),
    ),
    SceneSpec(
        "scene-020",
        "沙漠星夜",
        "墨烬在沙海亲手切断最后一条假坐标，头顶那只黑洞终于失去喂食，开始往内塌缩。",
        [front_actor("mo_jin", -2.1, facing="right"), front_actor("doctor_xu", 0.4, facing="left"), back_actor("crowd", 3.3, facing="left")],
        sci_props(19, desert=True),
        [
            line("mo_jin", "假坐标清空了，它吃不到外面那层假路了，接下来就看主门那一拳。"),
            line("doctor_xu", "黑洞在缩，说明门脉终于开始往里反咬，你们真把它喂到头了。"),
            line("crowd", "沙海风压在回卷，远处的塔全在倒，天好像终于往上抬了一点。"),
            line("mo_jin", "别高兴太早，只有等城里那道红光彻底灭掉，今夜才算真结束。"),
        ],
        effects=[effect("黑洞旋转", start_ms=200, end_ms=12400, alpha=0.18, playback_speed=0.88), effect("绚烂的烟花", start_ms=11400, end_ms=14000, alpha=0.12, playback_speed=0.96)],
        audio=story_audio(thunder=True, heart=True),
    ),
    SceneSpec(
        "scene-021",
        "night-bridge",
        "最终一击落下，主门脉被罗汉和叶岚前后夹死，匡元帅连同那道猩红门影一起被抛出外环。",
        [front_actor("luo_han", -1.9, facing="right"), front_actor("ye_lan", 0.6, facing="left"), back_actor("marshal_kuang", 3.0, facing="left")],
        sci_props(20, bridge=True),
        [
            line("luo_han", "这一拳给外环，给底层，给刚才差点掉下去的每一个人。"),
            line("ye_lan", "这一掌给主塔，给被你篡掉的每一条权限，也给你这张疯脸。"),
            line("marshal_kuang", "你们挡得住这一夜，挡不住下一次门开！"),
            line("luo_han", "下一次轮不到你开口了。"),
        ],
        extra_beats=[beat(3200, 4600, "luo_han", "straight-punch", x0=-1.8, x1=-0.9, z0=0.0, z1=0.10, facing="right", effect="直拳特效"), beat(4700, 6200, "ye_lan", "double-palm-push", x0=0.5, x1=1.4, z0=0.06, z1=0.10, facing="right", effect="死亡光线特效"), beat(6900, 8600, "luo_han", "combo-punch", x0=-0.8, x1=0.2, z0=0.10, z1=0.04, facing="right", effect="thunder-strike"), beat(9400, 11200, "luo_han", "double-palm-push", x0=0.2, x1=1.5, z0=0.04, z1=0.10, facing="right", effect="爆炸特效")],
        effects=[effect("死亡光线特效", start_ms=3200, end_ms=6200, alpha=0.18, playback_speed=0.96), effect("龟派气功", start_ms=6700, end_ms=9600, alpha=0.16, playback_speed=0.94), effect("爆炸特效", start_ms=9800, end_ms=12600, alpha=0.18, playback_speed=0.92)],
        audio=story_audio(boom=True, thunder=True, metal=True, heart=True),
        camera=scene_camera(20, battle=True, aerial=True),
    ),
    SceneSpec(
        "scene-022",
        "park-evening",
        "红光彻底熄灭后，舰城缓慢回到稳定轨道，人们站在仍发烫的桥面上，终于敢抬头看真正的夜空。",
        [front_actor("ye_lan", -2.2, facing="right"), front_actor("luo_han", 0.2, facing="left"), back_actor("chief_qiao", 2.8, facing="left"), back_actor("crowd", 3.7, facing="left")],
        sci_props(21, bridge=True),
        [
            line("chief_qiao", "主门脉归零，轨道恢复，苍穹九号还在，我们也都还在。"),
            line("ye_lan", "桥还烫，塔还冒烟，但至少头顶那张嘴终于闭上了。"),
            line("luo_han", "闭上就好，剩下的裂缝明天再补，今夜先把活着的人都数回来。"),
            line("crowd", "天真的亮出来了，原来夜空没有那道门的时候，是这么安静。"),
        ],
        effects=[effect("风起云涌", start_ms=400, end_ms=2200, alpha=0.12, playback_speed=0.92), effect("绚烂的烟花", start_ms=10800, end_ms=13800, alpha=0.12, playback_speed=0.96)],
        audio=story_audio(),
    ),
]


class NebulaGateMutinyVideo(BaseVideoScript):
    def get_title(self) -> str:
        return "星门叛变"

    def get_theme(self) -> str:
        return "科幻舰城、星门失控、叛乱夺权、双线作战、黑洞终局"

    def get_cast(self) -> list[dict]:
        return CAST

    def get_video_options(self) -> dict:
        return VIDEO

    def has_tts(self) -> bool:
        return True

    def get_notes(self) -> dict:
        return {
            "scene_count": len(SCENE_SPECS),
            "format": "nebula-gate-mutiny",
            "bgm_assets": [
                SUSPENSE_BGM,
                INVESTIGATION_BGM,
                ASCENT_BGM,
                WAR_BGM,
                CRISIS_BGM,
                FINAL_BGM,
                AFTERMATH_BGM,
            ],
            "featured_effects": [
                "黑洞旋转",
                "死亡光线特效",
                "激光剑对战",
                "御剑飞行",
                "爆炸特效",
                "电闪雷鸣",
                "飞踢",
                "龟派气功",
            ],
        }

    def get_default_output(self) -> str:
        return "outputs/nebula_gate_mutiny.mp4"

    def get_description(self) -> str:
        return "Render a 22-scene sci-fi mutiny story with sharp dialogue, heavy conflict, TTS, story-driven BGM, rich effects, and dense sound design."

    def get_scenes(self) -> list[dict]:
        scenes: list[dict] = []
        for scene_index, spec in enumerate(SCENE_SPECS):
            dialogue_items, talk_beats, expressions_track = build_dialogue_bundle(spec.lines)
            talk_beats = trim_talk_beats_for_actions(talk_beats, spec.extra_beats)
            beats = sorted([*talk_beats, *spec.extra_beats], key=lambda item: (item["start_ms"], item["actor_id"]))
            expressions_sorted = sorted(expressions_track, key=lambda item: (item["start_ms"], item["actor_id"]))
            battle = bool(spec.extra_beats or spec.effects)
            aerial = any(item.get("type") in {"御剑飞行", "黑洞旋转", "死亡光线特效"} for item in spec.effects)
            endgame = scene_index >= 18
            audio_payload = scene_audio(bgm=scene_bgm(scene_index, battle=battle, endgame=endgame), sfx=list(spec.audio.get("sfx", [])))
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


SCRIPT = NebulaGateMutinyVideo()


def build_story() -> dict:
    return SCRIPT.build_story()


def main() -> int:
    return SCRIPT()


if __name__ == "__main__":
    raise SystemExit(main())
