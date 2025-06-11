import sys
from pathlib import Path
from src.db_manager import import_image_preview_cache_json

def json_to_db(json_path: str, db_path: str = None):
    """
    画像リストJSONからDB（yolo_data.db等）を構築するユーティリティ関数。
    json_path: 画像リストJSONのパス
    db_path: 出力DBファイルのパス（省略時はデフォルト）
    """
    json_path = Path(json_path)
    if db_path is not None:
        db_path = Path(db_path)
    print(f"[INFO] 画像リストJSON→DBインポート開始: {json_path} → {db_path if db_path else 'default'}")
    import_image_preview_cache_json(json_path=json_path, db_path=db_path)
    print(f"[INFO] インポート完了: {db_path if db_path else 'default'}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="画像リストJSON→DBインポートユーティリティ")
    parser.add_argument("--json", type=str, required=True, help="画像リストJSONのパス")
    parser.add_argument("--db", type=str, default=None, help="出力DBファイルのパス（省略時はデフォルト）")
    args = parser.parse_args()
    json_to_db(args.json, args.db) 