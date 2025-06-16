import os
import json
from datetime import datetime
from caption_board_ocr_utils import format_date

def print_extracted_results_summary(extracted_results):
    """
    OCR抽出結果リストをターミナルに整形表示
    """
    found_locations = []
    found_date_counts = []
    for i, result in enumerate(extracted_results, 1):
        if result['location_value']:
            print(f"{i}. {result['filename']}: {result['location_value']}")
            found_locations.append(result['location_value'])
        elif result['date_value'] and result['count_value']:
            date_val = result['date_value']
            formatted_date = format_date(date_val)
            combined = f"{formatted_date} {result['count_value']}"
            print(f"{i}. {result['filename']}: {combined}")
            found_date_counts.append(combined)
        else:
            print(f"{i}. {result['filename']}: 抽出データなし")
    if found_locations:
        print(f"\n抽出された測点名称: {len(found_locations)}件")
        for loc in found_locations:
            print(f"  - {loc}")
    if found_date_counts:
        print(f"\n抽出された日付・台数: {len(found_date_counts)}件")
        for dc in found_date_counts:
            print(f"  - {dc}")
    if not found_locations and not found_date_counts:
        print("\n抽出データはありませんでした。")

def save_success_results(extracted_results, project_root, log_prefix="caption_board_ocr_success"):
    """
    成功した抽出結果のみをlogsディレクトリに保存
    """
    success_results = [r for r in extracted_results if r.get('location_value') or (r.get('date_value') and r.get('count_value'))]
    if success_results:
        log_dir = os.path.join(project_root, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        out_path = os.path.join(log_dir, f'{log_prefix}_{ts}.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(success_results, f, ensure_ascii=False, indent=2)
        print(f"\n[INFO] 検出OK {len(success_results)} 件を {out_path} に保存しました")
    else:
        print("\n[INFO] 成功検出はありませんでした (ファイル保存スキップ)")

def print_final_stats(results):
    """
    最終的な件数サマリを表示
    """
    print(f"\n総処理ファイル数: {len(results)}")
    location_count = sum(1 for r in results if r['location_value'])
    date_count_pairs = sum(1 for r in results if r['date_value'] and r['count_value'])
    print(f"測点名称検出数: {location_count}")
    print(f"日付・台数検出数: {date_count_pairs}")

def list_caption_board_images(image_data, caption_board_images):
    """
    キャプションボード画像の一覧をターミナルに表示
    """
    print(f"=== キャプションボード画像一覧 ({len(caption_board_images)}件) ===")
    for i, img_info in enumerate(caption_board_images):
        bbox = img_info['bbox']
        role = bbox.get('role', '') or 'None'
        cname = bbox.get('cname', '')
        size = f"{bbox.get('width', '?')}x{bbox.get('height', '?')}"
        print(f"{i:2d}. {os.path.basename(img_info['filename'])}")
        print(f"    パス: {img_info['image_path']}")
        print(f"    ロール: {role}")
        print(f"    クラス: {cname}")
        print(f"    サイズ: {size}")
        print()
