from __future__ import annotations

import argparse
import json
from pathlib import Path


BACKGROUNDS = [
    "mountain-cliff",
    "temple-courtyard",
    "training-ground",
    "night-bridge",
    "inn-hall",
    "theatre-stage",
]

FLOORS = {
    "mountain-cliff": "stone-court",
    "temple-courtyard": "stone-court",
    "training-ground": "stone-court",
    "night-bridge": "dark-stage",
    "inn-hall": "wood-plank",
    "theatre-stage": "dark-stage",
}

SECTS = [
    {
        "id": "shaolin",
        "display_name": "少林方丈",
        "asset_id": "master-monk",
        "npc_asset_ids": ["master-monk", "npc-boy"],
        "props": ["training-drum", "lantern"],
        "signature": "thunder-strike",
        "retort": "少林以静制动，不凭嘴硬。",
        "opening": "少林众僧在此，张无忌，你还敢硬闯山门？",
        "taunt": "若想过关，先接我这一记金刚雷音。",
    },
    {
        "id": "wudang",
        "display_name": "武当长老",
        "asset_id": "strategist",
        "npc_asset_ids": ["strategist", "npc-boy"],
        "props": ["weapon-rack", "lantern"],
        "signature": "sword-arc",
        "retort": "武当借力打力，岂会被你一味猛攻吓住。",
        "opening": "武当剑圈已成，你若再进一步，就是自取其辱。",
        "taunt": "来，看你能否破开这道太极剑环。",
    },
    {
        "id": "emei",
        "display_name": "峨眉掌门",
        "asset_id": "swordswoman",
        "npc_asset_ids": ["swordswoman", "npc-girl"],
        "props": ["lantern", "weapon-rack"],
        "signature": "sword-arc",
        "retort": "峨眉剑势最重分寸，你这一路只是逞强。",
        "opening": "张无忌，你在光明顶太张狂，今天该收一收锋芒了。",
        "taunt": "先别得意，峨眉这一剑专断横气。",
    },
    {
        "id": "huashan",
        "display_name": "华山掌门",
        "asset_id": "general-guard",
        "npc_asset_ids": ["general-guard", "npc-boy"],
        "props": ["weapon-rack", "training-drum"],
        "signature": "dragon-palm",
        "retort": "华山讲究一线争先，绝不让你抢住上风。",
        "opening": "华山弟子列阵在前，今天便要当众试试你的九阳余劲。",
        "taunt": "你若挡不住，我这一掌就把你送回山脚。",
    },
    {
        "id": "kunlun",
        "display_name": "昆仑长老",
        "asset_id": "official-minister",
        "npc_asset_ids": ["official-minister", "npc-boy"],
        "props": ["weapon-rack", "lantern"],
        "signature": "dragon-palm",
        "retort": "昆仑山势高绝，你这口气倒比山风还急。",
        "opening": "昆仑一脉久候多时，今日要你把狂言一句一句吞回去。",
        "taunt": "有本事就接我昆仑裂云掌。",
    },
    {
        "id": "kongtong",
        "display_name": "崆峒宿老",
        "asset_id": "farmer-old",
        "npc_asset_ids": ["farmer-old", "npc-boy"],
        "props": ["training-drum", "weapon-rack"],
        "signature": "thunder-strike",
        "retort": "崆峒七伤，招招见骨，你可别只会喊疼。",
        "opening": "崆峒门人已封住退路，张无忌，你今天只能一路打出去。",
        "taunt": "我这七伤劲一到，你身上的护体真气也得碎开。",
    },
]

