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
    cast_member,
    dialogue,
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
        "effect_overlay_alpha": 0.32,
    },
}

CAST = [
    cast_member("hao", "郝大嘴", "detective-sleek"),
    cast_member("bai", "白守正", "official-minister"),
    cast_member("xiao_qin", "小秦", "npc-girl"),
    cast_member("narrator", "旁白", "narrator"),
]

SCENE_DURATION_MS = 15_000
DIALOGUE_WINDOWS = [
    (200, 2600),
    (3200, 5600),
    (7200, 9600),
    (10400, 13200),
]

FLOOR_BY_BACKGROUND = {
    "theatre-stage": "dark-stage",
    "shop-row": "stone-court",
    "bank-lobby": "wood-plank",
    "town-hall-records": "wood-plank",
    "cafe-night": "dark-stage",
    "hotel-lobby": "wood-plank",
    "archive-library": "wood-plank",
    "restaurant-booth": "wood-plank",
    "room-day": "wood-plank",
    "museum-gallery": "wood-plank",
}

LAUGH_AUDIO = "assets/audio/女生大笑.wav"

DialogueLine = tuple[str, str]


@dataclass(frozen=True)
class SceneSpec:
    scene_id: str
    background: str
    summary: str
    actors: list[dict]
    props: list[dict]
    lines: list[DialogueLine]
    audio: dict
    extra_beats: list[dict] = field(default_factory=list)


def line(speaker_id: str, text: str) -> DialogueLine:
    return (speaker_id, text)


def front_actor(actor_id: str, x: float, *, facing: str, scale: float = 1.0, z: float = 0.0) -> dict:
    return actor(actor_id, x, z=z, facing=facing, scale=scale)


def mid_actor(actor_id: str, x: float, *, facing: str, scale: float = 0.94, z: float = -0.08) -> dict:
    return actor(actor_id, x, z=z, facing=facing, scale=scale, layer="mid")


def infer_expression(text: str) -> str:
    if any(token in text for token in ("骗", "假", "糊涂", "不对", "哪有", "荒唐")):
        return "skeptical"
    if any(token in text for token in ("快", "赶紧", "马上", "坏了")):
        return "excited"
    if any(token in text for token in ("主意", "规章", "流程", "办法", "合同")):
        return "thinking"
    if any(token in text for token in ("好家伙", "厉害", "行啊", "这就")):
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
    return camera_pan(
        x=-0.18 + 0.05 * (scene_index % 3),
        z=0.03,
        zoom=1.02,
        to_x=0.16 - 0.04 * (scene_index % 2),
        to_z=0.01,
        to_zoom=1.08 + 0.01 * (scene_index % 3),
        ease="ease-in-out",
    )


def stage_props(scene_index: int, *, outside: bool = False, office: bool = False) -> list[dict]:
    if outside:
        return [
            prop("house", 0.0, -1.06, scale=1.0, layer="back"),
            prop("wall-door", 3.7, -1.0, scale=0.9, layer="back"),
            prop("lantern" if scene_index % 2 else "horse", -3.7, -0.92, scale=0.86, layer="front"),
        ]
    if office:
        return [
            prop("wall-window", 3.7, -0.98, scale=0.92, layer="back"),
        ]
    return [
        prop("wall-window", 3.7, -0.98, scale=0.90, layer="back"),
    ]


def laughter_audio(*, laugh: bool = False) -> dict:
    sfx = []
    if laugh:
        sfx.append(audio_sfx(LAUGH_AUDIO, start_ms=10600, volume=2.40))
    return scene_audio(sfx=sfx)


