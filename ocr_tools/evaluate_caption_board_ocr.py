import sys
import json
import os
from typing import List, Dict, Any
from datetime import datetime

# ----- パス設定 -----
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
src_dir = os.path.join(project_root, 'src')
# for import
sys.path.insert(0, current_dir)
sys.path.insert(0, project_root)
sys.path.insert(0, src_dir)

from google.cloud.documentai_v1.types import Document
from ocr_tools.ocr_value_extractor import (
    extract_texts_with_boxes_from_documentai_result,
    get_cache_path,
    copy_to_local,
)
from src.utils.path_manager import path_manager
from ocr_tools.caption_board_value_extractor import extract_caption_board_values
from ocr_tools.caption_board_ocr_filter import should_skip_ocr_by_size_and_aspect
from ocr_tools.ocr_keyword_config import PRIMARY_KEYWORDS

ocr_cache_dir = os.path.join(project_root, "ocr_tools", "ocr_cache")
master_json_path = path_manager.image_preview_cache_master


def load_master() -> List[Dict[str, Any]]:
    with open(master_json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_image_size_and_bbox_info(item: Dict[str, Any]) -> tuple[int, int, Dict[str, Any] | None]:
    """画像サイズとキャプションボードのbbox情報を取得"""
    image_width, image_height = 1280, 960  # デフォルト
    caption_board_bbox = None
    
    for bbox in item.get("bboxes", []):
        # 画像サイズを取得（通常、bboxのxyxyから推定）
        xyxy = bbox.get("xyxy", [])
        if len(xyxy) >= 4:
            x1, y1, x2, y2 = xyxy
            # 全体画像のサイズを推定（最大座標値）
            w_est = max(x2, image_width)
            h_est = max(y2, image_height)
            if w_est > image_width:
                image_width = int(w_est)
            if h_est > image_height:
                image_height = int(h_est)
        
        # キャプションボード関連のbboxを取得
        cname = bbox.get("cname", "") or ""
        role = bbox.get("role", "") or ""
        if cname == "caption_board" or "caption_board" in role:
            caption_board_bbox = bbox
            # 最初に見つかったキャプションボードを使用
            # （複数ある場合は最初のものを優先）
    
    return image_width, image_height, caption_board_bbox


def analyse():
    data = load_master()
    total = len(data)
    processed = 0
    success = 0
    results = []
    size_analysis = []

    for item in data:
        image_path = item.get("image_path")
        if not image_path:
            continue
        
        # 画像サイズとキャプションボードのbbox情報を取得
        w, h, caption_board_bbox = get_image_size_and_bbox_info(item)
          # キャプションボードのサイズを計算
        caption_board_width = None
        caption_board_height = None
        caption_board_area = None
        
        if caption_board_bbox:
            # xyxyから幅と高さを計算
            xyxy = caption_board_bbox.get("xyxy", [])
            if len(xyxy) >= 4:
                x1, y1, x2, y2 = xyxy
                caption_board_width = int(x2 - x1)
                caption_board_height = int(y2 - y1)
                caption_board_area = caption_board_width * caption_board_height
        
        # OCRキャッシュの確認
        local_path = copy_to_local(image_path) or image_path
        cache_path = get_cache_path(local_path)
        has_cache = os.path.exists(cache_path)
        
        if not has_cache:
            # キャッシュがない場合もサイズ分析に含める
            size_analysis.append({
                "filename": item["filename"],
                "image_path": image_path,
                "image_width": w,
                "image_height": h,
                "caption_board_width": caption_board_width,
                "caption_board_height": caption_board_height,
                "caption_board_area": caption_board_area,
                "has_cache": False,
                "ocr_success": False,
                "location_value": None,
                "date_value": None,
                "count_value": None,
            })
            continue
        
        processed += 1
        
        with open(cache_path, "r", encoding="utf-8") as f:
            cached = json.load(f)
        document_dict = cached.get("document", {})
        
        try:
            document = Document.from_json(json.dumps(document_dict))
        except Exception:
            size_analysis.append({
                "filename": item["filename"],
                "image_path": image_path,
                "image_width": w,
                "image_height": h,
                "caption_board_width": caption_board_width,
                "caption_board_height": caption_board_height,
                "caption_board_area": caption_board_area,
                "has_cache": True,
                "ocr_success": False,
                "location_value": None,
                "date_value": None,
                "count_value": None,
            })
            continue
        
        texts_with_boxes = extract_texts_with_boxes_from_documentai_result(document, w, h)
        if not texts_with_boxes:
            size_analysis.append({
                "filename": item["filename"],
                "image_path": image_path,
                "image_width": w,
                "image_height": h,
                "caption_board_width": caption_board_width,
                "caption_board_height": caption_board_height,
                "caption_board_area": caption_board_area,
                "has_cache": True,
                "ocr_success": False,
                "location_value": None,
                "date_value": None,
                "count_value": None,
            })
            continue
        
        extracted = extract_caption_board_values(
            texts_with_boxes,
            keyword_list=PRIMARY_KEYWORDS,
            value_pattern=r"([0-9]+\.?[0-9]*)\s*°?C?",
            max_y_diff=50,
            min_x_diff=5,
        )

        pairs = extracted["pairs"]
        location_val = extracted["location_value"]
        date_val = extracted["date_value"]
        count_val = extracted["count_value"]
        
        # キャプションボードのロール情報を取得
        caption_board_role = None
        if caption_board_bbox:
            caption_board_role = caption_board_bbox.get("role", "")
        
        # ロール別の成功判定
        if caption_board_role and ("thermometer" in caption_board_role):
            # 温度管理用ボード：日付または台数があればOK
            ocr_success = bool(date_val or count_val)
            board_type = "温度管理用"
        elif caption_board_role and ("dekigata" in caption_board_role):
            # 出来形用ボード：後で別基準を設定予定、現在は除外
            ocr_success = False
            board_type = "出来形用"
        else:
            # 一般的なキャプションボード：何かしらの情報があればOK
            ocr_success = bool(location_val or date_val or count_val)
            board_type = "一般"
        
        # 詳細な成功タイプを記録
        success_type = []
        if location_val:
            success_type.append("場所")
        if date_val:
            success_type.append("日付")
        if count_val:            success_type.append("台数")
        
        if ocr_success:
            success += 1
            results.append({
                "filename": item["filename"],
                "image_path": image_path,
                "board_type": board_type,
                "caption_board_role": caption_board_role,
                "location_value": location_val,
                "date_value": date_val,
                "count_value": count_val,
                "success_type": success_type,
            })
        
        # サイズ分析データに追加
        size_analysis.append({
            "filename": item["filename"],
            "image_path": image_path,
            "board_type": board_type,
            "caption_board_role": caption_board_role,
            "image_width": w,
            "image_height": h,
            "caption_board_width": caption_board_width,
            "caption_board_height": caption_board_height,
            "caption_board_area": caption_board_area,
            "has_cache": has_cache,
            "ocr_success": ocr_success,
            "location_value": location_val,
            "date_value": date_val,
            "count_value": count_val,
        })

    print(f"総件数: {total}")
    print(f"OCR キャッシュあり: {processed}")
    print(f"期待値取得成功: {success}")
    
    # サイズ別の成功率分析
    print("\n=== キャプションボードサイズ分析 ===")
    
    # キャプションボード情報がある画像のみで分析
    cb_images = [item for item in size_analysis if item["caption_board_area"] is not None]
    cache_images = [item for item in cb_images if item["has_cache"]]
    
    if cb_images:
        print(f"キャプションボード検出: {len(cb_images)}件")
        print(f"キャッシュあり: {len(cache_images)}件")
        
        if cache_images:
            # サイズ別成功率
            areas = [item["caption_board_area"] for item in cache_images]
            areas.sort()
            
            # 4分位数で分割
            q1_idx = len(areas) // 4
            q2_idx = len(areas) // 2
            q3_idx = 3 * len(areas) // 4
            
            if len(areas) > 3:
                q1 = areas[q1_idx]
                q2 = areas[q2_idx]
                q3 = areas[q3_idx]
                
                print(f"\nサイズ分布（面積）:")
                print(f"  最小: {min(areas):,} px²")
                print(f"  Q1: {q1:,} px²")
                print(f"  中央値: {q2:,} px²")
                print(f"  Q3: {q3:,} px²")
                print(f"  最大: {max(areas):,} px²")
                
                # サイズ別成功率
                size_groups = [
                    ("極小", [item for item in cache_images if item["caption_board_area"] < q1]),
                    ("小", [item for item in cache_images if q1 <= item["caption_board_area"] < q2]),
                    ("中", [item for item in cache_images if q2 <= item["caption_board_area"] < q3]),
                    ("大", [item for item in cache_images if item["caption_board_area"] >= q3]),
                ]
                
                print(f"\nサイズ別成功率:")
                for group_name, group_items in size_groups:
                    if group_items:
                        success_count = sum(1 for item in group_items if item["ocr_success"])
                        success_rate = success_count / len(group_items) * 100
                        avg_area = sum(item["caption_board_area"] for item in group_items) / len(group_items)
                        print(f"  {group_name}サイズ({len(group_items)}件): {success_count}/{len(group_items)} = {success_rate:.1f}% (平均面積: {avg_area:,.0f} px²)")

    # 結果保存
    if results:
        out_dir = os.path.join(project_root, "logs")
        os.makedirs(out_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 成功ケース
        out_path = os.path.join(out_dir, f"caption_board_ocr_eval_{ts}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n成功ケース詳細: {out_path}")
        
        # サイズ分析結果
        size_out_path = os.path.join(out_dir, f"caption_board_size_analysis_{ts}.json")
        with open(size_out_path, "w", encoding="utf-8") as f:
            json.dump(size_analysis, f, ensure_ascii=False, indent=2)
        print(f"サイズ分析結果: {size_out_path}")


if __name__ == "__main__":
    analyse()