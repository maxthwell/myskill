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
        "effect_overlay_alpha": 0.48,
    },
}

CAST = [
    cast_member("lin_shen", "林深", "detective-sleek"),
    cast_member("su_qing", "苏青", "reporter-selfie"),
    cast_member("qiao_man", "乔曼", "office-worker-modern"),
    cast_member("old_guan", "关伯", "farmer-old"),
    cast_member("xiao_tong", "小童", "npc-boy"),
    cast_member("narrator", "旁白", "narrator"),
]

SCENE_DURATION_MS = 14_500
DIALOGUE_WINDOWS = [
    (0, 2500),
    (3000, 5200),
    (7200, 9500),
    (10100, 12600),
]


DialogueLine = tuple[str, str]


@dataclass(frozen=True)
class SceneSpec:
    scene_id: str
    background: str
    floor: str
    summary: str
    actors: list[dict]
    props: list[dict]
    lines: list[DialogueLine]
    audio: dict
    extra_beats: list[dict] = field(default_factory=list)
    effects: list[dict] = field(default_factory=list)


def line(speaker_id: str, text: str) -> DialogueLine:
    return (speaker_id, text)


def front_actor(actor_id: str, x: float, *, facing: str, scale: float = 1.0, z: float = 0.0) -> dict:
    return actor(actor_id, x, z=z, facing=facing, scale=scale)


def mid_actor(actor_id: str, x: float, *, facing: str, scale: float = 1.0, z: float = -0.08) -> dict:
    return actor(actor_id, x, z=z, facing=facing, scale=scale, layer="mid")


def detective_scene(
    scene_id: str,
    *,
    background: str,
    floor: str,
    summary: str,
    actors: Sequence[dict],
    props: Sequence[dict],
    lines: Sequence[DialogueLine],
    audio: dict,
    extra_beats: Sequence[dict] = (),
    effects: Sequence[dict] = (),
) -> SceneSpec:
    return SceneSpec(
        scene_id=scene_id,
        background=background,
        floor=floor,
        summary=summary,
        actors=list(actors),
        props=list(props),
        lines=list(lines),
        audio=audio,
        extra_beats=list(extra_beats),
        effects=list(effects),
    )


def infer_expression(text: str) -> str:
    if any(token in text for token in ("鬼", "影子", "尸体", "死", "别回头", "冷")):
        return "thinking"
    if any(token in text for token in ("不可能", "骗人", "假的", "装神弄鬼")):
        return "skeptical"
    if any(token in text for token in ("快", "危险", "立刻", "马上")):
        return "excited"
    if any(token in text for token in ("凶手", "真相", "证据")):
        return "angry"
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
    return camera_pan(
        x=-0.22 + 0.05 * (scene_index % 3),
        z=0.04,
        zoom=1.01 + 0.02 * (scene_index % 2),
        to_x=0.18 - 0.04 * (scene_index % 2),
        to_z=0.01,
        to_zoom=1.08 + 0.01 * (scene_index % 3),
        ease="ease-in-out",
    )


def hotel_props(scene_index: int, *, interior: bool) -> list[dict]:
    if interior:
        return [
            prop("wall-window", -3.8, -1.0, scale=0.9 + 0.04 * (scene_index % 2), layer="back"),
            prop("lantern", 3.8, -0.94, scale=0.84 + 0.03 * ((scene_index + 1) % 2), layer="front"),
        ]
    return [
        prop("house", 0.0, -1.08, scale=1.0, layer="back"),
        prop("moon", 3.8, -0.4, scale=0.72, layer="back"),
        prop("star", -3.8, -0.55, scale=0.5, layer="back"),
    ]


def suspense_audio(*, heartbeat: bool = True, ghost: bool = False, laugh: bool = False) -> dict:
    sfx = []
    bgm = audio_bgm("assets/audio/心脏怦怦跳.wav", volume=0.16, loop=True) if heartbeat else None
    if ghost:
        sfx.append(audio_sfx("assets/audio/恐怖的幽灵声音.wav", start_ms=8400, volume=0.45))
    if laugh:
        sfx.append(audio_sfx("assets/audio/女生大笑.wav", start_ms=10800, volume=0.34))
    return scene_audio(bgm=bgm, sfx=sfx)


