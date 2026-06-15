# -*- coding: utf-8 -*-
"""异步任务队列管理器 + SSE 广播"""

import asyncio
import json
import uuid
import os
import aiosqlite
from pathlib import Path
from config.settings import settings
from src.models import (
    GenerationRequest, GenerationTask, SubTaskInfo, TaskStatus, WorkflowType
)
from src.db import (
    init_db, save_task, save_subtask, get_task, list_tasks, get_subtasks, DB_PATH
)
from src.prompt_builder import build_prompts_for_request
from src.workflow_engine import load_workflow_json, inject_parameters, detect_model_type, resolve_workflow
from src.comfyui_client import comfyui_client
from src.cards import get_card


class TaskManager:
    """
    异步任务管理器。
    管理生成任务的队列、执行和状态广播。
    """

    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.active_count = 0
        self.max_concurrent = settings.max_concurrent_tasks
        self.poll_interval = settings.poll_interval
        self.poll_timeout = settings.poll_timeout
        self.sse_clients: list[asyncio.Queue] = []
        self._running = False
        self._worker_task: asyncio.Task | None = None  # 保存 worker 引用用于安全关闭

    async def start(self):
        """启动任务管理器（初始化 DB 并启动 worker）"""
        await init_db(DB_PATH)
        await self._recover_orphaned_tasks()
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())



    async def _recover_orphaned_tasks(self):
        """启动时扫描并清理僵尸任务（服务重启后残留的 running/pending）"""
        async with aiosqlite.connect(DB_PATH) as db:
            # 把 running/pending 子任务标为 failed
            await db.execute("""
                UPDATE subtasks SET status = 'failed',
                prompt_positive = prompt_positive || ' [服务重启，任务丢失]'
                WHERE status IN ('running', 'pending')
                  AND task_id IN (SELECT task_id FROM tasks WHERE status IN ('running', 'pending'))
            """)
            await db.commit()

            # 重新判定任务状态
            async with db.execute(
                "SELECT task_id FROM tasks WHERE status IN ('running', 'pending')"
            ) as cursor:
                rows = await cursor.fetchall()
            for (task_id,) in rows:
                async with db.execute(
                    "SELECT status FROM subtasks WHERE task_id = ?", (task_id,)
                ) as cursor2:
                    subs = await cursor2.fetchall()
                statuses = [s[0] for s in subs]
                failed = statuses.count("failed")
                completed = statuses.count("completed")
                total = len(subs)
                new_status = "completed" if (completed + failed == total and failed == 0) else "failed"
                await db.execute(
                    "UPDATE tasks SET status = ?, completed_at = datetime('now'), completed_subtasks = ? WHERE task_id = ?",
                    (new_status, completed, task_id)
                )
            await db.commit()
            print(f"[启动恢复] 已清理 {len(rows)} 个僵尸任务")
    async def shutdown(self):
        """安全关闭任务管理器：取消 worker 并断开 SSE 客户端"""
        self._running = False
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        # 通知所有 SSE 客户端关闭
        for client_q in self.sse_clients:
            await client_q.put({"type": "server_shutdown"})
        self.sse_clients.clear()
    async def submit_task(self, request: GenerationRequest, card_id: str = None) -> str:
        """
        提交生成任务，拆分为子任务并入队

        Args:
            request: 生成请求

        Returns:
            task_id 字符串
        """
        task_id = str(uuid.uuid4())[:8]

        # img2img 模式：先上传图片到 ComfyUI
        if request.category == WorkflowType.IMG2IMG and request.image_filename:
            local_path = os.path.join("data/uploads", request.image_filename)
            if os.path.exists(local_path):
                try:
                    comfyui_filename = await comfyui_client.upload_image_to_comfyui(local_path)
                    request.image_filename = comfyui_filename
                except Exception as e:
                    raise RuntimeError(f"上传图片到 ComfyUI 失败: {e}")

                # 工作流卡片参数覆盖
        card = None
        if card_id:
            card = get_card(card_id)
            if card:
                if card.get("checkpoint"):
                    request.model_name = card["checkpoint"]
                    request.model_type = card.get("model_type") or detect_model_type(card["checkpoint"])
                if card.get("steps"):
                    request.steps = card["steps"]
                if card.get("cfg"):
                    request.cfg = card["cfg"]
                if card.get("sampler_name"):
                    request.sampler_name = card["sampler_name"]
                if card.get("scheduler"):
                    request.scheduler = card["scheduler"]
                if card.get("width"):
                    request.width = card["width"]
                if card.get("height"):
                    request.height = card["height"]

        # ??????????????? GenerationRequest ?????? inject_parameters?
        card_vae = card.get("vae", "") if card else ""
        card_clip = card.get("clip_model", "") if card else ""
        card_lora = card.get("lora", "") if card else ""
        card_lora_strength = card.get("lora_strength", 1.0) if card else 1.0

        # ???????????????????????? Prompt ???
        if request.batch_prompts and len(request.batch_prompts) > 0:
            subtask_configs = []
            for idx, prompt_text in enumerate(request.batch_prompts):
                safe_name = request.project_name or "batch"
                filename = f"{safe_name}_{idx + 1:03d}"
                subtask_configs.append({
                    "positive": prompt_text.strip(),
                    "negative": request.free_negative or "lowres, bad anatomy, bad hands, worst quality",
                    "filename": filename,
                })
        else:
            subtask_configs = build_prompts_for_request(request)

        # 统一展开：角色类 dict 在 submit_task 一处完成角度 x 表情 x 候选展开
        is_character_expandable = isinstance(subtask_configs, dict) and subtask_configs.get("type") == "character"

        if is_character_expandable:
            base = subtask_configs
            candidate_count = max(1, getattr(request, "candidate_count", 1) or 1)
            expanded_configs = []
            for angle in base["angles"]:
                for p in base["prompts"]:
                    for c_idx in range(candidate_count):
                        c_label = f"_c{c_idx + 1}" if candidate_count > 1 else ""
                        filename = f"{base['genre_label']}_{base['role']}_{angle}_{p['expression']}{c_label}"
                        expanded_configs.append({
                            "positive": p["positive"],
                            "negative": p["negative"],
                            "filename": filename,
                        })
            subtask_configs = expanded_configs

        # 卡片参数覆盖
        if card:
            pos_prefix = card.get("positive_prefix", "")
            neg_prefix = card.get("negative_prefix", "")
            if pos_prefix or neg_prefix:
                for cfg_item in subtask_configs:
                    if pos_prefix:
                        cfg_item["positive"] = pos_prefix + ", " + cfg_item["positive"]
                    if neg_prefix:
                        cfg_item["negative"] = neg_prefix + ", " + cfg_item["negative"]

        # 创建主任务
        task = GenerationTask(
            task_id=task_id,
            category=request.category,
            genre=request.genre,
            project_name=request.project_name,
            status=TaskStatus.PENDING,
            total_subtasks=len(subtask_configs) * request.batch_count,
            completed_subtasks=0,
            request=request,
        )
        await save_task(DB_PATH, task)

        # 创建子任务并入队
        for cfg in subtask_configs:
            for batch_idx in range(request.batch_count):
                subtask_id = str(uuid.uuid4())[:8]
                filename = cfg["filename"]
                if request.batch_count > 1:
                    filename += f"_{batch_idx + 1}"
                sub = SubTaskInfo(
                    subtask_id=subtask_id,
                    task_id=task_id,
                    prompt_positive=cfg["positive"],
                    prompt_negative=cfg["negative"],
                    filename=filename,
                    status=TaskStatus.PENDING,
                    vae_name=card_vae,
                    clip_name=card_clip,
                    lora_name=card_lora,
                    lora_strength=card_lora_strength,
                )
                await save_subtask(DB_PATH, sub)
                await self.queue.put(sub)

        # 推送任务创建事件
        await self._broadcast({
            "type": "task_created",
            "task_id": task_id,
            "total": task.total_subtasks,
            "status": "pending",
        })

        return task_id

    async def cancel_task(self, task_id: str):
        """取消任务及其所有子任务"""
        task_data = await get_task(DB_PATH, task_id)
        if not task_data:
            return

        # 取消 ComfyUI 中正在运行的子任务
        subs = await get_subtasks(DB_PATH, task_id)
        for sub in subs:
            if sub["comfyui_prompt_id"]:
                await comfyui_client.cancel_task(sub["comfyui_prompt_id"])

        # 更新数据库状态
        from src.db import save_task as db_save_task
        task = GenerationTask(
            task_id=task_id,
            category=task_data["category"],
            genre=task_data["genre"],
            project_name=task_data["project_name"],
            status=TaskStatus.CANCELLED,
            total_subtasks=task_data["total_subtasks"],
            completed_subtasks=task_data["completed_subtasks"],
            request=GenerationRequest.model_validate_json(task_data["request_json"]),
            created_at=task_data["created_at"],
        )
        await db_save_task(DB_PATH, task)

    async def get_task_detail(self, task_id: str) -> dict:
        """获取任务详情，包含子任务列表"""
        task = await get_task(DB_PATH, task_id)
        if not task:
            return None
        subs = await get_subtasks(DB_PATH, task_id)
        task["subtasks"] = subs
        return task

    async def list_all_tasks(self, status: str = None) -> list[dict]:
        """列出所有任务"""
        return await list_tasks(DB_PATH, status)

    async def subscribe_sse(self) -> asyncio.Queue:
        """注册 SSE 客户端，返回消息队列"""
        q: asyncio.Queue = asyncio.Queue()
        self.sse_clients.append(q)
        return q

    def unsubscribe_sse(self, q: asyncio.Queue):
        """注销 SSE 客户端"""
        if q in self.sse_clients:
            self.sse_clients.remove(q)

    async def _broadcast(self, event: dict):
        """向所有 SSE 客户端广播事件"""
        for q in self.sse_clients:
            try:
                await q.put(event)
            except Exception:
                pass

    async def _worker_loop(self):
        """Worker 主循环：从队列取子任务并执行"""
        while self._running:
            try:
                sub: SubTaskInfo = await self.queue.get()
                while self.active_count >= self.max_concurrent:
                    await asyncio.sleep(1.0)
                self.active_count += 1
                asyncio.create_task(self._run_subtask(sub))
            except Exception as e:
                print(f"Worker 异常: {e}")
                await asyncio.sleep(1.0)

    async def _run_subtask(self, sub: SubTaskInfo):
        """执行单个子任务：提交 ComfyUI → 轮询结果 → 保存图片"""
        try:
            task_data = await get_task(DB_PATH, sub.task_id)
            if not task_data:
                return
            req = GenerationRequest.model_validate_json(task_data["request_json"])

            # 加载并注入工作流参数
                        # 安全兜底：从 checkpoint 文件名推断 model_type
            resolved_model_type = req.model_type or (detect_model_type(req.model_name) if req.model_name else "sdxl")
            base_workflow = load_workflow_json(req.category.value, resolved_model_type)
            workflow, _seed = inject_parameters(
                workflow=base_workflow,
                model_name=req.model_name,
                positive_prompt=sub.prompt_positive,
                negative_prompt=sub.prompt_negative,
                seed=req.seed,
                seed_mode="fixed",
                width=req.width,
                height=req.height,
                steps=req.steps,
                cfg=req.cfg,
                image_filename=req.image_filename,
                denoising_strength=req.denoising_strength,
                sampler_name=req.sampler_name,
                scheduler=req.scheduler,
                vae_name=sub.vae_name,
                clip_name=sub.clip_name,
                lora_name=sub.lora_name,
                lora_strength=sub.lora_strength,
                model_type=resolved_model_type,
            )

            sub.status = TaskStatus.RUNNING
            await save_subtask(DB_PATH, sub)
            await self._broadcast({
                "type": "subtask_started",
                "task_id": sub.task_id,
                "subtask_id": sub.subtask_id,
                "filename": sub.filename,
            })

            print(f"[TASK START] task={sub.task_id} subtask={sub.subtask_id} filename={sub.filename}")

                        # ComfyUI 健康检查：降级时等待恢复（连续502过多）
            if comfyui_client.is_degraded:
                print(f"[健康检查] ComfyUI 降级中，等待30秒后重试 subtask={sub.subtask_id}")
                await asyncio.sleep(30)
                if comfyui_client.is_degraded:
                    raise RuntimeError("ComfyUI 持续降级（连续502），跳过当前子任务")
                comfyui_client.reset_error_counter()

