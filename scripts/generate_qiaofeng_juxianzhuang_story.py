#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


CAST = [
    {"id": "qiao_feng", "display_name": "乔峰", "asset_id": "general-guard"},
    {"id": "azi", "display_name": "阿紫", "asset_id": "npc-girl"},
    {"id": "you_ji", "display_name": "游骥", "asset_id": "official-minister"},
    {"id": "you_ju", "display_name": "游驹", "asset_id": "detective-sleek"},
    {"id": "xuan_nan", "display_name": "玄难", "asset_id": "master-monk"},
    {"id": "murong_fu", "display_name": "慕容复", "asset_id": "strategist"},
    {"id": "crowd_elder", "display_name": "群雄老者", "asset_id": "farmer-old"},
    {"id": "crowd_guard", "display_name": "庄客", "asset_id": "npc-boy"},
]

FLOOR_BY_BACKGROUND = {
    "street-day": "stone-court",
    "town-hall-records": "wood-plank",
    "hotel-lobby": "wood-plank",
    "room-day": "wood-plank",
    "museum-gallery": "wood-plank",
    "school-yard": "stone-court",
    "park-evening": "dark-stage",
    "archive-library": "wood-plank",
    "restaurant-booth": "wood-plank",
    "cafe-night": "dark-stage",
    "theatre-stage": "dark-stage",
    "bank-lobby": "wood-plank",
    "shop-row": "stone-court",
}

DIALOGUE_WINDOWS = [
    (300, 1500),
    (1850, 3050),
    (5150, 6350),
    (6700, 7900),
    (9950, 11150),
    (11450, 12650),
]

ACTION_WINDOWS = [
    (3320, 4720),
    (8140, 9540),
    (12950, 14400),
]

