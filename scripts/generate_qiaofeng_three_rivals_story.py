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
        "effect_overlay_alpha": 0.42,
    },
}

CAST = [
    cast_member("qiao_feng", "乔峰", "general-guard"),
    cast_member("azi", "阿紫", "npc-girl"),
    cast_member("ding", "星宿老怪", "official-minister"),
    cast_member("zhuang", "庄聚贤", "detective-sleek"),
    cast_member("murong_fu", "慕容复", "strategist"),
    cast_member("crowd_guard", "群雄喽啰", "npc-boy"),
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
    "street-day": "stone-court",
}

FIST_AUDIO = "assets/audio/031_26_赤手空拳打斗的声音_爱给网_aigei_com.mp3"
METAL_AUDIO = "assets/audio/刀剑、金属碰撞（带回音）_爱给网_aigei_com.mp3"
BOOM_AUDIO = "assets/audio/音效 爆炸 爆破 爆发 战斗_爱给网_aigei_com.mp3"
EXCLUSIVE_BGM = "assets/bgm/乔峰专属bgm.mp3"


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


def infer_expression(text: str) -> str:
    if any(token in text for token in ("毒", "杀", "掌", "退", "破", "围", "战")):
        return "fierce"
    if any(token in text for token in ("快", "小心", "当心", "后退")):
        return "excited"
    if any(token in text for token in ("算计", "联手", "路数", "真气", "局面")):
        return "thinking"
    if any(token in text for token in ("果然", "体面", "可笑", "不过")):
        return "smirk"
    return "neutral"


def build_dialogue_bundle(lines: Sequence[DialogueLine]) -> tuple[list[dict], list[dict], list[dict]]:
    dialogue_items: list[dict] = []
    talk_beats: list[dict] = []
    expressions: list[dict] = []
    for (start_ms, end_ms), (speaker_id, text) in zip(DIALOGUE_WINDOWS, lines):
        dialogue_items.append(dialogue(start_ms, end_ms, speaker_id, text))
        talk_beats.append(beat(start_ms, end_ms, speaker_id, "talk", emotion="focused"))
        expressions.append(expression(speaker_id, start_ms, end_ms, infer_expression(text)))
    return dialogue_items, talk_beats, expressions


def scene_camera(scene_index: int) -> dict:
    if scene_index in {3, 6, 8}:
        return camera_static(x=0.0, z=0.04, zoom=1.08)
    return camera_pan(
        x=-0.24 + 0.05 * (scene_index % 3),
        z=0.04,
        zoom=1.02,
        to_x=0.20 - 0.04 * (scene_index % 2),
        to_z=0.01,
        to_zoom=1.09 + 0.01 * (scene_index % 3),
        ease="ease-in-out",
    )


def wuxia_props(scene_index: int, *, interior: bool = False, night: bool = False) -> list[dict]:
    if interior:
        return [
            prop("wall-window", -3.8, -1.0, scale=0.9, layer="back"),
            prop("weapon-rack" if scene_index % 2 == 0 else "training-drum", 0.0, -1.04, scale=0.92, layer="mid"),
            prop("lantern", 3.7, -0.92, scale=0.92, layer="front"),
        ]
    items = [prop("house", 0.0, -1.08, scale=1.0, layer="back")]
    if night:
        items.extend(
            [
                prop("moon", 3.8, -0.42, scale=0.74, layer="back"),
                prop("lantern", -3.6, -0.92, scale=0.96, layer="front"),
            ]
        )
    else:
        items.extend(
            [
                prop("horse", -3.7, -0.92, scale=0.84, layer="front"),
                prop("wall-door", 3.7, -1.0, scale=0.92, layer="back"),
            ]
        )
    return items


def combat_audio(*, metal: bool = False, boom: bool = False) -> dict:
    sfx = [audio_sfx(FIST_AUDIO, start_ms=4200, volume=0.48)]
    if metal:
        sfx.append(audio_sfx(METAL_AUDIO, start_ms=8200, volume=0.42))
    if boom:
        sfx.append(audio_sfx(BOOM_AUDIO, start_ms=10800, volume=0.36))
    return scene_audio(sfx=sfx)


