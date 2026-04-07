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
    cast_member("zhou_yu", "周瑜", "general-guard"),
    cast_member("zhuge_liang", "诸葛亮", "strategist"),
    cast_member("huang_gai", "黄盖", "farmer-old"),
    cast_member("cao_cao", "曹操", "official-minister"),
    cast_member("sun_quan", "孙权", "emperor-ming"),
    cast_member("lu_su", "鲁肃", "detective-sleek"),
    cast_member("xiao_qiao", "小乔", "npc-girl"),
    cast_member("messenger", "校尉", "npc-boy"),
    cast_member("narrator", "旁白", "narrator"),
]

SCENE_DURATION_MS = 15_200
DIALOGUE_WINDOWS = [
    (400, 3000),
    (3600, 6200),
    (7600, 10200),
    (11000, 14000),
]

FLOOR_BY_BACKGROUND = {
    "night-bridge": "dark-stage",
    "mountain-cliff": "stone-court",
    "temple-courtyard": "stone-court",
    "training-ground": "stone-court",
    "park-evening": "dark-stage",
    "town-hall-records": "wood-plank",
    "theatre-stage": "dark-stage",
    "archive-library": "wood-plank",
    "hotel-lobby": "wood-plank",
    "inn-hall": "wood-plank",
    "room-day": "wood-plank",
    "street-day": "stone-court",
}

FIST_AUDIO = "assets/audio/031_26_赤手空拳打斗的声音_爱给网_aigei_com.mp3"
METAL_AUDIO = "assets/audio/刀剑、金属碰撞（带回音）_爱给网_aigei_com.mp3"
BOOM_AUDIO = "assets/audio/音效 爆炸 爆破 爆发 战斗_爱给网_aigei_com.mp3"
DIALOGUE_BGM = "assets/bgm/历史的天空-古筝-纯音乐.mp3"
BATTLE_BGM = "assets/bgm/最后之战-热血-卢冠廷.mp3"


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
    audio: dict = field(default_factory=scene_audio)
    camera: dict | None = None


def line(speaker_id: str, text: str) -> DialogueLine:
    return (speaker_id, text)


def front_actor(actor_id: str, x: float, *, facing: str, scale: float = 1.0, z: float = 0.0) -> dict:
    return actor(actor_id, x, z=z, facing=facing, scale=scale)


def mid_actor(actor_id: str, x: float, *, facing: str, scale: float = 0.94, z: float = -0.12) -> dict:
    return actor(actor_id, x, z=z, facing=facing, scale=scale, layer="mid")


def back_actor(actor_id: str, x: float, *, facing: str, scale: float = 0.88, z: float = -0.72) -> dict:
    return actor(actor_id, x, z=z, facing=facing, scale=scale, layer="back")


def infer_expression(text: str) -> str:
    if any(token in text for token in ("杀", "破", "火", "箭", "攻", "斩", "战", "追", "烧")):
        return "angry"
    if any(token in text for token in ("快", "起火", "出船", "迎上", "压上", "急报")):
        return "excited"
    if any(token in text for token in ("风", "局", "计", "谋", "退路", "时机", "军心", "阵")):
        return "thinking"
    if any(token in text for token in ("笑", "稳住", "可惜", "自负", "果然")):
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
            x=-0.38 + 0.05 * (scene_index % 3),
            z=0.04,
            zoom=1.05,
            to_x=0.26 - 0.04 * (scene_index % 2),
            to_z=0.01,
            to_zoom=1.13,
            ease="ease-in-out",
        )
    if scene_index in {1, 6, 18}:
        return camera_static(x=0.0, z=0.02, zoom=1.06)
    return camera_pan(
        x=-0.24 + 0.04 * (scene_index % 2),
        z=0.03,
        zoom=1.0,
        to_x=0.18 - 0.05 * (scene_index % 3),
        to_z=0.0,
        to_zoom=1.08,
        ease="ease-in-out",
    )


def river_props(scene_index: int, *, night: bool = False) -> list[dict]:
    items = [prop("house", 0.0, -1.08, scale=1.0, layer="back")]
    if night:
        items.extend(
            [
                prop("moon", 3.8, -0.42, scale=0.74, layer="back"),
                prop("star", -3.8, -0.55, scale=0.56, layer="back"),
                prop("lantern", -3.5, -0.92, scale=0.96, layer="front"),
            ]
        )
    else:
        items.extend(
            [
                prop("horse", -3.7, -0.92, scale=0.82, layer="front"),
                prop("wall-door", 3.8, -1.02, scale=0.9, layer="back"),
            ]
        )
    if scene_index % 2 == 0:
        items.append(prop("weapon-rack", 0.8, -1.0, scale=0.88, layer="mid"))
    return items


