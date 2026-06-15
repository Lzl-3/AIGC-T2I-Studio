# -*- coding: utf-8 -*-
"""
数据集筛选器微服务 — 端口 8888
独立 FastAPI 实例，零侵入主项目。

启动: python filter_server.py
访问: http://localhost:8888
"""

import json
import os
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

# 确保能导入 src 模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.dataset_filter import DatasetFilter, _quality_score


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class FilterRequest(BaseModel):
    input_dir: str = Field(..., description="原始素材目录路径")
    output_dir: str = Field(default="", description="筛选结果输出目录")
    quality_threshold: float = Field(default=0.15, ge=0.0, le=1.0)
    hamming_threshold: int = Field(default=5, ge=0, le=64)
    composition_targets: Optional[Dict[str, float]] = None


class TaskInfo:
    """任务运行状态容器。"""
    def __init__(self, task_id: str, request: FilterRequest):
        self.task_id = task_id
        self.request = request
        self.status = "pending"       # pending | running | done | cancelled | error
        self.stage = ""               # scanning | quality | dedup | balance | finished
        self.current = 0
        self.total = 0
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.started_at: Optional[float] = None
        self.finished_at: Optional[float] = None
        self._cancel_flag = threading.Event()


# ---------------------------------------------------------------------------
# 任务管理器
# ---------------------------------------------------------------------------

class TaskManager:
    """内存任务管理器，重启丢失。"""
    def __init__(self):
        self._tasks: Dict[str, TaskInfo] = {}

    def create(self, request: FilterRequest) -> TaskInfo:
        task_id = uuid.uuid4().hex[:12]
        info = TaskInfo(task_id, request)
        self._tasks[task_id] = info
        return info

    def get(self, task_id: str) -> Optional[TaskInfo]:
        return self._tasks.get(task_id)

    def list_recent(self, limit: int = 10):
        return list(self._tasks.values())[-limit:]


task_manager = TaskManager()


# ---------------------------------------------------------------------------
# FastAPI 应用
# ---------------------------------------------------------------------------

app = FastAPI(title="AIGC 数据集筛选器", version="1.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# 后台筛选执行器
# ---------------------------------------------------------------------------

def _run_filter_in_thread(info: TaskInfo):
    """在后台线程中执行 DatasetFilter，逐阶段更新进度。"""
    try:
        info.status = "running"
        info.started_at = time.time()

        output_dir = info.request.output_dir or (
            f"training_dataset/{time.strftime('%Y%m%d_%H%M%S')}"
        )

        f = DatasetFilter(
            input_dir=info.request.input_dir,
            output_dir=output_dir,
            quality_threshold=info.request.quality_threshold,
            hamming_threshold=info.request.hamming_threshold,
        )

        # --- 阶段 1: 扫描 ---
        info.stage = "scanning"
        f._scan_images()
        info.total = len(f.records)
        if info._cancel_flag.is_set():
            info.status = "cancelled"
            return
        if info.total == 0:
            info.status = "done"
            info.result = f._empty_report()
            info.result["output_dir"] = output_dir
            return

        # --- 阶段 2: 质量筛选（逐张处理，实时进度） ---
        info.stage = "quality"
        info.total = len(f.records)
        info.current = 0
        for i, r in enumerate(f.records):
            if info._cancel_flag.is_set():
                info.status = "cancelled"
                return
            try:
                from PIL import Image
                img = Image.open(r["path"]).convert("RGB")
                img.load()
                score, details = _quality_score(img)
                r["quality_score"] = round(score, 4)
                r["quality_details"] = details
                if score < f.quality_threshold:
                    r["stage"] = "rejected"
                    r["reason"] = f"质量分 {score:.4f} 低于阈值 {f.quality_threshold}"
                else:
                    r["stage"] = "quality_passed"
                img.close()
            except Exception as exc:
                r["quality_score"] = 0.0
                r["stage"] = "rejected"
                r["reason"] = f"图片读取失败: {exc}"
            info.current = i + 1
            time.sleep(0.005)

        if info._cancel_flag.is_set():
            info.status = "cancelled"
            return

        # --- 阶段 3: 去重 ---
        info.stage = "dedup"
        active = [r for r in f.records if r.get("stage") == "quality_passed"]
        info.total = len(active)
        info.current = 0
        for i, r in enumerate(active):
            try:
                img = __import__("PIL.Image", fromlist=["Image"]).Image.open(r["path"]).convert("L")
                img.load()
                r["dhash"] = __import__("src.dataset_filter", fromlist=["_compute_dhash"])._compute_dhash(img)
                img.close()
            except Exception:
                r["dhash"] = 0
            info.current = i + 1
            if info._cancel_flag.is_set():
                info.status = "cancelled"
                return
            time.sleep(0.005)
        active = f._stage_dedup(active)

        if info._cancel_flag.is_set():
            info.status = "cancelled"
            return

        # --- 阶段 4: 构图均衡 ---
        info.stage = "balance"
        active = f._stage_balance(active)
        for r in active:
            r["stage"] = "selected"
        info.current = info.total

        # --- 阶段 5: 复制文件 ---
        info.stage = "copying"
        rejected_list = [r for r in f.records if r.get("stage") == "rejected"]
        duplicate_list = [r for r in f.records if r.get("stage") == "duplicate"]
        cluster_removed_list = [r for r in f.records if r.get("stage") == "cluster_removed"]
        selected_list = [r for r in f.records if r.get("stage") == "selected"]

        f._copy_files(rejected_list, "rejected")
        f._copy_files(duplicate_list, "duplicate")
        f._copy_files(cluster_removed_list, "cluster_removed")
        f._copy_files(selected_list, "selected")

        # 生成报告
        f.report = {
            "config": {
                "quality_threshold": f.quality_threshold,
                "hamming_threshold": f.hamming_threshold,
                "composition_targets": dict(f.COMPOSITION_TARGETS),
            },
            "input_count": f.records and len(f.records) or 0,
            "rejected_count": len(rejected_list),
            "duplicate_count": len(duplicate_list),
            "cluster_removed_count": len(cluster_removed_list),
            "selected_count": len(selected_list),
            "copy_errors": f.copy_errors,
            "images": [
                {
                    "filename": r["filename"],
                    "quality_score": r.get("quality_score"),
                    "quality_details": r.get("quality_details"),
                    "dhash": r.get("dhash"),
                    "composition": r.get("composition"),
                    "composition_source": r.get("composition_source"),
                    "stage": r.get("stage"),
                    "reason": r.get("reason", ""),
                }
                for r in f.records
            ],
        }
        f._write_report()

        info.stage = "finished"
        info.status = "done"
        info.finished_at = time.time()
        info.result = f.report
        info.result["output_dir"] = str(Path(output_dir).resolve())

    except Exception as exc:
        info.status = "error"
        info.error = str(exc)
        info.finished_at = time.time()


# ---------------------------------------------------------------------------
# API 端点
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"service": "dataset-filter", "status": "ok"}


