# -*- coding: utf-8 -*-
"""
训练素材自动筛选模块 V1
纯 Pillow + 标准库实现，零外部依赖。

三层管道：
  1. quality_score()      — 质量打分（锐度/分辨率/对比度/色彩）
  2. phash_dedup()        — 64-bit dHash 感知哈希去重
  3. composition_balance() — 构图均衡（元数据优先 + 纵横比兜底）

用法:
    from src.dataset_filter import DatasetFilter
    f = DatasetFilter(input_dir="data/raw", output_dir="training_dataset")
    report = f.run()
"""

import json
import math
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageStat


# ---------------------------------------------------------------------------
# 类型别名
# ---------------------------------------------------------------------------

ImageRecord = Dict[str, Any]


# ---------------------------------------------------------------------------
# 私有工具函数
# ---------------------------------------------------------------------------

def _image_extensions() -> set:
    """支持的图片扩展名集合。"""
    return {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}


def _is_image(path: Path) -> bool:
    """判断文件是否为支持的图片格式。"""
    return path.suffix.lower() in _image_extensions()


def _hamming_distance(a: int, b: int) -> int:
    """计算两个 64-bit 整数的汉明距离。"""
    return (a ^ b).bit_count()


def _compute_dhash(image: Image.Image) -> int:
    """
    计算图片的 64-bit dHash（差异哈希）。

    算法：resize(9x8) → 灰度 → 逐行左-右比较 → 64bit 整数。
    """
    img = image.convert("L").resize((9, 8), Image.LANCZOS)
    pixels = list(img.getdata())
    hash_bits = 0
    for row in range(8):
        for col in range(8):
            idx = row * 9 + col
            if pixels[idx] > pixels[idx + 1]:
                hash_bits |= 1 << (row * 8 + col)
    return hash_bits


