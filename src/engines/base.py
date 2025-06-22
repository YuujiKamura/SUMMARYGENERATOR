"""Engine base protocol for unified detection/OCR pipeline."""
from __future__ import annotations

from typing import Protocol, Dict, Any


class DetectionEngine(Protocol):
    """共通推論エンジン I/F (YOLO, OCR 等)"""

    name: str          # human-readable id ("yolo", "ocr")
    cache_ns: str      # CacheManager に保存する名前空間キー

    def detect(self, img_path: str) -> Dict[str, Any]:
        """画像を処理し結果 dict を返す。キャッシュに保存しやすい構造にする。"""
        ... 