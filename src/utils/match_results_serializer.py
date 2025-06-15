from __future__ import annotations

"""match_results_serializer

画像⇄ChainRecord マッチ結果を汎用 JSON 形式へシリアライズするユーティリティ。
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def _record_to_dict(rec: Any) -> Dict[str, Any]:
    if rec is None:
        return {}
    if hasattr(rec, "to_dict"):
        return rec.to_dict()
    if isinstance(rec, dict):
        return rec
    if hasattr(rec, "__dict__"):
        return dict(rec.__dict__)
    return {"value": str(rec)}


def to_dict_list(
    match_results: Dict[str, List[Any]],
    *,
    image_roles: Optional[Dict[str, List[str]]] = None,
    image_bboxes: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> List[Dict[str, Any]]:
    """match_results を JSON シリアライズしやすいリストに変換"""
    image_roles = image_roles or {}
    image_bboxes = image_bboxes or {}

    items: List[Dict[str, Any]] = []
    for img_path, recs in match_results.items():
        items.append({
            "image_path": img_path,
            "roles": image_roles.get(img_path, []),
            "bboxes": image_bboxes.get(img_path, []),
            "matched_records": [_record_to_dict(r) for r in recs],
        })
    return items


def save_json(
    match_results: Dict[str, List[Any]],
    out_path: Path | str,
    *,
    image_roles: Optional[Dict[str, List[str]]] = None,
    image_bboxes: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ensure_ascii: bool = False,
    indent: int = 2,
) -> None:
    """match_results を JSON ファイルに保存"""
    data = to_dict_list(match_results, image_roles=image_roles, image_bboxes=image_bboxes)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent) 