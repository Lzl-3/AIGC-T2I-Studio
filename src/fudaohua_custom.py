# -*- coding: utf-8 -*-
"""服道化自定义预设 - 用户手动输入的训练预设"""
import os, json, uuid
from typing import List, Dict, Optional

CUSTOM_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'fudaohua_custom')


def save_custom_preset(preset_type: str, name: str, core_tags: str) -> dict:
    """保存自定义预设到固定文件夹"""
    type_dir = os.path.join(CUSTOM_DIR, preset_type)
    os.makedirs(type_dir, exist_ok=True)
    preset_id = '99_' + uuid.uuid4().hex[:8]
    preset = {
        "id": preset_id,
        "name_cn": name,
        "core_tags": core_tags,
        "training_tags": [t.strip() for t in core_tags.replace(",", " ").split() if len(t.strip()) > 2],
    }
    filepath = os.path.join(type_dir, preset_id + '.json')
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(preset, f, ensure_ascii=False, indent=2)
    return preset


def list_custom_presets(preset_type: str) -> List[dict]:
    """列出指定类型的所有自定义预设"""
    type_dir = os.path.join(CUSTOM_DIR, preset_type)
    if not os.path.isdir(type_dir):
        return []
    presets = []
    for fname in sorted(os.listdir(type_dir)):
        if fname.endswith('.json'):
            fpath = os.path.join(type_dir, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    p = json.load(f)
                presets.append({
                    "id": p["id"],
                    "name_cn": p["name_cn"],
                    "tag_count": len(p.get("training_tags", [])),
                    "training_tags": p.get("training_tags", []),
                })
            except Exception:
                pass
    return presets


def get_custom_preset(preset_type: str, preset_id: str) -> Optional[dict]:
    """获取单个自定义预设的完整数据"""
    type_dir = os.path.join(CUSTOM_DIR, preset_type)
    filepath = os.path.join(type_dir, preset_id + '.json')
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def delete_custom_preset(preset_type: str, preset_id: str) -> bool:
    """删除自定义预设"""
    type_dir = os.path.join(CUSTOM_DIR, preset_type)
    filepath = os.path.join(type_dir, preset_id + '.json')
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False