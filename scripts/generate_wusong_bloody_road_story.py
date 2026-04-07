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
        "effect_overlay_alpha": 0.90,
    },
}

CAST = [
    cast_member("wu_song", "武松", "young-hero"),
    cast_member("wu_da", "武大郎", "farmer-old"),
    cast_member("pan_jinlian", "潘金莲", "office-worker-modern"),
    cast_member("xi_menqing", "西门庆", "official-minister"),
    cast_member("wang_po", "王婆", "npc-girl"),
    cast_member("county_master", "阳谷县令", "emperor-ming"),
    cast_member("shi_en", "施恩", "detective-sleek"),
    cast_member("jiang_men", "蒋门神", "general-guard"),
    cast_member("zhang_dujian", "张都监", "emperor-ming"),
    cast_member("sun_erniang", "孙二娘", "swordswoman"),
    cast_member("guard", "差拨军汉", "npc-boy"),
    cast_member("crowd", "看客百姓", "npc-boy"),
]

SCENE_DURATION_MS = 14_800
DIALOGUE_WINDOWS = [
    (400, 3000),
    (3600, 6200),
    (7400, 10000),
    (10900, 13700),
]

FLOOR_BY_BACKGROUND = {
    "cafe-night": "wood-plank",
    "street-day": "stone-court",
    "park-evening": "dark-stage",
    "room-day": "wood-plank",
    "town-hall-records": "wood-plank",
    "training-ground": "stone-court",
    "museum-gallery": "wood-plank",
    "night-bridge": "dark-stage",
    "mountain-cliff": "stone-court",
    "inn-hall": "wood-plank",
    "theatre-stage": "dark-stage",
    "temple-courtyard": "stone-court",
}

FIST_AUDIO = "assets/audio/031_26_赤手空拳打斗的声音_爱给网_aigei_com.mp3"
METAL_AUDIO = "assets/audio/刀剑、金属碰撞（带回音）_爱给网_aigei_com.mp3"
BOOM_AUDIO = "assets/audio/音效 爆炸 爆破 爆发 战斗_爱给网_aigei_com.mp3"
THUNDER_AUDIO = "assets/audio/打雷闪电.wav"
HEART_AUDIO = "assets/audio/心脏怦怦跳.wav"

OPEN_BGM = "assets/bgm/王进打高俅-赵季平-水浒传.mp3"
REVENGE_BGM = "assets/bgm/武松杀嫂-水浒传-赵季平.mp3"
ROAD_BGM = "assets/bgm/历史的天空-古筝-三国演义片尾曲.mp3"
FIGHT_BGM = "assets/bgm/王进打高俅-赵季平-水浒传.mp3"
FINAL_BGM = "assets/bgm/最后之战-热血-卢冠廷.mp3"
AFTERMATH_BGM = "assets/bgm/铁血丹心.mp3"

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
    if any(token in text for token in ("杀", "打", "砍", "死", "滚", "宰", "拳", "刀", "毒", "火")):
        return "angry"
    if any(token in text for token in ("快", "立刻", "马上", "冲", "追", "拿下")):
        return "excited"
    if any(token in text for token in ("计", "案", "证", "药", "酒", "路数", "局")):
        return "thinking"
    if any(token in text for token in ("哥哥", "回来", "放心", "好汉")):
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


def scene_camera(scene_index: int, *, battle: bool, chase: bool = False) -> dict:
    if chase:
        return camera_pan(x=-0.30, z=0.04, zoom=1.08, to_x=0.26, to_z=0.0, to_zoom=1.18, ease="ease-in-out")
    if battle:
        return camera_pan(x=-0.24 + 0.04 * (scene_index % 3), z=0.04, zoom=1.07, to_x=0.18, to_z=0.01, to_zoom=1.16, ease="ease-in-out")
    if scene_index in {0, 8, 19, 31}:
        return camera_static(x=0.0, z=0.03, zoom=1.08)
    return camera_pan(x=-0.18, z=0.02, zoom=1.0, to_x=0.14, to_z=0.0, to_zoom=1.06, ease="ease-in-out")


def market_props(scene_index: int, *, indoor: bool = False, night: bool = False, bridge: bool = False) -> list[dict]:
    if indoor:
        return [
            prop("wall-window", -3.8, -1.0, scale=0.92, layer="back"),
            prop("wall-door", 3.8, -1.02, scale=0.92, layer="back"),
            prop("lantern", 3.1, -0.92, scale=0.94, layer="front"),
        ]
    if bridge:
        return [
            prop("moon", 3.8, -0.42, scale=0.72, layer="back"),
            prop("star", -3.8, -0.55, scale=0.56, layer="back"),
            prop("house", 0.0, -1.10, scale=0.98, layer="back"),
        ]
    items = [prop("house", 0.0, -1.08, scale=0.98, layer="back")]
    if night:
        items.extend(
            [
                prop("moon", 3.7, -0.44, scale=0.74, layer="back"),
                prop("star", -3.6, -0.56, scale=0.55, layer="back"),
                prop("lantern", -3.3, -0.92, scale=0.94, layer="front"),
            ]
        )
    else:
        items.extend(
            [
                prop("wall-door", 3.8, -1.02, scale=0.90, layer="back"),
                prop("horse", -3.7, -0.92, scale=0.80, layer="front"),
            ]
        )
    if scene_index % 2 == 0:
        items.append(prop("weapon-rack", 0.8, -1.0, scale=0.88, layer="mid"))
    return items


def default_foregrounds(scene_index: int, background: str) -> list[dict]:
    if background in {"room-day", "town-hall-records", "inn-hall", "cafe-night", "museum-gallery"}:
        fg_id = "开着门的室内" if scene_index % 2 == 0 else "古典木门木窗-有点日式风格"
        return [foreground(fg_id, x=-0.01, y=-0.02, width=1.02, height=1.06, opacity=1.0)]
    if background in {"street-day", "park-evening", "training-ground", "night-bridge", "mountain-cliff", "temple-courtyard"}:
        return [foreground("中式古典大门", x=-0.01, y=-0.02, width=1.02, height=1.06, opacity=1.0)]
    if background == "theatre-stage":
        return [foreground("敞开的红色帘子-窗帘或床帘皆可", x=-0.02, y=-0.04, width=1.04, height=1.10, opacity=1.0)]
    return []


