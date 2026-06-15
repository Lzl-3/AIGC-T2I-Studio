# -*- coding: utf-8 -*-
"""Prompt builder - 直接从角色预设置构建 Prompt，不使用额外风格层。"""

from src.models import GenerationRequest
from src.character_presets import (
    GENDER_TAGS, GENRE_ENVIRONMENT_TAGS, DEFAULT_CHARACTER_FALLBACKS,
)
from typing import Optional
from config.settings import NEGATIVE_PROMPT
from src.character_generator import build_character_prompts



# ============================================================
# 本地常量（不含风格注入，仅质量增强）
# ============================================================

QUALITY_TAGS = (
    "masterpiece, best quality, highly detailed, sharp focus"
)

WEAPON_QUALITY_TAGS = (
    "detailed weapon, sharp focus on weapon, weapon clearly visible, "
    "intricate weapon design, high quality weapon rendering, polished weapon, "
    "PBR metal, physically based rendering"
)

WEAPON_NEGATIVE_TAGS = (
    "blurry weapon, distorted weapon, broken weapon, low quality weapon, "
    "poorly drawn weapon, deformed weapon"
)

CHARACTER_SHEET_TAGS = (
    "character turnaround sheet, multiple views, reference sheet, "
    "front view, side view, back view, three views, "
    "standing pose, neutral expression, white background, "
    "full body, same character, consistent design, consistent lighting"
)


def build_prompts_for_request(request: GenerationRequest) -> list[dict]:
    """Build all subtask prompts from a generation request."""
    subtasks = []

    if request.category.value == "character":
        subtasks = _build_character_subtasks(request)
    elif request.category.value == "scene":
        subtasks = _build_scene_subtasks(request)
    elif request.category.value == "costume":
        subtasks = _build_costume_subtasks(request)
    elif request.category.value == "img2img":
        subtasks = _build_img2img_subtasks(request)

    # Inject user style tags if provided
    style_tags = getattr(request, "style_tags", "") or ""
    style_tags = style_tags.strip()

    is_single_char = request.category.value == "character"

    if isinstance(subtasks, list):
        for s in subtasks:
            if style_tags:
                s["positive"] = style_tags + ", " + s["positive"]
            s["positive"] = _apply_safety_injections(s["positive"], is_single_char)
    elif isinstance(subtasks, dict) and subtasks.get("type") == "character":
        for p in subtasks["prompts"]:
            if style_tags:
                p["positive"] = style_tags + ", " + p["positive"]
            p["positive"] = _apply_safety_injections(p["positive"], is_single_char)

    return subtasks


# ============================================================
# Character
# ============================================================

def _build_character_subtasks(request: GenerationRequest):
    """Build character prompt expansion metadata.

    Delegates to character_generator module for prompt assembly.
    Character generation uses fixed identity + face + hair + costume + expression only.
    Completely independent from training material module.
    """
    # Free prompt mode
    if request.free_positive:
        genre_label = _get_genre_label(request.genre.value)
        return _build_free_prompt_subtasks(request, genre_label, "character")

    # Delegate to dedicated character generator
    return build_character_prompts(request)


# ============================================================
# Scene
# ============================================================

def _build_scene_subtasks(request: GenerationRequest):
    """Build scene prompts."""
    scene_type = getattr(request, "scene_type", "") or ""
    time_of_day = getattr(request, "time_of_day", "") or ""
    atmosphere = getattr(request, "atmosphere", "") or ""
    project = request.project_name or "scene"

    positive = f"{scene_type}, {time_of_day}, {atmosphere}, {QUALITY_TAGS}"
    positive = positive.strip(", ")
    negative = NEGATIVE_PROMPT

    return [{"positive": positive, "negative": negative, "filename": project}]


# ============================================================
# Costume
# ============================================================

def _build_costume_subtasks(request: GenerationRequest):
    """Build costume prompts."""
    item_type = getattr(request, "item_type", "") or ""
    material = getattr(request, "material", "") or ""
    item_style = getattr(request, "item_style", "") or ""
    project = request.project_name or "costume"

    positive = f"{item_type}, {material}, {item_style}, {QUALITY_TAGS}"
    positive = positive.strip(", ")
    negative = NEGATIVE_PROMPT

    return [{"positive": positive, "negative": negative, "filename": project}]


# ============================================================
# Img2Img
# ============================================================

def _build_img2img_subtasks(request: GenerationRequest):
    """Build img2img prompts."""
    project = request.project_name or "img2img"
    user_prompt = (request.img2img_prompt or "").strip()
    positive = (user_prompt + ", " + QUALITY_TAGS) if user_prompt else QUALITY_TAGS
    negative = NEGATIVE_PROMPT
    return [{"positive": positive, "negative": negative, "filename": project}]


# ============================================================
# Free prompt
# ============================================================

