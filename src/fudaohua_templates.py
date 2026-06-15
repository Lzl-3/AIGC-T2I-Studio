# -*- coding: utf-8 -*-
import os, json, uuid
from typing import List, Dict, Optional

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'fudaohua_templates')
VALID_TYPES = ('costume', 'prop', 'makeup')

def _ensure_type_dir(t):
    d = os.path.join(TEMPLATE_DIR, t)
    os.makedirs(d, exist_ok=True)
    return d

def _slugify(title):
    safe = title.replace(' ', '_').replace('/', '_').replace('\\', '_')
    safe = ''.join(c for c in safe if c.isalnum() or c in '_-')
    return safe if safe else uuid.uuid4().hex[:8]

class TemplateManager:
    @staticmethod
    def save(ptype, title, pos_template, neg_prompt=''):
        if ptype not in VALID_TYPES:
            raise ValueError('bad type')
        if not title.strip():
            raise ValueError('title required')
        td = _ensure_type_dir(ptype)
        slug = _slugify(title)
        t = {'type': ptype, 'title': title.strip(), 'positive_template': pos_template.strip(), 'negative_prompt': neg_prompt.strip()}
        fp = os.path.join(td, slug + '.json')
        with open(fp, 'w', encoding='utf-8') as f:
            json.dump(t, f, ensure_ascii=False, indent=2)
        return t

    @staticmethod
    def get(ptype, title):
        if ptype not in VALID_TYPES: return None
        td = _ensure_type_dir(ptype)
        fp = os.path.join(td, _slugify(title) + '.json')
        if not os.path.exists(fp): return None
        with open(fp, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def list_all(ptype):
        if ptype not in VALID_TYPES: return []
        td = _ensure_type_dir(ptype)
        out = []
        for fn in sorted(os.listdir(td)):
            if fn.endswith('.json'):
                try:
                    with open(os.path.join(td, fn), 'r', encoding='utf-8') as f:
                        t = json.load(f)
                    out.append({'type': t.get('type', ptype), 'title': t.get('title', ''), 'positive_template': t.get('positive_template', ''), 'negative_prompt': t.get('negative_prompt', '')})
                except: pass
        return out

    @staticmethod
    def delete(ptype, title):
        if ptype not in VALID_TYPES: return False
        td = _ensure_type_dir(ptype)
        fp = os.path.join(td, _slugify(title) + '.json')
        if os.path.exists(fp):
            os.remove(fp)
            return True
        return False

    @staticmethod
    def migrate_builtin_presets():
        from src.fudaohua_presets import COSTUME_PRESETS, PROP_PRESETS, MAKEUP_PRESETS, COSTUME_TEMPLATE, PROP_TEMPLATE, MAKEUP_TEMPLATE, NEGATIVE_PROMPT
        tm = {'costume': (COSTUME_PRESETS, COSTUME_TEMPLATE), 'prop': (PROP_PRESETS, PROP_TEMPLATE), 'makeup': (MAKEUP_PRESETS, MAKEUP_TEMPLATE)}
        result = {'migrated': 0, 'types': {}}
        for ptype, (presets, default_tpl) in tm.items():
            td = _ensure_type_dir(ptype)
            existing = [f for f in os.listdir(td) if f.endswith('.json')]
            if existing:
                result['types'][ptype] = f'skipped ({len(existing)} existing)'
                continue
            count = 0
            for preset in presets.values():
                positive = default_tpl.replace('{core_tags}', preset.get('core_tags', ''))
                try:
                    TemplateManager.save(ptype, preset['name_cn'], positive, NEGATIVE_PROMPT)
                    count += 1
                except: pass
            result['types'][ptype] = f'migrated {count}'
            result['migrated'] += count
        return result

def list_templates(ptype): return TemplateManager.list_all(ptype)
def save_template(ptype, title, pos, neg=''): return TemplateManager.save(ptype, title, pos, neg)
def delete_template(ptype, title): return TemplateManager.delete(ptype, title)
def get_template(ptype, title): return TemplateManager.get(ptype, title)
