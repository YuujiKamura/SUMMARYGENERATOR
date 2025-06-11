import os
import json

def save_last_json_path(json_path, config_path):
    """最後に使用したJSONパスを設定ファイルに保存"""
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"last_json_path": os.path.abspath(json_path)}, f)
    except Exception as e:
        print(f"[WARN] JSONパス保存失敗: {e}")

def save_image_cache_dir(folder_path, image_cache_dir_config):
    """画像キャッシュディレクトリパスを設定ファイルに保存"""
    try:
        with open(image_cache_dir_config, "w", encoding="utf-8") as f:
            json.dump({"image_cache_dir": folder_path}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] フォルダパス保存失敗: {e}")
