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


def detect_value_pairs_from_boxes_enhanced(
    texts_with_boxes: List[Dict[str, Any]],
    keyword_list: Optional[Iterable[str]] = None,
    *,
    max_y_diff: int = 30,
    min_x_diff: int = 10,
) -> List[Dict[str, Any]]:  # noqa: D401
    """Thin wrapper that delegates to the new implementation in value_pairs.py."""
    return _detect_impl(
        texts_with_boxes,
        keyword_list=keyword_list,
        max_y_diff=max_y_diff,
        min_x_diff=min_x_diff,
    )