SCENE_OUTLINES = [
    {
        "id": "scene-001",
        "background": "street-day",
        "summary": "乔峰抱着阿紫来到聚贤庄外，群雄先声夺人。",
        "actors": ["qiao_feng", "azi", "you_ji", "crowd_guard"],
        "props": ["house", "wall-door", "horse"],
        "lines": [
            ("crowd_guard", "来人止步，前面就是聚贤庄。"),
            ("azi", "我姐夫伤重，借路片刻也不行么。"),
            ("you_ji", "乔峰，你还敢踏进中原地界。"),
            ("qiao_feng", "我来求医，不来惹事。"),
            ("crowd_guard", "你一句不惹事，谁敢信。"),
            ("qiao_feng", "谁若逼我，我只得应战。"),
        ],
    },
    {
        "id": "scene-002",
        "background": "town-hall-records",
        "summary": "游氏兄弟并肩出面，当众质问乔峰。",
        "actors": ["qiao_feng", "you_ji", "you_ju", "azi"],
        "props": ["wall-window", "lantern", "house"],
        "lines": [
            ("you_ju", "乔峰，你在雁门关外的血债如何算。"),
            ("qiao_feng", "血债真假未明，先别急着盖棺。"),
            ("you_ji", "聚贤庄今日广发英雄帖，只等你来。"),
            ("azi", "人倒不少，胆子却全躲在帖子后面。"),
            ("you_ju", "小妖女，你也配插嘴。"),
            ("qiao_feng", "骂她一句，我便记你一掌。"),
        ],
    },
    {
        "id": "scene-003",
        "background": "hotel-lobby",
        "summary": "玄难现身劝解，先问乔峰可愿束手。",
        "actors": ["qiao_feng", "azi", "xuan_nan", "you_ji"],
        "props": ["wall-door", "wall-window", "house"],
        "lines": [
            ("xuan_nan", "乔帮主，回头尚未太晚。"),
            ("qiao_feng", "大师若肯听我，我愿把话说清。"),
            ("you_ji", "与其听他辩，不如先废他双臂。"),
            ("azi", "你们一口一句公道，倒像在抢先定罪。"),
            ("xuan_nan", "贫僧只问一句，你可愿放下兵锋。"),
            ("qiao_feng", "人若逼到眼前，我放不下。"),
        ],
    },
    {
        "id": "scene-004",
        "background": "room-day",
        "summary": "庄中大厅剑拔弩张，乔峰自辩来意。",
        "actors": ["qiao_feng", "you_ji", "you_ju", "xuan_nan"],
        "props": ["lantern", "wall-window", "house"],
        "lines": [
            ("qiao_feng", "我只求一席清静，让阿紫缓口气。"),
            ("you_ji", "你踏进这里，便没有清静二字。"),
            ("you_ju", "中原群豪在此，不容契丹恶名横走。"),
            ("xuan_nan", "若能免战，贫僧仍愿周旋。"),
            ("qiao_feng", "我不怕战，只怕是非再被人写死。"),
            ("you_ji", "那便让拳脚来断是非。"),
        ],
    },
    {
        "id": "scene-005",
        "background": "museum-gallery",
        "summary": "阿紫言辞尖刻，群雄怒火更盛。",
        "actors": ["azi", "qiao_feng", "crowd_elder", "you_ju"],
        "props": ["lantern", "star", "moon"],
        "lines": [
            ("azi", "你们围一人，还好意思自称英雄。"),
            ("crowd_elder", "对付乔峰，讲不得江湖单挑。"),
            ("qiao_feng", "阿紫，少说两句，站在我身后。"),
            ("you_ju", "你护得住她，未必护得住自己。"),
            ("azi", "你们若真有种，就一个个上。"),
            ("qiao_feng", "今日谁先动手，我先记谁。"),
        ],
    },
    {
        "id": "scene-006",
        "background": "school-yard",
        "summary": "前排庄客扑上，乔峰以降龙十八掌开局震退。",
        "actors": ["qiao_feng", "you_ji", "crowd_guard", "azi"],
        "props": ["house", "horse", "wall-door"],
        "lines": [
            ("crowd_guard", "众人并肩上，别让他腾出手。"),
            ("qiao_feng", "既然要上，就接我降龙十八掌。"),
            ("azi", "好，让他们知道什么叫真本事。"),
            ("you_ji", "稳住阵脚，不许后退。"),
            ("qiao_feng", "这一掌先让前排退三步。"),
            ("crowd_guard", "掌风怎么这样沉重。"),
        ],
    },
    {
        "id": "scene-007",
        "background": "park-evening",
        "summary": "游氏兄弟命众人结阵，从两翼逼近。",
        "actors": ["qiao_feng", "you_ji", "you_ju", "crowd_guard"],
        "props": ["wall-window", "house", "horse"],
        "lines": [
            ("you_ji", "左翼压过去，别给他回身。"),
            ("you_ju", "右翼封门，耗也耗死他。"),
            ("qiao_feng", "靠人海来压，我早见惯了。"),
            ("crowd_guard", "别怕，他再猛也只一人。"),
            ("qiao_feng", "你们再近一步，我再出掌。"),
            ("you_ji", "乔峰，今天偏要逼你出掌。"),
        ],
    },
    {
        "id": "scene-008",
        "background": "archive-library",
        "summary": "玄难再劝，乔峰不愿束手仍留余地。",
        "actors": ["qiao_feng", "xuan_nan", "azi", "crowd_elder"],
        "props": ["lantern", "wall-window", "moon"],
        "lines": [
            ("xuan_nan", "乔帮主，收住怒意，还来得及。"),
            ("qiao_feng", "大师肯信我，我也愿信大师。"),
            ("crowd_elder", "大师莫再劝，他不会回头。"),
            ("azi", "你们只会逼他，哪给过路。"),
            ("xuan_nan", "贫僧只求少流些血。"),
            ("qiao_feng", "若他们停手，我自然停手。"),
        ],
    },
    {
        "id": "scene-009",
        "background": "restaurant-booth",
        "summary": "乔峰抱起阿紫往侧廊冲，群雄一路追堵。",
        "actors": ["qiao_feng", "azi", "you_ju", "crowd_guard"],
        "props": ["wall-door", "house", "wall-window"],
        "lines": [
            ("azi", "姐夫，他们从右边包过来了。"),
            ("qiao_feng", "抱紧我，我先闯回廊。"),
            ("you_ju", "拦住他，别让他转进内厅。"),
            ("crowd_guard", "门口太窄，他跑不远。"),
            ("qiao_feng", "窄路正好，一次只来几个。"),
            ("azi", "那就让他们一个个倒下。"),
        ],
    },
    {
        "id": "scene-010",
        "background": "cafe-night",
        "summary": "慕容复现身观战，先用言语试探乔峰。",
        "actors": ["qiao_feng", "murong_fu", "azi", "you_ji"],
        "props": ["moon", "star", "lantern"],
        "lines": [
            ("murong_fu", "乔兄，一别多日，风采依旧。"),
            ("qiao_feng", "慕容公子既在，为何只看不劝。"),
            ("you_ji", "慕容公子自会站在公道这边。"),
            ("azi", "公道若靠旁观，那也太便宜了。"),
            ("murong_fu", "我只想看乔兄今日如何脱身。"),
            ("qiao_feng", "想看，就看清谁先失了体面。"),
        ],
    },
    {
        "id": "scene-011",
        "background": "theatre-stage",
        "summary": "乔峰与慕容复隔空较劲，群雄反成陪衬。",
        "actors": ["qiao_feng", "murong_fu", "you_ju", "azi"],
        "props": ["lantern", "star", "moon"],
        "lines": [
            ("murong_fu", "乔兄若再进一步，我也只好出手。"),
            ("qiao_feng", "你若要战，就别借他人声势。"),
            ("you_ju", "慕容公子，一起拿下他。"),
            ("murong_fu", "急什么，我这一道剑气先试掌路。"),
            ("qiao_feng", "剑气来得再快，也压不住我。"),
            ("azi", "你们总算肯自己露面了。"),
        ],
    },
    {
        "id": "scene-012",
        "background": "bank-lobby",
        "summary": "大厅再度合围，乔峰被逼回到中央空地。",
        "actors": ["qiao_feng", "you_ji", "you_ju", "crowd_guard"],
        "props": ["wall-door", "wall-window", "house"],
        "lines": [
            ("you_ji", "门窗全封住，看他往哪退。"),
            ("you_ju", "庄中上下都压过去。"),
            ("qiao_feng", "退路被堵，那我就只走正面。"),
            ("crowd_guard", "别散开，把他困在中间。"),
            ("qiao_feng", "人多不等于阵稳。"),
            ("you_ji", "阵稳不稳，你马上就知道。"),
        ],
    },
    {
        "id": "scene-013",
        "background": "room-day",
        "summary": "阿紫心神慌乱，乔峰一边护她一边稳局。",
        "actors": ["qiao_feng", "azi", "xuan_nan", "crowd_elder"],
        "props": ["lantern", "wall-window", "moon"],
        "lines": [
            ("azi", "姐夫，我眼前发黑，他们还在逼。"),
            ("qiao_feng", "别怕，靠着我，谁也近不了。"),
            ("crowd_elder", "他还在护人，这正是破绽。"),
            ("xuan_nan", "莫趁人之危，诸位留一线。"),
            ("azi", "他们若留一线，就不是他们了。"),
            ("qiao_feng", "所以我只能替你挡全场。"),
        ],
    },
    {
        "id": "scene-014",
        "background": "hotel-lobby",
        "summary": "桌椅翻飞，乔峰二次爆发，以降龙十八掌扫开近身者。",
        "actors": ["qiao_feng", "you_ji", "crowd_guard", "azi"],
        "props": ["lantern", "house", "wall-door"],
        "lines": [
            ("crowd_guard", "趁他护人，齐上。"),
            ("qiao_feng", "谁敢近她半步，再吃我降龙十八掌。"),
            ("you_ji", "挡住，别被一掌冲散。"),
            ("azi", "姐夫，让他们看看什么叫退潮。"),
            ("qiao_feng", "这一掌不伤命，只教你们让路。"),
            ("crowd_guard", "桌案都被掌风掀起来了。"),
        ],
    },
    {
        "id": "scene-015",
        "background": "shop-row",
        "summary": "乔峰正面喝退游氏兄弟，言语比掌风更重。",
        "actors": ["qiao_feng", "you_ji", "you_ju", "azi"],
        "props": ["house", "wall-window", "horse"],
        "lines": [
            ("qiao_feng", "游氏兄弟，你们若真讲义气，就自己上前。"),
            ("you_ji", "我们站在这里，便是自己在前。"),
            ("you_ju", "聚贤庄今日不能让你走脱。"),
            ("azi", "不能让他走，却没人真敢贴身。"),
            ("qiao_feng", "你们借英雄名，却做围猎事。"),
            ("you_ji", "只要能除你，名声我担得起。"),
        ],
    },
    {
        "id": "scene-016",
        "background": "park-evening",
        "summary": "夜色渐沉，群雄气势衰下去，乔峰却越战越稳。",
        "actors": ["qiao_feng", "crowd_elder", "crowd_guard", "azi"],
        "props": ["moon", "star", "house"],
        "lines": [
            ("crowd_elder", "怎么越围越乱，他反倒越稳。"),
            ("crowd_guard", "前排都不敢再贴近了。"),
            ("azi", "方才那么凶，现在怎么都缩了。"),
            ("qiao_feng", "我本不想逼人，可你们偏要试。"),
            ("crowd_elder", "再拖下去，庄中人心要散。"),
            ("qiao_feng", "心若不齐，阵自然先散。"),
        ],
    },
    {
        "id": "scene-017",
        "background": "museum-gallery",
        "summary": "玄难最后一次劝止，乔峰只求带阿紫离开。",
        "actors": ["qiao_feng", "xuan_nan", "azi", "you_ju"],
        "props": ["lantern", "wall-window", "moon"],
        "lines": [
            ("xuan_nan", "乔帮主，带人离去，莫再恋战。"),
            ("qiao_feng", "我从未恋战，我只求一条路。"),
            ("you_ju", "让你离去，聚贤庄颜面何存。"),
            ("azi", "颜面比命还大，你们也真可笑。"),
            ("xuan_nan", "贫僧愿替你挡一句，你快走。"),
            ("qiao_feng", "大师这份心，我记住了。"),
        ],
    },
    {
        "id": "scene-018",
        "background": "street-day",
        "summary": "乔峰背起阿紫强闯外院，最后一波围堵被撕开。",
        "actors": ["qiao_feng", "azi", "you_ji", "crowd_guard"],
        "props": ["horse", "house", "wall-door"],
        "lines": [
            ("azi", "姐夫，门外似乎还有一层人。"),
            ("qiao_feng", "那就再闯一层，我背你出去。"),
            ("you_ji", "外院收口，别让他越门。"),
            ("crowd_guard", "全都压上，把门堵死。"),
            ("qiao_feng", "再接一记降龙十八掌，门自然开。"),
            ("azi", "这一掌之后，谁还敢拦。"),
        ],
    },
    {
        "id": "scene-019",
        "background": "school-yard",
        "summary": "群雄追到院外却不敢贴近，阿紫回头冷笑。",
        "actors": ["qiao_feng", "azi", "crowd_elder", "murong_fu"],
        "props": ["house", "horse", "moon"],
        "lines": [
            ("crowd_elder", "别追太近，他回身就是一掌。"),
            ("azi", "方才不是喊着替天行道么。"),
            ("murong_fu", "乔兄今日确实打出了名声。"),
            ("qiao_feng", "名声也好，骂名也罢，我都背惯了。"),
            ("azi", "他们只会远远看着你走。"),
            ("crowd_elder", "谁也没想到会是这个局面。"),
        ],
    },
    {
        "id": "scene-020",
        "background": "cafe-night",
        "summary": "乔峰带阿紫离开聚贤庄，身后群雄只剩沉默。",
        "actors": ["qiao_feng", "azi", "murong_fu", "xuan_nan"],
        "props": ["moon", "star", "horse"],
        "lines": [
            ("azi", "姐夫，我们总算出了庄。"),
            ("qiao_feng", "出了庄，不等于出了江湖。"),
            ("murong_fu", "乔兄，此去山高路远，珍重。"),
            ("xuan_nan", "愿你心中仍存一念慈悲。"),
            ("qiao_feng", "我若无慈悲，聚贤庄早不是今日模样。"),
            ("azi", "走吧，让他们在身后慢慢议论。"),
        ],
    },
]

