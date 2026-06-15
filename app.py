# -*- coding: utf-8 -*-
"""AIGC T2I Studio - FastAPI 主入口"""

import asyncio
import json
import uuid
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Query, UploadFile
from fastapi.responses import (
    HTMLResponse, FileResponse, StreamingResponse, JSONResponse
)
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
import logging

logger = logging.getLogger(__name__)

from config.settings import settings
from src.models import GenerationRequest, TaskStatus, WorkflowType, GenreType
from src.db import list_tasks as db_list_tasks
from src.task_manager import task_manager
from src.comfyui_client import comfyui_client
# FLUX_MODEL / ZIMAGE_MODEL now auto-detected via detect_model_type()
from src.workflow_engine import detect_model_type
from src.character_presets import list_presets
from src.cards import (
    list_all_cards, get_card, create_card, update_card,
    delete_card, lock_card, unlock_card, CARDS_DIR
)

import src.scene_material as sm

# ============================================================
# 加载角色扩展包（独立文件，不影响内置角色）
# 删掉 src/character_addons.py 即可回退到内置 7 个角色
# ============================================================
try:
    from src.character_addons import CHARACTER_ADDON_LAYERS, CHARACTER_ADDON_PRESETS
    from src.character_presets import CHARACTER_LAYERS, CHARACTER_PRESETS
    CHARACTER_LAYERS.update(CHARACTER_ADDON_LAYERS)
    CHARACTER_PRESETS.update(CHARACTER_ADDON_PRESETS)
    print(f'[Addons] 已加载 {len(CHARACTER_ADDON_LAYERS)} 个扩展角色')
except ImportError:
    pass  # 没有扩展包时静默跳过




@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    await task_manager.start()
    from src.scene_material import scene_batch_queue
    await scene_batch_queue.start()
    # 启动时自动迁移旧预设到模板目录
    try:
        TemplateManager.migrate_builtin_presets()
    except Exception:
        pass
    yield
    await task_manager.shutdown()
    await scene_batch_queue.shutdown()
    await comfyui_client.close()


app = FastAPI(
    title="AIGC T2I Studio",
    version="2.0.0",
    lifespan=lifespan,
)

# 静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/output", StaticFiles(directory="output"), name="output")

# 上传目录
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory="data/uploads"), name="uploads")

# 场景训练素材静态目录
app.mount("/scene_material/previews", StaticFiles(directory="data/scene_training_materials/previews"), name="scene_material_previews")
app.mount("/scene_material/batches", StaticFiles(directory="data/scene_training_materials/batches"), name="scene_material_batches")


# ========== 页面路由 ==========

@app.get("/", response_class=HTMLResponse)
async def index():
    """首页"""
    html_path = Path("static/index.html")
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")
    return "<h1>AIGC T2I Studio</h1><p>static/index.html 未找到</p>"


# ========== API 接口 ==========

@app.get("/api/health")
async def health_check():
    """健康检查 + ComfyUI 连接状态"""
    try:
        comfyui_alive = await asyncio.wait_for(comfyui_client.check_server_alive(), timeout=5.0)
    except (asyncio.TimeoutError, Exception):
        comfyui_alive = False
    return {
        "status": "ok",
        "comfyui_connected": comfyui_alive,
        "comfyui_url": settings.comfyui_base_url,
    }


@app.get("/api/models")
async def get_models():
    """ComfyUI models - fast offline fallback"""
    try:
        alive = await asyncio.wait_for(comfyui_client.check_server_alive(), timeout=8.0)
    except (asyncio.TimeoutError, Exception):
        alive = False
    if not alive:
        return {"models": [], "vaes": [], "clips": [], "loras": [], "error": "ComfyUI not connected"}
    async def safe_fetch(fn):
        try:
            return await fn()
        except Exception:
            return []
    models, vaes, clips, loras = await asyncio.gather(
        safe_fetch(comfyui_client.get_available_models),
        safe_fetch(comfyui_client.get_available_vaes),
        safe_fetch(comfyui_client.get_available_clips),
        safe_fetch(comfyui_client.get_available_loras),
    )
    # Also fetch UNET models (Flux etc.) from UNETLoader
    unet_models = await safe_fetch(comfyui_client.get_available_unet_models)
    for m in unet_models:
        if m not in models:
            models.append(m)
        # 为每个模型附加架构类型标签
    models_with_type = [{"name": m, "type": detect_model_type(m)} for m in models]
    return {"models": models_with_type, "vaes": vaes, "clips": clips, "loras": loras}
@app.get("/api/character-presets")
async def get_character_presets():
    """获取角色预设列表（名称和描述）"""
    presets = list_presets()
    return {"presets": presets}


