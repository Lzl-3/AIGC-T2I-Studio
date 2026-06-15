# -*- coding: utf-8 -*-
"""Character presets v2: 7 characters with identity + emotion fields for 13-layer prompt architecture.
"""

from typing import Optional

# Gender tags mapping
GENDER_TAGS = {
    "female": "1girl, asian woman, female, chinese facial features",
    "male": "1boy, asian man, male, chinese facial features",
    "elder_male": "elderly asian man, mature asian male, dignified presence",
    "elder_female": "elderly asian woman, mature asian female, graceful aging",
    "young_female": "1girl, young asian girl, youthful, adolescent female, chinese facial features",
    "young_male": "1boy, young asian boy, youthful, adolescent male, chinese facial features",
    "monster": "monster, demon, creature, supernatural being",
    "mythical_beast": "mythical beast, divine creature, sacred beast, spirit animal",
}

# Genre environment tags
GENRE_ENVIRONMENT_TAGS = {
    "xianxia": "xianxia cultivator, bamboo forest, misty atmosphere",
    "urban": "modern city street, warm lighting",
    "transmigration": "ancient palace, dimensional portal, dramatic sky",
    "historical": "ancient chinese palace, lanterns, traditional courtyard",
    "modern_era": "old shanghai street, vintage architecture, nostalgic atmosphere, warm sepia",
    "supernatural": "foggy street, dim moonlight, eerie atmosphere",
    "sci_fi": "ruined city, dystopian landscape, neon city, dramatic sky, industrial",
    "esports": "esports arena, gaming studio, led stage, neon lighting, tournament hall",
}

# Generic character fallbacks
DEFAULT_CHARACTER_FALLBACKS = {
    "female": ("slender figure, delicate oval face, dark brown almond eyes, smooth fair skin, soft asian feminine features, natural makeup, long black hair, natural skin texture"),
    "male": ("athletic build, sharp defined jawline, dark brown eyes, clean skin, asian masculine features, angular face, black hair, heroic temperament"),
    "1girl": ("slender figure, delicate oval face, dark brown almond eyes, smooth fair skin, soft asian feminine features, natural makeup, black hair, natural skin texture"),
    "1boy": ("athletic build, sharp defined jawline, dark brown eyes, clean skin, asian masculine features, black hair, heroic temperament"),
    "elder_male": ("mature asian face, dignified presence, deep wise dark eyes, silver-streaked black hair, weathered refined features"),
    "elder_female": ("mature asian face, graceful aging, wise gentle dark eyes, silver hair, elegant features, dignified posture"),
    "young_female": ("petite figure, cute round face, large sparkling dark eyes, youthful glow, innocent expression, rosy cheeks, black hair"),
    "young_male": ("youthful asian face, energetic dark eyes, clear skin, teenage build, lively expression, black hair"),
    "monster": ("fierce glowing eyes, razor-sharp teeth, monstrous visage, intimidating presence, dark aura, inhuman proportions"),
    "mythical_beast": ("majestic presence, divine luminous aura, ornate mythical features, glowing ethereal eyes"),
}


