# -*- coding: utf-8 -*-
"""WD14 Tagger - ????????
?? WaifuDiffusion v1.4 ViT ????? ONNX Runtime ??
"""

import logging
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Tuple, List, Optional
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)

# ?? dbimutils ????? cv2 ???? numpy ??? ??

def _make_square(img: np.ndarray, target_size: int) -> np.ndarray:
    """????????????????"""
    old_h, old_w = img.shape[:2]
    desired_size = max(old_h, old_w, target_size)
    delta_w = desired_size - old_w
    delta_h = desired_size - old_h
    top, bottom = delta_h // 2, delta_h - (delta_h // 2)
    left, right = delta_w // 2, delta_w - (delta_w // 2)
    color = [255, 255, 255]
    if len(img.shape) == 2:
        img = np.stack([img] * 3, axis=-1)
    new_im = np.full((desired_size, desired_size, img.shape[2]), 255, dtype=img.dtype)
    new_im[top:top + old_h, left:left + old_w] = img
    return new_im


def _smart_resize(img: np.ndarray, size: int) -> np.ndarray:
    """???????????"""
    from PIL import Image as PILImage
    pil_img = PILImage.fromarray(img)
    if pil_img.size[0] > size or pil_img.size[1] > size:
        pil_img.thumbnail((size, size), PILImage.LANCZOS)
    else:
        pil_img = pil_img.resize((size, size), PILImage.LANCZOS)
    return np.asarray(pil_img)


# ?? WD14 Tagger ??? ??

class WD14Tagger:
    """Waifu Diffusion 1.4 ViT ?????

    ?? ONNX Runtime ????????????
    ?????model.onnx + selected_tags.csv
    """

    def __init__(
        self,
        model_path: str = "",
        tags_csv_path: str = "",
        gpu: bool = True,
    ) -> None:
        """
        Args:
            model_path: model.onnx ???????????????
            tags_csv_path: selected_tags.csv ????
            gpu: ???? CUDA ???? GPU ????? CPU
        """
        # ??????? tag ?????????
        _base = Path(__file__).resolve().parent.parent / "tag" / "stable-diffusion-webui-wd14-tagger-master" / "stable-diffusion-webui-wd14-tagger-master" / "extensions" / "wd-v1-4-vit-tagger"
        self.model_path = Path(model_path) if model_path else _base / "model.onnx"
        self.tags_csv_path = Path(tags_csv_path) if tags_csv_path else _base / "selected_tags.csv"
        self.gpu = gpu
        self._model = None
        self._tags: Optional[pd.DataFrame] = None
        self._input_height: int = 0

    def load(self) -> None:
        """?? ONNX ??????"""
        if self._model is not None:
            return

        if not self.model_path.exists():
            raise FileNotFoundError(f"???????: {self.model_path}")
        if not self.tags_csv_path.exists():
            raise FileNotFoundError(f"???????: {self.tags_csv_path}")

        import onnxruntime as ort

        providers: List[str] = (
            ["CUDAExecutionProvider", "CPUExecutionProvider"]
            if self.gpu
            else ["CPUExecutionProvider"]
        )
        try:
            self._model = ort.InferenceSession(str(self.model_path), providers=providers)
        except Exception as e:
            if self.gpu:
                logger.warning(f"CUDA ??????? CPU: {e}")
                self._model = ort.InferenceSession(str(self.model_path), providers=["CPUExecutionProvider"])
            else:
                raise

        # ????????
        input_shape = self._model.get_inputs()[0].shape
        self._input_height = input_shape[1]  # type: ignore[index]

        # ?????
        self._tags = pd.read_csv(str(self.tags_csv_path))
        logger.info(f"WD14 Tagger ????????={self._input_height}????={len(self._tags)}")

    def unload(self) -> None:
        """??????"""
        if self._model is not None:
            del self._model
            self._model = None
            self._tags = None
            logger.info("WD14 Tagger ???")

    def interrogate(
        self,
        image: Image.Image,
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """?????????

        Args:
            image: PIL Image ??

        Returns:
            (ratings, tags): ????????????? -> ??? 0~1?
        """
        if self._model is None or self._tags is None:
            self.load()
        assert self._model is not None and self._tags is not None

        # ?? ????? ??
        # Alpha ???????
        image = image.convert("RGBA")
        new_image = Image.new("RGBA", image.size, "WHITE")
        new_image.paste(image, mask=image)
        image = new_image.convert("RGB")

        arr = np.asarray(image)
        # PIL RGB ? OpenCV BGR????? BGR ???
        arr = arr[:, :, ::-1]

        arr = _make_square(arr, self._input_height)
        arr = _smart_resize(arr, self._input_height)
        arr = arr.astype(np.float32)
        arr = np.expand_dims(arr, 0)

        # ?? ONNX ?? ??
        input_name = self._model.get_inputs()[0].name
        output_name = self._model.get_outputs()[0].name
        confidents = self._model.run([output_name], {input_name: arr})[0]

        # ?? ???? ??
        tags_df = self._tags[:][["name"]]
        tags_df["confidents"] = confidents[0]

        # ? 4 ?????general, sensitive, questionable, explicit?
        ratings = dict(zip(
            tags_df["name"].iloc[:4].tolist(),
            tags_df["confidents"].iloc[:4].tolist(),
        ))

        # ???????
        tags = dict(zip(
            tags_df["name"].iloc[4:].tolist(),
            tags_df["confidents"].iloc[4:].tolist(),
        ))

        return ratings, tags

    def postprocess_tags(
        self,
        tags: Dict[str, float],
        threshold: float = 0.35,
        additional_tags: Optional[List[str]] = None,
        exclude_tags: Optional[List[str]] = None,
        sort_by_alphabetical_order: bool = False,
        add_confident_as_weight: bool = False,
        replace_underscore: bool = True,
        escape_tag: bool = False,
    ) -> Dict[str, float]:
        """???????????????

        Args:
            tags: interrogate ???????
            threshold: ??????0~1????????????
            additional_tags: ???????
            exclude_tags: ???????
            sort_by_alphabetical_order: True=???, False=?????
            add_confident_as_weight: ??????? `:???`
            replace_underscore: ????????
            escape_tag: ???????

        Returns:
            ???? {???: ???} ??
        """
        additional_tags = additional_tags or []
        exclude_tags = exclude_tags or []

        for t in additional_tags:
            tags[t] = 1.0

        tags = {
            t: c
            for t, c in sorted(
                tags.items(),
                key=lambda i: i[0 if sort_by_alphabetical_order else 1],
                reverse=not sort_by_alphabetical_order,
            )
            if c >= threshold and t not in exclude_tags
        }

        new_tags: Dict[str, float] = {}
        for tag, conf in tags.items():
            new_tag = tag
            if replace_underscore:
                new_tag = new_tag.replace("_", " ")
            if add_confident_as_weight:
                new_tag = f"({new_tag}:{conf:.2f})"
            new_tags[new_tag] = conf

        return new_tags


# ?? ???? ??

_tagger: Optional[WD14Tagger] = None


def get_tagger(model_path: str = "", tags_csv_path: str = "", gpu: bool = True) -> WD14Tagger:
    """???? WD14Tagger ???????"""
    global _tagger
    if _tagger is None:
        _tagger = WD14Tagger(model_path=model_path, tags_csv_path=tags_csv_path, gpu=gpu)
        _tagger.load()
    return _tagger
