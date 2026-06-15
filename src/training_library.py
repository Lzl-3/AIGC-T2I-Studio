# -*- coding: utf-8 -*-
"""训练素材变体资产库

提供训练策略所需的所有变化维度：服装、武器、背景、构图、角度、表情、动作、手部、镜头距离、光线。
每个维度按训练策略比例分配。

训练目标：通用人物 LoRA + 仙侠/武侠动作泛化
"""

from typing import Optional

# ============================================================
# 服装变体库（英文 Prompt 标签）
# 保持 5 套服装多样性，避免服装过度固定
# ============================================================

COSTUME_VARIANTS = {
    "white_hanfu": {
        "label": "白衣汉服",
        "prompt": "white hanfu dress, flowing silk fabric, elegant wide sleeves, traditional chinese costume, PBR fabric rendering",
        "ratio": 0.25,
    },
    "cyan_robe": {
        "label": "青衣",
        "prompt": "cyan daoist robe, layered silk garments, embroidered trim, flowing fabric, traditional cultivator attire",
        "ratio": 0.20,
    },
    "black_robe": {
        "label": "黑衣",
        "prompt": "black martial arts robe, dark fabric, sleek silhouette, fitted cut, warrior attire",
        "ratio": 0.20,
    },
    "light_casual": {
        "label": "浅色便服",
        "prompt": "light cream casual wear, soft beige fabric, simple elegant cut, relaxed fit",
        "ratio": 0.20,
    },
    "dark_formal": {
        "label": "深色正装",
        "prompt": "dark formal attire, navy blue robe, structured silhouette, refined details, dignified appearance",
        "ratio": 0.15,
    },
}

# ============================================================
# 背景类型（降低复杂场景权重，保证训练重点是人物）
# ============================================================

BACKGROUND_VARIANTS = {
    "studio": {
        "label": "摄影棚",
        "pool": [
            "grey studio background, soft diffused lighting, clean minimal backdrop, photography studio",
            "light grey seamless background, portrait lighting setup, clean professional backdrop",
            "dark grey gradient background, rim lighting, studio portrait setup",
            "soft beige studio background, warm ambient light, clean backdrop",
            "white seamless background, even lighting, clean studio look",
        ],
        "ratio": 0.55,
    },
    "blurred": {
        "label": "虚化背景",
        "pool": [
            "shallow depth of field, bokeh background, blurred natural scenery",
            "soft bokeh lights, out of focus background, dreamy atmosphere",
            "blurred garden background, soft focus, ethereal atmosphere",
            "depth of field blur, cinematic bokeh, soft background separation",
        ],
        "ratio": 0.15,
    },
    "indoor_simple": {
        "label": "简单室内",
        "pool": [
            "traditional chinese interior, wooden furniture, soft lantern light, simple room",
            "minimalist room, clean walls, natural window light, serene atmosphere",
            "simple study room, wooden desk, scroll paintings, quiet indoor setting",
            "bamboo interior, simple decor, soft shadows, peaceful room",
        ],
        "ratio": 0.15,
    },
    "courtyard": {
        "label": "庭院",
        "pool": [
            "traditional chinese courtyard, stone pathway, potted plants, tranquil garden",
            "zen garden, raked sand, small bonsai trees, peaceful courtyard",
            "ancient courtyard, weathered stone walls, climbing vines, historic atmosphere",
        ],
        "ratio": 0.10,
    },
    "themed": {
        "label": "题材环境",
        "pool": [
            "misty bamboo forest, soft green atmosphere, ethereal lighting",
            "mountain peak at dawn, sea of clouds, majestic sunrise",
        ],
        "ratio": 0.05,
    },
}

# ============================================================
# 武器变体（人物 LoRA 不固定武器，混搭出现）
# ============================================================

WEAPON_VARIANTS = {
    "sword": {
        "label": "持剑",
        "prompt": "holding a chinese jian sword, ornate silver blade, red tassel, PBR metal",
        "count": 20,
    },
    "no_weapon": {
        "label": "无武器",
        "prompt": "",
        "count": 100,
    },
    "book": {
        "label": "持书",
        "prompt": "holding an ancient book, leather-bound tome, scholarly accessory",
        "count": 10,
    },
    "umbrella": {
        "label": "持伞",
        "prompt": "holding a paper umbrella, oil-paper parasol, traditional chinese umbrella, elegant accessory",
        "count": 10,
    },
    "empty_hands": {
        "label": "空手",
        "prompt": "empty hands, relaxed natural pose, hands at sides",
        "count": 10,
    },
}

# ============================================================
# 构图（全身占比提升至 45%，突出完整人物结构学习）
# ============================================================