@app.post("/api/generate")
async def submit_generation(request: GenerationRequest, card_id: str = Query(None)):
    """提交生成任务，可选关联工作流卡片"""
    if not await comfyui_client.check_server_alive():
        raise HTTPException(
            status_code=503,
            detail=f"ComfyUI 服务器未连接，请确认 {settings.comfyui_base_url} 可访问",
        )
    # 如果指定了卡片，用卡片参数覆盖默认值
    if card_id:
        card = get_card(card_id)
        if card:
            if not request.model_name and card.get("checkpoint"):
                request.model_name = card["checkpoint"]
                request.model_type = card.get("model_type") or detect_model_type(card["checkpoint"])
        else:
            raise HTTPException(status_code=404, detail="卡片不存在")
    if not request.model_name:
        models = await comfyui_client.get_available_models()
        if models:
            request.model_name = models[0]
    # Auto-detect model type from checkpoint name (checkpoint -> model_type -> workflow)
    if request.model_name and not request.model_type:
        request.model_type = detect_model_type(request.model_name)
    request.apply_model_defaults()
    task_id = await task_manager.submit_task(request, card_id)
    return {"task_id": task_id, "status": "pending"}


@app.post("/api/upload")
async def api_upload_image(file: UploadFile):
    """上传图片到本地服务器"""
    allowed_types = {"image/png", "image/jpeg", "image/webp", "image/gif"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="仅支持 PNG/JPEG/WebP/GIF")

    ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "png"
    safe_name = f"{uuid.uuid4().hex[:12]}.{ext}"
    file_path = UPLOAD_DIR / safe_name
    content_bytes = await file.read()
    file_path.write_bytes(content_bytes)
    return {
        "filename": safe_name,
        "path": f"data/uploads/{safe_name}",
        "url": f"/uploads/{safe_name}"
    }


@app.get("/api/tasks")
async def api_list_tasks(status: str = Query(None)):
    """任务列表"""
    tasks = await task_manager.list_all_tasks(status)
    return {"tasks": tasks, "total": len(tasks)}


@app.get("/api/tasks/{task_id}")
async def api_get_task(task_id: str):
    """获取单个任务详情（含子任务）"""
    task = await task_manager.get_task_detail(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@app.delete("/api/tasks/{task_id}")
async def api_cancel_task(task_id: str):
    """取消任务"""
    await task_manager.cancel_task(task_id)
    return {"status": "cancelled"}


@app.get("/api/output")
async def api_browse_output(
    genre: str = Query(None),
    category: str = Query(None),
    search: str = Query(None),
):
    """浏览输出目录的生成图片"""
    output_dir = Path(settings.output_dir)
    if not output_dir.exists():
        return {"files": []}

    files = []
    for png_file in output_dir.rglob("*.png"):
        rel_path = str(png_file.relative_to(output_dir)).replace('\\', "/")
        rel_lower = rel_path.lower()
        if genre and genre not in rel_lower:
            continue
        if category and category not in rel_lower:
            continue
        if search and search.lower() not in rel_lower:
            continue
        txt_file = png_file.with_suffix(".txt")
        has_label = txt_file.exists()
        files.append({
            "path": rel_path,
            "filename": png_file.name,
            "has_label": has_label,
            "size_bytes": png_file.stat().st_size,
            "mtime": png_file.stat().st_mtime,
        })
    files.sort(key=lambda x: x["path"], reverse=True)
    return {"files": files}


@app.get("/api/output/label")
async def api_get_label(path: str = Query(...)):
    """获取图片对应的正向提示词标签"""
    label_path = Path(settings.output_dir) / path.replace(".png", ".txt")
    if not label_path.exists():
        raise HTTPException(status_code=404, detail="标签文件不存在")
    return {"content": label_path.read_text(encoding="utf-8")}


@app.get("/api/output/structure")
async def api_output_structure():
    """获取输出目录结构（文件夹树）"""
    output_dir = Path(settings.output_dir)
    if not output_dir.exists():
        return {"structure": []}

    def build_tree(path: Path, depth: int = 0) -> list:
        if depth > 3:
            return []
        items = []
        for child in sorted(path.iterdir()):
            if child.is_dir():
                items.append({
                    "type": "folder",
                    "name": child.name,
                    "path": str(child.relative_to(output_dir)),
                    "children": build_tree(child, depth + 1),
                })
            elif child.suffix.lower() == ".png":
                items.append({
                    "type": "file",
                    "name": child.name,
                    "path": str(child.relative_to(output_dir)),
                })
        return items

    return {"structure": build_tree(output_dir)}


@app.delete("/api/output/delete")
async def api_delete_output(path: str = Query(...)):
    """删除输出图片及其标签文件"""
    full_path = Path(settings.output_dir) / path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    try:
        full_path.resolve().relative_to(Path(settings.output_dir).resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="路径越权")
    full_path.unlink()
    txt_path = full_path.with_suffix(".txt")
    if txt_path.exists():
        txt_path.unlink()
    return {"status": "deleted", "path": path}


# ========== Candidate Selection API ==========

@app.post("/api/candidates/select")
async def api_select_candidate(request: dict):
    summary_path = request.get("candidates_summary_path", "")
    selected_index = request.get("selected_index", 1)
    if not summary_path:
        raise HTTPException(status_code=400, detail="missing candidates_summary_path")
    summary_file = Path(summary_path)
    if not summary_file.exists():
        raise HTTPException(status_code=404, detail="summary file not found")
    try:
        summary = json.loads(summary_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invalid JSON")
    candidates = summary.get("candidates", [])
    selected = next((c for c in candidates if c["index"] == selected_index), None)
    if not selected:
        raise HTTPException(status_code=404, detail="candidate not found")
    summary["selected_index"] = selected_index
    summary_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    subtask_id = summary.get("subtask_id", "")
    if subtask_id:
        import aiosqlite
        from src.db import DB_PATH
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE subtasks SET image_path = ? WHERE subtask_id = ?", (selected["image_path"], subtask_id))
            await db.commit()
    return {"status": "selected", "selected_index": selected_index, "image_path": selected["image_path"], "seed": selected["seed"], "subtask_id": subtask_id}

@app.get("/api/candidates/{subtask_id}")
async def api_get_candidates(subtask_id: str):
    output_root = Path(settings.output_dir)
    for cf in output_root.rglob("*_candidates.json"):
        try:
            s = json.loads(cf.read_text(encoding="utf-8"))
            if s.get("subtask_id") == subtask_id:
                return s
        except: continue
    raise HTTPException(status_code=404, detail="not found")

# ========== 工作流卡片 API ==========

@app.get("/api/cards")
async def api_list_cards(category: str = Query(None)):
    """列出所有工作流卡片"""
    cards = list_all_cards(category or "")
    return {"cards": cards, "total": len(cards)}


@app.get("/api/cards/{card_id}")
async def api_get_card(card_id: str):
    """获取单张卡片详情"""
    card = get_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="卡片不存在")
    return card


@app.post("/api/cards")
async def api_create_card(data: dict):
    """创建新工作流卡片"""
    try:
        card = create_card(data)
        return card.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"创建卡片失败: {str(e)}")


