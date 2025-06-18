#!/usr/bin/env python3
"""
失敗例の詳細なYOLO検出情報を確認するスクリプト
"""

import json
import os

def analyze_failed_cases():
    # ログディレクトリのパス - ocr_toolsから見て上位の logs
    logs_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    size_analysis_files = [f for f in os.listdir(logs_dir) if f.startswith("caption_board_size_analysis_")]
    if not size_analysis_files:
        print("分析ファイルが見つかりません")
        return
    
    latest_file = sorted(size_analysis_files)[-1]
    file_path = os.path.join(logs_dir, latest_file)
    
    with open(file_path, "r", encoding="utf-8") as f:
        size_data = json.load(f)
      # マスターファイルを読み込み
    master_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'image_preview_cache_master.json')
    with open(master_path, "r", encoding="utf-8") as f:
        master_data = json.load(f)
    
    # すべてのケースを対象とする (has_cache が True のもの)
    all_cases = [item for item in size_data if item.get("has_cache", False)]
    
    print("=== 全ケースの詳細YOLO検出情報 ===")
    
    for case_item in all_cases: # failed_cases を all_cases に変更
        filename = case_item["filename"]
        image_path = case_item["image_path"]
        # caption_board_area が存在しない場合も考慮
        area = case_item.get("caption_board_area", 0) 
        ocr_success = case_item.get("ocr_success", False) # OCR成功/失敗フラグを取得
        
        # OCR成功か失敗かでプレフィックスを変更
        status_prefix = "✅" if ocr_success else "❌"
        # OCRキャッシュの有無を表示
        ocr_cache_status = "あり" if case_item.get("has_cache", False) else "なし"
        print(format_case_header(image_path, filename, ocr_cache_status, status_prefix))
        ocr_skip_info_str = format_ocr_skip_info(case_item)
        if ocr_skip_info_str:
            print(ocr_skip_info_str)
        if ocr_success:
            ocr_success_info_str = format_ocr_success_info(case_item)
            if ocr_success_info_str:
                print(ocr_success_info_str)
        
        # マスターデータから対応する項目を検索
        master_item = None
        for item in master_data:
            if item["filename"] == filename:
                master_item = item
                break
        
        if master_item:
            print(f"  検出されたbbox数: {len(master_item.get('bboxes', []))}")
            for i, bbox in enumerate(master_item.get('bboxes', [])):
                cname = bbox.get('cname', 'N/A')
                role = bbox.get('role', 'N/A') 
                xyxy = bbox.get('xyxy', [])
                if role and role not in ['N/A', '', None] and role != cname :
                    detection_source = "ロール"
                    name_to_display = role
                elif cname and cname not in ['N/A', '', None]:
                    detection_source = "クラス"
                    name_to_display = cname
                else:
                    detection_source = "不明"
                    name_to_display = "N/A"
                if len(xyxy) >= 4:
                    w = int(xyxy[2] - xyxy[0])
                    h = int(xyxy[3] - xyxy[1])
                    bbox_specific_area = w * h
                    print(format_bbox_line(name_to_display, detection_source, w, h, bbox_specific_area))
                    ocr_results = bbox.get('ocr_results') 
                    if ocr_results and isinstance(ocr_results, dict):
                        value_pairs = ocr_results.get('value_pairs')
                        if value_pairs and isinstance(value_pairs, list):
                            pairs_str_list = []
                            for pair_idx, pair in enumerate(value_pairs):
                                key_text = pair.get('key', {}).get('text', 'N/A')
                                value_text = pair.get('value', {}).get('text', 'N/A')
                                pairs_str_list.append(f"ペア{pair_idx+1}: [{key_text}] -> [{value_text}]")
                            if pairs_str_list:
                                print(format_bbox_pair_results(pairs_str_list))
                else:
                    print(format_bbox_line_no_size(name_to_display, detection_source))
        else:
            print("  マスターデータで見つかりませんでした")

def format_case_header(image_path, filename, ocr_cache_status, status_prefix):
    abs_image_path = os.path.abspath(image_path)
    return f"\n{status_prefix} {os.path.basename(image_path)}\n  画像絶対パス: {abs_image_path}\n  ファイル名: {filename}\n  OCRキャッシュ: {ocr_cache_status}"

def format_bbox_line(name_to_display, detection_source, w, h, bbox_specific_area):
    return f"  - {name_to_display} ({detection_source}, サイズ: {w}×{h}px [{bbox_specific_area:,} px²])"

def format_bbox_line_no_size(name_to_display, detection_source):
    return f"  - {name_to_display} ({detection_source}、サイズ情報なし)"

def format_bbox_pair_results(pairs_str_list):
    return f"    ペアマッチング結果: {'; '.join(pairs_str_list)}"

def format_ocr_success_info(case_item):
    # OCR成功時に取得できた期待値を表示
    vals = []
    if case_item.get('location_value'):
        vals.append(f"場所: {case_item['location_value']}")
    if case_item.get('date_value'):
        vals.append(f"日付: {case_item['date_value']}")
    if case_item.get('count_value'):
        vals.append(f"台数: {case_item['count_value']}")
    if vals:
        return "  取得値: " + ", ".join(vals)
    return ""

def format_ocr_skip_info(case_item):
    if case_item.get('ocr_skipped'):
        reason = case_item.get('ocr_skip_reason', '')
        return f"  [OCRスキップ: {reason}]"
    return ""

if __name__ == "__main__":
    analyze_failed_cases()