@app.post("/api/filter/start")
def start_filter(req: FilterRequest):
    """提交筛选任务，返回 task_id。"""
    # 校验输入目录
    input_path = Path(req.input_dir)
    if not input_path.is_dir():
        raise HTTPException(400, f"输入目录不存在: {req.input_dir}")

    info = task_manager.create(req)
    thread = threading.Thread(target=_run_filter_in_thread, args=(info,), daemon=True)
    thread.start()
    return {"task_id": info.task_id, "status": "pending"}


@app.get("/api/filter/status/{task_id}")
def get_status(task_id: str):
    """查询任务进度。"""
    info = task_manager.get(task_id)
    if not info:
        raise HTTPException(404, "任务不存在")
    elapsed = (time.time() - info.started_at) if info.started_at else 0
    return {
        "task_id": info.task_id,
        "status": info.status,
        "stage": info.stage,
        "current": info.current,
        "total": info.total,
        "elapsed_seconds": round(elapsed, 1),
        "error": info.error,
    }


@app.get("/api/filter/result/{task_id}")
def get_result(task_id: str):
    """获取筛选结果摘要。"""
    info = task_manager.get(task_id)
    if not info:
        raise HTTPException(404, "任务不存在")
    if info.status not in ("done",):
        raise HTTPException(400, f"任务尚未完成，当前状态: {info.status}")
    return info.result


@app.post("/api/filter/cancel/{task_id}")
def cancel_filter(task_id: str):
    """取消正在运行的任务。"""
    info = task_manager.get(task_id)
    if not info:
        raise HTTPException(404, "任务不存在")
    if info.status in ("running",):
        info._cancel_flag.set()
        return {"task_id": task_id, "status": "cancelling"}
    return {"task_id": task_id, "status": info.status, "message": "任务不在运行中"}


@app.get("/api/filter/browse")
def browse_directory(dir_path: str = Query(...)):
    """浏览目录内容（图片列表 + 子目录）。"""
    p = Path(dir_path)
    if not p.is_dir():
        raise HTTPException(400, f"目录不存在: {dir_path}")
    items = []
    for entry in sorted(p.iterdir()):
        if entry.is_file():
            ext = entry.suffix.lower()
            if ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
                items.append({
                    "name": entry.name,
                    "type": "image",
                    "size": entry.stat().st_size,
                })
        elif entry.is_dir():
            items.append({"name": entry.name, "type": "directory"})
    return {"path": str(p.resolve()), "count": len(items), "items": items[:500]}


# ---------------------------------------------------------------------------
# 静态文件 & 首页
# ---------------------------------------------------------------------------

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def index():
    return FileResponse("static/dataset_filter.html")


# ---------------------------------------------------------------------------
# 启动入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("  数据集筛选器微服务")
    print("  地址: http://localhost:8888")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8888, log_level="info")