@app.put("/api/cards/{card_id}")
async def api_update_card(card_id: str, data: dict):
    """更新工作流卡片（锁定状态仅允许修改备注）"""
    card = update_card(card_id, data)
    if not card:
        raise HTTPException(status_code=404, detail="卡片不存在")
    return card.to_dict()


@app.delete("/api/cards/{card_id}")
async def api_delete_card(card_id: str):
    """删除工作流卡片"""
    ok = delete_card(card_id)
    if not ok:
        raise HTTPException(status_code=404, detail="卡片不存在")
    return {"status": "deleted"}


@app.post("/api/cards/{card_id}/lock")
async def api_lock_card(card_id: str, data: dict = None):
    """锁定卡片（验图通过后执行）"""
    notes = data.get("notes", "") if data else ""
    card = lock_card(card_id, notes)
    if not card:
        raise HTTPException(status_code=404, detail="卡片不存在")
    return card.to_dict()


@app.post("/api/cards/{card_id}/unlock")
async def api_unlock_card(card_id: str):
    """解锁卡片（回到测试状态）"""
    card = unlock_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="卡片不存在")
    return card.to_dict()


# ========== SSE 推送 ==========

@app.get("/api/events")
async def sse_events(request: Request):
    """SSE 事件推送：任务进度实时更新"""
    client_queue = await task_manager.subscribe_sse()

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(
                        client_queue.get(), timeout=15.0
                    )
                    yield {
                        "event": event.get("type", "message"),
                        "data": json.dumps(event, ensure_ascii=False),
                    }
                except asyncio.TimeoutError:
                    yield {"event": "heartbeat", "data": "ping"}
        finally:
            task_manager.unsubscribe_sse(client_queue)

    return EventSourceResponse(event_generator())


# ============================================================
# Prompt 工作室 API
# ============================================================

from src.qwen_prompt import pipeline
from src.models import (
    PromptPolishRequest, PromptPolishResult,
    PromptConvertRequest, PromptConvertResult,
    PromptGenerateRequest,
)


@app.get("/prompt-studio")
async def prompt_studio_page():
    """Prompt 工作室页面"""
    return FileResponse("static/prompt-studio.html")


@app.post("/api/prompt/polish", response_model=PromptPolishResult)
async def prompt_polish(request: PromptPolishRequest):
    """阶段1：粗糙中文 -> Qwen 润色 -> 标准中文"""
    return await pipeline.polish(request.idea)


@app.post("/api/prompt/convert", response_model=PromptConvertResult)
async def prompt_convert(request: PromptConvertRequest):
    """阶段2：标准中文 -> Qwen 翻译 -> ComfyUI 英文标签 JSON"""
    return await pipeline.convert(request.chinese_prompt)