def _build_free_prompt_subtasks(request: GenerationRequest, genre_label: str, category: str):
    """Build subtasks for free prompt mode."""
    positive = request.free_positive or ""
    negative = request.free_negative or NEGATIVE_PROMPT
    filename = f"{genre_label}_{request.project_name or 'free'}"
    return [{"positive": positive, "negative": negative, "filename": filename}]


# ============================================================
# Safety injections
# ============================================================

ANATOMY_LOCK = (
    "perfect anatomy, anatomically correct, "
    "five fingers on each hand, proportional limbs, natural body proportions"
)

FULL_BODY_KEYWORDS = [
    "full body", "full-body", "全身", "head to toe",
]

UPPER_BODY_COMPOSITION = (
    "upper body framing, hands clearly visible, "
    "upper chest and head in frame, medium shot"
)

HAND_ACTION_KEYWORDS = [
    "holding", "wielding", "carrying", "手握", "手持",
]

PROP_KEYWORDS = [
    "sword", "blade", "weapon", "gun", "staff", "wand", "book",
    "orb", "fan", "umbrella", "umbrella", "dagger", "spear",
]


def _has_hand_action(prompt_text: str) -> bool:
    text_lower = prompt_text.lower()
    return any(kw in text_lower for kw in HAND_ACTION_KEYWORDS)


def _has_prop(prompt_text: str) -> bool:
    text_lower = prompt_text.lower()
    return any(kw in text_lower for kw in PROP_KEYWORDS)


def _has_full_body(prompt_text: str) -> bool:
    text_lower = prompt_text.lower()
    return any(kw in text_lower for kw in FULL_BODY_KEYWORDS)


def _apply_composition_override(positive: str) -> str:
    if _has_hand_action(positive) and _has_prop(positive) and _has_full_body(positive):
        for kw in FULL_BODY_KEYWORDS:
            positive = positive.replace(kw, "")
            positive = positive.replace(kw.upper(), "")
        import re
        positive = re.sub(r",\s*,", ", ", positive)
        positive = re.sub(r"\s{2,}", " ", positive)
        positive = positive.strip(", ")
        positive = positive + ", " + UPPER_BODY_COMPOSITION
    return positive


def _inject_anatomy_lock(positive: str) -> str:
    if ANATOMY_LOCK not in positive:
        positive = positive + ", " + ANATOMY_LOCK
    return positive


def _inject_pose_lock(positive: str) -> str:
    pose_lock = (
        "only two hands visible, no third hand, no extra arm, "
        "no floating hand, hands anatomically correct, "
        "each hand clearly doing a single distinct action"
    )
    if pose_lock not in positive:
        positive = positive + ", " + pose_lock
    return positive


def _apply_safety_injections(positive: str, is_single_character: bool = True) -> str:
    if not is_single_character:
        return positive
    positive = _apply_composition_override(positive)
    positive = _inject_anatomy_lock(positive)
    if _has_hand_action(positive):
        positive = _inject_pose_lock(positive)
    return positive


def _get_genre_label(genre_value: str) -> str:
    labels = {
        "xianxia": "玄幻", "urban": "都市", "transmigration": "穿越",
        "historical": "古代", "modern_era": "近现代",
        "supernatural": "悬疑", "sci_fi": "科幻", "esports": "电竞",
    }
    return labels.get(genre_value, genre_value)


def build_prompt_from_identity_costume(
    identity: dict,
    costume: dict,
    genre_label: str = "",
    composition: str = "full body shot",
    lighting: str = "cinematic lighting",
    gender_tag: str = "",
) -> dict:
    """从身份层 + 装扮层 构建 ComfyUI Prompt"""
    parts = []

    if identity.get("temperament"):
        parts.append(identity["temperament"])
    if identity.get("face_desc"):
        parts.append(identity["face_desc"])
    if costume.get("hairstyle"):
        parts.append(costume["hairstyle"])

    outfit_parts = []
    if costume.get("outfit"):
        outfit_parts.append(costume["outfit"])
    if costume.get("accessories"):
        outfit_parts.append(costume["accessories"])
    if costume.get("makeup"):
        outfit_parts.append(costume["makeup"])
    if outfit_parts:
        parts.append(", ".join(outfit_parts))

    if costume.get("props"):
        parts.append(costume["props"])

    env_parts = []
    if genre_label:
        env_parts.append(f"{genre_label} setting")
    if composition:
        env_parts.append(composition)
    if lighting:
        env_parts.append(lighting)
    if costume.get("scene_hint"):
        env_parts.append(costume["scene_hint"])
    if env_parts:
        parts.append(", ".join(env_parts))

    parts.append(QUALITY_TAGS)

    positive = ", ".join(p for p in parts if p)

    gender = gender_tag
    if not gender and identity.get("gender"):
        gmap = {"female": "1girl", "male": "1boy"}
        gender = gmap.get(identity["gender"], "1girl")
    if gender:
        positive = gender + ", " + positive

    return {
        "positive": positive,
        "negative": NEGATIVE_PROMPT,
    }
