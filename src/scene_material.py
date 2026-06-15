# -*- coding: utf-8 -*-
"""场景 LoRA 训练素材生产室 - 独立后端模块"""
import asyncio, json, os, uuid, random, shutil, copy, logging
from datetime import datetime
from pathlib import Path
from typing import Optional
logger = logging.getLogger(__name__)

N_UNET="75:70"; N_CLIP="75:71"; N_VAE="75:72"; N_POSITIVE="75:74"
N_NEGATIVE="75:67"; N_WIDTH="75:68"; N_HEIGHT="75:69"; N_LATENT="75:66"
N_NOISE="75:73"; N_SCHEDULER="75:62"; N_GUIDER="75:63"; N_SAMPLER="75:64"
N_SAMPLER_SELECT="75:61"; N_SAVE="9"; N_VAE_DECODE="75:65"

SCENE_MATERIAL_ROOT=Path("data/scene_training_materials")
TEMPLATES_DIR=SCENE_MATERIAL_ROOT/"templates"
PREVIEWS_DIR=SCENE_MATERIAL_ROOT/"previews"
BATCHES_DIR=SCENE_MATERIAL_ROOT/"batches"
DEFAULT_MODEL="flux-2-klein-base-9b-fp8.safetensors"
DEFAULT_CLIP="qwen_3_8b_fp8mixed.safetensors"
DEFAULT_VAE="full_encoder_small_decoder.safetensors"
DEFAULT_STEPS=25; DEFAULT_CFG=3.5; DEFAULT_SAMPLER="euler"
DEFAULT_WIDTH=1344; DEFAULT_HEIGHT=768
SCENE_CATEGORIES=["修仙秘境","古风宫殿","现代都市","科幻未来","自然山水","室内场景","废墟战场","异域风情","暗黑魔界","仙侠宗门"]
SIZE_PRESETS={"16:9 横版":(1344,768),"4:3 横版":(1216,912),"1:1 方形":(1024,1024),"3:4 竖版":(912,1216),"9:16 竖版":(768,1344)}
def _ensure_dirs():
 for d in [SCENE_MATERIAL_ROOT,TEMPLATES_DIR,PREVIEWS_DIR,BATCHES_DIR]: d.mkdir(parents=True,exist_ok=True)
_ensure_dirs()

