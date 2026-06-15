# -*- coding: utf-8 -*-
"""Workflow JSON injection engine. Supports SDXL (CheckpointLoaderSimple), Flux (FluxStartSettings / Flux2 UNETLoader), and Z-Image (QwenImageStartSettings / modular V2).

Architecture selection: checkpoint -> model_type -> workflow
"""

import json, copy, random
from pathlib import Path
from config.settings import settings
from config.settings import (
    ZIMAGE_MODEL, ZIMAGE_TEXT_ENCODER, ZIMAGE_VAE, ZIMAGE_CLIP_TYPE,
    ZIMAGE_SAMPLER, ZIMAGE_SCHEDULER,
)

# ============================================================
# 模型架构识别
# ============================================================

def detect_model_type(checkpoint_name: str) -> str:
    """从底模文件名自动识别模型架构类型

    可扩展架构类型：
      sd3      - Stable Diffusion 3 / 3.5 系列
      wan      - Wan 视频/图像生成模型
      qwen_image - Qwen Image 系列（通义万相）
    """
    if not checkpoint_name:
        return "sdxl"
    name = checkpoint_name.lower()
    # Z-Image 系列（含 z_image、zimage、z-image 三种命名）
    if "z_image" in name or "zimage" in name or "z-image" in name:
        return "zimage"
    # Flux 系列（含 Klein 蒸馏版本）
    if "flux" in name or "klein" in name:
        return "flux"
    # TODO: 未来扩展
    # if "sd3" in name or "sd3_5" in name:
    #     return "sd3"
    # if "wan" in name:
    #     return "wan"
    # if "qwen_image" in name or "qwen-image" in name:
    #     return "qwen_image"
    return "sdxl"


# ============================================================
# 工作流映射 —— 架构优先，类别其次
# ============================================================

MODEL_WORKFLOW_MAP = {
    "sdxl": {
        "character": "character.json",
        "scene": "scene.json",
        "costume": "costume.json",
        "img2img": "img2img.json",
        "makeup": "makeup.json",
    },
    "flux": {
        "character": "flux_character.json",
        "scene": "flux2_base.json",
        "costume": "flux2_base.json",
    },
    "zimage": {
        "character": "zimage_character.json",
        "scene": "zimage_v2_scene.json",
        "costume": "zimage_v2_costume.json",
    },
}


def load_workflow_json(category: str, model_type: str = "sdxl") -> dict:
    """加载工作流 JSON，优先按模型架构选择文件

    选择链路：model_type -> 架构映射表 -> category -> workflow 文件
    """
    arch_map = MODEL_WORKFLOW_MAP.get(model_type, {})
    filename = arch_map.get(category)
    if not filename:
        filename = f"{category}.json"
    path = Path(settings.workflow_dir) / filename
    if not path.exists():
        raise FileNotFoundError(
            f"工作流文件不存在: {path} (model_type={model_type}, category={category})"
        )
    with open(path, "r", encoding="utf-8") as f:
        return copy.deepcopy(json.load(f))


def resolve_workflow(category: str, checkpoint: str) -> dict:
    """一步式解析工作流：底模 -> 架构 -> workflow

    任务提交链路的推荐入口，自动从 checkpoint 文件名推断架构。
    """
    model_type = detect_model_type(checkpoint)
    return load_workflow_json(category, model_type)

# SDXL node IDs
NODE_CHECKPOINT, NODE_POSITIVE, NODE_NEGATIVE = "4", "5", "6"
NODE_LATENT, NODE_SAMPLER, NODE_VAE_DECODE = "7", "8", "9"
NODE_SAVE, NODE_LOAD_IMAGE, NODE_ENCODE = "10", "11", "12"
NODE_VAE_LOADER, NODE_CLIP_LOADER, NODE_LORA_LOADER = "100", "101", "102"

# Z-Image node IDs (old QwenImageStartSettings architecture)
Z_SETTINGS, Z_SAMPLER, Z_VAE_DECODE, Z_SAVE = "1", "2", "3", "4"