CHARACTER_PRESETS = {
    "Lin Xiaoxiao": {
        "gender": "female",
        "trigger_word": "Lin Xiaoxiao",
        "identity": "young female cultivator, 168cm, nine-head body proportion, slender and graceful, young adult",
        "face": (
            "delicate oval face, fair porcelain skin, dark brown almond eyes, "
            "straight natural eyebrows, small refined nose, soft lips, "
            "asian feminine features, clean facial topology, 3D rendered face"
        ),
        "emotion": "calm expression, neutral face, serene gaze, relaxed features",
        "hair": (
            "long straight black hair reaching waist, silky smooth, flowing strands, "
            "simple silver hair crown accessory, elegant updo, "
            "dark lustrous shine, detailed hair strands, hair physics"
        ),
        "clothing": (
            "white hanfu dress, flowing silk fabric, elegant wide sleeves, "
            "traditional chinese costume, PBR fabric rendering, "
            "AAA quality fabric rendering"
        ),
        "weapon": (
            "holding a chinese jian sword, ornate silver blade, "
            "red tassel, PBR metal, detailed weapon"
        ),
        "composition": "bust shot, head and shoulders portrait, upper chest framing, front view, looking at viewer, symmetrical face",
    },

    "Ye Wuhen": {
        "gender": "male",
        "trigger_word": "Ye Wuhen",
        "identity": "young male dark cultivator",
        "face": (
            "sharp defined jawline, deep dark eyes, pale alabaster skin, "
            "straight refined nose, thin lips, asian masculine features, "
            "angular face structure, 3D rendered face"
        ),
        "emotion": "cold stern expression, piercing gaze, intimidating presence",
        "hair": (
            "long silver-white hair, windswept, ethereal flow, "
            "physically simulated hair, individual hair strands, "
            "metallic silver sheen, dramatic wind effect"
        ),
        "clothing": (
            "black daoist robe, PBR silk fabric, gold trim embroidery, "
            "dark inner robe, flowing dramatic cape, ancient chinese armor pauldrons, "
            "AAA game costume, dark fantasy aesthetic"
        ),
    },

    "Su Qianyue": {
        "gender": "female",
        "trigger_word": "Su Qianyue",
        "identity": "young female musician cultivator",
        "face": (
            "gentle round face, smooth porcelain skin, large sparkling dark brown doe eyes, "
            "cherry pink lips, soft natural eyebrows, "
            "asian feminine features, soft CG realism, 3D rendered face"
        ),
        "emotion": "sweet warm expression, kind eyes, gentle smile",
        "hair": (
            "twin buns with pink silk ribbons, long twin tails, "
            "dark brown silky hair, detailed braids, soft hair physics, "
            "delicate hair accessories"
        ),
        "clothing": (
            "pink and white qipao dress, cherry blossom embroidery, "
            "PBR silk fabric, delicate lace trim, elegant feminine cut, "
            "soft fabric rendering"
        ),
    },

    "Jian Wuji": {
        "gender": "male",
        "trigger_word": "Jian Wuji",
        "identity": "young male warrior cultivator",
        "face": (
            "angular chiseled face, fierce dark eyes, "
            "scar across left eyebrow, weathered tanned skin, "
            "strong masculine jaw, asian features, 3D rendered face"
        ),
        "emotion": "battle-hardened expression, determined gaze, fierce intensity",
        "hair": (
            "short spiky black hair, messy warrior style, "
            "dynamic hair rendering, wind-swept, rugged appearance"
        ),
        "clothing": (
            "dark red martial arts robe, PBR fabric, black pants, "
            "leather arm guards, battle-worn costume, "
            "AAA game character costume"
        ),
    },

    "Bai Linger": {
        "gender": "young_female",
        "trigger_word": "Bai Linger",
        "identity": "young female spirit cultivator",
        "face": (
            "small cute face, large sparkling dark brown eyes, "
            "fair youthful skin, cute petite nose, "
            "asian young girl, soft CG render"
        ),
        "emotion": "adorable expression, innocent gaze, bright cheerful smile",
        "hair": (
            "short white bob cut, fluffy soft texture, soft straight bangs, "
            "small red hairpin accessory, physically simulated short hair, "
            "clean hair silhouette"
        ),
        "clothing": (
            "white and red miko-style robe, golden bell accessories, "
            "ribbon sash with bow, layered flowing skirt, "
            "semi-realistic fabric, magical details"
        ),
    },

    "Mo Yuan": {
        "gender": "elder_male",
        "trigger_word": "Mo Yuan",
        "identity": "elder male imperial cultivator",
        "face": (
            "mature dignified asian face, deep-set piercing dark eyes, "
            "sharp aquiline nose, thin well-groomed beard, "
            "middle-aged, weathered wisdom, 3D rendered character"
        ),
        "emotion": "stern commanding expression, cold calculating gaze, authoritative presence",
        "hair": (
            "long black hair with silver-white streaks, "
            "half-up bun with golden hairpin, dignified styling, "
            "detailed hair rendering, wispy grey accents"
        ),
        "clothing": (
            "black and purple imperial dragon robe, heavy brocade fabric, "
            "golden dragon embroidery, golden crown headpiece, "
            "regal PBR fabric, majestic silhouette"
        ),
    },

    "Huo Lie": {
        "gender": "male",
        "trigger_word": "Huo Lie",
        "identity": "young male barbarian cultivator",
        "face": (
            "rugged battle-scarred face, fierce blazing dark eyes, "
            "weathered tanned skin, strong square jaw, "
            "asian features, intimidating presence, 3D rendered"
        ),
        "emotion": "fierce battle rage, burning intensity, wild aggressive gaze",
        "hair": (
            "wild red mane, unkempt and spiky, fiery orange-red tips, "
            "dynamic wind effect, raw untamed look, "
            "aggressive silhouette"
        ),
        "clothing": (
            "red and black barbarian armor, fur-trimmed shoulders, "
            "dark iron plates with battle damage, visible tribal tattoos, "
            "PBR metal and leather, savage aesthetic"
        ),
    },
}


