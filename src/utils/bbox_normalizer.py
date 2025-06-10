"""
YOLO/xyxy bbox正規化・検証の共通モジュール
今後は全てのbbox正規化処理をここに集約すること
"""

def xyxy_to_yolo(xyxy, img_w, img_h):
    x_min, y_min, x_max, y_max = map(float, xyxy)
    x_center = (x_min + x_max) / 2 / img_w
    y_center = (y_min + y_max) / 2 / img_h
    width = (x_max - x_min) / img_w
    height = (y_max - y_min) / img_h
    return x_center, y_center, width, height

def yolo_to_xyxy(x, y, w, h, img_w, img_h):
    x_min = (x - w / 2) * img_w
    y_min = (y - h / 2) * img_h
    x_max = (x + w / 2) * img_w
    y_max = (y + h / 2) * img_h
    return x_min, y_min, x_max, y_max

def is_bbox_valid_xyxy(xyxy, img_w, img_h):
    x_min, y_min, x_max, y_max = map(float, xyxy)
    w = x_max - x_min
    h = y_max - y_min
    if w <= 0 or h <= 0:
        return False
    if not (0 <= x_min < img_w and 0 <= x_max <= img_w and 0 <= y_min < img_h and 0 <= y_max <= img_h):
        return False
    return True

def is_bbox_valid_yolo(x, y, w, h):
    return 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 and 0.0 < w <= 1.0 and 0.0 < h <= 1.0

def convert_bbox_to_yolo(bbox, img_w, img_h):
    """
    dict型 or list/tuple型両対応でYOLO形式(x_center, y_center, w, h)に変換しclass_idも返す
    """
    if isinstance(bbox, dict):
        vals = bbox.get('bbox') or bbox.get('xywh') or bbox.get('xyxy')
        if vals and len(vals) == 4:
            x_min, y_min, x_max, y_max = map(float, vals)
            class_id = int(bbox.get('cid', bbox.get('class_id', 0)))
        else:
            x_min = float(bbox.get("x_min", 0))
            y_min = float(bbox.get("y_min", 0))
            x_max = float(bbox.get("x_max", 0))
            y_max = float(bbox.get("y_max", 0))
            class_id = int(bbox.get("class_id", 0))
    else:
        if len(bbox) < 5:
            raise ValueError(f"bboxリストの要素数が不足: {bbox}")
        x_min, y_min, x_max, y_max = map(float, bbox[:4])
        class_id = int(bbox[4])
    # min/max正規化
    x_min, x_max = min(x_min, x_max), max(x_min, x_max)
    y_min, y_max = min(y_min, y_max), max(y_min, y_max)
    x_center = (x_min + x_max) / 2 / img_w
    y_center = (y_min + y_max) / 2 / img_h
    width = (x_max - x_min) / img_w
    height = (y_max - y_min) / img_h
    return class_id, x_center, y_center, width, height