# Z-Image V2 node IDs (modular: UNETLoader + CLIPLoader + VAELoader + ConditioningZeroOut)
ZV2_CLIP_TEXT = "57:27"       # CLIPTextEncode
ZV2_COND_ZERO = "57:33"       # ConditioningZeroOut (CFG-Zero)
ZV2_UNET = "57:28"            # UNETLoader
ZV2_VAE = "57:29"             # VAELoader
ZV2_CLIP = "57:30"            # CLIPLoader
ZV2_LATENT = "57:13"          # EmptySD3LatentImage
ZV2_AURAFLOW = "57:11"        # ModelSamplingAuraFlow
ZV2_KSAMPLER = "57:3"         # KSampler
ZV2_VAE_DECODE_NODE = "57:8"  # VAEDecode
ZV2_SAVE_NODE = "9"           # SaveImage

# Flux node IDs (FluxStartSettings + Fluxstarsampler)
F_START, F_SAMPLER, F_SAVE = "1", "2", "3"

# Flux 2 node IDs (UNETLoader + CLIPLoader + VAELoader + Flux2Scheduler + SamplerCustomAdvanced)
F2_UNET, F2_CLIP, F2_VAE = "75:70", "75:71", "75:72"
F2_POSITIVE, F2_NEGATIVE = "75:74", "75:67"
F2_WIDTH, F2_HEIGHT = "75:68", "75:69"
F2_LATENT, F2_NOISE = "75:66", "75:73"
F2_SCHEDULER, F2_GUIDER, F2_SAMPLER = "75:62", "75:63", "75:64"
F2_SAMPLER_SELECT = "75:61"
F2_SAVE = "9"


def inject_parameters(workflow, model_name, positive_prompt, negative_prompt,
                      seed, seed_mode, width, height, steps, cfg,
                      image_filename="", denoising_strength=1.0,
                      sampler_name="", scheduler="",
                      vae_name="", clip_name="", lora_name="", lora_strength=1.0,
                      model_type="sdxl"):
    # Auto-detect Flux 2 workflow (has UNETLoader + Flux2Scheduler)
    if F2_UNET in workflow:
        return _inject_flux2(workflow, model_name, positive_prompt, negative_prompt,
                             seed, seed_mode, width, height, steps, cfg,
                             sampler_name, scheduler)
    # Auto-detect Z-Image V2 (modular architecture with ConditioningZeroOut)
    if ZV2_CLIP_TEXT in workflow:
        return _inject_zimage_v2(workflow, model_name, positive_prompt, negative_prompt,
                                 seed, seed_mode, width, height, steps, cfg,
                                 sampler_name, scheduler,
                                 vae_name=vae_name, clip_name=clip_name)
    if model_type == "zimage":
        return _inject_zimage(workflow, model_name, positive_prompt, negative_prompt,
                              seed, seed_mode, width, height, steps, cfg,
                              sampler_name, scheduler)
    if model_type == "flux":
        return _inject_flux(workflow, model_name, positive_prompt,
                            seed, seed_mode, width, height, steps, cfg,
                            sampler_name, scheduler)
    return _inject_sdxl(workflow, model_name, positive_prompt, negative_prompt,
                         seed, seed_mode, width, height, steps, cfg,
                         image_filename, denoising_strength, sampler_name, scheduler,
                         vae_name, clip_name, lora_name, lora_strength)


def _inject_sdxl(workflow, model_name, positive_prompt, negative_prompt,
                 seed, seed_mode, width, height, steps, cfg,
                 image_filename, denoising_strength, sampler_name, scheduler,
                 vae_name, clip_name, lora_name, lora_strength) -> dict:
    if vae_name:
        _add_vae(workflow, vae_name)
    if clip_name:
        _add_clip(workflow, clip_name)
    if lora_name:
        _add_lora(workflow, lora_name, lora_strength)

    if NODE_CHECKPOINT in workflow:
        workflow[NODE_CHECKPOINT]["inputs"]["ckpt_name"] = model_name
    if NODE_POSITIVE in workflow:
        workflow[NODE_POSITIVE]["inputs"]["text"] = positive_prompt
    if NODE_NEGATIVE in workflow:
        workflow[NODE_NEGATIVE]["inputs"]["text"] = negative_prompt
    if NODE_LATENT in workflow:
        workflow[NODE_LATENT]["inputs"]["width"] = width
        workflow[NODE_LATENT]["inputs"]["height"] = height

    final_seed = seed
    if NODE_SAMPLER in workflow:
        final_seed = seed if seed_mode == "fixed" else random.randint(0, 2**32 - 1)
        k = workflow[NODE_SAMPLER]["inputs"]
        k["seed"] = final_seed
        k["steps"] = steps
        k["cfg"] = cfg
        if "denoise" in k:
            k["denoise"] = denoising_strength
        if sampler_name:
            k["sampler_name"] = sampler_name
        if scheduler:
            k["scheduler"] = scheduler

    if NODE_LOAD_IMAGE in workflow and image_filename:
        workflow[NODE_LOAD_IMAGE]["inputs"]["image"] = image_filename
    return workflow


