import csv
import json
from pathlib import Path
from data_loader import load_records, load_image_roles
from result_formatter import format_match_result
from matcher import match_images_and_records, match_images_and_records_normal

if __name__ == '__main__':
    records = load_records('data/records_and_roles.csv')
    image_roles = load_image_roles('data/image_preview_cache_master.json')
    # まずノーマルマッチング結果を出力
    print("\n=== [Normal Matching Results] ===")
    normal_results = match_images_and_records_normal(records, image_roles, formatter=format_match_result)
    for img_path, record, found, match_val, formatted in normal_results:
        print(f"[IMAGE] {img_path}")
        print(formatted)
    # その後カテゴリ別マッチング結果を出力
    results_by_category = match_images_and_records(records, image_roles, formatter=format_match_result)
    for category, results in results_by_category.items():
        print(f"\n=== {category} ===")
        for img_path, record, found, match_val, formatted in results:
            print(f"[IMAGE] {img_path}")
            print(formatted)