async def prompt_describe_image(request: dict):
    """上传图片 -> Qwen 视觉分析 -> 中文描述 + ComfyUI 英文标签
    
    POST body: {"image_base64": "...", "image_mime": "image/png"}
    """
    image_b64 = request.get("image_base64", "").strip()
    if not image_b64:
        raise HTTPException(status_code=400, detail="请提供图片数据")
    
    # 去掉可能的 data:image/...;base64, 前缀
    if "," in image_b64 and image_b64.startswith("data:"):
        image_b64 = image_b64.split(",", 1)[1]
    
    image_mime = request.get("image_mime", "image/png")
    
    try:
        result = await pipeline.describe_image(image_b64, image_mime)
        return result
    except Exception as e:
        logger.error(f"图片分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"图片分析失败: {str(e)[:200]}")

async def prompt_generate(request: PromptGenerateRequest):
    """鑻辨枃 Prompt -> 鎻愪氦 ComfyUI 鐢熸垚浠诲姟"""
    if not await comfyui_client.check_server_alive():
        raise HTTPException(status_code=503, detail="ComfyUI 鏈嶅姟鍣ㄦ湭杩炴帴")
    
    category_map = {
        "character": WorkflowType.CHARACTER,
        "costume": WorkflowType.COSTUME,
        "scene": WorkflowType.SCENE,
        "img2img": WorkflowType.IMG2IMG,
    }
    category = category_map.get(request.workflow_type, WorkflowType.CHARACTER)
    
    gen_req = GenerationRequest(
        category=category,
        genre=GenreType.XIANXIA,
        project_name="Prompt Studio",
        batch_prompts=[request.positive] if request.positive else [],
        free_negative=request.negative,
        width=request.params.get("width", 512),
        height=request.params.get("height", 768),
    )

    task_id = await task_manager.submit_task(gen_req)
    return {"task_id": task_id, "status": "queued"}


# ============================================================
# 角色卡片装扮系统 API
# ============================================================

from src.cards import (
    get_card_costumes, add_card_costume, update_card_costume,
    activate_card_costume, delete_card_costume, update_card_identity,
    get_card_combined_prompt,
)


@app.get("/api/cards/{card_id}/costumes")
async def api_get_card_costumes(card_id: str):
    """获取卡片的所有装扮信息"""
    result = get_card_costumes(card_id)
    if result is None:
        raise HTTPException(status_code=404, detail="卡片不存在")
    return result


@app.post("/api/cards/{card_id}/costumes")
async def api_add_card_costume(card_id: str, costume: dict):
    """添加新装扮到装扮库"""
    result = add_card_costume(card_id, costume)
    if result is None:
        raise HTTPException(status_code=404, detail="卡片不存在或已被锁定")
    return result


@app.put("/api/cards/{card_id}/costumes/{index}")
async def api_update_card_costume(card_id: str, index: int, costume: dict):
    """更新装扮库中指定索引的装扮"""
    result = update_card_costume(card_id, index, costume)
    if result is None:
        raise HTTPException(status_code=404, detail="卡片不存在或索引无效")
    return result


@app.post("/api/cards/{card_id}/costumes/{index}/activate")
async def api_activate_card_costume(card_id: str, index: int):
    """切换激活装扮"""
    result = activate_card_costume(card_id, index)
    if result is None:
        raise HTTPException(status_code=404, detail="卡片不存在或索引无效")
    return result


@app.delete("/api/cards/{card_id}/costumes/{index}")
async def api_delete_card_costume(card_id: str, index: int):
    """删除装扮库中的装扮"""
    result = delete_card_costume(card_id, index)
    if result is None:
        raise HTTPException(status_code=400, detail="删除失败：卡片不存在、索引无效或至少保留一个装扮")
    return result


@app.put("/api/cards/{card_id}/identity")
async def api_update_card_identity(card_id: str, identity: dict):
    """更新卡片身份信息"""
    result = update_card_identity(card_id, identity)
    if result is None:
        raise HTTPException(status_code=400, detail="更新失败：卡片不存在或已被锁定")
    return result


@app.get("/api/cards/{card_id}/combined-prompt")
async def api_get_combined_prompt(card_id: str):
    """获取身份+装扮合并的 Prompt 参数"""
    result = get_card_combined_prompt(card_id)
    if result is None:
        raise HTTPException(status_code=404, detail="卡片不存在")
    return result


# ============================================================
# 训练素材工作室 API
# ============================================================

from src.character_presets import list_training_identities
from src.training_library import get_all_dimensions
from src.training_material import MaterialBatchGenerator, get_strategy_summary


@app.get("/api/training/identity-presets")
async def api_training_identity_presets():
    """获取纯身份预设列表（仅 脸/发型/气质，不含服装/武器）。"""
    return {"identities": list_training_identities()}


@app.get("/api/training/library")
async def api_training_library():
    """获取训练素材变体库（服装/武器/背景/构图/角度/表情/动作）及其策略比例。"""
    return get_all_dimensions()


@app.get("/api/training/strategy")
async def api_training_strategy():
    """获取训练策略摘要。"""
    return get_strategy_summary()


@app.post("/api/training/material/preview")
async def api_training_material_preview(request: dict):
    """预览训练素材 Prompt 列表（不提交生成）。
    
    请求体: {"identity_key": "Lin Xiaoxiao", "total": 150, "model_type": "sdxl"}
    """
    identity_key = request.get("identity_key", "")
    total = request.get("total", 150)
    model_type = request.get("model_type", "sdxl")  # sdxl / flux / zimage
    
    if not identity_key:
        raise HTTPException(status_code=400, detail="请选择角色")
    if total < 10 or total > 500:
        raise HTTPException(status_code=400, detail="素材数量需在 10-500 之间")
    
    try:
        gen = MaterialBatchGenerator(identity_key, total=total, model_type=model_type)
        prompts = gen.preview_prompts()
        return {
            "identity_key": identity_key,
            "identity_name": gen.identity.get("name", identity_key),
            "total": total,
            "prompts": prompts,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/training/material/generate")
async def api_training_material_generate(request: dict):
    """批量提交训练素材生成任务。
    
    请求体: {"identity_key": "Lin Xiaoxiao", "total": 150, "batch_size": 10}
    """
    if not await comfyui_client.check_server_alive():
        raise HTTPException(status_code=503, detail="ComfyUI 服务器未连接")
    
    identity_key = request.get("identity_key", "")
    total = request.get("total", 150)
    batch_size = request.get("batch_size", 10)
    model_type = request.get("model_type", "sdxl")  # sdxl / flux / zimage
    
    if not identity_key:
        raise HTTPException(status_code=400, detail="请选择角色")
    if total < 10 or total > 500:
        raise HTTPException(status_code=400, detail="素材数量需在 10-500 之间")

    try:
        gen = MaterialBatchGenerator(identity_key, total=total, batch_size=batch_size, model_type=model_type)
        requests = gen.generate_requests()

        task_ids = []
        for req in requests:
            task_id = await task_manager.submit_task(req)
            task_ids.append(task_id)

        return {
            "identity_name": gen.identity.get("name", identity_key),
            "total_images": total,
            "batches": len(task_ids),
            "task_ids": task_ids,
            "status": "queued",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"训练素材生成失败: {str(e)}")


# ============================================================
# 风格标签库 API
# ============================================================

from src.style_tags import get_all_tags, get_all_presets, merge_tags


@app.get("/api/style-tags")
async def api_style_tags():
    """获取风格标签库（7大类 + 预设模板）。"""
    return {
        "categories": get_all_tags(),
        "presets": get_all_presets(),
    }


async def api_character_layers(name: str = Query(None)):
    """获取角色的结构化8层数据。不传name则返回所有角色摘要。"""
    if name:
        layers = get_character_layers(name)
        if layers is None:
            raise HTTPException(status_code=404, detail="角色不存在")
        return {"name": name, "layers": layers}
    return {"characters": list_character_layers()}


async def api_update_character(name: str, update: dict):
    """更新角色结构化层数据（运行时修改，不持久化到文件）。
    
    请求体: {"layer_key": "face", "value": {...}}  或  {"layer_key": "temperament", "value": "新气质"}
    """
    layer_key = update.get("layer_key", "")
    value = update.get("value")
    if not layer_key:
        raise HTTPException(status_code=400, detail="请指定 layer_key")
    
    success = update_character_layer(name, layer_key, value)
    if not success:
        raise HTTPException(status_code=400, detail="更新失败：角色不存在或层名无效")
    
    return {"status": "ok", "name": name, "layer_key": layer_key}


async def api_build_structured_prompt(request: dict):
    """从结构化层 + 风格标签构建完整 Prompt。
    
    请求体: {"name": "Lin Xiaoxiao", "style_tags": ["8K超清", "电影级光影"], "overrides": {"face": {...}}}
    """
    name = request.get("name", "")
    style_tags = request.get("style_tags", [])
    custom_style = request.get("custom_style", "")
    overrides = request.get("overrides", {})
    
    if not name:
        raise HTTPException(status_code=400, detail="请指定角色名")
    
    # 应用临时覆盖
    if overrides:
        layers = get_character_layers(name)
        if layers:
            for key, val in overrides.items():
                if key in layers:
                    layers[key] = val
    
    prompt = build_structured_prompt(name, style_tags, custom_style)
    if prompt is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    
    return {"name": name, "prompt": prompt, "style_tags": style_tags, "custom_style": custom_style}


# ============================================================
from src.style_tags import get_all_tags, get_all_presets, merge_tags


@app.get("/api/style-tags")
async def api_style_tags():
    """获取风格标签库（7大类 + 预设模板）。"""
    return {
        "categories": get_all_tags(),
        "presets": get_all_presets(),
    }


async def api_character_layers(name: str = Query(None)):
    """获取角色的结构化8层数据。不传name则返回所有角色摘要。"""
    if name:
        layers = get_character_layers(name)
        if layers is None:
            raise HTTPException(status_code=404, detail="角色不存在")
        return {"name": name, "layers": layers}
    return {"characters": list_character_layers()}


async def api_update_character(name: str, update: dict):
    """更新角色结构化层数据（运行时修改，不持久化到文件）。
    
    请求体: {"layer_key": "face", "value": {...}}  或  {"layer_key": "temperament", "value": "新气质"}
    """
    layer_key = update.get("layer_key", "")
    value = update.get("value")
    if not layer_key:
        raise HTTPException(status_code=400, detail="请指定 layer_key")
    
    success = update_character_layer(name, layer_key, value)
    if not success:
        raise HTTPException(status_code=400, detail="更新失败：角色不存在或层名无效")
    
    return {"status": "ok", "name": name, "layer_key": layer_key}


async def api_build_structured_prompt(request: dict):
    """从结构化层 + 风格标签构建完整 Prompt。
    
    请求体: {"name": "Lin Xiaoxiao", "style_tags": ["8K超清", "电影级光影"], "overrides": {"face": {...}}}
    """
    name = request.get("name", "")
    style_tags = request.get("style_tags", [])
    custom_style = request.get("custom_style", "")
    overrides = request.get("overrides", {})
    
    if not name:
        raise HTTPException(status_code=400, detail="请指定角色名")
    
    # 应用临时覆盖
    if overrides:
        layers = get_character_layers(name)
        if layers:
            for key, val in overrides.items():
                if key in layers:
                    layers[key] = val
    
    prompt = build_structured_prompt(name, style_tags, custom_style)
    if prompt is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    
    return {"name": name, "prompt": prompt, "style_tags": style_tags, "custom_style": custom_style}


# ============================================================
# 服道化素材工作室 统一 API


# ============================================================
# 服道化素材工作室 统一 API
# ============================================================

from src.fudaohua_presets import (
    list_costumes, list_props, list_makeups,
    get_costume, get_prop, get_makeup, BASE_MODELS,
)
from src.fudaohua_engine import FudaohuaEngine
from src.fudaohua_templates import TemplateManager, list_templates, save_template, delete_template, get_template

VALID_FDH_TYPES = ("costume", "prop", "makeup")
_active_fdh_engines = {}


@app.get("/api/fudaohua/presets")
async def api_fudaohua_presets():
    """Get all presets for costume/prop/makeup + base models"""
    return {
        "costume": list_costumes(),
        "prop": list_props(),
        "makeup": list_makeups(),
        "_models": BASE_MODELS,
    }


@app.post("/api/fudaohua/preview")
async def api_fudaohua_preview(request: dict):
    """Generate 1 preview image"""
    if not await comfyui_client.check_server_alive():
        raise HTTPException(status_code=503, detail="ComfyUI not connected")
    preset_type = request.get("type", "costume")
    preset_id = request.get("preset_id", "")
    positive_template = request.get("positive_template", "")
    negative_prompt = request.get("negative_prompt", "")
    request_title = request.get("title", "")
    base_model = request.get("base_model", "flux2_klein_9b")
    seed = request.get("seed", 0) or None
    if preset_type not in VALID_FDH_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid type: {preset_type}")
    if not preset_id and not positive_template:
        raise HTTPException(status_code=400, detail="Preset or template required")
    try:
        engine = FudaohuaEngine(
            preset_type=preset_type, preset_id=preset_id,
            total=1, batch_size=1,
            base_model=base_model, seed=seed,
            positive_template=positive_template,
            negative_prompt=negative_prompt,
            request_title=request_title,
        )
        req = engine.build_preview_request()
        task_id = await task_manager.submit_task(req)
        _active_fdh_engines[task_id] = engine
        return {
            "task_id": task_id,
            "preset_type": preset_type,
            "preset_name": engine.preset["name_cn"],
            "status": "queued",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/fudaohua/repreview")
async def api_fudaohua_repreview(request: dict):
    """Re-generate preview with different seed"""
    return await api_fudaohua_preview(request)


@app.post("/api/fudaohua/prompts")
async def api_fudaohua_prompts(request: dict):
    """Preview prompt list without submitting tasks"""
    preset_type = request.get("type", "costume")
    preset_id = request.get("preset_id", "")
    positive_template = request.get("positive_template", "")
    negative_prompt = request.get("negative_prompt", "")
    request_title = request.get("title", "")
    total = request.get("total", 200)
    preview_count = min(total, request.get("preview_count", 30))
    seed = request.get("seed", 0) or None
    if preset_type not in VALID_FDH_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid type: {preset_type}")
    if not preset_id and not positive_template:
        raise HTTPException(status_code=400, detail="Preset or template required")
    try:
        engine = FudaohuaEngine(
            preset_type=preset_type, preset_id=preset_id,
            total=preview_count, batch_size=10, seed=seed,
            positive_template=positive_template,
            negative_prompt=negative_prompt,
            request_title=request_title,
        )
        prompts = engine.build_preview_prompts_text()
        return {
            "preset_type": preset_type,
            "preset_name": engine.preset["name_cn"],
            "total": len(prompts),
            "prompts": prompts,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/fudaohua/generate")
async def api_fudaohua_generate(request: dict):
    """Batch submit training material generation"""
    if not await comfyui_client.check_server_alive():
        raise HTTPException(status_code=503, detail="ComfyUI not connected")
    preset_type = request.get("type", "costume")
    preset_id = request.get("preset_id", "")
    positive_template = request.get("positive_template", "")
    negative_prompt = request.get("negative_prompt", "")
    request_title = request.get("title", "")
    total = request.get("total", 200)
    batch_size = request.get("batch_size", 10)
    base_model = request.get("base_model", "flux2_klein_9b")
    seed = request.get("seed", 0) or None
    if preset_type not in VALID_FDH_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid type: {preset_type}")
    if not preset_id and not positive_template:
        raise HTTPException(status_code=400, detail="Preset or template required")
    if total < 10 or total > 1000:
        raise HTTPException(status_code=400, detail="Total must be 10-1000")
    try:
        engine = FudaohuaEngine(
            preset_type=preset_type, preset_id=preset_id,
            total=total, batch_size=batch_size,
            base_model=base_model, seed=seed,
            positive_template=positive_template,
            negative_prompt=negative_prompt,
            request_title=request_title,
        )
        requests_list = engine.build_generation_requests()
        task_ids = []
        for req in requests_list:
            tid = await task_manager.submit_task(req)
            task_ids.append(tid)
        group_id = engine._task_group_id
        _active_fdh_engines[group_id] = engine
        return {
            "preset_type": preset_type,
            "preset_name": engine.preset["name_cn"],
            "total_images": engine.total,
            "batches": len(requests_list),
            "task_ids": task_ids,
            "task_group_id": group_id,
            "status": "queued",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generate failed: {str(e)}")


@app.post("/api/fudaohua/stop")
async def api_fudaohua_stop(request: dict):
    """Stop generation"""
    task_group_id = request.get("task_group_id", "")
    task_ids = request.get("task_ids", [])
    cancelled = 0
    for tid in task_ids:
        if await task_manager.cancel_task(tid):
            cancelled += 1
    if task_group_id in _active_fdh_engines:
        del _active_fdh_engines[task_group_id]
    return {"ok": True, "cancelled": cancelled}


@app.post("/api/fudaohua/export")
async def api_fudaohua_export(request: dict):
    """Export training dataset"""
    preset_type = request.get("type", "costume")
    preset_id = request.get("preset_id", "")
    if not preset_id:
        raise HTTPException(status_code=400, detail="Preset required")
    return {
        "ok": True,
        "preset_type": preset_type,
        "preset_id": preset_id,
        "message": "Export ready",
    }


@app.post("/api/fudaohua/quality")
async def api_fudaohua_quality(request: dict):
    """Quality scoring (placeholder)"""
    return {"ok": True, "message": "Quality scoring ready", "scores": []}


@app.post("/api/fudaohua/dedup")
async def api_fudaohua_dedup(request: dict):
    """Auto dedup (placeholder)"""
    return {"ok": True, "message": "Dedup ready", "duplicates": []}


@app.post("/api/fudaohua/filter")
async def api_fudaohua_filter(request: dict):
    """Filter low quality (placeholder)"""
    threshold = request.get("threshold", 0.5)
    return {"ok": True, "message": "Filter ready", "threshold": threshold, "kept": 0}




# ============================================================
# 服道化模板管理 API

@app.get("/api/fudaohua/templates")
async def api_fudaohua_templates(preset_type: str = "costume"):
    """获取指定类型的模板列表"""
    return {"templates": list_templates(preset_type)}


@app.post("/api/fudaohua/template/save")
async def api_fudaohua_template_save(request: dict):
    """保存模板（同标题覆盖）"""
    preset_type = request.get("type", "costume")
    title = request.get("title", "").strip()
    positive_template = request.get("positive_template", "").strip()
    negative_prompt = request.get("negative_prompt", "").strip()

    if not title:
        raise HTTPException(status_code=400, detail="标题不能为空")
    if not positive_template:
        raise HTTPException(status_code=400, detail="正面提示词不能为空")
    if preset_type not in ("costume", "prop", "makeup"):
        raise HTTPException(status_code=400, detail=f"无效类型: {preset_type}")

    try:
        template = save_template(preset_type, title, positive_template, negative_prompt)
        return {"ok": True, "title": template["title"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")


@app.delete("/api/fudaohua/template/{preset_type}/{title}")
async def api_fudaohua_template_delete(preset_type: str, title: str):
    """删除指定模板"""
    try:
        from urllib.parse import unquote
        title = unquote(title)
    except Exception:
        pass
    if delete_template(preset_type, title):
        return {"ok": True}
    raise HTTPException(status_code=404, detail="模板不存在")



# 服道化自定义预设 API
# ============================================================

from src.fudaohua_custom import save_custom_preset, delete_custom_preset


@app.post("/api/fudaohua/custom/save")
async def api_fudaohua_custom_save(request: dict):
    preset_type = request.get("type", "costume")
    name = request.get("name", "").strip()
    core_tags = request.get("core_tags", "").strip()

    if not name:
        raise HTTPException(status_code=400, detail="名称不能为空")
    if not core_tags:
        raise HTTPException(status_code=400, detail="提示词不能为空")
    if preset_type not in ("costume", "prop", "makeup"):
        raise HTTPException(status_code=400, detail=f"无效类型: {preset_type}")

    try:
        preset = save_custom_preset(preset_type, name, core_tags)
        return {"ok": True, "id": preset["id"], "name": preset["name_cn"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")


@app.delete("/api/fudaohua/custom/{preset_type}/{preset_id}")
async def api_fudaohua_custom_delete(preset_type: str, preset_id: str):
    if delete_custom_preset(preset_type, preset_id):
        return {"ok": True}
    raise HTTPException(status_code=404, detail="预设不存在")


# ========== 启动 ==========


# ============================================================
# Qwen Prompt 工作室路由
# ============================================================
from src.qwen_routes import router as qwen_router
app.include_router(qwen_router)

# ============================================================
# Character Manager routes
# ============================================================
from src.character_addons import router as character_router
app.include_router(character_router)

# ============================================================
# WD14 Tagger 标签提取路由
# ============================================================
from src.wd14_tagger import get_tagger
from pydantic import BaseModel, Field

class TaggerRequest(BaseModel):
    image: str
    threshold: float = Field(default=0.35, ge=0.0, le=1.0)

@app.post("/api/tagger/interrogate")
async def tagger_interrogate(req: TaggerRequest):
    import base64
    from io import BytesIO
    from PIL import Image
    img_data = req.image
    if "," in img_data:
        img_data = img_data.split(",", 1)[1]
    try:
        img_bytes = base64.b64decode(img_data)
    except Exception:
        raise HTTPException(status_code=400, detail="图片数据解码失败")
    try:
        image = Image.open(BytesIO(img_bytes)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="图片格式不支持")
    tagger = get_tagger()
    ratings, tags = tagger.interrogate(image)
    processed = tagger.postprocess_tags(tags, threshold=req.threshold)
    return {"ratings": ratings, "tags": processed, "tag_count": len(processed)}



# ============================================================
# 场景 LoRA 训练素材生产室 API
# ============================================================

@app.get("/api/scene-material/templates")
async def api_sm_templates():
    """获取场景训练模板列表"""
    return {"templates": sm.list_templates()}


@app.get("/api/scene-material/template/{template_id}")
async def api_sm_template_get(template_id: str):
    """获取单个模板"""
    t = sm.get_template(template_id)
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    return t


@app.post("/api/scene-material/template/save")
async def api_sm_template_save(data: dict):
    """保存模板（有id则更新，无id则新建）"""
    try:
        result = sm.save_template(data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")


@app.delete("/api/scene-material/template/{template_id}")
async def api_sm_template_delete(template_id: str):
    """删除模板（不删除关联数据）"""
    if sm.delete_template(template_id):
        return {"ok": True}
    raise HTTPException(status_code=404, detail="模板不存在")


@app.post("/api/scene-material/preview")
async def api_sm_preview(data: dict):
    """生成预览（每次1张）"""
    try:
        tid = data.get("template_id") or data.get("id") or str(uuid.uuid4())[:8]
        result = await sm.generate_preview(
            template_id=tid,
            model=data.get("model", ""),
            width=data.get("width", 1344),
            height=data.get("height", 768),
            positive_prompt=data.get("positive_prompt", ""),
            negative_prompt=data.get("negative_prompt", ""),
            seed_mode=data.get("seed_mode", "random"),
            seed=data.get("seed", 0),
            steps=data.get("steps", 25),
            cfg=data.get("cfg", 3.5),
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预览生成失败: {str(e)}")


@app.get("/api/scene-material/preview/{template_id}")
async def api_sm_preview_get(template_id: str):
    """获取预览信息"""
    info = sm.get_preview_info(template_id)
    if not info:
        return {"template_id": template_id, "has_preview": False}
    return info


@app.post("/api/scene-material/batch")
async def api_sm_batch(data: dict):
    """提交批量生成（非阻塞，返回batch_id）"""
    try:
        tid = data.get("template_id") or str(uuid.uuid4())[:8]
        result = await sm.submit_batch(
            template_id=tid,
            total=data.get("total", 10),
            model=data.get("model", ""),
            width=data.get("width", 1344),
            height=data.get("height", 768),
            positive_prompt=data.get("positive_prompt", ""),
            negative_prompt=data.get("negative_prompt", ""),
            seed_mode=data.get("seed_mode", "random"),
            seed=data.get("seed", 0),
            steps=data.get("steps", 25),
            cfg=data.get("cfg", 3.5),
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交批量任务失败: {str(e)}")


@app.get("/api/scene-material/batch/{batch_id}/status")
async def api_sm_batch_status(batch_id: str):
    """查询批量任务状态（轮询用）"""
    s = sm.get_batch_status(batch_id)
    if not s:
        raise HTTPException(status_code=404, detail="批次不存在")
    return s


@app.get("/api/scene-material/batches")
async def api_sm_batches():
    """批量任务列表"""
    return {"batches": sm.get_batches()}


@app.get("/api/scene-material/batch/{batch_id}")
async def api_sm_batch_detail(batch_id: str):
    """批量详情（含图片列表和状态）"""
    d = sm.get_batch_detail(batch_id)
    if not d:
        raise HTTPException(status_code=404, detail="批次不存在")
    return d


@app.post("/api/scene-material/batch/{batch_id}/status")
async def api_sm_item_status(batch_id: str, data: dict):
    """更新图片状态: approved/rejected/used_for_training"""
    stem = data.get("stem", "")
    status = data.get("status", "")
    value = data.get("value", True)
    if not stem or status not in ("approved", "rejected", "used_for_training"):
        raise HTTPException(status_code=400, detail="无效参数")
    if sm.update_item_status(batch_id, stem, status, value):
        return {"ok": True}
    raise HTTPException(status_code=404, detail="图片不存在")


@app.post("/api/scene-material/batch/{batch_id}/export")
async def api_sm_batch_export(batch_id: str):
    """导出 approved 图片"""
    result = sm.export_approved(batch_id)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result.get("error", "导出失败"))
    return result


@app.get("/api/scene-material/categories")
async def api_sm_categories():
    """场景分类列表"""
    return {"categories": sm.get_scene_categories()}


@app.get("/api/scene-material/size-presets")
async def api_sm_size_presets():
    """尺寸预设列表"""
    return {"presets": sm.get_size_presets()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
