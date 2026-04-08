#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageSequence

import generate_actions_pose_reconstruction as poseviz


ROOT_DIR = Path(__file__).resolve().parents[1]
TMP_ROOT = ROOT_DIR / "tmp" / "direct_runs" / "pose_fight_showcase"
OUTPUT_DEFAULT = ROOT_DIR / "outputs" / "pose_fight_showcase.mp4"
FONT_BOLD = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
FONT_REGULAR = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")

DEFAULT_WIDTH = 960
DEFAULT_HEIGHT = 540
DEFAULT_FPS = 24
FAST_FPS = 12
FAST2_WIDTH = 640
FAST2_HEIGHT = 360
FAST2_FPS = 8
FAST3_WIDTH = 480
FAST3_HEIGHT = 270
FAST3_FPS = 6

WIDTH = DEFAULT_WIDTH
HEIGHT = DEFAULT_HEIGHT
GROUND_Y = HEIGHT * 0.82
TMP_DIR = TMP_ROOT / "normal"

TITLE = "天井连环斗"


@dataclass(frozen=True)
class SfxCue:
    path: Path
    offset_s: float
    volume: float = 0.84


@dataclass(frozen=True)
class EffectCue:
    effect_id: str
    start_s: float
    duration_s: float = 1.2
    alpha: float = 0.92
    playback_speed: float = 2.4


@dataclass(frozen=True)
class ActorSpec:
    actor_id: str
    label: str
    character_id: str
    track_name: str
    expression: str
    x_ratio: float
    scale: float
    mirror: bool = False
    phase_s: float = 0.0
    speed: float = 1.0
    y_shift_ratio: float = 0.0


@dataclass(frozen=True)
class SceneSpec:
    scene_id: str
    title: str
    background_id: str
    bgm_path: Path
    duration_s: float
    accent: tuple[int, int, int]
    tint: tuple[int, int, int, int] = (0, 0, 0, 0)
    actors: tuple[ActorSpec, ...] = field(default_factory=tuple)
    effects: tuple[EffectCue, ...] = field(default_factory=tuple)
    sfx: tuple[SfxCue, ...] = field(default_factory=tuple)


BACKGROUND_PATHS = {
    "training-ground": ROOT_DIR / "assets" / "backgrounds" / "training-ground.jpg",
    "temple-courtyard": ROOT_DIR / "assets" / "backgrounds" / "temple-courtyard.jpg",
    "night-bridge": ROOT_DIR / "assets" / "backgrounds" / "night-bridge.jpg",
    "mountain-cliff": ROOT_DIR / "assets" / "backgrounds" / "mountain-cliff.jpg",
    "shop-row": ROOT_DIR / "assets" / "backgrounds" / "shop-row.jpg",
    "street-day": ROOT_DIR / "assets" / "backgrounds" / "street-day.jpg",
    "school-yard": ROOT_DIR / "assets" / "backgrounds" / "school-yard.jpg",
    "桂林山水": ROOT_DIR / "assets" / "backgrounds" / "桂林山水.gif",
    "苍凉的明月夜": ROOT_DIR / "assets" / "backgrounds" / "苍凉的明月夜.gif",
}

EFFECT_PATHS = {
    "命中特效": ROOT_DIR / "assets" / "effects" / "命中特效.gif",
    "飞踢": ROOT_DIR / "assets" / "effects" / "飞踢.gif",
    "银河旋转特效": ROOT_DIR / "assets" / "effects" / "银河旋转特效.gif",
    "金龙飞旋特效-适合降龙十八掌": ROOT_DIR / "assets" / "effects" / "金龙飞旋特效-适合降龙十八掌.gif",
    "爆炸特效": ROOT_DIR / "assets" / "effects" / "爆炸特效.webp",
    "风起云涌": ROOT_DIR / "assets" / "effects" / "风起云涌.gif",
    "电闪雷鸣": ROOT_DIR / "assets" / "effects" / "电闪雷鸣.gif",
}

STILL_TRACKS = {
    "站立",
    "放松站立",
    "女人站立",
    "女人单手掐腰站立",
    "坐",
    "坐下",
    "蹲下",
    "朝右跪坐",
    "朝左趴下",
    "头部朝左放松躺下",
}


def _bgm(name: str) -> Path:
    return ROOT_DIR / "assets" / "bgm" / f"{name}.mp3"


def _audio(name: str) -> Path:
    if name.endswith(".wav") or name.endswith(".mp3"):
        return ROOT_DIR / "assets" / "audio" / name
    candidate_wav = ROOT_DIR / "assets" / "audio" / f"{name}.wav"
    if candidate_wav.exists():
        return candidate_wav
    return ROOT_DIR / "assets" / "audio" / f"{name}.mp3"