COMPOSITION_VARIANTS = {
    "full_body": {
        "label": "全身",
        "prompt": "full body shot, standing pose, complete figure from head to toe",
        "ratio": 0.45,
    },
    "half_body": {
        "label": "半身",
        "prompt": "half body shot, waist up, medium shot framing",
        "ratio": 0.25,
    },
    "bust": {
        "label": "胸像",
        "prompt": "bust shot, head and shoulders portrait, upper chest framing",
        "ratio": 0.15,
    },
    "closeup": {
        "label": "特写",
        "prompt": "close-up shot, tight face framing, detailed facial features, portrait macro",
        "ratio": 0.10,
    },
    "environmental": {
        "label": "环境人像",
        "prompt": "environmental portrait, figure in a wider scene, cinematic wide shot",
        "ratio": 0.05,
    },
}

# ============================================================
# 角度（保留基础角度 + 新增俯视/仰视/回眸）
# ============================================================

ANGLE_VARIANTS = {
    "front": {
        "label": "正脸",
        "prompt": "front view, looking at viewer, symmetrical face",
        "ratio": 0.25,
    },
    "left45": {
        "label": "左45度",
        "prompt": "three-quarter view from left, 45 degree angle, profile leaning",
        "ratio": 0.15,
    },
    "right45": {
        "label": "右45度",
        "prompt": "three-quarter view from right, 45 degree angle, profile leaning",
        "ratio": 0.15,
    },
    "side": {
        "label": "侧脸",
        "prompt": "side profile view, looking to the side, silhouette",
        "ratio": 0.10,
    },
    "back_turn": {
        "label": "背转/回眸",
        "prompt": "looking back over shoulder, back view with face turning, dynamic twist",
        "ratio": 0.10,
    },
    "low_angle": {
        "label": "仰视",
        "prompt": "low angle shot, looking up at figure, heroic perspective, worm\'s eye view",
        "ratio": 0.10,
    },
    "high_angle": {
        "label": "俯视",
        "prompt": "high angle shot, looking down at figure, bird\'s eye perspective",
        "ratio": 0.10,
    },
    "overhead": {
        "label": "俯仰",
        "prompt": "dynamic camera angle, slight dutch angle, dramatic perspective",
        "ratio": 0.05,
    },
}

# ============================================================
# 表情（保留基础表情 + 新增严肃/自信/惊讶，避免过度极端）
# ============================================================

EXPRESSION_VARIANTS = {
    "calm": {
        "label": "平静",
        "prompt": "calm expression, neutral face, serene gaze, relaxed features",
        "ratio": 0.35,
    },
    "smile": {
        "label": "微笑",
        "prompt": "gentle smile, soft expression, warm slight smile, kind eyes",
        "ratio": 0.20,
    },
    "cool": {
        "label": "清冷",
        "prompt": "cool detached expression, aloof gaze, sharp focused eyes, distant look",
        "ratio": 0.10,
    },
    "serious": {
        "label": "严肃",
        "prompt": "serious expression, determined gaze, focused intensity, composed features",
        "ratio": 0.10,
    },
    "confident": {
        "label": "自信",
        "prompt": "confident expression, self-assured gaze, slight smirk, proud bearing",
        "ratio": 0.10,
    },
    "thoughtful": {
        "label": "若有所思",
        "prompt": "thoughtful expression, looking into distance, contemplative gaze, pensive mood",
        "ratio": 0.05,
    },
    "happy": {
        "label": "开心",
        "prompt": "happy expression, bright smile, joyful eyes, cheerful mood",
        "ratio": 0.05,
    },
    "surprised": {
        "label": "惊讶",
        "prompt": "slightly surprised expression, widened eyes, gently parted lips, subtle astonishment",
        "ratio": 0.05,
    },
}

# ============================================================
# 动作（三层结构：基础人物动作 / 仙侠气质动作 / 战斗动作）
# 总计 20 个动作，避免大量重复站姿
# ============================================================

