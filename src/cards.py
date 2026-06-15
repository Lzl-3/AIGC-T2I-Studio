# -*- coding: utf-8 -*-
"""工作流卡片管理器：CRUD + 锁定 + 模型注入

每张卡片 = 一套预设的工作流参数（基模/VAE/CLIP/LoRA + 默认参数 + 提示词模板）
人工验图后锁定，生图时只选卡片不调参。
"""

import json
import uuid
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from config.settings import settings
from src.workflow_engine import detect_model_type

CARDS_DIR = Path(settings.workflow_dir) / "cards"

# 卡片状态
STATUS_DRAFT = "draft"       # 草稿：可随意修改
STATUS_TESTING = "testing"   # 测试中：参数基本确定，允许微调
STATUS_LOCKED = "locked"     # 已锁定：不可修改，生图专用


def _ensure_dir():
    """确保卡片存储目录存在"""
    CARDS_DIR.mkdir(parents=True, exist_ok=True)


def _card_path(card_id: str) -> Path:
    """获取卡片文件路径"""
    return CARDS_DIR / f"{card_id}.json"


class WorkflowCard:
    """工作流卡片数据模型"""

    def __init__(
        self,
        card_id: str = "",
        name: str = "",
        description: str = "",
        category: str = "character",
        status: str = STATUS_DRAFT,

        # 模型选择
        checkpoint: str = "",
        model_type: str = "",
        vae: str = "",
        clip_model: str = "",
        lora: str = "",
        lora_strength: float = 1.0,
        controlnet: str = "",

        # 默认生成参数
        width: int = 1024,
        height: int = 1024,
        steps: int = 28,
        cfg: float = 7.0,
        sampler_name: str = "euler_ancestral",
        scheduler: str = "normal",
        batch_count: int = 1,

        # 提示词模板
        positive_prefix: str = "",
        negative_prefix: str = "",

        # 元数据
        created_at: str = "",
        updated_at: str = "",
        locked_at: str = "",
        notes: str = "",
    ):
        self.card_id = card_id or str(uuid.uuid4())[:8]
        self.name = name
        self.description = description
        self.category = category
        self.status = status

        self.checkpoint = checkpoint
        self.model_type = model_type
        self.vae = vae
        self.clip_model = clip_model
        self.lora = lora
        self.lora_strength = lora_strength
        self.controlnet = controlnet

        self.width = width
        self.height = height
        self.steps = steps
        self.cfg = cfg
        self.sampler_name = sampler_name
        self.scheduler = scheduler
        self.batch_count = batch_count

        self.positive_prefix = positive_prefix
        self.negative_prefix = negative_prefix

        now = datetime.now().isoformat()
        self.created_at = created_at or now
        self.updated_at = updated_at or now
        self.locked_at = locked_at
        self.notes = notes

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "card_id": self.card_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "status": self.status,
            "checkpoint": self.checkpoint,
            "model_type": self.model_type,
            "vae": self.vae,
            "clip_model": self.clip_model,
            "lora": self.lora,
            "lora_strength": self.lora_strength,
            "controlnet": self.controlnet,
            "width": self.width,
            "height": self.height,
            "steps": self.steps,
            "cfg": self.cfg,
            "sampler_name": self.sampler_name,
            "scheduler": self.scheduler,
            "batch_count": self.batch_count,
            "positive_prefix": self.positive_prefix,
            "negative_prefix": self.negative_prefix,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "locked_at": self.locked_at,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WorkflowCard":
        """从字典反序列化"""
        return cls(**d)

    def save(self):
        """保存卡片到文件"""
        _ensure_dir()
        self.updated_at = datetime.now().isoformat()
        with open(_card_path(self.card_id), "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    def delete(self):
        """删除卡片文件"""
        p = _card_path(self.card_id)
        if p.exists():
            p.unlink()

    def lock(self, notes: str = ""):
        """锁定卡片（不可再修改参数）"""
        self.status = STATUS_LOCKED
        self.locked_at = datetime.now().isoformat()
        if notes:
            self.notes = notes
        self.save()

    def unlock(self):
        """解锁卡片（回到测试状态）"""
        if self.status == STATUS_LOCKED:
            self.status = STATUS_TESTING
            self.locked_at = ""
            self.save()

    def is_locked(self) -> bool:
        """是否已锁定"""
        return self.status == STATUS_LOCKED


# ========== CRUD 操作 ==========

def list_all_cards(category: str = "") -> list[dict]:
    """列出所有卡片"""
    _ensure_dir()
    cards = []
    for f in sorted(CARDS_DIR.glob("*.json"), reverse=True):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                d = json.load(fh)
            if category and d.get("category", "") != category:
                continue
            cards.append(d)
        except Exception:
            pass
    return cards


def get_card(card_id: str) -> Optional[dict]:
    """获取单张卡片"""
    p = _card_path(card_id)
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def create_card(data: dict) -> WorkflowCard:
    """创建新卡片"""
    card = WorkflowCard(
        name=data.get("name", "未命名卡片"),
        description=data.get("description", ""),
        category=data.get("category", "character"),
        status=data.get("status", STATUS_DRAFT),
        checkpoint=data.get("checkpoint", ""),
        model_type=data.get("model_type") or detect_model_type(data.get("checkpoint", "")),
        vae=data.get("vae", ""),
        clip_model=data.get("clip_model", ""),
        lora=data.get("lora", ""),
        lora_strength=data.get("lora_strength", 1.0),
        controlnet=data.get("controlnet", ""),
        width=data.get("width", 1024),
        height=data.get("height", 1024),
        steps=data.get("steps", 28),
        cfg=data.get("cfg", 7.0),
        sampler_name=data.get("sampler_name", "euler_ancestral"),
        scheduler=data.get("scheduler", "normal"),
        batch_count=data.get("batch_count", 1),
        positive_prefix=data.get("positive_prefix", ""),
        negative_prefix=data.get("negative_prefix", ""),
        notes=data.get("notes", ""),
    )
    card.save()
    return card


def update_card(card_id: str, data: dict) -> Optional[WorkflowCard]:
    """更新卡片（锁定状态只允许更新 notes 和 status）"""
    existing = get_card(card_id)
    if not existing:
        return None

    card = WorkflowCard.from_dict(existing)
    if card.is_locked():
        # 锁定后只允许更新备注和状态
        if "notes" in data:
            card.notes = data["notes"]
        if "status" in data and data["status"] != STATUS_LOCKED:
            card.status = data["status"]
        card.save()
        return card

    # 非锁定状态可更新全部字段
    updatable = [
        "name", "description", "category", "status",
        "checkpoint", "model_type", "vae", "clip_model", "lora", "lora_strength", "controlnet",
        "width", "height", "steps", "cfg", "sampler_name", "scheduler", "batch_count",
        "positive_prefix", "negative_prefix", "notes",
    ]
    for key in updatable:
        if key in data:
            setattr(card, key, data[key])
    # 自动推断 model_type（如果 checkpoint 变更）
    if data.get("checkpoint") and not data.get("model_type"):
        card.model_type = detect_model_type(data["checkpoint"])
    card.save()
    return card


def delete_card(card_id: str) -> bool:
    """删除卡片"""
    p = _card_path(card_id)
    if p.exists():
        p.unlink()
        return True
    return False


def lock_card(card_id: str, notes: str = "") -> Optional[WorkflowCard]:
    """锁定卡片"""
    existing = get_card(card_id)
    if not existing:
        return None
    card = WorkflowCard.from_dict(existing)
    card.lock(notes)
    return card


def unlock_card(card_id: str) -> Optional[WorkflowCard]:
    """解锁卡片"""
    existing = get_card(card_id)
    if not existing:
        return None
    card = WorkflowCard.from_dict(existing)
    card.unlock()
    return card


# ============================================================
# 角色卡片的身份 + 装扮拆分系统
# ============================================================

COSTUME_SYSTEM_VERSION = 1


def _ensure_costume_system(card_data: dict) -> dict:
    """确保卡片包含装扮系统字段（向后兼容旧卡片）"""
    if "identity" not in card_data:
        card_data["identity"] = {
            "name": card_data.get("name", ""),
            "gender": "female",
            "age_range": "",
            "face_desc": "",
            "body_type": "",
            "temperament": "",
        }
    if "costume_active_index" not in card_data:
        card_data["costume_active_index"] = 0
    if "costume_library" not in card_data:
        default_costume = {
            "name": "默认装扮",
            "outfit": card_data.get("positive_prefix", ""),
            "accessories": "",
            "hairstyle": "",
            "makeup": "",
            "props": "",
            "scene_hint": "",
        }
        card_data["costume_library"] = [default_costume]
    return card_data


def _read_card_json(card_id: str) -> dict:
    """读取卡片 JSON 并自动补全装扮系统"""
    data = get_card(card_id)
    if data is None:
        return None
    return _ensure_costume_system(data)


def _write_card_json(card_id: str, data: dict):
    """写入卡片 JSON"""
    _ensure_dir()
    data["updated_at"] = datetime.now().isoformat()
    with open(_card_path(card_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------- 装扮库 CRUD ----------

def get_card_costumes(card_id: str) -> dict:
    """获取卡片的所有装扮信息"""
    data = _read_card_json(card_id)
    if data is None:
        return None
    return {
        "identity": data.get("identity", {}),
        "active_index": data.get("costume_active_index", 0),
        "costumes": data.get("costume_library", []),
    }


def add_card_costume(card_id: str, costume: dict) -> dict:
    """添加新装扮到装扮库"""
    data = _read_card_json(card_id)
    if data is None:
        return None
    costume.setdefault("name", "新装扮")
    for key in ("outfit", "accessories", "hairstyle", "makeup", "props", "scene_hint"):
        costume.setdefault(key, "")
    data["costume_library"].append(costume)
    _write_card_json(card_id, data)
    return {
        "identity": data["identity"],
        "active_index": data["costume_active_index"],
        "costumes": data["costume_library"],
        "added_index": len(data["costume_library"]) - 1,
    }


def update_card_costume(card_id: str, index: int, costume: dict) -> dict:
    """更新装扮库中指定索引的装扮"""
    data = _read_card_json(card_id)
    if data is None:
        return None
    if index < 0 or index >= len(data["costume_library"]):
        return None
    library = data["costume_library"]
    for key in ("name", "outfit", "accessories", "hairstyle", "makeup", "props", "scene_hint"):
        if key in costume and costume[key]:
            library[index][key] = costume[key]
    _write_card_json(card_id, data)
    return {
        "identity": data["identity"],
        "active_index": data["costume_active_index"],
        "costumes": data["costume_library"],
        "updated_index": index,
    }


def activate_card_costume(card_id: str, index: int) -> dict:
    """切换激活装扮"""
    data = _read_card_json(card_id)
    if data is None:
        return None
    if index < 0 or index >= len(data["costume_library"]):
        return None
    data["costume_active_index"] = index
    _write_card_json(card_id, data)
    return {
        "identity": data["identity"],
        "active_index": index,
        "costumes": data["costume_library"],
    }


def delete_card_costume(card_id: str, index: int) -> dict:
    """删除装扮库中的装扮（至少保留一个）"""
    data = _read_card_json(card_id)
    if data is None:
        return None
    if index < 0 or index >= len(data["costume_library"]):
        return None
    if len(data["costume_library"]) <= 1:
        return None
    data["costume_library"].pop(index)
    if data["costume_active_index"] >= len(data["costume_library"]):
        data["costume_active_index"] = 0
    elif data["costume_active_index"] > index:
        data["costume_active_index"] -= 1
    _write_card_json(card_id, data)
    return {
        "identity": data["identity"],
        "active_index": data["costume_active_index"],
        "costumes": data["costume_library"],
    }


def update_card_identity(card_id: str, identity: dict) -> dict:
    """更新卡片身份信息（锁定的卡片不允许修改）"""
    data = _read_card_json(card_id)
    if data is None:
        return None
    if data.get("status") == STATUS_LOCKED:
        return None
    for key in ("name", "gender", "age_range", "face_desc", "body_type", "temperament"):
        if key in identity:
            data["identity"][key] = identity[key]
    _write_card_json(card_id, data)
    return {"identity": data["identity"]}


def get_card_combined_prompt(card_id: str) -> dict:
    """获取身份+当前激活装扮的合并参数"""
    data = _read_card_json(card_id)
    if data is None:
        return None
    identity = data.get("identity", {})
    lib = data.get("costume_library", [])
    idx = data.get("costume_active_index", 0)
    active_costume = lib[idx] if 0 <= idx < len(lib) else {}
    return {
        "card_id": card_id,
        "identity": identity,
        "costume": active_costume,
        "checkpoint": data.get("checkpoint", ""),
        "model_type": data.get("model_type", ""),
        "width": data.get("width", 1024),
        "height": data.get("height", 1024),
        "steps": data.get("steps", 28),
        "cfg": data.get("cfg", 7.0),
        "sampler_name": data.get("sampler_name", "euler_ancestral"),
        "scheduler": data.get("scheduler", "normal"),
        "batch_count": data.get("batch_count", 1),
        "negative_prefix": data.get("negative_prefix", ""),
        "category": data.get("category", "character"),
        "status": data.get("status", STATUS_DRAFT),
    }
