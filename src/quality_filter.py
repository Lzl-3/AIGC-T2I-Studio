# -*- coding: utf-8 -*-
"""image quality scoring and filtering"""
import os,json
from pathlib import Path
from typing import Optional

class QualityFilter:
    """score and filter generated images by basic quality metrics"""

    def __init__(self,output_dir:str="./output"):
        self.output_dir=Path(output_dir)
        self.scores={}

    def _file_size_score(self,filepath:str)->float:
        """score based on file size (larger=more detail, 0-1)"""
        try: size=os.path.getsize(filepath); return min(size/(500*1024),1.0)
        except: return 0.0

    def _resolution_score(self,filepath:str)->float:
        """check if file exists and has reasonable size"""
        try:
            from PIL import Image; img=Image.open(filepath); w,h=img.size
            score=min((w*h)/(1024*1024),1.0); img.close(); return score
        except: return 0.5

    def score_all(self)->dict:
        """score all images in output directory"""
        results=[]
        if not self.output_dir.exists(): return {"images":[],"avg_score":0.0}
        for f in sorted(self.output_dir.glob("*.png")):
            fpath=str(f); fs=self._file_size_score(fpath);
            rs=self._resolution_score(fpath);
            total=0.6*fs+0.4*rs;
            results.append({"file":f.name,"size_score":round(fs,3),"resolution_score":round(rs,3),"total_score":round(total,3)})
            self.scores[fpath]=total
        avg=sum(r["total_score"] for r in results)/len(results) if results else 0.0
        return {"images":results,"avg_score":round(avg,3),"count":len(results)}

    def filter_by_score(self,min_score:float=0.3)->dict:
        """return images above minimum score threshold"""
        all_scored=self.score_all()
        passed=[i for i in all_scored["images"] if i["total_score"]>=min_score]
        failed=[i for i in all_scored["images"] if i["total_score"]<min_score]
        return {"total":all_scored["count"],"passed":len(passed),"failed":len(failed),"passed_images":passed,"failed_images":failed,"min_score":min_score}

    def get_top_n(self,n:int=150)->dict:
        """return top N images by quality score"""
        all_scored=self.score_all()
        sorted_images=sorted(all_scored["images"],key=lambda x:x["total_score"],reverse=True)
        top=sorted_images[:n]
        return {"top_n":n,"images":top,"avg_score":round(sum(i["total_score"] for i in top)/len(top),3) if top else 0.0}