SCENES: list[SceneSpec] = [
    SceneSpec(
        "01",
        "擂台摆架",
        "training-ground",
        _bgm("男儿当自强"),
        3.6,
        (255, 234, 188),
        (18, 10, 6, 44),
        actors=(
            ActorSpec("yue", "岳沉风", "face-2", "放松站立", "serious", 0.26, 0.82),
            ActorSpec("huo", "霍惊鸿", "face-17", "站立", "focused", 0.74, 0.82, True),
        ),
        effects=(EffectCue("风起云涌", 0.4, 1.3, 0.82, 1.8),),
        sfx=(SfxCue(_audio("心脏怦怦跳"), 0.6, 0.12),),
    ),
    SceneSpec(
        "02",
        "逼步试探",
        "training-ground",
        _bgm("男儿当自强"),
        3.8,
        (255, 226, 180),
        (0, 0, 0, 26),
        actors=(
            ActorSpec("yue", "岳沉风", "face-2", "行走", "focused", 0.30, 0.82, False, 0.15, 1.0),
            ActorSpec("huo", "霍惊鸿", "face-17", "向左行走", "serious", 0.70, 0.82, False, 0.0, 1.0),
        ),
        sfx=(SfxCue(_audio("031_26_赤手空拳打斗的声音_爱给网_aigei_com.mp3"), 1.4, 0.54),),
    ),
    SceneSpec(
        "03",
        "快拳碰头",
        "training-ground",
        _bgm("男儿当自强"),
        3.8,
        (255, 214, 163),
        actors=(
            ActorSpec("yue", "岳沉风", "face-2", "面向右拳击", "angry", 0.32, 0.84),
            ActorSpec("huo", "霍惊鸿", "face-17", "拳击", "angry", 0.68, 0.84, True, 0.1),
        ),
        effects=(EffectCue("命中特效", 1.35, 0.9, 0.98, 2.6),),
        sfx=(
            SfxCue(_audio("格斗打中"), 1.35, 0.92),
            SfxCue(_audio("一拳击中"), 2.2, 0.96),
        ),
    ),
    SceneSpec(
        "04",
        "飞踢破门",
        "street-day",
        _bgm("最后之战-热血-卢冠廷"),
        3.7,
        (255, 222, 190),
        (0, 0, 0, 18),
        actors=(
            ActorSpec("yue", "岳沉风", "face-2", "人物A飞踢倒人物B", "angry", 0.34, 0.88),
            ActorSpec("huo", "霍惊鸿", "face-17", "蹲下", "shocked", 0.72, 0.76, True),
        ),
        effects=(EffectCue("飞踢", 1.2, 1.0, 0.98, 2.6),),
        sfx=(
            SfxCue(_audio("格斗打中"), 1.2, 0.94),
            SfxCue(_audio("一拳击中"), 1.9, 0.96),
        ),
    ),
    SceneSpec(
        "05",
        "翻身闪位",
        "street-day",
        _bgm("最后之战-热血-卢冠廷"),
        3.6,
        (255, 222, 194),
        actors=(
            ActorSpec("huo", "霍惊鸿", "face-17", "翻跟头gif", "focused", 0.66, 0.86, True, 0.0, 0.92),
            ActorSpec("yue", "岳沉风", "face-2", "面向右拳击", "angry", 0.30, 0.84, False, 0.2, 1.06),
        ),
        effects=(EffectCue("命中特效", 2.2, 0.9, 0.9, 2.4),),
        sfx=(SfxCue(_audio("格斗打中"), 2.18, 0.86),),
    ),
    SceneSpec(
        "06",
        "女侠入锋",
        "temple-courtyard",
        _bgm("杀破狼"),
        4.0,
        (255, 230, 198),
        actors=(
            ActorSpec("su", "苏晚棠", "face-13", "舞剑", "focused", 0.48, 0.82, False, 0.0, 0.92),
            ActorSpec("yue", "岳沉风", "face-2", "跑", "serious", 0.22, 0.80, False, 0.35, 0.8),
            ActorSpec("huo", "霍惊鸿", "face-17", "跑", "serious", 0.78, 0.80, True, 0.12, 0.82),
        ),
        effects=(EffectCue("银河旋转特效", 1.05, 1.25, 0.94, 2.5),),
        sfx=(SfxCue(_audio("刀剑、金属碰撞（带回音）_爱给网_aigei_com.mp3"), 1.0, 0.92),),
    ),
    SceneSpec(
        "07",
        "两翼包夹",
        "temple-courtyard",
        _bgm("杀破狼"),
        4.0,
        (255, 223, 180),
        actors=(
            ActorSpec("yue", "岳沉风", "face-2", "跑", "focused", 0.24, 0.81, False, 0.0, 0.96),
            ActorSpec("huo", "霍惊鸿", "face-17", "拳击", "angry", 0.54, 0.84, True, 0.15),
            ActorSpec("su", "苏晚棠", "face-13", "舞剑", "angry", 0.80, 0.78, True, 0.32, 0.92),
        ),
        effects=(EffectCue("命中特效", 1.9, 0.8, 0.98, 2.6),),
        sfx=(
            SfxCue(_audio("格斗打中"), 1.9, 0.92),
            SfxCue(_audio("刀剑、金属碰撞（带回音）_爱给网_aigei_com.mp3"), 2.45, 0.82),
        ),
    ),
    SceneSpec(
        "08",
        "桥头扫腿",
        "night-bridge",
        _bgm("杀破狼"),
        3.8,
        (203, 227, 255),
        (8, 18, 38, 62),
        actors=(
            ActorSpec("huo", "霍惊鸿", "face-17", "人物A飞踢倒人物B", "angry", 0.64, 0.88, True, 0.12),
            ActorSpec("yue", "岳沉风", "face-2", "蹲下", "pained", 0.30, 0.76),
        ),
        effects=(EffectCue("飞踢", 1.1, 1.0, 0.98, 2.8),),
        sfx=(SfxCue(_audio("格斗打中"), 1.15, 0.94),),
    ),
    SceneSpec(
        "09",
        "后空翻脱手",
        "night-bridge",
        _bgm("杀破狼"),
        4.0,
        (219, 233, 255),
        (0, 0, 0, 42),
        actors=(
            ActorSpec("yue", "岳沉风", "face-2", "连续后空翻", "focused", 0.34, 0.86, False, 0.0, 0.88),
            ActorSpec("su", "苏晚棠", "face-13", "舞剑", "serious", 0.72, 0.80, True, 0.28, 0.92),
        ),
        effects=(EffectCue("银河旋转特效", 2.0, 1.0, 0.9, 2.6),),
        sfx=(SfxCue(_audio("刀剑、金属碰撞（带回音）_爱给网_aigei_com.mp3"), 2.02, 0.86),),
    ),
    SceneSpec(
        "10",
        "太极化劲",
        "school-yard",
        _bgm("王进打高俅-赵季平-水浒传"),
        4.0,
        (255, 226, 191),
        actors=(
            ActorSpec("liu", "柳青鸢", "face-14", "太极", "calm", 0.36, 0.82, False, 0.0, 0.82),
            ActorSpec("huo", "霍惊鸿", "face-17", "拳击", "angry", 0.68, 0.84, True, 0.2, 1.0),
        ),
        effects=(EffectCue("风起云涌", 1.5, 1.4, 0.82, 2.0),),
        sfx=(SfxCue(_audio("031_26_赤手空拳打斗的声音_爱给网_aigei_com.mp3"), 1.4, 0.52),),
    ),
    SceneSpec(
        "11",
        "龙掌反推",
        "school-yard",
        _bgm("王进打高俅-赵季平-水浒传"),
        3.9,
        (255, 226, 184),
        actors=(
            ActorSpec("yue", "岳沉风", "face-2", "降龙十八掌", "angry", 0.32, 0.86, False, 0.0, 0.9),
            ActorSpec("huo", "霍惊鸿", "face-17", "跑", "shocked", 0.72, 0.80, True, 0.16, 1.0),
        ),
        effects=(EffectCue("金龙飞旋特效-适合降龙十八掌", 1.25, 1.15, 0.98, 2.6),),
        sfx=(SfxCue(_audio("音效 爆炸 爆破 爆发 战斗_爱给网_aigei_com.mp3"), 1.25, 0.74),),
    ),
    SceneSpec(
        "12",
        "鲤鱼翻身",
        "shop-row",
        _bgm("最后之战-热血-卢冠廷"),
        3.7,
        (255, 220, 182),
        actors=(
            ActorSpec("huo", "霍惊鸿", "face-17", "鲤鱼打挺", "angry", 0.50, 0.82, False, 0.0, 0.92),
            ActorSpec("yue", "岳沉风", "face-2", "拳击", "focused", 0.24, 0.80, False, 0.2),
            ActorSpec("su", "苏晚棠", "face-13", "蹲下", "serious", 0.78, 0.74, True),
        ),
        effects=(EffectCue("命中特效", 1.95, 0.9, 0.94, 2.5),),
        sfx=(SfxCue(_audio("格斗打中"), 1.95, 0.9),),
    ),
    SceneSpec(
        "13",
        "倒立逼近",
        "shop-row",
        _bgm("最后之战-热血-卢冠廷"),
        3.8,
        (255, 220, 186),
        actors=(
            ActorSpec("yue", "岳沉风", "face-2", "倒立行走", "focused", 0.30, 0.80, False, 0.0, 0.9),
            ActorSpec("huo", "霍惊鸿", "face-17", "面向右拳击", "angry", 0.68, 0.84, False, 0.18),
        ),
        sfx=(SfxCue(_audio("031_26_赤手空拳打斗的声音_爱给网_aigei_com.mp3"), 1.5, 0.5),),
    ),
    SceneSpec(
        "14",
        "拳脚连缠",
        "street-day",
        _bgm("乔峰专属bgm"),
        4.0,
        (255, 225, 185),
        actors=(
            ActorSpec("yue", "岳沉风", "face-2", "面向右拳击", "angry", 0.28, 0.84),
            ActorSpec("huo", "霍惊鸿", "face-17", "人物A飞踢倒人物B", "angry", 0.68, 0.88, True, 0.14),
            ActorSpec("liu", "柳青鸢", "face-14", "跑", "focused", 0.52, 0.74, False, 0.28, 1.0, -0.02),
        ),
        effects=(
            EffectCue("飞踢", 1.0, 1.0, 0.98, 2.7),
            EffectCue("命中特效", 2.05, 0.8, 0.94, 2.6),
        ),
        sfx=(
            SfxCue(_audio("格斗打中"), 1.02, 0.9),
            SfxCue(_audio("一拳击中"), 2.05, 0.96),
        ),
    ),
    SceneSpec(
        "15",
        "夜桥剑浪",
        "苍凉的明月夜",
        _bgm("乔峰专属bgm"),
        3.9,
        (225, 236, 255),
        (10, 18, 34, 56),
        actors=(
            ActorSpec("su", "苏晚棠", "face-13", "舞剑", "focused", 0.34, 0.82, False, 0.0, 0.92),
            ActorSpec("liu", "柳青鸢", "face-14", "舞剑", "angry", 0.70, 0.82, True, 0.34, 0.92),
        ),
        effects=(EffectCue("银河旋转特效", 1.3, 1.2, 0.96, 2.5),),
        sfx=(SfxCue(_audio("刀剑、金属碰撞（带回音）_爱给网_aigei_com.mp3"), 1.32, 0.92),),
    ),
    SceneSpec(
        "16",
        "崖边追命",
        "mountain-cliff",
        _bgm("最后之战-热血-卢冠廷"),
        4.0,
        (255, 226, 190),
        (0, 0, 0, 24),
        actors=(
            ActorSpec("yue", "岳沉风", "face-2", "跑", "angry", 0.24, 0.82, False, 0.06, 1.0),
            ActorSpec("huo", "霍惊鸿", "face-17", "人物A飞踢倒人物B", "angry", 0.62, 0.88, True, 0.14),
            ActorSpec("su", "苏晚棠", "face-13", "跑", "focused", 0.82, 0.76, True, 0.28, 0.98),
        ),
        effects=(EffectCue("飞踢", 1.6, 1.0, 0.98, 2.7),),
        sfx=(SfxCue(_audio("格斗打中"), 1.6, 0.94),),
    ),
    SceneSpec(
        "17",
        "巷口混战",
        "shop-row",
        _bgm("最后之战-热血-卢冠廷"),
        4.0,
        (255, 222, 180),
        actors=(
            ActorSpec("yue", "岳沉风", "face-2", "拳击", "angry", 0.24, 0.84),
            ActorSpec("huo", "霍惊鸿", "face-17", "拳击", "angry", 0.50, 0.84, True, 0.18),
            ActorSpec("su", "苏晚棠", "face-13", "舞剑", "serious", 0.78, 0.78, True, 0.34),
        ),
        effects=(
            EffectCue("命中特效", 1.1, 0.8, 0.96, 2.6),
            EffectCue("银河旋转特效", 2.1, 1.0, 0.88, 2.4),
        ),
        sfx=(
            SfxCue(_audio("格斗打中"), 1.1, 0.9),
            SfxCue(_audio("刀剑、金属碰撞（带回音）_爱给网_aigei_com.mp3"), 2.1, 0.86),
        ),
    ),
    SceneSpec(
        "18",
        "翻腾穿云",
        "桂林山水",
        _bgm("乔峰专属bgm"),
        3.9,
        (255, 240, 216),
        (0, 0, 0, 18),
        actors=(
            ActorSpec("yue", "岳沉风", "face-2", "连续后空翻", "focused", 0.30, 0.84, False, 0.0, 0.88),
            ActorSpec("huo", "霍惊鸿", "face-17", "翻跟头gif", "focused", 0.70, 0.84, True, 0.16, 0.92),
        ),
        effects=(EffectCue("风起云涌", 1.2, 1.3, 0.84, 2.0),),
        sfx=(SfxCue(_audio("031_26_赤手空拳打斗的声音_爱给网_aigei_com.mp3"), 1.6, 0.48),),
    ),
    SceneSpec(
        "19",
        "双掌对轰",
        "mountain-cliff",
        _bgm("最后之战-热血-卢冠廷"),
        4.0,
        (255, 228, 188),
        actors=(
            ActorSpec("yue", "岳沉风", "face-2", "降龙十八掌", "angry", 0.30, 0.86, False, 0.0, 0.92),
            ActorSpec("huo", "霍惊鸿", "face-17", "降龙十八掌", "angry", 0.70, 0.86, True, 0.2, 0.92),
        ),
        effects=(
            EffectCue("金龙飞旋特效-适合降龙十八掌", 1.0, 1.2, 0.98, 2.5),
            EffectCue("爆炸特效", 2.05, 1.0, 0.96, 2.2),
        ),
        sfx=(
            SfxCue(_audio("音效 爆炸 爆破 爆发 战斗_爱给网_aigei_com.mp3"), 1.0, 0.76),
            SfxCue(_audio("音效 爆炸 爆破 爆发 战斗_爱给网_aigei_com.mp3"), 2.05, 0.82),
        ),
    ),
    SceneSpec(
        "20",
        "雷桥总决",
        "night-bridge",
        _bgm("杀破狼"),
        4.1,
        (215, 231, 255),
        (6, 16, 38, 70),
        actors=(
            ActorSpec("yue", "岳沉风", "face-2", "面向右拳击", "angry", 0.24, 0.84),
            ActorSpec("huo", "霍惊鸿", "face-17", "人物A飞踢倒人物B", "angry", 0.50, 0.88, True, 0.12),
            ActorSpec("su", "苏晚棠", "face-13", "舞剑", "focused", 0.78, 0.78, True, 0.3),
        ),
        effects=(
            EffectCue("电闪雷鸣", 0.55, 1.2, 0.9, 2.0),
            EffectCue("命中特效", 1.45, 0.8, 0.98, 2.7),
            EffectCue("银河旋转特效", 2.45, 1.0, 0.92, 2.5),
        ),
        sfx=(
            SfxCue(_audio("打雷闪电"), 0.55, 0.72),
            SfxCue(_audio("格斗打中"), 1.45, 0.94),
            SfxCue(_audio("刀剑、金属碰撞（带回音）_爱给网_aigei_com.mp3"), 2.45, 0.86),
        ),
    ),
    SceneSpec(
        "21",
        "三面围杀",
        "training-ground",
        _bgm("乔峰专属bgm"),
        4.0,
        (255, 226, 188),
        actors=(
            ActorSpec("yue", "岳沉风", "face-2", "拳击", "angry", 0.22, 0.84),
            ActorSpec("huo", "霍惊鸿", "face-17", "拳击", "angry", 0.48, 0.84, True, 0.18),
            ActorSpec("su", "苏晚棠", "face-13", "舞剑", "angry", 0.76, 0.80, True, 0.3),
            ActorSpec("liu", "柳青鸢", "face-14", "跑", "focused", 0.90, 0.70, True, 0.25, 1.0, -0.02),
        ),
        effects=(EffectCue("命中特效", 1.7, 0.8, 0.96, 2.6),),
        sfx=(SfxCue(_audio("格斗打中"), 1.7, 0.92),),
    ),
    SceneSpec(
        "22",
        "收势立场",
        "temple-courtyard",
        _bgm("铁血丹心"),
        3.6,
        (255, 234, 196),
        (8, 8, 8, 18),
        actors=(
            ActorSpec("liu", "柳青鸢", "face-14", "太极", "calm", 0.28, 0.80, False, 0.0, 0.8),
            ActorSpec("yue", "岳沉风", "face-2", "放松站立", "relieved", 0.52, 0.82),
            ActorSpec("su", "苏晚棠", "face-13", "站立", "smile", 0.76, 0.80, True),
        ),
        effects=(EffectCue("风起云涌", 0.8, 1.3, 0.82, 1.8),),
    ),
]