HERO_ACTIONS = [
    ("point", "enter", "point"),
    ("point", "dragon-palm", "point"),
    ("point", "somersault", "dragon-palm"),
    ("enter", "dragon-palm", "point"),
    ("point", "big-jump", "point"),
    ("dragon-palm", "big-jump", "dragon-palm"),
    ("enter", "dragon-palm", "sword-arc"),
    ("point", "handstand-walk", "dragon-palm"),
    ("enter", "big-jump", "dragon-palm"),
    ("point", "dragon-palm", "point"),
    ("sword-arc", "dragon-palm", "point"),
    ("enter", "dragon-palm", "big-jump"),
    ("point", "thunder-strike", "dragon-palm"),
    ("dragon-palm", "big-jump", "dragon-palm"),
    ("point", "sword-arc", "point"),
    ("enter", "dragon-palm", "thunder-strike"),
    ("point", "big-jump", "enter"),
    ("dragon-palm", "big-jump", "dragon-palm"),
    ("point", "dragon-palm", "exit"),
    ("enter", "point", "enter"),
]

RIVAL_ACTIONS = [
    ("point", "enter", "point"),
    ("point", "thunder-strike", "point"),
    ("point", "thunder-strike", "point"),
    ("point", "sword-arc", "point"),
    ("point", "enter", "point"),
    ("enter", "thunder-strike", "exit"),
    ("enter", "sword-arc", "thunder-strike"),
    ("point", "thunder-strike", "point"),
    ("enter", "point", "enter"),
    ("point", "sword-arc", "point"),
    ("point", "sword-arc", "thunder-strike"),
    ("enter", "thunder-strike", "point"),
    ("point", "point", "enter"),
    ("enter", "thunder-strike", "exit"),
    ("point", "sword-arc", "point"),
    ("enter", "point", "exit"),
    ("point", "point", "enter"),
    ("enter", "thunder-strike", "point"),
    ("point", "point", "exit"),
    ("point", "enter", "point"),
]


