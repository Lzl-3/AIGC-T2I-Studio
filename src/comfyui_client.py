# -*- coding: utf-8 -*-
"""ComfyUI API 客户端 — 带退避重试"""

import asyncio
import httpx
from pathlib import Path
from config.settings import settings


# 瞬时错误状态码（需要退避重试）
RETRYABLE_STATUSES = {502, 503, 504}
MAX_RETRIES = 5
BASE_BACKOFF = 2.0  # 基础退避秒数


class ComfyUIClient:
    """ComfyUI API 客户端：提交工作流、轮询结果、下载图片"""

    def __init__(self):
        self.base_url = settings.comfyui_base_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None
        self._consecutive_502_errors = 0

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=15.0))
        return self._client

    async def _request_with_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
        """带指数退避的 HTTP 请求，自动重试 502/503/504 瞬时错误

        Args:
            method: HTTP 方法 (get/post)
            url: 请求 URL
            **kwargs: 传递给 httpx 的额外参数

        Returns:
            httpx.Response 对象

        Raises:
            httpx.HTTPStatusError: 非瞬时错误或重试耗尽
        """
        client = await self._get_client()
        last_exception = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                if method.lower() == "get":
                    resp = await client.get(url, **kwargs)
                else:
                    resp = await client.post(url, **kwargs)

                # 瞬时错误 → 退避重试
                if resp.status_code in RETRYABLE_STATUSES:
                    self._consecutive_502_errors += 1
                    if attempt < MAX_RETRIES:
                        delay = BASE_BACKOFF * (2 ** attempt)
                        print(f"[ComfyUI] {resp.status_code} 错误 (第{attempt+1}次), {delay:.1f}s 后重试: {url}")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        resp.raise_for_status()
                else:
                    # 非瞬时错误 → 重置连续错误计数
                    self._consecutive_502_errors = 0

                resp.raise_for_status()
                return resp

            except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError) as e:
                self._consecutive_502_errors += 1
                last_exception = e
                if attempt < MAX_RETRIES:
                    delay = BASE_BACKOFF * (2 ** attempt)
                    print(f"[ComfyUI] 连接错误 (第{attempt+1}次), {delay:.1f}s 后重试: {e}")
                    await asyncio.sleep(delay)
                    continue
                raise

            except httpx.HTTPStatusError:
                raise

        if last_exception:
            raise last_exception

    @property
    def is_degraded(self) -> bool:
        """ComfyUI 是否处于降级状态（连续 3 次以上 502）"""
        return self._consecutive_502_errors >= 3

    def reset_error_counter(self):
        """重置连续错误计数"""
        self._consecutive_502_errors = 0

    async def check_server_alive(self) -> bool:
        """检查 ComfyUI 服务器是否在线"""
        try:
            resp = await self._request_with_retry("get", f"{self.base_url}/system_stats")
            return resp.status_code == 200
        except Exception:
            return False

    async def get_available_models(self) -> list[str]:
        """获取 ComfyUI 可用 checkpoint 模型列表

        Returns:
            checkpoint 模型文件名列表
        """
        try:
            client = await self._get_client()
            resp = await client.get(f"{self.base_url}/object_info")
            data = resp.json()
            checkpoint_info = data.get("CheckpointLoaderSimple", {})
            input_info = checkpoint_info.get("input", {})
            required = input_info.get("required", {})
            ckpt_name = required.get("ckpt_name", [[]])
            if ckpt_name and len(ckpt_name) > 0 and isinstance(ckpt_name[0], list):
                return ckpt_name[0]
            return []
        except Exception:
            return []

    async def get_available_vaes(self) -> list[str]:
        """获取 ComfyUI 可用 VAE 模型列表

        Returns:
            VAE 模型文件名列表
        """
        try:
            client = await self._get_client()
            resp = await client.get(f"{self.base_url}/object_info")
            data = resp.json()
            vae_info = data.get("VAELoader", {})
            input_info = vae_info.get("input", {})
            required = input_info.get("required", {})
            vae_name = required.get("vae_name", [[]])
            if vae_name and len(vae_name) > 0 and isinstance(vae_name[0], list):
                return vae_name[0]
            return []
        except Exception:
            return []

    async def get_available_clips(self) -> list[str]:
        """获取 ComfyUI 可用 CLIP 模型列表

        Returns:
            CLIP 模型文件名列表
        """
        try:
            client = await self._get_client()
            resp = await client.get(f"{self.base_url}/object_info")
            data = resp.json()
            clip_info = data.get("CLIPLoader", {})
            input_info = clip_info.get("input", {})
            required = input_info.get("required", {})
            clip_name = required.get("clip_name", [[]])
            if clip_name and len(clip_name) > 0 and isinstance(clip_name[0], list):
                return clip_name[0]
            return []
        except Exception:
            return []

    async def get_available_unet_models(self) -> list[str]:
        """Get UNET models from UNETLoader (Flux etc.)"""
        try:
            client = await self._get_client()
            resp = await client.get(f"{self.base_url}/object_info")
            data = resp.json()
            unet_info = data.get("UNETLoader", {})
            input_info = unet_info.get("input", {})
            required = input_info.get("required", {})
            unet_name = required.get("unet_name", [[]])
            if unet_name and len(unet_name) > 0 and isinstance(unet_name[0], list):
                return unet_name[0]
            return []
        except Exception:
            return []

    async def get_available_loras(self) -> list[str]:
        """获取 ComfyUI 可用 LoRA 模型列表

        Returns:
            LoRA 模型文件名列表
        """
        try:
            client = await self._get_client()
            resp = await client.get(f"{self.base_url}/object_info")
            data = resp.json()
            lora_info = data.get("LoraLoader", {})
            input_info = lora_info.get("input", {})
            required = input_info.get("required", {})
            lora_name = required.get("lora_name", [[]])
            if lora_name and len(lora_name) > 0 and isinstance(lora_name[0], list):
                return lora_name[0]
            return []
        except Exception:
            return []

    async def upload_image_to_comfyui(self, local_path: str) -> str:
        """上传图片到 ComfyUI 的 input 目录，返回 ComfyUI 内部文件名

        Args:
            local_path: 本地图片路径

        Returns:
            ComfyUI input 目录中的文件名
        """
        client = await self._get_client()
        local_file = Path(local_path)
        with open(local_file, "rb") as f:
            files = {"image": (local_file.name, f, "image/png")}
            resp = await client.post(
                f"{self.base_url}/upload/image",
                files=files,
            )
            resp.raise_for_status()
            result = resp.json()
            return result.get("name", local_file.name)

    async def submit_workflow(self, workflow: dict) -> str:
        """提交工作流到 ComfyUI，返回 prompt_id

        Args:
            workflow: ComfyUI 工作流 dict（已注入参数）

        Returns:
            prompt_id 字符串，用于后续查询
        """
        payload = {"prompt": workflow}
        resp = await self._request_with_retry(
            "post",
            f"{self.base_url}/prompt",
            json=payload,
        )
        result = resp.json()
        return result.get("prompt_id", "")

    async def get_history(self, prompt_id: str) -> dict:
        """查询 prompt 执行历史/状态

        Returns:
            包含执行结果的 dict，未完成时为空
        """
        resp = await self._request_with_retry(
            "get",
            f"{self.base_url}/history/{prompt_id}"
        )
        return resp.json()

    async def get_queue_status(self) -> dict:
        """查询 ComfyUI 队列状态（排队 + 运行中）"""
        client = await self._get_client()
        resp = await client.get(f"{self.base_url}/queue")
        resp.raise_for_status()
        return resp.json()

    async def download_image(
        self, filename: str, subfolder: str = "", folder_type: str = "output"
    ) -> bytes:
        """从 ComfyUI 下载生成图片

        Args:
            filename: 图片文件名
            subfolder: 子文件夹路径
            folder_type: 类型（output/temp）

        Returns:
            图片二进制数据
        """
        client = await self._get_client()
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type,
        }
        resp = await client.get(
            f"{self.base_url}/view",
            params=params,
        )
        resp.raise_for_status()
        return resp.content

    async def cancel_task(self, prompt_id: str):
        """取消 ComfyUI 队列中的任务/释放资源"""
        client = await self._get_client()
        try:
            resp = await client.post(
                f"{self.base_url}/queue",
                json={"delete": [prompt_id]},
            )
            resp.raise_for_status()
        except Exception:
            pass  # 取消失败不阻塞主流程

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None


# 全局单例
comfyui_client = ComfyUIClient()