def _ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required")
    return ffmpeg


@lru_cache(maxsize=16)
def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REGULAR), size=size)


def _render_scale() -> float:
    return poseviz.render_scale_for_size(WIDTH, HEIGHT)


def _ui_px(value: int) -> int:
    return max(1, int(round(value * max(0.66, _render_scale() * 0.92))))


@lru_cache(maxsize=64)
def _track(track_name: str) -> poseviz.PoseTrack:
    return poseviz._load_track(poseviz.POSE_DIR / f"{track_name}.pose.json", width=WIDTH, height=HEIGHT)


@lru_cache(maxsize=64)
def _textures(character_id: str) -> poseviz.TexturePack:
    return poseviz._load_texture_pack(character_id)


def _set_render_profile(*, fast: bool = False, fast2: bool = False, fast3: bool = False) -> int:
    global WIDTH, HEIGHT, GROUND_Y, TMP_DIR
    if fast3:
        WIDTH = FAST3_WIDTH
        HEIGHT = FAST3_HEIGHT
        TMP_DIR = TMP_ROOT / "fast3"
        fps = FAST3_FPS
    elif fast2:
        WIDTH = FAST2_WIDTH
        HEIGHT = FAST2_HEIGHT
        TMP_DIR = TMP_ROOT / "fast2"
        fps = FAST2_FPS
    elif fast:
        WIDTH = DEFAULT_WIDTH
        HEIGHT = DEFAULT_HEIGHT
        TMP_DIR = TMP_ROOT / "fast"
        fps = FAST_FPS
    else:
        WIDTH = DEFAULT_WIDTH
        HEIGHT = DEFAULT_HEIGHT
        TMP_DIR = TMP_ROOT / "normal"
        fps = DEFAULT_FPS
    GROUND_Y = HEIGHT * 0.82
    _track.cache_clear()
    _background_frame.cache_clear()
    _effect_frames.cache_clear()
    return fps


