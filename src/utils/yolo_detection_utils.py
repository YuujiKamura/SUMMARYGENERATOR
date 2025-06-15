from __future__ import annotations

"""yolo_detection_utils

YOLO 推論結果(dict) から image_roles / image_bboxes へ変換する補助関数。
"""

from typing import Dict, List, Tuple, Any
from pathlib import Path
from src.utils.yolo_predict_cli import detect_boxes_with_yolo


def split_roles_bboxes(det_results: Dict[str, List[Tuple[int, str, float, list]]]) -> tuple[
    Dict[str, List[str]], Dict[str, List[Dict[str, Any]]]
]:
    """detect_boxes_with_yolo の戻り値を image_roles / image_bboxes に変換"""
    image_roles: Dict[str, List[str]] = {}
    image_bboxes: Dict[str, List[Dict[str, Any]]] = {}

    for img_path, detections in det_results.items():
        roles = []
        bboxes = []
        for class_id, class_name, conf_score, xyxy in detections:
            roles.append(class_name)
            bboxes.append({
                "bbox": xyxy,
                "role": class_name,
                "confidence": conf_score,
            })
        image_roles[img_path] = list(set(roles))
        image_bboxes[img_path] = bboxes

    return image_roles, image_bboxes


# -----------------------------------------------------------------------------
# Convenience: run YOLO detection on directory
# -----------------------------------------------------------------------------

def detect_dir(
    image_dir: Path | str,
    model_path: str,
    *,
    conf: float = 0.10,
) -> Dict[str, List[tuple]]:
    """image_dir 配下画像を detect_boxes_with_yolo で推論し dict を返す"""
    image_dir = Path(image_dir)
    image_files = sorted(
        str(p)
        for p in image_dir.rglob('*')
        if p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
    )
    if not image_files:
        raise FileNotFoundError(f"画像が見つかりません: {image_dir}")
    return detect_boxes_with_yolo(image_files, model_path, confidence=conf) 