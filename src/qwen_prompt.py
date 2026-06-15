# -*- coding: utf-8 -*-
"""Prompt 优化管线：中文润色 + ComfyUI 转换"""
import json, logging, os, re
from .qwen_client import QwenClient, QwenAPIError
from .models import PromptPolishResult, PromptConvertResult
logger = logging.getLogger(__name__)

SYSTEM_POLISH = (
    "你是一个 AI 绘画提示词优化专家。\n"
    "用户会用口语化、碎片化、不标准的中文描述想要的画面。\n"
    "你需要将其扩展润色为一段完整、优美、富有画面感的标准中文。\n\n"
    "【规则】\n"
    "1. 补全缺失的细节：服饰材质、光影方向、氛围情绪、构图视角、色彩倾向\n"
    "2. 保持用户原意，不编造用户没提到的核心主体\n"
    "3. 如有风格关键词（仙侠/科幻/古风/赛博朋克等），保留并围绕它展开\n"
    "4. 输出纯文本一段话，80-150 字，语言优美但不浮夸\n"
    "5. 不要输出任何 JSON、解释、前缀，只输出润色后的中文文本\n\n"
    "【示例】\n"
    "输入：一个女的在打架 穿白衣服 背景是山\n"
    "输出：一位白衣女剑客，身姿矫健，正在山巅与人激战。衣袂翻飞如流云，身后是连绵苍山与翻涌云海。逆光勾勒出轮廓，仙侠风格，动态感十足。"
)

SYSTEM_CONVERT = (
    "你是一个 ComfyUI / Stable Diffusion 的英文 Prompt 工程师。\n"
    "你会收到一段标准的中文画面描述，需要转换为英文 danbooru 风格标签。\n\n"
    "【输出格式 - 严格 JSON，不要任何额外文字】\n"
    "示例格式：{\"positive\":\"英文标签，逗号分隔\",\"negative\":\"负向标签\",\"params\":{\"width\":512,\"height\":768,\"steps\":20,\"cfg\":7.0}}\n"
    "务必只输出 JSON，不要带任何解释文字。\n\n"
    "【规则】\n"
    "1. positive 按此顺序排列：质量词 > 主体 > 服饰 > 动作 > 场景 > 光影 > 风格\n"
    "2. positive 以 masterpiece, best quality, newest 开头\n"
    "3. 人物用 1girl/1boy/1other 标签\n"
    "4. 全部用小写英文，逗号+空格分隔，无句号\n"
    "5. negative 默认：lowres, bad anatomy, bad hands, extra fingers, poorly drawn hands, poorly drawn face, deformed, blurry, watermark\n"
    "6. 根据画面自动判断横竖构图：人像用 512x768，场景用 768x512\n"
    "7. steps 默认 20，复杂多人场景设为 25-30\n"
    "8. cfg 默认 7.0\n"
    "9. 如果中文提到风格，追加对应英文触发词（仙侠->xianxia, 科幻->sci-fi, 古风->chinese ancient style, 赛博朋克->cyberpunk）\n"
    "10. 根据描述补全光影标签（cinematic lighting / rim light / soft light 等）"
)

