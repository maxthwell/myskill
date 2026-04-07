#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


CAST = [
    {"id": "qiao_feng", "display_name": "乔峰", "asset_id": "general-guard"},
    {"id": "azhu", "display_name": "阿朱", "asset_id": "npc-girl"},
    {"id": "xuan_nan", "display_name": "玄难", "asset_id": "master-monk"},
    {"id": "xuan_ci", "display_name": "玄慈", "asset_id": "master-monk"},
    {"id": "xuan_ji", "display_name": "玄寂", "asset_id": "master-monk"},
    {"id": "murong_fu", "display_name": "慕容复", "asset_id": "strategist"},
    {"id": "crowd_elder", "display_name": "群雄老者", "asset_id": "farmer-old"},
    {"id": "monk_guard", "display_name": "知客僧", "asset_id": "npc-boy"},
]

FLOOR_BY_BACKGROUND = {
    "mountain-cliff": "stone-court",
    "temple-courtyard": "stone-court",
    "training-ground": "stone-court",
    "inn-hall": "wood-plank",
    "archive-library": "wood-plank",
    "room-day": "wood-plank",
    "hotel-lobby": "wood-plank",
    "museum-gallery": "wood-plank",
    "night-bridge": "dark-stage",
    "park-evening": "dark-stage",
    "street-day": "stone-court",
    "town-hall-records": "wood-plank",
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
        "background": "mountain-cliff",
        "summary": "夜上少室山，乔峰背着阿朱来到山门前求见方丈。",
        "actors": ["qiao_feng", "azhu", "monk_guard", "crowd_elder"],
        "opponent": "monk_guard",
        "props": ["house", "moon", "wall-door"],
        "lines": [
            ("monk_guard", "来者止步，少林山门夜里不接外客。"),
            ("azhu", "小女子伤得厉害，求大师先容我们进门歇一歇。"),
            ("crowd_elder", "乔峰，你身背命案，还敢闯到少林来。"),
            ("qiao_feng", "我来求见玄慈方丈，问几桩旧事，也替她求一线生机。"),
            ("monk_guard", "方丈岂是你说见就见。"),
            ("qiao_feng", "你只管进去通报，若他不见，我自会下山。"),
        ],
    },
    {
        "id": "scene-002",
        "background": "temple-courtyard",
        "summary": "玄难赶到山门前，先问乔峰为何执意夜闯少林。",
        "actors": ["qiao_feng", "azhu", "xuan_nan", "monk_guard"],
        "opponent": "xuan_nan",
        "props": ["training-drum", "wall-window", "lantern"],
        "lines": [
            ("xuan_nan", "乔帮主，你夜到少林，是为求医，还是为问罪。"),
            ("qiao_feng", "两样都有，我要见玄慈，也要替阿朱讨一味药。"),
            ("azhu", "我若死在山门前，只怕这场误会就再也说不清了。"),
            ("monk_guard", "大师，此人来势太硬，不可轻信。"),
            ("xuan_nan", "乔帮主若真无恶意，先把掌力收住。"),
            ("qiao_feng", "只要少林不先拔刀，我这双手今晚就不先伤人。"),
        ],
    },
    {
        "id": "scene-003",
        "background": "training-ground",
        "summary": "玄寂率戒律僧赶来，认定乔峰是为玄苦之死而来寻衅。",
        "actors": ["qiao_feng", "xuan_nan", "xuan_ji", "azhu"],
        "opponent": "xuan_ji",
        "props": ["weapon-rack", "training-drum", "lantern"],
        "lines": [
            ("xuan_ji", "玄苦师兄死于非命，乔峰，你今日自己送上门来，正好拿你问话。"),
            ("qiao_feng", "我来正是为了问清玄苦大师之死。"),
            ("xuan_nan", "师弟，先听他说完，莫把山门先变成刑场。"),
            ("azhu", "诸位若真想问话，也该先给人一个说话的机会。"),
            ("xuan_ji", "少林不是你放肆之地。"),
            ("qiao_feng", "若你们只想定罪，不如明说，不必借问话做门面。"),
        ],
    },
    {
        "id": "scene-004",
        "background": "inn-hall",
        "summary": "乔峰被带进外院偏殿，却仍被挡在玄慈之外。",
        "actors": ["qiao_feng", "azhu", "xuan_nan", "crowd_elder"],
        "opponent": "crowd_elder",
        "props": ["wall-window", "lantern", "wall-door"],
        "lines": [
            ("qiao_feng", "我只求当面问方丈一句，当年雁门关外，到底是谁领头。"),
            ("crowd_elder", "你一个契丹人，也配在少林提雁门关。"),
            ("azhu", "诸位这样层层阻拦，倒更像怕旧事被翻出来。"),
            ("xuan_nan", "阿弥陀佛，少说一句，局面未必不能缓。"),
            ("qiao_feng", "大师，我今夜肯收着掌，只因还念少林是清净地。"),
            ("crowd_elder", "清净地也容不得你来逼宫。"),
        ],
    },
    {
        "id": "scene-005",
        "background": "archive-library",
        "summary": "阿朱出言求情，却仍让偏殿里的气氛彻底绷紧。",
        "actors": ["azhu", "qiao_feng", "xuan_ji", "monk_guard"],
        "opponent": "xuan_ji",
        "props": ["wall-door", "wall-window", "lantern"],
        "lines": [
            ("azhu", "少林若真以慈悲为本，总不该把伤者一直晾在门边。"),
            ("xuan_ji", "妖女，你再出言不逊，贫僧先封你哑穴。"),
            ("qiao_feng", "你敢碰她一下，我今晚便不再讲客气。"),
            ("monk_guard", "大师，他护得这样紧，分明心里有鬼。"),
            ("azhu", "若诸位都不肯开口，今晚这场误会只会越闹越大。"),
            ("qiao_feng", "阿朱，站到我身后，余下的话让我来说。"),
        ],
    },
    {
        "id": "scene-006",
        "background": "temple-courtyard",
        "summary": "戒律僧先行动手，乔峰被迫以掌风震退前排。",
        "actors": ["qiao_feng", "azhu", "monk_guard", "xuan_ji"],
        "opponent": "xuan_ji",
        "props": ["training-drum", "weapon-rack", "lantern"],
        "lines": [
            ("monk_guard", "众僧听令，先拿下他再请方丈发落。"),
            ("qiao_feng", "我已让到山门里，你们还要逼掌，那就怪不得我。"),
            ("azhu", "乔大哥，他们既不肯让路，你也只能先护住自己。"),
            ("xuan_ji", "少林伏魔阵一开，看你还能横到几时。"),
            ("qiao_feng", "我这一掌先让你们退开三丈。"),
            ("monk_guard", "掌风一到，连地上的沙石都被掀起来了。"),
        ],
    },
    {
        "id": "scene-007",
        "background": "training-ground",
        "summary": "罗汉阵层层压上，乔峰边护阿朱边破阵前行。",
        "actors": ["qiao_feng", "azhu", "xuan_ji", "monk_guard"],
        "opponent": "xuan_ji",
        "props": ["weapon-rack", "training-drum", "lantern"],
        "lines": [
            ("xuan_ji", "第一排守中路，第二排封两翼，别让他靠近大殿。"),
            ("qiao_feng", "阵法若只靠人多，破起来也不过多费两步。"),
            ("azhu", "左边阵脚先乱了，你若往那边发力，也许能少伤几个人。"),
            ("monk_guard", "稳住脚下，不许被他喝退。"),
            ("qiao_feng", "我不想伤少林弟子，你们自己退开。"),
            ("xuan_ji", "少林今日宁折不退。"),
        ],
    },
    {
        "id": "scene-008",
        "background": "room-day",
        "summary": "玄难再次挡在正中，希望乔峰就此住手。",
        "actors": ["qiao_feng", "xuan_nan", "azhu", "crowd_elder"],
        "opponent": "xuan_nan",
        "props": ["wall-door", "wall-window", "lantern"],
        "lines": [
            ("xuan_nan", "乔帮主，再往前一步，就是少林大殿。"),
            ("qiao_feng", "我只要见玄慈，当面问一句旧案。"),
            ("crowd_elder", "少林若给你开了这个口，天下英雄怎么看。"),
            ("azhu", "外面的人只会讲道理，真正被逼到墙角的是我们。"),
            ("xuan_nan", "贫僧信你尚存分寸，你也该信少林还讲法度。"),
            ("qiao_feng", "若真讲法度，就不该用这么多人拦一个来问话的人。"),
        ],
    },
    {
        "id": "scene-009",
        "background": "street-day",
        "summary": "慕容复带着群豪赶到寺外，顺势把局面推得更僵。",
        "actors": ["qiao_feng", "murong_fu", "azhu", "crowd_elder"],
        "opponent": "murong_fu",
        "props": ["house", "horse", "wall-door"],
        "lines": [
            ("murong_fu", "乔兄，少林今晚钟声未歇，看来你又把场面闹大了。"),
            ("qiao_feng", "慕容复，你来得倒巧，是想劝和，还是想添柴。"),
            ("azhu", "慕容公子若肯劝和，今晚也许真能少流些血。"),
            ("crowd_elder", "慕容公子来得正好，大家一起拿住乔峰。"),
            ("murong_fu", "我只怕诸位一拥而上，反倒显不出中原人物的体面。"),
            ("qiao_feng", "你若真要体面，就别只站在后面说漂亮话。"),
        ],
    },
    {
        "id": "scene-010",
        "background": "hotel-lobby",
        "summary": "外院与偏殿连成一片混战，乔峰被迫正面撕开包围。",
        "actors": ["qiao_feng", "azhu", "murong_fu", "monk_guard"],
        "opponent": "murong_fu",
        "props": ["wall-window", "weapon-rack", "lantern"],
        "lines": [
            ("monk_guard", "前后一起压上，别让他再退回廊下。"),
            ("murong_fu", "乔兄，你若再往里闯，我也只好陪少林挡你一程。"),
            ("qiao_feng", "你想借少林的手成名，那就先接我一掌。"),
            ("azhu", "乔大哥，右边回廊更窄，你在那里更容易护住我。"),
            ("murong_fu", "好，我便看看降龙十八掌今晚还能剩几分威势。"),
            ("qiao_feng", "够把挡路的人一层一层打散。"),
        ],
    },
    {
        "id": "scene-011",
        "background": "archive-library",
        "summary": "乔峰护着阿朱退到藏经阁外长廊，局面短暂喘息。",
        "actors": ["qiao_feng", "azhu", "xuan_nan", "monk_guard"],
        "opponent": "xuan_nan",
        "props": ["wall-door", "lantern", "wall-window"],
        "lines": [
            ("azhu", "我胸口像压着石头，再拖下去恐怕真撑不住。"),
            ("qiao_feng", "你先靠柱子坐稳，我替你把这一条廊守住。"),
            ("xuan_nan", "乔帮主，你护她的心是真的，何必非要把少林逼到这一步。"),
            ("monk_guard", "大师，再迟疑，他就要闯进藏经阁了。"),
            ("qiao_feng", "我若真想闯阁，刚才那一路就不会处处收劲。"),
            ("azhu", "他们看不见你留手，只会觉得自己颜面受损。"),
        ],
    },
    {
        "id": "scene-012",
        "background": "museum-gallery",
        "summary": "玄慈终于现身，在众僧与群豪之前与乔峰第一次对话。",
        "actors": ["qiao_feng", "xuan_ci", "xuan_nan", "azhu"],
        "opponent": "xuan_ci",
        "props": ["wall-window", "weapon-rack", "lantern"],
        "lines": [
            ("xuan_ci", "乔峰，你一路闯到此处，究竟想从老衲口中问出什么。"),
            ("qiao_feng", "我要问雁门关外那场血案，也要问玄苦大师临终前见过谁。"),
            ("xuan_nan", "方丈既已现身，诸位都先收兵。"),
            ("azhu", "若早肯见他，也不至于先动这么多人的手。"),
            ("xuan_ci", "你今夜带掌入寺，少林不能当作什么都没发生。"),
            ("qiao_feng", "我若不一路打到这里，方丈未必肯出来。"),
        ],
    },
    {
        "id": "scene-013",
        "background": "town-hall-records",
        "summary": "乔峰当众追问带头大哥，玄慈神色迟疑，群豪议论四起。",
        "actors": ["qiao_feng", "xuan_ci", "crowd_elder", "azhu"],
        "opponent": "xuan_ci",
        "props": ["wall-window", "wall-door", "lantern"],
        "lines": [
            ("qiao_feng", "当年是谁一纸传讯，召来中原好手围杀雁门关外一家。"),
            ("xuan_ci", "往事牵连甚众，不是一句话就能当众说尽。"),
            ("crowd_elder", "方丈何必同他纠缠，先把人拿下再问。"),
            ("azhu", "诸位如此着急，倒更像怕方丈真的把名字说出来。"),
            ("qiao_feng", "方丈，你沉默一息，我心里的疑云就重一层。"),
            ("xuan_ci", "老衲不会逃避，只是此处不是分辨旧案的好地方。"),
        ],
    },
    {
        "id": "scene-014",
        "background": "night-bridge",
        "summary": "慕容复趁众人分神从侧面偷袭，乔峰回身硬接。",
        "actors": ["qiao_feng", "murong_fu", "azhu", "xuan_nan"],
        "opponent": "murong_fu",
        "props": ["lantern", "moon", "weapon-rack"],
        "lines": [
            ("murong_fu", "乔兄，你既逼得方丈难堪，我便替中原武林先讨你这一笔。"),
            ("qiao_feng", "你果然忍不住了，想出手就别借别人名头。"),
            ("azhu", "慕容公子总爱挑别人分神的时候出手。"),
            ("xuan_nan", "慕容公子，此处不是火上浇油的时候。"),
            ("murong_fu", "我这一招若压住他，今夜局面自然就平了。"),
            ("qiao_feng", "那你就来，看你的斗转星移能不能卸掉我的掌力。"),
        ],
    },
    {
        "id": "scene-015",
        "background": "training-ground",
        "summary": "钟鼓齐鸣，玄寂再开阵势，要在达摩院前困死乔峰。",
        "actors": ["qiao_feng", "xuan_ji", "xuan_ci", "monk_guard"],
        "opponent": "xuan_ji",
        "props": ["training-drum", "weapon-rack", "lantern"],
        "lines": [
            ("xuan_ji", "钟鼓已鸣，少林弟子各守其位，今日绝不能让他越过达摩院。"),
            ("qiao_feng", "你们一层又一层拦我，到底是护寺，还是护一个不敢说出的名字。"),
            ("xuan_ci", "师弟，莫伤无辜，先守住门户。"),
            ("monk_guard", "众僧听令，收口，别让他从中路突破。"),
            ("qiao_feng", "门若不开，我便自己打出一条路。"),
            ("xuan_ji", "那就看你还能不能把这一院石板都踏碎。"),
        ],
    },
    {
        "id": "scene-016",
        "background": "temple-courtyard",
        "summary": "乔峰以降龙十八掌连破木杖和棍阵，直逼大殿台阶。",
        "actors": ["qiao_feng", "azhu", "xuan_ji", "monk_guard"],
        "opponent": "xuan_ji",
        "props": ["training-drum", "weapon-rack", "lantern"],
        "lines": [
            ("azhu", "他们的棍阵已经乱了，再往前半步就是台阶。"),
            ("qiao_feng", "我这一掌开中路，你抓紧跟在我身后。"),
            ("xuan_ji", "木杖齐出，封他膝下，别让他借力腾身。"),
            ("monk_guard", "棍头刚碰上掌风就全偏了。"),
            ("qiao_feng", "少林棍法原该堂堂正正，不该用来围一个抱着伤者的人。"),
            ("xuan_ji", "今夜你不倒下，少林就没有退路。"),
        ],
    },
    {
        "id": "scene-017",
        "background": "room-day",
        "summary": "玄难亲自拦在石阶上，与乔峰作最后一次正面交锋。",
        "actors": ["qiao_feng", "xuan_nan", "azhu", "xuan_ci"],
        "opponent": "xuan_nan",
        "props": ["wall-door", "wall-window", "lantern"],
        "lines": [
            ("xuan_nan", "再往上就是佛殿正门，乔帮主，贫僧只能亲自拦你。"),
            ("qiao_feng", "大师若非被局势所逼，本不该站在我对面。"),
            ("azhu", "玄难大师心里明白，却还是得替少林守住门面。"),
            ("xuan_ci", "玄难师弟，小心他的掌路。"),
            ("xuan_nan", "若你还能信贫僧一句，就别把这一阶也打成血路。"),
            ("qiao_feng", "我信大师，但我更要一个答案。"),
        ],
    },
    {
        "id": "scene-018",
        "background": "hotel-lobby",
        "summary": "阿朱吐露她偷听到的线索，乔峰意识到带头大哥就在眼前。",
        "actors": ["azhu", "qiao_feng", "xuan_ci", "murong_fu"],
        "opponent": "murong_fu",
        "props": ["wall-door", "wall-window", "lantern"],
        "lines": [
            ("azhu", "乔大哥，我在偏殿听见他们提过，带头大哥就在少林高僧之中。"),
            ("qiao_feng", "方丈，你若再不说，今夜这场血战就真要算在你头上。"),
            ("xuan_ci", "有些罪，老衲可以认；有些人，老衲一时还不能当众连累。"),
            ("murong_fu", "乔兄，你苦寻多年，原来真相一直在你眼前。"),
            ("azhu", "慕容公子此刻说得轻巧，方才偷袭时怎么不见你讲真相。"),
            ("qiao_feng", "方丈，我只问你一句，当年那道讯令，是不是你发的。"),
        ],
    },
    {
        "id": "scene-019",
        "background": "park-evening",
        "summary": "玄慈终于松口承认当年误判，却求乔峰先离少林再说。",
        "actors": ["qiao_feng", "xuan_ci", "xuan_nan", "azhu"],
        "opponent": "xuan_ci",
        "props": ["moon", "lantern", "weapon-rack"],
        "lines": [
            ("xuan_ci", "当年少林确有误判，老衲也难辞其咎。"),
            ("qiao_feng", "这一句我等了多年，却偏偏是在满寺刀棍之后才听见。"),
            ("xuan_nan", "方丈既已开口，今夜便到此为止吧。"),
            ("azhu", "方丈只说了一半，乔大哥这些年的苦岂不是白受了。"),
            ("xuan_ci", "老衲欠你的，终会还你一个交代，但今夜少林不能再死人。"),
            ("qiao_feng", "好，我带她离寺，可这笔旧账不会就这样算了。"),
        ],
    },
    {
        "id": "scene-020",
        "background": "mountain-cliff",
        "summary": "乔峰背着阿朱离开少林，回望山门，决意继续追查真相。",
        "actors": ["qiao_feng", "azhu", "xuan_nan", "murong_fu"],
        "opponent": "murong_fu",
        "props": ["moon", "horse", "house"],
        "lines": [
            ("azhu", "这一夜打进打出，总算逼得他们松了口。"),
            ("qiao_feng", "松口还不够，我要的是一桩桩都见天日。"),
            ("xuan_nan", "乔帮主，少林今日欠你的，贫僧记在心里。"),
            ("murong_fu", "乔兄，此去若再查下去，只怕会把整个江湖都掀翻。"),
            ("qiao_feng", "若真相本就埋在江湖底下，那我就把这一潭水全部翻开。"),
            ("azhu", "那就走吧，等下次回来，我们要把该问的话全都问清。"),
        ],
    },
]