SCENE_SPECS = [
    detective_scene(
        "scene-001",
        background="night-bridge",
        floor="dark-stage",
        summary="深夜，侦探林深赶到停业多年的河湾旅馆，苏青已经在门外等他。",
        actors=[
            front_actor("lin_shen", -2.5, facing="right"),
            front_actor("su_qing", 2.3, facing="left", scale=0.96),
        ],
        props=hotel_props(0, interior=False),
        lines=[
            line("su_qing", "就是这家旅馆，三天里死了两个人，监控却只拍到一团白影。"),
            line("lin_shen", "白影不会自己开门，真正让我在意的是，现场没有任何脚印。"),
            line("su_qing", "关伯说，午夜十二点以后，二楼尽头会有人一直敲墙。"),
            line("lin_shen", "先进去，越像鬼，越说明有人在借鬼做事。"),
        ],
        extra_beats=[
            beat(5400, 6800, "lin_shen", "enter", x0=-2.8, x1=-1.8, facing="right", emotion="calm"),
            beat(5400, 6800, "su_qing", "point", facing="left", emotion="charged"),
        ],
        audio=suspense_audio(heartbeat=True, ghost=False),
    ),
    detective_scene(
        "scene-002",
        background="hotel-lobby",
        floor="wood-plank",
        summary="大堂灯影发黄，守门老人关伯说旅馆早该拆掉，偏偏总有人回来。",
        actors=[
            front_actor("lin_shen", -2.3, facing="right"),
            mid_actor("su_qing", -0.3, facing="right", scale=0.92),
            front_actor("old_guan", 2.4, facing="left", scale=0.98),
        ],
        props=hotel_props(1, interior=True),
        lines=[
            line("old_guan", "我劝你们天亮再查，昨夜那位客人就是听见哭声，自己走进了尽头房。"),
            line("lin_shen", "哭声从哪来。"),
            line("old_guan", "没人知道，可门一关上，里面就像有人拖着铁链走路。"),
            line("su_qing", "你昨晚为什么不报警。"),
        ],
        extra_beats=[
            beat(2600, 4200, "old_guan", "point", facing="left"),
            beat(5600, 7000, "lin_shen", "nod", facing="right", emotion="focused"),
        ],
        audio=suspense_audio(heartbeat=True, ghost=True),
    ),
    detective_scene(
        "scene-003",
        background="room-day",
        floor="wood-plank",
        summary="死者住过的三零七房间门锁反扣，窗边的镜子上残着一道手印。",
        actors=[
            front_actor("lin_shen", -2.0, facing="right"),
            front_actor("su_qing", 1.8, facing="left", scale=0.95),
        ],
        props=hotel_props(2, interior=True),
        lines=[
            line("su_qing", "门闩是从里面插上的，法医却说死者临死前曾经拼命后退。"),
            line("lin_shen", "镜面有雾，说明有人在我们来之前，对着这里长时间呼吸。"),
            line("su_qing", "可房里除了我们，根本没有第三个人。"),
            line("lin_shen", "第三个人离开了，只是没从门走。"),
        ],
        extra_beats=[
            beat(5400, 6800, "lin_shen", "point", facing="right"),
            beat(5600, 7000, "su_qing", "exit", x0=1.8, x1=1.2, facing="left", emotion="awkward"),
        ],
        effects=[
            effect(asset_path="assets/effects/启动大招特效.webp", start_ms=9000, end_ms=11800, alpha=0.32, playback_speed=0.65),
        ],
        audio=suspense_audio(heartbeat=True, ghost=True),
    ),
    detective_scene(
        "scene-004",
        background="archive-library",
        floor="wood-plank",
        summary="档案室里，林深翻出十年前的火灾记录，发现旅馆老板一家只登记死了三人。",
        actors=[
            front_actor("lin_shen", -2.4, facing="right"),
            front_actor("qiao_man", 2.2, facing="left", scale=0.96),
        ],
        props=hotel_props(3, interior=True),
        lines=[
            line("qiao_man", "我是死者的妹妹乔曼，我哥说过，旅馆真正死掉的人其实是四个。"),
            line("lin_shen", "少了谁。"),
            line("qiao_man", "老板的小儿子，当年没有尸体，警方就把他当成失踪。"),
            line("lin_shen", "失踪的孩子，往往会变成最方便的鬼。"),
        ],
        extra_beats=[
            beat(2600, 4200, "qiao_man", "talk", facing="left", emotion="tense"),
            beat(5600, 6900, "lin_shen", "point", facing="right"),
        ],
        audio=suspense_audio(heartbeat=False, ghost=False),
    ),
    detective_scene(
        "scene-005",
        background="museum-gallery",
        floor="wood-plank",
        summary="证物室里，一台老式录音机还在工作，磁带反复播放孩子的笑声。",
        actors=[
            front_actor("lin_shen", -2.3, facing="right"),
            mid_actor("su_qing", 0.0, facing="right", scale=0.92),
            front_actor("qiao_man", 2.3, facing="left", scale=0.96),
        ],
        props=hotel_props(4, interior=True),
        lines=[
            line("su_qing", "你听，这不是哭声，是有人把笑声放慢以后反复倒带。"),
            line("qiao_man", "我小时候听过这个录音，只有旅馆老板的儿子喜欢这样笑。"),
            line("lin_shen", "所以所谓闹鬼，从头到尾都有人在幕后操控。"),
            line("su_qing", "可控制录音的人，为什么每次都比我们早一步。"),
        ],
        extra_beats=[
            beat(2600, 4200, "su_qing", "point", facing="right"),
            beat(5600, 7000, "lin_shen", "nod", facing="right"),
        ],
        effects=[
            effect(asset_path="assets/effects/启动大招特效.webp", start_ms=9600, end_ms=12500, alpha=0.28, playback_speed=0.7),
        ],
        audio=scene_audio(
            bgm=audio_bgm("assets/audio/心脏怦怦跳.wav", volume=0.15, loop=True),
            sfx=[audio_sfx("assets/audio/女生大笑.wav", start_ms=7600, volume=0.42)],
        ),
    ),
    detective_scene(
        "scene-006",
        background="cafe-night",
        floor="dark-stage",
        summary="短暂停电后，两人去夜间咖啡馆复盘，发现死者都查过同一个地下账本。",
        actors=[
            front_actor("lin_shen", -2.2, facing="right"),
            front_actor("su_qing", 2.1, facing="left", scale=0.95),
        ],
        props=hotel_props(5, interior=False),
        lines=[
            line("su_qing", "两个死者，一个查火灾，一个查旧账，线索最后都落回旅馆老板。"),
            line("lin_shen", "更准确地说，是落回老板失踪的小儿子。"),
            line("su_qing", "你怀疑他没死，还一直躲在旅馆里。"),
            line("lin_shen", "不，我怀疑有人希望我们这么想。"),
        ],
        extra_beats=[
            beat(5400, 6800, "lin_shen", "point", facing="right"),
            beat(5600, 6900, "su_qing", "nod", facing="left"),
        ],
        audio=suspense_audio(heartbeat=False, ghost=False),
    ),
    detective_scene(
        "scene-007",
        background="town-hall-records",
        floor="wood-plank",
        summary="旧账本显示，旅馆火灾后有人持续收到封口费，签名一直是关伯代领。",
        actors=[
            front_actor("lin_shen", -2.4, facing="right"),
            mid_actor("su_qing", -0.1, facing="right", scale=0.92),
            front_actor("old_guan", 2.4, facing="left", scale=0.98),
        ],
        props=hotel_props(6, interior=True),
        lines=[
            line("lin_shen", "关伯，这些年封口费都是你领的。"),
            line("old_guan", "我只是替死人守门，没拿不该拿的钱。"),
            line("su_qing", "可每个死者出事前，都来找过你。"),
            line("old_guan", "因为只有我知道，二楼尽头那面墙后面还藏着一间小屋。"),
        ],
        extra_beats=[
            beat(5400, 6800, "lin_shen", "point", facing="right"),
            beat(5600, 7200, "old_guan", "talk", facing="left", emotion="tense"),
        ],
        audio=suspense_audio(heartbeat=True, ghost=False),
    ),
    detective_scene(
        "scene-008",
        background="inn-hall",
        floor="wood-plank",
        summary="三人重新回到旅馆大厅，关伯说出失踪孩子并未死，而是被老板亲手锁进密室。",
        actors=[
            front_actor("lin_shen", -2.5, facing="right"),
            front_actor("old_guan", 0.0, facing="left", scale=0.98),
            front_actor("qiao_man", 2.5, facing="left", scale=0.96),
        ],
        props=hotel_props(7, interior=True),
        lines=[
            line("old_guan", "火不是意外，老板怕私账曝光，想烧掉证据，也把儿子一起困在了墙里。"),
            line("qiao_man", "所以这些年真正回来的，不是鬼，是知道真相的人。"),
            line("lin_shen", "而每个靠近密室的人，最后都被某个人提前灭口。"),
            line("old_guan", "那个人今晚就在楼上，等你们自己送上门。"),
        ],
        extra_beats=[
            beat(2500, 4200, "old_guan", "point", facing="left"),
            beat(5600, 7000, "lin_shen", "nod", facing="right"),
        ],
        effects=[
            effect(asset_path="assets/effects/启动大招特效.webp", start_ms=10800, end_ms=13200, alpha=0.25, playback_speed=0.7),
        ],
        audio=suspense_audio(heartbeat=True, ghost=True),
    ),
    detective_scene(
        "scene-009",
        background="night-bridge",
        floor="dark-stage",
        summary="二楼走廊尽头忽然传来铁链擦地声，小童从暗门里踉跄跑出来。",
        actors=[
            front_actor("lin_shen", -2.5, facing="right"),
            mid_actor("su_qing", -0.3, facing="right", scale=0.92),
            front_actor("xiao_tong", 2.3, facing="left", scale=0.9),
        ],
        props=hotel_props(8, interior=False),
        lines=[
            line("xiao_tong", "别回头，墙里面一直有人在敲门，他说自己还没死。"),
            line("su_qing", "你是谁，为什么躲在旅馆里。"),
            line("xiao_tong", "我是当年那个孩子的孙子，我是来替他把录音放给所有人听的。"),
            line("lin_shen", "放录音的人不是凶手，但真正的凶手已经被你逼出来了。"),
        ],
        extra_beats=[
            beat(2600, 4200, "xiao_tong", "enter", x0=2.8, x1=2.1, facing="left", emotion="excited"),
            beat(5600, 7000, "lin_shen", "point", facing="right"),
        ],
        effects=[
            effect(asset_path="assets/effects/启动大招特效.webp", start_ms=1800, end_ms=4200, alpha=0.30, playback_speed=0.6),
            effect("thunder-strike", start_ms=8600, end_ms=10800, alpha=0.34, playback_speed=0.55),
        ],
        audio=scene_audio(
            bgm=audio_bgm("assets/audio/心脏怦怦跳.wav", volume=0.2, loop=True),
            sfx=[audio_sfx("assets/audio/恐怖的幽灵声音.wav", start_ms=2200, volume=0.46)],
        ),
    ),
    detective_scene(
        "scene-010",
        background="bank-lobby",
        floor="wood-plank",
        summary="林深在地下账房逼住真正的凶手关伯，原来这些年的闹鬼全是他在清理知情者。",
        actors=[
            front_actor("lin_shen", -2.4, facing="right"),
            front_actor("old_guan", 2.2, facing="left", scale=0.98),
            mid_actor("su_qing", -0.2, facing="right", scale=0.92),
        ],
        props=hotel_props(9, interior=True),
        lines=[
            line("lin_shen", "你不是守门人，你是一直替老板守住罪证的人。"),
            line("old_guan", "我守的不是罪证，是那个孩子到死都没等来的公道。"),
            line("su_qing", "所以你就一边放鬼影，一边杀掉每个想翻旧案的人。"),
            line("old_guan", "他们不配把真相写成一页新闻，然后转身就忘。"),
        ],
        extra_beats=[
            beat(5400, 7000, "lin_shen", "point", facing="right", emotion="charged"),
            beat(5600, 7300, "old_guan", "talk", facing="left", emotion="charged"),
        ],
        audio=suspense_audio(heartbeat=True, ghost=False),
    ),
    detective_scene(
        "scene-011",
        background="theatre-stage",
        floor="dark-stage",
        summary="关伯崩溃承认自己故意制造鬼影，可他否认最后一名死者是自己杀的。",
        actors=[
            front_actor("lin_shen", -2.3, facing="right"),
            front_actor("old_guan", 0.0, facing="left", scale=0.98),
            front_actor("qiao_man", 2.3, facing="left", scale=0.96),
        ],
        props=hotel_props(10, interior=False),
        lines=[
            line("old_guan", "前两个人是我推下去的，可你们报纸上写的第三个，不是我碰的。"),
            line("qiao_man", "那晚我哥临死前给我发过一条短信，他说屋里还有另一个人。"),
            line("lin_shen", "另一个人就是老板本人，他这些年根本没离开过旅馆。"),
            line("old_guan", "不可能，我亲眼看见他在火里倒下。"),
        ],
        extra_beats=[
            beat(2600, 4200, "old_guan", "talk", facing="left", emotion="hurt"),
            beat(5600, 7000, "lin_shen", "nod", facing="right"),
        ],
        effects=[
            effect(asset_path="assets/effects/启动大招特效.webp", start_ms=10200, end_ms=12800, alpha=0.22, playback_speed=0.72),
        ],
        audio=suspense_audio(heartbeat=True, ghost=True),
    ),
    detective_scene(
        "scene-012",
        background="room-day",
        floor="wood-plank",
        summary="密室终于被撬开，里面只剩一把烧黑的儿童椅和一面朝内的镜子，真正的结局仍留下一丝寒意。",
        actors=[
            front_actor("lin_shen", -2.3, facing="right"),
            mid_actor("su_qing", 0.0, facing="right", scale=0.92),
            front_actor("narrator", 2.3, facing="left", scale=0.96),
        ],
        props=hotel_props(11, interior=True),
        lines=[
            line("su_qing", "屋里没有人，只有这把椅子和镜子，像是有人一直坐在这里看着门外。"),
            line("lin_shen", "老板早就死了，最后一名死者是自己被镜中的白影吓到，失足撞上了窗台。"),
            line("narrator", "案子似乎已经结束，可镜面最深处，仍像有个孩子把手轻轻贴在里面。"),
            line("su_qing", "林深，你刚才有没有听见，有人在墙后面笑。"),
        ],
        extra_beats=[
            beat(5400, 6800, "lin_shen", "point", facing="right"),
            beat(5600, 6900, "su_qing", "nod", facing="right", emotion="tense"),
        ],
        effects=[
            effect(asset_path="assets/effects/启动大招特效.webp", start_ms=9800, end_ms=13200, alpha=0.30, playback_speed=0.60),
        ],
        audio=scene_audio(
            bgm=audio_bgm("assets/audio/心脏怦怦跳.wav", volume=0.18, loop=True),
            sfx=[
                audio_sfx("assets/audio/恐怖的幽灵声音.wav", start_ms=8600, volume=0.42),
                audio_sfx("assets/audio/女生大笑.wav", start_ms=11600, volume=0.28),
            ],
        ),
    ),
]


