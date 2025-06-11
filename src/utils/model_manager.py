"""
YOLO モデルの検出とメタ情報取得を担当。
"""
from __future__ import annotations
import datetime as _dt
import os
from pathlib import Path
from typing import Dict, List, Tuple

class ModelManager:
    """プリセット / トレーニング済みモデルの探索."""

    def __init__(self) -> None:
        self.models: Dict[str, Dict[str, dict]] = {
            "プリセットモデル": {},
            "トレーニング済みモデル": {},
        }
        self._discover()

    # ---------- 公開 API ---------- #
    def categories(self) -> List[str]:
        return list(self.models)

    def entries(self, category: str) -> List[Tuple[str, dict]]:
        return list(self.models.get(category, {}).items())

    def info(self, path: str) -> dict | None:
        for cat in self.models.values():
            if path in cat:
                return cat[path]
        return None

    def get_default_model(self) -> Tuple[str, dict] | None:
        """デフォルトモデル取得（優先モデル廃止のためNone固定）"""
        return None

    # ---------- 内部 ---------- #
    def _discover(self) -> None:
        from src.utils.path_manager import path_manager
        self.models = {
            "プリセットモデル": {},
            "トレーニング済みモデル": {},
        }
        for search_dir in path_manager.model_search_dirs:
            for pt in search_dir.rglob("*.pt"):
                # カテゴリ・experiment名の判定
                rel = pt.relative_to(search_dir)
                experiment = None
                category = "プリセットモデル"
                if "datasets" in str(search_dir):
                    experiment = rel.parts[0] if len(rel.parts) > 1 else None
                    category = "トレーニング済みモデル"
                else:
                    category = "プリセットモデル"
                self.models[category][str(pt)] = {
                    "name": pt.name,
                    "path": str(pt),
                    "size": self._fmt(pt.stat().st_size),
                    "modified": _dt.datetime.fromtimestamp(pt.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                    "experiment": experiment,
                    "type": self._guess_type(pt.name),
                }

    @staticmethod
    def _guess_type(name: str) -> str:
        lower = name.lower()
        if "yolov8" in lower:
            return "YOLOv8"
        if "yolov11" in lower:
            return "YOLOv11"
        if "best" in lower or "last" in lower:
            return "トレーニング済み"
        return "不明"

    @staticmethod
    def _fmt(size: int) -> str:
        for u in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{int(size):.1f}{u}"
            size = int(size / 1024)
        return f"{int(size):.1f}TB"