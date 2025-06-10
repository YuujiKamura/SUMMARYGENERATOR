# summarygenerator/utils/test_resource_files.py
"""
リソースファイル（role_mapping.json, preset_roles.json, default_records.json など）の絶対パス取得・内容読み込みテスト
"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from path_manager import path_manager

RESOURCE_PROPS = [
    ("role_mapping", path_manager.role_mapping),
    ("preset_roles", path_manager.preset_roles),
    ("default_records", path_manager.default_records),
]

def test_resource_file(prop_name, file_path):
    print(f"[{prop_name}] {file_path}")
    if not file_path or not Path(file_path).exists():
        print(f"  ❌ ファイルが存在しません")
        return False
    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        print(f"  ✅ 読み込み成功 (type={type(data)})")
        return True
    except Exception as e:
        print(f"  ❌ 読み込み失敗: {e}")
        return False

def main():
    print("=== リソースファイル読み込みテスト ===")
    all_ok = True
    for prop_name, file_path in RESOURCE_PROPS:
        ok = test_resource_file(prop_name, file_path)
        all_ok = all_ok and ok
    if all_ok:
        print("\nすべてのリソースファイルの読み込みに成功しました。")
    else:
        print("\n一部のリソースファイルでエラーが発生しました。")

def test_image_preview_cache_jsons(cache_dir, max_files=10):
    print(f"\n=== image_preview_cache配下の個別画像JSON詳細テスト ===")
    json_files = list(cache_dir.glob('*.json'))
    if not json_files:
        print("  ❌ JSONファイルが見つかりません")
        return False
    all_ok = True
    for i, json_file in enumerate(json_files[:max_files]):
        print(f"[{i+1}] {json_file.resolve()}")
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 必須キー検証
            image_path = data.get('image_path')
            bboxes = data.get('bboxes')
            if not image_path:
                print("  ❌ image_pathキーがありません")
                all_ok = False
            else:
                print(f"  image_path: {image_path}")
            if bboxes is None:
                print("  ❌ bboxesキーがありません")
                all_ok = False
            elif not isinstance(bboxes, list):
                print(f"  ❌ bboxesがリスト型でありません: {type(bboxes)}")
                all_ok = False
            elif len(bboxes) == 0:
                print("  ⚠️ bboxesが空です")
            else:
                for j, bbox in enumerate(bboxes):
                    if not isinstance(bbox, dict):
                        print(f"    ❌ bboxes[{j}]がdict型でありません: {type(bbox)}")
                        all_ok = False
                        continue
                    # bbox内の必須キー
                    for key in ('cid', 'xyxy'):
                        if key not in bbox:
                            print(f"    ❌ bboxes[{j}]に{key}キーがありません")
                            all_ok = False
                    # ラベル・ロール
                    label = bbox.get('cname') or bbox.get('label') or bbox.get('role')
                    if not label:
                        print(f"    ⚠️ bboxes[{j}]にラベル/ロール情報がありません")
                    else:
                        print(f"    label/role: {label}")
        except Exception as e:
            print(f"  ❌ 読み込み失敗: {e}")
            all_ok = False
    if all_ok:
        print("\nimage_preview_cache配下の個別画像JSONはすべて正常です。")
    else:
        print("\n一部の個別画像JSONでエラーや警告が発生しました。")
    return all_ok

if __name__ == "__main__":
    main()
    # image_preview_cache配下の詳細テスト
    # パスマネージャー経由で絶対パス取得
    cache_dir = path_manager.image_cache_dir
    test_image_preview_cache_jsons(cache_dir, max_files=10)
