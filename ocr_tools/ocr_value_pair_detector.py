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

def detect_location_value_pairs(
    texts_with_boxes: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    「場所」キーワードとその値（測点名称）を検出
    同一テキストボックス内や近隣テキストボックスから検出する    """
    results = []
    location_keyword = "場所"
    
    print(f"[LOG] 場所キーワード検出開始: '{location_keyword}'")
    
    # 同一テキストボックス内での検出
    for box in texts_with_boxes:
        text = box.get("text", "")
        if "場所" in text or "場 所" in text:  # スペース入りもサポート
            print(f"  [LOG] 場所キーワード発見: text='{text}', x={box['x']}, y={box['y']}")
            
            # パターン1: "場所 小山" or "場所小山" or "場 所 小山" 形式（No.付きも含む）
            pattern1 = re.search(r"場\s*所\s*([^\s\n|]+(?:\s*No\.\d+)?)", text)
            if pattern1:
                location_value = pattern1.group(1).strip()
                print(f"    [LOG] 同一テキスト内ペア検出: '{location_value}'")
                results.append({
                    "keyword": location_keyword,
                    "value": location_value,
                    "value_text": text,
                    "keyword_box": box,
                    "value_box": box,
                    "distance": 0.0
                })
                continue
            
            # パターン2: 改行やパイプで区切られた場合
            # "工事名\n場所|小山" のようなケース
            lines = re.split(r'[\n|]', text)
            for i, line in enumerate(lines):
                if location_keyword in line:
                    # 同じ行内で値を探す
                    value_match = re.search(r"場所\s*([^\s]+)", line)
                    if value_match:
                        location_value = value_match.group(1)
                        print(f"    [LOG] 同一行内ペア検出: '{location_value}'")
                        results.append({
                            "keyword": location_keyword,
                            "value": location_value,
                            "value_text": text,
                            "keyword_box": box,
                            "value_box": box,
                            "distance": 0.0
                        })
                        break
                    # 次の行で値を探す
                    elif i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line and not any(kw in next_line for kw in ["工事名", "日付", "測点"]):
                            location_value = next_line
                            print(f"    [LOG] 次行ペア検出: '{location_value}'")
                            results.append({
                                "keyword": location_keyword,
                                "value": location_value,
                                "value_text": text,
                                "keyword_box": box,
                                "value_box": box,
                                "distance": 0.0
                            })
                            break
    
    # 近隣テキストボックス間での検出（既存ロジック）
    if not results:
        print(f"  [LOG] 近隣テキストボックス検索開始")
        for box in texts_with_boxes:
            text = box.get("text", "")
            if location_keyword in text:
                x0, y0 = box["x"], box["y"]
                print(f"    [LOG] 場所キーワード: text='{text}', x={x0}, y={y0}")
                
                # 右側または下側の近いテキストボックスを探す
                candidates = []
                for other_box in texts_with_boxes:
                    if other_box is box:
                        continue
                    
                    x1, y1 = other_box["x"], other_box["y"]
                    other_text = other_box.get("text", "").strip()
                    
                    # 空文字やキーワードは除外
                    if not other_text or any(kw in other_text for kw in ["工事名", "日付", "測点", "工種"]):
                        continue
                    
                    # 右側 (x1 > x0) または下側 (y1 > y0) で距離を計算
                    if x1 > x0 or y1 > y0:
                        distance = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
                        if distance < 200:  # 距離制限
                            candidates.append((other_box, other_text, distance))
                            print(f"      [LOG] 候補: text='{other_text}', distance={distance:.1f}")
                
                if candidates:
                    # 最も近い候補を選択
                    best_box, best_text, best_distance = min(candidates, key=lambda x: x[2])
                    print(f"    [LOG] 近隣ペア決定: '{best_text}' (distance={best_distance:.1f})")
                    results.append({
                        "keyword": location_keyword,
                        "value": best_text,
                        "value_text": best_text,
                        "keyword_box": box,
                        "value_box": best_box,
                        "distance": best_distance
                    })
                    break
    
    print(f"[LOG] 場所検出結果: {len(results)}件")
    return results


def detect_value_pairs_from_boxes_enhanced(
    texts_with_boxes: List[Dict[str, Any]],
    keyword_list=None,
    value_pattern=r"([0-9]+\.[0-9]+|[0-9]+)\s*℃",
    max_y_diff=30,
    min_x_diff=10
) -> List[Dict[str, Any]]:
    """
    拡張版のペア検出（従来の温度検出 + 場所検出 + テキスト検出）
    """
    results = []
    
    if keyword_list is None:
        keyword_list = []
    
    # テキスト系キーワードの特別処理
    text_keywords = ["日付", "台数", "工事名", "材料名"]
    text_keywords_to_process = [kw for kw in keyword_list if kw in text_keywords]
    if text_keywords_to_process:
        text_results = detect_text_value_pairs_from_boxes(
            texts_with_boxes, text_keywords_to_process, r"([^\s\n|]+)", max_y_diff, min_x_diff
        )
        results.extend(text_results)
    
    # 場所キーワードの特別処理
    if "場所" in keyword_list:
        location_results = detect_location_value_pairs(texts_with_boxes)
        results.extend(location_results)
    
    # 従来の温度等の数値検出
    numeric_keywords = [kw for kw in keyword_list if kw not in text_keywords and kw != "場所"]
    if numeric_keywords:
        temp_results = detect_value_pairs_from_boxes(
            texts_with_boxes, numeric_keywords, value_pattern, max_y_diff, min_x_diff
        )
        results.extend(temp_results)
    
    return results

def detect_text_value_pairs_from_boxes(
    texts_with_boxes: List[Dict[str, Any]],
    keyword_list=None,
    value_pattern=r"([^\s\n|]+)",
    max_y_diff=30,
    min_x_diff=10
) -> List[Dict[str, Any]]:
    """
    texts_with_boxes: [{"text": str, "x": int, "y": int}, ...]
    keyword_list: 検出したいキーワード（例：['日付', '台数']）
    value_pattern: 値の正規表現
    max_y_diff: y座標の許容差
    min_x_diff: x座標の最小差（右側判定）
    Returns: [{"keyword":..., "value":..., "value_text":..., "keyword_box":..., "value_box":..., "distance": ...}, ...]
    """
    if keyword_list is None:
        keyword_list = ["日付", "台数"]
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
                    value_text = m.group(1).strip()
                    distance = abs(b["x"] - x0) + abs(b["y"] - y0)
                    print(f"    [LOG]   候補値: text='{b['text']}', x={b['x']}, y={b['y']}, value='{value_text}', distance={distance}")
                    value_boxes.append((b, value_text, distance))
            if value_boxes:
                # 最も近い（距離が短い）値を選択
                value_box, value_text, distance = min(value_boxes, key=lambda t: t[2])
                print(f"  [LOG]  ペア決定: keyword='{kw}', value='{value_text}', value_text='{value_box['text']}', distance={distance}")
                results.append({
                    "keyword": kw,
                    "value": value_text,
                    "value_text": value_box["text"],
                    "keyword_box": kw_box,
                    "value_box": value_box,
                    "distance": distance
                })
            else:
                print(f"  [LOG]  値候補なし")
    print(f"[LOG] テキスト検出結果: {results}")
    return results