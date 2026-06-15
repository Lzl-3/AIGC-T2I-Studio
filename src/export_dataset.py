# -*- coding: utf-8 -*-
"""export training dataset for OneTrainer / kohya"""
import os,json,shutil
from pathlib import Path
from typing import Optional
from datetime import datetime
from src.caption_generator import CaptionGenerator
from src.deduplicate import ImageDeduplicator
from src.quality_filter import QualityFilter
from src.costume_presets import COSTUME_PRESETS

class DatasetExporter:
    """export training dataset with captions"""

    def __init__(self,costume_id:str,output_dir:str="./output",export_dir:str="./datasets"):
        costume=COSTUME_PRESETS.get(costume_id)
        if not costume: raise ValueError(f"unknown costume: {costume_id}")
        self.costume=costume
        self.costume_id=costume_id
        self.output_dir=Path(output_dir)
        self.export_dir=Path(export_dir)
        self.caption_gen=CaptionGenerator(costume_id)
        self.dedup=ImageDeduplicator(str(output_dir))
        self.quality=QualityFilter(str(output_dir))

    def prepare_dataset(self,top_n:int=150,min_score:float=0.3)->dict:
        """full pipeline: dedup -> score -> filter -> export"""
        result={"costume":self.costume["name_cn"],"costume_id":self.costume_id,"trigger_word":self.caption_gen.get_trigger_word(),"steps":{}}
        result["steps"]["dedup"]=self.dedup.find_duplicates()
        result["steps"]["scoring"]=self.quality.score_all()
        result["steps"]["filter"]=self.quality.filter_by_score(min_score)
        result["steps"]["top_n"]=self.quality.get_top_n(top_n)
        result["ready"]=result["steps"]["top_n"]["avg_score"]>=min_score
        return result

    def export(self,top_n:int=150,copy_files:bool=True)->dict:
        """export dataset: copy top images + generate .txt captions"""
        top=self.quality.get_top_n(top_n)
        top_images=top["images"]
        if not top_images: return {"error":"no images to export"}
        dataset_name=f"{self.costume_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}"
        dataset_path=self.export_dir/dataset_name
        img_path=dataset_path/"images"
        img_path.mkdir(parents=True,exist_ok=True)
        exported=[]
        for item in top_images:
            src=self.output_dir/item["file"]
            dst=img_path/item["file"]
            if copy_files and os.path.exists(src): shutil.copy2(src,dst)
            txt_name=item["file"].replace(".png",".txt")
            txt_path=img_path/txt_name
            caption=self.caption_gen.generate_txt_content(item["file"])
            with open(txt_path,"w",encoding="utf-8") as f: f.write(caption)
            exported.append({"image":item["file"],"caption":caption,"score":item["total_score"]})
        meta={"costume":self.costume["name_cn"],"costume_id":self.costume_id,"trigger_word":self.caption_gen.get_trigger_word(),"training_tags":self.costume["training_tags"],"image_count":len(exported),"exported_at":datetime.now().isoformat(),"images":exported}
        with open(dataset_path/"dataset_meta.json","w",encoding="utf-8") as f: json.dump(meta,f,ensure_ascii=False,indent=2)
        return {"dataset_name":dataset_name,"dataset_path":str(dataset_path),"image_count":len(exported),"avg_score":top["avg_score"],"meta":meta}