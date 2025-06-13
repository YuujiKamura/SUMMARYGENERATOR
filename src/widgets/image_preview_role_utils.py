import os
import json
from src.utils.last_opened_path import save_last_path, load_last_path

__all__ = ["load_roles", "load_last_image_path", "save_last_image_path"]

def load_roles(dialog):
    preset_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'preset_roles.json'))
    try:
        with open(preset_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"ロール読込失敗: {e}")
        return []

def load_last_image_path(config_path):
    return load_last_path(config_path, "last_image_path")

def save_last_image_path(config_path, path):
    save_last_path(config_path, "last_image_path", path)