@lru_cache(maxsize=32)
def _background_frame(background_id: str) -> Image.Image:
    path = BACKGROUND_PATHS[background_id]
    with Image.open(path) as image:
        image.seek(0)
        frame = image.convert("RGB")
    return ImageOps.fit(frame, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS)


@lru_cache(maxsize=32)
def _effect_frames(effect_id: str) -> tuple[Image.Image, ...]:
    path = EFFECT_PATHS[effect_id]
    with Image.open(path) as image:
        frames: list[Image.Image] = []
        for frame in ImageSequence.Iterator(image):
            frames.append(frame.convert("RGBA"))
        if not frames:
            frames.append(image.convert("RGBA"))
    return tuple(frames)


def _scene_paths(scene: SceneSpec) -> dict[str, Path]:
    scene_dir = TMP_DIR / f"scene_{scene.scene_id}"
    scene_dir.mkdir(parents=True, exist_ok=True)
    return {
        "dir": scene_dir,
        "audio": scene_dir / "scene_audio.m4a",
        "video": scene_dir / "scene_video.mp4",
        "scene_mp4": scene_dir / f"{scene.scene_id}.mp4",
    }


def _all_head_size() -> int:
    values = [_track(actor.track_name).head_size for scene in SCENES for actor in scene.actors]
    scale = _render_scale()
    min_head = max(28, int(round(58 * scale)))
    max_head = max(min_head + 8, int(round(76 * scale)))
    return max(min_head, min(max_head, int(round(sum(values) / len(values) * 0.78))))


