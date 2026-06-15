# -*- coding: utf-8 -*-
"""项目配置管理，支持 .env 环境变量覆盖"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """全局配置类"""

    comfyui_base_url: str = "http://192.168.1.88:8188"
    output_dir: str = "./output"
    db_path: str = "./data/tasks.db"
    workflow_dir: str = "./workflows"
    max_concurrent_tasks: int = 2
    poll_interval: float = 2.0
    poll_timeout: int = 600

    # Qwen 本地模型 (vLLM + LiteLLM)
    qwen_base_url: str = "http://192.168.1.222:3688/v1"
    qwen_api_key: str = ""
    qwen_model: str = "qwen3.6-35b-a3b-nvfp4"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# ============================================================
# 底模配置（从 character_tuning 迁移）
# ============================================================

# SDXL 默认参数
DEFAULT_SAMPLER = "dpmpp_2m"
DEFAULT_SCHEDULER = "karras"
DEFAULT_STEPS = 30
DEFAULT_CFG = 5.5
DEFAULT_WIDTH = 1024
DEFAULT_HEIGHT = 1536

# Z-Image 模型配置
ZIMAGE_MODEL = "z_image_turbo_bf16.safetensors"
ZIMAGE_TEXT_ENCODER = "qwen_3_4b.safetensors"
ZIMAGE_VAE = "ae.safetensors"
ZIMAGE_CLIP_TYPE = "lumina2"
ZIMAGE_SAMPLER = "euler"
ZIMAGE_SCHEDULER = "simple"
ZIMAGE_STEPS = 6
ZIMAGE_CFG = 2.0
ZIMAGE_WIDTH = 1328
ZIMAGE_HEIGHT = 1328
ZIMAGE_CANDIDATE_COUNT = 1

ZIMAGE_SIZE_TIERS = {
    "small":  (1280, 704),
    "medium": (1344, 768),
    "large":  (1536, 864),
}

# Flux 2 Klein 模型配置
FLUX_CANDIDATE_COUNT = 1
FLUX_MODEL = "flux-2-klein-base-9b-fp8.safetensors"
FLUX_SAMPLER = "euler"
FLUX_SCHEDULER = "simple"
FLUX_STEPS = 25
FLUX_CFG = 3.5
FLUX_WIDTH = 1024
FLUX_HEIGHT = 1536

# 通用 Negative Prompt
NEGATIVE_PROMPT = (
    "worst quality, "
    "low quality, "
    "blurry, "
    "bad anatomy, "
    "bad hands, "
    "extra fingers, "
    "missing fingers, "
    "deformed face, "
    "text, "
    "watermark, "
    "logo"
)
