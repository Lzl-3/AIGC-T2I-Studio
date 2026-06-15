# -*- coding: utf-8 -*-
# Role addon package - user character CRUD managed via data/characters/*.json
# Auto-injects into character_presets at startup, exposes /api/characters/* routes

import json, os, shutil
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARS_DATA_DIR = os.path.join(BASE_DIR, 'data', 'characters')
CHARS_ASSET_DIR = os.path.join(BASE_DIR, 'characters')
TRASH_DATA_DIR = os.path.join(CHARS_ASSET_DIR, '.trash', 'data')
TRASH_ASSET_DIR = os.path.join(CHARS_ASSET_DIR, '.trash')

os.makedirs(CHARS_DATA_DIR, exist_ok=True)
os.makedirs(CHARS_ASSET_DIR, exist_ok=True)
os.makedirs(TRASH_DATA_DIR, exist_ok=True)
os.makedirs(TRASH_ASSET_DIR, exist_ok=True)
# ============================================================
# Pydantic model
# ============================================================

class CharacterCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, description='character name')
    positive: str = Field(default='', description='positive prompt (English)')
    negative: str = Field(default='', description='negative prompt (English)')
    metadata: dict = Field(default_factory=dict, description='extra metadata (gender, age, etc.)')


# ============================================================
# JSON file helpers
# ============================================================

def _json_path(name: str) -> str:
    return os.path.join(CHARS_DATA_DIR, name + '.json')


def _load_json(name: str) -> Optional[dict]:
    path = _json_path(name)
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _save_json(data: dict) -> None:
    path = _json_path(data['name'])
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _delete_json(name: str) -> None:
    src = _json_path(name)
    if not os.path.exists(src):
        return
    dst = os.path.join(TRASH_DATA_DIR, name + '.json')
    os.makedirs(TRASH_DATA_DIR, exist_ok=True)
    if os.path.exists(dst):
        os.remove(dst)
    shutil.move(src, dst)


def _asset_dir(name: str) -> str:
    return os.path.join(CHARS_ASSET_DIR, name)


def _create_asset_dir(name: str) -> str:
    path = _asset_dir(name)
    os.makedirs(path, exist_ok=True)
    return path


def _trash_asset_dir(name: str) -> None:
    src = _asset_dir(name)
    if not os.path.exists(src):
        return
    dst = os.path.join(TRASH_ASSET_DIR, name)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.move(src, dst)


# ============================================================
# Dict builders: JSON -> CHARACTER_ADDON_LAYERS / PRESETS
# ============================================================

def _build_layers_entry(data: dict) -> dict:
    """从用户 JSON 构建 CHARACTER_LAYERS 条目。

    优先使用 metadata 中用户明确指定的字段；
    metadata 为空时从 positive Prompt 文本自动推断性别/面部/发型/气质。
    """
    name = data["name"]
    positive = data.get("positive", "")
    meta = data.get("metadata", {})
    pos_lower = positive.lower()

    # --- 性别推断 ---
    gender = meta.get("gender", "")
    if not gender:
        if any(w in pos_lower for w in ("1girl", "female", "woman", "girl")):
            gender = "女"
        elif any(w in pos_lower for w in ("1boy", "male", "man", "boy")):
            gender = "男"
        else:
            gender = "女"

    # --- 面部标签提取 ---
    face = _parse_face_from_prompt(positive)

    # --- 发型标签提取 ---
    hair = _parse_hair_from_prompt(positive)

    import re

    # --- 纯净气质 Prompt（去除通用质量标签，保留角色特征） ---
    quality_noise = [
        "masterpiece", "best quality", "highly detailed", "sharp focus",
        "ultra detailed", "8k", "professional lighting", "cinematic",
        "game cg", "anime style",
    ]
    clean = positive
    for noise in quality_noise:
        clean = re.sub(r"\b" + re.escape(noise) + r"\b,?\s*", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r",\s*,", ", ", clean)
    # Normalize: replace newlines and Chinese commas with commas, collapse spaces
    clean = clean.replace("\n", ", ").replace("，", ", ")
    clean = re.sub(r",\s*,", ", ", clean)
    clean = re.sub(r"\s{2,}", " ", clean).strip(", ")

    return {
        "era": meta.get("era", ""),
        "identity": {
            "gender": gender,
            "age": meta.get("age", "") or "青年",
            "height": meta.get("height", "") or "",
            "body": meta.get("body", "") or "",
        },
        "face": face,
        "hair": hair,
        "upper": {"garment": "", "fabric": "", "sleeves": "", "detail": ""},
        "lower": {"garment": "", "fabric": "", "detail": ""},
        "footwear": {"type": "", "detail": ""},
        "accessories": [],
        "makeup": meta.get("makeup", ""),
        "temperament": meta.get("temperament", "") or clean,
        "style": positive,
    }


