from __future__ import annotations

from typing import Dict, Any

from src.engines.base import DetectionEngine

# 遅延 import で YOLO 関連の重い依存を回避
class YoloDetectionEngine(DetectionEngine):
    """YOLOv8 bbox 検出エンジンを共通 I/F でラップ"""

    name = "yolo"
    cache_ns = "yolo_bboxes"

    def __init__(self, model: str | None = None):
        from src.yolo_predict_core import YoloPredictCore  # type: ignore
        self.core = YoloPredictCore(weights=model)

    # -------------------------------------------------------------
    def detect(self, img_path: str) -> Dict[str, Any]:
        bboxes = self.core.predict(img_path)
        return {"bboxes": [b.as_dict() if hasattr(b, "as_dict") else b for b in bboxes]} 