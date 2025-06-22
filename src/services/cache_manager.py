"""Unified CacheManager

画像プレビューキャッシュ (image_preview_cache) と OCR キャッシュ (ocr_tools/ocr_cache)
を一元的に扱うサービスクラス。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional
import json
import os

from src.utils.path_manager import PathManager
from src.services.cache_service import CacheService


class CacheManager:
    """image_preview_cache と OCR キャッシュの双方を管理するラッパ。"""

    def __init__(self, path_manager: PathManager | None = None):
        self.pm = path_manager or PathManager()
        self.image_cache = CacheService(base_dir=self.pm.yolo_image_cache_dir)
        # OCR キャッシュは ocr_tools/ocr_cache 配下 (ハッシュ+prefix 付きファイル).
        self.ocr_cache_dir: Path = self.pm.project_root / "ocr_tools" / "ocr_cache"
        self.ocr_cache_dir.mkdir(parents=True, exist_ok=True)

        # 汎用エンジン結果キャッシュ用ディレクトリ (将来拡張)
        self._engine_cache_root: Path = self.pm.project_root / "engine_cache"
        self._engine_cache_root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Image preview cache helpers
    # ------------------------------------------------------------------
    def load_image_cache_json(self, img_path: str | Path, *, full: bool = True) -> Any:
        return self.image_cache.load_cache_json(img_path, return_full=full)

    def get_image_cache_path(self, img_path: str | Path) -> Path:
        return self.image_cache.get_cache_path(img_path)

    # ------------------------------------------------------------------
    # OCR cache helpers – OCR キャッシュは caption_board_ocr_pipeline と同形式
    # ------------------------------------------------------------------
    def _ocr_cache_path(self, img_path: str | Path) -> Path:
        img_path = Path(img_path)
        h = self._sha1(img_path)
        return self.ocr_cache_dir / f"ocr_{h}.json"

    def load_ocr_cache(self, img_path: str | Path) -> Optional[dict]:
        p = self._ocr_cache_path(img_path)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def save_ocr_cache(self, img_path: str | Path, data: dict) -> bool:
        p = self._ocr_cache_path(img_path)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
        except OSError:
            return False

    # ------------------------------------------------------------------
    @staticmethod
    def _sha1(p: Path) -> str:
        import hashlib
        return hashlib.sha1(str(p).encode("utf-8")).hexdigest()

    # ================================================================
    # Unified engine cache I/F (DetectionEngine)
    # ================================================================
    def _engine_cache_path(self, img_path: str | Path, ns: str) -> Path:
        """ネームスペース毎にサブディレクトリを分割"""
        img_path = Path(img_path)
        fname = f"{self._sha1(img_path)}.json"
        return self._engine_cache_root / ns / fname

    def load_engine_cache(self, img_path: str | Path, ns: str) -> Optional[dict]:
        p = self._engine_cache_path(img_path, ns)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def save_engine_cache(self, img_path: str | Path, ns: str, data: dict) -> bool:
        p = self._engine_cache_path(img_path, ns)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
        except OSError:
            return False 