def _inject_zimage(workflow, model_name, positive_prompt, negative_prompt,
                   seed, seed_mode, width, height, steps, cfg,
                   sampler_name, scheduler) -> dict:
    final_seed = seed
    if Z_SETTINGS not in workflow:
        return workflow, final_seed
    s = workflow[Z_SETTINGS]["inputs"]
    s["Positive_Prompt"] = positive_prompt
    s["Negative_Prompt"] = negative_prompt
    s["Diffusion_Model"] = model_name
    s["CLIP"] = ZIMAGE_TEXT_ENCODER
    s["VAE"] = ZIMAGE_VAE
    s["CLIP_Type"] = ZIMAGE_CLIP_TYPE
    s["Latent_Width"] = width
    s["Latent_Height"] = height

    if Z_SAMPLER in workflow:
        final_seed = seed if seed_mode == "fixed" else random.randint(0, 2**32 - 1)
        k = workflow[Z_SAMPLER]["inputs"]
        k["seed"] = final_seed
        k["steps"] = steps
        k["cfg"] = cfg
        k["sampler_name"] = sampler_name or ZIMAGE_SAMPLER
        k["scheduler"] = scheduler or ZIMAGE_SCHEDULER
    return workflow, final_seed


def _inject_flux(workflow, model_name, positive_prompt,
                 seed, seed_mode, width, height, steps, cfg,
                 sampler_name, scheduler) -> dict:
    """Inject parameters into Flux workflow (FluxStartSettings + Fluxstarsampler).
    Flux uses single conditioning (no negative prompt)."""
    # Node 1: FluxStartSettings
    if F_START in workflow:
        s = workflow[F_START]["inputs"]
        s["text"] = positive_prompt
        s["UNET"] = model_name
        s["Latent_Width"] = width
        s["Latent_Height"] = height

    # Node 2: Fluxstarsampler
    final_seed = seed
    if F_SAMPLER in workflow:
        final_seed = seed if seed_mode == "fixed" else random.randint(0, 2**32 - 1)
        k = workflow[F_SAMPLER]["inputs"]
        k["seed"] = final_seed
        k["steps"] = str(steps)
        k["guidance"] = str(cfg)
        if sampler_name:
            k["sampler"] = sampler_name
        if scheduler:
            k["scheduler"] = scheduler

    return workflow, final_seed


def _inject_flux2(workflow, model_name, positive_prompt, negative_prompt,
                   seed, seed_mode, width, height, steps, cfg,
                   sampler_name, scheduler) -> dict:
    """Inject parameters into Flux 2 workflow (UNETLoader + CLIPLoader + Flux2Scheduler + SamplerCustomAdvanced)."""
    if F2_UNET in workflow:
        workflow[F2_UNET]["inputs"]["unet_name"] = model_name
    if F2_POSITIVE in workflow:
        workflow[F2_POSITIVE]["inputs"]["text"] = positive_prompt
    if F2_NEGATIVE in workflow:
        workflow[F2_NEGATIVE]["inputs"]["text"] = negative_prompt
    if F2_WIDTH in workflow:
        workflow[F2_WIDTH]["inputs"]["value"] = width
    if F2_HEIGHT in workflow:
        workflow[F2_HEIGHT]["inputs"]["value"] = height
    if F2_SCHEDULER in workflow:
        workflow[F2_SCHEDULER]["inputs"]["steps"] = steps
    if F2_GUIDER in workflow:
        workflow[F2_GUIDER]["inputs"]["cfg"] = cfg
    final_seed = seed
    if F2_NOISE in workflow:
        final_seed = seed if seed_mode == "fixed" else random.randint(0, 2**32 - 1)
        workflow[F2_NOISE]["inputs"]["noise_seed"] = final_seed
    return workflow, final_seed

