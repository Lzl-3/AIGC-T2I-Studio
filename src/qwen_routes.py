# -*- coding: utf-8 -*-
"""Qwen Prompt 工作室 API 路由"""

from fastapi import APIRouter, HTTPException
from src.qwen_prompt import pipeline
from src.models import (
    PromptPolishRequest, PromptPolishResult,
    PromptConvertRequest, PromptConvertResult,
    PromptGenerateRequest,
)
from src.comfyui_client import comfyui_client

router = APIRouter(prefix="/api/prompt", tags=["Qwen Prompt"])


@router.post("/polish", response_model=PromptPolishResult)
async def prompt_polish(request: PromptPolishRequest):
    """阶段1：粗糙中文 -> Qwen 润色 -> 标准中文"""
    return await pipeline.polish(request.idea)


@router.post("/convert", response_model=PromptConvertResult)
async def prompt_convert(request: PromptConvertRequest):
    """阶段2：标准中文 -> Qwen 翻译 -> ComfyUI 英文标签 JSON"""
    return await pipeline.convert(request.chinese_prompt)


@router.post("/generate")
async def prompt_generate(request: PromptGenerateRequest):
    """英文 Prompt -> 注入工作流 -> 提交 ComfyUI"""
    wf = pipeline.inject_workflow(
        positive=request.positive,
        negative=request.negative,
        params=request.params,
        workflow_type=request.workflow_type,
    )
    prompt_id = await comfyui_client.submit_workflow(wf)
    if not prompt_id:
        raise HTTPException(status_code=500, detail="ComfyUI 提交失败")
    return {"prompt_id": prompt_id, "status": "queued"}
