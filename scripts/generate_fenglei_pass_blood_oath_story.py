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
    cast_member("xiao_han", "萧寒", "general-guard"),
    cast_member("ning_shuang", "宁霜", "npc-girl"),
    cast_member("gu_yunzhou", "顾云舟", "detective-sleek"),
    cast_member("old_qin", "秦老卒", "farmer-old"),
    cast_member("xue_cang", "薛藏锋", "official-minister"),
    cast_member("yan_wang", "燕王", "emperor-ming"),
    cast_member("scout", "斥候", "npc-boy"),
    cast_member("narrator", "旁白", "narrator"),
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
    "钱塘江": "dark-stage",
}

FIST_AUDIO = "assets/audio/031_26_赤手空拳打斗的声音_爱给网_aigei_com.mp3"
METAL_AUDIO = "assets/audio/刀剑、金属碰撞（带回音）_爱给网_aigei_com.mp3"
BOOM_AUDIO = "assets/audio/音效 爆炸 爆破 爆发 战斗_爱给网_aigei_com.mp3"
HEART_AUDIO = "assets/audio/心脏怦怦跳.wav"

OMEN_BGM = "assets/bgm/历史的天空-三国演义-毛阿敏.mp3"
MARCH_BGM = "assets/bgm/铁血丹心.mp3"
WAR_BGM = "assets/bgm/男儿当自强.mp3"
CRISIS_BGM = "assets/bgm/杀破狼.mp3"
FINAL_BGM = "assets/bgm/最后之战-热血-卢冠廷.mp3"
DAWN_BGM = "assets/bgm/历史的天空-古筝-三国演义片尾曲.mp3"


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
    if any(token in text for token in ("杀", "斩", "破", "轰", "烧", "退", "阵", "冲", "血", "战")):
        return "angry"
    if any(token in text for token in ("快", "马上", "立刻", "追", "压上", "起火", "别停")):
        return "excited"
    if any(token in text for token in ("图", "局", "门", "计", "退路", "伏兵", "钟楼", "暗门")):
        return "thinking"
    if any(token in text for token in ("稳住", "赢了", "活着", "守住", "天亮")):
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
        return camera_pan(x=-0.32, z=0.06, zoom=1.10, to_x=0.28, to_z=0.02, to_zoom=1.20, ease="ease-in-out")
    if battle:
        return camera_pan(x=-0.26 + 0.05 * (scene_index % 3), z=0.04, zoom=1.08, to_x=0.18, to_z=0.0, to_zoom=1.16, ease="ease-in-out")
    if scene_index in {0, 9, 19}:
        return camera_static(x=0.0, z=0.03, zoom=1.08)
    return camera_pan(x=-0.16, z=0.02, zoom=1.0, to_x=0.12, to_z=0.0, to_zoom=1.06, ease="ease-in-out")