# ============================================================
# 结构化8层角色数据（对齐仿真人提取规范）
# L1: 时代  L2: 身份  L3: 脸部  L4: 发型  L5: 上身
# L6: 下身  L7: 鞋履  L8: 配饰/妆容
# ============================================================

CHARACTER_LAYERS = {
    "Lin Xiaoxiao": {
        "era": "中国古代",
        "identity": {"gender": "女", "age": "青年", "height": "168cm", "body": "九头身比例，纤细修长"},
        "face": {"structure": "鹅蛋脸", "skin": "白皙细腻", "eyes": "深棕色杏眼", "nose": "精致小巧", "lips": "柔和唇形", "eyebrows": "自然平眉"},
        "hair": {"style": "黑长直及腰", "texture": "丝滑柔顺", "accessory": "简约银色发冠束发"},
        "upper": {"garment": "白色交领汉服上衣", "fabric": "丝绸", "sleeves": "广袖流云", "detail": "银色云纹暗绣"},
        "lower": {"garment": "淡蓝色百褶长裙", "fabric": "垂感丝绸", "detail": "金色滚边"},
        "footwear": {"type": "白色绣花布鞋", "detail": "银色绣纹"},
        "accessories": ["银色发冠", "玉质耳坠", "银色细手链", "红色腰束配金饰"],
        "makeup": "清透自然妆，淡雅素净",
        "temperament": "优雅温婉，仙气飘飘，沉静内敛",
        "style": "",
    },
    "Ye Wuhen": {
        "era": "中国古代",
        "identity": {"gender": "男", "age": "青年", "height": "185cm", "body": "高大挺拔，精瘦有力"},
        "face": {"structure": "棱角分明", "skin": "苍白冷白皮", "eyes": "深邃黑眸", "nose": "挺拔直鼻", "lips": "薄唇", "eyebrows": "凌厉剑眉"},
        "hair": {"style": "银白长发", "texture": "飘逸飞扬", "accessory": "无发冠，自然披散"},
        "upper": {"garment": "黑色道袍", "fabric": "丝绸", "sleeves": "宽袖", "detail": "金线镶边刺绣"},
        "lower": {"garment": "黑色长裤", "fabric": "丝绸", "detail": "暗纹"},
        "footwear": {"type": "黑色长靴", "detail": "金属饰扣"},
        "accessories": ["金色护肩甲", "暗色披风", "龙纹腰封"],
        "makeup": "偏冷白皮，凌厉眉形",
        "temperament": "冷酷无情，孤傲狠厉，杀伐果断",
        "style": "",
    },
    "Su Qianyue": {
        "era": "中国古代",
        "identity": {"gender": "女", "age": "青年", "height": "160cm", "body": "娇小玲珑"},
        "face": {"structure": "圆脸", "skin": "白皙细腻", "eyes": "大眼棕色", "nose": "小巧", "lips": "樱桃粉唇", "eyebrows": "柔和弯眉"},
        "hair": {"style": "双丸子头配双马尾", "texture": "深棕色丝滑", "accessory": "粉色丝带蝴蝶结"},
        "upper": {"garment": "粉白旗袍式上衣", "fabric": "丝绸", "sleeves": "短袖", "detail": "樱花刺绣"},
        "lower": {"garment": "粉色褶裙", "fabric": "轻纱", "detail": "蕾丝花边"},
        "footwear": {"type": "粉色绣花鞋", "detail": "蝴蝶结装饰"},
        "accessories": ["粉色丝带发饰", "玉质手镯", "小巧耳钉"],
        "makeup": "自然妆，粉嫩腮红，柔和眉形",
        "temperament": "甜美温柔，善良纯真，聪慧灵动",
        "style": "",
    },
    "Jian Wuji": {
        "era": "中国古代",
        "identity": {"gender": "男", "age": "青年", "height": "190cm", "body": "魁梧健壮，肌肉分明"},
        "face": {"structure": "国字脸，棱角分明", "skin": "古铜色，风吹日晒", "eyes": "锐利黑眸", "nose": "宽鼻梁", "lips": "厚唇", "eyebrows": "浓眉，左眉有疤"},
        "hair": {"style": "黑色短发，凌乱刺猬头", "texture": "粗硬", "accessory": "无"},
        "upper": {"garment": "暗红色武服", "fabric": "棉麻", "sleeves": "窄袖", "detail": "磨损痕迹"},
        "lower": {"garment": "黑色束脚武裤", "fabric": "棉布", "detail": ""},
        "footwear": {"type": "黑色皮靴", "detail": "金属护胫"},
        "accessories": ["皮质护臂", "粗布腰带", "旧伤疤"],
        "makeup": "不修边幅，天然肤色",
        "temperament": "豪迈粗犷，热血无畏，刚毅坚定",
        "style": "",
    },
    "Bai Linger": {
        "era": "仙侠古风",
        "identity": {"gender": "女", "age": "少女", "height": "145cm", "body": "娇小可爱"},
        "face": {"structure": "小圆脸", "skin": "白皙粉嫩", "eyes": "大眼深棕色", "nose": "小巧可爱", "lips": "樱桃小嘴", "eyebrows": "自然淡眉"},
        "hair": {"style": "白色短发波波头", "texture": "蓬松柔软", "accessory": "红色小发夹"},
        "upper": {"garment": "白红巫女式上衣", "fabric": "棉麻", "sleeves": "宽袖", "detail": "金色铃铛装饰"},
        "lower": {"garment": "红色褶裙", "fabric": "棉布", "detail": "蝴蝶结腰带"},
        "footwear": {"type": "白色布鞋", "detail": "红色绑带"},
        "accessories": ["红色发夹", "金色铃铛", "红色丝带"],
        "makeup": "素颜清纯，天然婴儿肌",
        "temperament": "天真可爱，活泼灵动，元气满满",
        "style": "",
    },
    "Mo Yuan": {
        "era": "中国古代",
        "identity": {"gender": "男", "age": "中年", "height": "182cm", "body": "伟岸挺拔，不怒自威"},
        "face": {"structure": "方脸，成熟", "skin": "暗沉，岁月痕迹", "eyes": "深邃锐利", "nose": "鹰钩鼻", "lips": "薄唇", "eyebrows": "浓眉，微白"},
        "hair": {"style": "黑色长发夹杂银丝", "texture": "梳理整齐", "accessory": "金色发冠半束"},
        "upper": {"garment": "黑紫龙纹袍", "fabric": "锦缎", "sleeves": "广袖", "detail": "金龙刺绣"},
        "lower": {"garment": "黑色长袍下摆", "fabric": "锦缎", "detail": "暗金滚边"},
        "footwear": {"type": "黑色官靴", "detail": "金线绣纹"},
        "accessories": ["金色发冠", "龙纹玉佩", "金色护腕"],
        "makeup": "沉稳成熟，细纹增添威严",
        "temperament": "威严深沉，智谋过人，深不可测",
        "style": "",
    },
    "Huo Lie": {
        "era": "中国古代",
        "identity": {"gender": "男", "age": "青年", "height": "195cm", "body": "虎背熊腰，肌肉虬结"},
        "face": {"structure": "方脸，粗犷", "skin": "古铜色，战痕累累", "eyes": "赤红怒目", "nose": "宽鼻", "lips": "厚唇", "eyebrows": "浓眉倒竖"},
        "hair": {"style": "红色狂野长发", "texture": "凌乱张扬", "accessory": "无"},
        "upper": {"garment": "红黑蛮族战甲", "fabric": "皮革+铁甲", "sleeves": "无袖", "detail": "部落刺青"},
        "lower": {"garment": "黑色战裤", "fabric": "皮革", "detail": "铁甲护膝"},
        "footwear": {"type": "黑色战靴", "detail": "铁甲护胫"},
        "accessories": ["兽皮毛领", "部落刺青", "铁甲护肩", "骨饰项链"],
        "makeup": "部落战纹，粗犷面容",
        "temperament": "狂野暴烈，桀骜不驯，热血沸腾",
        "style": "",
    },
}


