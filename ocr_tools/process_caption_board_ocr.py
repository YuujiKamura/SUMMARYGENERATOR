import os
import sys
import json
import argparse
from pathlib import Path

# パスの設定
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
src_dir = os.path.join(project_root, 'src')
ocr_tools_dir = current_dir

# パスを追加
sys.path.insert(0, ocr_tools_dir)
sys.path.insert(0, src_dir)

from utils.path_manager import path_manager

from ocr_value_extractor import process_image_json, init_documentai_engine, extract_texts_with_boxes_from_documentai_result
from ocr_aa_layout import print_ocr_aa_layout
from caption_board_value_extractor import extract_caption_board_values

# 追加: コア処理モジュールのインポート
from caption_board_ocr_pipeline import process_caption_board_image
from caption_board_ocr_reporter import print_extracted_results_summary, save_success_results, print_final_stats, list_caption_board_images
from caption_board_ocr_utils import format_date
from caption_board_ocr_data import load_image_cache_master, find_caption_board_images

def process_images_with_engine(image_list):
    """画像リストを受けてDocumentAIエンジン初期化→一括処理"""
    try:
        from ocr_value_extractor import init_documentai_engine
        engine = init_documentai_engine()
        print("DocumentAI エンジン初期化完了")
    except Exception as e:
        print(f"DocumentAI エンジンの初期化に失敗: {e}")
        return []
    results = []
    for i, img_info in enumerate(image_list, 1):
        print(f"\n--- 画像 {i}/{len(image_list)} ---")
        print(f"ファイル: {img_info['filename']}")
        print(f"パス: {img_info['image_path']}")
        result = process_caption_board_image(img_info, engine, ocr_tools_dir, src_dir)
        if result:
            results.append(result)
    return results

def process_caption_board_ocr():
    """キャプションボード画像のOCR処理とペアマッチング（バッチ）"""
    print("=== キャプションボード画像のOCR・ペアマッチング処理開始 ===")
    extracted_results = []
    # 画像データを読み込み
    image_data = load_image_cache_master(project_root)
    print(f"総画像数: {len(image_data)}")
      # キャプションボード関連画像を抽出（4-8件目の5件）
    caption_board_images = find_caption_board_images(image_data, limit=5, skip=3)
    print(f"キャプションボード関連画像: {len(caption_board_images)}件（4-8件目）")
    
    if not caption_board_images:
        print("キャプションボード関連の画像が見つかりませんでした。")
        return extracted_results
    
    # 各画像を処理
    results = process_images_with_engine(caption_board_images)
    extracted_results.extend(results)
    
    print("\n=== 処理完了 ===")
    print("\n=== 抽出結果一覧 ===")
    print_extracted_results_summary(extracted_results)
    save_success_results(extracted_results, project_root)
    return extracted_results

def parse_arguments():
    """コマンドライン引数をパース"""
    parser = argparse.ArgumentParser(description='キャプションボード画像のOCR処理とペアマッチング')
    parser.add_argument('--index', '-i', type=int, help='処理したい画像のインデックス番号 (0から開始)')
    parser.add_argument('--filename', '-f', type=str, help='処理したい画像のファイル名 (部分一致)')
    parser.add_argument('--range', '-r', type=str, help='処理範囲 (例: "3:8" で4-8件目の5件)')
    parser.add_argument('--list', '-l', action='store_true', help='キャプションボード画像の一覧を表示')
    parser.add_argument('--lower-half', '-lh', action='store_true', help='画像リスト下半分の先頭5件を処理')
    return parser.parse_args()

def list_caption_board_images_cli():
    """キャプションボード画像の一覧を表示（CLI用ラッパー）"""
    image_data = load_image_cache_master(project_root)
    caption_board_images = find_caption_board_images(image_data, limit=999, skip=0)
    list_caption_board_images(image_data, caption_board_images)

def _select_by_index(caption_board_images, value):
    if not isinstance(value, int) or value < 0 or value >= len(caption_board_images):
        print(f"エラー: インデックス {value} は範囲外です (0-{len(caption_board_images)-1})")
        return []
    print(f"=== 画像 {value} の処理 ===")
    return [caption_board_images[value]]

def _select_by_filename(caption_board_images, value):
    if not isinstance(value, str):
        print("ファイル名パターンが不正です")
        return []
    selected = [img_info for img_info in caption_board_images if value.lower() in os.path.basename(img_info['filename']).lower()]
    if not selected:
        print(f"ファイル名に '{value}' を含む画像が見つかりませんでした")
        return []
    print(f"=== ファイル名 '{value}' にマッチする画像 ({len(selected)}件) ===")
    return selected

def _select_by_range(caption_board_images, value):
    if not isinstance(value, str):
        print("範囲指定が不正です")
        return []
    try:
        if ':' in value:
            start, end = map(int, value.split(':'))
        else:
            start = int(value)
            end = start + 1
    except Exception:
        print(f"エラー: 範囲の指定が不正です: {value}")
        print("例: '3:8' (4-8件目の5件) または '5' (6件目のみ)")
        return []
    if start < 0 or end > len(caption_board_images):
        print(f"エラー: 範囲 {start}:{end} が範囲外です (0-{len(caption_board_images)})")
        return []
    print(f"=== 範囲 {start}:{end} の画像処理 ({end-start}件) ===")
    return caption_board_images[start:end]

_SELECTORS = {
    'index': _select_by_index,
    'filename': _select_by_filename,
    'range': _select_by_range,
}

def process_images(mode: str, value=None):
    if value is None or mode not in _SELECTORS:
        print(f"不正なmodeまたは値: mode={mode}, value={value}")
        return []
    image_data = load_image_cache_master(project_root)
    caption_board_images = find_caption_board_images(image_data, limit=999, skip=0)
    selected_images = _SELECTORS[mode](caption_board_images, value)
    if not selected_images:
        return []
    return process_images_with_engine(selected_images)

if __name__ == "__main__":
    args = parse_arguments()
    if args.list:
        list_caption_board_images_cli()
    elif args.index is not None:
        results = process_images('index', args.index)
    elif args.filename:
        results = process_images('filename', args.filename)
    elif args.lower_half:
        image_data = load_image_cache_master(project_root)
        caption_images = find_caption_board_images(image_data, limit=999, skip=0)
        half_idx = len(caption_images) // 2
        end_idx = min(half_idx + 5, len(caption_images))
        range_str = f"{half_idx}:{end_idx}"
        print(f"[INFO] 下半分の先頭5件を処理します (範囲 {range_str})")
        results = process_images('range', range_str)
    elif args.range:
        results = process_images('range', args.range)
    else:
        results = process_caption_board_ocr()
    if args.list:
        pass
    elif results:
        print_final_stats(results)
    else:
        print("\n処理対象がありませんでした。")
    save_success_results(results, project_root)
