# -*- coding: utf-8 -*-
"""服道化素材工作室 - 统一生成引擎

支持服装/道具/妆容三类 LoRA 训练素材的 prompt 生成与任务提交
包含预览图、批量生成、重新预览功能
"""

import random
import uuid
from typing import Optional, List, Dict

from src.fudaohua_presets import (
    COSTUME_PRESETS, PROP_PRESETS, MAKEUP_PRESETS,
    CHARACTER_POOL, HAIRSTYLE_POOL, MAKEUP_POOL,
    PROP_POOL, BACKGROUND_POOL, ANGLE_POOL, ACTION_POOL,
    LIGHTING_POOL, QUALITY_TAG, NEGATIVE_PROMPT, BASE_MODELS,
    COSTUME_TEMPLATE, PROP_TEMPLATE, MAKEUP_TEMPLATE,
    HAND_POSITION_POOL, FACE_SHAPE_POOL, EXPRESSION_POOL, CLOTHING_POOL,
    get_costume, get_prop, get_makeup,
)
from src.models import GenerationRequest, WorkflowType, GenreType


PRESET_MAP = {
    "costume": (COSTUME_PRESETS, get_costume, COSTUME_TEMPLATE),
    "prop": (PROP_PRESETS, get_prop, PROP_TEMPLATE),
    "makeup": (MAKEUP_PRESETS, get_makeup, MAKEUP_TEMPLATE),
}