def story_audio(*, metal: bool = False, boom: bool = False, thunder: bool = False, heart: bool = False) -> dict:
    sfx = [
        audio_sfx(FIST_AUDIO, start_ms=4000, volume=0.78),
        audio_sfx(FIST_AUDIO, start_ms=8200, volume=0.80),
    ]
    if metal:
        sfx.append(audio_sfx(METAL_AUDIO, start_ms=5600, volume=0.70))
        sfx.append(audio_sfx(METAL_AUDIO, start_ms=10400, volume=0.68))
    if boom:
        sfx.append(audio_sfx(BOOM_AUDIO, start_ms=6900, volume=0.66))
        sfx.append(audio_sfx(BOOM_AUDIO, start_ms=11400, volume=0.60))
    if thunder:
        sfx.append(audio_sfx(THUNDER_AUDIO, start_ms=2400, volume=0.70))
    if heart:
        sfx.append(audio_sfx(HEART_AUDIO, start_ms=2300, volume=0.64))
    return scene_audio(sfx=sfx)


def scene_bgm(scene_index: int, *, battle: bool, final_arc: bool = False) -> dict:
    if scene_index <= 3:
        path, volume = OPEN_BGM, 0.40
    elif scene_index <= 7:
        path, volume = FIGHT_BGM, 0.46
    elif scene_index <= 15:
        path, volume = REVENGE_BGM, 0.42
    elif scene_index <= 20:
        path, volume = ROAD_BGM, 0.39
    elif scene_index <= 27:
        path, volume = FIGHT_BGM, 0.48
    elif final_arc:
        path, volume = FINAL_BGM, 0.50
    else:
        path, volume = AFTERMATH_BGM, 0.38
    if battle and path in {OPEN_BGM, ROAD_BGM, REVENGE_BGM}:
        path, volume = FIGHT_BGM, 0.48
    return audio_bgm(path, volume=volume, loop=True)


def tiger_beats() -> list[dict]:
    return [
        beat(3400, 4700, "wu_song", "somersault", x0=-1.8, x1=-0.8, z0=0.02, z1=0.24, facing="right", effect="thunder-strike"),
        beat(5200, 6700, "wu_song", "hook-punch", x0=-0.8, x1=0.0, z0=0.18, z1=0.06, facing="right", effect="hit"),
        beat(7600, 9200, "wu_song", "swing-punch", x0=0.0, x1=0.8, z0=0.08, z1=0.04, facing="right", effect="dragon-palm"),
        beat(10100, 11800, "wu_song", "double-palm-push", x0=0.8, x1=1.5, z0=0.02, z1=0.06, facing="right", effect="爆炸特效"),
    ]


def brawl_beats(left_id: str, right_id: str, *, left_x: float, right_x: float, heavy: bool = False) -> list[dict]:
    return [
        beat(3400, 4700, left_id, "straight-punch", x0=left_x, x1=left_x + 0.55, z0=0.0, z1=0.08, facing="right", effect="直拳特效" if heavy else "hit"),
        beat(5100, 6400, right_id, "hook-punch", x0=right_x, x1=right_x - 0.42, z0=0.04, z1=0.12, facing="left", effect="hit"),
        beat(7200, 8700, left_id, "combo-punch" if heavy else "swing-punch", x0=left_x + 0.30, x1=left_x + 1.00, z0=0.10, z1=0.04, facing="right", effect="dragon-palm" if heavy else "hit"),
        beat(9300, 10800, right_id, "spin-kick", x0=right_x - 0.12, x1=right_x - 0.78, z0=0.12, z1=0.0, facing="left", effect="thunder-strike"),
        beat(11200, 12600, left_id, "double-palm-push", x0=left_x + 0.78, x1=left_x + 1.46, z0=0.02, z1=0.08, facing="right", effect="sword-arc"),
    ]


