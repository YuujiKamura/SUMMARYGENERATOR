# summarygenerator/utils/generate_image_cache_master.py
"""
image_preview_cache配下の全個別画像JSONを集約し、
マスタJSON（全画像分のimage_path, bboxes, 主要メタ情報を1ファイルにまとめたもの）を生成するスクリプト。
"""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from path_manager import path_manager


def main():
    cache_dir = path_manager.image_cache_dir
    # workspace直下のdata/に出力
    output_path = Path(__file__).parent.parent.parent / 'data' / 'image_preview_cache_master.json'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    master_list = []
    json_files = sorted(cache_dir.glob('*.json'))
    print(f"集約対象: {len(json_files)}件")
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            entry = {
                'filename': json_file.name,
                'image_path': data.get('image_path'),
                'bboxes': data.get('bboxes'),
                # 必要なら他のメタ情報も追加可能
            }
            master_list.append(entry)
        except Exception as e:
            print(f"[ERROR] {json_file}: {e}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(master_list, f, ensure_ascii=False, indent=2)
    print(f"マスタJSONを出力: {output_path} ({len(master_list)}件)")

if __name__ == "__main__":
    main()
