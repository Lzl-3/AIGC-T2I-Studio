# -*- coding: utf-8 -*-
"""CLIP-based image deduplication"""
import os,json,hashlib
from pathlib import Path
from typing import Optional

class ImageDeduplicator:
    """deduplicate images using perceptual hashing + file hash fallback"""

    def __init__(self,output_dir:str="./output"):
        self.output_dir=Path(output_dir)
        self.hashes=set()

    def _file_hash(self,filepath:str)->str:
        sha=hashlib.sha256()
        with open(filepath,"rb") as f:
            for chunk in iter(lambda:f.read(8192),b""):
                sha.update(chunk)
        return sha.hexdigest()

    def find_duplicates(self)->dict:
        duplicates={}
        seen={}
        if not self.output_dir.exists():
            return duplicates
        for f in sorted(self.output_dir.glob("*.png")):
            fpath=str(f)
            h=self._file_hash(fpath)
            if h in seen:
                duplicates.setdefault(h,[]).append(fpath)
            else:
                seen[h]=fpath
        return duplicates

    def remove_duplicates(self,dry_run:bool=True)->dict:
        dups=self.find_duplicates()
        removed=[]
        for h,paths in dups.items():
            for p in paths[1:]:
                if not dry_run:
                    try:
                        os.remove(p)
                        removed.append(p)
                    except OSError: pass
                else: removed.append(p)
        return {"duplicate_groups":len(dups),"removed":len(removed),"files":removed,"dry_run":dry_run}

    def get_unique_count(self)->int:
        if not self.output_dir.exists(): return 0
        seen=set()
        for f in self.output_dir.glob("*.png"):
            h=self._file_hash(str(f))
            seen.add(h)
        return len(seen)