class FudaohuaEngine:
    """服道化素材生成引擎

    负责：构建随机 prompt → 预览单图 → 批量提交 ComfyUI 任务
    """

    def __init__(
        self,
        preset_type: str,
        preset_id: str = "",
        total: int = 200,
        batch_size: int = 10,
        base_model: str = "flux2_klein_9b",
        seed: Optional[int] = None,
        positive_template: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        request_title: str = "",
    ):
        if preset_type not in PRESET_MAP:
            raise ValueError(f"不支持的类型: {preset_type}，可选: costume/prop/makeup")

        self.preset_type = preset_type
        presets, getter, default_template = PRESET_MAP[preset_type]
        self.presets = presets

        # raw_template 模式：直接使用用户输入的正反提示词
        if positive_template and positive_template.strip():
            self._raw_mode = True
            self.preset_id = "__template__"
            self.preset = {
                "id": "__template__",
                "name_cn": request_title or "自定义模板",
                "core_tags": positive_template.strip(),
            }
            self._neg = (negative_prompt or "").strip() or NEGATIVE_PROMPT
            self.positive_template = "{core_tags}"
        else:
            # 兼容旧预设模式
            self._raw_mode = False
            self.preset_id = preset_id
            self.preset = getter(preset_id)
            if not self.preset:
                raise ValueError(f"预设不存在: {preset_id}")
            self._neg = negative_prompt.strip() if negative_prompt and negative_prompt.strip() else NEGATIVE_PROMPT
            self.positive_template = positive_template or default_template

        self.total = total
        self.batch_size = batch_size
        self.rng = random.Random(seed) if seed is not None else random.Random()

        # 匹配底模配置
        model = BASE_MODELS[0]
        for m in BASE_MODELS:
            if m["key"] == base_model:
                model = m
                break
        self.model_type = model["type"]
        self.width = model["width"]
        self.height = model["height"]
        self.checkpoint = model.get("checkpoint", "")
        self.base_model_key = base_model

        # 任务跟踪
        self._task_ids: List[str] = []
        self._task_group_id: str = uuid.uuid4().hex[:12]

    def _pick(self, pool: list) -> str:
        """从池中随机选择一个元素"""
        return self.rng.choice(pool)

    def _build_costume_prompt(self, index: int) -> dict:
        """构建服装训练 prompt"""
        if self._raw_mode:
            return {
                "positive": self.preset["core_tags"],
                "negative": self._neg,
                "meta": {"index": index + 1, "preset_name": self.preset["name_cn"], "preset_type": self.preset_type},
            }
        character = self._pick(CHARACTER_POOL)
        hairstyle = self._pick(HAIRSTYLE_POOL)
        makeup = self._pick(MAKEUP_POOL)
        prop = self._pick(PROP_POOL)
        background = self._pick(BACKGROUND_POOL)
        angle = self._pick(ANGLE_POOL)
        action = self._pick(ACTION_POOL)
        lighting = self._pick(LIGHTING_POOL)

        positive = self.positive_template.format(
            core_tags=self.preset["core_tags"],
            character=character,
            hairstyle=hairstyle,
            makeup=makeup,
            prop=prop,
            background=background,
            angle=angle,
            action=action,
            lighting=lighting,
            quality=QUALITY_TAG,
        )

        return {
            "positive": positive,
            "negative": self._neg,
            "meta": {
                "index": index + 1,
                "preset_name": self.preset["name_cn"],
                "preset_type": self.preset_type,
                "character": character,
                "hairstyle": hairstyle,
                "makeup": makeup,
                "prop": prop,
                "background": background,
                "angle": angle,
                "action": action,
            },
        }

    def _build_prop_prompt(self, index: int) -> dict:
        """构建道具训练 prompt"""
        if self._raw_mode:
            return {
                "positive": self.preset["core_tags"],
                "negative": self._neg,
                "meta": {"index": index + 1, "preset_name": self.preset["name_cn"], "preset_type": self.preset_type},
            }
        character = self._pick(CHARACTER_POOL)
        hairstyle = self._pick(HAIRSTYLE_POOL)
        hand_position = self._pick(HAND_POSITION_POOL)
        background = self._pick(BACKGROUND_POOL)
        angle = self._pick(ANGLE_POOL)
        lighting = self._pick(LIGHTING_POOL)

        positive = self.positive_template.format(
            core_tags=self.preset["core_tags"],
            character=character,
            hairstyle=hairstyle,
            hand_position=hand_position,
            background=background,
            angle=angle,
            lighting=lighting,
            quality=QUALITY_TAG,
        )

        return {
            "positive": positive,
            "negative": self._neg,
            "meta": {
                "index": index + 1,
                "preset_name": self.preset["name_cn"],
                "preset_type": self.preset_type,
                "character": character,
                "hairstyle": hairstyle,
                "hand_position": hand_position,
                "background": background,
                "angle": angle,
            },
        }

    def _build_makeup_prompt(self, index: int) -> dict:
        """构建妆容训练 prompt"""
        if self._raw_mode:
            return {
                "positive": self.preset["core_tags"],
                "negative": self._neg,
                "meta": {"index": index + 1, "preset_name": self.preset["name_cn"], "preset_type": self.preset_type},
            }
        character = self._pick(CHARACTER_POOL)
        face_shape = self._pick(FACE_SHAPE_POOL)
        hairstyle = self._pick(HAIRSTYLE_POOL)
        clothing = self._pick(CLOTHING_POOL)
        expression = self._pick(EXPRESSION_POOL)
        background = self._pick(BACKGROUND_POOL)
        lighting = self._pick(LIGHTING_POOL)

        positive = self.positive_template.format(
            core_tags=self.preset["core_tags"],
            character=character,
            face_shape=face_shape,
            hairstyle=hairstyle,
            clothing=clothing,
            expression=expression,
            background=background,
            lighting=lighting,
            quality=QUALITY_TAG,
        )

        return {
            "positive": positive,
            "negative": self._neg,
            "meta": {
                "index": index + 1,
                "preset_name": self.preset["name_cn"],
                "preset_type": self.preset_type,
                "character": character,
                "face_shape": face_shape,
                "hairstyle": hairstyle,
                "clothing": clothing,
                "expression": expression,
                "background": background,
            },
        }

    def _build_single_prompt(self, index: int) -> dict:
        """根据类型分发到正确的 prompt 构建器"""
        if self.preset_type == "costume":
            return self._build_costume_prompt(index)
        elif self.preset_type == "prop":
            return self._build_prop_prompt(index)
        elif self.preset_type == "makeup":
            return self._build_makeup_prompt(index)

    # ===== 公开 API =====

    def build_prompts(self, count: Optional[int] = None) -> List[dict]:
        """构建全部 prompt 列表（含 meta）"""
        n = count or self.total
        return [self._build_single_prompt(i) for i in range(n)]

    def build_preview_prompt(self) -> dict:
        """构建 1 张预览图的 prompt"""
        return self._build_single_prompt(0)

    def build_preview_prompts_text(self) -> List[str]:
        """构建预览用的纯文本 prompt 列表（用于 Prompt 预览面板）"""
        preview_count = min(self.total, 50)
        prompts = self.build_prompts(preview_count)
        return [p["positive"] for p in prompts]

    def build_generation_requests(self) -> List[GenerationRequest]:
        """构建批量生成请求列表（分批次）"""
        all_prompts = self.build_prompts()
        requests = []
        for start in range(0, self.total, self.batch_size):
            end = min(start + self.batch_size, self.total)
            batch = all_prompts[start:end]
            req = GenerationRequest(
                category=WorkflowType.COSTUME,
                genre=GenreType.XIANXIA,
                project_name=f"{self.preset["name_cn"]}_训练素材_{start + 1}-{end}",
                batch_prompts=[p["positive"] for p in batch],
                free_negative=self._neg,
                model_type=self.model_type,
                model_name=self.checkpoint,
                width=self.width,
                height=self.height,
            )
            req.apply_model_defaults()
            requests.append(req)
        return requests

    def build_preview_request(self) -> GenerationRequest:
        """构建预览图生成请求（1 张）"""
        prompt = self.build_preview_prompt()
        req = GenerationRequest(
            category=WorkflowType.COSTUME,
            genre=GenreType.XIANXIA,
            project_name=f"{self.preset["name_cn"]}_预览图",
            batch_prompts=[prompt["positive"]],
            free_negative=self._neg,
            model_type=self.model_type,
            model_name=self.checkpoint,
            width=self.width,
            height=self.height,
        )
        req.apply_model_defaults()
        return req
