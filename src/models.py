# -*- coding: utf-8 -*-
"""Pydantic 数据模型定义"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from config.settings import (DEFAULT_STEPS, DEFAULT_CFG, DEFAULT_WIDTH, DEFAULT_HEIGHT, ZIMAGE_STEPS, ZIMAGE_CFG, ZIMAGE_WIDTH, ZIMAGE_HEIGHT, ZIMAGE_SAMPLER, ZIMAGE_SCHEDULER, FLUX_STEPS, FLUX_CFG, FLUX_WIDTH, FLUX_HEIGHT, FLUX_SAMPLER, FLUX_SCHEDULER, ZIMAGE_CANDIDATE_COUNT, FLUX_CANDIDATE_COUNT)


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowType(str, Enum):
    """工作流类型"""
    CHARACTER = "character"
    SCENE = "scene"
    COSTUME = "costume"
    IMG2IMG = "img2img"


class GenreType(str, Enum):
    """题材类型"""
    XIANXIA = "xianxia"
    URBAN = "urban"
    TRANSMIGRATION = "transmigration"
    HISTORICAL = "historical"
    MODERN_ERA = "modern_era"
    SUPERNATURAL = "supernatural"
    SCI_FI = "sci_fi"
    ESPORTS = "esports"


# 题材中文名映射
GENRE_LABELS = {
    GenreType.XIANXIA: "玄幻修仙",
    GenreType.URBAN: "都市爱情",
    GenreType.TRANSMIGRATION: "穿越重生",
    GenreType.HISTORICAL: "古代历史",
    GenreType.MODERN_ERA: "近现代",
    GenreType.SUPERNATURAL: "悬疑灵异",
    GenreType.SCI_FI: "末世科幻",
    GenreType.ESPORTS: "游戏电竞",
}


class GenerationRequest(BaseModel):
    """前端提交的生成请求"""
    model_type: str = Field(default="sdxl", description="sdxl / zimage / flux")
    category: WorkflowType = Field(..., description="生成类型: character/scene/costume/img2img")
    genre: GenreType = Field(..., description="题材")
    project_name: str = Field(..., min_length=1, description="项目名称")

    # 角色参数
    role_name: Optional[str] = Field(None, description="角色名")
    character_gender: str = Field(default="female", description="角色性别/类型: female/male/elder_male/elder_female/young_female/young_male/monster/mythical_beast")
    angles: list[str] = Field(default_factory=lambda: ["front_view"], description="角度列表")
    expressions: list[str] = Field(default_factory=lambda: ["neutral"], description="表情列表")

    # 场景参数
    scene_type: Optional[str] = Field(None, description="场景类型")
    time_of_day: Optional[str] = Field(None, description="时间")
    atmosphere: Optional[str] = Field(None, description="氛围")

    # 服装道具参数
    item_type: Optional[str] = Field(None, description="物品类型")
    material: Optional[str] = Field(None, description="材质")
    item_style: Optional[str] = Field(None, description="风格")

    # 光照参数
    lighting: str = Field(default="natural_light", description="光照类型")

    # 构图参数
    composition: str = Field(default="full_body", description="构图: half_body/full_body/portrait/close_up")

    # 三视图模式
    character_sheet_mode: bool = Field(default=False, description="是否生成角色三视图")

    # 风格标签（用户从风格库中多选的标签）
    style_tags: str = Field(default="", description="用户选中的风格标签，逗号分隔")

    # 自由提示词
    free_positive: str = Field(default="", description="自定义正向提示词")
    free_negative: str = Field(default="", description="自定义负向提示词")

    # img2img 参数
    image_filename: str = Field(default="", description="上传的图片文件名（在 ComfyUI input 目录）")
    img2img_prompt: str = Field(default="", description="img2img 用户期望输出描述")
    denoising_strength: float = Field(default=0.4, ge=0.0, le=1.0, description="img2img 降噪强度")

    # 采样器参数
    sampler_name: str = Field(default="", description="采样器名称，空则用模板默认")
    scheduler: str = Field(default="", description="调度器名称，空则用模板默认")

    # 生成参数
    seed_mode: str = Field(default="random", description="种子模式: random/fixed")
    seed: int = Field(default=0, description="固定种子值")
    candidate_count: int = Field(default=0, ge=0, le=16, description="Candidate images per shot (0=use model default)")
    model_name: str = Field(default="", description="底模文件名，空则由后端自动选择第一个可用模型")
    width: int = Field(default=DEFAULT_WIDTH, ge=64, le=4096, description="宽度")
    height: int = Field(default=DEFAULT_HEIGHT, ge=64, le=4096, description="高度")
    steps: int = Field(default=DEFAULT_STEPS, ge=1, le=100, description="采样步数")
    cfg: float = Field(default=DEFAULT_CFG, ge=1.0, le=30.0, description="CFG Scale")
    batch_count: int = Field(default=1, ge=1, le=4, description="每张图出图数")


    # ???????
    batch_prompts: list[str] = Field(default_factory=list, description="?????????????????????")

    def apply_model_defaults(self):
        """Apply model-specific defaults (SDXL, Z-Image or Flux)"""
        if self.model_type == "sdxl" or not self.model_type:
            # SDXL defaults: higher steps, proper sampler for quality
            if self.steps <= 28:
                object.__setattr__(self, "steps", 40)
            if not self.sampler_name:
                object.__setattr__(self, "sampler_name", "dpmpp_2m")
            if not self.scheduler:
                object.__setattr__(self, "scheduler", "karras")
        elif self.model_type == "zimage":
            if self.candidate_count <= 0:
                object.__setattr__(self, "candidate_count", ZIMAGE_CANDIDATE_COUNT)
            if self.steps == DEFAULT_STEPS:
                object.__setattr__(self, "steps", ZIMAGE_STEPS)
            if self.cfg == DEFAULT_CFG:
                object.__setattr__(self, "cfg", ZIMAGE_CFG)
            if self.width <= DEFAULT_WIDTH:
                object.__setattr__(self, "width", ZIMAGE_WIDTH)
            if self.height <= DEFAULT_HEIGHT:
                object.__setattr__(self, "height", ZIMAGE_HEIGHT)
            if not self.sampler_name:
                object.__setattr__(self, "sampler_name", ZIMAGE_SAMPLER)
            if not self.scheduler:
                object.__setattr__(self, "scheduler", ZIMAGE_SCHEDULER)
        elif self.model_type == "flux":
            if self.candidate_count <= 0:
                object.__setattr__(self, "candidate_count", FLUX_CANDIDATE_COUNT)
            if self.steps == DEFAULT_STEPS:
                object.__setattr__(self, "steps", FLUX_STEPS)
            if self.cfg == DEFAULT_CFG:
                object.__setattr__(self, "cfg", FLUX_CFG)
            if self.width <= DEFAULT_WIDTH:
                object.__setattr__(self, "width", FLUX_WIDTH)
            if self.height <= DEFAULT_HEIGHT:
                object.__setattr__(self, "height", FLUX_HEIGHT)
            if not self.sampler_name:
                object.__setattr__(self, "sampler_name", FLUX_SAMPLER)
            if not self.scheduler:
                object.__setattr__(self, "scheduler", FLUX_SCHEDULER)

class SubTaskInfo(BaseModel):
    """子任务信息"""
    subtask_id: str
    task_id: str
    prompt_positive: str
    prompt_negative: str
    filename: str
    status: TaskStatus = TaskStatus.PENDING
    comfyui_prompt_id: Optional[str] = None
    image_path: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    vae_name: str = ""
    clip_name: str = ""
    lora_name: str = ""
    lora_strength: float = 1.0


class GenerationTask(BaseModel):
    """生成任务"""
    task_id: str
    category: WorkflowType
    genre: GenreType
    project_name: str
    status: TaskStatus = TaskStatus.PENDING
    total_subtasks: int = 0
    completed_subtasks: int = 0
    request: GenerationRequest
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: list[GenerationTask]
    total: int


# ============================================================
# Prompt 工作室数据模型
# ============================================================

class PromptPolishRequest(BaseModel):
    """阶段① 润色请求"""
    idea: str = Field(..., min_length=1, max_length=500, description="用户粗糙中文描述")


class PromptPolishResult(BaseModel):
    """阶段① 润色结果"""
    original: str = Field(..., description="原始粗糙输入")
    polished: str = Field(..., description="润色后的标准中文")


class PromptConvertRequest(BaseModel):
    """阶段② 转换请求"""
    chinese_prompt: str = Field(..., min_length=1, description="标准中文描述")


class PromptConvertResult(BaseModel):
    """阶段② 转换结果"""
    chinese_prompt: str = Field(..., description="输入的标准中文")
    positive: str = Field(..., description="ComfyUI 英文正向标签")
    negative: str = Field(..., description="ComfyUI 英文负向标签")
    params: dict = Field(..., description="生成参数 {width, height, steps, cfg}")
    raw_response: str = Field(default="", description="Qwen 原始输出 (调试用)")


class PromptGenerateRequest(BaseModel):
    """一键生成请求"""
    positive: str = Field(..., min_length=1, description="英文正向 Prompt")
    negative: str = Field(default="", description="英文负向 Prompt")
    params: dict = Field(default_factory=dict, description="生成参数")
    workflow_type: str = Field(default="character", description="工作流类型: character/costume/scene/img2img")


# ============================================================
# 角色卡片：身份 + 装扮拆分
# ============================================================

class CharacterIdentity(BaseModel):
    """身份层 — 锁定不变"""
    name: str = Field(..., description="角色名")
    gender: str = Field(default="female", description="性别: female/male")
    age_range: str = Field(default="青年", description="年龄段")
    face_desc: str = Field(default="", description="面部特征描述")
    body_type: str = Field(default="", description="体型描述")
    temperament: str = Field(default="", description="气质描述")


class CostumeOverlay(BaseModel):
    """装扮层 — 可随意修改"""
    name: str = Field(default="默认装扮", description="装扮名称")
    outfit: str = Field(default="", description="服装描述")
    accessories: str = Field(default="", description="配饰")
    hairstyle: str = Field(default="", description="发型")
    makeup: str = Field(default="", description="妆容")
    props: str = Field(default="", description="道具")
    scene_hint: str = Field(default="", description="场景暗示")


class CostumeActivateRequest(BaseModel):
    """激活装扮请求"""
    index: int = Field(..., ge=0, description="装扮库中的索引位置")


class CardOverlayUpdate(BaseModel):
    """卡片装扮更新请求"""
    costume: Optional[CostumeOverlay] = Field(None, description="更新后的装扮")