def _mix_scene_audio(scene: SceneSpec, output_path: Path) -> None:
    command = [_ffmpeg(), "-y", "-stream_loop", "-1", "-i", str(scene.bgm_path)]
    for cue in scene.sfx:
        command.extend(["-i", str(cue.path)])
    filters = [f"[0:a]atrim=0:{scene.duration_s:.3f},asetpts=N/SR/TB,volume=0.22[bgm]"]
    mix_inputs = ["[bgm]"]
    for index, cue in enumerate(scene.sfx, start=1):
        delay_ms = int(round(cue.offset_s * 1000))
        label = f"sfx{index}"
        filters.append(f"[{index}:a]adelay={delay_ms}|{delay_ms},volume={cue.volume:.3f}[{label}]")
        mix_inputs.append(f"[{label}]")
    filters.append(f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)},alimiter=limit=0.92[aout]")
    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[aout]",
            "-t",
            f"{scene.duration_s:.3f}",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(output_path),
        ]
    )
    subprocess.run(command, check=True)


def _draw_scene_header(draw: ImageDraw.ImageDraw, scene: SceneSpec, t_s: float) -> None:
    title_font = _font(_ui_px(24), bold=True)
    sub_font = _font(_ui_px(18))
    plate_w = _ui_px(360)
    plate_h = _ui_px(74)
    x0 = _ui_px(24)
    y0 = _ui_px(20)
    draw.rounded_rectangle((x0, y0, x0 + plate_w, y0 + plate_h), radius=_ui_px(18), fill=(10, 14, 20, 186))
    draw.text((x0 + _ui_px(18), y0 + _ui_px(12)), TITLE, fill=(244, 240, 232), font=title_font)
    draw.text((x0 + _ui_px(18), y0 + _ui_px(40)), f"{scene.scene_id}  {scene.title}", fill=scene.accent, font=sub_font)
    bar_x0 = x0 + _ui_px(18)
    bar_x1 = x0 + plate_w - _ui_px(18)
    bar_y = y0 + plate_h - _ui_px(12)
    draw.rounded_rectangle((bar_x0, bar_y, bar_x1, bar_y + _ui_px(6)), radius=_ui_px(3), fill=(70, 76, 88, 180))
    progress = min(1.0, max(0.0, t_s / max(scene.duration_s, 0.001)))
    draw.rounded_rectangle((bar_x0, bar_y, bar_x0 + int((bar_x1 - bar_x0) * progress), bar_y + _ui_px(6)), radius=_ui_px(3), fill=scene.accent + (255,))


