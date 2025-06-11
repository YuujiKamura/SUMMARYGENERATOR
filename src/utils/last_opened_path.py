import os
import json

def save_last_path(config_path: str, key: str, value: str) -> None:
    """
    指定したconfig_path(JSON)にkey: valueで保存する
    """
    data = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = {}
    data[key] = value
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[last_opened_path] 保存エラー: {e}")

def load_last_path(config_path: str, key: str) -> str | None:
    """
    指定したconfig_path(JSON)からkeyの値を取得する
    """
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get(key)
        except Exception as e:
            print(f"[last_opened_path] 読込エラー: {e}")
    return None 