ACTION_PROFILES = {
    "gate_probe": {
        "hero": [
            ("enter", (-2.75, -2.15)),
            ("point", (-2.15, -1.95)),
            ("enter", (-1.95, -2.35)),
        ],
        "rival": [
            ("point", (2.35, 2.15)),
            ("enter", (2.15, 1.80)),
            ("point", (1.80, 2.10)),
        ],
    },
    "hard_standoff": {
        "hero": [
            ("point", (-2.55, -2.05)),
            ("enter", (-2.05, -1.55)),
            ("point", (-1.55, -1.95)),
        ],
        "rival": [
            ("point", (2.35, 2.10)),
            ("point", (2.10, 1.75)),
            ("enter", (1.75, 2.00)),
        ],
    },
    "hall_pressure": {
        "hero": [
            ("point", (-2.45, -2.00)),
            ("enter", (-2.00, -1.65)),
            ("point", (-1.65, -1.95)),
        ],
        "rival": [
            ("point", (2.20, 2.05)),
            ("point", (2.05, 1.90)),
            ("point", (1.90, 2.10)),
        ],
    },
    "first_strike": {
        "hero": [
            ("enter", (-2.55, -1.55)),
            ("dragon-palm", (-1.55, -0.15)),
            ("point", (-0.15, -0.65)),
        ],
        "rival": [
            ("enter", (2.30, 1.50)),
            ("thunder-strike", (1.50, 0.75)),
            ("enter", (0.75, 1.35)),
        ],
    },
    "formation_push": {
        "hero": [
            ("enter", (-2.65, -1.70)),
            ("dragon-palm", (-1.70, -0.30)),
            ("enter", (-0.30, 0.60)),
        ],
        "rival": [
            ("enter", (2.35, 1.60)),
            ("thunder-strike", (1.60, 0.95)),
            ("point", (0.95, 1.35)),
        ],
    },
    "leader_confrontation": {
        "hero": [
            ("point", (-2.40, -1.85)),
            ("enter", (-1.85, -1.20)),
            ("point", (-1.20, -1.60)),
        ],
        "rival": [
            ("point", (2.10, 1.95)),
            ("enter", (1.95, 1.50)),
            ("point", (1.50, 1.85)),
        ],
    },
    "mixed_brawl": {
        "hero": [
            ("enter", (-2.50, -1.30)),
            ("dragon-palm", (-1.30, 0.05)),
            ("sword-arc", (0.05, 0.70)),
        ],
        "rival": [
            ("enter", (2.35, 1.45)),
            ("sword-arc", (1.45, 0.55)),
            ("thunder-strike", (0.55, 1.10)),
        ],
    },
    "corridor_breath": {
        "hero": [
            ("enter", (-2.60, -2.10)),
            ("point", (-2.10, -1.85)),
            ("enter", (-1.85, -2.20)),
        ],
        "rival": [
            ("point", (2.20, 2.00)),
            ("enter", (2.00, 1.75)),
            ("point", (1.75, 1.95)),
        ],
    },
    "truth_pressure": {
        "hero": [
            ("point", (-2.30, -1.90)),
            ("point", (-1.90, -1.45)),
            ("enter", (-1.45, -1.75)),
        ],
        "rival": [
            ("point", (2.00, 1.85)),
            ("enter", (1.85, 1.55)),
            ("point", (1.55, 1.80)),
        ],
    },
    "sneak_attack": {
        "hero": [
            ("point", (-2.35, -1.90)),
            ("sword-arc", (-1.90, -0.60)),
            ("dragon-palm", (-0.60, 0.10)),
        ],
        "rival": [
            ("enter", (2.45, 1.40)),
            ("thunder-strike", (1.40, 0.45)),
            ("enter", (0.45, 1.00)),
        ],
    },
    "final_barrier": {
        "hero": [
            ("enter", (-2.55, -1.50)),
            ("dragon-palm", (-1.50, -0.20)),
            ("dragon-palm", (-0.20, 0.55)),
        ],
        "rival": [
            ("point", (2.20, 1.70)),
            ("thunder-strike", (1.70, 0.80)),
            ("enter", (0.80, 1.30)),
        ],
    },
    "stair_duel": {
        "hero": [
            ("point", (-2.40, -1.85)),
            ("enter", (-1.85, -1.10)),
            ("dragon-palm", (-1.10, -0.20)),
        ],
        "rival": [
            ("point", (2.10, 1.80)),
            ("enter", (1.80, 1.10)),
            ("point", (1.10, 1.45)),
        ],
    },
    "ceasefire_exit": {
        "hero": [
            ("point", (-2.25, -1.80)),
            ("enter", (-1.80, -1.35)),
            ("exit", (-1.35, -2.45)),
        ],
        "rival": [
            ("point", (1.95, 1.75)),
            ("enter", (1.75, 1.45)),
            ("point", (1.45, 1.70)),
        ],
    },
    "departure": {
        "hero": [
            ("enter", (-2.60, -2.05)),
            ("point", (-2.05, -1.75)),
            ("exit", (-1.75, -2.75)),
        ],
        "rival": [
            ("point", (2.20, 1.95)),
            ("point", (1.95, 1.75)),
            ("exit", (1.75, 2.35)),
        ],
    },
}