def _render_background(scene: SceneSpec) -> Image.Image:
    image = _background_frame(scene.background_id).convert("RGBA")
    if scene.tint[3] > 0:
        image.alpha_composite(Image.new("RGBA", image.size, scene.tint))
    floor = Image.new("RGBA", image.size, (0, 0, 0, 0))
    floor_draw = ImageDraw.Draw(floor, "RGBA")
    horizon = int(round(HEIGHT * 0.78))
    floor_draw.rectangle((0, horizon, WIDTH, HEIGHT), fill=(22, 18, 16, 46))
    floor_draw.rectangle((0, int(round(HEIGHT * 0.82)), WIDTH, HEIGHT), fill=(10, 10, 10, 34))
    image.alpha_composite(floor)
    return image


def _sample_actor_track(actor: ActorSpec, t_s: float) -> dict[str, poseviz.np.ndarray]:
    track = _track(actor.track_name)
    if actor.track_name in STILL_TRACKS:
        sample_t = min(track.total_duration_s, (t_s * 0.2 + actor.phase_s) % max(track.total_duration_s, 0.001))
    else:
        sample_t = (t_s * actor.speed + actor.phase_s) % max(track.total_duration_s, 0.001)
    return poseviz._sample_track(track, sample_t)


def _actor_stage_points(actor: ActorSpec, track: poseviz.PoseTrack, points: dict[str, poseviz.np.ndarray]) -> dict[str, tuple[float, float]]:
    base = {name: poseviz._stage_point(track, point, width=WIDTH, height=HEIGHT) for name, point in points.items()}
    actor_scale = actor.scale * (0.76 + 0.24 * _render_scale())
    anchor_x = WIDTH * actor.x_ratio
    center_x = WIDTH * 0.5
    stage: dict[str, tuple[float, float]] = {}
    for name, (x, y) in base.items():
        stage_x = center_x + (x - center_x) * actor_scale + (anchor_x - center_x)
        if actor.mirror:
            stage_x = anchor_x - (stage_x - anchor_x)
        stage_y = GROUND_Y + (y - GROUND_Y) * actor_scale + actor.y_shift_ratio * HEIGHT
        stage[name] = (stage_x, stage_y)
    return stage