SCENE_SPECS = [
    SceneSpec(
        "scene-001",
        "cafe-night",
        "武松归乡路经景阳冈酒肆，一进门便要好酒，整间店的人都被他的气势压得抬不起头。",
        [front_actor("wu_song", -2.1, facing="right"), front_actor("crowd", 0.8, facing="left"), back_actor("guard", 3.2, facing="left")],
        market_props(0, indoor=True),
        [
            line("wu_song", "店家，上酒，三碗不够就六碗，今夜我走得远，肚里要先烧起一口热气。"),
            line("crowd", "这汉子开口就像打雷，瞧着不似寻常过路人。"),
            line("guard", "客官，这酒后劲极大，平常人三碗就扶着门出去。"),
            line("wu_song", "我不是平常人，酒要是没劲，倒是浪费了你这块招牌。"),
        ],
        audio=story_audio(heart=True),
    ),
    SceneSpec(
        "scene-002",
        "cafe-night",
        "店家连连劝阻，又把景阳冈猛虎吃人的榜文摆出来，想压住武松这口硬气。",
        [front_actor("wu_song", -2.1, facing="right"), front_actor("guard", 0.6, facing="left"), back_actor("crowd", 3.0, facing="left")],
        market_props(1, indoor=True),
        [
            line("guard", "客官，榜文写得明白，天黑之后景阳冈不能过，前几日又添了两条人命。"),
            line("wu_song", "我若被一张纸就吓住，也不配吃你这十八碗透瓶香。"),
            line("crowd", "他越喝眼越亮，不像醉，倒像真要去把那虎打死。"),
            line("wu_song", "把酒再满上，我喝完这一碗，就让那畜生知道什么叫撞见爷爷。"),
        ],
        effects=[effect("风起云涌", start_ms=10100, end_ms=13600, alpha=0.14, playback_speed=0.92)],
        audio=story_audio(heart=True),
    ),
    SceneSpec(
        "scene-003",
        "park-evening",
        "月色压林，榜文在风里拍得乱响，武松拎着哨棒独自上冈，越走越听见山风像兽喘。",
        [front_actor("wu_song", -2.2, facing="right"), back_actor("crowd", 3.3, facing="left")],
        [*market_props(2, night=True), prop("tiger", 2.8, -0.94, scale=0.72, layer="mid")],
        [
            line("wu_song", "好一个景阳冈，风都带着腥气，难怪把一群活人吓得不敢抬脚。"),
            line("crowd", "若这时有人在林子里看他，只会当他不是人，是一口会走路的硬刀。"),
            line("wu_song", "越凶越好，省得我回头还要满山去找。"),
            line("wu_song", "出来吧，别躲了，我这条路今夜只准我一个活物过。"),
        ],
        effects=[effect("电闪雷鸣", start_ms=800, end_ms=2800, alpha=0.16, playback_speed=0.94), effect("风起云涌", start_ms=3600, end_ms=11800, alpha=0.16, playback_speed=0.92)],
        audio=story_audio(thunder=True, heart=True),
    ),
    SceneSpec(
        "scene-004",
        "park-evening",
        "吊睛白额虎从乱树后猛扑出来，武松酒意尽散，哨棒横起，整座山冈都像被这一扑震了一下。",
        [front_actor("wu_song", -2.0, facing="right"), back_actor("crowd", 3.2, facing="left")],
        [prop("tiger", 1.6, -0.88, scale=0.88, layer="front"), *market_props(3, night=True)],
        [
            line("wu_song", "来得好！你若再慢一步，我倒嫌今夜这一身酒白热了。"),
            line("crowd", "那虎张口扑人，爪风刮得草叶都翻了，换了旁人，魂已经先碎。"),
            line("wu_song", "想拿我下酒？先看看你这一口牙够不够硬。"),
            line("wu_song", "这一棒下去，要么你死，要么我今晚就埋在你肚里。"),
        ],
        extra_beats=tiger_beats(),
        effects=[effect("飞踢", start_ms=3400, end_ms=5200, alpha=0.18, playback_speed=0.94), effect("命中特效", start_ms=7200, end_ms=9200, alpha=0.18, playback_speed=0.92)],
        audio=story_audio(boom=True, thunder=True),
        camera=scene_camera(3, battle=True, chase=True),
    ),
    SceneSpec(
        "scene-005",
        "park-evening",
        "哨棒打折之后，武松索性弃棒上手，拽住虎头连拳带肘狠狠干下去，硬把猛虎压进泥里。",
        [front_actor("wu_song", -1.9, facing="right"), back_actor("crowd", 3.1, facing="left")],
        [prop("tiger", 1.2, -0.90, scale=0.90, layer="front"), *market_props(4, night=True)],
        [
            line("wu_song", "棒断了更好，爷爷这双拳头，本就比木头更认得你这张脸。"),
            line("crowd", "拳拳到肉，像雷一样砸进虎骨里，那畜生越挣，武松的火气越旺。"),
            line("wu_song", "你方才不是凶得很么，怎么现在只剩这点喘气的本事。"),
            line("wu_song", "给我趴下！今夜景阳冈只许我武松一个名字站着。"),
        ],
        extra_beats=brawl_beats("wu_song", "crowd", left_x=-1.8, right_x=3.0, heavy=True)[:4],
        effects=[effect("dragon-palm", start_ms=6900, end_ms=9800, alpha=0.18, playback_speed=0.90), effect("爆炸特效", start_ms=10800, end_ms=12400, alpha=0.18, playback_speed=0.92)],
        audio=story_audio(boom=True),
        camera=scene_camera(4, battle=True, chase=True),
    ),
    SceneSpec(
        "scene-006",
        "street-day",
        "一夜过去天光大亮，村人上冈看见死虎横陈、武松提气而立，顿时把他奉成打虎英雄。",
        [front_actor("wu_song", -1.8, facing="right"), front_actor("crowd", 1.0, facing="left"), back_actor("guard", 3.2, facing="left")],
        [prop("tiger", 2.2, -0.96, scale=0.84, layer="mid"), *market_props(5)],
        [
            line("crowd", "天一亮上冈的人都看傻了，景阳冈那头吊睛白额虎，真被这位好汉一人打死了！"),
            line("guard", "快回县里报喜，阳谷县多少年都没人敢上冈，如今竟真出了个活阎罗。"),
            line("wu_song", "别把我往神仙里抬，我只是命硬，拳头也比它更硬。"),
            line("crowd", "命硬也好，拳硬也好，今日起阳谷县人人都记住你武松这两个字。"),
        ],
        effects=[effect("绚烂的烟花", start_ms=10800, end_ms=13800, alpha=0.12, playback_speed=0.96)],
        audio=story_audio(),
    ),
    SceneSpec(
        "scene-007",
        "town-hall-records",
        "打虎喜讯传进县衙，阳谷县令亲迎武松，把他奉为都头，公堂上下都在看这位新出炉的英雄。",
        [front_actor("county_master", -2.0, facing="right"), front_actor("wu_song", 0.4, facing="left"), back_actor("guard", 3.0, facing="left")],
        market_props(6, indoor=True),
        [
            line("county_master", "打虎的喜报刚进县衙，你就到了，一人打死吊睛虎，给我阳谷挣足了脸面，这都头之职，非你武松莫属。"),
            line("wu_song", "蒙大人看得起，武松只求做事痛快，不求穿这身公服摆威风。"),
            line("guard", "都头说话也像出拳，干净利落，难怪一上来就压住全堂气口。"),
            line("county_master", "好，我就喜欢你这股硬劲，阳谷县从今日起有一把真刀了。"),
        ],
        audio=story_audio(),
    ),
    SceneSpec(
        "scene-008",
        "street-day",
        "受封都头之后，武松先回家与武大重逢，小小炊饼担前，兄弟二人一句哥哥一句兄弟，情分直把人心烫热。",
        [front_actor("wu_da", -2.1, facing="right"), front_actor("wu_song", 1.0, facing="left"), back_actor("crowd", 3.1, facing="left")],
        market_props(7),
        [
            line("wu_da", "二郎，你受了都头还肯先回这个家，真是你回来了？这些年我日日念你，只怕这辈子再见不着你。"),
            line("wu_song", "哥哥，我这条命走得再远，也总要回你这口锅边来。"),
            line("crowd", "都头原来还有这样一个哥哥，两个一站，像天硬地软都在他们中间。"),
            line("wu_da", "快回家，炊饼凉了不要紧，家里的灯可一直给你留着。"),
        ],
        audio=story_audio(),
    ),
    SceneSpec(
        "scene-009",
        "room-day",
        "潘金莲初见武松，心思一下就偏了，言语眼波都往歪处拐，屋里空气都黏得发烫。",
        [front_actor("pan_jinlian", -2.0, facing="right"), front_actor("wu_song", 1.8, facing="left"), back_actor("wu_da", 3.2, facing="left", scale=0.88)],
        market_props(8, indoor=True),
        [
            line("pan_jinlian", "叔叔真是好人物，站在屋里像把刚开锋的刀，叫人看一眼就移不开。"),
            line("wu_song", "嫂嫂说笑了，我是粗汉，不懂这些花话，只认一口热饭一张干净床。"),
            line("wu_da", "一家人和和气气最好，二郎回来，我这屋总算像个家了。"),
            line("pan_jinlian", "是啊，家里多了这样一位叔叔，往后想必热闹得很。"),
        ],
        audio=story_audio(heart=True),
    ),
    SceneSpec(
        "scene-010",
        "room-day",
        "潘金莲递酒送笑，试探越来越露骨，武松却一句重话就把她那点歪火当场踩灭。",
        [front_actor("pan_jinlian", -2.0, facing="right"), front_actor("wu_song", 1.8, facing="left")],
        market_props(9, indoor=True),
        [
            line("pan_jinlian", "叔叔这一身汗气未散，我给你筛一盏酒，暖暖身子，也暖暖心。"),
            line("wu_song", "酒我自己会喝，心也不用嫂嫂来暖，做人先把门槛站稳，比什么都强。"),
            line("pan_jinlian", "你一句话就冷成这样，真叫人下不来台。"),
            line("wu_song", "下不来就别往上爬，哥哥还在，你我之间只该守本分两个字。"),
        ],
        effects=[effect("风起云涌", start_ms=10300, end_ms=13400, alpha=0.12, playback_speed=0.92)],
        audio=story_audio(heart=True),
    ),
    SceneSpec(
        "scene-011",
        "street-day",
        "武松外出当差几日不在家，潘金莲倚窗望街，恰好撞上西门庆，两人眼神一碰，祸根便落下了。",
        [front_actor("pan_jinlian", -2.1, facing="right"), front_actor("xi_menqing", 1.2, facing="left"), back_actor("wang_po", 3.0, facing="left")],
        market_props(10),
        [
            line("xi_menqing", "武松一走，这窗口上就站着这样一位娘子，一眼就把满街人都比成了灰。"),
            line("pan_jinlian", "你若只是拿嘴撩人，就快走，别叫街坊都瞧见。"),
            line("wang_po", "二位倒像前世就认得，我这老婆子只看一眼，便知道有一段热事要开张。"),
            line("xi_menqing", "热不热我不知道，我只知道这扇窗一开，我的魂就先过去半个。"),
        ],
        audio=story_audio(heart=True),
    ),
    SceneSpec(
        "scene-012",
        "cafe-night",
        "几日下来王婆两头递话，西门庆与潘金莲越走越近，一张脏网在小巷灯影里慢慢拉紧。",
        [front_actor("wang_po", -2.2, facing="right"), front_actor("xi_menqing", 0.4, facing="left"), front_actor("pan_jinlian", 2.8, facing="left", scale=0.94)],
        market_props(11, indoor=True),
        [
            line("wang_po", "这几日你来我往，郎有情妾有意，就差一层窗纸，捅破了，今后便是好风好月。"),
            line("xi_menqing", "银子和胭脂我都备好，只要她肯点头，我便叫这阳谷街都给她让路。"),
            line("pan_jinlian", "我要的不是胭脂，是一口能烧到骨头里的活气。"),
            line("wang_po", "那就别犹豫，犹豫久了，热心也会凉，凉了再想烧，可就难了。"),
        ],
        audio=story_audio(heart=True),
    ),
    SceneSpec(
        "scene-013",
        "street-day",
        "武大撞见奸情后被西门庆一脚踹倒，脸贴在地上，心却像被人生生踩碎。",
        [front_actor("wu_da", -2.1, facing="right"), front_actor("xi_menqing", 1.0, facing="left"), back_actor("pan_jinlian", 3.0, facing="left")],
        market_props(12),
        [
            line("wu_da", "你们竟真做出这样见不得人的丑事，还敢当着我的脸站着。"),
            line("xi_menqing", "就凭你也配挡路，滚开，别拿你那点命来脏我的鞋。"),
            line("pan_jinlian", "你若识趣就忍下去，偏要闹，只会叫自己更难堪。"),
            line("wu_da", "我这口气咽不下，就算被打死，也要把这张脏脸撕给街坊看。"),
        ],
        extra_beats=[beat(7200, 8800, "xi_menqing", "straight-punch", x0=1.0, x1=0.2, z0=0.0, z1=0.06, facing="left", effect="hit")],
        effects=[effect("命中特效", start_ms=7300, end_ms=9000, alpha=0.18, playback_speed=0.92)],
        audio=story_audio(boom=True),
    ),
    SceneSpec(
        "scene-014",
        "room-day",
        "武大伤重卧床，潘金莲嘴上喂药，心里却已和王婆把一碗毒汤搅得乌黑。",
        [front_actor("wu_da", -2.1, facing="right"), front_actor("pan_jinlian", 0.7, facing="left"), back_actor("wang_po", 3.0, facing="left")],
        market_props(13, indoor=True),
        [
            line("wu_da", "这药怎么苦得发腥，我喝下去，心口像被刀子一下一下拧。"),
            line("pan_jinlian", "病深药苦，哥哥你只管喝，熬过去便能下床。"),
            line("wang_po", "苦口才利病，娘子这番心，可是把半条命都搭进去了。"),
            line("wu_da", "若二郎在家，绝不叫我喝得这样心慌。"),
        ],
        effects=[effect("黑洞旋转", start_ms=9200, end_ms=13200, alpha=0.10, playback_speed=0.90)],
        audio=story_audio(heart=True),
    ),
    SceneSpec(
        "scene-015",
        "room-day",
        "武松公干归来只见灵堂白布，他俯身验尸，一点点从焦黑指甲和毒痕里看出了血案。",
        [front_actor("wu_song", -2.0, facing="right"), front_actor("wu_da", 0.6, facing="left", scale=0.88), back_actor("pan_jinlian", 3.0, facing="left")],
        market_props(14, indoor=True),
        [
            line("wu_song", "我才离家几日，哥哥就死得这样急，指甲发乌，口鼻有滞，这不是病死，是有人下了狠手。"),
            line("pan_jinlian", "叔叔，你莫胡猜，人死都死了，何苦再翻他的尸。"),
            line("wu_song", "你若心里没鬼，声音为什么抖得像筛糠。"),
            line("wu_song", "这一案我要查到底，谁碰了我哥哥，我就要谁拿命来还。"),
        ],
        effects=[effect("电闪雷鸣", start_ms=1800, end_ms=3800, alpha=0.16, playback_speed=0.94)],
        audio=story_audio(thunder=True, heart=True),
    ),
    SceneSpec(
        "scene-016",
        "town-hall-records",
        "灵堂逼供，武松把王婆、潘金莲逼到脸无人色，一字一句都像在堂下砸钉子。",
        [front_actor("wu_song", -2.2, facing="right"), front_actor("pan_jinlian", 0.4, facing="left"), front_actor("wang_po", 2.8, facing="left", scale=0.94)],
        market_props(15, indoor=True),
        [
            line("wu_song", "王婆，你那间茶坊里一天能卖几盏茶，却偏生装得下这么大一桩奸毒。"),
            line("wang_po", "好汉饶命，我不过是个媒婆嘴，真下手的不是我。"),
            line("pan_jinlian", "别再逼了，我承认，我认了，可都是西门庆那厮把我往火里推。"),
            line("wu_song", "谁推的谁害的我都会算，今日先把你们的话，一句一句刻进我刀里。"),
        ],
        audio=story_audio(heart=True),
    ),
    SceneSpec(
        "scene-017",
        "museum-gallery",
        "武松提刀直奔狮子楼，西门庆还想靠嘴硬和财势压人，却被武松一眼瞪得腿软。",
        [front_actor("wu_song", -2.1, facing="right"), front_actor("xi_menqing", 1.0, facing="left"), back_actor("crowd", 3.1, facing="left")],
        market_props(16, indoor=True),
        [
            line("xi_menqing", "武都头，有话可以坐下说，你若真动手，满楼都是见证。"),
            line("wu_song", "见证更好，我今日就是要满楼人都看着，你这张命该怎么还。"),
            line("crowd", "武都头提刀上楼，眼里的火比灯还亮，谁都知道要出血了。"),
            line("wu_song", "西门庆，站直了，别让我这一刀落得不痛快。"),
        ],
        extra_beats=brawl_beats("wu_song", "xi_menqing", left_x=-2.0, right_x=0.9, heavy=True),
        effects=[effect("激光剑对战", start_ms=3400, end_ms=9800, alpha=0.14, playback_speed=0.95), effect("命中特效", start_ms=11200, end_ms=12600, alpha=0.18, playback_speed=0.92)],
        audio=story_audio(metal=True, boom=True),
        camera=scene_camera(16, battle=True),
    ),
    SceneSpec(
        "scene-018",
        "room-day",
        "回到家中，武松在灵前手刃潘金莲，白绫和烛火都压不住那股滚烫的血气。",
        [front_actor("wu_song", -2.0, facing="right"), front_actor("pan_jinlian", 1.0, facing="left"), back_actor("wu_da", 3.0, facing="left", scale=0.88)],
        market_props(17, indoor=True),
        [
            line("pan_jinlian", "叔叔，我认罪，我知错，你饶我这一命，我下辈子给你哥哥做牛做马。"),
            line("wu_song", "我哥哥活着时你不做人，如今求饶，晚了。"),
            line("pan_jinlian", "你若真杀了我，这一身官服也保不住你。"),
            line("wu_song", "官服算个什么，我哥哥那条命，才是我今夜真正要穿在身上的血衣。"),
        ],
        extra_beats=[beat(7600, 9300, "wu_song", "straight-punch", x0=-1.8, x1=-0.8, z0=0.0, z1=0.08, facing="right", effect="直拳特效"), beat(9800, 11400, "wu_song", "double-palm-push", x0=-0.8, x1=0.3, z0=0.06, z1=0.0, facing="right", effect="爆炸特效")],
        effects=[effect("熊熊大火", start_ms=10300, end_ms=13600, alpha=0.10, playback_speed=0.92)],
        audio=story_audio(boom=True, heart=True),
    ),
    SceneSpec(
        "scene-019",
        "town-hall-records",
        "手刃仇人之后，武松自首受审，县令知他情有可原，却终究只能按律发配孟州。",
        [front_actor("county_master", -2.0, facing="right"), front_actor("wu_song", 0.4, facing="left"), back_actor("guard", 3.0, facing="left")],
        market_props(18, indoor=True),
        [
            line("county_master", "你报了兄仇，这案子查得明白，杀得也明白，可国法摆在堂上，我不能当它不存在。"),
            line("wu_song", "杀人偿命，武松认，但我不后悔，换一千回，我也照样宰他们。"),
            line("guard", "都头这口气从上堂到现在没软过半分，真像铁里炼出来的。"),
            line("county_master", "发配孟州，路上不得加害，谁若暗里做手脚，本官第一个不饶。"),
        ],
        audio=story_audio(),
    ),
    SceneSpec(
        "scene-020",
        "inn-hall",
        "判决落定后，武松发配途中路过十字坡，黑店杀气暗涌，孙二娘一试之下，反倒先认出了武松这口真英雄气。",
        [front_actor("sun_erniang", -2.1, facing="right"), front_actor("wu_song", 0.8, facing="left"), back_actor("guard", 3.2, facing="left")],
        market_props(19, indoor=True),
        [
            line("sun_erniang", "这位刚从官司路上过来的官人，一身枷锁还站得这么稳，怕不是寻常囚徒。"),
            line("wu_song", "黑店的香肉酒也想灌我？掌柜的，先把眼睛擦亮。"),
            line("sun_erniang", "好，好，好，一句话就见了底，你是条汉子，不该死在我这口锅边。"),
            line("wu_song", "你认出我，我也认你这身杀气，今日不翻脸，算你我都给江湖留几分面。"),
        ],
        audio=story_audio(heart=True),
    ),
    SceneSpec(
        "scene-021",
        "street-day",
        "走过十字坡到了孟州，施恩哭诉快活林被蒋门神夺走，武松一听便知道这口恶气迟早要替他出。",
        [front_actor("shi_en", -2.1, facing="right"), front_actor("wu_song", 0.8, facing="left"), back_actor("crowd", 3.0, facing="left")],
        market_props(20),
        [
            line("shi_en", "好汉刚到孟州，我就得把苦水倒给你听，我那快活林原本好好做生意，被蒋门神一来，连招牌都被他踩进泥里。"),
            line("wu_song", "一个恶汉敢把整条街压得不敢抬头，看来这孟州也缺一顿真拳头。"),
            line("crowd", "蒋门神手下又多又狠，谁替施恩出头，谁就得被他按在地上踩。"),
            line("shi_en", "我不敢求别的，只求好汉替我争回这一口做人的气。"),
        ],
        audio=story_audio(),
    ),
    SceneSpec(
        "scene-022",
        "training-ground",
        "蒋门神在快活林前耀武扬威，喝酒吃肉、打人辱人，把整条街都活活踩成了自己的台阶。",
        [front_actor("jiang_men", -2.0, facing="right"), front_actor("crowd", 0.7, facing="left"), back_actor("shi_en", 3.0, facing="left")],
        market_props(21),
        [
            line("jiang_men", "快活林从今往后姓蒋，谁要是不服，就把牙咬紧，等我一拳替他松开。"),
            line("crowd", "这厮每天都来砸场，谁敢直视他，转眼就要挨他一脚。"),
            line("shi_en", "我这口气被他压得快断了，只差一个人来把这条恶狗踹翻。"),
            line("jiang_men", "施恩，你若再敢找人来，来一个我废一个。"),
        ],
        effects=[effect("命中特效", start_ms=9800, end_ms=11500, alpha=0.16, playback_speed=0.92)],
        audio=story_audio(boom=True),
    ),
    SceneSpec(
        "scene-023",
        "street-day",
        "武松故意喝得半醉，一步三摇地闯进快活林，蒋门神一看便知道今天撞上了硬骨头。",
        [front_actor("wu_song", -2.1, facing="right"), front_actor("jiang_men", 1.2, facing="left"), back_actor("crowd", 3.2, facing="left")],
        market_props(22),
        [
            line("wu_song", "这地方既叫快活林，我今日便要在这儿痛痛快快打一场。"),
            line("jiang_men", "你醉成这样还敢进我地盘，看来是真不想站着出去。"),
            line("crowd", "这醉汉走路都像要倒，可眼神却像刀一样直钉蒋门神的脸。"),
            line("wu_song", "倒的是酒，不是胆，你若皮痒，我这就替你醒醒。"),
        ],
        audio=story_audio(heart=True),
    ),
    SceneSpec(
        "scene-024",
        "training-ground",
        "武松醉打蒋门神，先躲后压，再进肋下，最后一脚一拳把这条恶汉打得满地找牙。",
        [front_actor("wu_song", -2.0, facing="right"), front_actor("jiang_men", 1.6, facing="left"), back_actor("crowd", 3.3, facing="left")],
        market_props(23),
        [
            line("jiang_men", "站住！别总像泥鳅一样滑，我要正面把你这身骨头砸散。"),
            line("wu_song", "你砸得到再说，我这拳头专打你这种会喘气的脓包。"),
            line("crowd", "快看，蒋门神被压住了，武松这一套越打越凶，根本不给他喘气。"),
            line("wu_song", "施恩这一口气，今日我替他连本带利从你脸上收回来。"),
        ],
        extra_beats=brawl_beats("wu_song", "jiang_men", left_x=-1.9, right_x=1.5, heavy=True),
        effects=[effect("飞踢", start_ms=7100, end_ms=8700, alpha=0.18, playback_speed=0.94), effect("dragon-palm", start_ms=9000, end_ms=11600, alpha=0.18, playback_speed=0.90)],
        audio=story_audio(metal=True, boom=True),
        camera=scene_camera(23, battle=True),
    ),
    SceneSpec(
        "scene-025",
        "town-hall-records",
        "醉打蒋门神之后，张都监忽然示好，把武松请进府中好吃好喝，满屋笑脸却让人越看越冷。",
        [front_actor("zhang_dujian", -2.2, facing="right"), front_actor("wu_song", 0.4, facing="left"), back_actor("guard", 3.0, facing="left")],
        market_props(24, indoor=True),
        [
            line("zhang_dujian", "武都头快活林一战打得满城皆知，我府里正缺你这样的人，前番旧事，不如就此揭过。"),
            line("wu_song", "大人忽然看得起我，我记这情，但人心这东西，我向来只信三分。"),
            line("guard", "都监今日笑得格外和善，可这和善越多，越叫人背后发凉。"),
            line("zhang_dujian", "你只管安心住下，待我替你谋个前程，孟州城里自然没人再敢轻你。"),
        ],
        audio=story_audio(heart=True),
    ),
    SceneSpec(
        "scene-026",
        "museum-gallery",
        "都监府中夜夜饮宴，武松越住越觉得不对，墙后风声、门外脚步都像一把慢慢逼近的刀。",
        [front_actor("wu_song", -2.1, facing="right"), front_actor("zhang_dujian", 0.8, facing="left"), back_actor("guard", 3.0, facing="left")],
        market_props(25, indoor=True),
        [
            line("wu_song", "这几日酒太多，笑太满，倒把人笑得心里不安生。"),
            line("zhang_dujian", "你多心了，我待你是真，府里上下谁不夸你是条好汉。"),
            line("guard", "今晚鸳鸯楼上又设宴，灯火铺了一层又一层，像是专等一场大热闹。"),
            line("wu_song", "热闹未必是好事，灯越亮，越容易照出人脸底下那层黑。"),
        ],
        effects=[effect("黑洞旋转", start_ms=9800, end_ms=13200, alpha=0.10, playback_speed=0.90)],
        audio=story_audio(heart=True),
    ),
    SceneSpec(
        "scene-027",
        "night-bridge",
        "都监府里虚情假意铺了多日，直到押送途中至飞云浦，差拨忽然翻脸，刀子和绳索一齐压来，要把武松的命黑在水边。",
        [front_actor("wu_song", -2.0, facing="right"), front_actor("guard", 0.7, facing="left"), back_actor("zhang_dujian", 3.0, facing="left")],
        market_props(26, bridge=True),
        [
            line("guard", "武松，张都监前面几日给你的酒肉到这儿就算吃完了，走到这儿就够了，前头没你的路，只有你的一条命。"),
            line("wu_song", "果然还是翻脸了，我就说那几日的酒肉太香，香得不像给活人吃的。"),
            line("zhang_dujian", "要怪就怪你自己拳头太硬，不死，终究是个祸根。"),
            line("wu_song", "好，好，好，既然你们都把刀亮出来了，那我也不用再装糊涂。"),
        ],
        effects=[effect("电闪雷鸣", start_ms=1000, end_ms=3200, alpha=0.16, playback_speed=0.94)],
        audio=story_audio(thunder=True, heart=True),
    ),
    SceneSpec(
        "scene-028",
        "night-bridge",
        "飞云浦血战爆开，武松一身锁链照样翻身扑杀，把来害他的军汉一个个打进黑水边缘。",
        [front_actor("wu_song", -1.9, facing="right"), front_actor("guard", 1.2, facing="left"), back_actor("zhang_dujian", 3.1, facing="left")],
        market_props(27, bridge=True),
        [
            line("wu_song", "想黑我？你们这点手段，也配在飞云浦埋我武松。"),
            line("guard", "一起上！不趁他锁着，待会儿死的就是我们。"),
            line("wu_song", "锁得住手，锁不住我这口杀人的气。"),
            line("wu_song", "飞云浦今晚只留一个活名，那个人，不会是你们。"),
        ],
        extra_beats=brawl_beats("wu_song", "guard", left_x=-1.8, right_x=1.1, heavy=True),
        effects=[effect("thunder-strike", start_ms=3400, end_ms=6100, alpha=0.18, playback_speed=0.90), effect("爆炸特效", start_ms=9800, end_ms=12000, alpha=0.18, playback_speed=0.92)],
        audio=story_audio(metal=True, boom=True, thunder=True),
        camera=scene_camera(27, battle=True, chase=True),
    ),
    SceneSpec(
        "scene-029",
        "street-day",
        "飞云浦反杀之后，武松不逃反进，提着血刃当夜直扑鸳鸯楼，心里只剩一个字，杀。",
        [front_actor("wu_song", -2.1, facing="right"), back_actor("crowd", 3.0, facing="left")],
        market_props(28),
        [
            line("wu_song", "飞云浦都杀不死我，我就顺着这口血气直接来鸳鸯楼，你们那点脏胆子，今夜更别想保住。"),
            line("crowd", "武松这一身血一路走来，街上没人敢拦，连风都像在给他让路。"),
            line("wu_song", "张都监，蒋门神，你们不是爱设局么，爷爷这就提着命来收局。"),
            line("wu_song", "今夜我若不把你们一锅端净，这口气回头还得烧死我自己。"),
        ],
        effects=[effect("风起云涌", start_ms=9200, end_ms=13600, alpha=0.14, playback_speed=0.92)],
        audio=story_audio(boom=True, heart=True),
    ),
    SceneSpec(
        "scene-030",
        "museum-gallery",
        "鸳鸯楼酒席正热，张都监等人还在笑谈，下一瞬武松破门而入，满楼的喜气当场冻裂。",
        [front_actor("wu_song", -2.2, facing="right"), front_actor("zhang_dujian", 0.4, facing="left"), front_actor("jiang_men", 2.8, facing="left")],
        market_props(29, indoor=True),
        [
            line("zhang_dujian", "你不是该死在飞云浦么，怎么还能提着刀站到我楼上来。"),
            line("wu_song", "因为老天觉得你们这群畜生，还该由我亲手来剁。"),
            line("jiang_men", "一个人也敢闯楼，你这是送上门给我们收尾。"),
            line("wu_song", "收尾？好，我今日就拿你们的头，给我这一路血债真正收尾。"),
        ],
        audio=story_audio(heart=True),
    ),
    SceneSpec(
        "scene-031",
        "museum-gallery",
        "鸳鸯楼血战彻底爆开，武松从楼上杀到楼下，一拳一刀一脚，全是压了太久的怒火。",
        [front_actor("wu_song", -1.9, facing="right"), front_actor("jiang_men", 1.1, facing="left"), back_actor("zhang_dujian", 3.0, facing="left")],
        market_props(30, indoor=True),
        [
            line("wu_song", "这一刀给飞云浦，这一拳给我哥哥，这一脚给你们满肚子下作。"),
            line("jiang_men", "拦住他！别让他近都监身边，这厮疯起来真像阎罗出了殿。"),
            line("zhang_dujian", "武松，你若再往前一步，我要你全家都不得安生。"),
            line("wu_song", "我全家早被你们逼进血里了，现在轮到你们一个个下去作伴。"),
        ],
        extra_beats=[
            beat(3300, 4700, "wu_song", "straight-punch", x0=-1.8, x1=-1.0, z0=0.0, z1=0.08, facing="right", effect="直拳特效"),
            beat(5000, 6500, "wu_song", "hook-punch", x0=-1.0, x1=-0.1, z0=0.08, z1=0.14, facing="right", effect="hit"),
            beat(7000, 8600, "wu_song", "swing-punch", x0=-0.1, x1=0.8, z0=0.12, z1=0.10, facing="right", effect="dragon-palm"),
            beat(9100, 10800, "wu_song", "combo-punch", x0=0.7, x1=1.5, z0=0.10, z1=0.02, facing="right", effect="thunder-strike"),
            beat(11200, 12600, "wu_song", "double-palm-push", x0=1.3, x1=2.0, z0=0.02, z1=0.08, facing="right", effect="爆炸特效"),
        ],
        effects=[effect("激光剑对战", start_ms=3200, end_ms=9800, alpha=0.14, playback_speed=0.95), effect("熊熊大火", start_ms=10400, end_ms=13800, alpha=0.12, playback_speed=0.92)],
        audio=story_audio(metal=True, boom=True),
        camera=scene_camera(30, battle=True),
    ),
    SceneSpec(
        "scene-032",
        "mountain-cliff",
        "血溅鸳鸯楼后，武松连夜披着风远走，前路仍是刀山火海，可他背影愈走愈硬，再不回头。",
        [front_actor("wu_song", -2.2, facing="right"), back_actor("crowd", 3.0, facing="left")],
        market_props(31, night=True),
        [
            line("wu_song", "该杀的我都杀了，剩下这条路再难，我也得踩着血自己走出去。"),
            line("crowd", "夜风从山口灌下来，武松一身杀气还热着，可脚步已经稳得像铁。"),
            line("wu_song", "世道若逼人做鬼，那我就先做个会杀人的好汉，杀到它肯让路。"),
            line("wu_song", "天还没亮，可我这口气，已经不打算再向谁低了。"),
        ],
        effects=[effect("风起云涌", start_ms=600, end_ms=2600, alpha=0.12, playback_speed=0.92)],
        audio=story_audio(),
    ),
]