def hall_props(scene_index: int) -> list[dict]:
    return [
        prop("wall-window", -3.8, -1.0, scale=0.92, layer="back"),
        prop("weapon-rack" if scene_index % 2 == 0 else "training-drum", 0.0, -1.02, scale=0.92, layer="mid"),
        prop("lantern", 3.7, -0.92, scale=0.92, layer="front"),
    ]


def camp_audio(*, metal: bool = False, boom: bool = False, extra_boom: bool = False) -> dict:
    sfx = [audio_sfx(FIST_AUDIO, start_ms=4200, volume=0.44)]
    if metal:
        sfx.append(audio_sfx(METAL_AUDIO, start_ms=8200, volume=0.42))
    if boom:
        sfx.append(audio_sfx(BOOM_AUDIO, start_ms=10800, volume=0.48))
    if extra_boom:
        sfx.append(audio_sfx(BOOM_AUDIO, start_ms=6200, volume=0.34))
    return scene_audio(sfx=sfx)


def scene_bgm(scene_index: int, *, battle: bool) -> dict:
    path = BATTLE_BGM if battle else DIALOGUE_BGM
    volume = 0.62 if battle else 0.48
    return audio_bgm(path, volume=volume, loop=True)


SCENE_SPECS = [
    SceneSpec(
        scene_id="scene-001",
        background="mountain-cliff",
        summary="北岸大营灯火压江，曹操自恃兵锋正盛，认定一战便可压垮江东。",
        actors=[
            front_actor("cao_cao", -1.8, facing="right"),
            front_actor("messenger", 2.5, facing="left", scale=0.9),
        ],
        props=river_props(0, night=True),
        lines=[
            line("narrator", "建安十三年冬，北军南下，长江风声里，全营都在等一场定天下的大火。"),
            line("cao_cao", "江东舟楫虽多，终究不过一江之险，我若一举渡江，天下再无人敢言抗衡。"),
            line("messenger", "丞相，前线回报，东吴主战已定，周瑜亲自总督水军。"),
            line("cao_cao", "周瑜再锐，也不过是吴地一将，他若来战，我正好拿他祭旗。"),
        ],
    ),
    SceneSpec(
        scene_id="scene-002",
        background="town-hall-records",
        summary="建业议战，孙权终于拍板主战，周瑜与鲁肃当场接下军令。",
        actors=[
            front_actor("sun_quan", -2.2, facing="right"),
            front_actor("zhou_yu", 0.1, facing="left"),
            front_actor("lu_su", 2.6, facing="left", scale=0.94),
        ],
        props=hall_props(1),
        lines=[
            line("sun_quan", "曹操号称八十万，实则恃胜南来。朕只问一句，江东到底能不能战。"),
            line("zhou_yu", "能战，而且必须战。若让北军踏过长江，江东再无转身之地。"),
            line("lu_su", "主公若定主战，我愿连夜整船点粮，把三军心思全拧到一处。"),
            line("sun_quan", "好，孤今日断江东后路，主战之策，就由公瑾亲自去打出来。"),
        ],
    ),
    SceneSpec(
        scene_id="scene-003",
        background="inn-hall",
        summary="周瑜与诸葛亮初见，二人言语平静，实则句句都在试探对方的底牌。",
        actors=[
            front_actor("zhou_yu", -2.2, facing="right"),
            front_actor("zhuge_liang", 2.2, facing="left"),
            mid_actor("lu_su", 0.0, facing="left", scale=0.9),
        ],
        props=hall_props(2),
        lines=[
            line("zhou_yu", "诸葛先生远来，既为联吴抗曹，就该直说，刘备究竟能出多少兵。"),
            line("zhuge_liang", "兵不在多，在于敢不敢跟曹操在江面上赌一回天时。"),
            line("lu_su", "两位都别只试对方口风，眼下最紧的，是先把曹军拖进我们想要的水面。"),
            line("zhou_yu", "好，那就看先生的天时，与我江东的水战，到底能不能扣成一环。"),
        ],
    ),
    SceneSpec(
        scene_id="scene-004",
        background="training-ground",
        summary="黄盖请行苦肉计，周瑜咬牙同意，军中从这一刻起再无退路。",
        actors=[
            front_actor("zhou_yu", -2.3, facing="right"),
            front_actor("huang_gai", 2.1, facing="left"),
            mid_actor("xiao_qiao", 3.5, facing="left", scale=0.9),
        ],
        props=[
            prop("training-drum", -3.6, -1.08, scale=0.94, layer="back"),
            prop("weapon-rack", 3.7, -1.03, scale=0.92, layer="mid"),
        ],
        lines=[
            line("huang_gai", "要烧曹营，先得让他信我是真降。这一顿军棍，我来挨。"),
            line("zhou_yu", "老将军一身战伤还没愈，若再演这一场，稍有不慎就真回不来了。"),
            line("huang_gai", "大敌在前，还顾什么老命。公瑾，你只管打，我替你把火送进曹操船心。"),
            line("xiao_qiao", "既然此局只能往前，那便别让将士看见迟疑，今夜所有人都得相信这一场是真的。"),
        ],
    ),
    SceneSpec(
        scene_id="scene-005",
        background="archive-library",
        summary="曹操收到黄盖降书，自负与轻敌一齐抬头，连营之策也随之定下。",
        actors=[
            front_actor("cao_cao", -2.1, facing="right"),
            front_actor("messenger", 2.5, facing="left", scale=0.9),
        ],
        props=hall_props(4),
        lines=[
            line("messenger", "丞相，黄盖密书已到，说周瑜性急多疑，他愿率蒙冲斗舰前来归降。"),
            line("cao_cao", "黄盖是吴中老将，若真来降，正好替我敲开江东的第一道门。"),
            line("narrator", "大营里有人劝疑，有人劝信，而曹操最信的，始终是自己一路胜来的判断。"),
            line("cao_cao", "传令下去，水军诸部整肃阵列。既然江东要送船来，我便连船等他。"),
        ],
    ),
    SceneSpec(
        scene_id="scene-006",
        background="night-bridge",
        summary="北军连环锁船，江面上密如长城，看似稳固，实则也把火路一并锁死。",
        actors=[
            front_actor("cao_cao", -2.0, facing="right"),
            front_actor("messenger", 2.1, facing="left", scale=0.9),
        ],
        props=river_props(5, night=True),
        lines=[
            line("cao_cao", "北兵多不习水，把船锁在一处，摇晃既定，军心便能定。"),
            line("messenger", "可是丞相，若江上起火，这锁船之策，恐怕也不容易散开。"),
            line("cao_cao", "冬月江南少有东风，周瑜若想烧我，先得问天肯不肯。"),
            line("narrator", "连环铁索入水时，曹营欢声大起，却没人想到，越稳的阵，也越难转身。"),
        ],
    ),
    SceneSpec(
        scene_id="scene-007",
        background="mountain-cliff",
        summary="南屏山上风色细转，诸葛亮与周瑜都在等同一阵风，只是谁也不肯先说破。",
        actors=[
            front_actor("zhuge_liang", -2.3, facing="right"),
            front_actor("zhou_yu", 2.0, facing="left"),
            mid_actor("lu_su", 0.0, facing="left", scale=0.9),
        ],
        props=river_props(6, night=True),
        lines=[
            line("zhuge_liang", "江风昼夜多变，真正能决定今夜胜负的，未必是刀枪，反倒是这一口风。"),
            line("zhou_yu", "我不怕你借风成名，我只怕风到时，我的火船还没到该到的位置。"),
            line("lu_su", "两位都别再吊着彼此。东风若起，黄盖就得立刻离岸，半刻都拖不得。"),
            line("zhou_yu", "放心，风一转，我这边的鼓声会比江面更快。"),
        ],
    ),
    SceneSpec(
        scene_id="scene-008",
        background="training-ground",
        summary="东吴点将，孙权亲临阅军，黄盖、周瑜、鲁肃各自把最后一环咬死。",
        actors=[
            front_actor("sun_quan", -2.4, facing="right"),
            front_actor("zhou_yu", -0.3, facing="right"),
            front_actor("huang_gai", 2.1, facing="left"),
            mid_actor("lu_su", 3.6, facing="left", scale=0.9),
        ],
        props=[
            prop("training-drum", -3.6, -1.08, scale=0.96, layer="back"),
            prop("weapon-rack", 0.0, -1.02, scale=0.92, layer="mid"),
            prop("lantern", 3.8, -0.92, scale=0.92, layer="front"),
        ],
        lines=[
            line("sun_quan", "今夜不论东风早晚，江东诸将都只能进，不能退。"),
            line("zhou_yu", "水寨鼓一响，前军推火船，中军压弓弩，后军接长槊，层层咬住曹营。"),
            line("huang_gai", "末将只求一点，火船撞上之前，谁都别替我回头。"),
            line("lu_su", "粮船、箭船、退路，全给你们留好了。今晚不是试探，是决战。"),
        ],
    ),
    SceneSpec(
        scene_id="scene-009",
        background="night-bridge",
        summary="东风终于翻过江面，周瑜抬头一笑，整片水寨同时动了起来。",
        actors=[
            front_actor("zhou_yu", -2.1, facing="right"),
            front_actor("zhuge_liang", 2.0, facing="left"),
            mid_actor("lu_su", 0.1, facing="left", scale=0.9),
        ],
        props=river_props(8, night=True),
        lines=[
            line("narrator", "三更过后，江面风向忽转，原本贴着北岸的冷风，陡然一寸一寸倒向曹营。"),
            line("zhou_yu", "东风到了。传旗，起火船。"),
            line("zhuge_liang", "公瑾，今夜天时到了你手里，剩下的，就看江东诸将敢不敢把命一并押上。"),
            line("zhou_yu", "今夜押的不是命，是江东百年江山。"),
        ],
    ),
    SceneSpec(
        scene_id="scene-010",
        background="night-bridge",
        summary="黄盖率火船离岸，船头蒙着降旗，船腹里却全是浸满油脂的火具。",
        actors=[
            front_actor("huang_gai", -2.2, facing="right"),
            front_actor("zhou_yu", 2.0, facing="left"),
            mid_actor("lu_su", 3.6, facing="left", scale=0.88),
        ],
        props=river_props(9, night=True),
        lines=[
            line("huang_gai", "降旗挂正，舱门封死。等我冲到阵前，再把火一齐放出来。"),
            line("zhou_yu", "记住，船头一旦贴上曹营，别恋战，立刻换小舟脱身。"),
            line("lu_su", "后队弓弩已经压着，老将军只要把第一把火送进去，整片江面都会替你接上。"),
            line("huang_gai", "我这一生见过多少硬仗，今夜这一下，算我替江东砸开的门。"),
        ],
        extra_beats=[
            beat(7800, 11600, "huang_gai", "enter", x0=-2.6, x1=0.4, facing="right", emotion="charged"),
        ],
        audio=camp_audio(extra_boom=True),
    ),
    SceneSpec(
        scene_id="scene-011",
        background="mountain-cliff",
        summary="曹营望见降旗，仍只当黄盖真心来投，连巡江船都没有立刻压上去。",
        actors=[
            front_actor("cao_cao", -2.2, facing="right"),
            front_actor("messenger", 2.2, facing="left", scale=0.9),
        ],
        props=river_props(10, night=True),
        lines=[
            line("messenger", "丞相，前面有吴船打着降旗，队形散而不乱，正顺东风直向水寨而来。"),
            line("cao_cao", "黄盖果然来了。传令，前军让出一线水门，别误伤了投诚船只。"),
            line("messenger", "丞相，船速似乎比寻常快得多。"),
            line("cao_cao", "东风送帆，自然更快。你们只管看着，我今夜要亲眼看江东第一员老将是怎么来降的。"),
        ],
    ),
    SceneSpec(
        scene_id="scene-012",
        background="theatre-stage",
        summary="火船逼近水门，黄盖一声令下，船腹中的火线同时被点燃。",
        actors=[
            front_actor("huang_gai", -2.1, facing="right"),
            front_actor("cao_cao", 2.1, facing="left"),
            mid_actor("messenger", 3.5, facing="left", scale=0.88),
        ],
        props=[
            prop("star", -3.8, -0.55, scale=0.52, layer="back"),
            prop("moon", 3.8, -0.42, scale=0.72, layer="back"),
            prop("weapon-rack", 0.0, -1.0, scale=0.9, layer="mid"),
        ],
        lines=[
            line("huang_gai", "诸船听令，点火，撞寨。"),
            line("messenger", "丞相，火，火从船腹里窜出来了，他们不是来降，是来烧营。"),
            line("cao_cao", "立刻断索，退船，快把前面那几艘撞开。"),
            line("huang_gai", "现在才想退，已经晚了。"),
        ],
        extra_beats=[
            beat(7600, 10900, "huang_gai", "dragon-palm", x0=-1.8, x1=0.7, facing="right", effect="dragon-palm"),
            beat(10900, 13800, "cao_cao", "exit", x0=2.0, x1=3.6, facing="right", emotion="hurt"),
        ],
        effects=[
            effect("dragon-palm", start_ms=7600, end_ms=11100, alpha=0.24, playback_speed=0.88),
            effect("thunder-strike", start_ms=9800, end_ms=13600, alpha=0.22, playback_speed=0.80),
        ],
        audio=camp_audio(boom=True),
    ),
    SceneSpec(
        scene_id="scene-013",
        background="theatre-stage",
        summary="连环锁船在烈火里失去回旋，整片北军水寨很快被烧成一条火龙。",
        actors=[
            front_actor("cao_cao", 2.2, facing="left"),
            mid_actor("messenger", -0.2, facing="right", scale=0.92),
            mid_actor("huang_gai", -2.8, facing="right", scale=0.92),
        ],
        props=[
            prop("moon", 3.8, -0.42, scale=0.70, layer="back"),
            prop("star", -3.7, -0.56, scale=0.52, layer="back"),
        ],
        lines=[
            line("narrator", "火借风势，风助船势，火船一贴上锁链，整列战船便像被同一把火舌同时舔开。"),
            line("cao_cao", "不要乱，先断中段铁索，再用小舟拖开两翼。"),
            line("messenger", "丞相，索断不开，前后都是火，弟兄们连跳水都找不到缝。"),
            line("narrator", "曹营的号令仍在江上回响，可火比号令更快。"),
        ],
        effects=[
            effect("thunder-strike", start_ms=2400, end_ms=8800, alpha=0.24, playback_speed=0.76),
            effect("dragon-palm", start_ms=5600, end_ms=11800, alpha=0.26, playback_speed=0.84),
            effect("sword-arc", start_ms=8200, end_ms=14000, alpha=0.22, playback_speed=0.90),
        ],
        audio=camp_audio(metal=True, boom=True, extra_boom=True),
    ),
    SceneSpec(
        scene_id="scene-014",
        background="training-ground",
        summary="周瑜立在中军鼓下，一声令下，江东各路战船齐齐压向火后的缺口。",
        actors=[
            front_actor("zhou_yu", -2.2, facing="right"),
            front_actor("zhuge_liang", 2.1, facing="left"),
            mid_actor("lu_su", 0.1, facing="left", scale=0.9),
        ],
        props=[
            prop("training-drum", -3.6, -1.08, scale=0.98, layer="back"),
            prop("weapon-rack", 3.6, -1.02, scale=0.92, layer="mid"),
        ],
        lines=[
            line("zhou_yu", "前军压火口，中军破侧翼，后军截退路，谁也不准放曹船整列逃开。"),
            line("lu_su", "鼓旗已经传满江面，左右两翼都在往火后缺口挤。"),
            line("zhuge_liang", "火只是敲门，真正取胜的，还是你这一阵总攻。"),
            line("zhou_yu", "那就让曹操今晚记住，江东水军真正杀到的时候，火不过是个开场。"),
        ],
        extra_beats=[
            beat(8200, 11800, "zhou_yu", "sword-arc", x0=-2.0, x1=0.3, facing="right", effect="sword-arc"),
        ],
        effects=[effect("sword-arc", start_ms=8200, end_ms=12000, alpha=0.22, playback_speed=0.92)],
        audio=camp_audio(metal=True),
    ),
    SceneSpec(
        scene_id="scene-015",
        background="night-bridge",
        summary="江面正式短兵相接，黄盖从火里杀出，周瑜的中军也压到了近前。",
        actors=[
            front_actor("huang_gai", -2.0, facing="right"),
            front_actor("zhou_yu", 0.1, facing="right"),
            front_actor("cao_cao", 2.5, facing="left"),
        ],
        props=river_props(14, night=True),
        lines=[
            line("huang_gai", "火已经进去了，剩下的路，就用刀给我砍开。"),
            line("zhou_yu", "前面那艘大船就是中军，给我贴上去，别让曹操把队伍重新拢起来。"),
            line("cao_cao", "弓弩手压住火后水面，重兵护住中军大旗，不能让江东在混乱里凿穿。"),
            line("narrator", "火海之外，真正决定胜败的近身冲杀，此刻才刚刚开始。"),
        ],
        extra_beats=[
            beat(3600, 7200, "huang_gai", "dragon-palm", x0=-1.9, x1=0.2, facing="right", effect="dragon-palm"),
            beat(7600, 10800, "zhou_yu", "sword-arc", x0=-0.2, x1=1.0, facing="right", effect="sword-arc"),
            beat(10800, 13600, "cao_cao", "exit", x0=2.4, x1=3.8, facing="right", emotion="hurt"),
        ],
        effects=[
            effect("dragon-palm", start_ms=3600, end_ms=7400, alpha=0.22, playback_speed=0.86),
            effect("sword-arc", start_ms=7600, end_ms=11200, alpha=0.22, playback_speed=0.92),
            effect("thunder-strike", start_ms=9800, end_ms=13800, alpha=0.22, playback_speed=0.80),
        ],
        audio=camp_audio(metal=True, boom=True, extra_boom=True),
    ),
    SceneSpec(
        scene_id="scene-016",
        background="street-day",
        summary="曹操弃船登岸，带着残兵向乌林方向收拢，嘴上仍强撑着不肯承认败局。",
        actors=[
            front_actor("cao_cao", -2.1, facing="right"),
            front_actor("messenger", 2.0, facing="left", scale=0.9),
        ],
        props=river_props(15),
        lines=[
            line("messenger", "丞相，江上阵列已全乱了，再守水面，只会被火和吴军一起吞掉。"),
            line("cao_cao", "弃船走岸，先保中军。胜负未尽定，先退一步，不等于认输。"),
            line("messenger", "可是火线已经追到后军，弟兄们都在问，还能不能回头收拢。"),
            line("cao_cao", "回头只会再被火吞一次。告诉他们，谁能活着走出乌林，谁就是今天真正的赢。"),
        ],
        extra_beats=[
            beat(8600, 13600, "cao_cao", "exit", x0=-1.8, x1=1.8, facing="right", emotion="hurt"),
            beat(9000, 13800, "messenger", "exit", x0=1.9, x1=3.7, facing="right", emotion="hurt"),
        ],
        audio=camp_audio(extra_boom=True),
    ),
    SceneSpec(
        scene_id="scene-017",
        background="park-evening",
        summary="乌林追击仍在继续，周瑜顾不上火光刺眼，只想把曹军彻底压散在退路上。",
        actors=[
            front_actor("zhou_yu", -2.1, facing="right"),
            front_actor("huang_gai", 0.1, facing="right"),
            front_actor("cao_cao", 2.5, facing="left"),
        ],
        props=river_props(16, night=True),
        lines=[
            line("zhou_yu", "别给他收拾残兵的空档，乌林路窄，只要再压一阵，他就只能一路丢甲弃旗。"),
            line("huang_gai", "前面那支残兵已经乱了，我带轻舟再插一次，把他后队整个掀开。"),
            line("cao_cao", "稳住后军，别让他们看见吴军的旗就自己先散。"),
            line("narrator", "火后的追击没有壮阔阵形，只有一支又一支残破战船，在黑水里把退路越挤越窄。"),
        ],
        extra_beats=[
            beat(3800, 7200, "huang_gai", "dragon-palm", x0=-0.1, x1=1.1, facing="right", effect="dragon-palm"),
            beat(7600, 10800, "zhou_yu", "sword-arc", x0=-1.8, x1=0.6, facing="right", effect="sword-arc"),
            beat(10800, 13600, "cao_cao", "exit", x0=2.4, x1=3.9, facing="right", emotion="hurt"),
        ],
        effects=[
            effect("dragon-palm", start_ms=3800, end_ms=7600, alpha=0.22, playback_speed=0.88),
            effect("sword-arc", start_ms=7600, end_ms=11200, alpha=0.22, playback_speed=0.92),
        ],
        audio=camp_audio(metal=True, boom=True),
    ),
    SceneSpec(
        scene_id="scene-018",
        background="temple-courtyard",
        summary="大战一夜后，周瑜身上伤口裂开，却仍坐在军前清点得失，不许任何人先说松懈。",
        actors=[
            front_actor("zhou_yu", -2.2, facing="right"),
            front_actor("lu_su", 0.2, facing="left"),
            front_actor("xiao_qiao", 2.5, facing="left", scale=0.92),
        ],
        props=[
            prop("training-drum", -3.7, -1.08, scale=0.94, layer="back"),
            prop("lantern", 3.6, -0.92, scale=0.94, layer="front"),
            prop("house", 0.0, -1.1, scale=0.88, layer="back"),
        ],
        lines=[
            line("lu_su", "公瑾，前军回报，北军主力已经退散，江面火势也在收尾。"),
            line("zhou_yu", "还不算完，先把残火隔开，再把俘船和粮船一并清点，不能让胜仗变成乱仗。"),
            line("xiao_qiao", "你一夜没合眼，连伤口都又崩开了，还要硬撑到什么时候。"),
            line("zhou_yu", "等把今夜每一条船、每一名将士都安顿好，我再谈痛不痛。"),
        ],
    ),
    SceneSpec(
        scene_id="scene-019",
        background="town-hall-records",
        summary="孙权闻捷，亲自议功，周瑜却把最大一句话留给了江面，而不是留在殿上。",
        actors=[
            front_actor("sun_quan", -2.4, facing="right"),
            front_actor("zhou_yu", 0.0, facing="left"),
            front_actor("zhuge_liang", 2.4, facing="left"),
            mid_actor("lu_su", 3.8, facing="left", scale=0.88),
        ],
        props=hall_props(18),
        lines=[
            line("sun_quan", "这一战之后，曹操南下之锋已折。江东能守住长江，诸位都当记首功。"),
            line("zhou_yu", "臣不敢独受。若无主公定战、子敬联络、孔明断风，此局也扣不成今晚这一把火。"),
            line("zhuge_liang", "公瑾不必谦。火可以借风，阵却借不了。今夜真正压垮曹军的，是你把火后总攻接得太快。"),
            line("sun_quan", "既然大局已定，那就让天下从今日起知道，长江不是谁来都能跨过去。"),
        ],
    ),
    SceneSpec(
        scene_id="scene-020",
        background="park-evening",
        summary="江头风定，火光只剩零星反照。周瑜与诸葛亮并立远望，都知道此战只是乱世长卷的一页。",
        actors=[
            front_actor("zhou_yu", -2.1, facing="right"),
            front_actor("zhuge_liang", 2.0, facing="left"),
            mid_actor("narrator", 0.0, facing="right", scale=0.84, z=-0.9),
        ],
        props=river_props(19, night=True),
        lines=[
            line("narrator", "赤壁火熄之后，长江仍旧向东，江面没替谁停下，乱世也不会因为一场大胜就立刻归于平静。"),
            line("zhou_yu", "今夜我赢的是这一江火，可天下往后怎么走，仍旧步步都要再争。"),
            line("zhuge_liang", "能在乱世里先守住一口气，已经是难得胜局。其余的，留给往后的风去吹。"),
            line("narrator", "于是这一夜的火，既照亮了江水，也照亮了后来许多年反复被人回望的历史。"),
        ],
    ),
]