def _dialogue(start_ms: int, end_ms: int, speaker_id: str, text: str) -> dict:
    return {
        "start_ms": start_ms,
        "end_ms": end_ms,
        "speaker_id": speaker_id,
        "text": text,
        "subtitle": text,
        "voice": None,
        "bubble": False,
    }


def _expression(actor_id: str, start_ms: int, end_ms: int, expression: str) -> dict:
    return {"actor_id": actor_id, "start_ms": start_ms, "end_ms": end_ms, "expression": expression}


def _actor(actor_id: str, x: float, z: float, facing: str, scale: float, layer: str = "front") -> dict:
    return {
        "actor_id": actor_id,
        "spawn": {"x": x, "z": z},
        "scale": scale,
        "layer": layer,
        "facing": facing,
    }


def _beat(start_ms: int, end_ms: int, actor_id: str, motion: str, *, x0: float | None = None, x1: float | None = None, z0: float = 0.0, z1: float = 0.0, facing: str | None = None, effect: str | None = None, emotion: str = "charged") -> dict:
    beat = {
        "start_ms": start_ms,
        "end_ms": end_ms,
        "actor_id": actor_id,
        "motion": motion,
        "from": None if x0 is None else {"x": x0, "z": z0},
        "to": None if x1 is None else {"x": x1, "z": z1},
        "facing": facing,
        "emotion": emotion,
    }
    if effect:
        beat["effect"] = effect
    return beat


