#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import math
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont, ImageSequence

import generate_actions_pose_reconstruction as poseviz


ROOT_DIR = Path(__file__).resolve().parents[1]
TMP_ROOT = ROOT_DIR / "tmp" / "direct_runs" / "cangyun_escort_story"
TMP_DIR = TMP_ROOT / "normal"
OUTPUT_DEFAULT = ROOT_DIR / "outputs" / "cangyun_escort_story.mp4"
DEFAULT_FPS = 24
FAST_FPS = 12
FAST2_FPS = 8
FAST3_FPS = 6
DEFAULT_WIDTH = 960
DEFAULT_HEIGHT = 540
FAST_WIDTH = DEFAULT_WIDTH
FAST_HEIGHT = DEFAULT_HEIGHT
FAST2_WIDTH = 640
FAST2_HEIGHT = 360
FAST3_WIDTH = 480
FAST3_HEIGHT = 270
WIDTH = DEFAULT_WIDTH
HEIGHT = DEFAULT_HEIGHT
TITLE = "寒江断令"
GROUND_Y = HEIGHT * 0.82
TALK_GAP_S = 0.28
TALK_MOUTH_CYCLE_FRAMES = 4
FONT_REGULAR = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
FONT_BOLD = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
ACTION_TRACKS = {"拳击", "翻跟头gif", "人物A飞踢倒人物B", "舞剑", "跑", "连续后空翻", "降龙十八掌", "鲤鱼打挺"}
LEG_POINTS = {"left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle"}
ARM_POINTS = {"left_shoulder", "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist"}
EFFECT_DENSITY = 1.0
EFFECT_PLAYBACK_RATE = 2.8
EFFECT_ALPHA_MIN = 220
EFFECT_ALPHA_MAX = 255
RENDER_PROFILE = "normal"
EFFECT_ONE_SHOT_DURATION_S: dict[str, float] = {
    "rain": 2.2,
    "wind": 2.0,
    "impact": 1.1,
    "slash": 1.0,
    "thunder": 1.3,
    "fire": 1.8,
    "burst": 1.1,
    "embers": 1.6,
    "dust": 1.5,
}
EFFECT_AUDIO_HINTS: dict[str, tuple[str, ...]] = {
    "rain": ("暴雨", "雨"),
    "wind": ("风",),
    "impact": ("击中", "打中", "拳"),
    "slash": ("刀", "剑", "金属"),
    "thunder": ("打雷", "雷"),
    "fire": ("爆炸", "爆破", "火"),
    "burst": ("打斗", "击中", "拳", "爆"),
    "embers": ("心脏", "怦怦"),
    "dust": ("心脏", "怦怦"),
}
EFFECT_ASSET_MAP: dict[str, tuple[str, tuple[float, float, float, float], float]] = {
    "rain": ("电闪雷鸣", (0.0, 0.0, 1.0, 1.0), 0.28),
    "wind": ("风起云涌", (0.0, 0.0, 1.0, 1.0), 0.22),
    "impact": ("命中特效", (0.0, 0.0, 1.0, 1.0), 0.55),
    "slash": ("银河旋转特效", (0.0, 0.0, 1.0, 1.0), 0.32),
    "thunder": ("电闪雷鸣", (0.0, 0.0, 1.0, 1.0), 0.30),
    "fire": ("熊熊大火", (0.0, 0.0, 1.0, 1.0), 0.34),
    "burst": ("爆炸特效", (0.0, 0.0, 1.0, 1.0), 0.32),
    "embers": ("启动大招特效", (0.0, 0.0, 1.0, 1.0), 0.18),
    "dust": ("夕阳武士", (0.0, 0.0, 1.0, 1.0), 0.16),
}


@dataclass(frozen=True)
class SfxCue:
    path: Path
    offset_s: float
    volume: float = 0.8


@dataclass(frozen=True)
class ActorSpec:
    actor_id: str
    label: str
    character_id: str
    voice: str
    track_name: str
    expression: str
    x_offset: int
    scale: float = 0.9
    mirror: bool = False
    visible: bool = True


@dataclass(frozen=True)
class LineSpec:
    speaker_id: str
    text: str
    expression: str
    track_name: str | None = None


@dataclass(frozen=True)
class SceneSpec:
    scene_id: str
    title: str
    actors: tuple[ActorSpec, ...]
    lines: tuple[LineSpec, ...]
    bgm_path: Path
    background_top: tuple[int, int, int]
    background_bottom: tuple[int, int, int]
    accent: tuple[int, int, int]
    effect: str
    sfx: tuple[SfxCue, ...] = field(default_factory=tuple)
    hold_s: float = 0.42


@dataclass(frozen=True)
class ScheduledLine:
    speaker_id: str
    speaker_label: str
    text: str
    expression: str
    track_name: str | None
    voice: str
    tts_path: Path
    start_s: float
    end_s: float
    duration_s: float