class WuSongBloodyRoadVideo(BaseVideoScript):
    def get_title(self) -> str:
        return "武松血路"

    def get_theme(self) -> str:
        return "水浒热血、景阳冈打虎、兄仇复雪、快活林雪耻、飞云浦反杀、血溅鸳鸯楼"

    def get_cast(self) -> list[dict]:
        return CAST

    def get_video_options(self) -> dict:
        return VIDEO

    def has_tts(self) -> bool:
        return True

    def get_notes(self) -> dict:
        return {
            "scene_count": len(SCENE_SPECS),
            "format": "wusong-bloody-road",
            "bgm_assets": [OPEN_BGM, REVENGE_BGM, ROAD_BGM, FIGHT_BGM, FINAL_BGM, AFTERMATH_BGM],
            "featured_effects": [
                "电闪雷鸣",
                "风起云涌",
                "飞踢",
                "命中特效",
                "dragon-palm",
                "thunder-strike",
                "激光剑对战",
                "爆炸特效",
                "熊熊大火",
            ],
        }

    def get_default_output(self) -> str:
        return "outputs/wusong_bloody_road.mp4"

    def get_description(self) -> str:
        return "Render a 32-scene Water Margin action drama covering Wu Song from Jingyang Ridge to Bloody Yuanyang Tower."

    def get_scenes(self) -> list[dict]:
        scenes: list[dict] = []
        for scene_index, spec in enumerate(SCENE_SPECS):
            dialogue_items, talk_beats, expressions_track = build_dialogue_bundle(spec.lines)
            talk_beats = trim_talk_beats_for_actions(talk_beats, spec.extra_beats)
            beats = sorted([*talk_beats, *spec.extra_beats], key=lambda item: (item["start_ms"], item["actor_id"]))
            expressions_sorted = sorted(expressions_track, key=lambda item: (item["start_ms"], item["actor_id"]))
            battle = bool(spec.extra_beats or spec.effects)
            chase = spec.background in {"night-bridge", "mountain-cliff"} and battle
            final_arc = scene_index >= 28
            audio_payload = scene_audio(bgm=scene_bgm(scene_index, battle=battle, final_arc=final_arc), sfx=list(spec.audio.get("sfx", [])))
            scenes.append(
                scene(
                    spec.scene_id,
                    background=spec.background,
                    floor=FLOOR_BY_BACKGROUND[spec.background],
                    duration_ms=SCENE_DURATION_MS,
                    summary=spec.summary,
                    camera=spec.camera or scene_camera(scene_index, battle=battle, chase=chase),
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


SCRIPT = WuSongBloodyRoadVideo()


def build_story() -> dict:
    return SCRIPT.build_story()


def main() -> int:
    return SCRIPT()


if __name__ == "__main__":
    raise SystemExit(main())