def _expression_for_text(text: str) -> str:
    if any(token in text for token in ("掌", "战", "杀", "逼", "拦", "退")):
        return "fierce"
    if any(token in text for token in ("笑", "体面", "议论")):
        return "smirk"
    if any(token in text for token in ("莫", "愿", "慈悲", "听我")):
        return "deadpan"
    if any(token in text for token in ("怕", "伤", "缓口气", "发黑")):
        return "hurt"
    return "talk"


def _motion_expression(motion: str) -> str:
    if motion in {"dragon-palm", "thunder-strike", "sword-arc"}:
        return "fierce"
    if motion in {"somersault", "big-jump", "handstand-walk"}:
        return "smirk"
    if motion in {"enter", "exit"}:
        return "deadpan"
    return "talk"


def _main_rival(actor_ids: list[str]) -> str | None:
    for actor_id in actor_ids:
        if actor_id not in {"qiao_feng", "azi"}:
            return actor_id
    return None


def _scene_actors(actor_ids: list[str], scene_index: int) -> list[dict]:
    support_positions = [(-0.6, -0.18), (4.0, -0.14), (-4.2, -0.10)]
    actors: list[dict] = []
    rival_id = _main_rival(actor_ids)
    for actor_id in actor_ids:
        if actor_id == "qiao_feng":
            actors.append(_actor(actor_id, -2.7 + 0.12 * (scene_index % 2), 0.02, "right", 1.08))
        elif actor_id == rival_id:
            actors.append(_actor(actor_id, 2.5 - 0.15 * (scene_index % 3), 0.0, "left", 1.0))
        elif actor_id == "azi":
            actors.append(_actor(actor_id, -4.0, -0.14, "right", 0.90, layer="mid"))
        else:
            x, z = support_positions[len(actors) % len(support_positions)]
            actors.append(_actor(actor_id, x, z, "left" if x > 0 else "right", 0.92, layer="mid"))
    return actors