def fortress_props(scene_index: int, *, interior: bool = False, stage: bool = False, night: bool = False) -> list[dict]:
    if stage:
        return [
            prop("training-drum", -3.5, -1.02, scale=0.92, layer="back"),
            prop("weapon-rack", 3.3, -1.0, scale=0.92, layer="mid"),
            prop("lantern", 0.0, -0.92, scale=0.96, layer="front"),
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


def war_audio(*, metal: bool = False, boom: bool = False, heart: bool = False, inferno: bool = False, crowd: bool = False) -> dict:
    sfx = [
        {"asset_path": FIST_AUDIO, "start_ms": 3900, "volume": 0.84, "loop": False},
        {"asset_path": FIST_AUDIO, "start_ms": 7600, "volume": 0.82, "loop": False},
    ]
    if metal:
        sfx.append({"asset_path": METAL_AUDIO, "start_ms": 5600, "volume": 0.78, "loop": False})
        sfx.append({"asset_path": METAL_AUDIO, "start_ms": 9800, "volume": 0.74, "loop": False})
    if boom:
        sfx.append({"asset_path": BOOM_AUDIO, "start_ms": 6700, "volume": 0.72, "loop": False})
        sfx.append({"asset_path": BOOM_AUDIO, "start_ms": 11000, "volume": 0.68, "loop": False})
    if heart:
        sfx.append({"asset_path": HEART_AUDIO, "start_ms": 2200, "volume": 0.62, "loop": False})
    if inferno:
        sfx.append({"asset_path": BOOM_AUDIO, "start_ms": 2600, "volume": 0.56, "loop": False})
    if crowd:
        sfx.append({"asset_path": FIST_AUDIO, "start_ms": 11800, "volume": 0.64, "loop": False})
    return scene_audio(sfx=sfx)


def scene_bgm(scene_index: int) -> dict:
    if scene_index <= 2:
        path, volume = OMEN_BGM, 0.48
    elif scene_index <= 6:
        path, volume = MARCH_BGM, 0.54
    elif scene_index <= 12:
        path, volume = WAR_BGM, 0.62
    elif scene_index <= 16:
        path, volume = CRISIS_BGM, 0.60
    elif scene_index <= 18:
        path, volume = FINAL_BGM, 0.66
    else:
        path, volume = DAWN_BGM, 0.48
    return {"asset_path": path, "start_ms": 0, "volume": volume, "loop": True}


def default_foregrounds(scene_index: int, background: str) -> list[dict]:
    if background in {"temple-courtyard", "theatre-stage"}:
        return [foreground("敞开的红色帘子-窗帘或床帘皆可", asset_path="assets/foreground/敞开的红色帘子-窗帘或床帘皆可.webp", x=-0.02, y=-0.04, width=1.04, height=1.08, opacity=1.0)]
    if background in {"room-day", "archive-library", "town-hall-records", "inn-hall"}:
        fg_id = "开着门的室内" if scene_index % 2 == 0 else "古典木门木窗-有点日式风格"
        fg_path = "assets/foreground/开着门的室内.webp" if fg_id == "开着门的室内" else "assets/foreground/古典木门木窗-有点日式风格.webp"
        return [foreground(fg_id, asset_path=fg_path, x=-0.01, y=-0.02, width=1.02, height=1.06, opacity=1.0)]
    if background in {"night-bridge", "park-evening", "street-day", "training-ground", "mountain-cliff", "钱塘江"}:
        return [foreground("中式古典大门", asset_path="assets/foreground/中式古典大门.webp", x=-0.01, y=-0.02, width=1.02, height=1.06, opacity=1.0)]
    return []


def duel_beats(left_id: str, right_id: str, *, left_x: float, right_x: float, airborne: bool = False, heavy: bool = False) -> list[dict]:
    jump_z = 0.16 if airborne else 0.04
    return [
        beat(3300, 4500, left_id, "straight-punch", x0=left_x, x1=left_x + 0.45, z0=0.0, z1=jump_z, facing="right", effect="直拳特效"),
        beat(4700, 5900, right_id, "hook-punch", x0=right_x, x1=right_x - 0.38, z0=0.0, z1=jump_z, facing="left", effect="命中特效"),
        beat(6400, 7700, left_id, "combo-punch" if heavy else "swing-punch", x0=left_x + 0.22, x1=left_x + 0.80, z0=jump_z, z1=0.02, facing="right", effect="dragon-palm" if heavy else "命中特效"),
        beat(8200, 9400, right_id, "diagonal-kick" if airborne else "spin-kick", x0=right_x - 0.14, x1=right_x - 0.76, z0=jump_z, z1=0.02, facing="left", effect="thunder-strike"),
        beat(10000, 11300, left_id, "double-palm-push", x0=left_x + 0.40, x1=left_x + 0.98, z0=0.0, z1=0.0, facing="right", effect="sword-arc"),
    ]


def assault_combo(actor_id: str, *, start_x: float, facing: str) -> list[dict]:
    direction = 1.0 if facing == "right" else -1.0
    return [
        beat(3600, 4900, actor_id, "flying-kick", x0=start_x, x1=start_x + 0.9 * direction, z0=0.02, z1=0.22, facing=facing, effect="飞踢"),
        beat(5300, 6600, actor_id, "spin-kick", x0=start_x + 0.8 * direction, x1=start_x + 1.3 * direction, z0=0.18, z1=0.08, facing=facing, effect="命中特效"),
        beat(7600, 9000, actor_id, "double-palm-push", x0=start_x + 1.0 * direction, x1=start_x + 1.7 * direction, z0=0.06, z1=0.10, facing=facing, effect="dragon-palm"),
    ]


SCENE_SPECS = [
    SceneSpec(
        "scene-001",
        "mountain-cliff",
        "风雷关外战云压顶，萧寒在绝壁上看见敌营火海铺到天边，知道这一夜要拿血来守。",
        [front_actor("old_qin", -2.4, facing="right"), front_actor("xiao_han", 0.2, facing="left"), back_actor("scout", 3.2, facing="left")],
        fortress_props(0, night=True),
        [line("narrator", "北风卷旗，风雷关三十里外，敌军火把像一条赤蛇，正往山口慢慢爬来。"), line("scout", "报，薛藏锋主力已逼到黑石坡，骑阵、弩阵、火车阵全带来了。"), line("xiao_han", "他不是来试探，是来一口吞关。"), line("old_qin", "那就让他先知道，这道关不是门，是磨刀石。")],
        effects=[effect("风起云涌", start_ms=400, end_ms=2800, alpha=0.16, playback_speed=0.92), effect("千军万马冲杀", start_ms=2400, end_ms=14500, alpha=0.16, playback_speed=0.90)],
        audio=war_audio(heart=True, crowd=True),
    ),
    SceneSpec(
        "scene-002",
        "temple-courtyard",
        "燕王在关中点兵，宁霜与顾云舟当场立下血誓，要把这一夜拖到天亮。",
        [front_actor("yan_wang", -2.3, facing="right"), front_actor("ning_shuang", 0.3, facing="left"), front_actor("gu_yunzhou", 2.7, facing="left", scale=0.94), back_actor("xiao_han", 3.8, facing="left")],
        fortress_props(1, stage=True),
        [line("yan_wang", "今夜若关破，敌骑三日就能踏进中州腹地。"), line("ning_shuang", "那就不让他们破，我守东墙，谁上来谁死。"), line("gu_yunzhou", "薛藏锋更想抢钟楼和火库，只守城门还不够。"), line("xiao_han", "好，今夜分三线，谁先撑不住，另外两线就去替他续命。")],
        effects=[effect("风起云涌", start_ms=800, end_ms=3000, alpha=0.16, playback_speed=0.92)],
        audio=war_audio(crowd=True),
    ),
    SceneSpec(
        "scene-003",
        "archive-library",
        "顾云舟翻出旧图，发现风雷关真正的命门不是正门，而是钟楼下那条废弃火道。",
        [front_actor("gu_yunzhou", -2.2, facing="right"), front_actor("old_qin", 0.8, facing="left"), back_actor("ning_shuang", 3.0, facing="left")],
        fortress_props(2, interior=True),
        [line("gu_yunzhou", "找到了，钟楼下有一条废火道，直通内库。"), line("old_qin", "那条道二十年没人走，薛藏锋怎么会知道。"), line("ning_shuang", "他营中有旧军匠，若有人带路，今夜最危险的就不是城门。"), line("gu_yunzhou", "所以得有人守明线，也得有人去堵暗线。")],
        effects=[effect("黑洞旋转", start_ms=3600, end_ms=7400, alpha=0.14, playback_speed=0.90)],
        audio=war_audio(heart=True),
    ),
    SceneSpec(
        "scene-004",
        "night-bridge",
        "薛藏锋在江桥前亲自亮相，一开口就把压迫感推到所有人脸上。",
        [front_actor("xue_cang", -2.0, facing="right"), front_actor("xiao_han", 2.0, facing="left"), back_actor("scout", 3.5, facing="left")],
        fortress_props(3, night=True),
        [line("xue_cang", "风雷关守了十七年，今日也该换旗了。"), line("xiao_han", "换旗之前，先问问我刀肯不肯点头。"), line("xue_cang", "我今夜不只要关，还要把守关的人一个一个钉在城门上。"), line("xiao_han", "那你最好亲自来钉，不然别人靠近一步都难。")],
        effects=[effect("骑兵冲杀", start_ms=2400, end_ms=14500, alpha=0.18, playback_speed=0.90)],
        audio=war_audio(metal=True, crowd=True),
    ),
    SceneSpec(
        "scene-005",
        "training-ground",
        "第一轮冲锋砸上校场，萧寒带人硬碰敌军先锋，整片地面都在发抖。",
        [front_actor("xiao_han", -2.1, facing="right"), front_actor("scout", 0.7, facing="left"), mid_actor("xue_cang", 3.0, facing="left")],
        fortress_props(4, stage=True),
        [line("scout", "黑甲先锋到了，最前面那排全是重盾。"), line("xiao_han", "重盾也要靠人扛，先打人，再拆阵。"), line("xue_cang", "冲过去，把这道关先撞出第一道裂口。"), line("xiao_han", "来，今晚谁先退，谁就不是活人。")],
        extra_beats=duel_beats("xiao_han", "xue_cang", left_x=-2.0, right_x=2.9, heavy=True),
        effects=[effect("千军万马冲杀", start_ms=800, end_ms=5200, alpha=0.16, playback_speed=0.90), effect("爆炸特效", start_ms=6800, end_ms=8200, alpha=0.18, playback_speed=0.92)],
        audio=war_audio(metal=True, boom=True, crowd=True),
    ),
    SceneSpec(
        "scene-006",
        "street-day",
        "东街被弩车轰出火线，宁霜一边驱散百姓一边把敌人往窄巷里拖。",
        [front_actor("ning_shuang", -2.1, facing="right"), front_actor("scout", 0.6, facing="left"), back_actor("yan_wang", 3.1, facing="left")],
        fortress_props(5, night=False),
        [line("scout", "东街起火了，再退就退进百姓窝棚。"), line("ning_shuang", "别往宽处跑，把人全压进两边巷口。"), line("yan_wang", "宁霜，保住街心，不准火线越过钟楼。"), line("ning_shuang", "钟楼在，我在，火想过去先踩我尸体。")],
        extra_beats=[beat(5000, 6400, "ning_shuang", "flying-kick", x0=-2.0, x1=-1.0, z0=0.0, z1=0.22, facing="right", effect="飞踢"), beat(8000, 9300, "ning_shuang", "straight-punch", x0=-1.0, x1=-0.2, z0=0.08, z1=0.0, facing="right", effect="直拳特效")],
        effects=[effect("熊熊大火", start_ms=300, end_ms=14500, alpha=0.16, playback_speed=0.90), effect("火烧赤壁", start_ms=2600, end_ms=11000, alpha=0.14, playback_speed=0.92)],
        audio=war_audio(boom=True, inferno=True),
    ),
    SceneSpec(
        "scene-007",
        "room-day",
        "顾云舟带斥候摸进钟楼下方，准备在敌人动暗门之前先把路封死。",
        [front_actor("gu_yunzhou", -2.2, facing="right"), front_actor("scout", 0.5, facing="left"), back_actor("old_qin", 3.1, facing="left")],
        fortress_props(6, interior=True),
        [line("gu_yunzhou", "脚下回声发空，暗门就在这附近。"), line("scout", "墙缝有火药味，他们果然已经摸进来过。"), line("old_qin", "我守外口，你进去看，若真有敌人，先砍点火的人。"), line("gu_yunzhou", "不急，先抓住领路的，活口比尸体值钱。")],
        effects=[effect("黑洞旋转", start_ms=4200, end_ms=7600, alpha=0.14, playback_speed=0.90)],
        audio=war_audio(heart=True),
    ),
    SceneSpec(
        "scene-008",
        "inn-hall",
        "关内短暂喘息，萧寒和宁霜刚碰头，外头第二轮冲锋就已经开始擂门。",
        [front_actor("xiao_han", -2.0, facing="right"), front_actor("ning_shuang", 2.0, facing="left"), back_actor("yan_wang", 0.1, facing="left", scale=0.9)],
        fortress_props(7, interior=True),
        [line("ning_shuang", "你肩上又见血了，再顶一轮手会发麻。"), line("xiao_han", "麻也得抬，薛藏锋这波是要把人气打散。"), line("yan_wang", "钟楼那边顾云舟已摸下去，你们必须把正面拖住。"), line("xiao_han", "放心，我今夜最擅长的就是拖着敌人一起疯。")],
        audio=war_audio(heart=True),
    ),
    SceneSpec(
        "scene-009",
        "theatre-stage",
        "敌营在废戏台上擂鼓，薛藏锋借势逼降，关内却只回了更硬的杀气。",
        [front_actor("xue_cang", -2.2, facing="right"), front_actor("yan_wang", 0.3, facing="left"), back_actor("xiao_han", 3.0, facing="left")],
        fortress_props(8, stage=True),
        [line("xue_cang", "开关投降，我只杀主将，余人还可活。"), line("yan_wang", "你若真只想杀主将，何必带火车和弩海。"), line("xiao_han", "别跟他讲条件，他想要的从来不是关，是把人心一起碾碎。"), line("xue_cang", "好，那我就把你们最后这点硬气也一并碾了。")],
        effects=[effect("风起云涌", start_ms=900, end_ms=3400, alpha=0.16, playback_speed=0.92), effect("死亡光线特效", start_ms=8700, end_ms=11300, alpha=0.16, playback_speed=0.96)],
        audio=war_audio(metal=True, boom=True),
    ),
    SceneSpec(
        "scene-010",
        "town-hall-records",
        "顾云舟撬开暗格，终于确认钟楼下有人通敌，而且引火的人就在内军里。",
        [front_actor("gu_yunzhou", -2.2, facing="right"), front_actor("old_qin", 0.7, facing="left"), back_actor("yan_wang", 3.0, facing="left")],
        fortress_props(9, interior=True),
        [line("gu_yunzhou", "看见了，内门封蜡是新的，昨夜才有人动过。"), line("old_qin", "那就是自己人带的路。"), line("yan_wang", "名字先别报出去，关口已经够乱，再乱军心就真的散了。"), line("gu_yunzhou", "明白，我先顺着火绳找，找到谁，谁今晚就别想出钟楼。")],
        audio=war_audio(heart=True),
    ),
    SceneSpec(
        "scene-011",
        "钱塘江",
        "外河突然燃起长火带，敌军借水面火光掩护骑兵转阵，想从侧翼扑进来。",
        [front_actor("xiao_han", -2.1, facing="right"), front_actor("scout", 0.5, facing="left"), back_actor("xue_cang", 3.1, facing="left")],
        fortress_props(10, night=True),
        [line("scout", "河面起火了，他们用火带遮住了马队换位。"), line("xiao_han", "果然是冲侧翼来的，所有人往石坡收，别让骑阵跑起来。"), line("xue_cang", "你只顾看门，却看不见我脚下这一圈路已经全是我的了。"), line("xiao_han", "看见了，所以我这回不守，我直接压过去。")],
        extra_beats=assault_combo("xiao_han", start_x=-2.0, facing="right"),
        effects=[effect("火烧赤壁", start_ms=600, end_ms=10200, alpha=0.16, playback_speed=0.92), effect("骑兵冲杀", start_ms=3400, end_ms=14500, alpha=0.16, playback_speed=0.90)],
        audio=war_audio(boom=True, inferno=True, metal=True),
    ),
    SceneSpec(
        "scene-012",
        "park-evening",
        "宁霜在城垛上迎住黑翼刀手，一连三次换位，把对方整条扑杀线生生折断。",
        [front_actor("ning_shuang", -2.1, facing="right"), front_actor("xue_cang", 2.0, facing="left"), back_actor("scout", 3.3, facing="left")],
        fortress_props(11, night=True),
        [line("xue_cang", "你是这关里最像刀的人，可惜刀太亮，最容易折。"), line("ning_shuang", "亮刀不是为了好看，是为了让你死前看得清。"), line("scout", "东垛黑翼全压上来了！"), line("ning_shuang", "来得好，我正嫌这一段杀得还不够快。")],
        extra_beats=duel_beats("ning_shuang", "xue_cang", left_x=-2.0, right_x=1.9, airborne=True, heavy=False),
        effects=[effect("激光剑对战", start_ms=3600, end_ms=10400, alpha=0.15, playback_speed=0.95), effect("命中特效", start_ms=10400, end_ms=11800, alpha=0.18, playback_speed=0.92)],
        audio=war_audio(metal=True, boom=True),
    ),
    SceneSpec(
        "scene-013",
        "archive-library",
        "顾云舟顺着火绳摸到钟楼底，终于和通敌的守库校尉撞了个正着。",
        [front_actor("gu_yunzhou", -2.1, facing="right"), front_actor("scout", 0.8, facing="left"), back_actor("old_qin", 3.0, facing="left")],
        fortress_props(12, interior=True),
        [line("scout", "原来真是他，火绳就是从库房墙后放进去的。"), line("gu_yunzhou", "你不是替薛藏锋开门，你是在替全关的人挖坟。"), line("old_qin", "少废话，先断火，再把人摁住。"), line("gu_yunzhou", "好，活口留下，我要知道薛藏锋最后那刀落在哪。")],
        extra_beats=[beat(5200, 6600, "gu_yunzhou", "straight-punch", x0=-2.0, x1=-1.2, z0=0.0, z1=0.08, facing="right", effect="直拳特效"), beat(7900, 9400, "gu_yunzhou", "hook-punch", x0=-1.0, x1=-0.2, z0=0.08, z1=0.02, facing="right", effect="命中特效")],
        effects=[effect("直拳特效", start_ms=5200, end_ms=6500, alpha=0.18, playback_speed=0.96)],
        audio=war_audio(heart=True, metal=True),
    ),
    SceneSpec(
        "scene-014",
        "training-ground",
        "真正的重甲骑阵终于撞进关前空地，地面震得像要整个翻起来。",
        [front_actor("xiao_han", -2.2, facing="right"), front_actor("xue_cang", 2.0, facing="left"), back_actor("scout", 3.5, facing="left")],
        fortress_props(13, stage=True),
        [line("scout", "重甲骑阵到了，后面还跟着火车，他们是要一口压死校场。"), line("xiao_han", "那就让我站在最前面，让他们第一口先咬到铁。"), line("xue_cang", "你再硬，也只是一个人。"), line("xiao_han", "一个人先把你的势头打断，后面的人就全能活。")],
        extra_beats=duel_beats("xiao_han", "xue_cang", left_x=-2.0, right_x=1.9, airborne=False, heavy=True),
        effects=[effect("骑兵冲杀", start_ms=1200, end_ms=14500, alpha=0.18, playback_speed=0.90), effect("爆炸特效", start_ms=6200, end_ms=8500, alpha=0.18, playback_speed=0.92)],
        audio=war_audio(metal=True, boom=True, crowd=True),
    ),
    SceneSpec(
        "scene-015",
        "street-day",
        "钟楼火道被提前封死，但敌军也顺势在街心扔下连环火罐，要逼关内军彻底乱套。",
        [front_actor("ning_shuang", -2.1, facing="right"), front_actor("yan_wang", 0.3, facing="left"), back_actor("scout", 3.0, facing="left")],
        fortress_props(14, night=False),
        [line("scout", "火罐全砸进街心了，再不压，半条街都会被点穿。"), line("yan_wang", "把后备水符全部抬出来，今夜烧掉的不能是人心。"), line("ning_shuang", "我去劈开火线，你把百姓再往里拖一层。"), line("yan_wang", "去，今晚所有人的命都押在你那一刀上。")],
        extra_beats=[beat(5400, 6800, "ning_shuang", "double-palm-push", x0=-2.0, x1=-1.1, z0=0.0, z1=0.0, facing="right", effect="sword-arc"), beat(8200, 9700, "ning_shuang", "spin-kick", x0=-1.0, x1=-0.1, z0=0.12, z1=0.02, facing="right", effect="thunder-strike")],
        effects=[effect("熊熊大火", start_ms=300, end_ms=14500, alpha=0.16, playback_speed=0.90), effect("爆炸特效", start_ms=7600, end_ms=9400, alpha=0.18, playback_speed=0.92)],
        audio=war_audio(boom=True, inferno=True),
    ),
    SceneSpec(
        "scene-016",
        "inn-hall",
        "短暂喘口气的空档里，顾云舟终于问出真相，薛藏锋最后一击会落在主门吊桥机括。",
        [front_actor("gu_yunzhou", -2.3, facing="right"), front_actor("xiao_han", 0.1, facing="left"), front_actor("ning_shuang", 2.4, facing="left")],
        fortress_props(15, interior=True),
        [line("gu_yunzhou", "问出来了，薛藏锋最后一击不打人，他打吊桥机括。"), line("xiao_han", "机括一断，主门会自己塌，我们前面全白守。"), line("ning_shuang", "那就别再分兵了，最后这口气我们三个人一起去扛。"), line("xiao_han", "好，顾云舟去拆机括，宁霜跟我上桥，今晚最后一轮一起收。")],
        audio=war_audio(heart=True),
    ),
    SceneSpec(
        "scene-017",
        "night-bridge",
        "吊桥前的最后死战爆开，薛藏锋亲手压阵，萧寒和宁霜一左一右把他卡在桥心。",
        [front_actor("xiao_han", -2.1, facing="right"), front_actor("ning_shuang", -0.4, facing="right", scale=0.94), front_actor("xue_cang", 2.0, facing="left")],
        fortress_props(16, night=True),
        [line("xue_cang", "你们总算都到了，我也懒得再拆，一口气送你们一起上路。"), line("xiao_han", "送不送得走，看你还剩几成力。"), line("ning_shuang", "桥就这么宽，今晚你退不了，我们也不退。"), line("xue_cang", "很好，那就让这座桥做最后一块棺板。")],
        extra_beats=[*duel_beats("xiao_han", "xue_cang", left_x=-2.0, right_x=1.9, airborne=True, heavy=True), beat(5200, 6800, "ning_shuang", "diagonal-kick", x0=-0.4, x1=0.4, z0=0.12, z1=0.08, facing="right", effect="飞踢")],
        effects=[effect("风起云涌", start_ms=400, end_ms=2600, alpha=0.16, playback_speed=0.92), effect("死亡光线特效", start_ms=9200, end_ms=11600, alpha=0.18, playback_speed=0.96)],
        audio=war_audio(metal=True, boom=True, heart=True),
        camera=scene_camera(16, battle=True, aerial=True),
    ),
    SceneSpec(
        "scene-018",
        "mountain-cliff",
        "顾云舟在机括室强行逆锁吊桥，铁链巨响一起，整道桥身都开始疯狂震动。",
        [front_actor("gu_yunzhou", -2.1, facing="right"), front_actor("old_qin", 0.8, facing="left"), back_actor("scout", 3.0, facing="left")],
        fortress_props(17, interior=True),
        [line("gu_yunzhou", "锁柱卡住了，再慢半息，桥面的人全得陪着掉。"), line("old_qin", "别怕反震，我替你顶第一下，你只管把逆锁扳死。"), line("scout", "铁链在回拉，桥心的人开始稳住了！"), line("gu_yunzhou", "稳住就好，接下来轮到他们往回塌。")],
        effects=[effect("启动大招特效", start_ms=3300, end_ms=5600, alpha=0.16, playback_speed=0.92), effect("龟派气功", start_ms=5800, end_ms=10800, alpha=0.16, playback_speed=0.94)],
        audio=war_audio(heart=True, boom=True),
    ),
    SceneSpec(
        "scene-019",
        "night-bridge",
        "桥心震开的一瞬，萧寒和宁霜同时前压，把薛藏锋从桥背打进火海和铁链之间。",
        [front_actor("xiao_han", -2.0, facing="right"), front_actor("ning_shuang", -0.5, facing="right", scale=0.94), front_actor("xue_cang", 2.0, facing="left")],
        fortress_props(18, night=True),
        [line("xiao_han", "就是现在，桥稳了一半，他的脚反而空了。"), line("ning_shuang", "我封左，你杀正面，别给他再起身的空。"), line("xue_cang", "你们以为这样就能压住我？"), line("xiao_han", "压不压得住，你下一口血会告诉你。")],
        extra_beats=[beat(3300, 4700, "xiao_han", "straight-punch", x0=-1.9, x1=-1.0, z0=0.0, z1=0.08, facing="right", effect="直拳特效"), beat(4700, 6100, "ning_shuang", "hook-punch", x0=-0.5, x1=0.3, z0=0.08, z1=0.12, facing="right", effect="命中特效"), beat(6200, 7600, "xiao_han", "swing-punch", x0=-0.9, x1=0.1, z0=0.12, z1=0.08, facing="right", effect="sword-arc"), beat(7800, 9300, "xiao_han", "combo-punch", x0=0.0, x1=1.0, z0=0.08, z1=0.02, facing="right", effect="dragon-palm"), beat(9600, 11200, "ning_shuang", "double-palm-push", x0=0.2, x1=1.2, z0=0.02, z1=0.04, facing="right", effect="thunder-strike")],
        effects=[effect("爆炸特效", start_ms=9800, end_ms=11800, alpha=0.18, playback_speed=0.92), effect("命中特效", start_ms=11200, end_ms=12400, alpha=0.18, playback_speed=0.92)],
        audio=war_audio(metal=True, boom=True, crowd=True),
        camera=scene_camera(18, battle=True, aerial=True),
    ),
    SceneSpec(
        "scene-020",
        "temple-courtyard",
        "天亮前最后一阵风吹过城头，关内外终于分出了生死，风雷关把这一夜硬生生熬了过去。",
        [front_actor("yan_wang", -2.2, facing="right"), front_actor("xiao_han", 0.1, facing="left"), front_actor("ning_shuang", 2.5, facing="left", scale=0.94), back_actor("gu_yunzhou", 3.8, facing="left", scale=0.88)],
        fortress_props(19, stage=True),
        [line("yan_wang", "桥没断，钟楼没塌，风雷关还站着。"), line("gu_yunzhou", "活着的人都站着，死了的人也把这一夜给我们垫出来了。"), line("ning_shuang", "别停，先抬伤兵，再清火线，真正的天亮要靠我们自己搬出来。"), line("xiao_han", "好，把活着的人都带回灯下，等太阳上来，我们再把这道关重新立一遍。")],
        effects=[effect("风起云涌", start_ms=400, end_ms=2200, alpha=0.12, playback_speed=0.92), effect("绚烂的烟花", start_ms=11200, end_ms=14200, alpha=0.12, playback_speed=0.96)],
        audio=war_audio(crowd=True),
    ),
]


class FengleiPassBloodOathVideo(BaseVideoScript):
    def get_title(self) -> str:
        return "风雷关血誓"

    def get_theme(self) -> str:
        return "热血战争、格斗武侠、守关死战、步步紧逼、爽剧反杀"

    def get_cast(self) -> list[dict]:
        return CAST

    def get_video_options(self) -> dict:
        return VIDEO

    def has_tts(self) -> bool:
        return True

    def get_notes(self) -> dict:
        return {
            "scene_count": len(SCENE_SPECS),
            "format": "fenglei-pass-blood-oath",
            "bgm_assets": [OMEN_BGM, MARCH_BGM, WAR_BGM, CRISIS_BGM, FINAL_BGM, DAWN_BGM],
            "featured_effects": [
                "千军万马冲杀",
                "骑兵冲杀",
                "熊熊大火",
                "火烧赤壁",
                "死亡光线特效",
                "爆炸特效",
                "飞踢",
                "直拳特效",
                "命中特效",
                "龟派气功",
            ],
        }

    def get_default_output(self) -> str:
        return "outputs/fenglei_pass_blood_oath.mp4"

    def get_description(self) -> str:
        return "Render a 20-scene hot-blooded war wuxia story with dense dialogue escalation, layered combat, strong effects, rich sound design, and story-driven BGM."

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


SCRIPT = FengleiPassBloodOathVideo()


def build_story() -> dict:
    return SCRIPT.build_story()


def main() -> int:
    return SCRIPT()


if __name__ == "__main__":
    raise SystemExit(main())
