"""
bbox変換・clip・valid判定などYOLO bbox操作ユーティリティ
"""
from decimal import Decimal, ROUND_HALF_UP, getcontext
from src.utils.bbox_convert import xywh_norm_to_xyxy_abs, xyxy_abs_to_xywh_norm
from src.utils.bbox_normalizer import is_bbox_valid_yolo

getcontext().prec = 10

def horizontal_flip_bbox(bbox):
    class_id, x, y, w, h = bbox
    x_flipped = 1.0 - x
    return [class_id, x_flipped, y, w, h]

def norm01(x):
    return float(max(Decimal('0.0'), min(Decimal(str(x)), Decimal('1.0'))))

def is_bbox_valid(b):
    return is_bbox_valid_yolo(*b)

def clip_bbox_with_imgsize(b, img_w, img_h):
    class_id, x, y, w, h = b
    x = Decimal(str(x))
    y = Decimal(str(y))
    w = Decimal(str(w))
    h = Decimal(str(h))
    img_w_d = Decimal(str(img_w))
    img_h_d = Decimal(str(img_h))
    x1, y1, x2, y2 = xywh_norm_to_xyxy_abs(float(x), float(y), float(w), float(h), int(img_w), int(img_h))
    x1 = Decimal(str(x1)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    y1 = Decimal(str(y1)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    x2 = Decimal(str(x2)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    y2 = Decimal(str(y2)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    x1 = max(Decimal('0.0'), min(x1, img_w_d))
    y1 = max(Decimal('0.0'), min(y1, img_h_d))
    x2 = max(Decimal('0.0'), min(x2, img_w_d))
    y2 = max(Decimal('0.0'), min(y2, img_h_d))
    if x2 <= x1 or y2 <= y1:
        return None
    x_c, y_c, w_c, h_c = xyxy_abs_to_xywh_norm(float(x1), float(y1), float(x2), float(y2), int(img_w), int(img_h))
    x_c = Decimal(str(x_c)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    y_c = Decimal(str(y_c)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    w_c = Decimal(str(w_c)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    h_c = Decimal(str(h_c)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    x_c = max(Decimal('0.0'), min(x_c, Decimal('1.0')))
    y_c = max(Decimal('0.0'), min(y_c, Decimal('1.0')))
    w_c = max(Decimal('0.0'), min(w_c, Decimal('1.0')))
    h_c = max(Decimal('0.0'), min(h_c, Decimal('1.0')))
    if w_c <= 0 or h_c <= 0:
        return None
    return [class_id, float(x_c), float(y_c), float(w_c), float(h_c)]

def clip01(x):
    return max(0.0, min(1.0, float(x)))

def clip_bbox01(bbox):
    class_id, x, y, w, h = bbox
    x = max(0.0, min(1.0, x))
    y = max(0.0, min(1.0, y))
    w = max(0.0, min(1.0, w))
    h = max(0.0, min(1.0, h))
    return [class_id, x, y, w, h]