class DetectiveHauntedHotelVideo(BaseVideoScript):
    def get_title(self) -> str:
        return "河湾旅馆疑影"

    def get_theme(self) -> str:
        return "侦探、悬疑、恐怖氛围、旧旅馆密室谜案"

    def get_cast(self) -> list[dict]:
        return CAST

    def get_video_options(self) -> dict:
        return VIDEO

    def has_tts(self) -> bool:
        return True

    def get_notes(self) -> dict:
        return {
            "scene_count": len(SCENE_SPECS),
            "tone": "suspense-horror-detective",
        }

    def get_default_output(self) -> str:
        return "outputs/detective_haunted_hotel.mp4"

    def get_description(self) -> str:
        return "Render a suspense detective story set in a haunted riverside hotel."

    def get_scenes(self) -> list[dict]:
        scenes: list[dict] = []
        for scene_index, spec in enumerate(SCENE_SPECS):
            dialogue_items, talk_beats, expressions = build_dialogue_bundle(spec.lines)
            beats = sorted(
                [*talk_beats, *spec.extra_beats],
                key=lambda item: (item["start_ms"], item["actor_id"]),
            )
            expression_track = sorted(
                expressions,
                key=lambda item: (item["start_ms"], item["actor_id"]),
            )
            scenes.append(
                scene(
                    spec.scene_id,
                    background=spec.background,
                    floor=spec.floor,
                    duration_ms=SCENE_DURATION_MS,
                    summary=spec.summary,
                    camera=scene_camera(scene_index),
                    effects=spec.effects,
                    props=spec.props,
                    actors=spec.actors,
                    beats=beats,
                    expressions=expression_track,
                    dialogues=dialogue_items,
                    audio=spec.audio,
                )
            )
        return scenes


SCRIPT = DetectiveHauntedHotelVideo()


def build_story() -> dict:
    return SCRIPT.build_story()


def main() -> int:
    return SCRIPT()


if __name__ == "__main__":
    raise SystemExit(main())