def get_character_layers(name: str) -> Optional[dict]:
    """获取角色的结构化8层数据。"""
    return CHARACTER_LAYERS.get(name)


def update_character_layer(name: str, layer_key: str, value) -> bool:
    """更新角色的某一个结构化层（运行时修改，不持久化到文件）。

    Args:
        name: 角色名
        layer_key: 层名称 (era/identity/face/hair/upper/lower/footwear/accessories/makeup/temperament)
        value: 新值

    Returns:
        是否成功
    """
    char = CHARACTER_LAYERS.get(name)
    if not char:
        return False
    if layer_key in char:
        char[layer_key] = value
        return True
    return False


def get_character_preset(name: str) -> Optional[dict]:
    """Get character preset by name. Returns None if not found."""
    return CHARACTER_PRESETS.get(name)

def list_presets() -> list[dict]:
    """Return simplified info for all presets (for frontend display)."""
    return [
        {
            "name": name,
            "gender": preset.get("gender", "female"),
            "trigger_word": preset["trigger_word"],
            "identity": preset.get("identity", ""),
            "face": preset["face"],
            "emotion": preset.get("emotion", ""),
            "hair": preset["hair"],
            "clothing": preset["clothing"],
            "weapon": preset.get("weapon", ""),
        }
        for name, preset in CHARACTER_PRESETS.items()
    ]