# 提交到 ComfyUI（每子任务正好1张图，展开已在 submit_task 统一完成）
            prompt_id = await comfyui_client.submit_workflow(workflow)
            if not prompt_id:
                raise RuntimeError("ComfyUI 提交失败：未返回 prompt_id")
            sub.comfyui_prompt_id = prompt_id
            await save_subtask(DB_PATH, sub)

            # 轮询等待生成完成
            image_bytes = await self._poll_for_result(sub, prompt_id)
            if not image_bytes:
                raise TimeoutError(f"ComfyUI 生成超时（{self.poll_timeout}秒），prompt_id: {prompt_id}")

            # 保存图片
            output_path = self._get_output_path(req, sub.filename)
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_bytes(image_bytes)

            # 保存元数据
            cand_meta = {
                "prompt": sub.prompt_positive,
                "negative_prompt": sub.prompt_negative,
                "width": req.width,
                "height": req.height,
                "steps": req.steps,
                "cfg": req.cfg,
                "seed": req.seed,
                "workflow_name": f"zimage_v2_{req.category.value}" if req.model_type == "zimage" else f"{req.model_type}_{req.category.value}",
            }
            meta_path = output_file.with_suffix(".json")
            meta_path.write_text(json.dumps(cand_meta, ensure_ascii=False, indent=2), encoding="utf-8")

            # 保存正向提示词到同目录 txt
            label_path = output_file.with_suffix(".txt")
            label_path.write_text(sub.prompt_positive, encoding="utf-8")

            # 子任务完成
            sub.image_path = str(output_path)
            rel = Path(output_path).relative_to(settings.output_dir)
            sub.status = TaskStatus.COMPLETED
            await save_subtask(DB_PATH, sub)
            await self._update_task_progress(sub.task_id)

            await self._broadcast({
                "type": "subtask_completed",
                "task_id": sub.task_id,
                "subtask_id": sub.subtask_id,
                "filename": sub.filename,
                "image_path": str(output_path),
                "rel_path": str(rel),
                "seed": req.seed,
            })

            print(f"[TASK DONE] task={sub.task_id} subtask={sub.subtask_id} filename={sub.filename}")

        except Exception as e:
            print(f"[TASK FAIL] task={sub.task_id} subtask={sub.subtask_id} filename={sub.filename} error={e}")
            sub.status = TaskStatus.FAILED
            sub.prompt_positive = f"{sub.prompt_positive} [错误: {str(e)}]"
            await save_subtask(DB_PATH, sub)
            await self._update_task_progress(sub.task_id)

            await self._broadcast({
                "type": "subtask_failed",
                "task_id": sub.task_id,
                "subtask_id": sub.subtask_id,
                "filename": sub.filename,
                "error": str(e),
            })
        finally:
            self.active_count -= 1
            self.queue.task_done()

    async def _poll_for_result(self, sub: SubTaskInfo, prompt_id: str) -> bytes | None:
        """轮询 ComfyUI 直到图片生成完成或超时

        改进：连续错误超过阈值时提前退出，避免浪费完整超时时间。
        """
        elapsed = 0.0
        consecutive_errors = 0
        max_consecutive_errors = 10

        while elapsed < self.poll_timeout:
            await asyncio.sleep(self.poll_interval)
            elapsed += self.poll_interval

            # 每10秒广播一次进度
            if int(elapsed) % 10 == 0 and int(elapsed) > 0:
                await self._broadcast_progress(sub, elapsed)

            try:
                history = await comfyui_client.get_history(prompt_id)
                consecutive_errors = 0  # 成功请求，重置错误计数

                prompt_data = history.get(prompt_id)
                if prompt_data and "outputs" in prompt_data:
                    # 找到 SaveImage 节点的输出
                    for node_id, output in prompt_data["outputs"].items():
                        if "images" in output:
                            for img in output["images"]:
                                filename = img["filename"]
                                subfolder = img.get("subfolder", "")
                                folder_type = img.get("type", "output")
                                return await comfyui_client.download_image(
                                    filename, subfolder, folder_type
                                )
            except Exception as e:
                consecutive_errors += 1
                print(f"[轮询异常] subtask={sub.subtask_id} prompt_id={prompt_id} "
                      f"连续错误={consecutive_errors}/{max_consecutive_errors} error={e}")

                if consecutive_errors >= max_consecutive_errors:
                    raise RuntimeError(
                        f"ComfyUI 连续 {consecutive_errors} 次轮询失败，放弃等待"
                    )

        return None
    def _get_output_path(self, request: GenerationRequest, filename: str) -> str:
        """生成输出文件路径"""
        from src.models import GENRE_LABELS
        genre_label = GENRE_LABELS.get(request.genre, request.genre.value)
        category_dir = request.category.value
        project = request.project_name
        safe_filename = _sanitize_filename(filename)
        return str(
            Path(settings.output_dir)
            / category_dir
            / genre_label
            / project
            / f"{safe_filename}.png"
        )

    
    async def _broadcast_progress(self, sub, elapsed: float):
        """广播生成进度"""
        await self._broadcast({
            "type": "subtask_progress",
            "task_id": sub.task_id,
            "subtask_id": sub.subtask_id,
            "filename": sub.filename,
            "elapsed": round(elapsed, 1),
            "timeout": self.poll_timeout,
        })

    async def _update_task_progress(self, task_id: str):
        """更新任务完成进度"""
        subs = await get_subtasks(DB_PATH, task_id)
        completed = sum(1 for s in subs if s["status"] == "completed")
        failed = sum(1 for s in subs if s["status"] == "failed")
        total = len(subs)

        task_data = await get_task(DB_PATH, task_id)
        if not task_data:
            return

        req = GenerationRequest.model_validate_json(task_data["request_json"])

        if completed + failed >= total:
            status = TaskStatus.COMPLETED if failed == 0 else TaskStatus.FAILED
            from datetime import datetime
            task = GenerationTask(
                task_id=task_id,
                category=task_data["category"],
                genre=task_data["genre"],
                project_name=task_data["project_name"],
                status=status,
                total_subtasks=total,
                completed_subtasks=completed,
                request=req,
                created_at=task_data["created_at"],
                completed_at=datetime.now().isoformat(),
            )
        else:
            task = GenerationTask(
                task_id=task_id,
                category=task_data["category"],
                genre=task_data["genre"],
                project_name=task_data["project_name"],
                status=TaskStatus.RUNNING,
                total_subtasks=total,
                completed_subtasks=completed,
                request=req,
                created_at=task_data["created_at"],
            )
        await save_task(DB_PATH, task)

        await self._broadcast({
            "type": "task_progress",
            "task_id": task_id,
            "completed": completed,
            "failed": failed,
            "total": total,
            "status": task.status.value,
        })


def _sanitize_filename(name: str) -> str:
    """过滤文件名中的非法字符"""
    illegal_chars = r'/\:*?"<>|'
    for ch in illegal_chars:
        name = name.replace(ch, "_")
    return name


# 全局任务管理器实例
task_manager = TaskManager()