ACTION_VARIANTS = {
    # ---- 第一层：基础人物动作（占比 40%）----
    "natural_standing": {
        "label": "自然站立",
        "prompt": "natural standing pose, relaxed upright posture, arms at sides, balanced stance",
        "ratio": 0.10,
    },
    "walking": {
        "label": "行走",
        "prompt": "walking pose, mid-stride, flowing movement, dynamic walk cycle",
        "ratio": 0.08,
    },
    "turning_back": {
        "label": "转身回望",
        "prompt": "turning pose, looking back over shoulder, dynamic twist, body in motion",
        "ratio": 0.07,
    },
    "sitting": {
        "label": "坐姿",
        "prompt": "sitting pose, seated position, relaxed posture, elegant seated figure",
        "ratio": 0.06,
    },
    "looking_far": {
        "label": "远眺",
        "prompt": "looking into distance, gazing at horizon, peaceful faraway stare, contemplative standing",
        "ratio": 0.05,
    },
    "waving": {
        "label": "挥手",
        "prompt": "waving hand gesture, greeting pose, arm raised gently",
        "ratio": 0.04,
    },

    # ---- 第二层：仙侠气质动作（占比 35%）----
    "holding_sword": {
        "label": "持剑",
        "prompt": "holding a sword gracefully, blade at side, elegant sword stance, cultivator bearing",
        "ratio": 0.06,
    },
    "sword_on_back": {
        "label": "背剑",
        "prompt": "sword carried on back, blade visible behind shoulder, warrior burden, xianxia swordsman",
        "ratio": 0.05,
    },
    "hand_seal": {
        "label": "手诀",
        "prompt": "making hand seal gesture, fingers forming mystical mudra, cultivator casting technique",
        "ratio": 0.05,
    },
    "reading_scroll": {
        "label": "阅读卷轴",
        "prompt": "reading an ancient scroll, studying scripture, scholarly cultivator pose, focused reading",
        "ratio": 0.04,
    },
    "holding_fan": {
        "label": "持扇",
        "prompt": "holding an elegant folding fan, refined gesture, scholar bearing, graceful fan pose",
        "ratio": 0.04,
    },
    "holding_umbrella": {
        "label": "持伞",
        "prompt": "holding a paper umbrella, oil-paper parasol, elegant rainy day pose, traditional bearing",
        "ratio": 0.04,
    },
    "hands_behind": {
        "label": "双手背后",
        "prompt": "hands clasped behind back, dignified posture, composed stance, elder bearing",
        "ratio": 0.04,
    },
    "adjusting_sleeve": {
        "label": "整理衣袖",
        "prompt": "adjusting flowing sleeve, graceful hand movement, elegant gesture, traditional mannerism",
        "ratio": 0.03,
    },

    # ---- 第三层：战斗动作（占比 25%）----
    "sword_ready": {
        "label": "剑势待发",
        "prompt": "sword ready stance, poised for combat, blade drawn and steady, focused martial intent",
        "ratio": 0.04,
    },
    "drawing_sword": {
        "label": "拔剑",
        "prompt": "drawing sword from sheath, dynamic unsheathing motion, blade partially revealed, intense moment",
        "ratio": 0.04,
    },
    "sword_slash": {
        "label": "挥剑",
        "prompt": "sword slash motion, sweeping blade arc, dynamic attack movement, martial arts combat",
        "ratio": 0.04,
    },
    "sword_pointing": {
        "label": "剑指",
        "prompt": "sword pointing forward, blade extended toward enemy, focused aim, offensive stance",
        "ratio": 0.03,
    },
    "combat_stance": {
        "label": "战斗姿态",
        "prompt": "combat stance, martial arts ready position, balanced fighting posture, warrior guard",
        "ratio": 0.04,
    },
    "casting_spell": {
        "label": "施法",
        "prompt": "casting a spell, mystical energy gathering, glowing hands, cultivator unleashing power",
        "ratio": 0.04,
    },
    "defensive_stance": {
        "label": "防御姿态",
        "prompt": "defensive stance, guarded posture, bracing for impact, low center of gravity, martial defense",
        "ratio": 0.02,
    },
}

# ============================================================
# 手部动作维度（增强手部泛化能力与结构学习质量）
# ============================================================

HAND_VARIANTS = {
    "natural": {
        "label": "自然",
        "prompt": "hands relaxed at sides, natural finger position, anatomically correct hands",
        "ratio": 0.30,
    },
    "single_hand_object": {
        "label": "单手执物",
        "prompt": "one hand holding object, single hand grip, detailed fingers wrapped around item",
        "ratio": 0.15,
    },
    "double_hand_object": {
        "label": "双手执物",
        "prompt": "both hands holding object, two-handed grip, hands working together",
        "ratio": 0.10,
    },
    "hands_behind": {
        "label": "双手背后",
        "prompt": "hands behind back, fingers interlaced, relaxed back grip",
        "ratio": 0.10,
    },
    "crossed_arms": {
        "label": "抱臂",
        "prompt": "arms crossed over chest, hands resting on opposite arms, folded arms pose",
        "ratio": 0.10,
    },
    "touch_hair": {
        "label": "抚发",
        "prompt": "one hand touching hair, fingers gently brushing strands, elegant hand near face",
        "ratio": 0.10,
    },
    "touch_face": {
        "label": "触脸",
        "prompt": "hand near face, fingers touching chin or cheek, thoughtful hand placement",
        "ratio": 0.05,
    },
    "pointing": {
        "label": "指点",
        "prompt": "hand pointing gesture, finger extended, directing motion, clear hand shape",
        "ratio": 0.10,
    },
}

