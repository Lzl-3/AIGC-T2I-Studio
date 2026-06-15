# -*- coding: utf-8 -*-
"""SQLite 数据库操作（异步）"""

import json
import aiosqlite
from src.models import GenerationTask, SubTaskInfo, TaskStatus
DB_PATH = "./data/tasks.db"


async def init_db(db_path: str = DB_PATH):
    """初始化数据库，创建表"""
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                genre TEXT NOT NULL,
                project_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT "pending",
                total_subtasks INTEGER DEFAULT 0,
                completed_subtasks INTEGER DEFAULT 0,
                request_json TEXT,
                created_at TEXT,
                completed_at TEXT,
                error_message TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subtasks (
                subtask_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                prompt_positive TEXT NOT NULL,
                prompt_negative TEXT NOT NULL,
                filename TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT "pending",
                comfyui_prompt_id TEXT,
                image_path TEXT,
                created_at TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id)
            )
        """)
        await db.commit()

        # 迁移：为 subtasks 表增加模型参数列（v1.1）
        try:
            await db.execute("ALTER TABLE subtasks ADD COLUMN vae_name TEXT DEFAULT ''")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE subtasks ADD COLUMN clip_name TEXT DEFAULT ''")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE subtasks ADD COLUMN lora_name TEXT DEFAULT ''")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE subtasks ADD COLUMN lora_strength REAL DEFAULT 1.0")
        except Exception:
            pass
        await db.commit()



async def save_task(db_path: str, task: GenerationTask):
    """保存任务到数据库"""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT OR REPLACE INTO tasks 
            (task_id, category, genre, project_name, status,
             total_subtasks, completed_subtasks, request_json,
             created_at, completed_at, error_message) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task.task_id, task.category.value, task.genre.value,
                task.project_name, task.status.value,
                task.total_subtasks, task.completed_subtasks,
                task.request.model_dump_json(), task.created_at,
                task.completed_at, task.error_message
            )
        )
        await db.commit()


async def save_subtask(db_path: str, sub: SubTaskInfo):
    """保存子任务到数据库"""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT OR REPLACE INTO subtasks 
            (subtask_id, task_id, prompt_positive, prompt_negative,
             filename, status, comfyui_prompt_id, image_path, created_at,
             vae_name, clip_name, lora_name, lora_strength) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                sub.subtask_id, sub.task_id, sub.prompt_positive,
                sub.prompt_negative, sub.filename, sub.status.value,
                sub.comfyui_prompt_id, sub.image_path, sub.created_at,
                sub.vae_name, sub.clip_name, sub.lora_name, sub.lora_strength
            )
        )
        await db.commit()


async def get_task(db_path: str, task_id: str) -> dict | None:
    """获取单个任务"""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def list_tasks(db_path: str, status: str = None) -> list[dict]:
    """列出任务，可按状态筛选"""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        if status:
            cursor = await db.execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC",
                (status,)
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM tasks ORDER BY created_at DESC"
            )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_subtasks(db_path: str, task_id: str) -> list[dict]:
    """获取某任务的所有子任务"""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM subtasks WHERE task_id = ? ORDER BY created_at",
            (task_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
