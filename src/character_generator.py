# -*- coding: utf-8 -*-
"""Character Prompt Builder

Independent from training material module.
Fixed: identity + face + hair + costume + accessories + temperament + makeup
Variable: expression (from request.expressions)
"""

from typing import Optional
from src.character_presets import (
    CHARACTER_LAYERS, CHARACTER_PRESETS, GENDER_TAGS,
    GENRE_ENVIRONMENT_TAGS, DEFAULT_CHARACTER_FALLBACKS,
)
from config.settings import NEGATIVE_PROMPT

QUALITY_TAGS = "masterpiece, best quality, highly detailed, sharp focus"

EXPRESSION_MAP = {
    "neutral": "calm expression, neutral face, serene gaze",
    "smile": "gentle smile, soft expression, warm slight smile",
    "angry": "angry expression, fierce glare, intense eyes",
    "sad": "sad expression, sorrowful gaze, melancholic look",
}

ANATOMY_LOCK = "perfect anatomy, anatomically correct, five fingers on each hand, proportional limbs, natural body proportions"
POSE_LOCK = "only two hands visible, no third hand, no extra arm, no floating hand, hands anatomically correct"


def _build_identity_tag(layers, gender_tag):
    ident = layers["identity"]
    return f"{gender_tag}, {ident['height']}, {ident['age']}, {ident['body']}, chinese facial features"


def _build_face_tag(layers):
    face = layers["face"]
    return f"{face['structure']}, {face['skin']}, {face['eyes']}, {face['nose']}, {face['lips']}, {face['eyebrows']}"


def _build_hair_tag(layers):
    hair = layers["hair"]
    parts = [hair["style"], hair["texture"]]
    if hair.get("accessory"):
        parts.append(hair["accessory"])
    return ", ".join(parts)


def _build_costume_tag(layers):
    upper = layers["upper"]
    lower = layers["lower"]
    footwear = layers["footwear"]
    acc = layers.get("accessories", [])
    upper_text = f"{upper['garment']}, {upper['fabric']}, {upper['sleeves']}"
    if upper.get("detail"):
        upper_text += f", {upper['detail']}"
    lower_text = f"{lower['garment']}, {lower['fabric']}"
    if lower.get("detail"):
        lower_text += f", {lower['detail']}"
    footwear_text = footwear["type"]
    if footwear.get("detail"):
        footwear_text += f", {footwear['detail']}"
    parts = [upper_text, lower_text, footwear_text]
    if acc:
        parts.append(", ".join(acc))
    return ", ".join(parts)


def _build_makeup_tag(layers):
    return f"makeup: {layers['makeup']}"


def _build_fixed_base(layers, gender_tag):
    parts = [
        layers.get("temperament", ""),
        _build_identity_tag(layers, gender_tag),
        _build_face_tag(layers),
        _build_hair_tag(layers),
        _build_costume_tag(layers),
        _build_makeup_tag(layers),
    ]
    return ", ".join(p for p in parts if p)


def _apply_safety_injections(positive):
    if ANATOMY_LOCK not in positive:
        positive = positive + ", " + ANATOMY_LOCK
    if POSE_LOCK not in positive:
        positive = positive + ", " + POSE_LOCK
    return positive


def build_character_prompts(request):
    """Build character generation prompts from character profile.

    Fixed layers: identity + face + hair + costume + accessories + temperament + makeup
    Variable: expression (from request.expressions)

    Completely independent from training material module.
    Training material uses get_training_identity() for identity-only extraction.
    This module reads full CHARACTER_LAYERS for complete fixed prompt assembly.
    """
    from src.prompt_builder import _get_genre_label

    role = request.role_name or "character"
    genre_label = _get_genre_label(request.genre.value)
    gender_tag = GENDER_TAGS.get(
        request.character_gender, "1girl, asian woman, female, chinese facial features"
    )
    environment = GENRE_ENVIRONMENT_TAGS.get(request.genre.value, "")

    layers = CHARACTER_LAYERS.get(role)

    if layers:
        fixed_base = _build_fixed_base(layers, gender_tag)
    else:
        preset = CHARACTER_PRESETS.get(role)
        if preset:
            trigger = preset.get("trigger_word", role)
            fixed_parts = [
                f"{gender_tag}, {trigger}, {preset.get('identity', '')}",
                preset.get("face", ""),
                preset.get("hair", ""),
                preset.get("clothing", ""),
                preset.get("weapon", ""),
            ]
            fixed_base = ", ".join(p for p in fixed_parts if p)
        else:
            first_tag = gender_tag.split(",")[0].strip()
            fallback_face = DEFAULT_CHARACTER_FALLBACKS.get(
                first_tag, DEFAULT_CHARACTER_FALLBACKS.get("female", "")
            )
            fixed_base = f"{gender_tag}, {role}, {fallback_face}"

    expressions = getattr(request, "expressions", []) or ["neutral"]
    prompt_infos = []

    for expr in expressions:
        expr_tag = EXPRESSION_MAP.get(
            expr, f"{expr} expression, calm expression, neutral face"
        )
        parts = [fixed_base, expr_tag]
        if environment:
            parts.append(environment)
        parts.append(QUALITY_TAGS)
        positive = ", ".join(p for p in parts if p)
        positive = _apply_safety_injections(positive)
        negative = NEGATIVE_PROMPT + ", multiple characters"
        prompt_infos.append({
            "positive": positive,
            "negative": negative,
            "expression": expr,
        })

    return {
        "type": "character",
        "prompts": prompt_infos,
        "angles": getattr(request, "angles", ["front_view"]) or ["front_view"],
        "genre_label": genre_label,
        "role": role,
    }