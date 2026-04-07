#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from storyboard import (
    BaseVideoScript,
    actor,
    audio_sfx,
    beat,
    camera_pan,
    camera_static,
    cast_member,
    dialogue,
    effect,
    expression,
    npc_group,
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
        "effect_overlay_alpha": 0.5,
    },
}

CAST = [
    cast_member("shen", "沈行舟", "young-hero"),
    cast_member("ling", "凌秋儿", "swordswoman"),
    cast_member("xie", "谢北溟", "strategist"),
    cast_member("wu_chen", "无尘大师", "master-monk"),
    cast_member("han", "韩总镖头", "farmer-old"),
    cast_member("lu", "陆知府", "official-minister"),
]

SCENE_DURATION_MS = 15_200
DIALOGUE_WINDOWS = [
    (400, 3000),
    (3600, 6200),
    (7600, 10200),
    (11000, 14000),
]

FLOOR_BY_BACKGROUND = {
    "shop-row": "stone-court",
    "inn-hall": "wood-plank",
    "temple-courtyard": "stone-court",
    "training-ground": "stone-court",
    "night-bridge": "dark-stage",
    "mountain-cliff": "stone-court",
    "archive-library": "wood-plank",
    "town-hall-records": "wood-plank",
    "theatre-stage": "dark-stage",
    "park-evening": "dark-stage",
}

FIST_AUDIO = "assets/audio/031_26_赤手空拳打斗的声音_爱给网_aigei_com.mp3"
METAL_AUDIO = "assets/audio/刀剑、金属碰撞（带回音）_爱给网_aigei_com.mp3"
BOOM_AUDIO = "assets/audio/音效 爆炸 爆破 爆发 战斗_爱给网_aigei_com.mp3"


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
    npc_groups: list[dict] = field(default_factory=list)
    audio: dict = field(default_factory=scene_audio)
    camera: dict | None = None


def line(speaker_id: str, text: str) -> DialogueLine:
    return (speaker_id, text)


def front_actor(actor_id: str, x: float, *, facing: str, scale: float = 1.0, z: float = 0.0) -> dict:
    return actor(actor_id, x, z=z, facing=facing, scale=scale)


def mid_actor(actor_id: str, x: float, *, facing: str, scale: float = 0.94, z: float = -0.08) -> dict:
    return actor(actor_id, x, z=z, facing=facing, scale=scale, layer="mid")


def infer_expression(text: str) -> str:
    if any(token in text for token in ("杀", "夺", "逼", "退", "战", "断")):
        return "fierce"
    if any(token in text for token in ("快", "走", "小心", "马上")):
        return "excited"
    if any(token in text for token in ("局", "算", "印", "真假", "机关")):
        return "thinking"
    if any(token in text for token in ("笑", "果然", "不过如此")):
        return "smirk"
    if any(token in text for token in ("稳住", "不必慌", "听我")):
        return "calm"
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
    if scene_index in {4, 8}:
        return camera_static(x=0.0, z=0.04, zoom=1.08)
    return camera_pan(
        x=-0.26 + 0.05 * (scene_index % 3),
        z=0.05,
        zoom=1.01 + 0.02 * (scene_index % 2),
        to_x=0.22 - 0.04 * (scene_index % 2),
        to_z=0.02,
        to_zoom=1.08 + 0.01 * (scene_index % 3),
        ease="ease-in-out",
    )


def wuxia_props(scene_index: int, *, interior: bool, night: bool = False) -> list[dict]:
    if interior:
        return [
            prop("wall-window", -3.8, -1.0, scale=0.9 + 0.03 * (scene_index % 2), layer="back"),
            prop("wall-window", 3.7, -0.95, scale=0.9, layer="back"),
            prop("weapon-rack" if scene_index % 2 == 0 else "lantern", 0.0, -1.05, scale=0.92, layer="mid"),
        ]
    items = [prop("house", 0.0, -1.08, scale=1.0, layer="back")]
    if night:
        items.extend(
            [
                prop("moon", 3.8, -0.42, scale=0.74, layer="back"),
                prop("lantern", -3.5, -0.92, scale=0.98, layer="front"),
            ]
        )
    else:
        items.extend(
            [
                prop("horse", -3.7, -0.9, scale=0.8 + 0.04 * (scene_index % 2), layer="front"),
                prop("wall-door", 3.7, -1.0, scale=0.92, layer="back"),
            ]
        )
    return items


