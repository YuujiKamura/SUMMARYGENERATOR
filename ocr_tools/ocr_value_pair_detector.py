import re
from typing import List, Dict, Any

def detect_value_pairs_from_boxes(
    texts_with_boxes: List[Dict[str, Any]],
    keyword_list=None,
    value_pattern=r"([0-9]+\.[0-9]+|[0-9]+)\s*℃",
    max_y_diff=30,
    min_x_diff=10
) -> List[Dict[str, Any]]:
    """
    texts_with_boxes: [{"text": str, "x": int, "y": int}, ...]
    keyword_list: 検出したいキーワード（例：['到着温度']）
    value_pattern: 値の正規表現
    max_y_diff: y座標の許容差
    min_x_diff: x座標の最小差（右側判定）
    Returns: [{"keyword":..., "value":..., "value_text":..., "keyword_box":..., "value_box":...}, ...]
    """
    if keyword_list is None:
        keyword_list = ["到着温度"]
    results = []
    for kw in keyword_list:
        print(f"[LOG] キーワード候補抽出: '{kw}'")
        kw_boxes = [b for b in texts_with_boxes if kw in b.get("text", "")]
        for kw_box in kw_boxes:
            x0, y0 = kw_box["x"], kw_box["y"]
            print(f"  [LOG]  キーワード検出: text='{kw_box['text']}', x={x0}, y={y0}")
            value_boxes = []
            for b in texts_with_boxes:
                if b is kw_box:
                    continue
                m = re.search(value_pattern, b.get("text", ""))
                if m and (b["x"] > x0 + min_x_diff) and (abs(b["y"] - y0) <= max_y_diff):
                    print(f"    [LOG]   候補値: text='{b['text']}', x={b['x']}, y={b['y']}, value={m.group(1)}")
                    value_boxes.append((b, float(m.group(1))))
            if value_boxes:
                value_box, value = min(value_boxes, key=lambda t: t[0]["x"])
                print(f"  [LOG]  ペア決定: keyword='{kw}', value='{value}', value_text='{value_box['text']}'")
                results.append({
                    "keyword": kw,
                    "value": value,
                    "value_text": value_box["text"],
                    "keyword_box": kw_box,
                    "value_box": value_box
                })
            else:
                print(f"  [LOG]  値候補なし")
    print(f"[LOG] 検出結果: {results}")
    return results 