# summarygenerator/utils/test_resource_files.py
"""
リソースファイル（role_mapping.json, preset_roles.json, default_records.json など）の絶対パス取得・内容読み込みテスト
"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
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

def import_chain_records_to_db(db_path, json_path):
    import sqlite3
    from utils.chain_record_utils import load_chain_records
    recs = load_chain_records(json_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('DELETE FROM chain_records')
    for r in recs:
        # extra_jsonに全情報を格納
        extra = r.to_dict().copy()
        extra.pop('remarks', None)
        extra.pop('photo_category', None)
        cur.execute(
            'INSERT INTO chain_records (remarks, photo_category, extra_json) VALUES (?, ?, ?)',
            (
                r.remarks,
                r.photo_category,
                json.dumps(extra, ensure_ascii=False)
            )
        )
    conn.commit()
    print(f"DBへChainRecordを{len(recs)}件インポートしました。")
    conn.close()

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
    # DBへChainRecordをインポート
    import_chain_records_to_db(
        db_path=str(Path(__file__).parent.parent / "yolo_data.db"),
        json_path=str(Path(__file__).parent.parent / "data/dictionaries/default_records.json")
    )

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

def test_import_chain_records_to_db():
    import sqlite3
    from utils.chain_record_utils import load_chain_records
    db_path = str(Path(__file__).parent.parent / "yolo_data.db")
    json_path = str(Path(__file__).parent.parent / "data/dictionaries/default_records.json")
    recs = load_chain_records(json_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('DELETE FROM chain_records')
    success, fail = 0, 0
    for r in recs:
        try:
            # extra_jsonに全情報を格納
            extra = r.to_dict().copy()
            extra.pop('remarks', None)
            extra.pop('photo_category', None)
            cur.execute(
                'INSERT INTO chain_records (remarks, photo_category, extra_json) VALUES (?, ?, ?)',
                (
                    r.remarks,
                    r.photo_category,
                    json.dumps(extra, ensure_ascii=False)
                )
            )
            success += 1
        except Exception as e:
            print(f"[ERROR] INSERT失敗: remarks={r.remarks}, error={e}")
            fail += 1
    conn.commit()
    # 検証: DBから全件取得しremarksを比較
    cur.execute('SELECT remarks FROM chain_records')
    db_remarks = [row[0] for row in cur.fetchall()]
    file_remarks = [r.remarks for r in recs]
    print(f"[TEST] 成功: {success}件, 失敗: {fail}件, DB件数: {len(db_remarks)}")
    assert set(db_remarks) == set(file_remarks), f"DB登録件数={len(db_remarks)}, ファイル件数={len(file_remarks)}"
    print(f"[TEST] ChainRecordインポート・検証OK: {len(db_remarks)}件")
    conn.close()

if __name__ == "__main__":
    main()
    # image_preview_cache配下の詳細テスト
    # パスマネージャー経由で絶対パス取得
    cache_dir = path_manager.image_cache_dir
    test_image_preview_cache_jsons(cache_dir, max_files=10)
    # DBインポートテスト
    test_import_chain_records_to_db()
