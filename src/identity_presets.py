# -*- coding: utf-8 -*-
"""纯身份预设库 —— 仅包含锁定不变的身份层

与 character_presets.py 的区别：
  - character_presets: 身份 + 服装 + 武器（完整角色卡）
  - identity_presets:  仅身份层（脸/发型/气质/年龄/妆容）

训练策略要求身份锁定不变，服装/武器/背景变化。
"""

from typing import Optional

IDENTITY_PRESETS = {
    "Lin Xiaoxiao": {
        "name": "林潇潇",
        "gender": "female",
        "age_range": "青年",
        "trigger_word": "Lin Xiaoxiao",
        "identity_tag": "1girl, young female cultivator, asian",
        "face": "delicate oval face, fair porcelain skin, dark brown almond eyes, straight natural eyebrows, small refined nose, soft lips, asian feminine features, clean facial topology, 3D rendered face",
        "hair": "long straight black hair, silky smooth, flowing strands, physically simulated hair, detailed hair strands, waist-length, dark lustrous shine",
        "temperament": "优雅温婉, 仙气飘飘, 沉静内敛",
        "makeup": "自然妆, 淡雅素净, 国漫风格",
        "body_type": "纤细修长, 东方女性身材",
    },
    "Ye Wuhen": {
        "name": "夜无痕",
        "gender": "male",
        "age_range": "青年",
        "trigger_word": "Ye Wuhen",
        "identity_tag": "1boy, young male dark cultivator, asian",
        "face": "sharp defined jawline, deep dark eyes, pale alabaster skin, straight refined nose, thin lips, asian masculine features, angular face structure, 3D rendered face",
        "hair": "long silver-white hair, windswept, ethereal flow, physically simulated hair, individual hair strands, metallic silver sheen",
        "temperament": "冷酷无情, 孤傲狠厉, 杀伐果断",
        "makeup": "偏冷白皮, 凌厉眉形",
        "body_type": "高大挺拔, 精瘦有力",
    },
    "Su Qianyue": {
        "name": "苏浅月",
        "gender": "female",
        "age_range": "青年",
        "trigger_word": "Su Qianyue",
        "identity_tag": "1girl, young female musician cultivator, asian",
        "face": "gentle round face, smooth porcelain skin, large sparkling dark brown doe eyes, cherry pink lips, soft natural eyebrows, asian feminine features, soft CG realism, 3D rendered face",
        "hair": "twin buns with pink silk ribbons, long twin tails, dark brown silky hair, detailed braids, soft hair physics",
        "temperament": "甜美温柔, 善良纯真, 聪慧灵动",
        "makeup": "自然妆, 粉嫩腮红, 柔和眉形",
        "body_type": "娇小玲珑, 可爱身材",
    },
    "Jian Wuji": {
        "name": "剑无极",
        "gender": "male",
        "age_range": "青年",
        "trigger_word": "Jian Wuji",
        "identity_tag": "1boy, young male warrior cultivator, asian",
        "face": "angular chiseled face, fierce dark eyes, scar across left eyebrow, weathered tanned skin, strong masculine jaw, asian features, 3D rendered face",
        "hair": "short spiky black hair, messy warrior style, wind-swept, rugged appearance",
        "temperament": "豪迈粗犷, 热血无畏, 刚毅坚定",
        "makeup": "古铜肤色, 不修边幅",
        "body_type": "魁梧健壮, 肌肉分明",
    },
    "Bai Linger": {
        "name": "白灵儿",
        "gender": "young_female",
        "age_range": "少女",
        "trigger_word": "Bai Linger",
        "identity_tag": "1girl, young female spirit cultivator, asian, youthful",
        "face": "small cute face, large sparkling dark brown eyes, fair youthful skin, cute petite nose, asian young girl, soft CG render",
        "hair": "short white bob cut, fluffy soft texture, soft straight bangs, small red hairpin, physically simulated short hair, clean hair silhouette",
        "temperament": "天真可爱, 活泼灵动, 元气满满",
        "makeup": "素颜清纯, 天然婴儿肌",
        "body_type": "娇小可爱, 少女体态",
    },
    "Mo Yuan": {
        "name": "墨渊",
        "gender": "elder_male",
        "age_range": "中年",
        "trigger_word": "Mo Yuan",
        "identity_tag": "1boy, mature male imperial cultivator, asian, dignified",
        "face": "mature dignified asian face, deep-set piercing dark eyes, sharp aquiline nose, thin well-groomed beard, middle-aged, weathered wisdom, 3D rendered character",
        "hair": "long black hair with silver-white streaks, half-up bun with golden hairpin, dignified styling, wispy grey accents",
        "temperament": "威严深沉, 智谋过人, 深不可测",
        "makeup": "沉稳成熟, 细纹增添威严",
        "body_type": "伟岸挺拔, 不怒自威",
    },
    "Huo Lie": {
        "name": "霍烈",
        "gender": "male",
        "age_range": "青年",
        "trigger_word": "Huo Lie",
        "identity_tag": "1boy, young male barbarian cultivator, asian",
        "face": "rugged battle-scarred face, fierce blazing dark eyes, weathered tanned skin, strong square jaw, asian features, intimidating presence, 3D rendered",
        "hair": "wild red mane, unkempt and spiky, fiery orange-red tips, dynamic wind effect, raw untamed look",
        "temperament": "狂野暴烈, 桀骜不驯, 热血沸腾",
        "makeup": "部落战纹, 粗犷面容",
        "body_type": "虎背熊腰, 肌肉虬结",
    },
}


def get_identity(name: str) -> Optional[dict]:
    """获取指定角色的纯身份信息。"""
    return IDENTITY_PRESETS.get(name)


def list_identities() -> list[dict]:
    """列出所有纯身份预设，供前端下拉框使用。"""
    return [
        {
            "key": key,
            "name": data["name"],
            "gender": data["gender"],
            "age_range": data["age_range"],
            "trigger_word": data["trigger_word"],
            "temperament": data["temperament"],
        }
        for key, data in IDENTITY_PRESETS.items()
    ]