def escort_npcs(scene_id: str, *, asset_ids: list[str], behavior: str, count: int) -> list[dict]:
    return [
        npc_group(
            f"{scene_id}-crowd",
            count=count,
            asset_ids=asset_ids,
            behavior=behavior,
            layer="back",
            watch=True,
            anchor_x=0.0,
            anchor_frontness=-0.12,
            area={"x_min": -4.6, "x_max": 4.6, "front_min": -0.34, "front_max": 0.08},
            scale_min=0.62,
            scale_max=0.82,
        )
    ]


def combat_audio(*, metal: bool = False, boom: bool = False) -> dict:
    sfx = [audio_sfx(FIST_AUDIO, start_ms=4200, volume=0.42)]
    if metal:
        sfx.append(audio_sfx(METAL_AUDIO, start_ms=8400, volume=0.42))
    if boom:
        sfx.append(audio_sfx(BOOM_AUDIO, start_ms=10900, volume=0.34))
    return scene_audio(sfx=sfx)


SCENE_SPECS = [
    SceneSpec(
        scene_id="scene-001",
        background="shop-row",
        summary="暮色压上街口，陆知府把寒江铜匣交给沈行舟，叮嘱他连夜送往山寺。",
        actors=[
            front_actor("shen", -2.5, facing="right"),
            front_actor("lu", 2.4, facing="left"),
            mid_actor("ling", -0.2, facing="right", scale=0.94),
        ],
        props=wuxia_props(0, interior=False),
        lines=[
            line("lu", "寒江铜匣不能落进谢北溟手里，你今晚必须把它送到栖云寺。"),
            line("shen", "一只铜匣竟能惊动知府和江湖两路人，它里面到底藏着什么。"),
            line("ling", "别在街口问，西市已经混进了他的耳目，我们先出城。"),
            line("lu", "记住，匣上三道火漆印若被破开，整座寒江城都会翻脸。"),
        ],
        npc_groups=escort_npcs("scene-001", asset_ids=["npc-boy", "official-minister"], behavior="wander", count=5),
    ),
    SceneSpec(
        scene_id="scene-002",
        background="inn-hall",
        summary="驿馆短暂停脚，谢北溟先礼后兵，开口就要买下寒江铜匣。",
        actors=[
            front_actor("shen", -2.4, facing="right"),
            front_actor("xie", 2.5, facing="left"),
            mid_actor("ling", -0.3, facing="right"),
            mid_actor("han", 1.0, facing="left", scale=0.92),
        ],
        props=wuxia_props(1, interior=True),
        lines=[
            line("xie", "沈少侠，把铜匣交出来，我给你十车黄金，省得今夜刀光见血。"),
            line("shen", "你肯出这么高的价，说明匣里装的不是宝物，而是你不敢见人的旧账。"),
            line("han", "总镖局今晚只认镖令，不认黄金，谢先生还是省些口舌。"),
            line("ling", "他既然来了驿馆，就不会只带嘴来，行舟，准备走后门。"),
        ],
        extra_beats=[
            beat(6300, 8100, "xie", "point", facing="left", emotion="charged"),
            beat(6400, 7400, "ling", "enter", x0=-0.6, x1=0.4, facing="right", emotion="focused"),
        ],
    ),
    SceneSpec(
        scene_id="scene-003",
        background="temple-courtyard",
        summary="栖云寺钟声未歇，无尘大师认出铜匣旧印，劝众人先稳住杀气。",
        actors=[
            front_actor("shen", -2.3, facing="right"),
            front_actor("wu_chen", 2.3, facing="left"),
            mid_actor("ling", -0.4, facing="right"),
        ],
        props=[
            prop("training-drum", -3.6, -1.08, scale=0.92, layer="back"),
            prop("weapon-rack", 3.5, -1.02, scale=0.94, layer="mid"),
            prop("lantern", 0.0, -0.9, scale=0.96, layer="front"),
        ],
        lines=[
            line("wu_chen", "这不是普通镖物，这是二十年前寒江盟封存的问罪匣，里面多半是旧证。"),
            line("shen", "若只是旧证，谢北溟何必一路追杀。"),
            line("ling", "因为他怕的不是纸，是纸上那枚能翻案的掌门血印。"),
            line("wu_chen", "今夜先别开匣，等追兵现身，真伪自会一起浮出水面。"),
        ],
    ),
    SceneSpec(
        scene_id="scene-004",
        background="training-ground",
        summary="寺后练武场忽起埋伏，沈行舟与凌秋儿并肩突围，先打散第一波追兵。",
        actors=[
            front_actor("shen", -2.8, facing="right"),
            front_actor("ling", -0.6, facing="right", scale=0.96),
            front_actor("xie", 2.5, facing="left"),
        ],
        props=[
            prop("weapon-rack", -3.6, -1.06, scale=0.96, layer="back"),
            prop("training-drum", 3.6, -1.06, scale=0.92, layer="mid"),
        ],
        lines=[
            line("xie", "我给过你们离开的价码，现在只剩下把命和铜匣一起留下。"),
            line("shen", "要匣子就亲手来拿，藏在黑衣人后面，只会显得你更心虚。"),
            line("ling", "左边三人交给我，你冲正面，把阵脚先撕开。"),
            line("shen", "好，先破他的前排，再逼他自己露手。"),
        ],
        extra_beats=[
            beat(3200, 7600, "ling", "sword-arc", x0=-0.8, x1=0.5, facing="right", effect="sword-arc"),
            beat(6300, 10600, "shen", "dragon-palm", x0=-2.4, x1=-0.2, facing="right", effect="dragon-palm"),
            beat(9800, 13200, "xie", "exit", x0=2.2, x1=3.1, facing="right", emotion="awkward"),
        ],
        effects=[effect("aura", start_ms=4500, end_ms=7800, alpha=0.22, playback_speed=0.8)],
        npc_groups=escort_npcs("scene-004", asset_ids=["npc-boy", "general-guard"], behavior="guard", count=6),
        audio=combat_audio(metal=True),
    ),
    SceneSpec(
        scene_id="scene-005",
        background="night-bridge",
        summary="寒桥窄如刀背，谢北溟拦在桥心，要沈行舟当众开匣验印。",
        actors=[
            front_actor("shen", -2.2, facing="right"),
            front_actor("xie", 2.2, facing="left"),
            mid_actor("ling", -0.8, facing="right"),
        ],
        props=wuxia_props(4, interior=False, night=True),
        lines=[
            line("xie", "就在桥上开匣，让所有人看清里面只有一页废纸，你还护什么。"),
            line("shen", "你急着在桥上动手，不是为验印，是怕天一亮，城里的人都知道你在追什么。"),
            line("ling", "桥面太窄，他想逼你一手护匣一手接招，千万别顺他的步子。"),
            line("shen", "那就让他先退，我今天偏在桥心站稳。"),
        ],
        extra_beats=[
            beat(6200, 9800, "xie", "thunder-strike", x0=2.0, x1=0.7, facing="left", effect="thunder-strike"),
            beat(6300, 10600, "shen", "somersault", x0=-1.8, x1=0.2, facing="right", emotion="charged"),
        ],
        effects=[effect("thunder-strike", start_ms=6400, end_ms=9400, alpha=0.34, playback_speed=0.88)],
        audio=combat_audio(boom=True),
    ),
    SceneSpec(
        scene_id="scene-006",
        background="mountain-cliff",
        summary="追兵逼到断崖，韩总镖头用旧伤换来一线空档，把开匣铜钥交给沈行舟。",
        actors=[
            front_actor("shen", -2.4, facing="right"),
            front_actor("han", 0.0, facing="right", scale=0.94),
            front_actor("xie", 2.5, facing="left"),
            mid_actor("ling", -1.0, facing="right"),
        ],
        props=[
            prop("house", -3.8, -1.1, scale=0.78, layer="back"),
            prop("moon", 3.8, -0.46, scale=0.68, layer="back"),
            prop("lantern", 0.8, -0.92, scale=0.9, layer="front"),
        ],
        lines=[
            line("han", "铜匣的钥匙一直在我身上，陆知府不肯明说，就是怕有人先动我这把老骨头。"),
            line("xie", "韩总镖头，你守了二十年秘密，今天也该交班了。"),
            line("shen", "钥匙给我，你退后，这道崖口我替你守。"),
            line("han", "拿稳它，匣子一开，先被审的不是死人，是还活着的人。"),
        ],
        extra_beats=[
            beat(6400, 9400, "han", "point", facing="right", emotion="charged"),
            beat(10300, 13600, "shen", "big-jump", x0=-2.0, x1=0.6, facing="right", emotion="charged"),
        ],
        npc_groups=escort_npcs("scene-006", asset_ids=["npc-boy", "farmer-old"], behavior="guard", count=5),
        audio=combat_audio(),
    ),
    SceneSpec(
        scene_id="scene-007",
        background="archive-library",
        summary="藏经阁内烛影摇动，铜匣终于启封，里面不是秘籍，而是一卷寒江盟清洗名单。",
        actors=[
            front_actor("shen", -2.2, facing="right"),
            front_actor("wu_chen", 2.3, facing="left"),
            mid_actor("ling", -0.4, facing="right"),
        ],
        props=wuxia_props(6, interior=True),
        lines=[
            line("wu_chen", "名册上的最后一笔，是寒江盟前任掌门亲手写下的逐杀令，谢北溟就在执行者之列。"),
            line("shen", "难怪他非抢不可，这卷名册不是赃物，是能把整段旧案倒过来的刀。"),
            line("ling", "再看页角，这里还有陆家的火漆对印，说明知府这一脉一直在暗中保这份证据。"),
            line("wu_chen", "你们现在不能再逃，必须回城，当众把名单念出来。"),
        ],
    ),
    SceneSpec(
        scene_id="scene-008",
        background="town-hall-records",
        summary="回到衙署旧档房，陆知府摆出官印和旧卷，要在众目之下对证寒江旧案。",
        actors=[
            front_actor("lu", 2.4, facing="left"),
            front_actor("shen", -2.4, facing="right"),
            mid_actor("ling", -0.2, facing="right"),
            mid_actor("xie", 1.0, facing="left"),
        ],
        props=wuxia_props(7, interior=True),
        lines=[
            line("lu", "旧档、官印、寒江盟血印，三样都在这儿，谢北溟，你还想说这是伪造么。"),
            line("xie", "二十年前死人太多，谁还能分得清哪一枚印是真的，哪一句供词是逼出来的。"),
            line("shen", "你不敢否认自己名字在名册上，只敢拖着所有死人一起替你背黑锅。"),
            line("ling", "城中各门派的人都在门外，你若还想翻口，只能靠手里的剑。"),
        ],
        extra_beats=[
            beat(10400, 13200, "xie", "point", facing="left", emotion="charged"),
        ],
        npc_groups=escort_npcs("scene-008", asset_ids=["official-minister", "npc-boy"], behavior="wander", count=6),
    ),
    SceneSpec(
        scene_id="scene-009",
        background="theatre-stage",
        summary="废戏台成了最后的公证场，谢北溟撕下面皮，与沈行舟在满城目光里决战。",
        actors=[
            front_actor("shen", -2.0, facing="right"),
            front_actor("xie", 2.0, facing="left"),
            mid_actor("ling", -3.1, facing="right", scale=0.88),
            mid_actor("wu_chen", 3.1, facing="left", scale=0.88),
        ],
        props=[
            prop("star", -3.8, -0.55, scale=0.5, layer="back"),
            prop("moon", 3.8, -0.4, scale=0.7, layer="back"),
            prop("weapon-rack", 0.0, -1.0, scale=0.92, layer="mid"),
        ],
        lines=[
            line("xie", "既然你们非要翻旧案，我就先把能开口的人都斩在这座戏台上。"),
            line("shen", "你当年靠夜里灭口坐上今天的位置，今天也该在众人眼前把债还清。"),
            line("wu_chen", "此战不为争名，只为让寒江盟死去的人有个明白。"),
            line("ling", "行舟，别被他拖进消耗战，第三招后他一定会强行换步。"),
        ],
        extra_beats=[
            beat(3600, 7600, "xie", "sword-arc", x0=1.8, x1=0.4, facing="left", effect="sword-arc"),
            beat(7600, 10800, "shen", "dragon-palm", x0=-1.6, x1=0.6, facing="right", effect="dragon-palm"),
            beat(10800, 13600, "xie", "thunder-strike", x0=0.5, x1=-0.1, facing="left", effect="thunder-strike"),
        ],
        effects=[
            effect("aura", start_ms=3400, end_ms=6200, alpha=0.18, playback_speed=0.72),
            effect("dragon-palm", start_ms=7600, end_ms=10800, alpha=0.4, playback_speed=0.9),
        ],
        audio=combat_audio(metal=True, boom=True),
    ),
    SceneSpec(
        scene_id="scene-010",
        background="park-evening",
        summary="夜风吹散江边灯影，旧案昭雪，沈行舟把空铜匣重新封好，留给后人记住这一夜。",
        actors=[
            front_actor("shen", -2.3, facing="right"),
            front_actor("ling", 2.1, facing="left", scale=0.96),
            mid_actor("wu_chen", 0.1, facing="left", scale=0.92),
        ],
        props=[
            prop("moon", 3.8, -0.42, scale=0.76, layer="back"),
            prop("lantern", -3.6, -0.92, scale=0.96, layer="front"),
            prop("weapon-rack", 0.0, -1.02, scale=0.94, layer="mid"),
        ],
        lines=[
            line("ling", "寒江城总算肯听真话了，可这只匣子绕了一圈，还是落回了你手上。"),
            line("shen", "匣子里装的从来不是权势，是有人宁可丢命也不肯丢掉的一口公道。"),
            line("wu_chen", "把它重新封好吧，往后再有人想篡改旧案，也得先想起今夜这一战。"),
            line("shen", "封匣容易，守住人心更难，但至少从今晚起，寒江的风能吹得正一点。"),
        ],
    ),
]


class HanjiangNightEscortVideo(BaseVideoScript):
    def get_title(self) -> str:
        return "寒江夜镖"

    def get_theme(self) -> str:
        return "武侠、护镖追杀、旧案翻转、桥战与戏台决斗"

    def get_cast(self) -> list[dict]:
        return CAST

    def get_video_options(self) -> dict:
        return VIDEO

    def has_tts(self) -> bool:
        return True

    def get_notes(self) -> dict:
        return {
            "scene_count": len(SCENE_SPECS),
            "tone": "wuxia-escort-revenge",
        }

    def get_default_output(self) -> str:
        return "outputs/hanjiang_night_escort_story.mp4"

    def get_description(self) -> str:
        return "Render a ten-scene wuxia escort story with TTS dialogue and staged combat."

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
                    npc_groups=spec.npc_groups,
                    beats=beats,
                    expressions=expressions_sorted,
                    dialogues=dialogue_items,
                    audio=spec.audio,
                )
            )
        return scenes


SCRIPT = HanjiangNightEscortVideo()


def build_story() -> dict:
    return SCRIPT.build_story()


def main() -> int:
    return SCRIPT()


if __name__ == "__main__":
    raise SystemExit(main())
