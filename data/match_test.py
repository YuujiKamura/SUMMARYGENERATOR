import csv
import json
from pathlib import Path
try:
    # If executed as package module
    from .data_loader import load_records, load_image_roles
    from .result_formatter import format_match_result
    from .matcher import (
        match_images_and_records,
        match_images_and_records_normal,
    )
except ImportError:
    # If executed as a standalone script (cwd = data dir)
    from data_loader import load_records, load_image_roles
    from result_formatter import format_match_result
    from matcher import match_images_and_records, match_images_and_records_normal
import os

if __name__ == '__main__':
    base_dir = Path(__file__).parent
    records_csv = base_dir / 'records_and_roles.csv'
    json_path = base_dir / 'image_preview_cache_master.json'
    records = load_records(str(records_csv))
    image_roles = load_image_roles(str(json_path))
    # まずノーマルマッチング結果を出力
    print("\n=== [Normal Matching Results] ===")
    normal_results = match_images_and_records_normal(records, image_roles, formatter=format_match_result)
    for img_path, record, found, match_val, formatted in normal_results:
        print(f"[IMAGE] {os.path.basename(img_path)} | {formatted}")
    # その後カテゴリ別マッチング結果を出力
    results_by_category = match_images_and_records(records, image_roles, formatter=format_match_result)
    for category, results in results_by_category.items():
        print(f"\n=== {category} ===")
        for img_path, record, found, match_val, formatted in results:
            print(f"[IMAGE] {os.path.basename(img_path)} | {formatted}")