def _scene_props(prop_ids: list[str], scene_index: int) -> list[dict]:
    xs = [-4.1, 0.0, 4.0]
    zs = [-1.08, -0.86, -1.00]
    layers = ["back", "mid", "front"]
    props: list[dict] = []
    for idx, prop_id in enumerate(prop_ids[:3]):
        props.append(
            {
                "prop_id": prop_id,
                "x": xs[idx],
                "z": zs[idx],
                "scale": 0.88 + 0.06 * ((scene_index + idx) % 2),
                "layer": layers[idx],
            }
        )
    return props


def _npc_groups(scene_index: int, actor_ids: list[str]) -> list[dict]:
    if "crowd_guard" not in actor_ids and "crowd_elder" not in actor_ids:
        return []
    return [
        {
            "id": f"crowd-{scene_index+1:02d}",
            "count": 6 + (scene_index % 3),
            "asset_ids": ["npc-boy", "farmer-old"],
            "behavior": "guard" if scene_index % 2 == 0 else "wander",
            "layer": "back",
            "watch": True,
            "anchor": {"x": 0.0, "frontness": -0.10},
            "area": {"x_min": -4.8, "x_max": 4.8, "front_min": -0.30, "front_max": 0.08},
            "scale_min": 0.58,
            "scale_max": 0.82,
        }
    ]


def _dialogues_and_talk_beats(lines: list[tuple[str, str]]) -> tuple[list[dict], list[dict], list[dict]]:
    dialogues: list[dict] = []
    beats: list[dict] = []
    expressions: list[dict] = []
    for (start_ms, end_ms), (speaker_id, text) in zip(DIALOGUE_WINDOWS, lines):
        dialogues.append(_dialogue(start_ms, end_ms, speaker_id, text))
        beats.append(_beat(start_ms, end_ms, speaker_id, "talk", facing=None, emotion="focused"))
        expressions.append(_expression(speaker_id, start_ms, end_ms, _expression_for_text(text)))
    return dialogues, beats, expressions


def _action_beats(scene_index: int, actor_ids: list[str]) -> tuple[list[dict], list[dict], list[str]]:
    beats: list[dict] = []
    expressions: list[dict] = []
    effect_ids: set[str] = set()
    rival_id = _main_rival(actor_ids)
    hero_actions = HERO_ACTIONS[scene_index]
    rival_actions = RIVAL_ACTIONS[scene_index]
    hero_xs = [(-2.8, -1.1), (-1.4, 0.6), (-0.2, 1.3)]
    rival_xs = [(2.5, 1.0), (1.5, -0.1), (0.7, 2.2)]

    for idx, (start_ms, end_ms) in enumerate(ACTION_WINDOWS):
        hero_motion = hero_actions[idx]
        hero_from_x, hero_to_x = hero_xs[idx]
        hero_effect = hero_motion if hero_motion in {"dragon-palm", "thunder-strike", "sword-arc"} else None
        beats.append(
            _beat(
                start_ms,
                end_ms,
                "qiao_feng",
                hero_motion,
                x0=hero_from_x,
                x1=hero_to_x,
                facing="right",
                effect=hero_effect,
            )
        )
        expressions.append(_expression("qiao_feng", start_ms, end_ms, _motion_expression(hero_motion)))
        if hero_effect:
            effect_ids.add(hero_effect)

        if rival_id:
            rival_motion = rival_actions[idx]
            rival_from_x, rival_to_x = rival_xs[idx]
            rival_effect = rival_motion if rival_motion in {"dragon-palm", "thunder-strike", "sword-arc"} else None
            beats.append(
                _beat(
                    start_ms + 180,
                    end_ms + 180,
                    rival_id,
                    rival_motion,
                    x0=rival_from_x,
                    x1=rival_to_x,
                    facing="left",
                    effect=rival_effect,
                )
            )
            expressions.append(_expression(rival_id, start_ms + 180, end_ms + 180, _motion_expression(rival_motion)))
            if rival_effect:
                effect_ids.add(rival_effect)
    return beats, expressions, sorted(effect_ids)


