#!/usr/bin/env python3
from __future__ import annotations

from storyboard import (
    BaseVideoScript,
    actor,
    audio_bgm,
    audio_sfx,
    beat,
    camera_pan,
    camera_static,
    cast_member,
    effect,
    foreground,
    prop,
    scene,
    scene_audio,
)


VIDEO = {
    "width": 640,
    "height": 360,
    "fps": 8,
    "renderer": "panda_card_fast",
    "speed_mode": "extreme",
    "video_codec": "libx264",
    "encoder_preset": "ultrafast",
    "crf": 26,
    "audio_bitrate": "64k",
    "subtitle_mode": "bottom",
    "tts_enabled": False,
}

CAST = [
    cast_member("hero", "林骁", "general-guard"),
    cast_member("rival", "沈烈", "detective-sleek"),
    cast_member("oracle", "青灯子", "farmer-old"),
]

SCENES = [
    scene(
        "scene-001",
        background="street-day",
        floor="stone-court",
        duration_ms=7000,
        summary="街市外景纸片世界测试",
        camera=camera_pan(x=-0.18, z=0.02, zoom=1.0, to_x=0.16, to_z=0.0, to_zoom=1.08),
        actors=[
            actor("hero", -2.0, facing="right"),
            actor("rival", 2.1, facing="left", layer="mid"),
        ],
        props=[
            prop("house", 0.0, -0.2, scale=1.1, layer="back"),
            prop("wall-door", 2.8, -0.15, scale=0.92, layer="back"),
            prop("lantern", -3.0, -0.1, scale=0.82, layer="front"),
        ],
        beats=[
            beat(900, 2600, "hero", "enter", x0=-2.0, x1=-0.4, facing="right"),
            beat(2900, 4200, "rival", "enter", x0=2.1, x1=0.8, facing="left"),
        ],
        foregrounds=[],
        effects=[effect("风起云涌", start_ms=1, end_ms=7000, alpha=0.18, playback_speed=1.0)],
        audio=scene_audio(bgm=audio_bgm("assets/bgm/铁血丹心.mp3", volume=0.42), sfx=[]),
    ),
    scene(
        "scene-002",
        background="room-day",
        floor="wood-plank",
        duration_ms=7000,
        summary="室内纸片角色与门帘测试",
        camera=camera_static(x=0.0, z=0.03, zoom=1.08),
        actors=[
            actor("hero", -1.2, facing="right"),
            actor("oracle", 1.8, facing="left", layer="mid", scale=0.96),
        ],
        props=[
            prop("weapon-rack", -3.0, -0.1, scale=0.82, layer="mid"),
            prop("wall-window", 3.0, -0.15, scale=0.9, layer="back"),
        ],
        beats=[
            beat(1600, 3200, "hero", "double-palm-push", facing="right"),
            beat(3800, 5600, "hero", "hook-punch", facing="right"),
        ],
        foregrounds=[foreground("敞开的红色帘子-窗帘或床帘皆可", x=-0.02, y=-0.04, width=1.04, height=1.08, opacity=1.0)],
        effects=[effect("启动大招特效", start_ms=1200, end_ms=3600, alpha=0.72, playback_speed=1.0)],
        audio=scene_audio(
            bgm=audio_bgm("assets/bgm/仙剑情缘.mp3", volume=0.34),
            sfx=[audio_sfx("assets/audio/心脏怦怦跳.wav", start_ms=4200, volume=0.55)],
        ),
    ),
    scene(
        "scene-003",
        background="night-bridge",
        floor="dark-stage",
        duration_ms=7000,
        summary="桥上对冲与爆炸特效测试",
        camera=camera_pan(x=-0.24, z=0.02, zoom=1.04, to_x=0.22, to_z=0.0, to_zoom=1.14),
        actors=[
            actor("hero", -2.4, facing="right"),
            actor("rival", 2.2, facing="left"),
        ],
        props=[
            prop("moon", 3.5, -0.2, scale=0.75, layer="back"),
            prop("star", -3.5, -0.25, scale=0.55, layer="back"),
        ],
        beats=[
            beat(900, 2300, "hero", "flying-kick", x0=-2.4, x1=-0.6, facing="right"),
            beat(2900, 4600, "rival", "spin-kick", x0=2.2, x1=0.7, facing="left"),
            beat(4700, 6200, "hero", "combo-punch", facing="right"),
        ],
        effects=[
            effect("飞踢", start_ms=900, end_ms=2300, alpha=0.70, playback_speed=1.0),
            effect("爆炸特效", start_ms=4700, end_ms=6400, alpha=0.76, playback_speed=1.0),
        ],
        audio=scene_audio(
            bgm=audio_bgm("assets/bgm/杀破狼.mp3", volume=0.40),
            sfx=[audio_sfx("assets/audio/音效 爆炸 爆破 爆发 战斗_爱给网_aigei_com.mp3", start_ms=4780, volume=0.90)],
        ),
    ),
    scene(
        "scene-004",
        background="mountain-cliff",
        floor="stone-court",
        duration_ms=7000,
        summary="山崖终景与大特效测试",
        camera=camera_pan(x=-0.14, z=0.08, zoom=1.06, to_x=0.14, to_z=0.02, to_zoom=1.16),
        actors=[
            actor("hero", -1.8, facing="right"),
            actor("rival", 0.4, facing="left"),
            actor("oracle", 2.8, facing="left", layer="mid", scale=0.92),
        ],
        props=[
            prop("weapon-rack", -3.1, -0.2, scale=0.82, layer="mid"),
            prop("training-drum", 3.0, -0.2, scale=0.82, layer="mid"),
        ],
        beats=[
            beat(800, 2200, "hero", "diagonal-kick", facing="right"),
            beat(2600, 4200, "rival", "straight-punch", facing="left"),
            beat(4600, 6500, "hero", "somersault", facing="right"),
        ],
        effects=[
            effect("死亡光线特效", start_ms=2100, end_ms=4300, alpha=0.72, playback_speed=1.0),
            effect("电闪雷鸣", start_ms=1, end_ms=7000, alpha=0.46, playback_speed=1.0),
        ],
        audio=scene_audio(
            bgm=audio_bgm("assets/bgm/最后之战-热血-卢冠廷.mp3", volume=0.44),
            sfx=[audio_sfx("assets/audio/打雷闪电.wav", start_ms=300, volume=0.75)],
        ),
    ),
]


class PandaCardWorldDemo(BaseVideoScript):
    def get_title(self) -> str:
        return "Panda3D 纸片世界演示"

    def get_theme(self) -> str:
        return "paper-world-demo"

    def get_default_output(self) -> str:
        return "outputs/panda_card_world_demo.mp4"

    def get_video_options(self) -> dict:
        return VIDEO

    def get_cast(self):
        return CAST

    def get_scenes(self):
        return SCENES


if __name__ == "__main__":
    raise SystemExit(PandaCardWorldDemo()())
