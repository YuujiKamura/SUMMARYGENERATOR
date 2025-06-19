"""ocr_value_pair_detector.py (legacy shim)

このモジュールは後方互換のために残していますが、実装は
ocr_tools.value_pairs.detect_value_pairs_from_boxes_enhanced へ完全委譲します。
今後は value_pairs.py を直接 import することを推奨します。
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .value_pairs import (
    detect_value_pairs_from_boxes_enhanced as _detect_impl,
)

__all__ = ["detect_value_pairs_from_boxes_enhanced"]

# グローバルキャッシュ: ルール読込は高コストなので1度だけ行う
_GLOBAL_DETECTOR = None  # type: ignore

def detect_value_pairs_from_boxes_enhanced(
    texts_with_boxes: List[Dict[str, Any]],
    keyword_list: Optional[Iterable[str]] = None,
    *,
    max_y_diff: int = 30,
    min_x_diff: int = 10,
) -> List[Dict[str, Any]]:  # noqa: D401
    """Thin wrapper that delegates to the new implementation in value_pairs.py."""
    global _GLOBAL_DETECTOR  # pylint: disable=global-statement

    # キーワードフィルタが無い場合はキャッシュされた PairDetector を使う
    if keyword_list is None and max_y_diff == 30 and min_x_diff == 10:
        if _GLOBAL_DETECTOR is None:
            from .pair_detector import PairDetector

            _GLOBAL_DETECTOR = PairDetector()  # 初回のみ CSV をロード
        return _GLOBAL_DETECTOR.detect(texts_with_boxes)

    # フィルタやパラメータが指定されている場合は従来通り新規生成
    return _detect_impl(
        texts_with_boxes,
        keyword_list=keyword_list,
        max_y_diff=max_y_diff,
        min_x_diff=min_x_diff,
    )