def scene_bgm(scene_index: int, *, battle: bool) -> dict:
    return audio_bgm(EXCLUSIVE_BGM, volume=0.44, loop=True)


SCENE_SPECS = [
    SceneSpec(
        scene_id="scene-001",
        background="night-bridge",
        summary="夜桥风紧，阿紫报来消息，说星宿老怪、庄聚贤和慕容复已经在前头布下杀局。",
        actors=[
            front_actor("qiao_feng", -2.3, facing="right"),
            front_actor("azi", 2.2, facing="left", scale=0.92),
        ],
        props=wuxia_props(0, night=True),
        lines=[
            line("azi", "姐夫，前面桥口全是他们的人，星宿老怪、庄聚贤、慕容复，一个都没缺。"),
            line("qiao_feng", "三个人一起等我，倒省得我一处一处去找。"),
            line("azi", "他们摆明了是想车轮耗你，再等你真气一乱一起压上。"),
            line("qiao_feng", "要耗我，也得先看看他们有没有这个本事。"),
        ],
    ),
    SceneSpec(
        scene_id="scene-002",
        background="mountain-cliff",
        summary="星宿老怪先在断崖前现身，张口便要用毒功先废乔峰掌力。",
        actors=[
            front_actor("qiao_feng", -2.2, facing="right"),
            front_actor("ding", 2.3, facing="left", scale=0.98),
            mid_actor("azi", -0.7, facing="right", scale=0.90),
        ],
        props=[
            prop("house", -3.8, -1.08, scale=0.76, layer="back"),
            prop("moon", 3.8, -0.46, scale=0.7, layer="back"),
            prop("lantern", 0.6, -0.92, scale=0.92, layer="front"),
        ],
        lines=[
            line("ding", "乔峰，你掌力再强，也敌不过老仙一口化骨毒雾。"),
            line("qiao_feng", "丁春秋，你一生躲在毒后头，今天总算肯站出来见人了。"),
            line("azi", "老怪物少卖弄，你那点阴毒把戏，我在星宿海早看腻了。"),
            line("ding", "好，先让你们见识见识什么叫沾衣就烂，入骨难医。"),
        ],
        extra_beats=[
            beat(3800, 7600, "ding", "thunder-strike", x0=2.0, x1=0.8, facing="left", effect="thunder-strike"),
            beat(7700, 11000, "qiao_feng", "dragon-palm", x0=-1.9, x1=0.2, facing="right", effect="dragon-palm"),
        ],
        effects=[effect("thunder-strike", start_ms=3900, end_ms=7200, alpha=0.28, playback_speed=0.84)],
        audio=combat_audio(boom=True),
    ),
    SceneSpec(
        scene_id="scene-003",
        background="temple-courtyard",
        summary="毒雾被掌风震散，庄聚贤披着寒气踏入场中，要以冰蚕阴劲正面硬撼乔峰。",
        actors=[
            front_actor("qiao_feng", -2.5, facing="right"),
            front_actor("zhuang", 2.4, facing="left"),
            mid_actor("ding", 3.5, facing="left", scale=0.88),
        ],
        props=[
            prop("training-drum", -3.6, -1.08, scale=0.92, layer="back"),
            prop("weapon-rack", 3.5, -1.02, scale=0.94, layer="mid"),
            prop("lantern", 0.0, -0.92, scale=0.96, layer="front"),
        ],
        lines=[
            line("zhuang", "乔峰，聚贤庄那一战还没完，今天我亲手把你按在这里。"),
            line("qiao_feng", "庄聚贤，你练了一身邪门寒劲，却连自己想做什么都没想明白。"),
            line("ding", "庄帮主别跟他废话，你缠住正面，老仙替你封他退路。"),
            line("zhuang", "不必旁人插嘴，这一掌我自己接，也要自己讨回来。"),
        ],
        extra_beats=[
            beat(3400, 6900, "zhuang", "big-jump", x0=2.4, x1=0.6, facing="left", emotion="charged"),
            beat(7600, 10800, "qiao_feng", "somersault", x0=-2.1, x1=-0.2, facing="right", emotion="charged"),
        ],
        audio=combat_audio(),
    ),
    SceneSpec(
        scene_id="scene-004",
        background="training-ground",
        summary="庄聚贤近身缠斗越逼越紧，乔峰以降龙十八掌硬破其阴寒掌圈。",
        actors=[
            front_actor("qiao_feng", -2.7, facing="right"),
            front_actor("zhuang", 2.3, facing="left"),
            mid_actor("azi", -3.8, facing="right", scale=0.88),
        ],
        props=[
            prop("weapon-rack", -3.6, -1.04, scale=0.96, layer="back"),
            prop("training-drum", 3.6, -1.05, scale=0.92, layer="mid"),
        ],
        lines=[
            line("zhuang", "我不管你过去是谁，今天只要你倒下，我就算赢。"),
            line("qiao_feng", "赢不是靠一口怨气硬撑出来的，你掌路越急，破绽越大。"),
            line("azi", "姐夫，他双臂那股寒劲在回卷，你别和他久耗。"),
            line("qiao_feng", "好，那我就一掌打穿中路，看他还怎么缠。"),
        ],
        extra_beats=[
            beat(3600, 7200, "zhuang", "handstand-walk", x0=2.0, x1=0.7, facing="left", emotion="charged"),
            beat(7600, 10800, "qiao_feng", "dragon-palm", x0=-2.3, x1=0.5, facing="right", effect="dragon-palm"),
        ],
        effects=[effect("dragon-palm", start_ms=7700, end_ms=10900, alpha=0.36, playback_speed=0.88)],
        audio=combat_audio(metal=True),
    ),
    SceneSpec(
        scene_id="scene-005",
        background="park-evening",
        summary="庄聚贤被掌风震退后仍不肯退场，阿紫看出真正等着捡便宜的人其实是慕容复。",
        actors=[
            front_actor("qiao_feng", -2.2, facing="right"),
            front_actor("azi", 0.2, facing="left", scale=0.92),
            front_actor("zhuang", 2.4, facing="left", scale=0.96),
        ],
        props=[
            prop("moon", 3.8, -0.42, scale=0.74, layer="back"),
            prop("lantern", -3.5, -0.92, scale=0.96, layer="front"),
            prop("weapon-rack", 0.0, -1.0, scale=0.9, layer="mid"),
        ],
        lines=[
            line("azi", "你们两个打得热闹，倒把后面那位最会算账的公子给忘了。"),
            line("zhuang", "我先废他，再轮不到慕容复来捡现成。"),
            line("qiao_feng", "你若还有余力，就该先想想自己为什么总被人推到最前面。"),
            line("azi", "他说得对，你出死力，别人却只等你把他磨累。"),
        ],
    ),
    SceneSpec(
        scene_id="scene-006",
        background="town-hall-records",
        summary="慕容复终于现身，言语依旧漂亮，却摆明要等乔峰气机最乱时再出手。",
        actors=[
            front_actor("qiao_feng", -2.4, facing="right"),
            front_actor("murong_fu", 2.3, facing="left"),
            mid_actor("ding", 3.7, facing="left", scale=0.88),
            mid_actor("zhuang", 0.8, facing="left", scale=0.92),
        ],
        props=wuxia_props(5, interior=True),
        lines=[
            line("murong_fu", "乔兄一身豪气，今日却被迫与旁门左道纠缠，实在可惜。"),
            line("qiao_feng", "慕容复，你若真觉得可惜，就别站在后头等着摘果子。"),
            line("murong_fu", "我只是想看看，降龙十八掌在连战之后还能剩几成火候。"),
            line("qiao_feng", "你想试，就别再借别人拖我的气力。"),
        ],
        extra_beats=[
            beat(10400, 13200, "murong_fu", "point", facing="left", emotion="charged"),
        ],
    ),
    SceneSpec(
        scene_id="scene-007",
        background="theatre-stage",
        summary="废戏台上，三人终于一起压上，乔峰独立中央，一掌一掌硬顶三路杀招。",
        actors=[
            front_actor("qiao_feng", -1.8, facing="right"),
            front_actor("ding", 2.4, facing="left", scale=0.98),
            mid_actor("zhuang", 0.7, facing="left", scale=0.94),
            mid_actor("murong_fu", 3.5, facing="left", scale=0.9),
        ],
        props=[
            prop("star", -3.8, -0.55, scale=0.50, layer="back"),
            prop("moon", 3.8, -0.42, scale=0.72, layer="back"),
            prop("weapon-rack", 0.0, -1.0, scale=0.92, layer="mid"),
        ],
        lines=[
            line("ding", "老仙封他上路。"),
            line("zhuang", "我断他中路。"),
            line("murong_fu", "那我便收他回手之后的空门。"),
            line("qiao_feng", "三个人三样心思，居然也敢妄想同一口气压垮我。"),
        ],
        extra_beats=[
            beat(3200, 6400, "ding", "thunder-strike", x0=2.1, x1=0.8, facing="left", effect="thunder-strike"),
            beat(6300, 9200, "zhuang", "big-jump", x0=0.6, x1=-0.2, facing="left", emotion="charged"),
            beat(9300, 10850, "qiao_feng", "dragon-palm", x0=-1.6, x1=0.6, facing="right", effect="dragon-palm"),
            beat(10350, 13800, "murong_fu", "sword-arc", x0=3.1, x1=1.0, facing="left", effect="sword-arc"),
        ],
        effects=[
            effect("thunder-strike", start_ms=3300, end_ms=6200, alpha=0.28, playback_speed=0.82),
            effect("dragon-palm", start_ms=8600, end_ms=12100, alpha=0.38, playback_speed=0.88),
            effect("sword-arc", start_ms=9800, end_ms=13000, alpha=0.34, playback_speed=0.92),
        ],
        audio=combat_audio(metal=True, boom=True),
    ),
    SceneSpec(
        scene_id="scene-008",
        background="hotel-lobby",
        summary="混战挤进回廊，乔峰借狭窄地势先震退星宿老怪，再把庄聚贤逼出战圈。",
        actors=[
            front_actor("qiao_feng", -2.1, facing="right"),
            front_actor("ding", 1.8, facing="left"),
            front_actor("zhuang", 3.0, facing="left", scale=0.94),
            mid_actor("azi", -3.8, facing="right", scale=0.88),
        ],
        props=wuxia_props(7, interior=True),
        lines=[
            line("qiao_feng", "回廊这么窄，你们再多花样，也只能一人一人挨掌。"),
            line("ding", "老仙退一步，不是怕你，是怕沾了你这股蛮劲。"),
            line("zhuang", "你退，我不退，我今天非把这口气争回来。"),
            line("azi", "争什么争，你们两个一个怕正面对掌，一个只会死撑。"),
        ],
        extra_beats=[
            beat(3800, 7200, "qiao_feng", "dragon-palm", x0=-1.9, x1=0.5, facing="right", effect="dragon-palm"),
            beat(10300, 13200, "zhuang", "exit", x0=2.8, x1=3.8, facing="right", emotion="hurt"),
        ],
        effects=[effect("dragon-palm", start_ms=3900, end_ms=7000, alpha=0.34, playback_speed=0.86)],
        audio=combat_audio(),
    ),
    SceneSpec(
        scene_id="scene-009",
        background="street-day",
        summary="最后只剩乔峰与慕容复对立长街，斗转星移与降龙十八掌正面相撞。",
        actors=[
            front_actor("qiao_feng", -2.0, facing="right"),
            front_actor("murong_fu", 2.0, facing="left"),
            mid_actor("azi", -3.6, facing="right", scale=0.88),
        ],
        props=wuxia_props(8),
        lines=[
            line("murong_fu", "乔兄，前面两场不过替我探路，真正该分高下的，终究还是你我。"),
            line("qiao_feng", "你算得精，可惜算不准我这双掌什么时候会打到你身前。"),
            line("azi", "姐夫，小心他借你的力回送过来。"),
            line("qiao_feng", "借得去是他的本事，压得回去才是我的本事。"),
        ],
        extra_beats=[
            beat(3600, 7400, "murong_fu", "sword-arc", x0=1.9, x1=0.5, facing="left", effect="sword-arc"),
            beat(7800, 10800, "qiao_feng", "dragon-palm", x0=-1.6, x1=0.8, facing="right", effect="dragon-palm"),
        ],
        effects=[
            effect("sword-arc", start_ms=3600, end_ms=7200, alpha=0.34, playback_speed=0.9),
            effect("dragon-palm", start_ms=7800, end_ms=11400, alpha=0.40, playback_speed=0.88),
        ],
        audio=combat_audio(metal=True, boom=True),
    ),
    SceneSpec(
        scene_id="scene-010",
        background="park-evening",
        summary="夜风散尽杀气，三人退去，乔峰带着阿紫离开，只把一句不服来日再战留在身后。",
        actors=[
            front_actor("qiao_feng", -2.3, facing="right"),
            front_actor("azi", 2.0, facing="left", scale=0.92),
            mid_actor("murong_fu", 3.5, facing="left", scale=0.88),
        ],
        props=[
            prop("moon", 3.8, -0.42, scale=0.74, layer="back"),
            prop("lantern", -3.6, -0.92, scale=0.96, layer="front"),
            prop("house", 0.0, -1.08, scale=0.92, layer="back"),
        ],
        lines=[
            line("azi", "三个打一个还没留下你，他们今夜这口气怕是咽不下去了。"),
            line("qiao_feng", "咽不下就留着，江湖路长，他们若还想战，随时来找我。"),
            line("murong_fu", "乔兄今日确实打出了威名，只是下一次，未必还有这般运数。"),
            line("qiao_feng", "我从不靠运数站着，靠的是一口气，一双掌，还有不肯退的心。"),
        ],
    ),
]