# ============================================================
# 镜头距离维度（丰富画面空间层次）
# ============================================================

SHOT_DISTANCE_VARIANTS = {
    "close_shot": {
        "label": "近景",
        "prompt": "close shot, intimate framing, detailed facial view, portrait distance",
        "ratio": 0.10,
    },
    "medium_shot": {
        "label": "中景",
        "prompt": "medium shot, standard framing, natural viewing distance, balanced composition",
        "ratio": 0.60,
    },
    "long_shot": {
        "label": "远景",
        "prompt": "long shot, full figure in environment, distant framing, space around subject",
        "ratio": 0.25,
    },
    "wide_environmental": {
        "label": "广角环境",
        "prompt": "wide angle environmental shot, small figure in vast landscape, expansive composition",
        "ratio": 0.05,
    },
}

# ============================================================
# 光线维度（增强光照泛化能力）
# ============================================================

LIGHTING_VARIANTS = {
    "soft_light": {
        "label": "柔光",
        "prompt": "soft diffused lighting, gentle illumination, even light distribution, flattering light",
        "ratio": 0.30,
    },
    "studio_light": {
        "label": "摄影棚光",
        "prompt": "studio lighting, professional portrait lighting, three-point lighting, clean illumination",
        "ratio": 0.25,
    },
    "side_light": {
        "label": "侧光",
        "prompt": "side lighting, dramatic half-lit face, chiaroscuro effect, directional light from side",
        "ratio": 0.15,
    },
    "warm_light": {
        "label": "暖光",
        "prompt": "warm golden light, sunset glow, amber illumination, cozy atmosphere",
        "ratio": 0.15,
    },
    "cool_light": {
        "label": "冷光",
        "prompt": "cool blue light, moonlight illumination, cold atmospheric lighting, silver tones",
        "ratio": 0.10,
    },
    "rim_light": {
        "label": "轮廓光",
        "prompt": "rim lighting, backlit silhouette, edge light defining figure outline, dramatic backlight",
        "ratio": 0.05,
    },
}

# ============================================================
# 全局质量标签（附加到每条 Prompt 末尾）
# ============================================================

QUALITY_TAGS = (
    "masterpiece, best quality, highly detailed, sharp focus, "
    "professional lighting, 8k resolution, cinematic composition"
)

NEGATIVE_TAGS = (
    "lowres, bad anatomy, bad hands, worst quality, jpeg artifacts, "
    "blurry, deformed, disfigured, extra limbs, fused fingers, "
    "ugly, poorly drawn, watermark, text, signature"
)

# ============================================================
# 汇总函数
# ============================================================

def get_all_dimensions() -> dict:
    """返回所有训练素材维度的元数据，供前端配置面板使用。"""
    return {
        "costume": {
            "label": "服装",
            "variants": [
                {"key": k, "label": v["label"], "ratio": v["ratio"]}
                for k, v in COSTUME_VARIANTS.items()
            ],
        },
        "background": {
            "label": "背景",
            "variants": [
                {"key": k, "label": v["label"], "ratio": v["ratio"]}
                for k, v in BACKGROUND_VARIANTS.items()
            ],
        },
        "composition": {
            "label": "构图",
            "variants": [
                {"key": k, "label": v["label"], "ratio": v["ratio"]}
                for k, v in COMPOSITION_VARIANTS.items()
            ],
        },
        "angle": {
            "label": "角度",
            "variants": [
                {"key": k, "label": v["label"], "ratio": v["ratio"]}
                for k, v in ANGLE_VARIANTS.items()
            ],
        },
        "expression": {
            "label": "表情",
            "variants": [
                {"key": k, "label": v["label"], "ratio": v["ratio"]}
                for k, v in EXPRESSION_VARIANTS.items()
            ],
        },
        "action": {
            "label": "动作",
            "variants": [
                {"key": k, "label": v["label"], "ratio": v["ratio"]}
                for k, v in ACTION_VARIANTS.items()
            ],
        },
        "hand": {
            "label": "手部",
            "variants": [
                {"key": k, "label": v["label"], "ratio": v["ratio"]}
                for k, v in HAND_VARIANTS.items()
            ],
        },
        "shot_distance": {
            "label": "镜头距离",
            "variants": [
                {"key": k, "label": v["label"], "ratio": v["ratio"]}
                for k, v in SHOT_DISTANCE_VARIANTS.items()
            ],
        },
        "lighting": {
            "label": "光线",
            "variants": [
                {"key": k, "label": v["label"], "ratio": v["ratio"]}
                for k, v in LIGHTING_VARIANTS.items()
            ],
        },
        "weapon": {
            "label": "武器",
            "variants": [
                {"key": k, "label": v["label"], "count": v["count"]}
                for k, v in WEAPON_VARIANTS.items()
            ],
        },
    }