def _camera(scene_index: int) -> dict:
    return {
        "type": "pan",
        "x": -0.28 + 0.06 * (scene_index % 3),
        "z": 0.03,
        "zoom": 1.00 + 0.03 * (scene_index % 2),
        "to_x": 0.22 - 0.05 * (scene_index % 2),
        "to_z": 0.01,
        "to_zoom": 1.08,
        "ease": "ease-in-out",
    }


def build_story() -> dict:
    scenes: list[dict] = []
    used_backgrounds: set[str] = set()
    used_floors: set[str] = set()
    used_props: set[str] = set()
    used_effects: set[str] = set()
    used_motions: set[str] = set()

    for scene_index, outline in enumerate(SCENE_OUTLINES):
        if len(outline["lines"]) < 6:
            raise ValueError(f"{outline['id']} must contain at least 6 dialogue turns")

        background = outline["background"]
        floor = FLOOR_BY_BACKGROUND[background]
        actors = _scene_actors(outline["actors"], scene_index)
        dialogues, talk_beats, talk_expressions = _dialogues_and_talk_beats(outline["lines"])
        action_beats, action_expressions, effect_ids = _action_beats(scene_index, outline["actors"])
        beats = sorted([*talk_beats, *action_beats], key=lambda item: (item["start_ms"], item["actor_id"]))
        expressions = sorted([*talk_expressions, *action_expressions], key=lambda item: (item["start_ms"], item["actor_id"]))
        duration_ms = 15050

        for beat in beats:
            used_motions.add(str(beat["motion"]))
            if beat.get("effect"):
                used_effects.add(str(beat["effect"]))

        used_backgrounds.add(background)
        used_floors.add(floor)
        used_props.update(outline["props"])
        used_effects.update(effect_ids)

        scenes.append(
            {
                "id": outline["id"],
                "background": background,
                "floor": floor,
                "duration_ms": duration_ms,
                "summary": outline["summary"],
                "camera": _camera(scene_index),
                "effects": [{"type": effect_id} for effect_id in effect_ids],
                "props": _scene_props(outline["props"], scene_index),
                "actors": actors,
                "npc_groups": _npc_groups(scene_index, outline["actors"]),
                "beats": beats,
                "expressions": expressions,
                "dialogues": dialogues,
                "audio": {"bgm": None, "sfx": []},
            }
        )

    if len(scenes) < 20:
        raise ValueError("story must contain at least 20 scenes")

    return {
        "meta": {
            "title": "乔峰大战聚贤庄",
            "language": "zh-CN",
            "theme": "武侠、群雄围攻、聚贤庄夜战",
            "source_prompt": None,
        },
        "video": {
            "width": 960,
            "height": 540,
            "fps": 12,
            "renderer": "pygame_2d",
            "video_codec": "mpeg4",
            "mpeg4_qscale": 5,
            "encoder_preset": "ultrafast",
            "crf": 26,
            "subtitle_mode": "bottom",
            "tts_enabled": False,
        },
        "cast": CAST,
        "assets": {
            "backgrounds": sorted(used_backgrounds),
            "floors": sorted(used_floors),
            "props": sorted(used_props),
            "motions": sorted(used_motions),
            "effects": sorted(used_effects),
        },
        "scenes": scenes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a canonical 20-scene story for 乔峰大战聚贤庄.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    story = build_story()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(story, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    print(f"scene_count={len(story['scenes'])}")
    print(f"min_dialogue_turns={min(len(scene['dialogues']) for scene in story['scenes'])}")
    print(f"motion_count={len(story['assets']['motions'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