SCENE_PATTERNS = [
    "challenge",
    "rush",
    "counter",
    "air",
    "close",
    "finale",
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
    return {
        "actor_id": actor_id,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "expression": expression,
    }


def _actor(actor_id: str, x: float, facing: str, scale: float = 1.0) -> dict:
    return {
        "actor_id": actor_id,
        "spawn": {"x": x, "z": 0.0},
        "scale": scale,
        "layer": "front",
        "facing": facing,
    }


def _scene_props(prop_ids: list[str], background: str, scene_index: int) -> list[dict]:
    props: list[dict] = []
    for slot, prop_id in enumerate(prop_ids[:2]):
        base_x = -3.8 if slot == 0 else 3.7
        if background == "night-bridge":
            prop_id = "lantern"
        props.append(
            {
                "prop_id": prop_id,
                "x": base_x,
                "z": -1.05 if prop_id == "lantern" else (-1.2 if prop_id == "training-drum" else -0.95),
                "scale": 0.92 + 0.04 * ((scene_index + slot) % 2),
                "layer": "back" if slot == 0 else "front",
            }
        )
    return props


def _npc_group(scene_index: int, sect: dict) -> list[dict]:
    count = 5 + (scene_index % 3)
    return [
        {
            "id": f"{sect['id']}-crowd-{scene_index:02d}",
            "count": count,
            "asset_ids": sect["npc_asset_ids"],
            "behavior": "guard" if scene_index % 2 == 0 else "wander",
            "layer": "back",
            "watch": True,
            "anchor": {"x": 0.0, "frontness": -0.14},
            "area": {"x_min": -4.6, "x_max": 4.6, "front_min": -0.35, "front_max": 0.06},
            "scale_min": 0.62,
            "scale_max": 0.82,
        }
    ]


def _challenge_scene(scene_id: str, scene_index: int, background: str, sect: dict) -> dict:
    duration_ms = 15600
    start_b = 3000
    return {
        "id": scene_id,
        "background": background,
        "floor": FLOORS[background],
        "duration_ms": duration_ms,
        "summary": f"{sect['display_name']}当众叫阵，张无忌以短句回敬。",
        "camera": {"type": "pan", "x": -0.35, "z": 0.10, "zoom": 1.00, "to_x": 0.28, "to_z": 0.02, "to_zoom": 1.05, "ease": "inout"},
        "effects": [],
        "props": _scene_props(sect["props"], background, scene_index),
        "actors": [_actor("zhang", -2.2, "right"), _actor(sect["id"], 2.2, "left", 0.98)],
        "npc_groups": _npc_group(scene_index, sect),
        "beats": [
            {"start_ms": 320, "end_ms": 2500, "actor_id": sect["id"], "motion": "point", "from": None, "to": None, "facing": "left", "emotion": "charged"},
            {"start_ms": start_b, "end_ms": 5200, "actor_id": "zhang", "motion": "talk", "from": None, "to": None, "facing": "right", "emotion": "calm"},
            {"start_ms": 7200, "end_ms": 11200, "actor_id": sect["id"], "motion": "point", "from": None, "to": None, "facing": "left", "emotion": "charged"},
            {"start_ms": 11600, "end_ms": 14600, "actor_id": "zhang", "motion": "point", "from": None, "to": None, "facing": "right", "emotion": "charged"},
        ],
        "expressions": [
            _expression(sect["id"], 320, 2500, "fierce"),
            _expression("zhang", start_b, 5200, "deadpan"),
            _expression(sect["id"], 7200, 11200, "fierce"),
            _expression("zhang", 11600, 14600, "smirk"),
        ],
        "dialogues": [
            _dialogue(320, 2500, sect["id"], sect["opening"]),
            _dialogue(start_b, 5200, "zhang", "诸位既然齐来，张无忌就一场一场奉陪到底。"),
            _dialogue(7200, 11200, sect["id"], sect["taunt"]),
            _dialogue(11600, 14600, "zhang", "出手吧，我也正想看看六派到底能逼我退几步。"),
        ],
        "audio": {"bgm": None, "sfx": []},
    }


def _rush_scene(scene_id: str, scene_index: int, background: str, sect: dict) -> dict:
    duration_ms = 16800
    sig = sect["signature"]
    return {
        "id": scene_id,
        "background": background,
        "floor": FLOORS[background],
        "duration_ms": duration_ms,
        "summary": f"{sect['display_name']}抢攻，张无忌翻身突进反压半场。",
        "camera": {"type": "pan", "x": -0.20, "z": 0.05, "zoom": 1.03, "to_x": 0.16, "to_z": 0.03, "to_zoom": 1.10, "ease": "inout"},
        "effects": [],
        "props": _scene_props(sect["props"], background, scene_index),
        "actors": [_actor("zhang", -2.9, "right"), _actor(sect["id"], 2.4, "left", 0.98)],
        "npc_groups": _npc_group(scene_index, sect),
        "beats": [
            {"start_ms": 400, "end_ms": 5600, "actor_id": "zhang", "motion": "somersault", "from": {"x": -3.2, "z": 0.0}, "to": {"x": -0.4, "z": 0.0}, "facing": "right", "emotion": "charged"},
            {"start_ms": 2100, "end_ms": 7600, "actor_id": sect["id"], "motion": sig, "from": {"x": 2.3, "z": 0.0}, "to": {"x": 0.9, "z": 0.0}, "facing": "left", "emotion": "charged", "effect": sig},
            {"start_ms": 8900, "end_ms": 13400, "actor_id": "zhang", "motion": "big-jump", "from": {"x": -0.2, "z": 0.0}, "to": {"x": 1.2, "z": 0.0}, "facing": "right", "emotion": "charged"},
            {"start_ms": 11600, "end_ms": 16000, "actor_id": sect["id"], "motion": "exit", "from": {"x": 1.1, "z": 0.0}, "to": {"x": 2.9, "z": 0.0}, "facing": "right", "emotion": "awkward"},
        ],
        "expressions": [
            _expression("zhang", 400, 5600, "fierce"),
            _expression(sect["id"], 2100, 7600, "fierce"),
            _expression("zhang", 8900, 13400, "fierce"),
            _expression(sect["id"], 11600, 16000, "hurt"),
        ],
        "dialogues": [
            _dialogue(6200, 8200, sect["id"], "站住，别想一口气冲穿阵势。"),
            _dialogue(13800, 15950, "zhang", "阵不是靠人数堆出来的，破绽一露，就只能后退。"),
        ],
        "audio": {"bgm": None, "sfx": []},
    }


def _counter_scene(scene_id: str, scene_index: int, background: str, sect: dict) -> dict:
    duration_ms = 17000
    sig = "thunder-strike" if sect["signature"] != "thunder-strike" else "sword-arc"
    return {
        "id": scene_id,
        "background": background,
        "floor": FLOORS[background],
        "duration_ms": duration_ms,
        "summary": f"{sect['display_name']}借势反压，双方近中距离连续换招。",
        "camera": {"type": "static", "zoom": 1.08, "x": 0.0, "z": 0.06},
        "effects": [],
        "props": _scene_props(list(reversed(sect["props"])), background, scene_index),
        "actors": [_actor("zhang", -1.9, "right"), _actor(sect["id"], 1.8, "left", 0.98)],
        "npc_groups": _npc_group(scene_index, sect),
        "beats": [
            {"start_ms": 500, "end_ms": 4600, "actor_id": sect["id"], "motion": "handstand-walk", "from": {"x": 2.0, "z": 0.0}, "to": {"x": 0.8, "z": 0.0}, "facing": "left", "emotion": "charged"},
            {"start_ms": 1800, "end_ms": 6900, "actor_id": "zhang", "motion": sig, "from": {"x": -1.8, "z": 0.0}, "to": {"x": -0.2, "z": 0.0}, "facing": "right", "emotion": "charged", "effect": sig},
            {"start_ms": 8000, "end_ms": 12400, "actor_id": sect["id"], "motion": "sword-arc", "from": {"x": 0.8, "z": 0.0}, "to": {"x": -0.2, "z": 0.0}, "facing": "left", "emotion": "charged", "effect": "sword-arc"},
            {"start_ms": 11100, "end_ms": 16000, "actor_id": "zhang", "motion": "dragon-palm", "from": {"x": -0.4, "z": 0.0}, "to": {"x": 0.9, "z": 0.0}, "facing": "right", "emotion": "charged", "effect": "dragon-palm"},
        ],
        "expressions": [
            _expression(sect["id"], 500, 4600, "fierce"),
            _expression("zhang", 1800, 6900, "fierce"),
            _expression(sect["id"], 8000, 12400, "fierce"),
            _expression("zhang", 11100, 16000, "smirk"),
        ],
        "dialogues": [
            _dialogue(7000, 9300, sect["id"], sect["retort"]),
            _dialogue(13350, 16000, "zhang", "你们每一派都有绝招，可我今天偏要一招一招都接下来。"),
        ],
        "audio": {"bgm": None, "sfx": []},
    }


def _air_scene(scene_id: str, scene_index: int, background: str, sect: dict) -> dict:
    duration_ms = 16600
    return {
        "id": scene_id,
        "background": background,
        "floor": FLOORS[background],
        "duration_ms": duration_ms,
        "summary": f"{sect['display_name']}与张无忌双双腾空，打到半空再落地分开。",
        "camera": {"type": "pan", "x": -0.12, "z": 0.12, "zoom": 1.02, "to_x": 0.14, "to_z": 0.08, "to_zoom": 1.12, "ease": "inout"},
        "effects": [],
        "props": _scene_props(sect["props"], background, scene_index),
        "actors": [_actor("zhang", -2.1, "right"), _actor(sect["id"], 2.1, "left", 0.98)],
        "npc_groups": _npc_group(scene_index, sect),
        "beats": [
            {"start_ms": 600, "end_ms": 5200, "actor_id": "zhang", "motion": "big-jump", "from": {"x": -2.0, "z": 0.0}, "to": {"x": -0.4, "z": 0.0}, "facing": "right", "emotion": "charged"},
            {"start_ms": 1400, "end_ms": 6600, "actor_id": sect["id"], "motion": "big-jump", "from": {"x": 2.0, "z": 0.0}, "to": {"x": 0.6, "z": 0.0}, "facing": "left", "emotion": "charged"},
            {"start_ms": 8600, "end_ms": 12600, "actor_id": "zhang", "motion": "dunk", "from": {"x": -0.2, "z": 0.0}, "to": {"x": 1.0, "z": 0.0}, "facing": "right", "emotion": "charged"},
            {"start_ms": 11200, "end_ms": 15600, "actor_id": sect["id"], "motion": "exit", "from": {"x": 0.9, "z": 0.0}, "to": {"x": 2.7, "z": 0.0}, "facing": "left", "emotion": "hurt"},
        ],
        "expressions": [
            _expression("zhang", 600, 5200, "fierce"),
            _expression(sect["id"], 1400, 6600, "fierce"),
            _expression("zhang", 8600, 12600, "fierce"),
            _expression(sect["id"], 11200, 15600, "awkward"),
        ],
        "dialogues": [
            _dialogue(6900, 9500, sect["id"], "别逼我再提真气，你脚下那点地利我也能踩碎。"),
            _dialogue(12800, 15600, "zhang", "高处低处都一样，只要你心乱，落地那一刻就已经输了。"),
        ],
        "audio": {"bgm": None, "sfx": []},
    }


def _close_scene(scene_id: str, scene_index: int, background: str, sect: dict) -> dict:
    duration_ms = 17200
    return {
        "id": scene_id,
        "background": background,
        "floor": FLOORS[background],
        "duration_ms": duration_ms,
        "summary": f"{sect['display_name']}近身缠斗，张无忌连破对手三段攻势。",
        "camera": {"type": "static", "zoom": 1.12, "x": 0.0, "z": 0.06},
        "effects": [],
        "props": _scene_props(list(reversed(sect["props"])), background, scene_index),
        "actors": [_actor("zhang", -1.6, "right"), _actor(sect["id"], 1.5, "left", 0.98)],
        "npc_groups": _npc_group(scene_index, sect),
        "beats": [
            {"start_ms": 500, "end_ms": 4400, "actor_id": sect["id"], "motion": "point", "from": None, "to": None, "facing": "left", "emotion": "charged"},
            {"start_ms": 1500, "end_ms": 6600, "actor_id": "zhang", "motion": "handstand-walk", "from": {"x": -1.6, "z": 0.0}, "to": {"x": 0.2, "z": 0.0}, "facing": "right", "emotion": "calm"},
            {"start_ms": 7600, "end_ms": 11600, "actor_id": sect["id"], "motion": "dragon-palm", "from": {"x": 1.2, "z": 0.0}, "to": {"x": 0.2, "z": 0.0}, "facing": "left", "emotion": "charged", "effect": "dragon-palm"},
            {"start_ms": 10800, "end_ms": 16000, "actor_id": "zhang", "motion": "thunder-strike", "from": {"x": 0.0, "z": 0.0}, "to": {"x": 1.2, "z": 0.0}, "facing": "right", "emotion": "charged", "effect": "thunder-strike"},
        ],
        "expressions": [
            _expression(sect["id"], 500, 4400, "fierce"),
            _expression("zhang", 1500, 6600, "deadpan"),
            _expression(sect["id"], 7600, 11600, "fierce"),
            _expression("zhang", 10800, 16000, "fierce"),
        ],
        "dialogues": [
            _dialogue(4500, 6800, sect["id"], "你若真有本事，就别只在我身前绕。"),
            _dialogue(12100, 16000, "zhang", "绕你一圈，是让你看清楚，我什么时候都能从正面把招接回来。"),
        ],
        "audio": {"bgm": None, "sfx": []},
    }


def _finale_scene(scene_id: str, scene_index: int, background: str, sect: dict, is_last: bool) -> dict:
    duration_ms = 17600
    zhang_close = "六派连番上阵，到这一步还想拿气势压人，未免太慢了。"
    sect_close = "今日这一阵，就算你闯过去，六派也不会轻易认输。"
    if is_last:
        sect_close = "张无忌，今天六派虽退，你与江湖的账却还没有算完。"
        zhang_close = "我不求你们服气，只求你们今夜记住，真正的强弱，从来不靠围攻决定。"
    return {
        "id": scene_id,
        "background": background,
        "floor": FLOORS[background],
        "duration_ms": duration_ms,
        "summary": f"{sect['display_name']}这一轮收尾，张无忌强行压住全场气势。",
        "camera": {"type": "pan", "x": -0.18, "z": 0.04, "zoom": 1.05, "to_x": 0.18, "to_z": 0.00, "to_zoom": 1.16, "ease": "inout"},
        "effects": [],
        "props": _scene_props(sect["props"], background, scene_index),
        "actors": [_actor("zhang", -2.0, "right"), _actor(sect["id"], 1.9, "left", 0.98)],
        "npc_groups": _npc_group(scene_index, sect),
        "beats": [
            {"start_ms": 600, "end_ms": 5800, "actor_id": sect["id"], "motion": sect["signature"], "from": {"x": 1.9, "z": 0.0}, "to": {"x": 0.4, "z": 0.0}, "facing": "left", "emotion": "charged", "effect": sect["signature"]},
            {"start_ms": 2200, "end_ms": 8400, "actor_id": "zhang", "motion": "somersault", "from": {"x": -2.1, "z": 0.0}, "to": {"x": 0.5, "z": 0.0}, "facing": "right", "emotion": "charged"},
            {"start_ms": 9500, "end_ms": 12400, "actor_id": sect["id"], "motion": "talk", "from": None, "to": None, "facing": "left", "emotion": "hurt"},
            {"start_ms": 12800, "end_ms": 17000, "actor_id": "zhang", "motion": "talk", "from": None, "to": None, "facing": "right", "emotion": "deadpan"},
        ],
        "expressions": [
            _expression(sect["id"], 600, 5800, "fierce"),
            _expression("zhang", 2200, 8400, "fierce"),
            _expression(sect["id"], 9500, 12400, "hurt"),
            _expression("zhang", 12800, 17000, "deadpan"),
        ],
        "dialogues": [
            _dialogue(9500, 12400, sect["id"], sect_close),
            _dialogue(12800, 17000, "zhang", zhang_close),
        ],
        "audio": {"bgm": None, "sfx": []},
    }


def build_story() -> dict:
    cast = [
        {"id": "zhang", "display_name": "张无忌", "asset_id": "young-hero"},
        *[
            {
                "id": sect["id"],
                "display_name": sect["display_name"],
                "asset_id": sect["asset_id"],
            }
            for sect in SECTS
        ],
    ]

    scenes = []
    scene_number = 1
    for sect_index, sect in enumerate(SECTS):
        for phase_index, phase in enumerate(SCENE_PATTERNS):
            background = BACKGROUNDS[(sect_index * len(SCENE_PATTERNS) + phase_index) % len(BACKGROUNDS)]
            scene_id = f"scene-{scene_number:03d}"
            if phase == "challenge":
                scene = _challenge_scene(scene_id, scene_number, background, sect)
            elif phase == "rush":
                scene = _rush_scene(scene_id, scene_number, background, sect)
            elif phase == "counter":
                scene = _counter_scene(scene_id, scene_number, background, sect)
            elif phase == "air":
                scene = _air_scene(scene_id, scene_number, background, sect)
            elif phase == "close":
                scene = _close_scene(scene_id, scene_number, background, sect)
            else:
                scene = _finale_scene(scene_id, scene_number, background, sect, is_last=sect_index == len(SECTS) - 1)
            scenes.append(scene)
            scene_number += 1

    total_ms = sum(int(scene["duration_ms"]) for scene in scenes)
    title = "张无忌大战六大门派"
    theme = "武侠群战、轮番对打、长篇对话、围观门人"
    return {
        "meta": {
            "title": title,
            "language": "zh-CN",
            "theme": theme,
            "source_prompt": None,
        },
        "video": {
            "width": 960,
            "height": 540,
            "fps": 12,
            "subtitle_mode": "bottom",
            "tts_enabled": True,
            "encoder_preset": "medium",
            "crf": 23,
            "actor_front_bias": 1.0,
            "frame_center_z": 0.76,
            "stage_layout": {
                "background_width": 14.0,
                "background_height": 7.0,
                "background_y": 8.2,
                "background_z": 1.08,
                "ground_width": 19.5,
                "ground_height": 14.2,
                "ground_y": 6.8,
                "ground_z": -0.85,
                "ground_pitch": -77.5,
                "ground_slope": 0.24,
            },
        },
        "cast": cast,
        "assets": {
            "backgrounds": sorted(set(BACKGROUNDS)),
            "floors": sorted(set(FLOORS.values())),
            "props": ["lantern", "training-drum", "weapon-rack"],
            "motions": ["big-jump", "dragon-palm", "dunk", "exit", "handstand-walk", "point", "somersault", "sword-arc", "talk", "thunder-strike"],
            "effects": ["dragon-palm", "sword-arc", "thunder-strike"],
        },
        "scenes": scenes,
        "notes": {
            "scene_count": len(scenes),
            "estimated_duration_ms": total_ms,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a long wuxia story: Zhang Wuji versus six sects.")
    parser.add_argument("--output", default="work/zhang_wuji_six_sects_story.json")
    args = parser.parse_args()
    story = build_story()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output_path)
    print(f"scene_count={len(story['scenes'])}")
    print(f"duration_ms={story['notes']['estimated_duration_ms']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