def _compute_sharpness(image: Image.Image) -> float:
    """
    使用手工 3×3 Laplacian 卷积核计算锐度。

    Laplacian 核: [[0, 1, 0], [1, -4, 1], [0, 1, 0]]
    返回值 = 卷积结果的方差。
    """
    gray = image.convert("L")
    w, h = gray.size
    pixels = gray.load()
    values: List[float] = []
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            v = (
                pixels[x, y - 1]
                + pixels[x - 1, y]
                - 4 * pixels[x, y]
                + pixels[x + 1, y]
                + pixels[x, y + 1]
            )
            values.append(v)
    if not values:
        return 0.0
    n = len(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    return variance


def _compute_resolution_score(width: int, height: int) -> float:
    """
    分辨率评分：基于像素总数映射到 [0, 1]。

    >= 1024^2 → 1.0,  < 512^2 → 0.0, 中间线性插值。
    """
    pixels = width * height
    lo = 512 * 512      # 262,144
    hi = 1024 * 1024    # 1,048,576
    if pixels >= hi:
        return 1.0
    if pixels <= lo:
        return 0.0
    return (pixels - lo) / (hi - lo)


def _compute_contrast(image: Image.Image) -> float:
    """
    对比度：灰度直方图的标准差，归一化到 [0, 1]。
    灰度值范围 0-255，最大理论标准差约 127.5。
    """
    gray = image.convert("L")
    stat = ImageStat.Stat(gray)
    std = stat.stddev[0] if stat.stddev else 0.0
    return min(std / 127.5, 1.0)


def _compute_color_richness(image: Image.Image) -> float:
    """
    色彩丰富度：RGB 三通道各自标准差的均值，归一化到 [0, 1]。
    """
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")
    stat = ImageStat.Stat(image)
    if not stat.stddev or len(stat.stddev) < 3:
        return 0.0
    mean_std = sum(stat.stddev[i] for i in range(3)) / 3.0
    return min(mean_std / 127.5, 1.0)


def _quality_score(image: Image.Image) -> Tuple[float, Dict[str, float]]:
    """
    计算综合质量分（0-1），返回 (总分, 各维度分)。

    权重：锐度 0.40 | 分辨率 0.30 | 对比度 0.20 | 色彩 0.10
    """
    sharpness = _compute_sharpness(image)
    res = _compute_resolution_score(image.width, image.height)
    contrast = _compute_contrast(image)
    color = _compute_color_richness(image)

    # 锐度方差数值范围很大，用 log 压缩后 sigmoid 归一化
    sharpness_norm = 2.0 / (1.0 + math.exp(-sharpness / 10.0)) - 1.0

    total = (
        sharpness_norm * 0.40
        + res * 0.30
        + contrast * 0.20
        + color * 0.10
    )

    return total, {
        "sharpness": round(sharpness_norm, 4),
        "resolution": round(res, 4),
        "contrast": round(contrast, 4),
        "color_richness": round(color, 4),
    }


def _infer_composition_from_aspect(image: Image.Image) -> str:
    """
    纵横比兜底：根据 height/width 推断构图类型。

    映射规则（V1 启发式）:
        ar > 1.4        → 全身
        1.1 < ar <= 1.4 → 半身
        0.85 < ar <= 1.1 → 胸像
        0.6 < ar <= 0.85 → 特写
        ar <= 0.6       → 环境人像
    """
    w, h = image.width, image.height
    ar = h / w if w > 0 else 1.0
    if ar > 1.4:
        return "全身"
    elif ar > 1.1:
        return "半身"
    elif ar > 0.85:
        return "胸像"
    elif ar > 0.6:
        return "特写"
    else:
        return "环境人像"


def _read_metadata(image_path: Path) -> Optional[Dict[str, Any]]:
    """读取同名 .json 元数据文件，不存在则返回 None。"""
    json_path = image_path.with_suffix(".json")
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
    return None


# ---------------------------------------------------------------------------
# DatasetFilter 主类
# ---------------------------------------------------------------------------

class DatasetFilter:
    """
    训练素材自动筛选器。

    参数:
        input_dir:          原始素材目录
        output_dir:         筛选结果输出目录
        quality_threshold:  质量分最低阈值（低于此分进入 rejected）
        hamming_threshold:  dHash 汉明距离阈值（≤此值视为重复）
    """

    # 构图目标比例
    COMPOSITION_TARGETS: Dict[str, float] = {
        "全身": 0.45,
        "半身": 0.25,
        "胸像": 0.15,
        "特写": 0.10,
        "环境人像": 0.05,
    }

    def __init__(
        self,
        input_dir: str,
        output_dir: str = "training_dataset",
        quality_threshold: float = 0.15,
        hamming_threshold: int = 5,
    ) -> None:
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.quality_threshold = quality_threshold
        self.hamming_threshold = hamming_threshold

        # 管道状态
        self.records: List[ImageRecord] = []
        self.report: Dict[str, Any] = {}
        self.copy_errors: List[Dict[str, str]] = []

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def run(self) -> Dict[str, Any]:
        """
        执行完整筛选管道：
        1. 质量筛选    → rejected/
        2. 感知哈希去重 → duplicate/
        3. 构图均衡    → cluster_removed/
        4. 剩余        → selected/
        5. 写入 report.json
        """
        self._scan_images()
        if not self.records:
            return self._empty_report()

        total_input = len(self.records)

        # 第 1 层：质量打分 + 筛选
        self._stage_quality()

        active = [r for r in self.records if r.get("stage") in (None, "quality_passed")]

        # 第 2 层：感知哈希去重
        active = self._stage_dedup(active)

        # 第 3 层：构图均衡
        active = self._stage_balance(active)

        # 标记剩余为 selected
        for r in active:
            r["stage"] = "selected"

        # 收集最终状态
        rejected_list = [r for r in self.records if r.get("stage") == "rejected"]
        duplicate_list = [r for r in self.records if r.get("stage") == "duplicate"]
        cluster_removed_list = [r for r in self.records if r.get("stage") == "cluster_removed"]
        selected_list = [r for r in self.records if r.get("stage") == "selected"]

        # 输出目录
        self._copy_files(rejected_list, "rejected")
        self._copy_files(duplicate_list, "duplicate")
        self._copy_files(cluster_removed_list, "cluster_removed")
        self._copy_files(selected_list, "selected")

        # 生成报告
        self.report = {
            "config": {
                "quality_threshold": self.quality_threshold,
                "hamming_threshold": self.hamming_threshold,
                "composition_targets": dict(self.COMPOSITION_TARGETS),
            },
            "input_count": total_input,
            "copy_errors": self.copy_errors,
            "rejected_count": len(rejected_list),
            "duplicate_count": len(duplicate_list),
            "cluster_removed_count": len(cluster_removed_list),
            "selected_count": len(selected_list),
            "images": [
                {
                    "filename": r["filename"],
                    "path": str(r["path"]),
                    "quality_score": r.get("quality_score"),
                    "quality_details": r.get("quality_details"),
                    "dhash": r.get("dhash"),
                    "composition": r.get("composition"),
                    "composition_source": r.get("composition_source"),
                    "stage": r.get("stage"),
                    "reason": r.get("reason", ""),
                }
                for r in self.records
            ],
        }
        self._write_report()
        return self.report

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _scan_images(self) -> None:
        """扫描输入目录，构建初始记录列表。"""
        self.records = []
        if not self.input_dir.is_dir():
            return
        for fpath in sorted(self.input_dir.iterdir()):
            if fpath.is_file() and _is_image(fpath):
                self.records.append({
                    "filename": fpath.name,
                    "path": fpath,
                    "quality_score": None,
                    "quality_details": None,
                    "dhash": None,
                    "composition": None,
                    "composition_source": None,
                    "stage": None,
                    "reason": "",
                })

    def _stage_quality(self) -> None:
        """质量打分阶段：低于阈值标记为 rejected。"""
        for r in self.records:
            try:
                img = Image.open(r["path"]).convert("RGB")
                img.load()
                score, details = _quality_score(img)
                r["quality_score"] = round(score, 4)
                r["quality_details"] = details
                if score < self.quality_threshold:
                    r["stage"] = "rejected"
                    r["reason"] = f"质量分 {score:.4f} 低于阈值 {self.quality_threshold}"
                else:
                    r["stage"] = "quality_passed"
                img.close()
            except Exception as exc:
                r["quality_score"] = 0.0
                r["stage"] = "rejected"
                r["reason"] = f"图片读取失败: {exc}"

    def _stage_dedup(self, active: List[ImageRecord]) -> List[ImageRecord]:
        """
        感知哈希去重阶段。

        1. 为每张图计算 dHash
        2. 按汉明距离分组（距离 <= threshold 视为重复）
        3. 每组保留质量分最高的那张
        """
        # 计算所有活跃图片的 dHash
        for r in active:
            try:
                img = Image.open(r["path"]).convert("L")
                img.load()
                r["dhash"] = _compute_dhash(img)
                img.close()
            except Exception as exc:
                r["dhash"] = 0
                r["reason"] = (r.get("reason", "") + f" dHash 计算失败: {exc}").strip()

        # 按质量分降序排列（先处理高分图）
        active.sort(key=lambda r: r.get("quality_score") or 0, reverse=True)

        kept: List[ImageRecord] = []
        for r in active:
            is_dup = False
            for k in kept:
                dist = _hamming_distance(k.get("dhash", 0), r.get("dhash", 0))
                if dist <= self.hamming_threshold:
                    is_dup = True
                    break
            if is_dup:
                r["stage"] = "duplicate"
                r["reason"] = (
                    r.get("reason", "")
                    + f" 感知重复 (dHash 汉明距离 <= {self.hamming_threshold})"
                ).strip()
            else:
                kept.append(r)
        return kept

    def _stage_balance(self, active: List[ImageRecord]) -> List[ImageRecord]:
        """
        构图均衡阶段。

        1. 读取元数据获取 composition，无元数据则用纵横比兜底
        2. 按 composition 分组
        3. 每组超过目标比例的部分，按质量分从低到高剔除
        """
        total = len(active)
        if total == 0:
            return active

        # 获取每张图的构图类型
        for r in active:
            meta = _read_metadata(r["path"])
            if meta and "composition" in meta:
                comp = meta["composition"]
                if comp in self.COMPOSITION_TARGETS:
                    r["composition"] = comp
                    r["composition_source"] = "metadata"
                else:
                    try:
                        img = Image.open(r["path"]).convert("RGB")
                        img.load()
                        r["composition"] = _infer_composition_from_aspect(img)
                        img.close()
                    except Exception:
                        r["composition"] = "半身"
                    r["composition_source"] = "metadata_fallback_to_aspect"
            else:
                try:
                    img = Image.open(r["path"]).convert("RGB")
                    img.load()
                    r["composition"] = _infer_composition_from_aspect(img)
                    img.close()
                except Exception:
                    r["composition"] = "半身"
                r["composition_source"] = "aspect_ratio"

        # 按构图分组
        groups: Dict[str, List[ImageRecord]] = {}
        for r in active:
            comp = r.get("composition", "半身")
            groups.setdefault(comp, []).append(r)

        # 计算每组目标数量
        result: List[ImageRecord] = []
        for comp, target_ratio in self.COMPOSITION_TARGETS.items():
            members = groups.get(comp, [])
            target_count = max(1, round(total * target_ratio))
            if len(members) <= target_count:
                result.extend(members)
            else:
                # 按质量分升序排列，剔除最低分的多余图片
                members.sort(key=lambda r: r.get("quality_score") or 0)
                keep = members[-target_count:]
                remove = members[:-target_count]
                for r in remove:
                    r["stage"] = "cluster_removed"
                    r["reason"] = (
                        f"构图均衡剔除: '{comp}' 超出目标 "
                        f"({target_count}/{len(members)})"
                    )
                result.extend(keep)

        return result

    def _copy_files(self, records: List[ImageRecord], subdir: str) -> None:
        """将记录对应的文件复制到指定子目录，记录失败项到 self.copy_errors。"""
        if not records:
            return
        dest = self.output_dir / subdir
        dest.mkdir(parents=True, exist_ok=True)
        for r in records:
            src = r["path"]
            if src.exists():
                try:
                    shutil.copy2(src, dest / src.name)
                except OSError as exc:
                    self.copy_errors.append({
                        "filename": r["filename"],
                        "src": str(src),
                        "dest": str(dest / src.name),
                        "error": str(exc),
                    })

    def _write_report(self) -> None:
        """将报告写入 output_dir/report.json。"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        report_path = self.output_dir / "report.json"
        report_copy = json.loads(
            json.dumps(self.report, ensure_ascii=False, default=str)
        )
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_copy, f, ensure_ascii=False, indent=2)
        print(f"[DatasetFilter] 报告已写入: {report_path}")

    def _empty_report(self) -> Dict[str, Any]:
        """无图片时的空报告。"""
        self.report = {
            "input_count": 0,
            "rejected_count": 0,
            "duplicate_count": 0,
            "cluster_removed_count": 0,
            "selected_count": 0,
            "images": [],
        }
        return self.report