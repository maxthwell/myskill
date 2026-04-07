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
        "effect_overlay_alpha": 0.42,
    },
}

CAST = [
    cast_member("chen_he", "陈河", "detective-sleek"),
    cast_member("lin_yue", "林月", "office-worker-modern"),
    cast_member("old_qin", "秦伯", "farmer-old"),
    cast_member("ya_ya", "丫丫", "npc-girl"),
    cast_member("narrator", "旁白", "narrator"),
]

SCENE_DURATION_MS = 14_500
DIALOGUE_WINDOWS = [
    (0, 2600),
    (3000, 5300),
    (7100, 9500),
    (10100, 12700),
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
    effects: list[dict] = field(default_factory=list)
    extra_beats: list[dict] = field(default_factory=list)


def line(speaker_id: str, text: str) -> DialogueLine:
    return (speaker_id, text)


def front_actor(actor_id: str, x: float, *, facing: str, scale: float = 1.0, z: float = 0.0) -> dict:
    return actor(actor_id, x, z=z, facing=facing, scale=scale)


def mid_actor(actor_id: str, x: float, *, facing: str, scale: float = 1.0, z: float = -0.08) -> dict:
    return actor(actor_id, x, z=z, facing=facing, scale=scale, layer="mid")


def ghost_scene(
    scene_id: str,
    *,
    background: str,
    floor: str,
    summary: str,
    actors: Sequence[dict],
    props: Sequence[dict],
    lines: Sequence[DialogueLine],
    audio: dict,
    effects: Sequence[dict] = (),
    extra_beats: Sequence[dict] = (),
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
        effects=list(effects),
        extra_beats=list(extra_beats),
    )


def infer_expression(text: str) -> str:
    if any(token in text for token in ("鬼", "影", "冷", "哭", "死", "血", "尸", "笑")):
        return "thinking"
    if any(token in text for token in ("别", "快", "跑", "危险", "来了")):
        return "excited"
    if any(token in text for token in ("骗人", "不可能", "胡说", "假的")):
        return "skeptical"
    if any(token in text for token in ("打开", "进去", "查", "真相")):
        return "angry"
    return "neutral"


def build_dialogue_bundle(lines: Sequence[DialogueLine]) -> tuple[list[dict], list[dict], list[dict]]:
    dialogue_items: list[dict] = []
    beats: list[dict] = []
    expressions: list[dict] = []
    for (start_ms, end_ms), (speaker_id, text) in zip(DIALOGUE_WINDOWS, lines):
        dialogue_items.append(dialogue(start_ms, end_ms, speaker_id, text))
        beats.append(beat(start_ms, end_ms, speaker_id, "talk", emotion="focused"))
        expressions.append(expression(speaker_id, start_ms, end_ms, infer_expression(text)))
    return dialogue_items, beats, expressions


def scene_camera(scene_index: int) -> dict:
    return camera_pan(
        x=-0.24 + 0.05 * (scene_index % 3),
        z=0.03,
        zoom=1.01 + 0.015 * (scene_index % 2),
        to_x=0.20 - 0.04 * (scene_index % 2),
        to_z=0.01,
        to_zoom=1.08 + 0.01 * (scene_index % 3),
        ease="ease-in-out",
    )


def mansion_props(scene_index: int, *, outside: bool) -> list[dict]:
    if outside:
        return [
            prop("house", 0.0, -1.06, scale=1.02, layer="back"),
            prop("moon", 3.9, -0.46, scale=0.72, layer="back"),
            prop("star", -3.7, -0.55, scale=0.50, layer="back"),
        ]
    return [
        prop("wall-window", -3.8, -1.0, scale=0.90 + 0.03 * (scene_index % 2), layer="back"),
        prop("lantern", 3.75, -0.96, scale=0.84 + 0.04 * ((scene_index + 1) % 2), layer="front"),
    ]


def ghost_audio(*, heartbeat: bool = True, ghost: bool = False, laugh: bool = False, boom: bool = False) -> dict:
    sfx: list[dict] = []
    bgm = audio_bgm("assets/audio/心脏怦怦跳.wav", volume=0.18, loop=True) if heartbeat else None
    if ghost:
        sfx.append(audio_sfx("assets/audio/恐怖的幽灵声音.wav", start_ms=7600, volume=0.48))
    if laugh:
        sfx.append(audio_sfx("assets/audio/女生大笑.wav", start_ms=10200, volume=0.33))
    if boom:
        sfx.append(audio_sfx("assets/audio/音效 爆炸 爆破 爆发 战斗_爱给网_aigei_com.mp3", start_ms=9000, volume=0.30))
    return scene_audio(bgm=bgm, sfx=sfx)


SCENE_SPECS = [
    ghost_scene(
        "scene-001",
        background="night-bridge",
        floor="dark-stage",
        summary="暴雨前夜，陈河陪林月回到废弃祖宅，村口只有风和空桥。",
        actors=[
            front_actor("chen_he", -2.4, facing="right"),
            front_actor("lin_yue", 2.3, facing="left", scale=0.96),
        ],
        props=mansion_props(0, outside=True),
        lines=[
            line("lin_yue", "三年了，我妹妹就是在这栋宅子里失踪的。"),
            line("chen_he", "村里人说闹鬼，我只信留下鬼话的人。"),
            line("lin_yue", "你听，桥那头有人在唱童谣。"),
            line("chen_he", "别停，歌声越近，说明有人知道我们回来了。"),
        ],
        audio=ghost_audio(heartbeat=True, ghost=True),
        extra_beats=[
            beat(5300, 6900, "lin_yue", "point", facing="left"),
            beat(5600, 7200, "chen_he", "enter", x0=-2.7, x1=-1.8, facing="right"),
        ],
    ),
    ghost_scene(
        "scene-002",
        background="shop-row",
        floor="stone-court",
        summary="两人先去村口杂货铺打听，老人秦伯却催他们立刻离开。",
        actors=[
            front_actor("chen_he", -2.4, facing="right"),
            mid_actor("lin_yue", -0.2, facing="right", scale=0.92),
            front_actor("old_qin", 2.4, facing="left", scale=0.98),
        ],
        props=mansion_props(1, outside=False),
        lines=[
            line("old_qin", "天一黑，那宅子里的窗纸会自己亮起来，像有人在屋里走。"),
            line("chen_he", "三年前你也看见过。"),
            line("old_qin", "我只看见一个小姑娘站在井边，可她脚下没有影子。"),
            line("lin_yue", "那是我妹妹丫丫失踪前穿的裙子。"),
        ],
        audio=ghost_audio(heartbeat=True, ghost=False),
        effects=[
            effect("aura", start_ms=9400, end_ms=12600, alpha=0.22, playback_speed=0.70),
        ],
        extra_beats=[
            beat(5400, 6800, "old_qin", "point", facing="left"),
        ],
    ),
    ghost_scene(
        "scene-003",
        background="inn-hall",
        floor="wood-plank",
        summary="祖宅大门落灰，门内没有人，却有刚被踩过的湿脚印。",
        actors=[
            front_actor("chen_he", -2.2, facing="right"),
            front_actor("lin_yue", 2.2, facing="left", scale=0.96),
        ],
        props=mansion_props(2, outside=False),
        lines=[
            line("chen_he", "脚印是新的，水还没干。"),
            line("lin_yue", "可我们一路走来，地上根本没有雨。"),
            line("chen_he", "有人从宅子深处走出来，又故意把脚印留给我们看。"),
            line("lin_yue", "别说了，这宅子里好像有人在墙后喘气。"),
        ],
        audio=ghost_audio(heartbeat=True, ghost=True),
        extra_beats=[
            beat(5200, 6800, "chen_he", "point", facing="right"),
        ],
    ),
    ghost_scene(
        "scene-004",
        background="archive-library",
        floor="wood-plank",
        summary="书房里堆着发霉族谱，林月翻出一页被火烧过的儿童名册。",
        actors=[
            front_actor("lin_yue", -2.3, facing="right", scale=0.96),
            front_actor("chen_he", 2.1, facing="left"),
        ],
        props=mansion_props(3, outside=False),
        lines=[
            line("lin_yue", "这里写着丫丫的名字，后面却被人划成了亡故。"),
            line("chen_he", "她失踪那年，你们家是不是办过一场丧事。"),
            line("lin_yue", "没有，只是我父亲从那天起就把东厢房彻底封死了。"),
            line("chen_he", "那封住的不是房门，是知道真相的人。"),
        ],
        audio=ghost_audio(heartbeat=False, ghost=False),
        effects=[
            effect("thunder-strike", start_ms=10400, end_ms=12600, alpha=0.18, playback_speed=0.55),
        ],
    ),
    ghost_scene(
        "scene-005",
        background="room-day",
        floor="wood-plank",
        summary="镜房四面覆着白布，陈河掀开其中一块，镜子里却多出第三道人影。",
        actors=[
            front_actor("chen_he", -2.3, facing="right"),
            mid_actor("lin_yue", 0.0, facing="left", scale=0.92),
            front_actor("ya_ya", 2.4, facing="left", scale=0.88),
        ],
        props=mansion_props(4, outside=False),
        lines=[
            line("lin_yue", "陈河，你后面站着谁。"),
            line("chen_he", "别回头，镜里那个人没有眨眼。"),
            line("ya_ya", "姐姐，你终于回来了。"),
            line("lin_yue", "那声音就是丫丫，可她明明已经不见了三年。"),
        ],
        audio=ghost_audio(heartbeat=True, ghost=True, laugh=True),
        effects=[
            effect("aura", start_ms=7600, end_ms=12600, alpha=0.26, playback_speed=0.62),
        ],
        extra_beats=[
            beat(5400, 7000, "ya_ya", "enter", x0=2.9, x1=2.2, facing="left"),
        ],
    ),
    ghost_scene(
        "scene-006",
        background="museum-gallery",
        floor="wood-plank",
        summary="祠堂画像前，秦伯说出当年宅中失火，丫丫被锁进了井房。",
        actors=[
            front_actor("old_qin", -2.4, facing="right", scale=0.98),
            mid_actor("lin_yue", -0.1, facing="right", scale=0.92),
            front_actor("chen_he", 2.3, facing="left"),
        ],
        props=mansion_props(5, outside=False),
        lines=[
            line("old_qin", "那晚不是意外，是你父亲怕秘密外泄，把井房从外面钉死了。"),
            line("lin_yue", "你为什么现在才说。"),
            line("old_qin", "因为每个知道真相的人，后来都听见井底有人敲木板。"),
            line("chen_he", "所以今晚敲门的不是鬼，是被关死的记忆。"),
        ],
        audio=ghost_audio(heartbeat=True, ghost=False),
        extra_beats=[
            beat(2600, 4200, "old_qin", "point", facing="right"),
            beat(5600, 7000, "chen_he", "nod", facing="left"),
        ],
    ),
    ghost_scene(
        "scene-007",
        background="hotel-lobby",
        floor="wood-plank",
        summary="走廊深处突然传来孩子笑声，尽头门缝下缓缓流出黑水。",
        actors=[
            front_actor("chen_he", -2.3, facing="right"),
            front_actor("lin_yue", 2.2, facing="left", scale=0.96),
        ],
        props=mansion_props(6, outside=False),
        lines=[
            line("lin_yue", "黑水在往我们脚边流，它像是从门里面渗出来的。"),
            line("chen_he", "水里有墨味，不是井水，是供桌上烧过的符灰。"),
            line("lin_yue", "谁会把符灰倒在门里。"),
            line("chen_he", "怕的不是鬼，是怕门后的人把真相写到墙上。"),
        ],
        audio=ghost_audio(heartbeat=True, ghost=True),
        effects=[
            effect("thunder-strike", start_ms=8200, end_ms=11000, alpha=0.20, playback_speed=0.58),
        ],
    ),
    ghost_scene(
        "scene-008",
        background="theatre-stage",
        floor="dark-stage",
        summary="停电的一瞬间，丫丫站在二楼栏杆上，裙摆却像泡在水里一样往下滴。",
        actors=[
            front_actor("ya_ya", -2.2, facing="right", scale=0.88),
            mid_actor("lin_yue", 0.0, facing="right", scale=0.92),
            front_actor("chen_he", 2.3, facing="left"),
        ],
        props=mansion_props(7, outside=False),
        lines=[
            line("ya_ya", "姐姐，那天我一直在喊门，可没有人回来。"),
            line("lin_yue", "我那时被关在后院，我根本不知道你还活着。"),
            line("chen_he", "她不是来索命，她是来带我们去看被藏起来的井房。"),
            line("ya_ya", "门在地下，门后还有一个人，三年都没有离开。"),
        ],
        audio=ghost_audio(heartbeat=True, ghost=True, laugh=True),
        effects=[
            effect("aura", start_ms=1800, end_ms=12600, alpha=0.28, playback_speed=0.60),
        ],
        extra_beats=[
            beat(2600, 4200, "ya_ya", "point", facing="right"),
        ],
    ),
    ghost_scene(
        "scene-009",
        background="town-hall-records",
        floor="wood-plank",
        summary="地下账房里，陈河找到一封遗书，写着林父并未死在火里，而是一直躲在井房后壁。",
        actors=[
            front_actor("chen_he", -2.4, facing="right"),
            front_actor("lin_yue", 2.2, facing="left", scale=0.96),
        ],
        props=mansion_props(8, outside=False),
        lines=[
            line("chen_he", "遗书不是忏悔，是威胁，他说谁敢开井房就一起陪葬。"),
            line("lin_yue", "我父亲如果还活着，那他这三年靠什么活下来的。"),
            line("chen_he", "靠秦伯送饭，也靠村里人一起把鬼故事喂大。"),
            line("lin_yue", "原来最可怕的不是鬼，是活人把死者关在黑暗里。"),
        ],
        audio=ghost_audio(heartbeat=False, ghost=False),
    ),
    ghost_scene(
        "scene-010",
        background="bank-lobby",
        floor="stone-court",
        summary="暗门被打开，林父冲出来想抢遗书，井房深处却传来真正的敲门声。",
        actors=[
            front_actor("chen_he", -2.4, facing="right"),
            front_actor("old_qin", 0.0, facing="left", scale=0.98),
            front_actor("lin_yue", 2.4, facing="left", scale=0.96),
        ],
        props=mansion_props(9, outside=False),
        lines=[
            line("old_qin", "他疯了三年，夜夜都说井里有人要把门推开。"),
            line("chen_he", "因为门后确实有尸骨，你们把丫丫留在那里太久了。"),
            line("lin_yue", "那敲门声不是幻觉。"),
            line("old_qin", "不，那声音从火灾那晚开始，就从来没停过。"),
        ],
        audio=ghost_audio(heartbeat=True, ghost=True, boom=True),
        effects=[
            effect("thunder-strike", start_ms=8600, end_ms=11600, alpha=0.22, playback_speed=0.54),
        ],
    ),
    ghost_scene(
        "scene-011",
        background="cafe-night",
        floor="dark-stage",
        summary="井房被撬开，墙内露出狭小夹层，丫丫的旧鞋和一具蜷缩白骨一同显形。",
        actors=[
            front_actor("lin_yue", -2.3, facing="right", scale=0.96),
            mid_actor("chen_he", 0.0, facing="right"),
            front_actor("narrator", 2.3, facing="left", scale=0.95),
        ],
        props=mansion_props(10, outside=False),
        lines=[
            line("lin_yue", "那双鞋是我给她买的，鞋底还绣着她的名字。"),
            line("chen_he", "白骨在墙里，鬼影在宅里，你父亲只是借她的冤魂遮住自己的罪。"),
            line("narrator", "可就在骨头被抬出来的瞬间，屋里所有镜子同时起了一层水雾。"),
            line("lin_yue", "她还没走，她还在等一句迟到三年的道歉。"),
        ],
        audio=ghost_audio(heartbeat=True, ghost=True, laugh=False),
        effects=[
            effect("aura", start_ms=7600, end_ms=12600, alpha=0.30, playback_speed=0.58),
        ],
    ),
    ghost_scene(
        "scene-012",
        background="night-bridge",
        floor="dark-stage",
        summary="天快亮时，祖宅终于熄灯，桥边却又响起那首童谣，像有人还站在雾里。",
        actors=[
            front_actor("chen_he", -2.4, facing="right"),
            front_actor("lin_yue", 2.2, facing="left", scale=0.96),
            mid_actor("narrator", 0.0, facing="left", scale=0.94),
        ],
        props=mansion_props(11, outside=True),
        lines=[
            line("lin_yue", "她应该已经安息了，为什么歌声还在。"),
            line("chen_he", "因为这座宅子里死过的不止一个孩子。"),
            line("narrator", "雾里慢慢亮起第二双湿漉漉的小脚印，停在桥中央，再也没有往前一步。"),
            line("lin_yue", "陈河，别回头，桥那边又有人在叫我的名字。"),
        ],
        audio=ghost_audio(heartbeat=True, ghost=True, laugh=True),
        effects=[
            effect("aura", start_ms=7600, end_ms=12600, alpha=0.24, playback_speed=0.62),
        ],
    ),
]


class GhostMansionVideo(BaseVideoScript):
    def get_title(self) -> str:
        return "槐宅夜哭"

    def get_theme(self) -> str:
        return "鬼故事、祖宅秘闻、冤魂回响、阴冷悬疑"

    def get_cast(self) -> list[dict]:
        return CAST

    def get_video_options(self) -> dict:
        return VIDEO

    def has_tts(self) -> bool:
        return True

    def get_notes(self) -> dict:
        return {
            "scene_count": len(SCENE_SPECS),
            "tone": "ghost-story-suspense",
        }

    def get_default_output(self) -> str:
        return "outputs/ghost_mansion_story.mp4"

    def get_description(self) -> str:
        return "Render a multi-scene ghost story set in a haunted ancestral mansion."

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


SCRIPT = GhostMansionVideo()


def build_story() -> dict:
    return SCRIPT.build_story()


def main() -> int:
    return SCRIPT()


if __name__ == "__main__":
    raise SystemExit(main())