def _draw_actor(image: Image.Image, actor: ActorSpec, t_s: float, head_size: int) -> None:
    points = _sample_actor_track(actor, t_s)
    track = _track(actor.track_name)
    stage_points = _actor_stage_points(actor, track, points)
    textures = _textures(actor.character_id)
    palette = poseviz._palette_for_character(actor.character_id)
    draw_scale = _render_scale()
    limb_width = max(8, int(round(poseviz.LIMB_WIDTH * draw_scale)))
    joint_radius = max(4, int(round(poseviz.JOINT_RADIUS * draw_scale)))

    draw = ImageDraw.Draw(image, "RGBA")
    for start, end in poseviz.POSE_EDGES:
        if start not in {"left_hip", "right_hip", "left_knee", "right_knee"}:
            continue
        if start not in stage_points or end not in stage_points:
            continue
        draw.line((*stage_points[start], *stage_points[end]), fill=poseviz._edge_color(start, palette), width=limb_width, joint="curve")
    for name, (x, y) in stage_points.items():
        if name in {"nose", "left_hip", "right_hip"}:
            continue
        if name not in {"left_knee", "right_knee", "left_ankle", "right_ankle"}:
            continue
        color = poseviz._joint_color(name, palette)
        draw.ellipse((x - joint_radius, y - joint_radius, x + joint_radius, y + joint_radius), fill=color)

    poseviz._draw_torso(draw, stage_points, palette)
    poseviz._draw_torso_texture(image, stage_points, textures)

    draw = ImageDraw.Draw(image, "RGBA")
    for start, end in poseviz.POSE_EDGES:
        if start not in {"left_shoulder", "right_shoulder", "left_elbow", "right_elbow"}:
            continue
        if start not in stage_points or end not in stage_points:
            continue
        draw.line((*stage_points[start], *stage_points[end]), fill=poseviz._edge_color(start, palette), width=limb_width, joint="curve")
    for name, (x, y) in stage_points.items():
        if name in {"nose", "left_hip", "right_hip"}:
            continue
        if name not in {"left_shoulder", "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist"}:
            continue
        color = poseviz._joint_color(name, palette)
        draw.ellipse((x - joint_radius, y - joint_radius, x + joint_radius, y + joint_radius), fill=color)

    face_texture = poseviz._load_face_texture(actor.character_id, expression=actor.expression)
    poseviz._draw_panda_head(
        image,
        draw,
        stage_points,
        size=int(round(head_size * actor.scale * (0.76 + 0.24 * _render_scale()))),
        textures=textures,
        face_texture=face_texture,
    )


