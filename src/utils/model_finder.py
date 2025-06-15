from __future__ import annotations

"""model_finder

YOLO 学習/推論用 .pt ファイルを検索するユーティリティ。

使用例:

```
from src.utils.model_finder import find_latest_best_model
model_path = find_latest_best_model([Path('src/yolo'), Path('src/datasets')])
```
"""

import logging
from pathlib import Path
from typing import List

LOGGER = logging.getLogger(__name__)


def find_latest_best_model(search_dirs: List[Path]) -> Path:
    """search_dirs 配下から最新の best*.pt (なければ *.pt) を返す"""
    LOGGER.debug("モデル探索ディレクトリ: %s", ", ".join(str(d) for d in search_dirs))

    def collect(pattern: str) -> List[Path]:
        files: List[Path] = []
        for base in search_dirs:
            if base.exists():
                files.extend(base.rglob(pattern))
        return files

    candidates = collect("best*.pt") or collect("*.pt")
    if not candidates:
        raise FileNotFoundError("*.pt モデルが見つかりません")
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    LOGGER.info("選択されたモデル: %s", latest)
    return latest 