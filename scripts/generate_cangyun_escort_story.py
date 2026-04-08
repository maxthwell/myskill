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
from PIL import Image, ImageDraw, ImageFont

import generate_actions_pose_reconstruction as poseviz


ROOT_DIR = Path(__file__).resolve().parents[1]
TMP_DIR = ROOT_DIR / "tmp" / "direct_runs" / "cangyun_escort_story"
OUTPUT_DEFAULT = ROOT_DIR / "outputs" / "cangyun_escort_story.mp4"
FPS = 24
WIDTH = 960
HEIGHT = 540
TITLE = "苍云镖路"
GROUND_Y = HEIGHT * 0.82
TALK_GAP_S = 0.28
TALK_MOUTH_CYCLE_FRAMES = 4
FONT_REGULAR = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
FONT_BOLD = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
ACTION_TRACKS = {"拳击", "翻跟头gif", "人物A飞踢倒人物B", "舞剑", "跑", "连续后空翻", "降龙十八掌", "鲤鱼打挺"}
LEG_POINTS = {"left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle"}
ARM_POINTS = {"left_shoulder", "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist"}


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
        title="夜领血书",
        actors=(
            ActorSpec("xie", "谢长风", "farmer-old", "zh-CN-YunjianNeural", "放松站立", "serious", -220, 0.84),
            ActorSpec("lin", "林沧州", "general-guard", "zh-CN-YunxiNeural", "站立", "focused", 0, 0.98),
            ActorSpec("su", "苏清遥", "npc-girl", "zh-CN-XiaoxiaoNeural", "站立", "neutral", 230, 0.88),
        ),
        lines=(
            LineSpec("xie", "苍云关外三营将变，只有这封血书，能证陈堂主勾结铁无锋。", "serious"),
            LineSpec("lin", "师父放心，血书不入敌手，我也不会倒在半路。", "focused"),
            LineSpec("su", "我管封匣和药囊，你负责出刀。今夜我们就离城。", "focused"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "铁血丹心.mp3",
        background_top=(54, 49, 66),
        background_bottom=(16, 14, 26),
        accent=(242, 216, 158),
        effect="embers",
        sfx=(SfxCue(ROOT_DIR / "assets" / "audio" / "心脏怦怦跳.wav", 0.7, 0.12),),
    ),
    SceneSpec(
        scene_id="02",
        title="晨门启程",
        actors=(
            ActorSpec("lin", "林沧州", "general-guard", "zh-CN-YunxiNeural", "站立", "neutral", -180, 0.98),
            ActorSpec("su", "苏清遥", "npc-girl", "zh-CN-XiaoxiaoNeural", "站立", "smile", 30, 0.88),
            ActorSpec("han", "韩七", "detective-sleek", "zh-CN-YunjianNeural", "掐腰站立", "skeptical", 250, 0.9),
        ),
        lines=(
            LineSpec("han", "城门外三十里有雨桥，黑沙堂最爱在那里截镖。", "skeptical"),
            LineSpec("lin", "那就别走官道，先绕旧河埠，再折进竹林。", "neutral"),
            LineSpec("su", "真匣藏在马鞍底，给他们留下一个假的。", "smile"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "男儿当自强.mp3",
        background_top=(231, 216, 185),
        background_bottom=(164, 126, 79),
        accent=(117, 66, 30),
        effect="wind",
        sfx=(SfxCue(ROOT_DIR / "assets" / "audio" / "潺潺流水声.wav", 0.0, 0.08),),
    ),
    SceneSpec(
        scene_id="03",
        title="客栈探风",
        actors=(
            ActorSpec("inn", "店家", "farmer-old", "zh-CN-YunjianNeural", "放松站立", "nervous", -190, 0.82),
            ActorSpec("lin", "林沧州", "general-guard", "zh-CN-YunxiNeural", "站立", "focused", 10, 0.98),
            ActorSpec("su", "苏清遥", "npc-girl", "zh-CN-XiaoxiaoNeural", "坐下", "skeptical", 240, 0.84),
        ),
        lines=(
            LineSpec("inn", "昨夜有人包下后院，只问两件事，苍云镖局和苏姑娘。", "nervous"),
            LineSpec("lin", "果然有人先我们一步布网。", "focused"),
            LineSpec("su", "那就让他们盯着假匣，我们从后窗走。", "skeptical"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "历史的天空-古筝-三国演义片尾曲.mp3",
        background_top=(208, 184, 150),
        background_bottom=(112, 83, 60),
        accent=(250, 231, 202),
        effect="dust",
        sfx=(SfxCue(ROOT_DIR / "assets" / "audio" / "心脏怦怦跳.wav", 1.8, 0.1),),
    ),
    SceneSpec(
        scene_id="04",
        title="雨桥截镖",
        actors=(
            ActorSpec("lin", "林沧州", "general-guard", "zh-CN-YunxiNeural", "站立", "angry", -180, 0.98, True),
            ActorSpec("su", "苏清遥", "npc-girl", "zh-CN-XiaoxiaoNeural", "站立", "focused", 20, 0.88),
            ActorSpec("sha", "杀手", "official-minister", "zh-CN-YunjianNeural", "拳击", "angry", 260, 0.9),
        ),
        lines=(
            LineSpec("sha", "黑沙堂只要匣子，你们把命留下就够了。", "angry", "拳击"),
            LineSpec("lin", "货在我身后，命在我手里。你来拿试试。", "angry", "拳击"),
            LineSpec("su", "左边桥柱有火油，我点灯，你出刀。", "focused", "跑"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "最后之战-热血-卢冠廷.mp3",
        background_top=(58, 78, 108),
        background_bottom=(12, 16, 28),
        accent=(208, 230, 255),
        effect="rain",
        sfx=(
            SfxCue(ROOT_DIR / "assets" / "audio" / "暴雨.wav", 0.0, 0.18),
            SfxCue(ROOT_DIR / "assets" / "audio" / "格斗打中.wav", 2.3, 0.82),
            SfxCue(ROOT_DIR / "assets" / "audio" / "一拳击中.wav", 4.4, 0.95),
        ),
    ),
    SceneSpec(
        scene_id="05",
        title="荒庙验箭",
        actors=(
            ActorSpec("lin", "林沧州", "general-guard", "zh-CN-YunxiNeural", "蹲下", "pained", -170, 0.94),
            ActorSpec("su", "苏清遥", "npc-girl", "zh-CN-XiaoxiaoNeural", "朝右跪坐", "focused", 70, 0.86),
            ActorSpec("han", "韩七", "detective-sleek", "zh-CN-YunjianNeural", "放松站立", "serious", 280, 0.9),
        ),
        lines=(
            LineSpec("su", "箭簇上有衙门火漆，不是草寇的手笔。", "focused"),
            LineSpec("han", "陈堂主果然和铁无锋通气，镖局里还有内线。", "serious"),
            LineSpec("lin", "从现在起，除了我们三个，谁也不知道真血书在哪。", "pained"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "思君黯然-天龙八部-悲伤.mp3",
        background_top=(70, 59, 62),
        background_bottom=(22, 18, 24),
        accent=(255, 198, 162),
        effect="fire",
        sfx=(SfxCue(ROOT_DIR / "assets" / "audio" / "心脏怦怦跳.wav", 1.2, 0.12),),
    ),
    SceneSpec(
        scene_id="06",
        title="江渡疑云",
        actors=(
            ActorSpec("qiu", "秋伯", "farmer-old", "zh-CN-YunjianNeural", "坐下", "thinking", -200, 0.82),
            ActorSpec("lin", "林沧州", "general-guard", "zh-CN-YunxiNeural", "站立", "skeptical", 20, 0.98),
            ActorSpec("su", "苏清遥", "npc-girl", "zh-CN-XiaoxiaoNeural", "站立", "neutral", 240, 0.88),
        ),
        lines=(
            LineSpec("qiu", "你们昨夜刚过桥，桥头就先亮了灯。这行程，是从城里漏出去的。", "thinking"),
            LineSpec("lin", "城里知情的只有师父、韩七和陈堂主。", "skeptical"),
            LineSpec("su", "韩七跟了我们一路，我信他。剩下那个，就该查了。", "neutral"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "芦苇荡-赵季平-大话西游.mp3",
        background_top=(92, 122, 132),
        background_bottom=(33, 51, 60),
        accent=(220, 239, 224),
        effect="wind",
        sfx=(SfxCue(ROOT_DIR / "assets" / "audio" / "潺潺流水声.wav", 0.0, 0.16),),
    ),
    SceneSpec(
        scene_id="07",
        title="竹林寻踪",
        actors=(
            ActorSpec("lin", "林沧州", "general-guard", "zh-CN-YunxiNeural", "站立", "angry", -190, 0.98, True),
            ActorSpec("han", "韩七", "detective-sleek", "zh-CN-YunjianNeural", "站立", "focused", 30, 0.9),
            ActorSpec("liu", "探子", "official-minister", "zh-CN-YunjianNeural", "人物A飞踢倒人物B", "angry", 270, 0.86),
        ),
        lines=(
            LineSpec("liu", "铁爷只要匣子，不想和你们多费口舌。", "angry", "人物A飞踢倒人物B"),
            LineSpec("han", "你们今晨在渡口换了三批眼线，我早记下了。", "focused"),
            LineSpec("lin", "说出接头地点，我让你走得痛快些。", "angry", "拳击"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "杀破狼.mp3",
        background_top=(56, 96, 64),
        background_bottom=(16, 33, 19),
        accent=(184, 235, 188),
        effect="burst",
        sfx=(
            SfxCue(ROOT_DIR / "assets" / "audio" / "031_26_赤手空拳打斗的声音_爱给网_aigei_com.mp3", 1.0, 0.82),
            SfxCue(ROOT_DIR / "assets" / "audio" / "格斗打中.wav", 3.0, 0.85),
        ),
    ),
    SceneSpec(
        scene_id="08",
        title="潜灯入衙",
        actors=(
            ActorSpec("lin", "林沧州", "general-guard", "zh-CN-YunxiNeural", "站立", "focused", -180, 0.98),
            ActorSpec("su", "苏清遥", "npc-girl", "zh-CN-XiaoxiaoNeural", "站立", "smile", 30, 0.88),
            ActorSpec("clerk", "守册吏", "official-minister", "zh-CN-YunjianNeural", "放松站立", "skeptical", 250, 0.86),
        ),
        lines=(
            LineSpec("clerk", "卷宗重地，夜里不许进人。", "skeptical"),
            LineSpec("su", "那你就当今夜没看见我们。", "smile"),
            LineSpec("lin", "找苍云关军粮册，凡是红章封过的，全带走。", "focused"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "误入迷失森林-少年包青天.mp3",
        background_top=(52, 62, 84),
        background_bottom=(15, 18, 33),
        accent=(224, 235, 250),
        effect="thunder",
        sfx=(SfxCue(ROOT_DIR / "assets" / "audio" / "打雷闪电.wav", 1.6, 0.42),),
    ),
    SceneSpec(
        scene_id="09",
        title="地牢救师",
        actors=(
            ActorSpec("lin", "林沧州", "general-guard", "zh-CN-YunxiNeural", "站立", "angry", -190, 0.98, True),
            ActorSpec("xie", "谢长风", "farmer-old", "zh-CN-YunjianNeural", "朝右跪坐", "serious", 10, 0.82),
            ActorSpec("guard", "狱卒", "official-minister", "zh-CN-YunjianNeural", "拳击", "angry", 260, 0.86),
        ),
        lines=(
            LineSpec("guard", "陈堂主说了，谢长风一死，所有旧案都能沉底。", "angry", "拳击"),
            LineSpec("xie", "别管我，先把血书送去苍云关。", "serious"),
            LineSpec("lin", "师父，我既然来了，就带你一起走。", "angry", "舞剑"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "最后之战-热血-卢冠廷.mp3",
        background_top=(72, 36, 28),
        background_bottom=(18, 9, 12),
        accent=(255, 208, 184),
        effect="fire",
        sfx=(
            SfxCue(ROOT_DIR / "assets" / "audio" / "刀剑、金属碰撞（带回音）_爱给网_aigei_com.mp3", 2.0, 0.82),
            SfxCue(ROOT_DIR / "assets" / "audio" / "格斗打中.wav", 4.0, 0.82),
        ),
    ),
    SceneSpec(
        scene_id="10",
        title="夜巷追命",
        actors=(
            ActorSpec("lin", "林沧州", "general-guard", "zh-CN-YunxiNeural", "跑", "angry", -180, 0.98, True),
            ActorSpec("su", "苏清遥", "npc-girl", "zh-CN-XiaoxiaoNeural", "跑", "focused", 20, 0.88),
            ActorSpec("han", "韩七", "detective-sleek", "zh-CN-YunjianNeural", "跑", "serious", 250, 0.9),
        ),
        lines=(
            LineSpec("han", "后巷全是弩手，前街是刀阵，陈堂主这是要把我们困死在城里。", "serious"),
            LineSpec("su", "我往西巷撒烟粉，你带师父走屋脊。", "focused"),
            LineSpec("lin", "今夜先出城，明早再和他们算总账。", "angry", "跑"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "杀破狼.mp3",
        background_top=(27, 36, 61),
        background_bottom=(7, 8, 18),
        accent=(208, 226, 255),
        effect="thunder",
        sfx=(
            SfxCue(ROOT_DIR / "assets" / "audio" / "打雷闪电.wav", 0.9, 0.52),
            SfxCue(ROOT_DIR / "assets" / "audio" / "暴雨.wav", 0.0, 0.16),
        ),
    ),
    SceneSpec(
        scene_id="11",
        title="山寺逼供",
        actors=(
            ActorSpec("lin", "林沧州", "general-guard", "zh-CN-YunxiNeural", "站立", "serious", -180, 0.98),
            ActorSpec("xie", "谢长风", "farmer-old", "zh-CN-YunjianNeural", "坐下", "thinking", 30, 0.82),
            ActorSpec("liu", "探子", "official-minister", "zh-CN-YunjianNeural", "朝右跪坐", "fear", 260, 0.84),
        ),
        lines=(
            LineSpec("liu", "铁无锋今夜会在断雁坡收网，陈堂主亲自押后。", "fear"),
            LineSpec("xie", "他不是只要血书，他还要那枚开关铁券。", "thinking"),
            LineSpec("lin", "原来他们盯的从来不是镖，是苍云关的兵门。", "serious"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "思君黯然-天龙八部-悲伤.mp3",
        background_top=(66, 61, 70),
        background_bottom=(22, 20, 28),
        accent=(231, 214, 188),
        effect="embers",
        sfx=(SfxCue(ROOT_DIR / "assets" / "audio" / "心脏怦怦跳.wav", 2.0, 0.12),),
    ),
    SceneSpec(
        scene_id="12",
        title="绝壁采药",
        actors=(
            ActorSpec("su", "苏清遥", "npc-girl", "zh-CN-XiaoxiaoNeural", "蹲下", "pained", -180, 0.84),
            ActorSpec("yao", "药娘", "npc-girl", "zh-CN-XiaoxiaoNeural", "坐下", "neutral", 40, 0.82),
            ActorSpec("lin", "林沧州", "general-guard", "zh-CN-YunxiNeural", "站立", "focused", 250, 0.98),
        ),
        lines=(
            LineSpec("yao", "你中了裂骨散，不到寅时解毒，手脚都会废。", "neutral"),
            LineSpec("lin", "药在哪，你说。", "focused"),
            LineSpec("su", "断雁坡就在前面，别为我误了送信时辰。", "pained"),
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
        title="雪坡埋伏",
        actors=(
            ActorSpec("lin", "林沧州", "general-guard", "zh-CN-YunxiNeural", "站立", "angry", -190, 0.98, True),
            ActorSpec("su", "苏清遥", "npc-girl", "zh-CN-XiaoxiaoNeural", "站立", "focused", 30, 0.88),
            ActorSpec("tie", "铁无锋", "emperor-ming", "zh-CN-YunjianNeural", "拳击", "angry", 270, 0.92),
        ),
        lines=(
            LineSpec("tie", "一封血书，就想撬开苍云关？你们太天真了。", "angry", "拳击"),
            LineSpec("su", "你敢带人围坡，就说明陈堂主的退路还没布好。", "focused"),
            LineSpec("lin", "退路留给你自己吧，今天我先替雨桥那几条命讨债。", "angry", "拳击"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "男儿当自强.mp3",
        background_top=(174, 184, 198),
        background_bottom=(92, 102, 118),
        accent=(255, 234, 204),
        effect="impact",
        sfx=(
            SfxCue(ROOT_DIR / "assets" / "audio" / "一拳击中.wav", 2.5, 0.95),
            SfxCue(ROOT_DIR / "assets" / "audio" / "格斗打中.wav", 4.5, 0.88),
        ),
    ),
    SceneSpec(
        scene_id="14",
        title="旧阁焚卷",
        actors=(
            ActorSpec("su", "苏清遥", "npc-girl", "zh-CN-XiaoxiaoNeural", "站立", "angry", -180, 0.88),
            ActorSpec("han", "韩七", "detective-sleek", "zh-CN-YunjianNeural", "站立", "focused", 20, 0.9),
            ActorSpec("chen", "陈堂主", "official-minister", "zh-CN-YunjianNeural", "放松站立", "cold", 260, 0.88),
        ),
        lines=(
            LineSpec("chen", "只要旧卷一烧，谢长风当年的口供就成了疯话。", "cold"),
            LineSpec("han", "你借镖路运兵器，又借官印灭口，这笔账今夜算不清了。", "focused"),
            LineSpec("su", "烧吧，火越大，城里的人越知道你心虚。", "angry"),
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
        title="渡口换船",
        actors=(
            ActorSpec("qiu", "秋伯", "farmer-old", "zh-CN-YunjianNeural", "放松站立", "smile", -190, 0.82),
            ActorSpec("xie", "谢长风", "farmer-old", "zh-CN-YunjianNeural", "坐下", "neutral", 40, 0.8),
            ActorSpec("lin", "林沧州", "general-guard", "zh-CN-YunxiNeural", "站立", "neutral", 260, 0.98),
        ),
        lines=(
            LineSpec("qiu", "官船都被封了，只剩我这条破渡船，能走暗水。", "smile"),
            LineSpec("xie", "过了寒沙湾，再有半日就到苍云关。", "neutral"),
            LineSpec("lin", "今夜多谢秋伯，若我还能回来，替你重修这一渡。", "neutral"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "芦苇荡-赵季平-大话西游.mp3",
        background_top=(89, 122, 142),
        background_bottom=(27, 46, 63),
        accent=(229, 241, 228),
        effect="wind",
        sfx=(SfxCue(ROOT_DIR / "assets" / "audio" / "潺潺流水声.wav", 0.0, 0.15),),
    ),
    SceneSpec(
        scene_id="16",
        title="长街鸣刀",
        actors=(
            ActorSpec("han", "韩七", "detective-sleek", "zh-CN-YunjianNeural", "拳击", "angry", -190, 0.9, True),
            ActorSpec("lin", "林沧州", "general-guard", "zh-CN-YunxiNeural", "跑", "focused", 20, 0.98),
            ActorSpec("su", "苏清遥", "npc-girl", "zh-CN-XiaoxiaoNeural", "跑", "focused", 240, 0.88),
        ),
        lines=(
            LineSpec("han", "我留在街口断后，你们把人和证物送到关前！", "angry", "拳击"),
            LineSpec("su", "韩七，活着来寒寺会合！", "focused", "跑"),
            LineSpec("lin", "一炷香后不见你，我就回头拆了这条街！", "focused", "跑"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "杀破狼.mp3",
        background_top=(64, 55, 74),
        background_bottom=(20, 16, 27),
        accent=(244, 223, 193),
        effect="slash",
        sfx=(
            SfxCue(ROOT_DIR / "assets" / "audio" / "刀剑、金属碰撞（带回音）_爱给网_aigei_com.mp3", 1.7, 0.82),
            SfxCue(ROOT_DIR / "assets" / "audio" / "031_26_赤手空拳打斗的声音_爱给网_aigei_com.mp3", 3.6, 0.88),
        ),
    ),
    SceneSpec(
        scene_id="17",
        title="寒寺密誓",
        actors=(
            ActorSpec("xie", "谢长风", "farmer-old", "zh-CN-YunjianNeural", "坐下", "thinking", -210, 0.82),
            ActorSpec("lin", "林沧州", "general-guard", "zh-CN-YunxiNeural", "站立", "serious", 10, 0.98),
            ActorSpec("su", "苏清遥", "npc-girl", "zh-CN-XiaoxiaoNeural", "站立", "focused", 240, 0.88),
        ),
        lines=(
            LineSpec("xie", "二十年前苍云关兵变，陈堂主靠假军令，屠了整营斥候。", "thinking"),
            LineSpec("lin", "所以你把血书藏进镖路二十年，只等今日送到关前。", "serious"),
            LineSpec("su", "那我们就把这条路走到底，谁拦谁死。", "focused"),
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
        title="关前拒门",
        actors=(
            ActorSpec("feng", "封校尉", "official-minister", "zh-CN-YunjianNeural", "放松站立", "skeptical", -190, 0.86),
            ActorSpec("lin", "林沧州", "general-guard", "zh-CN-YunxiNeural", "站立", "angry", 20, 0.98),
            ActorSpec("su", "苏清遥", "npc-girl", "zh-CN-XiaoxiaoNeural", "站立", "angry", 240, 0.88),
        ),
        lines=(
            LineSpec("feng", "关门已封，今夜任何文书都不得入关。", "skeptical"),
            LineSpec("su", "你若不看这半卷军粮册，明天开的就不是关门，是棺材板。", "angry"),
            LineSpec("lin", "铁无锋的人就在后面。等他们到了，你连后悔都来不及。", "angry"),
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
        title="断碑决战",
        actors=(
            ActorSpec("lin", "林沧州", "general-guard", "zh-CN-YunxiNeural", "站立", "angry", -190, 0.98, True),
            ActorSpec("tie", "铁无锋", "emperor-ming", "zh-CN-YunjianNeural", "拳击", "angry", 170, 0.92),
            ActorSpec("chen", "陈堂主", "official-minister", "zh-CN-YunjianNeural", "放松站立", "cold", 330, 0.84),
        ),
        lines=(
            LineSpec("chen", "苍云关一开，你们谁也护不住那封血书。", "cold"),
            LineSpec("tie", "我挡住林沧州，你去杀谢长风！", "angry", "拳击"),
            LineSpec("lin", "你们今天谁也别想越过这块断碑。", "angry", "舞剑"),
        ),
        bgm_path=ROOT_DIR / "assets" / "bgm" / "最后之战-热血-卢冠廷.mp3",
        background_top=(108, 30, 28),
        background_bottom=(20, 8, 10),
        accent=(255, 222, 206),
        effect="impact",
        sfx=(
            SfxCue(ROOT_DIR / "assets" / "audio" / "刀剑、金属碰撞（带回音）_爱给网_aigei_com.mp3", 2.0, 0.86),
            SfxCue(ROOT_DIR / "assets" / "audio" / "格斗打中.wav", 4.7, 0.86),
            SfxCue(ROOT_DIR / "assets" / "audio" / "一拳击中.wav", 5.3, 0.95),
        ),
    ),
    SceneSpec(
        scene_id="20",
        title="血书昭世",
        actors=(
            ActorSpec("xie", "谢长风", "farmer-old", "zh-CN-YunjianNeural", "放松站立", "relieved", -200, 0.82),
            ActorSpec("su", "苏清遥", "npc-girl", "zh-CN-XiaoxiaoNeural", "站立", "smile", 20, 0.88),
            ActorSpec("lin", "林沧州", "general-guard", "zh-CN-YunxiNeural", "站立", "neutral", 250, 0.98),
        ),
        lines=(
            LineSpec("xie", "血书、军粮册、官印残蜡都在这里。陈堂主与铁无锋谋反的证据俱全。", "relieved"),
            LineSpec("su", "苍云关众军亲眼所见，这笔旧账，再也压不回黑夜里。", "smile"),
            LineSpec("lin", "关门既守住了，江湖路还长。等我们回城，再替死者一一讨名。", "neutral"),
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


@lru_cache(maxsize=32)
def _textures(character_id: str) -> poseviz.TexturePack:
    return poseviz._load_texture_pack(character_id)


def _all_head_size() -> int:
    values = [_track(actor.track_name).head_size for scene in SCENES for actor in scene.actors]
    base = int(round(sum(values) / len(values) * 0.88))
    return max(62, min(80, base))


async def _synthesize_tts(text: str, voice: str, output_path: Path) -> None:
    if output_path.exists() and output_path.stat().st_size > 0:
        return
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            communicate = edge_tts.Communicate(text=text, voice=voice, rate="+0%")
            await communicate.save(str(output_path))
            return
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(1.2 * (attempt + 1))
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


def _build_schedule(scene: SceneSpec, scene_dir: Path) -> tuple[list[ScheduledLine], float]:
    actor_map = {actor.actor_id: actor for actor in scene.actors}
    schedule: list[ScheduledLine] = []
    cursor = scene.hold_s
    for index, line in enumerate(scene.lines, start=1):
        actor = actor_map[line.speaker_id]
        tts_path = scene_dir / f"line_{index:02d}.mp3"
        asyncio.run(_synthesize_tts(line.text, actor.voice, tts_path))
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


def _draw_effect(draw: ImageDraw.ImageDraw, scene: SceneSpec, progress: float) -> None:
    accent = scene.accent
    if scene.effect == "rain":
        for index in range(16):
            x = (index * 73 + int(progress * 340)) % (WIDTH + 140) - 70
            y = (index * 37 + int(progress * 220)) % HEIGHT
            draw.line((x, y, x - 18, y + 38), fill=(*accent, 90), width=2)
    elif scene.effect == "wind":
        for index in range(4):
            y = 118 + index * 74 + math.sin(progress * 6.0 + index) * 10.0
            draw.arc((64, y - 18, WIDTH - 64, y + 22), 8, 170, fill=(*accent, 110), width=3)
    elif scene.effect == "impact":
        radius = 40 + progress * 130
        cx = WIDTH * 0.56
        cy = HEIGHT * 0.58
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=(*accent, 88), width=4)
    elif scene.effect == "slash":
        x0 = WIDTH * (0.2 + progress * 0.34)
        draw.line((x0, HEIGHT * 0.18, x0 + 180, HEIGHT * 0.8), fill=(*accent, 155), width=10)
        draw.line((x0 + 16, HEIGHT * 0.23, x0 + 168, HEIGHT * 0.76), fill=(255, 247, 236, 175), width=4)
    elif scene.effect == "thunder":
        if 0.2 < progress < 0.3:
            draw.rectangle((0, 0, WIDTH, HEIGHT), fill=(235, 242, 255, 90))
        bolt = [(WIDTH * 0.68, 0), (WIDTH * 0.62, 118), (WIDTH * 0.69, 118), (WIDTH * 0.57, 250), (WIDTH * 0.66, 250), (WIDTH * 0.55, 420)]
        draw.line(bolt, fill=(*accent, 180), width=6)
    elif scene.effect == "fire":
        for index in range(9):
            x = 90 + index * 92 + math.sin(progress * 7.0 + index) * 16.0
            flame_h = 80 + (index % 3) * 24
            draw.polygon([(x, HEIGHT), (x - 20, HEIGHT - flame_h * 0.4), (x, HEIGHT - flame_h), (x + 20, HEIGHT - flame_h * 0.4)], fill=(255, 140, 42, 92))
    elif scene.effect == "burst":
        cx = WIDTH * 0.56
        cy = HEIGHT * 0.54
        for index in range(8):
            angle = progress * math.tau + index * (math.tau / 8.0)
            x1 = cx + math.cos(angle) * 40
            y1 = cy + math.sin(angle) * 40
            x2 = cx + math.cos(angle) * 110
            y2 = cy + math.sin(angle) * 110
            draw.line((x1, y1, x2, y2), fill=(*accent, 138), width=5)
    elif scene.effect == "embers":
        for index in range(18):
            x = (index * 53 + int(progress * 250)) % WIDTH
            y = HEIGHT - ((index * 33 + int(progress * 310)) % HEIGHT)
            r = 3 + (index % 3)
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(*accent, 122))
    elif scene.effect == "dust":
        for index in range(12):
            x = (index * 81 + int(progress * 180)) % WIDTH
            y = HEIGHT * 0.78 + math.sin(progress * 4.0 + index) * 12.0
            draw.ellipse((x - 18, y - 8, x + 18, y + 8), fill=(*accent, 46))


def _draw_caption(draw: ImageDraw.ImageDraw, scene: SceneSpec, progress: float) -> None:
    title_font = _font(26, bold=True)
    scene_font = _font(22, bold=True)
    draw.rounded_rectangle((28, 24, 470, 126), radius=20, fill=(14, 18, 28, 208))
    draw.text((48, 42), TITLE, fill=(248, 244, 235), font=title_font)
    draw.text((48, 78), f"{scene.scene_id}  {scene.title}", fill=scene.accent, font=scene_font)
    bar_w = int(320 * min(1.0, max(0.0, progress)))
    draw.rounded_rectangle((48, 110, 368, 118), radius=4, fill=(82, 88, 106))
    draw.rounded_rectangle((48, 110, 48 + bar_w, 118), radius=4, fill=scene.accent)


def _draw_subtitle(draw: ImageDraw.ImageDraw, label: str, text: str) -> None:
    name_font = _font(24, bold=True)
    text_font = _font(26, bold=False)
    lines = _wrap_text(f"{label}：{text}", text_font, WIDTH - 140)
    plate_h = 82 + max(0, len(lines) - 1) * 30
    y0 = HEIGHT - plate_h - 28
    draw.rounded_rectangle((38, y0, WIDTH - 38, HEIGHT - 28), radius=18, fill=(16, 18, 24, 220))
    draw.text((60, y0 + 18), label, fill=(255, 226, 172), font=name_font)
    text_y = y0 + 18
    for idx, line in enumerate(lines):
        x = 60 if idx == 0 else 60
        prefix = f"{label}：" if idx == 0 else ""
        content = line[len(prefix) :] if idx == 0 and line.startswith(prefix) else line
        offset_x = 44 if idx == 0 else 0
        draw.text((60 + offset_x, text_y), content, fill=(247, 244, 238), font=text_font)
        text_y += 30


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
    anchor_x = WIDTH * 0.5 + actor.x_offset
    for name, (x, y) in base.items():
        stage_x = WIDTH * 0.5 + (x - WIDTH * 0.5) * actor.scale + actor.x_offset
        if actor.mirror:
            stage_x = anchor_x - (stage_x - anchor_x)
        stage_y = GROUND_Y + (y - GROUND_Y) * actor.scale
        stage[name] = (stage_x, stage_y)
    return stage


def _draw_actor(
    image: Image.Image,
    actor: ActorSpec,
    active: ScheduledLine | None,
    t_s: float,
    head_size: int,
) -> None:
    speaking = active is not None and active.speaker_id == actor.actor_id
    track_name = active.track_name if speaking and active.track_name else actor.track_name
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
        draw.line((*stage_points[start], *stage_points[end]), fill=poseviz._edge_color(start, palette), width=poseviz.LIMB_WIDTH, joint="curve")
    for name, (x, y) in stage_points.items():
        if name in {"nose", "left_hip", "right_hip"} or name not in LEG_POINTS:
            continue
        radius = poseviz.JOINT_RADIUS
        color = poseviz._joint_color(name, palette)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
    poseviz._draw_torso(draw, stage_points, palette)
    poseviz._draw_torso_texture(image, stage_points, textures)
    draw = ImageDraw.Draw(image, "RGBA")
    for start, end in poseviz.POSE_EDGES:
        if start not in ARM_POINTS or start not in stage_points or end not in stage_points:
            continue
        draw.line((*stage_points[start], *stage_points[end]), fill=poseviz._edge_color(start, palette), width=poseviz.LIMB_WIDTH, joint="curve")
    for name, (x, y) in stage_points.items():
        if name in {"nose", "left_hip", "right_hip"} or name not in ARM_POINTS:
            continue
        radius = poseviz.JOINT_RADIUS
        color = poseviz._joint_color(name, palette)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
    mouth_open = speaking and (int(t_s * FPS) % TALK_MOUTH_CYCLE_FRAMES) < (TALK_MOUTH_CYCLE_FRAMES // 2)
    expression = active.expression if speaking else actor.expression
    face_texture = poseviz._load_face_texture(actor.character_id, expression=expression, talking=speaking, mouth_open=mouth_open)
    poseviz._draw_panda_head(image, draw, stage_points, size=int(head_size * actor.scale), textures=textures, face_texture=face_texture)
    head_center = poseviz._head_center(stage_points)
    if head_center is not None:
        label_font = _font(20, bold=True)
        bubble_color = (255, 230, 172, 220) if speaking else (18, 22, 32, 188)
        text_color = (78, 42, 20) if speaking else (240, 240, 240)
        text_w = label_font.getbbox(actor.label)[2] - label_font.getbbox(actor.label)[0]
        cx, cy = head_center
        box = (cx - text_w * 0.55 - 18, cy - head_size * actor.scale * 1.18, cx + text_w * 0.55 + 18, cy - head_size * actor.scale * 0.86)
        draw.rounded_rectangle(box, radius=12, fill=bubble_color)
        draw.text((box[0] + 16, box[1] + 6), actor.label, fill=text_color, font=label_font)


def _render_scene_frame(scene: SceneSpec, schedule: list[ScheduledLine], duration_s: float, t_s: float, head_size: int) -> Image.Image:
    image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
    _gradient_background(image, scene.background_top, scene.background_bottom)
    draw = ImageDraw.Draw(image, "RGBA")
    progress = 0.0 if duration_s <= 1e-6 else max(0.0, min(1.0, t_s / duration_s))
    _draw_effect(draw, scene, progress)
    active = _active_line(schedule, t_s)
    for actor in scene.actors:
        if not actor.visible:
            continue
        _draw_actor(image, actor, active, t_s, head_size)
    draw = ImageDraw.Draw(image, "RGBA")
    _draw_caption(draw, scene, progress)
    if active is not None:
        _draw_subtitle(draw, active.speaker_label, active.text)
    return image.convert("RGB")


def _render_scene_video(scene: SceneSpec, schedule: list[ScheduledLine], duration_s: float, head_size: int, output_path: Path) -> None:
    proc = poseviz._open_ffmpeg_stream(FPS, WIDTH, HEIGHT, output_path)
    try:
        assert proc.stdin is not None
        total_frames = max(1, int(round(duration_s * FPS)))
        for frame_index in range(total_frames):
            t_s = frame_index / FPS
            frame = _render_scene_frame(scene, schedule, duration_s, t_s, head_size)
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


def render_story(output_path: Path, *, force: bool = False) -> None:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    head_size = _all_head_size()
    scene_outputs: list[Path] = []
    for scene in SCENES:
        paths = _scene_paths(scene)
        if not force and paths["scene_mp4"].exists() and paths["scene_mp4"].stat().st_size > 0:
            scene_outputs.append(paths["scene_mp4"])
            print(paths["scene_mp4"])
            continue
        schedule, duration_s = _build_schedule(scene, paths["dir"])
        _mix_scene_audio(scene, schedule, duration_s, paths["audio"])
        _render_scene_video(scene, schedule, duration_s, head_size, paths["video"])
        _mux_scene(paths["video"], paths["audio"], paths["scene_mp4"])
        scene_outputs.append(paths["scene_mp4"])
        print(paths["scene_mp4"])
    _concat_scenes(scene_outputs, output_path)
    print(output_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a multi-character Water Margin dialogue story using DNN pose stickman actors with Chinese subtitles, TTS, BGM, SFX, and action blocking.")
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    render_story(args.output.resolve(), force=args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
