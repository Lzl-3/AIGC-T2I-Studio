# -*- coding: utf-8 -*-
"""
Qwen 本地模型客户端 (OpenAI 兼容接口)
通过 vLLM + LiteLLM 接入，统一封装对话请求。
"""

import logging
from openai import AsyncOpenAI
from config.settings import settings

logger = logging.getLogger(__name__)


class QwenAPIError(Exception):
    """Qwen API 调用异常"""
    pass


class QwenClient:
    """Qwen 模型统一调用客户端

    支持 vLLM / LiteLLM / 任何 OpenAI 兼容接口。
    单例模式：全局只维护一个客户端实例。
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._client = AsyncOpenAI(
            base_url=settings.qwen_base_url,
            api_key=settings.qwen_api_key,
            timeout=60.0,
            max_retries=2,
        )
        self._model = settings.qwen_model
        logger.info(f"QwenClient 初始化: {settings.qwen_base_url} | 模型={self._model}")

    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 8169,
    ) -> str:
        """通用对话接口

        Args:
            system_prompt: 系统提示词（定义角色和输出格式）
            user_message: 用户输入
            temperature: 创造性参数 (0.3=精准, 0.7=平衡, 0.8=创意)
            max_tokens: 最大输出 token 数

        Returns:
            模型回复文本（已 strip）

        Raises:
            QwenAPIError: 调用失败时抛出
        """
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            if content is None:
                reasoning = getattr(response.choices[0].message, "reasoning", None)
                if reasoning:
                    logger.warning(f"[Qwen] content为空，从 reasoning 回退")
                    return reasoning.strip()
                raise QwenAPIError("模型未返回有效内容")
            return content.strip()

        except Exception as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower():
                raise QwenAPIError(f"Qwen 模型响应超时: {error_msg}")
            elif "connection" in error_msg.lower() or "refused" in error_msg.lower():
                raise QwenAPIError(f"无法连接 Qwen 服务 ({settings.qwen_base_url}): {error_msg}")
            elif "401" in error_msg or "unauthorized" in error_msg.lower():
                raise QwenAPIError("Qwen API Key 验证失败，请检查 QWEN_API_KEY")
            else:
                raise QwenAPIError(f"Qwen 调用异常: {error_msg}")

    async def chat_vision(
        self,
        system_prompt: str,
        user_text: str,
        image_base64: str,
        image_mime: str = "image/png",
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """多模态对话接口（图片 + 文字）

        Args:
            system_prompt: 系统提示词
            user_text: 用户文字输入
            image_base64: 图片的 base64 编码（不含 data: 前缀）
            image_mime: 图片 MIME 类型
            temperature: 创造性参数
            max_tokens: 最大输出 token 数

        Returns:
            模型回复文本

        Raises:
            QwenAPIError: 调用失败时抛出
        """
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_text},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{image_mime};base64,{image_base64}"
                                },
                            },
                        ],
                    },
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            if content is None:
                reasoning = getattr(response.choices[0].message, "reasoning", None)
                if reasoning:
                    logger.warning(f"[Qwen] content为空，从 reasoning 回退")
                    return reasoning.strip()
                raise QwenAPIError("模型未返回有效内容")
            return content.strip()

        except Exception as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower():
                raise QwenAPIError(f"Qwen 视觉模型响应超时: {error_msg}")
            elif "connection" in error_msg.lower() or "refused" in error_msg.lower():
                raise QwenAPIError(f"无法连接 Qwen 服务 ({settings.qwen_base_url}): {error_msg}")
            elif "401" in error_msg or "unauthorized" in error_msg.lower():
                raise QwenAPIError("Qwen API Key 验证失败")
            elif "vision" in error_msg.lower() or "image" in error_msg.lower() or "multimodal" in error_msg.lower():
                raise QwenAPIError("当前 Qwen 模型不支持图片输入，请确认模型支持视觉功能")
            else:
                raise QwenAPIError(f"Qwen 视觉调用异常: {error_msg}")

