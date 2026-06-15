# -*- coding: utf-8 -*-
"""auto caption generator - clothing-only training tags"""
from typing import Optional
from src.costume_presets import COSTUME_PRESETS

class CaptionGenerator:
    """generate training captions that only include clothing features"""

    def __init__(self,costume_id:str):
        costume=COSTUME_PRESETS.get(costume_id)
        if not costume: raise ValueError(f"unknown costume: {costume_id}")
        self.costume=costume
        self.costume_id=costume_id

    def generate_tags(self)->str:
        """return comma-separated training tags (clothing only)"""
        tags=self.costume.get("training_tags",[])
        return ", ".join(tags)

    def generate_txt_content(self,image_filename:str)->str:
        """generate .txt caption file content for LoRA training"""
        tags=self.generate_tags()
        return tags

    def get_trigger_word(self)->str:
        """get trigger word for LoRA activation"""
        costume_id=self.costume_id
        return costume_id.replace("_","")