SCENES: list[SceneSpec] = [
    SceneSpec(
        scene_id="01",
        title="雪夜遗令",
        actors=(
            ActorSpec("shen", "沈孤鸿", "farmer-old", "zh-CN-YunjianNeural", "放松站立", "serious", -220, 0.82),
            ActorSpec("lu", "陆青川", "face-2", "zh-CN-YunxiNeural", "站立", "focused", 0, 0.96),
            ActorSpec("ning", "宁听雪", "face-13", "zh-CN-XiaoxiaoNeural", "站立", "neutral", 230, 0.88),
        ),
        lines=(
            LineSpec("shen", "断龙令今夜必须送到白鹿关，迟一刻，关外三营都会被假军令调走。", "serious"),
            LineSpec("lu", "师叔把令箭交给我，我便护它到天亮。", "focused"),
            LineSpec("ning", "我带药囊和封蜡，路上若有人查匣，我来替你周旋。", "neutral"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "铁血丹心.mp3",
        background_top=(52, 47, 67),
        background_bottom=(15, 13, 24),
        accent=(242, 220, 173),
        effect="embers",
        sfx=(SfxCue(ROOT_DIR / "assets" / "audio" / "心脏怦怦跳.wav", 0.8, 0.12),),
    ),
    SceneSpec(
        scene_id="02",
        title="镖局封门",
        actors=(
            ActorSpec("lu", "陆青川", "face-2", "zh-CN-YunxiNeural", "站立", "serious", -200, 0.96),
            ActorSpec("ning", "宁听雪", "face-13", "zh-CN-XiaoxiaoNeural", "站立", "skeptical", 20, 0.88),
            ActorSpec("han", "韩照", "detective-sleek", "zh-CN-YunjianNeural", "放松站立", "focused", 250, 0.9),
        ),
        lines=(
            LineSpec("han", "前后门都换成了叶藏锋的人，明面上是护院，脚下站位却像围杀。", "focused"),
            LineSpec("ning", "那就不走门，后井有条旧水道，能通到灯市边上的染坊。", "skeptical"),
            LineSpec("lu", "你在前探路，我背令匣走井道。今夜谁也别回头。", "serious"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "男儿当自强.mp3",
        background_top=(219, 203, 170),
        background_bottom=(149, 113, 73),
        accent=(121, 70, 34),
        effect="wind",
        sfx=(SfxCue(ROOT_DIR / "assets" / "audio" / "潺潺流水声.wav", 0.1, 0.08),),
    ),
    SceneSpec(
        scene_id="03",
        title="灯市换匣",
        actors=(
            ActorSpec("shop", "染坊娘子", "face-15", "zh-CN-XiaoxiaoNeural", "坐下", "nervous", -200, 0.84),
            ActorSpec("ning", "宁听雪", "face-13", "zh-CN-XiaoxiaoNeural", "站立", "smile", 20, 0.88),
            ActorSpec("lu", "陆青川", "face-2", "zh-CN-YunxiNeural", "站立", "focused", 250, 0.96),
        ),
        lines=(
            LineSpec("shop", "你们来得比约定早，假匣和旧封条都备好了，只是街口多了三拨生面孔。", "nervous"),
            LineSpec("ning", "越热闹越好，他们盯着我手里的假货，才看不见你背后的真匣。", "smile"),
            LineSpec("lu", "换完就走，灯一灭，整条街都会变成他们的网。", "focused"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "历史的天空-古筝-三国演义片尾曲.mp3",
        background_top=(203, 178, 143),
        background_bottom=(108, 79, 56),
        accent=(248, 230, 204),
        effect="dust",
        sfx=(SfxCue(ROOT_DIR / "assets" / "audio" / "心脏怦怦跳.wav", 1.9, 0.1),),
    ),
    SceneSpec(
        scene_id="04",
        title="雨巷截杀",
        actors=(
            ActorSpec("lu", "陆青川", "face-2", "zh-CN-YunxiNeural", "站立", "angry", -190, 0.96, True),
            ActorSpec("ning", "宁听雪", "face-13", "zh-CN-XiaoxiaoNeural", "跑", "focused", 20, 0.88),
            ActorSpec("yuan", "袁烈", "emperor-ming", "zh-CN-YunjianNeural", "拳击", "angry", 260, 0.92),
        ),
        lines=(
            LineSpec("yuan", "把匣子放下，我只断你们一只手。再跑，我就收两条命。", "angry", "拳击"),
            LineSpec("lu", "令匣你碰不到，今夜这条巷子就是你的坟。", "angry", "拳击"),
            LineSpec("ning", "右边墙头有空档，我扔火粉逼他抬头，你借势出拳。", "focused", "跑"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "最后之战-热血-卢冠廷.mp3",
        background_top=(57, 76, 107),
        background_bottom=(12, 16, 27),
        accent=(206, 228, 255),
        effect="rain",
        sfx=(
            SfxCue(ROOT_DIR / "assets" / "audio" / "暴雨.wav", 0.0, 0.18),
            SfxCue(ROOT_DIR / "assets" / "audio" / "格斗打中.wav", 2.4, 0.82),
            SfxCue(ROOT_DIR / "assets" / "audio" / "一拳击中.wav", 4.1, 0.94),
        ),
    ),
    SceneSpec(
        scene_id="05",
        title="河仓疗伤",
        actors=(
            ActorSpec("lu", "陆青川", "face-2", "zh-CN-YunxiNeural", "蹲下", "pained", -190, 0.92),
            ActorSpec("ning", "宁听雪", "face-13", "zh-CN-XiaoxiaoNeural", "朝右跪坐", "focused", 40, 0.86),
            ActorSpec("han", "韩照", "detective-sleek", "zh-CN-YunjianNeural", "放松站立", "serious", 260, 0.9),
        ),
        lines=(
            LineSpec("ning", "刀口里有麻骨散，袁烈不是来抢匣，是想先废你的右臂。", "focused"),
            LineSpec("han", "码头外沿多了军中暗哨，能调得动他们的人，只能是叶藏锋。", "serious"),
            LineSpec("lu", "那就顺着这条线往前查，今夜先活下来，明夜再拔他的根。", "pained"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "思君黯然-天龙八部-悲伤.mp3",
        background_top=(70, 59, 62),
        background_bottom=(22, 18, 24),
        accent=(255, 201, 166),
        effect="embers",
        sfx=(SfxCue(ROOT_DIR / "assets" / "audio" / "心脏怦怦跳.wav", 1.3, 0.12),),
    ),
    SceneSpec(
        scene_id="06",
        title="义庄验尸",
        actors=(
            ActorSpec("han", "韩照", "detective-sleek", "zh-CN-YunjianNeural", "站立", "focused", -190, 0.9),
            ActorSpec("lu", "陆青川", "face-2", "zh-CN-YunxiNeural", "站立", "skeptical", 10, 0.96),
            ActorSpec("ning", "宁听雪", "face-13", "zh-CN-XiaoxiaoNeural", "站立", "serious", 250, 0.88),
        ),
        lines=(
            LineSpec("han", "死者腰牌背面刻着白鹿关仓印，叶藏锋已经把手伸到关口。", "focused"),
            LineSpec("lu", "他若只是求财，不会动关仓和军印。断龙令背后还有更大的局。", "skeptical"),
            LineSpec("ning", "那我们就不能只逃，要拿到能钉死他的卷册和人证。", "serious"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "芦苇荡-赵季平-大话西游.mp3",
        background_top=(86, 116, 128),
        background_bottom=(31, 49, 59),
        accent=(220, 239, 227),
        effect="wind",
        sfx=(SfxCue(ROOT_DIR / "assets" / "audio" / "潺潺流水声.wav", 0.0, 0.12),),
    ),
    SceneSpec(
        scene_id="07",
        title="竹海擒哨",
        actors=(
            ActorSpec("lu", "陆青川", "face-2", "zh-CN-YunxiNeural", "站立", "angry", -190, 0.96, True),
            ActorSpec("han", "韩照", "detective-sleek", "zh-CN-YunjianNeural", "站立", "focused", 20, 0.9),
            ActorSpec("qian", "钱哨头", "official-minister", "zh-CN-YunjianNeural", "人物A飞踢倒人物B", "fear", 270, 0.86),
        ),
        lines=(
            LineSpec("qian", "别打了，我只负责沿河递信，真正接匣的人在府衙案库等你们。", "fear", "人物A飞踢倒人物B"),
            LineSpec("han", "案库夜里只开一道偏门，钥匙归叶藏锋心腹管。", "focused"),
            LineSpec("lu", "很好，你带路。敢耍花样，我先折你的腿。", "angry", "拳击"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "杀破狼.mp3",
        background_top=(55, 94, 64),
        background_bottom=(15, 31, 18),
        accent=(185, 235, 190),
        effect="burst",
        sfx=(
            SfxCue(ROOT_DIR / "assets" / "audio" / "031_26_赤手空拳打斗的声音_爱给网_aigei_com.mp3", 1.0, 0.82),
            SfxCue(ROOT_DIR / "assets" / "audio" / "格斗打中.wav", 3.0, 0.86),
        ),
    ),
    SceneSpec(
        scene_id="08",
        title="夜入案库",
        actors=(
            ActorSpec("lu", "陆青川", "face-2", "zh-CN-YunxiNeural", "站立", "focused", -190, 0.96),
            ActorSpec("ning", "宁听雪", "face-13", "zh-CN-XiaoxiaoNeural", "站立", "smile", 20, 0.88),
            ActorSpec("clerk", "守库吏", "official-minister", "zh-CN-YunjianNeural", "放松站立", "skeptical", 260, 0.86),
        ),
        lines=(
            LineSpec("clerk", "三更以后不准翻册，谁给你们的胆子闯案库。", "skeptical"),
            LineSpec("ning", "你认清楚，是叶大人让我们来换封条。你若耽误时辰，掉脑袋的是你。", "smile"),
            LineSpec("lu", "找白鹿关仓册、调兵票底和押印名单，一页都不能漏。", "focused"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "误入迷失森林-少年包青天.mp3",
        background_top=(52, 61, 84),
        background_bottom=(15, 18, 33),
        accent=(224, 236, 250),
        effect="thunder",
        sfx=(SfxCue(ROOT_DIR / "assets" / "audio" / "打雷闪电.wav", 1.7, 0.42),),
    ),
    SceneSpec(
        scene_id="09",
        title="狱中救证",
        actors=(
            ActorSpec("lu", "陆青川", "face-2", "zh-CN-YunxiNeural", "站立", "angry", -190, 0.96, True),
            ActorSpec("qin", "秦刀", "face-17", "zh-CN-YunxiNeural", "朝右跪坐", "serious", 20, 0.88),
            ActorSpec("guard", "狱卒", "official-minister", "zh-CN-YunjianNeural", "拳击", "angry", 260, 0.86),
        ),
        lines=(
            LineSpec("guard", "叶大人交代过，秦刀活不到天亮，谁来都一样。", "angry", "拳击"),
            LineSpec("qin", "仓门机括图在我脑子里，只要你们带我出去，我就能开白鹿关北门。", "serious"),
            LineSpec("lu", "先跟我杀出去，到了外头，你再把这笔旧账一条条说清。", "angry", "舞剑"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "最后之战-热血-卢冠廷.mp3",
        background_top=(71, 35, 28),
        background_bottom=(18, 9, 12),
        accent=(255, 208, 184),
        effect="fire",
        sfx=(
            SfxCue(ROOT_DIR / "assets" / "audio" / "刀剑、金属碰撞（带回音）_爱给网_aigei_com.mp3", 2.0, 0.84),
            SfxCue(ROOT_DIR / "assets" / "audio" / "格斗打中.wav", 4.0, 0.84),
        ),
    ),
    SceneSpec(
        scene_id="10",
        title="屋脊脱围",
        actors=(
            ActorSpec("lu", "陆青川", "face-2", "zh-CN-YunxiNeural", "跑", "angry", -180, 0.96, True),
            ActorSpec("ning", "宁听雪", "face-13", "zh-CN-XiaoxiaoNeural", "跑", "focused", 20, 0.88),
            ActorSpec("qin", "秦刀", "face-17", "zh-CN-YunxiNeural", "跑", "serious", 240, 0.88),
        ),
        lines=(
            LineSpec("qin", "西巷全是弩手，正街又有封马，我熟悉屋檐走法，跟着我跳。", "serious"),
            LineSpec("ning", "我在后面撒药烟，他们看不清脚下，你们先过。", "focused"),
            LineSpec("lu", "一直翻到城西鼓楼，到了暗河口再分开换气。", "angry", "跑"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "杀破狼.mp3",
        background_top=(27, 36, 61),
        background_bottom=(7, 8, 18),
        accent=(208, 226, 255),
        effect="thunder",
        sfx=(
            SfxCue(ROOT_DIR / "assets" / "audio" / "打雷闪电.wav", 1.0, 0.52),
            SfxCue(ROOT_DIR / "assets" / "audio" / "暴雨.wav", 0.0, 0.16),
        ),
    ),
    SceneSpec(
        scene_id="11",
        title="山亭对质",
        actors=(
            ActorSpec("qin", "秦刀", "face-17", "zh-CN-YunxiNeural", "坐下", "thinking", -210, 0.86),
            ActorSpec("lu", "陆青川", "face-2", "zh-CN-YunxiNeural", "站立", "serious", 10, 0.96),
            ActorSpec("han", "韩照", "detective-sleek", "zh-CN-YunjianNeural", "站立", "focused", 250, 0.9),
        ),
        lines=(
            LineSpec("qin", "叶藏锋要的不是令箭本身，而是借断龙令打开白鹿关北仓，偷换军械。", "thinking"),
            LineSpec("han", "所以他先灭案库旧卷，再灭你这个做过仓匠的人证。", "focused"),
            LineSpec("lu", "只要把你和卷册一起送到关前，他这条线就再也藏不住。", "serious"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "思君黯然-天龙八部-悲伤.mp3",
        background_top=(67, 61, 71),
        background_bottom=(22, 20, 28),
        accent=(231, 214, 188),
        effect="embers",
        sfx=(SfxCue(ROOT_DIR / "assets" / "audio" / "心脏怦怦跳.wav", 2.0, 0.12),),
    ),
    SceneSpec(
        scene_id="12",
        title="绝壁采药",
        actors=(
            ActorSpec("ning", "宁听雪", "face-13", "zh-CN-XiaoxiaoNeural", "蹲下", "pained", -180, 0.84),
            ActorSpec("yao", "药娘", "face-15", "zh-CN-XiaoxiaoNeural", "坐下", "neutral", 40, 0.82),
            ActorSpec("lu", "陆青川", "face-2", "zh-CN-YunxiNeural", "站立", "focused", 250, 0.96),
        ),
        lines=(
            LineSpec("yao", "你替陆青川挡了一记透骨针，再不解毒，明日拿刀的人就变成你自己。", "neutral"),
            LineSpec("lu", "药采到了就走，白鹿关只剩半日路程，我们耽误不起。", "focused"),
            LineSpec("ning", "我还能撑，等把令箭送进关门，你再逼我喝药不迟。", "pained"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "莫失莫忘.mp3",
        background_top=(170, 182, 200),
        background_bottom=(80, 97, 120),
        accent=(245, 247, 255),
        effect="wind",
        sfx=(SfxCue(ROOT_DIR / "assets" / "audio" / "潺潺流水声.wav", 0.0, 0.1),),
    ),
    SceneSpec(
        scene_id="13",
        title="雪岭伏杀",
        actors=(
            ActorSpec("lu", "陆青川", "face-2", "zh-CN-YunxiNeural", "站立", "angry", -190, 0.96, True),
            ActorSpec("ning", "宁听雪", "face-13", "zh-CN-XiaoxiaoNeural", "站立", "focused", 30, 0.88),
            ActorSpec("yuan", "袁烈", "emperor-ming", "zh-CN-YunjianNeural", "拳击", "angry", 270, 0.92),
        ),
        lines=(
            LineSpec("yuan", "叶大人算得真准，你们果然会走雪岭近道。把秦刀留下，我饶你们一个全尸。", "angry", "拳击"),
            LineSpec("ning", "你敢堵在这里，说明叶藏锋还没拿到令箭，他比你更急。", "focused"),
            LineSpec("lu", "那我就先拿你的命，去换他今晚的胆寒。", "angry", "拳击"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "男儿当自强.mp3",
        background_top=(174, 184, 198),
        background_bottom=(92, 102, 118),
        accent=(255, 234, 204),
        effect="impact",
        sfx=(
            SfxCue(ROOT_DIR / "assets" / "audio" / "一拳击中.wav", 2.6, 0.95),
            SfxCue(ROOT_DIR / "assets" / "audio" / "格斗打中.wav", 4.5, 0.88),
        ),
    ),
    SceneSpec(
        scene_id="14",
        title="断塔焚册",
        actors=(
            ActorSpec("han", "韩照", "detective-sleek", "zh-CN-YunjianNeural", "站立", "focused", -180, 0.9),
            ActorSpec("ye", "叶藏锋", "official-minister", "zh-CN-YunjianNeural", "放松站立", "cold", 20, 0.88),
            ActorSpec("ning", "宁听雪", "face-13", "zh-CN-XiaoxiaoNeural", "站立", "angry", 260, 0.88),
        ),
        lines=(
            LineSpec("ye", "旧册一烧，北仓失印的事就只剩流言。你们拿什么进关告我。", "cold"),
            LineSpec("han", "卷册能烧，押印人和仓门图却在我们手里。你越急，越像做贼。", "focused"),
            LineSpec("ning", "火光照得满城都能看见，你这一烧，是替我们把人都喊醒了。", "angry"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "暗夜浮香-天龙八部背景乐-悲伤.mp3",
        background_top=(96, 32, 24),
        background_bottom=(22, 8, 10),
        accent=(255, 190, 146),
        effect="fire",
        sfx=(SfxCue(ROOT_DIR / "assets" / "audio" / "音效 爆炸 爆破 爆发 战斗_爱给网_aigei_com.mp3", 4.0, 0.2),),
    ),
    SceneSpec(
        scene_id="15",
        title="暗河换船",
        actors=(
            ActorSpec("boat", "乌篷翁", "farmer-old", "zh-CN-YunjianNeural", "坐下", "thinking", -190, 0.82),
            ActorSpec("qin", "秦刀", "face-17", "zh-CN-YunxiNeural", "坐下", "serious", 30, 0.86),
            ActorSpec("lu", "陆青川", "face-2", "zh-CN-YunxiNeural", "站立", "neutral", 250, 0.96),
        ),
        lines=(
            LineSpec("boat", "官道都断了，只剩暗河还能贴着山根走，天亮前就能把你们送到关下。", "thinking"),
            LineSpec("qin", "到了白鹿关南坡，我能认出藏机括钥的旧砖。", "serious"),
            LineSpec("lu", "过了这道水，前面就只剩硬闯。大家把最后的力气留到关前。", "neutral"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "芦苇荡-赵季平-大话西游.mp3",
        background_top=(88, 121, 141),
        background_bottom=(27, 46, 63),
        accent=(229, 241, 228),
        effect="wind",
        sfx=(SfxCue(ROOT_DIR / "assets" / "audio" / "潺潺流水声.wav", 0.0, 0.15),),
    ),
    SceneSpec(
        scene_id="16",
        title="长街断后",
        actors=(
            ActorSpec("han", "韩照", "detective-sleek", "zh-CN-YunjianNeural", "拳击", "angry", -190, 0.9, True),
            ActorSpec("lu", "陆青川", "face-2", "zh-CN-YunxiNeural", "跑", "focused", 20, 0.96),
            ActorSpec("ning", "宁听雪", "face-13", "zh-CN-XiaoxiaoNeural", "跑", "focused", 240, 0.88),
        ),
        lines=(
            LineSpec("han", "前街我来挡，你们带秦刀和令匣冲关，别让我的血白流。", "angry", "拳击"),
            LineSpec("ning", "韩照，最多一炷香，若你不来，我们就在关楼上替你点第一盏灯。", "focused", "跑"),
            LineSpec("lu", "守住自己这口气，关门一开，我回头接你。", "focused", "跑"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "杀破狼.mp3",
        background_top=(64, 55, 74),
        background_bottom=(20, 16, 27),
        accent=(244, 223, 193),
        effect="slash",
        sfx=(
            SfxCue(ROOT_DIR / "assets" / "audio" / "刀剑、金属碰撞（带回音）_爱给网_aigei_com.mp3", 1.8, 0.84),
            SfxCue(ROOT_DIR / "assets" / "audio" / "031_26_赤手空拳打斗的声音_爱给网_aigei_com.mp3", 3.7, 0.88),
        ),
    ),
    SceneSpec(
        scene_id="17",
        title="寒寺托证",
        actors=(
            ActorSpec("shen", "沈孤鸿", "farmer-old", "zh-CN-YunjianNeural", "坐下", "thinking", -210, 0.82),
            ActorSpec("lu", "陆青川", "face-2", "zh-CN-YunxiNeural", "站立", "serious", 10, 0.96),
            ActorSpec("ning", "宁听雪", "face-13", "zh-CN-XiaoxiaoNeural", "站立", "focused", 240, 0.88),
        ),
        lines=(
            LineSpec("shen", "二十年前我守过北仓，叶藏锋那时就偷换军械，死的人一直压在雪里。", "thinking"),
            LineSpec("lu", "今夜把令箭、仓册、人证和你的口供一并送上关楼，他就再也赖不掉。", "serious"),
            LineSpec("ning", "旧案埋得再深，只要见了天光，就会自己喊冤。", "focused"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "仙剑情缘.mp3",
        background_top=(58, 62, 89),
        background_bottom=(17, 20, 35),
        accent=(225, 221, 255),
        effect="embers",
        sfx=(SfxCue(ROOT_DIR / "assets" / "audio" / "心脏怦怦跳.wav", 2.2, 0.12),),
    ),
    SceneSpec(
        scene_id="18",
        title="关前拒令",
        actors=(
            ActorSpec("feng", "封守毅", "general-guard", "zh-CN-YunxiNeural", "放松站立", "skeptical", -190, 0.92),
            ActorSpec("lu", "陆青川", "face-2", "zh-CN-YunxiNeural", "站立", "angry", 20, 0.96),
            ActorSpec("ning", "宁听雪", "face-13", "zh-CN-XiaoxiaoNeural", "站立", "angry", 240, 0.88),
        ),
        lines=(
            LineSpec("feng", "关门夜封，任何私令都不能验。你们若再上前，我只能按闯关论。", "skeptical"),
            LineSpec("ning", "你若再迟半刻，明早开仓的人就会发现军械全成了废铁。", "angry"),
            LineSpec("lu", "后面追兵已到，你是守规矩，还是守白鹿关，今夜就得选。", "angry"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "观音降临-高潮版.mp3",
        background_top=(88, 103, 124),
        background_bottom=(27, 34, 49),
        accent=(251, 240, 204),
        effect="thunder",
        sfx=(SfxCue(ROOT_DIR / "assets" / "audio" / "打雷闪电.wav", 1.4, 0.45),),
    ),
    SceneSpec(
        scene_id="19",
        title="关楼决战",
        actors=(
            ActorSpec("lu", "陆青川", "face-2", "zh-CN-YunxiNeural", "站立", "angry", -190, 0.96, True),
            ActorSpec("yuan", "袁烈", "emperor-ming", "zh-CN-YunjianNeural", "拳击", "angry", 170, 0.92),
            ActorSpec("ye", "叶藏锋", "official-minister", "zh-CN-YunjianNeural", "放松站立", "cold", 330, 0.84),
        ),
        lines=(
            LineSpec("ye", "只要关门不开，今晚的一切都能算成匪患。陆青川，你赢不了朝里的手。", "cold"),
            LineSpec("yuan", "你去夺令匣，我来打碎他的骨头。", "angry", "拳击"),
            LineSpec("lu", "你们要的是整座关城，我要的只是让所有人看清你们的脸。", "angry", "舞剑"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "最后之战-热血-卢冠廷.mp3",
        background_top=(108, 30, 28),
        background_bottom=(20, 8, 10),
        accent=(255, 222, 206),
        effect="impact",
        sfx=(
            SfxCue(ROOT_DIR / "assets" / "audio" / "刀剑、金属碰撞（带回音）_爱给网_aigei_com.mp3", 2.0, 0.86),
            SfxCue(ROOT_DIR / "assets" / "audio" / "格斗打中.wav", 4.6, 0.86),
            SfxCue(ROOT_DIR / "assets" / "audio" / "一拳击中.wav", 5.3, 0.95),
        ),
    ),
    SceneSpec(
        scene_id="20",
        title="关楼昭令",
        actors=(
            ActorSpec("feng", "封守毅", "general-guard", "zh-CN-YunxiNeural", "放松站立", "relieved", -200, 0.92),
            ActorSpec("ning", "宁听雪", "face-13", "zh-CN-XiaoxiaoNeural", "站立", "smile", 20, 0.88),
            ActorSpec("lu", "陆青川", "face-2", "zh-CN-YunxiNeural", "站立", "neutral", 250, 0.96),
        ),
        lines=(
            LineSpec("feng", "断龙令、仓册、机括图与叶藏锋亲笔押印俱在，白鹿关众军听令，今夜就地封仓拿人。", "relieved"),
            LineSpec("ning", "雪夜里埋了二十年的旧案，总算在天亮前见了人心。", "smile"),
            LineSpec("lu", "关门守住了，命也守住了。接下来，该把那些躲在城里的名字一个个挖出来。", "neutral"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "铁血丹心.mp3",
        background_top=(163, 177, 204),
        background_bottom=(81, 100, 131),
        accent=(255, 242, 210),
        effect="wind",
        sfx=(SfxCue(ROOT_DIR / "assets" / "audio" / "潺潺流水声.wav", 0.0, 0.08),),
    ),
]


def _ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required")
    return ffmpeg


def _ffprobe_duration(path: Path) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe is required")
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return max(0.0, float((result.stdout or "0").strip() or 0.0))


@lru_cache(maxsize=16)
def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REGULAR), size=size)


def _render_scale() -> float:
    return poseviz.render_scale_for_size(WIDTH, HEIGHT)


def _ui_scale() -> float:
    return max(0.66, _render_scale() * 0.92)


def _ui_px(value: int) -> int:
    return max(1, int(round(value * _ui_scale())))


def _ui_font_px(value: int) -> int:
    return max(10, _ui_px(value) - 2)


def _actor_layout_scale() -> float:
    return 0.78 + 0.22 * _render_scale()


def _height_relative(value: float) -> float:
    return value / DEFAULT_HEIGHT * HEIGHT


@lru_cache(maxsize=64)
def _effect_path(effect_name: str) -> Path | None:
    assets = {
        "电闪雷鸣": ROOT_DIR / "assets" / "effects" / "电闪雷鸣.gif",
        "风起云涌": ROOT_DIR / "assets" / "effects" / "风起云涌.gif",
        "命中特效": ROOT_DIR / "assets" / "effects" / "命中特效.gif",
        "银河旋转特效": ROOT_DIR / "assets" / "effects" / "银河旋转特效.gif",
        "熊熊大火": ROOT_DIR / "assets" / "effects" / "熊熊大火.gif",
        "爆炸特效": ROOT_DIR / "assets" / "effects" / "爆炸特效.webp",
        "启动大招特效": ROOT_DIR / "assets" / "effects" / "启动大招特效.webp",
        "夕阳武士": ROOT_DIR / "assets" / "effects" / "夕阳武士.gif",
    }
    path = assets.get(effect_name)
    if path and path.exists():
        return path
    return None


@lru_cache(maxsize=64)
def _effect_frames(effect_name: str) -> tuple[Image.Image, ...]:
    path = _effect_path(effect_name)
    if path is None:
        return tuple()
    with Image.open(path) as image:
        total = max(1, int(getattr(image, "n_frames", 1)))
        frames: list[Image.Image] = []
        for index in range(total):
            image.seek(index)
            frame = image.convert("RGBA")
            if frame.size != (WIDTH, HEIGHT):
                frames.append(frame.copy())
            else:
                frames.append(frame.copy())
        return tuple(frames)


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for ch in text:
        trial = current + ch
        width = font.getbbox(trial)[2] - font.getbbox(trial)[0]
        if current and width > max_width:
            lines.append(current)
            current = ch
        else:
            current = trial
    if current:
        lines.append(current)
    return lines or [text]


@lru_cache(maxsize=64)
def _track(track_name: str) -> poseviz.PoseTrack:
    return poseviz._load_track(poseviz.POSE_DIR / f"{track_name}.pose.json", width=WIDTH, height=HEIGHT)


@lru_cache(maxsize=64)
def _has_track(track_name: str) -> bool:
    return (poseviz.POSE_DIR / f"{track_name}.pose.json").exists()


@lru_cache(maxsize=32)
def _textures(character_id: str) -> poseviz.TexturePack:
    return poseviz._load_texture_pack(character_id)


def _all_head_size() -> int:
    values = [_track(actor.track_name).head_size for scene in SCENES for actor in scene.actors]
    scale = _render_scale()
    min_head = max(28, int(round(62 * scale)))
    max_head = max(min_head + 8, int(round(80 * scale)))
    base = int(round(sum(values) / len(values) * 0.82))
    return max(min_head, min(max_head, base))


def _set_render_profile(*, fast: bool = False, fast2: bool = False, fast3: bool = False) -> int:
    global WIDTH, HEIGHT, GROUND_Y, EFFECT_DENSITY, TMP_DIR, RENDER_PROFILE
    if fast3:
        WIDTH = FAST3_WIDTH
        HEIGHT = FAST3_HEIGHT
        EFFECT_DENSITY = 0.52
        TMP_DIR = TMP_ROOT / "fast3"
        fps = FAST3_FPS
        RENDER_PROFILE = "fast3"
    elif fast2:
        WIDTH = FAST2_WIDTH
        HEIGHT = FAST2_HEIGHT
        EFFECT_DENSITY = 0.45
        TMP_DIR = TMP_ROOT / "fast2"
        fps = FAST2_FPS
        RENDER_PROFILE = "fast2"
    elif fast:
        WIDTH = FAST_WIDTH
        HEIGHT = FAST_HEIGHT
        EFFECT_DENSITY = 0.72
        TMP_DIR = TMP_ROOT / "fast"
        fps = FAST_FPS
        RENDER_PROFILE = "fast"
    else:
        WIDTH = DEFAULT_WIDTH
        HEIGHT = DEFAULT_HEIGHT
        EFFECT_DENSITY = 1.0
        TMP_DIR = TMP_ROOT / "normal"
        fps = DEFAULT_FPS
        RENDER_PROFILE = "normal"
    GROUND_Y = HEIGHT * 0.82
    _track.cache_clear()
    _effect_frames.cache_clear()
    return fps


def _scaled_effect_count(base: int) -> int:
    return max(1, int(round(base * EFFECT_DENSITY)))


def _default_idle_track(actor: ActorSpec, requested: str) -> str:
    palette = poseviz.CHARACTER_PALETTES.get(actor.character_id)
    feminine = actor.character_id in {"npc-girl", "office-worker-modern", "reporter-selfie"} or actor.character_id.startswith("face-") and actor.character_id in {"face-5", "face-7", "face-8", "face-13", "face-14", "face-15", "face-16"}
    if feminine:
        if requested == "掐腰站立" and _has_track("女人单手掐腰站立"):
            return "女人单手掐腰站立"
        if requested in {"站立", "放松站立"} and _has_track("女人站立"):
            return "女人站立"
    if requested == "站立" and _has_track("放松站立"):
        return "放松站立"
    return requested


async def _synthesize_tts(text: str, voice: str, output_path: Path, *, refresh: bool = False) -> None:
    if not refresh and output_path.exists() and output_path.stat().st_size > 0:
        return
    existing_ok = output_path.exists() and output_path.stat().st_size > 0
    temp_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            communicate = edge_tts.Communicate(text=text, voice=voice, rate="+0%")
            if temp_path.exists():
                temp_path.unlink()
            await communicate.save(str(temp_path))
            if temp_path.stat().st_size <= 0:
                raise RuntimeError(f"TTS output is empty: {temp_path}")
            temp_path.replace(output_path)
            return
        except Exception as exc:
            last_error = exc
            if temp_path.exists():
                temp_path.unlink()
            await asyncio.sleep(1.2 * (attempt + 1))
    if existing_ok:
        return
    assert last_error is not None
    raise last_error


def _scene_paths(scene: SceneSpec) -> dict[str, Path]:
    scene_dir = TMP_DIR / f"scene_{scene.scene_id}"
    scene_dir.mkdir(parents=True, exist_ok=True)
    return {
        "dir": scene_dir,
        "audio": scene_dir / "scene_audio.m4a",
        "video": scene_dir / "scene_video.mp4",
        "scene_mp4": scene_dir / f"{scene.scene_id}.mp4",
    }


def _build_schedule(scene: SceneSpec, scene_dir: Path, *, refresh_tts: bool = False) -> tuple[list[ScheduledLine], float]:
    actor_map = {actor.actor_id: actor for actor in scene.actors}
    schedule: list[ScheduledLine] = []
    cursor = scene.hold_s
    for index, line in enumerate(scene.lines, start=1):
        actor = actor_map[line.speaker_id]
        tts_path = scene_dir / f"line_{index:02d}.mp3"
        asyncio.run(_synthesize_tts(line.text, actor.voice, tts_path, refresh=refresh_tts))
        duration_s = _ffprobe_duration(tts_path)
        schedule.append(
            ScheduledLine(
                speaker_id=actor.actor_id,
                speaker_label=actor.label,
                text=line.text,
                expression=line.expression,
                track_name=line.track_name,
                voice=actor.voice,
                tts_path=tts_path,
                start_s=cursor,
                end_s=cursor + duration_s,
                duration_s=duration_s,
            )
        )
        cursor += duration_s + TALK_GAP_S
    scene_duration = max(cursor + 0.4, 5.0)
    return schedule, scene_duration


def _mix_scene_audio(scene: SceneSpec, schedule: list[ScheduledLine], duration_s: float, output_path: Path) -> None:
    ffmpeg = _ffmpeg()
    command = [ffmpeg, "-y", "-stream_loop", "-1", "-i", str(scene.bgm_path)]
    for line in schedule:
        command.extend(["-i", str(line.tts_path)])
    for cue in scene.sfx:
        command.extend(["-i", str(cue.path)])

    filters = [f"[0:a]atrim=0:{duration_s:.3f},asetpts=N/SR/TB,volume=0.16[bgm]"]
    mix_inputs = ["[bgm]"]
    for index, line in enumerate(schedule, start=1):
        delay_ms = int(line.start_s * 1000)
        label = f"tts{index}"
        filters.append(f"[{index}:a]adelay={delay_ms}|{delay_ms},volume=1.12[{label}]")
        mix_inputs.append(f"[{label}]")
    base_index = 1 + len(schedule)
    for cue_index, cue in enumerate(scene.sfx, start=base_index):
        label = f"sfx{cue_index}"
        delay_ms = int(cue.offset_s * 1000)
        filters.append(f"[{cue_index}:a]adelay={delay_ms}|{delay_ms},volume={cue.volume:.3f}[{label}]")
        mix_inputs.append(f"[{label}]")
    filters.append(f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)},alimiter=limit=0.92[aout]")
    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[aout]",
            "-t",
            f"{duration_s:.3f}",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(output_path),
        ]
    )
    subprocess.run(command, check=True)


def _gradient_background(image: Image.Image, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(image)
    for y in range(image.height):
        alpha = y / max(1, image.height - 1)
        color = tuple(int(top[i] * (1.0 - alpha) + bottom[i] * alpha) for i in range(3))
        draw.line((0, y, image.width, y), fill=color, width=1)


def _effect_trigger_times(scene: SceneSpec, duration_s: float) -> tuple[float, ...]:
    hints = EFFECT_AUDIO_HINTS.get(scene.effect, ())
    starts: list[float] = []
    if hints:
        for cue in scene.sfx:
            cue_name = cue.path.stem
            if any(hint in cue_name for hint in hints):
                starts.append(max(0.0, min(duration_s, cue.offset_s)))
    if not starts and scene.sfx:
        starts = [max(0.0, min(duration_s, cue.offset_s)) for cue in scene.sfx]
    if not starts:
        starts = [max(0.0, duration_s * 0.35)]
    deduped: list[float] = []
    for start_s in sorted(starts):
        if not deduped or abs(start_s - deduped[-1]) > 0.08:
            deduped.append(start_s)
    return tuple(deduped)


def _draw_effect(image: Image.Image, draw: ImageDraw.ImageDraw, scene: SceneSpec, t_s: float, duration_s: float) -> None:
    if EFFECT_DENSITY <= 0.0:
        return
    effect_spec = EFFECT_ASSET_MAP.get(scene.effect)
    if effect_spec is None:
        return
    effect_name, box_ratio, alpha = effect_spec
    frames = _effect_frames(effect_name)
    if not frames:
        return
    effect_duration = EFFECT_ONE_SHOT_DURATION_S.get(scene.effect, 1.4)
    active_start_s: float | None = None
    for start_s in _effect_trigger_times(scene, duration_s):
        end_s = min(duration_s, start_s + effect_duration)
        if start_s <= t_s <= end_s:
            active_start_s = start_s
            active_end_s = max(start_s + 0.001, end_s)
            break
    if active_start_s is None:
        return
    local_progress = (t_s - active_start_s) / max(0.001, active_end_s - active_start_s)
    effect_progress = max(0.0, min(1.0, local_progress * EFFECT_PLAYBACK_RATE))
    frame_index = min(len(frames) - 1, int(effect_progress * len(frames)))
    frame = frames[frame_index].copy()
    target_alpha = int(round(EFFECT_ALPHA_MIN + (EFFECT_ALPHA_MAX - EFFECT_ALPHA_MIN) * max(0.0, min(1.0, alpha))))
    channel = frame.getchannel("A").point(
        lambda value: 0 if value <= 0 else max(EFFECT_ALPHA_MIN, min(EFFECT_ALPHA_MAX, int(round(value * target_alpha / 255.0))))
    )
    frame.putalpha(channel)
    x = int(round(box_ratio[0] * WIDTH))
    y = int(round(box_ratio[1] * HEIGHT))
    w = max(4, int(round(box_ratio[2] * WIDTH)))
    h = max(4, int(round(box_ratio[3] * HEIGHT)))
    frame = frame.resize((w, h), Image.Resampling.LANCZOS)
    image.alpha_composite(frame, (x, y))


def _draw_caption(draw: ImageDraw.ImageDraw, scene: SceneSpec, progress: float) -> None:
    title_font = _font(_ui_font_px(26), bold=True)
    scene_font = _font(_ui_font_px(22), bold=True)
    x0 = _ui_px(28)
    y0 = _ui_px(24)
    x1 = _ui_px(470)
    y1 = _ui_px(126)
    draw.rounded_rectangle((x0, y0, x1, y1), radius=_ui_px(20), fill=(14, 18, 28, 208))
    draw.text((_ui_px(48), _ui_px(42)), TITLE, fill=(248, 244, 235), font=title_font)
    draw.text((_ui_px(48), _ui_px(78)), f"{scene.scene_id}  {scene.title}", fill=scene.accent, font=scene_font)
    if RENDER_PROFILE == "fast3":
        return
    bar_x = _ui_px(48)
    bar_y0 = _ui_px(110)
    bar_y1 = _ui_px(118)
    bar_max = _ui_px(320)
    bar_w = int(bar_max * min(1.0, max(0.0, progress)))
    draw.rounded_rectangle((bar_x, bar_y0, bar_x + bar_max, bar_y1), radius=_ui_px(4), fill=(82, 88, 106))
    draw.rounded_rectangle((bar_x, bar_y0, bar_x + bar_w, bar_y1), radius=_ui_px(4), fill=scene.accent)


def _draw_subtitle(draw: ImageDraw.ImageDraw, label: str, text: str) -> None:
    name_font = _font(_ui_font_px(24), bold=True)
    text_font = _font(_ui_font_px(26), bold=False)
    subtitle_margin = _ui_px(38)
    subtitle_bottom = _ui_px(28)
    plate_radius = _ui_px(18)
    line_gap = _ui_px(30)
    label_x = _ui_px(60)
    text_offset = _ui_px(44)
    lines = _wrap_text(f"{label}：{text}", text_font, WIDTH - subtitle_margin * 2 - _ui_px(24))
    plate_h = _ui_px(82) + max(0, len(lines) - 1) * line_gap
    y0 = HEIGHT - plate_h - subtitle_bottom
    draw.rounded_rectangle((subtitle_margin, y0, WIDTH - subtitle_margin, HEIGHT - subtitle_bottom), radius=plate_radius, fill=(16, 18, 24, 220))
    draw.text((label_x, y0 + _ui_px(18)), label, fill=(255, 226, 172), font=name_font)
    text_y = y0 + _ui_px(18)
    for idx, line in enumerate(lines):
        prefix = f"{label}：" if idx == 0 else ""
        content = line[len(prefix) :] if idx == 0 and line.startswith(prefix) else line
        offset_x = text_offset if idx == 0 else 0
        draw.text((label_x + offset_x, text_y), content, fill=(247, 244, 238), font=text_font)
        text_y += line_gap


def _render_scene_base(scene: SceneSpec) -> Image.Image:
    image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
    _gradient_background(image, scene.background_top, scene.background_bottom)
    draw = ImageDraw.Draw(image, "RGBA")
    _draw_caption(draw, scene, 1.0 if RENDER_PROFILE == "fast3" else 0.0)
    return image


def _render_subtitle_overlay(label: str, text: str) -> Image.Image:
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    _draw_subtitle(draw, label, text)
    return overlay


def _active_line(schedule: list[ScheduledLine], t_s: float) -> ScheduledLine | None:
    for item in schedule:
        if item.start_s <= t_s <= item.end_s:
            return item
    return None


def _actor_stage_points(
    actor: ActorSpec,
    track: poseviz.PoseTrack,
    points: dict[str, poseviz.np.ndarray],
) -> dict[str, tuple[float, float]]:
    base = {name: poseviz._stage_point(track, point, width=WIDTH, height=HEIGHT) for name, point in points.items()}
    stage: dict[str, tuple[float, float]] = {}
    layout_scale = _actor_layout_scale()
    actor_scale = actor.scale * layout_scale
    actor_offset = _height_relative(actor.x_offset) * layout_scale
    anchor_x = WIDTH * 0.5 + actor_offset
    for name, (x, y) in base.items():
        stage_x = WIDTH * 0.5 + (x - WIDTH * 0.5) * actor_scale + actor_offset
        if actor.mirror:
            stage_x = anchor_x - (stage_x - anchor_x)
        stage_y = GROUND_Y + (y - GROUND_Y) * actor_scale
        stage[name] = (stage_x, stage_y)
    return stage


def _render_actor_overlay(
    actor: ActorSpec,
    active: ScheduledLine | None,
    t_s: float,
    head_size: int,
    fps: int,
) -> Image.Image:
    image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw_scale = _render_scale()
    layout_scale = _actor_layout_scale()
    limb_width = max(8, int(round(poseviz.LIMB_WIDTH * draw_scale)))
    joint_radius = max(4, int(round(poseviz.JOINT_RADIUS * draw_scale)))
    speaking = active is not None and active.speaker_id == actor.actor_id
    requested_track = active.track_name if speaking and active.track_name else actor.track_name
    track_name = requested_track if speaking else _default_idle_track(actor, requested_track)
    track = _track(track_name)
    if not speaking:
        sample_t = 0.0
    elif track_name in ACTION_TRACKS:
        line_t = 0.0 if active is None else max(0.0, t_s - active.start_s)
        sample_t = (line_t * 0.55) % max(track.total_duration_s, 0.001)
    else:
        line_t = 0.0 if active is None else max(0.0, t_s - active.start_s)
        sample_t = min(track.total_duration_s * 0.12, line_t * 0.08)
    points = poseviz._sample_track(track, sample_t)
    stage_points = _actor_stage_points(actor, track, points)
    textures = _textures(actor.character_id)
    palette = poseviz._palette_for_character(actor.character_id)
    draw = ImageDraw.Draw(image, "RGBA")
    for start, end in poseviz.POSE_EDGES:
        if start not in LEG_POINTS or start not in stage_points or end not in stage_points:
            continue
        draw.line((*stage_points[start], *stage_points[end]), fill=poseviz._edge_color(start, palette), width=limb_width, joint="curve")
    for name, (x, y) in stage_points.items():
        if name in {"nose", "left_hip", "right_hip"} or name not in LEG_POINTS:
            continue
        radius = joint_radius
        color = poseviz._joint_color(name, palette)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
    poseviz._draw_torso(draw, stage_points, palette)
    poseviz._draw_torso_texture(image, stage_points, textures)
    draw = ImageDraw.Draw(image, "RGBA")
    for start, end in poseviz.POSE_EDGES:
        if start not in ARM_POINTS or start not in stage_points or end not in stage_points:
            continue
        draw.line((*stage_points[start], *stage_points[end]), fill=poseviz._edge_color(start, palette), width=limb_width, joint="curve")
    for name, (x, y) in stage_points.items():
        if name in {"nose", "left_hip", "right_hip"} or name not in ARM_POINTS:
            continue
        radius = joint_radius
        color = poseviz._joint_color(name, palette)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
    mouth_open = speaking and (int(t_s * fps) % TALK_MOUTH_CYCLE_FRAMES) < (TALK_MOUTH_CYCLE_FRAMES // 2)
    expression = active.expression if speaking else actor.expression
    face_texture = poseviz._load_face_texture(actor.character_id, expression=expression, talking=speaking, mouth_open=mouth_open)
    head_draw_size = int(head_size * actor.scale * layout_scale)
    poseviz._draw_panda_head(image, draw, stage_points, size=head_draw_size, textures=textures, face_texture=face_texture)
    head_center = poseviz._head_center(stage_points)
    if head_center is not None:
        label_font = _font(_ui_font_px(20), bold=True)
        bubble_color = (255, 230, 172, 220) if speaking else (18, 22, 32, 188)
        text_color = (78, 42, 20) if speaking else (240, 240, 240)
        text_w = label_font.getbbox(actor.label)[2] - label_font.getbbox(actor.label)[0]
        cx, _ = head_center
        bubble_w = text_w + _ui_px(36)
        bubble_h = _ui_px(34)
        foot_y = max(point[1] for point in stage_points.values())
        box_x0 = cx - bubble_w * 0.5
        box_y0 = foot_y + _ui_px(10)
        box_x0 = max(_ui_px(12), min(WIDTH - bubble_w - _ui_px(12), box_x0))
        box_y0 = max(_ui_px(12), min(HEIGHT - bubble_h - _ui_px(12), box_y0))
        box = (
            box_x0,
            box_y0,
            box_x0 + bubble_w,
            box_y0 + bubble_h,
        )
        draw.rounded_rectangle(box, radius=_ui_px(12), fill=bubble_color)
        draw.text((box[0] + _ui_px(16), box[1] + _ui_px(6)), actor.label, fill=text_color, font=label_font)
    return image


def _draw_actor(
    image: Image.Image,
    actor: ActorSpec,
    active: ScheduledLine | None,
    t_s: float,
    head_size: int,
    fps: int,
) -> None:
    image.alpha_composite(_render_actor_overlay(actor, active, t_s, head_size, fps))


def _render_scene_frame(scene: SceneSpec, schedule: list[ScheduledLine], duration_s: float, t_s: float, head_size: int, fps: int) -> Image.Image:
    image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
    _gradient_background(image, scene.background_top, scene.background_bottom)
    progress = 0.0 if duration_s <= 1e-6 else max(0.0, min(1.0, t_s / duration_s))
    active = _active_line(schedule, t_s)
    for actor in scene.actors:
        if not actor.visible:
            continue
        _draw_actor(image, actor, active, t_s, head_size, fps)
    draw = ImageDraw.Draw(image, "RGBA")
    _draw_caption(draw, scene, progress)
    if active is not None:
        _draw_subtitle(draw, active.speaker_label, active.text)
    draw = ImageDraw.Draw(image, "RGBA")
    _draw_effect(image, draw, scene, t_s, duration_s)
    return image.convert("RGB")


def _render_scene_video(
    scene: SceneSpec,
    schedule: list[ScheduledLine],
    duration_s: float,
    head_size: int,
    output_path: Path,
    fps: int,
    *,
    fast: bool,
    fast2: bool,
    fast3: bool,
) -> None:
    preset, crf = poseviz._encoding_profile(fast=fast, fast2=fast2, fast3=fast3)
    proc = poseviz._open_ffmpeg_stream(fps, WIDTH, HEIGHT, output_path, preset=preset, crf=crf)
    try:
        assert proc.stdin is not None
        total_frames = max(1, int(round(duration_s * fps)))
        base_frame = _render_scene_base(scene) if fast3 else None
        static_actors = {
            actor.actor_id: _render_actor_overlay(actor, None, 0.0, head_size, fps)
            for actor in scene.actors
            if actor.visible
        } if fast3 else {}
        subtitle_overlays = {
            (item.speaker_label, item.text): _render_subtitle_overlay(item.speaker_label, item.text)
            for item in schedule
        } if fast3 else {}
        for frame_index in range(total_frames):
            t_s = frame_index / fps
            if fast3:
                frame = base_frame.copy()
                progress = 0.0 if duration_s <= 1e-6 else max(0.0, min(1.0, t_s / duration_s))
                active = _active_line(schedule, t_s)
                for actor in scene.actors:
                    if not actor.visible:
                        continue
                    if active is not None and active.speaker_id == actor.actor_id:
                        frame.alpha_composite(_render_actor_overlay(actor, active, t_s, head_size, fps))
                    else:
                        frame.alpha_composite(static_actors[actor.actor_id])
                if active is not None:
                    frame.alpha_composite(subtitle_overlays[(active.speaker_label, active.text)])
                draw = ImageDraw.Draw(frame, "RGBA")
                _draw_effect(frame, draw, scene, t_s, duration_s)
                proc.stdin.write(frame.convert("RGB").tobytes())
            else:
                frame = _render_scene_frame(scene, schedule, duration_s, t_s, head_size, fps)
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
    head_size = _all_head_size()
    scene_outputs: list[Path] = []
    for scene in SCENES:
        paths = _scene_paths(scene)
        if not force and paths["scene_mp4"].exists() and paths["scene_mp4"].stat().st_size > 0:
            scene_outputs.append(paths["scene_mp4"])
            print(paths["scene_mp4"])
            continue
        schedule, duration_s = _build_schedule(scene, paths["dir"], refresh_tts=force)
        _mix_scene_audio(scene, schedule, duration_s, paths["audio"])
        _render_scene_video(scene, schedule, duration_s, head_size, paths["video"], fps, fast=fast, fast2=fast2, fast3=fast3)
        _mux_scene(paths["video"], paths["audio"], paths["scene_mp4"])
        scene_outputs.append(paths["scene_mp4"])
        print(paths["scene_mp4"])
    _concat_scenes(scene_outputs, output_path)
    print(output_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a multi-character Water Margin dialogue story using DNN pose stickman actors with Chinese subtitles, TTS, BGM, SFX, and action blocking.")
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