def _draw_effects(image: Image.Image, scene: SceneSpec, t_s: float) -> None:
    for cue in scene.effects:
        if not (cue.start_s <= t_s <= cue.start_s + cue.duration_s):
            continue
        frames = _effect_frames(cue.effect_id)
        if not frames:
            continue
        progress = min(0.999, max(0.0, (t_s - cue.start_s) / max(cue.duration_s, 0.001)))
        frame_index = min(len(frames) - 1, int(progress * cue.playback_speed * len(frames)))
        frame = ImageOps.fit(frames[frame_index], (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS)
        alpha = frame.getchannel("A").point(lambda value: 0 if value <= 0 else max(220, min(255, int(round(value * cue.alpha)))))
        frame.putalpha(alpha)
        image.alpha_composite(frame)


def _render_scene_frame(scene: SceneSpec, t_s: float, head_size: int) -> Image.Image:
    image = _render_background(scene)
    for actor in sorted(scene.actors, key=lambda item: item.scale):
        _draw_actor(image, actor, t_s, head_size)
    _draw_effects(image, scene, t_s)
    draw = ImageDraw.Draw(image, "RGBA")
    _draw_scene_header(draw, scene, t_s)
    if t_s < 0.18:
        alpha = int(round((0.18 - t_s) / 0.18 * 255))
        image.alpha_composite(Image.new("RGBA", image.size, (0, 0, 0, alpha)))
    if scene.duration_s - t_s < 0.18:
        alpha = int(round((0.18 - (scene.duration_s - t_s)) / 0.18 * 255))
        image.alpha_composite(Image.new("RGBA", image.size, (0, 0, 0, alpha)))
    return image.convert("RGB")


def _render_scene_video(scene: SceneSpec, output_path: Path, fps: int, *, fast: bool, fast2: bool, fast3: bool) -> None:
    head_size = _all_head_size()
    preset, crf = poseviz._encoding_profile(fast=fast, fast2=fast2, fast3=fast3)
    proc = poseviz._open_ffmpeg_stream(fps, WIDTH, HEIGHT, output_path, preset=preset, crf=crf)
    try:
        assert proc.stdin is not None
        total_frames = max(1, int(round(scene.duration_s * fps)))
        for frame_index in range(total_frames):
            t_s = frame_index / fps
            frame = _render_scene_frame(scene, t_s, head_size)
            proc.stdin.write(frame.tobytes())
    finally:
        if proc.stdin is not None:
            proc.stdin.close()
        proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg exited with code {proc.returncode}")


def _mux_scene(video_path: Path, audio_path: Path, output_path: Path) -> None:
    subprocess.run(
        [
            _ffmpeg(),
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-shortest",
            str(output_path),
        ],
        check=True,
    )


def _concat_scenes(scene_files: list[Path], output_path: Path) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False, dir=str(TMP_DIR)) as handle:
        for path in scene_files:
            handle.write(f"file '{path.resolve()}'\n")
        concat_list = Path(handle.name)
    try:
        subprocess.run(
            [
                _ffmpeg(),
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-c",
                "copy",
                str(output_path),
            ],
            check=True,
        )
    finally:
        concat_list.unlink(missing_ok=True)


def render_story(output_path: Path, *, force: bool = False, fast: bool = False, fast2: bool = False, fast3: bool = False) -> None:
    fps = _set_render_profile(fast=fast, fast2=fast2, fast3=fast3)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    scene_outputs: list[Path] = []
    for scene in SCENES:
        paths = _scene_paths(scene)
        if not force and paths["scene_mp4"].exists() and paths["scene_mp4"].stat().st_size > 0:
            scene_outputs.append(paths["scene_mp4"])
            print(paths["scene_mp4"])
            continue
        _mix_scene_audio(scene, paths["audio"])
        _render_scene_video(scene, paths["video"], fps, fast=fast, fast2=fast2, fast3=fast3)
        _mux_scene(paths["video"], paths["audio"], paths["scene_mp4"])
        scene_outputs.append(paths["scene_mp4"])
        print(paths["scene_mp4"])
    _concat_scenes(scene_outputs, output_path)
    print(output_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a 22-scene DNN-pose stickman fight video using local action tracks, BGM, SFX, and fullscreen effects.")
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--fast", action="store_true")
    parser.add_argument("--fast2", action="store_true")
    parser.add_argument("--fast3", action="store_true")
    args = parser.parse_args()
    render_story(args.output.resolve(), force=args.force, fast=args.fast, fast2=args.fast2, fast3=args.fast3)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
