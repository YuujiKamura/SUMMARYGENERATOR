import os
import json
import sys
import unicodedata
# tests/ ディレクトリを追加（utils用）
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
# src/ ディレクトリを追加（data_collector用）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from data_collector import DataCollector
import test_utils

def get_display_width(text):
    width = 0
    for c in text:
        if unicodedata.east_asian_width(c) in ('F', 'W', 'A'):
            width += 2
        else:
            width += 1
    return width

def pad_display(text, width):
    pad_len = width - get_display_width(text)
    return text + ' ' * pad_len

if __name__ == '__main__':
    # 温度管理用キーワード定義ファイル
    keywords_path = os.path.join(os.path.dirname(__file__), 'collect_keywords_tempmanage.json')
    test_json = os.path.join(os.path.dirname(__file__), "data", "ocr_sample_texts_with_boxes.json")

    with open(keywords_path, encoding='utf-8') as f:
        collect_dict = json.load(f)
    collector = DataCollector(collect_dict)

    print(f"--- test: {os.path.basename(test_json)} ---")
    with open(test_json, encoding='utf-8') as f:
        texts_with_boxes = json.load(f)
    result = collector.collect_pairs(texts_with_boxes)
    # トップレベルcategoryを用途判定として通知
    board_category = collect_dict.get('category', '不明')
    print(f"[BOARD CATEGORY] : {board_category}")
    print("[COLLECTED PAIRS]")
    compare_keys = [pair['label'] for pair in collect_dict.get('value_pairs', [])]
    test_utils.print_aligned_pairs(result, keys=compare_keys)
