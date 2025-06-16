#!/usr/bin/env python3
"""
キャプションボードサイズとOCR成功率の詳細分析スクリプト
"""

import json
import os

def analyze_caption_board_size_correlation():
    # 最新の分析結果ファイルを読み込み
    logs_dir = "../logs"
    size_analysis_files = [f for f in os.listdir(logs_dir) if f.startswith("caption_board_size_analysis_")]
    if not size_analysis_files:
        print("分析ファイルが見つかりません")
        return
    
    latest_file = sorted(size_analysis_files)[-1]
    file_path = os.path.join(logs_dir, latest_file)
    
    print(f"分析ファイル: {latest_file}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # OCRキャッシュがある画像のみをフィルタ
    cached_images = [item for item in data if item["has_cache"]]
    
    print(f"\n=== OCRキャッシュあり画像の詳細分析 ===")
    print(f"総数: {len(cached_images)}件")
    
    # 成功・失敗別にグループ化
    success_cases = [item for item in cached_images if item["ocr_success"]]
    failure_cases = [item for item in cached_images if not item["ocr_success"]]
    
    print(f"\n成功例: {len(success_cases)}件")
    print("---")
    for item in success_cases:
        size_info = ""
        if item["caption_board_area"]:
            size_info = f" (W×H: {item['caption_board_width']}×{item['caption_board_height']}, 面積: {item['caption_board_area']:,} px²)"
        
        extracted = []
        if item["location_value"]:
            extracted.append(f"場所:{item['location_value']}")
        if item["date_value"]:
            extracted.append(f"日付:{item['date_value']}")
        if item["count_value"]:
            extracted.append(f"台数:{item['count_value']}")
        
        extracted_str = " | ".join(extracted) if extracted else "なし"
        
        print(f"  • {os.path.basename(item['image_path'])}{size_info}")
        print(f"    抽出値: {extracted_str}")
    
    print(f"\n失敗例: {len(failure_cases)}件")
    print("---")
    for item in failure_cases:
        size_info = ""
        if item["caption_board_area"]:
            size_info = f" (W×H: {item['caption_board_width']}×{item['caption_board_height']}, 面積: {item['caption_board_area']:,} px²)"
        
        print(f"  • {os.path.basename(item['image_path'])}{size_info}")
    
    # サイズ分布と成功率の統計
    print(f"\n=== サイズ分布統計 ===")
    
    # キャプションボードが検出された画像のみ
    cb_detected = [item for item in cached_images if item["caption_board_area"] is not None]
    
    if cb_detected:
        areas = [item["caption_board_area"] for item in cb_detected]
        areas.sort()
        
        print(f"キャプションボード検出画像: {len(cb_detected)}件")
        print(f"面積範囲: {min(areas):,} - {max(areas):,} px²")
        
        # 詳細な分析
        success_with_cb = [item for item in cb_detected if item["ocr_success"]]
        failure_with_cb = [item for item in cb_detected if not item["ocr_success"]]
        
        if success_with_cb:
            success_areas = [item["caption_board_area"] for item in success_with_cb]
            avg_success_area = sum(success_areas) / len(success_areas)
            print(f"\n成功例の平均面積: {avg_success_area:,.0f} px²")
            print(f"成功例の面積範囲: {min(success_areas):,} - {max(success_areas):,} px²")
        
        if failure_with_cb:
            failure_areas = [item["caption_board_area"] for item in failure_with_cb]
            avg_failure_area = sum(failure_areas) / len(failure_areas)
            print(f"\n失敗例の平均面積: {avg_failure_area:,.0f} px²")
            print(f"失敗例の面積範囲: {min(failure_areas):,} - {max(failure_areas):,} px²")
        
        # サイズ閾値の推定
        print(f"\n=== サイズ閾値分析 ===")
        
        # 成功例と失敗例の境界を探る
        if success_with_cb and failure_with_cb:
            success_areas = sorted([item["caption_board_area"] for item in success_with_cb])
            failure_areas = sorted([item["caption_board_area"] for item in failure_with_cb])
            
            max_success_area = max(success_areas)
            min_failure_area = min(failure_areas)
            
            print(f"最大の成功例面積: {max_success_area:,} px²")
            print(f"最小の失敗例面積: {min_failure_area:,} px²")
            
            if min_failure_area > max_success_area:
                suggested_threshold = (max_success_area + min_failure_area) // 2
                print(f"推奨面積閾値: {suggested_threshold:,} px² (この値以下で成功率が高い)")
            else:
                print("成功例と失敗例の面積に重複があります。明確な閾値の特定は困難です。")

if __name__ == "__main__":
    analyze_caption_board_size_correlation()