def _parse_face_from_prompt(positive):
    """从 Prompt 文本提取面部特征关键词。"""
    pos_lower = positive.lower()
    result = {"structure": "", "skin": "", "eyes": "", "nose": "", "lips": "", "eyebrows": ""}

    skin_keywords = ["fair skin", "porcelain skin", "pale skin",
                     "smooth skin", "realistic skin", "natural skin",
                     "clear skin", "creamy skin"]
    for kw in skin_keywords:
        if kw in pos_lower:
            result["skin"] = kw
            break

    eye_keywords = ["detailed eyes", "almond eyes", "bright eyes",
                    "sparkling eyes", "dark eyes", "brown eyes",
                    "blue eyes", "green eyes", "deep eyes",
                    "sharp eyes", "beautiful eyes"]
    for kw in eye_keywords:
        if kw in pos_lower:
            result["eyes"] = kw
            break

    face_keywords = ["oval face", "delicate face", "round face",
                     "beautiful face", "angular face",
                     "chinese facial features", "sharp jawline"]
    for kw in face_keywords:
        if kw in pos_lower:
            result["structure"] = kw
            break

    return result


def _parse_hair_from_prompt(positive):
    """从 Prompt 文本提取发型关键词。"""
    pos_lower = positive.lower()
    result = {"style": "", "texture": "", "accessory": ""}

    hair_styles = [
        "long black hair", "long silver hair", "long white hair",
        "short hair", "ponytail", "braided hair", "bun", "updo",
        "windswept hair", "flowing hair", "straight hair", "wavy hair",
    ]
    for hs in hair_styles:
        if hs in pos_lower:
            result["style"] = hs
            break
    if not result["style"] and "hair" in pos_lower:
        m = re.search(r"([\w\s-]+)\s+hair", pos_lower)
        if m:
            candidate = m.group(1).strip()
            if candidate and candidate not in ("detailed", "individual", "strands"):
                result["style"] = candidate + " hair"

    textures = ["silky", "smooth", "glossy", "lustrous", "detailed hair strands"]
    for t in textures:
        if t in pos_lower:
            result["texture"] = t
            break

    accessories = [
        "hairpin", "hair crown", "hair accessory", "jade hairpin",
        "silver hairpin", "gold hairpin", "ribbon", "hair ornament",
        "crown", "tiara",
    ]
    for a in accessories:
        if a in pos_lower:
            result["accessory"] = a
            break

    return result


def _build_presets_entry(data: dict) -> dict:
    name = data['name']
    positive = data.get('positive', '')
    negative = data.get('negative', '')
    meta = data.get('metadata', {})
    return {
        'gender': meta.get('gender', 'female'),
        'trigger_word': meta.get('trigger_word', name),
        'identity': meta.get('identity', name),
        'face': positive,
        'emotion': '',
        'hair': '',
        'clothing': '',
        'weapon': '',
        'composition': '',
        'negative': negative,
    }

# ============================================================
# Scan + build + inject
# ============================================================