class QwenPromptPipeline:
    """两段式 Prompt 优化管线"""

    def __init__(self):
        self._client = QwenClient()

    async def polish(self, raw_idea: str) -> PromptPolishResult:
        """阶段1: 粗糙中文 -> 标准中文 (temperature=0.8)"""
        logger.info(f"[润色] 收到输入 ({len(raw_idea)} 字)")
        try:
            result = await self._client.chat(
                system_prompt=SYSTEM_POLISH,
                user_message=raw_idea,
                temperature=0.8,
                max_tokens=8169,
            )
            logger.info(f"[润色] 输出 ({len(result)} 字): {result[:60]}...")
            return PromptPolishResult(original=raw_idea, polished=result)
        except QwenAPIError as e:
            logger.error(f"[润色] 失败: {e}")
            raise

    async def convert(self, chinese_prompt: str) -> PromptConvertResult:
        """阶段2: 标准中文 -> ComfyUI 英文 JSON (temperature=0.3)"""
        logger.info(f"[转换] 收到输入 ({len(chinese_prompt)} 字)")
        try:
            raw = await self._client.chat(
                system_prompt=SYSTEM_CONVERT,
                user_message=chinese_prompt,
                temperature=0.3,
                max_tokens=8169,
            )
            data = self._parse_json(raw)
            logger.info(f"[转换] positive={len(data['positive'])} chars")
            return PromptConvertResult(
                chinese_prompt=chinese_prompt,
                positive=data["positive"],
                negative=data.get("negative", ""),
                params=data.get("params", {}),
                raw_response=raw,
            )
        except QwenAPIError as e:
            logger.error(f"[转换] Qwen 失败: {e}")
            raise
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"[转换] JSON 解析失败: {e}")
            raise ValueError(f"模型返回格式异常: {str(e)[:200]}")

    def _parse_json(self, raw: str) -> dict:
        """JSON 容错解析：直接解析 -> 正则兜底"""
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise ValueError(f"无法从输出提取 JSON: {raw[:200]}")

    def inject_workflow(
        self, positive: str, negative: str, params: dict, workflow_type: str = "character"
    ) -> dict:
        """将 Prompt 注入 ComfyUI 工作流模板"""
        wf_map = {"character": "character.json", "costume": "costume.json",
                   "scene": "scene.json", "img2img": "img2img.json"}
        wf_name = wf_map.get(workflow_type, "character.json")
        wf_path = os.path.join(os.path.dirname(__file__), "..", "workflows", wf_name)
        with open(wf_path, "r", encoding="utf-8") as f:
            wf = json.load(f)
        if "5" in wf: wf["5"]["inputs"]["text"] = positive
        if "6" in wf: wf["6"]["inputs"]["text"] = negative
        if "7" in wf:
            wf["7"]["inputs"]["width"] = params.get("width", 512)
            wf["7"]["inputs"]["height"] = params.get("height", 768)
        if "8" in wf:
            wf["8"]["inputs"]["steps"] = params.get("steps", 20)
            wf["8"]["inputs"]["cfg"] = params.get("cfg", 7.0)
        return wf




    # ============================================================
    # System Prompt: 图片描述 -> Prompt
    # ============================================================
    SYSTEM_DESCRIBE_IMAGE = (
        "你是一个 AI 图像分析和 Prompt 生成专家。\n"
        "你会看到一张图片，需要完成以下任务：\n\n"
        "1. 用一段流畅优美的中文描述图片内容（主体、服饰、场景、光影、风格）\n"
        "2. 将描述转化为 ComfyUI / Stable Diffusion 可用的英文 danbooru 风格标签\n"
        "3. 推荐合适的生成参数\n\n"
        "【输出格式 - 严格 JSON，不要任何额外文字】\n"
        '{"chinese_desc":"优美的中文画面描述，80-150字",'
        '"positive":"英文标签，逗号分隔，以 masterpiece, best quality 开头",'
        '"negative":"英文负向标签",'
        '"params":{"width":512,"height":768,"steps":20,"cfg":7.0}}\n\n'
        "【规则】\n"
        "1. chinese_desc 要描述图片中实际的内容和风格，语言优美\n"
        "2. positive 提取图片中的关键视觉元素作为标签\n"
        "3. 推断图片的风格（写实/二次元/水墨/3D等）并加入标签\n"
        "4. 如果图片有明显主体人物，以 1girl/1boy 开头\n"
        "5. negative 默认：lowres, bad anatomy, bad hands, extra fingers, "
        "poorly drawn hands, poorly drawn face, deformed, blurry, watermark\n"
        "6. 根据图片宽高比推断合适的生成尺寸\n"
        "7. 务必只输出 JSON，不要带任何解释文字"
    )

    async def describe_image(
        self, image_base64: str, image_mime: str = "image/png"
    ) -> dict:
        logger.info(f"[图片分析] 收到图片 ({image_mime})")
        try:
            raw = await self._client.chat_vision(
                system_prompt=self.SYSTEM_DESCRIBE_IMAGE,
                user_text="请分析这张图片，输出 JSON。",
                image_base64=image_base64,
                image_mime=image_mime,
                temperature=0.5,
                max_tokens=8169,
            )
            data = self._parse_json(raw)
            logger.info(f"[图片分析] 中文描述={len(data.get('chinese_desc', ''))} 字")
            return {
                "chinese_desc": data.get("chinese_desc", ""),
                "positive": data.get("positive", ""),
                "negative": data.get("negative", ""),
                "params": data.get("params", {}),
                "raw_response": raw,
            }
        except QwenAPIError as e:
            logger.error(f"[图片分析] Qwen 失败: {e}")
            raise
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"[图片分析] JSON 解析失败: {e}")
            raise ValueError(f"模型返回格式异常: {str(e)[:200]}")


pipeline = QwenPromptPipeline()