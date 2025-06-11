"""
bbox_convert.py
YOLO正規化xywh <-> 絶対xyxy座標変換ユーティリティ
"""
from typing import Tuple

def xywh_norm_to_xyxy_abs(
    x: float, y: float, w: float, h: float, img_w: int, img_h: int
) -> Tuple[float, float, float, float]:
    """
    YOLO形式の正規化xywh(bbox中心・幅・高さ: 0.0-1.0)を
    画像サイズ基準の絶対座標(x1, y1, x2, y2)に変換する。

    Args:
        x, y: bbox中心座標（正規化値, 0.0-1.0）
        w, h: bbox幅・高さ（正規化値, 0.0-1.0）
        img_w, img_h: 画像の幅・高さ（ピクセル）

    Returns:
        (x1, y1, x2, y2): bbox左上・右下の絶対座標
    """
    cx = x * img_w
    cy = y * img_h
    bw = w * img_w
    bh = h * img_h
    x1 = cx - bw / 2
    y1 = cy - bh / 2
    x2 = cx + bw / 2
    y2 = cy + bh / 2
    return x1, y1, x2, y2

def xyxy_abs_to_xywh_norm(
    x1: float, y1: float, x2: float, y2: float, img_w: int, img_h: int
) -> Tuple[float, float, float, float]:
    """
    画像サイズ基準の絶対座標(x1, y1, x2, y2)を
    YOLO形式の正規化xywh(bbox中心・幅・高さ: 0.0-1.0)に変換する。

    Args:
        x1, y1, x2, y2: bbox左上・右下の絶対座標
        img_w, img_h: 画像の幅・高さ（ピクセル）

    Returns:
        (x, y, w, h): bbox中心・幅・高さ（正規化値, 0.0-1.0）
    """
    bw = x2 - x1
    bh = y2 - y1
    cx = x1 + bw / 2
    cy = y1 + bh / 2
    x = cx / img_w
    y = cy / img_h
    w = bw / img_w
    h = bh / img_h
    return x, y, w, h

# --- テスト関数 ---
def _test_bbox_convert():
    img_w, img_h = 1280, 960
    # 例: 画像中央に幅320,高さ240のbbox
    x, y, w, h = 0.5, 0.5, 0.25, 0.25
    x1, y1, x2, y2 = xywh_norm_to_xyxy_abs(x, y, w, h, img_w, img_h)
    assert abs(x1 - 480) < 1e-3
    assert abs(y1 - 360) < 1e-3
    assert abs(x2 - 800) < 1e-3
    assert abs(y2 - 600) < 1e-3
    # 逆変換
    x_, y_, w_, h_ = xyxy_abs_to_xywh_norm(x1, y1, x2, y2, img_w, img_h)
    assert abs(x_ - x) < 1e-6
    assert abs(y_ - y) < 1e-6
    assert abs(w_ - w) < 1e-6
    assert abs(h_ - h) < 1e-6
    print("bbox_convert.py テストOK")

if __name__ == "__main__":
    _test_bbox_convert() 