CHARACTER_ADDON_LAYERS = {}
CHARACTER_ADDON_PRESETS = {}

def _scan_and_build():
    global CHARACTER_ADDON_LAYERS, CHARACTER_ADDON_PRESETS
    CHARACTER_ADDON_LAYERS = {}
    CHARACTER_ADDON_PRESETS = {}
    if not os.path.isdir(CHARS_DATA_DIR):
        return
    for fname in os.listdir(CHARS_DATA_DIR):
        if not fname.endswith('.json'):
            continue
        path = os.path.join(CHARS_DATA_DIR, fname)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            name = data.get('name', '')
            if not name:
                continue
            CHARACTER_ADDON_LAYERS[name] = _build_layers_entry(data)
            CHARACTER_ADDON_PRESETS[name] = _build_presets_entry(data)
        except Exception:
            pass


def _inject_into_presets():
    try:
        from src.character_presets import CHARACTER_LAYERS, CHARACTER_PRESETS
        CHARACTER_LAYERS.update(CHARACTER_ADDON_LAYERS)
        CHARACTER_PRESETS.update(CHARACTER_ADDON_PRESETS)
    except ImportError:
        pass


# Run at import time
_scan_and_build()
_inject_into_presets()

# ============================================================
# CRUD functions
# ============================================================

def create_character(name: str, positive: str = '', negative: str = '', metadata: dict = None) -> dict:
    if not name or not name.strip():
        raise ValueError('character name is required')
    name = name.strip()
    if _load_json(name) is not None:
        raise ValueError('character already exists: ' + name)
    data = {
        'name': name,
        'positive': positive or '',
        'negative': negative or '',
        'metadata': metadata or {},
    }
    data['metadata']['created_at'] = datetime.now().isoformat()
    _save_json(data)
    _create_asset_dir(name)
    CHARACTER_ADDON_LAYERS[name] = _build_layers_entry(data)
    CHARACTER_ADDON_PRESETS[name] = _build_presets_entry(data)
    _inject_into_presets()
    return data


def delete_character(name: str) -> bool:
    if not name or not name.strip():
        raise ValueError('character name is required')
    name = name.strip()
    data = _load_json(name)
    if data is None:
        return False
    _delete_json(name)
    _trash_asset_dir(name)
    CHARACTER_ADDON_LAYERS.pop(name, None)
    CHARACTER_ADDON_PRESETS.pop(name, None)
    try:
        from src.character_presets import CHARACTER_LAYERS, CHARACTER_PRESETS
        CHARACTER_LAYERS.pop(name, None)
        CHARACTER_PRESETS.pop(name, None)
    except ImportError:
        pass
    return True


def list_user_characters() -> list[dict]:
    result = []
    if not os.path.isdir(CHARS_DATA_DIR):
        return result
    for fname in os.listdir(CHARS_DATA_DIR):
        if not fname.endswith('.json'):
            continue
        path = os.path.join(CHARS_DATA_DIR, fname)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            result.append({
                'name': data.get('name', ''),
                'positive': data.get('positive', ''),
                'negative': data.get('negative', ''),
                'metadata': data.get('metadata', {}),
            })
        except Exception:
            pass
    return result

# ============================================================
# API Router
# ============================================================

router = APIRouter(prefix='/api/characters', tags=['Character Manager'])


@router.post('/create')
async def api_create_character(req: CharacterCreateRequest):
    try:
        data = create_character(
            name=req.name,
            positive=req.positive,
            negative=req.negative,
            metadata=req.metadata,
        )
        return {'status': 'ok', 'character': data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete('/{name:path}')
async def api_delete_character(name: str):
    try:
        ok = delete_character(name)
        if not ok:
            raise HTTPException(status_code=404, detail='character not found: ' + name)
        return {'status': 'ok', 'name': name}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get('/list')
async def api_list_characters():
    return {'characters': list_user_characters()}