def get_identity_only(name: str):
    """从完整角色预设中提取仅身份层（不含服装/武器）。供训练素材引擎使用。"""
    from typing import Optional
    preset = CHARACTER_PRESETS.get(name)
    if not preset:
        return None
    return {
        "name": name,
        "gender": preset.get("gender", "female"),
        "trigger_word": preset.get("trigger_word", name),
        "identity": preset.get("identity", ""),
        "face": preset.get("face", ""),
        "emotion": preset.get("emotion", ""),
        "hair": preset.get("hair", ""),
    }


# ============================================================
# 训练素材引擎接口（从 CHARACTER_LAYERS 提取纯身份）
# ============================================================

def get_training_identity(name: str):
    """从角色结构化层提取仅身份 Prompt 标签，供训练素材引擎使用。
    
    从 CHARACTER_LAYERS 读取，与角色调优面板共享同一数据源。
    返回 identity_tag/face/hair/body_type 用于拼接训练 Prompt；
    服装/武器/背景等变体由 training_library 提供。
    """
    layers = CHARACTER_LAYERS.get(name)
    if not layers:
        return None
    
    ident = layers["identity"]
    face_data = layers["face"]
    hair_data = layers["hair"]
    gender = ident.get("gender") or "女"
    age = ident.get("age") or "青年"
    body = ident.get("body") or ""
    
    # 身份标签（过滤空值）
    tag_parts = []
    if gender == "女":
        tag_parts.append("1girl")
    else:
        tag_parts.append("1boy")
    height = ident.get("height", "")
    if height and height.strip():
        tag_parts.append(height)
    if age and age.strip():
        tag_parts.append(age)
    if body and body.strip():
        tag_parts.append(body)
    identity_tag = ", ".join(tag_parts)
    
    # 脸部 Prompt（仅当源字段有实际内容时才构造标签）
    face_mappings = [
        ("structure", "face"),
        ("skin", "skin"),
        ("eyes", "eyes"),
        ("nose", ""),
        ("lips", ""),
        ("eyebrows", ""),
    ]
    face_parts = []
    for key, suffix in face_mappings:
        val = face_data.get(key, "").strip()
        if val:
            if suffix and not val.endswith(suffix):
                face_parts.append(val + " " + suffix)
            else:
                face_parts.append(val)
    face_prompt = ", ".join(face_parts)
    
    # 发型 Prompt（过滤空值）
    hair_parts = []
    style = hair_data.get("style", "").strip()
    texture = hair_data.get("texture", "").strip()
    accessory = hair_data.get("accessory", "").strip()
    if style:
        hair_parts.append(style)
    if texture:
        hair_parts.append(texture)
    if accessory:
        hair_parts.append(accessory)
    hair_prompt = ", ".join(hair_parts)
    
    return {
        "name": name,
        "gender": gender,
        "age_range": age,
        "trigger_word": name,
        "identity_tag": identity_tag,
        "face": face_prompt,
        "hair": hair_prompt,
        "body_type": body,
        "temperament": layers.get("temperament", ""),
        "makeup": layers.get("makeup", ""),
    }


def list_training_identities() -> list[dict]:
    """列出所有角色的训练身份摘要，供前端下拉框使用。"""
    return [
        {
            "key": name,
            "name": name,
            "gender": data["identity"].get("gender", "女"),
            "age_range": data["identity"].get("age", "青年"),
            "trigger_word": name,
        }
        for name, data in CHARACTER_LAYERS.items()
    ]