class RedCliffsNightBattleVideo(BaseVideoScript):
    def get_title(self) -> str:
        return "赤壁夜战"

    def get_theme(self) -> str:
        return "历史、三国、赤壁、谋略、火攻、夜战"

    def get_cast(self) -> list[dict]:
        return CAST

    def get_video_options(self) -> dict:
        return VIDEO

    def has_tts(self) -> bool:
        return True

    def get_notes(self) -> dict:
        return {
            "scene_count": len(SCENE_SPECS),
            "format": "history-red-cliffs-night-battle",
            "bgm_assets": [DIALOGUE_BGM, BATTLE_BGM],
        }

    def get_default_output(self) -> str:
        return "outputs/red_cliffs_night_battle.mp4"

    def get_description(self) -> str:
        return "Render a rich historical war story about the Battle of Red Cliffs with dialogue, combat, BGM, effects, and dense sound design."

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
                    props=spec.props,
                    actors=spec.actors,
                    beats=beats,
                    expressions=expressions_sorted,
                    dialogues=dialogue_items,
                    audio=audio_payload,
                )
            )
        return scenes


SCRIPT = RedCliffsNightBattleVideo()


def build_story() -> dict:
    return SCRIPT.build_story()


def main() -> int:
    return SCRIPT()


if __name__ == "__main__":
    raise SystemExit(main())