class QiaoFengThreeRivalsVideo(BaseVideoScript):
    def get_title(self) -> str:
        return "乔峰大战三强敌"

    def get_theme(self) -> str:
        return "武侠、乔峰、星宿老怪、庄聚贤、慕容复、连战围攻"

    def get_cast(self) -> list[dict]:
        return CAST

    def get_video_options(self) -> dict:
        return VIDEO

    def has_tts(self) -> bool:
        return True

    def get_notes(self) -> dict:
        return {
            "scene_count": len(SCENE_SPECS),
            "format": "wuxia-three-rivals",
            "bgm_assets": [EXCLUSIVE_BGM],
        }

    def get_default_output(self) -> str:
        return "outputs/qiaofeng_three_rivals.mp4"

    def get_description(self) -> str:
        return "Render a wuxia story where Qiao Feng battles Ding Chunqiu, Zhuang Juxian, and Murong Fu."

    def get_scenes(self) -> list[dict]:
        scenes: list[dict] = []
        for scene_index, spec in enumerate(SCENE_SPECS):
            dialogue_items, talk_beats, expressions_track = build_dialogue_bundle(spec.lines)
            beats = sorted(
                [*talk_beats, *spec.extra_beats],
                key=lambda item: (item["start_ms"], item["actor_id"]),
            )
            expressions_sorted = sorted(
                expressions_track,
                key=lambda item: (item["start_ms"], item["actor_id"]),
            )
            audio_payload = scene_audio(
                bgm=scene_bgm(scene_index, battle=bool(spec.extra_beats or spec.effects)),
                sfx=list(spec.audio.get("sfx", [])),
            )
            scenes.append(
                scene(
                    spec.scene_id,
                    background=spec.background,
                    floor=FLOOR_BY_BACKGROUND[spec.background],
                    duration_ms=SCENE_DURATION_MS,
                    summary=spec.summary,
                    camera=spec.camera or scene_camera(scene_index),
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


SCRIPT = QiaoFengThreeRivalsVideo()


def build_story() -> dict:
    return SCRIPT.build_story()


def main() -> int:
    return SCRIPT()


if __name__ == "__main__":
    raise SystemExit(main())