def _write_json(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 with open(path,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2)

def _write_txt(path,text):
 path.parent.mkdir(parents=True,exist_ok=True)
 with open(path,"w",encoding="utf-8") as f: f.write(text)

def _inject_scene_params(workflow,model,positive,negative,width,height,steps,cfg,seed_mode="random",seed=0):
 """显式注入参数到 Flux2 工作流节点"""
 if N_UNET in workflow: workflow[N_UNET]["inputs"]["unet_name"]=model
 if N_POSITIVE in workflow: workflow[N_POSITIVE]["inputs"]["text"]=positive
 if N_NEGATIVE in workflow: workflow[N_NEGATIVE]["inputs"]["text"]=negative
 if N_WIDTH in workflow: workflow[N_WIDTH]["inputs"]["value"]=width
 if N_HEIGHT in workflow: workflow[N_HEIGHT]["inputs"]["value"]=height
 if N_SCHEDULER in workflow: workflow[N_SCHEDULER]["inputs"]["steps"]=steps
 if N_GUIDER in workflow: workflow[N_GUIDER]["inputs"]["cfg"]=cfg
 final_seed=seed
 if N_NOISE in workflow:
  if seed_mode=="random" or seed==0: final_seed=random.randint(0,2**32-1)
  else: final_seed=seed
  workflow[N_NOISE]["inputs"]["noise_seed"]=final_seed
 if N_SAMPLER_SELECT in workflow: workflow[N_SAMPLER_SELECT]["inputs"]["sampler_name"]=DEFAULT_SAMPLER
 if N_SAVE in workflow: workflow[N_SAVE]["inputs"]["filename_prefix"]="scene_training"
 return workflow

async def _poll_result(client,prompt_id,timeout=600):
 elapsed=0; interval=2.0
 while elapsed<timeout:
  await asyncio.sleep(interval); elapsed+=interval
  try:
   history=await client.get_history(prompt_id)
   prompt_data=history.get(prompt_id)
   if prompt_data and "outputs" in prompt_data:
    for node_id,output in prompt_data["outputs"].items():
     if "images" in output:
      for img in output["images"]:
       return await client.download_image(img["filename"],img.get("subfolder",""),img.get("type","output"))
  except Exception: pass
 return None

# --- 模板管理 ---
def list_templates():
 templates=[]
 if TEMPLATES_DIR.exists():
  for f in sorted(TEMPLATES_DIR.glob("*.json")):
   try:
    data=json.loads(f.read_text(encoding="utf-8")); data["id"]=f.stem; templates.append(data)
   except Exception: pass
 return templates

def get_template(template_id):
 path=TEMPLATES_DIR/f"{template_id}.json"
 if not path.exists(): return None
 data=json.loads(path.read_text(encoding="utf-8")); data["id"]=path.stem
 return data

def save_template(data):
 tid=data.get("id") or str(uuid.uuid4())[:8]
 rec={"id":tid,"title":data.get("title","").strip(),"model":data.get("model",DEFAULT_MODEL),"width":data.get("width",DEFAULT_WIDTH),"height":data.get("height",DEFAULT_HEIGHT),"positive_prompt":data.get("positive_prompt","").strip(),"negative_prompt":data.get("negative_prompt","").strip(),"scene_category":data.get("scene_category",""),"seed_mode":data.get("seed_mode","random"),"seed":data.get("seed",0),"steps":data.get("steps",DEFAULT_STEPS),"cfg":data.get("cfg",DEFAULT_CFG),"workflow_key":data.get("workflow_key","flux2_klein_scene"),"updated_at":datetime.now().isoformat()}
 _write_json(TEMPLATES_DIR/f"{tid}.json",rec)
 return rec

def delete_template(template_id):
 path=TEMPLATES_DIR/f"{template_id}.json"
 if path.exists(): path.unlink(); return True
 return False

# --- 预览生成 ---
async def generate_preview(template_id,model=DEFAULT_MODEL,width=DEFAULT_WIDTH,height=DEFAULT_HEIGHT,positive_prompt="",negative_prompt="",seed_mode="random",seed=0,steps=DEFAULT_STEPS,cfg=DEFAULT_CFG):
 from src.comfyui_client import comfyui_client
 pd=PREVIEWS_DIR/template_id; pd.mkdir(parents=True,exist_ok=True)
 wp=Path("workflows/scene_training/flux2_klein_scene.json")
 if not wp.exists(): raise FileNotFoundError(f"工作流文件未找到: {wp}")
 workflow=json.loads(wp.read_text(encoding="utf-8"))
 workflow=_inject_scene_params(workflow,model,positive_prompt,negative_prompt,width,height,steps,cfg,seed_mode=seed_mode,seed=seed)
 fs=workflow[N_NOISE]["inputs"]["noise_seed"] if N_NOISE in workflow else seed
 client=comfyui_client; prompt_id=await client.submit_workflow(workflow)
 rp=await _poll_result(client,prompt_id)
 if not rp: raise RuntimeError("预览生成失败:ComfyUI 未返回结果")
 pfn=f"preview_{template_id}.png"
 shutil.copy2(rp,str(pd/pfn))
 meta={"template_id":template_id,"model":model,"width":width,"height":height,"positive_prompt":positive_prompt,"negative_prompt":negative_prompt,"seed_mode":seed_mode,"seed":fs,"steps":steps,"cfg":cfg,"generated_at":datetime.now().isoformat()}
 _write_json(pd/f"preview_{template_id}_metadata.json",meta)
 return {"ok":True,"template_id":template_id,"image_url":f"/scene_material/previews/{template_id}/{pfn}","seed":fs,"metadata":meta}

def get_preview_info(template_id):
 pd=PREVIEWS_DIR/template_id
 if not pd.exists(): return None
 pngs=list(pd.glob("*.png")); metas=list(pd.glob("*_metadata.json"))
 r={"template_id":template_id,"has_preview":len(pngs)>0}
 if pngs: r["image_url"]=f"/scene_material/previews/{template_id}/{pngs[0].name}"
 if metas:
  try: r["metadata"]=json.loads(metas[0].read_text(encoding="utf-8"))
  except Exception: pass
 return r

# --- 批量生成后台队列 ---
class SceneBatchQueue:
 def __init__(self):
  self._q=asyncio.Queue(); self._wt=None; self._running=False; self._active={}
 async def start(self):
  if not self._running: self._running=True; self._wt=asyncio.create_task(self._worker_loop())
 async def shutdown(self):
  self._running=False
  if self._wt and not self._wt.done(): self._wt.cancel()
  try: await self._wt
  except asyncio.CancelledError: pass
 async def submit(self,job):
  bid=job["batch_id"]; self._active[bid]={"status":"pending","total":job["total"],"completed":0,"failed":0}
  await self._q.put(job); return bid
 def get_status(self,bid): return self._active.get(bid)
 async def _worker_loop(self):
  while self._running:
   try: job=await asyncio.wait_for(self._q.get(),timeout=5.0)
   except asyncio.TimeoutError: continue
   bid=job["batch_id"]
   try: await self._process_batch(job)
   except Exception as e:
    logger.error(f"SceneBatchQueue 批量失败 {bid}: {e}")
    if bid in self._active: self._active[bid]["status"]="failed"; self._active[bid]["error"]=str(e)
 async def _process_batch(self,job):
  from src.comfyui_client import comfyui_client
  bid=job["batch_id"]; total=job["total"]; bd=BATCHES_DIR/bid
  info=self._active.get(bid)
  if info: info["status"]="running"
  wf=copy.deepcopy(job["workflow"]); client=comfyui_client
  for i in range(total):
   wf2=json.loads(json.dumps(wf,ensure_ascii=False))
   wf2=_inject_scene_params(wf2,job["model"],job["positive"],job["negative"],job["width"],job["height"],job["steps"],job["cfg"],seed_mode=job.get("seed_mode","random"),seed=job.get("seed",0))
   try:
    pid=await client.submit_workflow(wf2); rp=await _poll_result(client,pid)
    if rp:
     ix=f"{i+1:05d}"
     shutil.copy2(rp,str(bd/f"{ix}.png"))
     _write_json(bd/f"{ix}_metadata.json",{"batch_id":bid,"index":i+1,"model":job["model"],"width":job["width"],"height":job["height"],"positive_prompt":job["positive"],"negative_prompt":job["negative"],"steps":job["steps"],"cfg":job["cfg"],"generated_at":datetime.now().isoformat()})
     _write_txt(bd/f"{ix}_caption.txt",job["positive"])
     if info: info["completed"]=info.get("completed",0)+1
    else:
     if info: info["failed"]=info.get("failed",0)+1
   except Exception as e:
    logger.error(f"SceneBatchQueue 第{i+1}张失败: {e}")
    if info: info["failed"]=info.get("failed",0)+1
  _build_manifest(bd,bid,job.get("template_id",""),total)
  if info: info["status"]="completed"; info["finished_at"]=datetime.now().isoformat()

scene_batch_queue=SceneBatchQueue()

async def submit_batch(template_id,total=10,model=DEFAULT_MODEL,width=DEFAULT_WIDTH,height=DEFAULT_HEIGHT,positive_prompt="",negative_prompt="",seed_mode="random",seed=0,steps=DEFAULT_STEPS,cfg=DEFAULT_CFG):
 bid=datetime.now().strftime("%Y%m%d_%H%M%S_")+str(uuid.uuid4())[:8]
 bd=BATCHES_DIR/bid; bd.mkdir(parents=True,exist_ok=True)
 wp=Path("workflows/scene_training/flux2_klein_scene.json")
 if not wp.exists(): raise FileNotFoundError(f"工作流文件未找到: {wp}")
 workflow=json.loads(wp.read_text(encoding="utf-8"))
 workflow=_inject_scene_params(workflow,model,positive_prompt,negative_prompt,width,height,steps,cfg,seed_mode=seed_mode,seed=seed)
 _write_json(bd/"dataset_manifest.json",{"batch_id":bid,"template_id":template_id,"total":total,"generated_count":0,"failed_count":0,"created_at":datetime.now().isoformat(),"items":{}})
 job={"batch_id":bid,"template_id":template_id,"total":total,"model":model,"width":width,"height":height,"positive":positive_prompt,"negative":negative_prompt,"steps":steps,"cfg":cfg,"seed_mode":seed_mode,"seed":seed,"workflow":workflow}
 await scene_batch_queue.submit(job)
 return {"ok":True,"batch_id":bid,"total":total,"status":"pending"}

def get_batch_status(batch_id):
 s=scene_batch_queue.get_status(batch_id)
 if s: return s
 mp=BATCHES_DIR/batch_id/"dataset_manifest.json"
 if mp.exists():
  try:
   m=json.loads(mp.read_text(encoding="utf-8"))
   return {"batch_id":batch_id,"status":"completed","total":m.get("total",0),"completed":m.get("generated_count",0),"failed":m.get("failed_count",0)}
  except Exception: pass
 return None

# --- 训练集管理 ---
def get_batches():
 batches=[]
 if BATCHES_DIR.exists():
  for d in sorted(BATCHES_DIR.iterdir(),reverse=True):
   if d.is_dir():
    mp=d/"dataset_manifest.json"; m={}
    if mp.exists():
     try: m=json.loads(mp.read_text(encoding="utf-8"))
     except Exception: pass
    live=scene_batch_queue.get_status(d.name); pngs=len(list(d.glob("*.png")))
    batches.append({"batch_id":d.name,"template_id":m.get("template_id",""),"total":m.get("total",pngs),"generated_count":m.get("generated_count",pngs),"failed_count":m.get("failed_count",0),"status":live["status"] if live else "completed","completed":live["completed"] if live else pngs,"created_at":m.get("created_at","")})
 return batches

def get_batch_detail(batch_id):
 bd=BATCHES_DIR/batch_id
 if not bd.exists(): return None
 mp=bd/"dataset_manifest.json"; m={}
 if mp.exists():
  try: m=json.loads(mp.read_text(encoding="utf-8"))
  except Exception: pass
 items=m.get("items",{})
 imgs=[]
 for pf in sorted(bd.glob("*.png")):
  s=pf.stem; info=items.get(s,{})
  imgs.append({"filename":pf.name,"stem":s,"url":f"/scene_material/batches/{batch_id}/{pf.name}","approved":info.get("approved",False),"rejected":info.get("rejected",False),"used_for_training":info.get("used_for_training",False),"has_metadata":(bd/f"{s}_metadata.json").exists(),"has_caption":(bd/f"{s}_caption.txt").exists()})
 return {"batch_id":batch_id,"template_id":m.get("template_id",""),"total":m.get("total",len(imgs)),"generated_count":m.get("generated_count",len(imgs)),"created_at":m.get("created_at",""),"images":imgs}

def update_item_status(batch_id,stem,status,value):
 bd=BATCHES_DIR/batch_id; mp=bd/"dataset_manifest.json"
 if not mp.exists(): return False
 d=json.loads(mp.read_text(encoding="utf-8"))
 items=d.setdefault("items",{})
 if stem not in items: return False
 if status=="approved": items[stem]["approved"]=value
 if value: items[stem]["rejected"]=False
 elif status=="rejected": items[stem]["rejected"]=value
 if value: items[stem]["approved"]=False
 elif status=="used_for_training": items[stem]["used_for_training"]=value
 _write_json(mp,d); return True

def get_scene_categories(): return SCENE_CATEGORIES
def get_size_presets(): return SIZE_PRESETS

def export_approved(batch_id):
 bd=BATCHES_DIR/batch_id
 if not bd.exists(): return {"ok":False,"error":"批次不存在"}
 mp=bd/"dataset_manifest.json"
 if not mp.exists(): return {"ok":False,"error":"无 manifest"}
 d=json.loads(mp.read_text(encoding="utf-8"))
 items=d.get("items",{})
 ed=bd/"approved_export"; ed.mkdir(exist_ok=True)
 exported=[]
 for stem,info in items.items():
  if info.get("approved"):
   src=bd/f"{stem}.png"
   if src.exists():
    shutil.copy2(str(src),str(ed/f"{stem}.png"))
    for ext in ["_metadata.json","_caption.txt"]:
     aux=bd/f"{stem}{ext}"
     if aux.exists(): shutil.copy2(str(aux),str(ed/f"{stem}{ext}"))
    exported.append(stem)
 return {"ok":True,"count":len(exported),"export_dir":str(ed),"items":exported}

def _build_manifest(bd,bid,template_id,total):
 items={}
 for pf in sorted(bd.glob("*.png")):
  s=pf.stem; items[s]={"approved":False,"rejected":False,"used_for_training":False}
 omp=bd/"dataset_manifest.json"
 if omp.exists():
  try:
   old=json.loads(omp.read_text(encoding="utf-8"))
   for stem,info in old.get("items",{}).items():
    if stem in items:
     items[stem]["approved"]=info.get("approved",False)
     items[stem]["rejected"]=info.get("rejected",False)
     items[stem]["used_for_training"]=info.get("used_for_training",False)
  except Exception: pass
 _write_json(omp,{"batch_id":bid,"template_id":template_id,"total":total,"generated_count":len(items),"failed_count":total-len(items),"created_at":datetime.now().isoformat(),"items":items})