SCENE_SPECS = [
    SceneSpec(
        scene_id="scene-001",
        background="theatre-stage",
        summary="郝大嘴一上台就宣布自己刚应聘进了一家新公司，名字听着格外正经。",
        actors=[
            front_actor("hao", -2.2, facing="right"),
            front_actor("bai", 2.2, facing="left", scale=0.98),
        ],
        props=stage_props(0),
        lines=[
            line("hao", "我最近找着工作了，公司名字特响亮，叫全城反骗服务总社。"),
            line("bai", "这名不错啊，一听就像替老百姓看家护院的。"),
            line("hao", "我也是这么想的，结果一进门先交培训费，说先学怎么不让别人起疑心。"),
            line("bai", "等会儿，反骗公司第一课，先研究怎么让别人不起疑心。"),
        ],
        audio=laughter_audio(laugh=True),
        extra_beats=[
            beat(5800, 6900, "bai", "point", facing="left", emotion="charged"),
        ],
    ),
    SceneSpec(
        scene_id="scene-002",
        background="shop-row",
        summary="白守正追问公司地址，郝大嘴越介绍越像地下买卖。",
        actors=[
            front_actor("hao", -2.3, facing="right"),
            front_actor("bai", 2.3, facing="left"),
        ],
        props=stage_props(1, outside=True),
        lines=[
            line("bai", "公司开哪儿了。"),
            line("hao", "城西拐角，门口牌子写着金融咨询，后门牌子写着文艺培训，楼上还挂着养生体验。"),
            line("bai", "你们这是一个公司还是一栋楼里住了三种心眼子。"),
            line("hao", "经理说这叫分散风险，真出事先看哪个牌子方便摘。"),
        ],
        audio=laughter_audio(laugh=True),
        extra_beats=[
            beat(5800, 7000, "hao", "point", facing="right", emotion="focused"),
        ],
    ),
    SceneSpec(
        scene_id="scene-003",
        background="bank-lobby",
        summary="培训第一天，小秦负责迎宾，嘴里全是公司规范话术。",
        actors=[
            front_actor("hao", -2.4, facing="right"),
            front_actor("bai", 2.3, facing="left"),
            mid_actor("xiao_qin", 0.0, facing="left", scale=0.90),
        ],
        props=stage_props(2, office=True),
        lines=[
            line("hao", "前台小秦先给我们发工牌，岗位写的是客户情绪安抚专员。"),
            line("bai", "这听着像心理咨询。"),
            line("hao", "她解释得可直接了，就是对方发现不对劲的时候，你得先把人稳住。"),
            line("xiao_qin", "公司要求微笑服务，客户骂得越凶，咱们越得像亲戚。"),
        ],
        audio=laughter_audio(laugh=False),
        extra_beats=[
            beat(6000, 7000, "xiao_qin", "nod", facing="left", emotion="focused"),
        ],
    ),
    SceneSpec(
        scene_id="scene-004",
        background="town-hall-records",
        summary="经理给大家讲企业文化，核心思想就一句话，先把自己说信了。",
        actors=[
            front_actor("hao", -2.4, facing="right"),
            front_actor("bai", 2.2, facing="left"),
        ],
        props=stage_props(3, office=True),
        lines=[
            line("hao", "经理上课先说企业文化，做人要真诚。"),
            line("bai", "骗子公司还提真诚。"),
            line("hao", "他说你自己不信，怎么让别人信，所以骗人之前先感动自己。"),
            line("bai", "这不是企业文化，这是自我催眠。"),
        ],
        audio=laughter_audio(laugh=True),
        extra_beats=[
            beat(5800, 7000, "bai", "point", facing="left", emotion="charged"),
        ],
    ),
    SceneSpec(
        scene_id="scene-005",
        background="cafe-night",
        summary="公司还搞岗位细分，有人负责哭穷，有人负责装专家，流程完整得吓人。",
        actors=[
            front_actor("hao", -2.2, facing="right"),
            front_actor("bai", 2.2, facing="left"),
        ],
        props=[
            prop("moon", 3.8, -0.42, scale=0.72, layer="back"),
            prop("star", -3.8, -0.55, scale=0.52, layer="back"),
        ],
        lines=[
            line("hao", "公司分工特别细，有开场白组、压价组、催单组，还有售后失联组。"),
            line("bai", "售后失联还分组。"),
            line("hao", "那当然，谁负责关机，谁负责拉黑，谁负责朋友圈继续晒旅游，都有台账。"),
            line("bai", "好嘛，你们这是把缺德做成流水线了。"),
        ],
        audio=laughter_audio(laugh=True),
        extra_beats=[
            beat(5800, 7000, "hao", "point", facing="right", emotion="focused"),
        ],
    ),
    SceneSpec(
        scene_id="scene-006",
        background="hotel-lobby",
        summary="郝大嘴本来只想混口饭吃，结果考核内容越来越离谱。",
        actors=[
            front_actor("hao", -2.4, facing="right"),
            front_actor("bai", 2.4, facing="left"),
            mid_actor("xiao_qin", -0.2, facing="right", scale=0.88),
        ],
        props=stage_props(5, office=True),
        lines=[
            line("hao", "考核那天，经理让我对着镜子练三小时，主题是我真替你着想。"),
            line("bai", "这句一出口，镜子都得起雾。"),
            line("xiao_qin", "他还没完，第二项是接电话时要哭得像亲二舅住院。"),
            line("hao", "我一听就明白了，这哪是招员工，这是挑戏班子。"),
        ],
        audio=laughter_audio(laugh=True),
        extra_beats=[
            beat(5900, 6900, "xiao_qin", "point", facing="right", emotion="charged"),
        ],
    ),
    SceneSpec(
        scene_id="scene-007",
        background="archive-library",
        summary="白守正越听越不对，开始追问这家公司到底挣谁的钱。",
        actors=[
            front_actor("hao", -2.3, facing="right"),
            front_actor("bai", 2.2, facing="left"),
        ],
        props=stage_props(6, office=True),
        lines=[
            line("bai", "说了半天，你们公司到底卖什么。"),
            line("hao", "经理说公司不卖货，卖的是紧张、贪心和来不及。"),
            line("bai", "好家伙，直接把人的弱点当产品目录了。"),
            line("hao", "所以我才觉得不对，这买卖挣的是别人的糊涂钱。"),
        ],
        audio=laughter_audio(laugh=False),
        extra_beats=[
            beat(5800, 7000, "bai", "nod", facing="left", emotion="focused"),
        ],
    ),
    SceneSpec(
        scene_id="scene-008",
        background="restaurant-booth",
        summary="郝大嘴终于摊牌，自己根本没上岗，头一天就把公司给举报了。",
        actors=[
            front_actor("hao", -2.3, facing="right"),
            front_actor("bai", 2.2, facing="left"),
        ],
        props=stage_props(7),
        lines=[
            line("hao", "我当天下午就走了，出门先记门牌，转脸就去报案。"),
            line("bai", "这才像人话。"),
            line("hao", "我还顺手把他们培训手册带出来了，封面写着客户至上，背面写着得手就跑。"),
            line("bai", "你这不是入职，你是卧底实习。"),
        ],
        audio=laughter_audio(laugh=True),
        extra_beats=[
            beat(5800, 7000, "hao", "enter", x0=-2.8, x1=-1.8, facing="right", emotion="focused"),
        ],
    ),
    SceneSpec(
        scene_id="scene-009",
        background="room-day",
        summary="白守正追问后续，郝大嘴说那家公司被端之后还想改头换面重新开张。",
        actors=[
            front_actor("hao", -2.2, facing="right"),
            front_actor("bai", 2.2, facing="left"),
            mid_actor("xiao_qin", 0.1, facing="left", scale=0.88),
        ],
        props=stage_props(8, office=True),
        lines=[
            line("bai", "后来呢。"),
            line("hao", "后来他们又想改名，先叫财富陪跑，再叫感情修复，最后差点挂牌老年养生。"),
            line("xiao_qin", "经理还说市场在变化，骗术也得转型升级。"),
            line("bai", "这行业还讲迭代，那就更得让大家长记性。"),
        ],
        audio=laughter_audio(laugh=False),
        extra_beats=[
            beat(5800, 7000, "xiao_qin", "nod", facing="left", emotion="focused"),
        ],
    ),
    SceneSpec(
        scene_id="scene-010",
        background="museum-gallery",
        summary="最后抖出包袱，这家所谓公司最怕的不是警察，是老百姓多问一句为什么。",
        actors=[
            front_actor("hao", -2.2, facing="right"),
            front_actor("bai", 2.2, facing="left"),
        ],
        props=stage_props(9),
        lines=[
            line("hao", "所以我总结出来了，骗子公司最怕两样东西。"),
            line("bai", "哪两样。"),
            line("hao", "一怕你捂住钱包，二怕你多问一句为什么。"),
            line("bai", "对了，天上掉馅饼的时候先别张嘴，低头看看是不是有人在楼上和面。"),
        ],
        audio=laughter_audio(laugh=True),
        extra_beats=[
            beat(5900, 7000, "bai", "point", facing="left", emotion="charged"),
        ],
    ),
]


class XiangshengAntiFraudVideo(BaseVideoScript):
    def get_title(self) -> str:
        return "防骗公司"

    def get_theme(self) -> str:
        return "原创相声、双人捧逗、荒诞公司、反诈讽刺"

    def get_cast(self) -> list[dict]:
        return CAST

    def get_video_options(self) -> dict:
        return VIDEO

    def has_tts(self) -> bool:
        return True

    def get_notes(self) -> dict:
        return {
            "scene_count": len(SCENE_SPECS),
            "format": "xiangsheng-two-hander",
        }

    def get_default_output(self) -> str:
        return "outputs/xiangsheng_anti_fraud_company.mp4"

    def get_description(self) -> str:
        return "Render an original xiangsheng video about an absurd anti-fraud company."

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
                    camera=scene_camera(scene_index),
                    props=spec.props,
                    actors=spec.actors,
                    beats=beats,
                    expressions=expressions_sorted,
                    dialogues=dialogue_items,
                    audio=spec.audio,
                )
            )
        return scenes


SCRIPT = XiangshengAntiFraudVideo()


def build_story() -> dict:
    return SCRIPT.build_story()


def main() -> int:
    return SCRIPT()


if __name__ == "__main__":
    raise SystemExit(main())