def _inject_zimage_v2(workflow, model_name, positive_prompt, negative_prompt,
                      seed, seed_mode, width, height, steps, cfg,
                      sampler_name, scheduler,
                      vae_name="", clip_name="") -> dict:
    # Inject params into Z-Image V2 modular workflow.
    # UNETLoader: model filename
    if ZV2_UNET in workflow:
        workflow[ZV2_UNET]["inputs"]["unet_name"] = model_name
    # VAELoader: VAE filename
    if vae_name and ZV2_VAE in workflow:
        workflow[ZV2_VAE]["inputs"]["vae_name"] = vae_name
    # CLIPLoader: CLIP filename and type
    if clip_name and ZV2_CLIP in workflow:
        workflow[ZV2_CLIP]["inputs"]["clip_name"] = clip_name
    # CLIPTextEncode: positive prompt
    if ZV2_CLIP_TEXT in workflow:
        workflow[ZV2_CLIP_TEXT]["inputs"]["text"] = positive_prompt
    # ConditioningZeroOut: negative is always zeroed (CFG-Zero strategy)
    # EmptySD3LatentImage: width/height
    if ZV2_LATENT in workflow:
        workflow[ZV2_LATENT]["inputs"]["width"] = width
        workflow[ZV2_LATENT]["inputs"]["height"] = height
    # KSampler: seed, steps, cfg, sampler, scheduler
    final_seed = seed
    if ZV2_KSAMPLER in workflow:
        final_seed = seed if seed_mode == "fixed" else random.randint(0, 2**32 - 1)
        k = workflow[ZV2_KSAMPLER]["inputs"]
        k["seed"] = final_seed
        k["steps"] = steps
        k["cfg"] = cfg
        if sampler_name:
            k["sampler_name"] = sampler_name
        if scheduler:
            k["scheduler"] = scheduler
    return workflow, final_seed


def _add_vae(workflow, vae_name):
    if NODE_VAE_DECODE not in workflow or NODE_CHECKPOINT not in workflow:
        return
    workflow[NODE_VAE_LOADER] = {"inputs": {"vae_name": vae_name}, "class_type": "VAELoader", "_meta": {"title": "VAE"}}
    workflow[NODE_VAE_DECODE]["inputs"]["vae"] = [NODE_VAE_LOADER, 0]

def _add_clip(workflow, clip_name):
    if NODE_CHECKPOINT not in workflow:
        return
    workflow[NODE_CLIP_LOADER] = {"inputs": {"clip_name": clip_name, "type": "stable_diffusion"}, "class_type": "CLIPLoader", "_meta": {"title": "CLIP"}}
    for nid in (NODE_POSITIVE, NODE_NEGATIVE):
        if nid in workflow and "clip" in workflow[nid].get("inputs", {}):
            workflow[nid]["inputs"]["clip"] = [NODE_CLIP_LOADER, 0]

def _add_lora(workflow, lora_name, lora_strength=1.0):
    if NODE_SAMPLER not in workflow or NODE_CHECKPOINT not in workflow:
        return
    workflow[NODE_LORA_LOADER] = {"inputs": {"lora_name": lora_name, "strength_model": lora_strength, "strength_clip": lora_strength, "model": [NODE_CHECKPOINT, 0], "clip": [NODE_CHECKPOINT, 1]}, "class_type": "LoraLoader", "_meta": {"title": "LoRA"}}
    workflow[NODE_SAMPLER]["inputs"]["model"] = [NODE_LORA_LOADER, 0]
    for nid in (NODE_POSITIVE, NODE_NEGATIVE):
        if nid in workflow and "clip" in workflow[nid].get("inputs", {}):
            workflow[nid]["inputs"]["clip"] = [NODE_LORA_LOADER, 1]
