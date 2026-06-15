# -*- coding: utf-8 -*-
"""训练素材批量生成引擎

核心功能：
  给定角色身份 + 策略比例 → 生成 N 条英文 Prompt → 构造 GenerationRequest → 提交 task_manager

设计原则：
  - 身份锁定不变（face/hair/temperament/makeup/body_type 每张完全一致）
  - 服装/背景/武器/构图/角度/表情/动作按策略比例随机变化
  - 每批 10 张，支持预览（只出 Prompt 不提交）和正式生成
"""

import random
from typing import Optional
from src.character_presets import get_training_identity, CHARACTER_LAYERS
from src.training_library import (
    COSTUME_VARIANTS, BACKGROUND_VARIANTS, WEAPON_VARIANTS,
    COMPOSITION_VARIANTS, ANGLE_VARIANTS, EXPRESSION_VARIANTS,
    ACTION_VARIANTS, HAND_VARIANTS, SHOT_DISTANCE_VARIANTS, LIGHTING_VARIANTS,
    QUALITY_TAGS, NEGATIVE_TAGS,
    get_all_dimensions,
)
from src.models import GenerationRequest, WorkflowType, GenreType
from config.settings import ZIMAGE_MODEL, FLUX_MODEL


class MaterialBatchGenerator:
    """训练素材批量生成器。

    用法:
        gen = MaterialBatchGenerator("Lin Xiaoxiao", total=150)
        requests = gen.generate_requests()  # 返回 list[GenerationRequest]
        # 每个 request 包含 batch_prompts（默认每批 10 条）
    """

    def __init__(
        self,
        identity_key: str,
        total: int = 150,
        batch_size: int = 10,
        genre: GenreType = GenreType.XIANXIA,
        seed: Optional[int] = None,
        model_type: str = "sdxl",  # sdxl / flux / zimage
    ):
        self.identity = get_training_identity(identity_key)
        if self.identity is None:
            raise ValueError(f"未知角色: {identity_key}")

        self.identity_key = identity_key
        self.total = total
        self.batch_size = batch_size
        self.genre = genre
        self.model_type = model_type  # 底模类型
        self.rng = random.Random(seed) if seed is not None else random.Random()

        # 构建武器分配计划（按 count 而非 ratio）
        self._weapon_plan = self._build_weapon_plan()

    def _build_weapon_plan(self) -> list[str]:
        """根据武器 count 分配生成武器分配列表。

        例如 total=150 时: 20 sword + 20 none + 10 book + 10 umbrella + 10 empty = 70
        剩余的 80 张随机分配。
        """
        plan = []
        for key, variant in WEAPON_VARIANTS.items():
            count = min(variant["count"], self.total // len(WEAPON_VARIANTS) * 2)
            plan.extend([key] * count)

        # 填充剩余到 total
        remaining = self.total - len(plan)
        if remaining > 0:
            keys = list(WEAPON_VARIANTS.keys())
            for _ in range(remaining):
                plan.append(self.rng.choice(keys))

        self.rng.shuffle(plan)
        return plan[:self.total]

    def _pick_by_ratio(self, variants: dict, count: int) -> list[str]:
        """按比例随机选取 variant key。"""
        keys = list(variants.keys())
        ratios = [variants[k]["ratio"] for k in keys]
        return self.rng.choices(keys, weights=ratios, k=count)

    def _build_single_prompt(self, index: int) -> dict:
        """构建单张训练素材的完整 Prompt。

        Returns:
            {"positive": str, "negative": str, "meta": dict}
        """
        # 按比例随机选取各维度
        costume_key = self._pick_by_ratio(COSTUME_VARIANTS, 1)[0]
        bg_key = self._pick_by_ratio(BACKGROUND_VARIANTS, 1)[0]
        composition_key = self._pick_by_ratio(COMPOSITION_VARIANTS, 1)[0]
        angle_key = self._pick_by_ratio(ANGLE_VARIANTS, 1)[0]
        expression_key = self._pick_by_ratio(EXPRESSION_VARIANTS, 1)[0]
        action_key = self._pick_by_ratio(ACTION_VARIANTS, 1)[0]
        hand_key = self._pick_by_ratio(HAND_VARIANTS, 1)[0]
        shot_distance_key = self._pick_by_ratio(SHOT_DISTANCE_VARIANTS, 1)[0]
        lighting_key = self._pick_by_ratio(LIGHTING_VARIANTS, 1)[0]
        weapon_key = self._weapon_plan[index] if index < len(self._weapon_plan) else "no_weapon"

        # 随机选取背景词
        bg_pool = BACKGROUND_VARIANTS[bg_key]["pool"]
        bg_prompt = self.rng.choice(bg_pool)

        # 构建正向 Prompt（12 层架构）
        parts = [
            # Layer 0: 气质锚定（自由模型的完整 Prompt 在此，内置角色为空或简短气质词）
            self.identity.get("temperament", ""),
            # Layer 1: 身份标签
            self.identity["identity_tag"],
            # Layer 2: 脸
            self.identity["face"],
            # Layer 3: 发型
            self.identity["hair"],
            # Layer 3.5: 妆容
            self.identity.get("makeup", ""),
            # Layer 4: 体型
            self.identity.get("body_type", ""),
            # Layer 5: 服装
            COSTUME_VARIANTS[costume_key]["prompt"],
            # Layer 6: 构图
            COMPOSITION_VARIANTS[composition_key]["prompt"],
            # Layer 7: 镜头距离
            SHOT_DISTANCE_VARIANTS[shot_distance_key]["prompt"],
            # Layer 8: 角度 + 表情 + 动作
            ANGLE_VARIANTS[angle_key]["prompt"],
            EXPRESSION_VARIANTS[expression_key]["prompt"],
            ACTION_VARIANTS[action_key]["prompt"],
            # Layer 9: 手部
            HAND_VARIANTS[hand_key]["prompt"],
            # Layer 10: 光线
            LIGHTING_VARIANTS[lighting_key]["prompt"],
            # Layer 11: 背景 + 武器
            bg_prompt,
            WEAPON_VARIANTS[weapon_key]["prompt"],
            # 质量标签
            QUALITY_TAGS,
        ]

        positive = ", ".join(p.strip() for p in parts if p and p.strip())

        return {
            "positive": positive,
            "negative": NEGATIVE_TAGS,
            "meta": {
                "index": index + 1,
                "costume": COSTUME_VARIANTS[costume_key]["label"],
                "background": BACKGROUND_VARIANTS[bg_key]["label"],
                "weapon": WEAPON_VARIANTS[weapon_key]["label"],
                "composition": COMPOSITION_VARIANTS[composition_key]["label"],
                "angle": ANGLE_VARIANTS[angle_key]["label"],
                "expression": EXPRESSION_VARIANTS[expression_key]["label"],
                "action": ACTION_VARIANTS[action_key]["label"],
                "hand": HAND_VARIANTS[hand_key]["label"],
                "shot_distance": SHOT_DISTANCE_VARIANTS[shot_distance_key]["label"],
                "lighting": LIGHTING_VARIANTS[lighting_key]["label"],
            },
        }

    def preview_prompts(self) -> list[dict]:
        """预览所有 Prompt，不提交生成。

        Returns:
            list of {"positive": str, "negative": str, "meta": dict}
        """
        return [self._build_single_prompt(i) for i in range(self.total)]

    def generate_requests(self) -> list[GenerationRequest]:
        """生成一批 GenerationRequest，每批 batch_size 条 prompt。

        Returns:
            list[GenerationRequest] 每个 request 含 batch_prompts
        """
        all_prompts = self.preview_prompts()
        requests = []

        for batch_start in range(0, self.total, self.batch_size):
            batch_end = min(batch_start + self.batch_size, self.total)
            batch_prompts = all_prompts[batch_start:batch_end]

            model_name_map = {"zimage": ZIMAGE_MODEL, "flux": FLUX_MODEL}
            model_name = model_name_map.get(self.model_type, "")
            req = GenerationRequest(
                model_type=self.model_type,
                model_name=model_name,
                category=WorkflowType.CHARACTER,
                genre=self.genre,
                project_name=f"{self.identity['name']}_训练素材_{batch_start + 1}-{batch_end}",
                batch_prompts=[p["positive"] for p in batch_prompts],
                free_negative=NEGATIVE_TAGS,
            )
            req.apply_model_defaults()
            requests.append(req)

        return requests


def get_strategy_summary() -> dict:
    """获取训练策略摘要（供前端显示）。"""
    dims = get_all_dimensions()
    return {
        "identity_count": len(CHARACTER_LAYERS),
        "identity_names": list(CHARACTER_LAYERS.keys()),
        "dimensions": dims,
        "quality_tags": QUALITY_TAGS,
        "negative_tags": NEGATIVE_TAGS,
        "default_total": 150,
        "default_batch_size": 10,
        "recommended_total": {
            "identity_lora": "100-200张",
            "costume_lora": "30-80张/套",
            "weapon_lora": "20-50张/种",
        },
    }