SCENE_ACTION_PROFILE = [
    "gate_probe",
    "hard_standoff",
    "hard_standoff",
    "hall_pressure",
    "hall_pressure",
    "first_strike",
    "formation_push",
    "hall_pressure",
    "leader_confrontation",
    "mixed_brawl",
    "corridor_breath",
    "leader_confrontation",
    "truth_pressure",
    "sneak_attack",
    "final_barrier",
    "formation_push",
    "stair_duel",
    "truth_pressure",
    "ceasefire_exit",
    "departure",
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


def _beat(
    start_ms: int,
    end_ms: int,
    actor_id: str,
    motion: str,
    *,
    x0: float | None = None,
    x1: float | None = None,
    z0: float = 0.0,
    z1: float = 0.0,
    facing: str | None = None,
    effect: str | None = None,
    emotion: str = "charged",
) -> dict:
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
    if any(token in text for token in ("掌", "闯", "拦", "退", "阵", "打", "逼", "拿下", "偷袭")):
        return "fierce"
    if any(token in text for token in ("求", "信", "法度", "慈悲", "交代")):
        return "deadpan"
    if any(token in text for token in ("伤", "死", "撑不住", "生机")):
        return "hurt"
    if any(token in text for token in ("笑", "体面", "漂亮话")):
        return "smirk"
    return "talk"


def _motion_expression(motion: str) -> str:
    if motion in {"dragon-palm", "thunder-strike", "sword-arc"}:
        return "fierce"
    if motion in {"enter", "exit"}:
        return "deadpan"
    return "talk"


def _scene_actors(outline: dict, scene_index: int) -> list[dict]:
    actor_ids = outline["actors"]
    opponent = outline["opponent"]
    support_positions = [(-1.0, -0.22), (3.9, -0.16), (-3.0, -0.24)]
    actors: list[dict] = []
    support_index = 0
    for actor_id in actor_ids:
        if actor_id == "qiao_feng":
            actors.append(_actor(actor_id, -2.7 + 0.10 * (scene_index % 2), 0.02, "right", 1.08))
        elif actor_id == opponent:
            actors.append(_actor(actor_id, 2.5 - 0.14 * (scene_index % 3), 0.0, "left", 1.0))
        elif actor_id == "azhu":
            actors.append(_actor(actor_id, -4.1, -0.14, "right", 0.90, layer="mid"))
        else:
            x, z = support_positions[support_index % len(support_positions)]
            support_index += 1
            facing = "left" if x > 0 else "right"
            actors.append(_actor(actor_id, x, z, facing, 0.94, layer="mid"))
    return actors


def _scene_props(prop_ids: list[str], scene_index: int) -> list[dict]:
    xs = [-4.1, 0.0, 4.0]
    zs = [-1.08, -0.90, -1.00]
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


def _dialogues_and_talk_beats(lines: list[tuple[str, str]]) -> tuple[list[dict], list[dict], list[dict]]:
    dialogues: list[dict] = []
    beats: list[dict] = []
    expressions: list[dict] = []
    for (start_ms, end_ms), (speaker_id, text) in zip(DIALOGUE_WINDOWS, lines):
        dialogues.append(_dialogue(start_ms, end_ms, speaker_id, text))
        beats.append(_beat(start_ms, end_ms, speaker_id, "talk", facing=None, emotion="focused"))
        expressions.append(_expression(speaker_id, start_ms, end_ms, _expression_for_text(text)))
    return dialogues, beats, expressions


def _action_beats(scene_index: int, opponent: str) -> tuple[list[dict], list[dict], list[str]]:
    beats: list[dict] = []
    expressions: list[dict] = []
    effect_ids: set[str] = set()
    profile_id = SCENE_ACTION_PROFILE[scene_index]
    profile = ACTION_PROFILES[profile_id]
    hero_actions = profile["hero"]
    rival_actions = profile["rival"]

    for (start_ms, end_ms), (hero_motion, (hero_from_x, hero_to_x)), (rival_motion, (rival_from_x, rival_to_x)) in zip(
        ACTION_WINDOWS,
        hero_actions,
        rival_actions,
    ):
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

        rival_effect = rival_motion if rival_motion in {"dragon-palm", "thunder-strike", "sword-arc"} else None
        beats.append(
            _beat(
                start_ms + 180,
                end_ms + 180,
                opponent,
                rival_motion,
                x0=rival_from_x,
                x1=rival_to_x,
                facing="left",
                effect=rival_effect,
            )
        )
        expressions.append(_expression(opponent, start_ms + 180, end_ms + 180, _motion_expression(rival_motion)))
        if rival_effect:
            effect_ids.add(rival_effect)

    return beats, expressions, sorted(effect_ids)


def _camera(scene_index: int) -> dict:
    return {
        "type": "pan",
        "x": -0.28 + 0.06 * (scene_index % 3),
        "z": 0.03,
        "zoom": 1.00 + 0.03 * (scene_index % 2),
        "to_x": 0.22 - 0.04 * (scene_index % 2),
        "to_z": 0.01,
        "to_zoom": 1.08 + 0.02 * (scene_index % 3),
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
        dialogues, talk_beats, talk_expressions = _dialogues_and_talk_beats(outline["lines"])
        action_beats, action_expressions, effect_ids = _action_beats(scene_index, outline["opponent"])
        beats = sorted([*talk_beats, *action_beats], key=lambda item: (item["start_ms"], item["actor_id"]))
        expressions = sorted([*talk_expressions, *action_expressions], key=lambda item: (item["start_ms"], item["actor_id"]))

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
                "duration_ms": 15050,
                "summary": outline["summary"],
                "camera": _camera(scene_index),
                "effects": [{"type": effect_id} for effect_id in effect_ids],
                "props": _scene_props(outline["props"], scene_index),
                "actors": _scene_actors(outline, scene_index),
                "npc_groups": [],
                "beats": beats,
                "expressions": expressions,
                "dialogues": dialogues,
                "audio": {"bgm": None, "sfx": []},
            }
        )

    return {
        "meta": {
            "title": "乔峰大战少林寺",
            "language": "zh-CN",
            "theme": "武侠、寺门对峙、少林围战、追查雁门关旧案",
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
            "tts_enabled": True,
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
    parser = argparse.ArgumentParser(description="Generate a canonical 20-scene story for 乔峰大战少林寺.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    story = build_story()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(story, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    print(f"scene_count={len(story['scenes'])}")
    print(f"min_dialogue_turns={min(len(scene['dialogues']) for scene in story['scenes'])}")
    print(f"tts_enabled={story['video']['tts_enabled']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
