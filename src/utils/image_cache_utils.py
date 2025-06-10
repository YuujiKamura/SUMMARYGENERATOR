# --- Copied from src/image_cache_utils.py ---
import os
import json
import hashlib
from pathlib import Path

def get_image_cache_path(image_path, cache_dir=None):
    if cache_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        cache_dir = os.path.abspath(os.path.join(base_dir, "image_preview_cache"))
    os.makedirs(cache_dir, exist_ok=True)
    h = hashlib.sha1(image_path.encode("utf-8")).hexdigest()
    return os.path.join(cache_dir, f"{h}.json")

def save_image_cache(image_path, bboxes, cache_dir=None):
    abs_image_path = os.path.abspath(image_path)
    img_cache_path = get_image_cache_path(abs_image_path, cache_dir)
    bboxes_out = [b.to_dict() if hasattr(b, 'to_dict') else b for b in bboxes]
    try:
        with open(img_cache_path, "w", encoding="utf-8") as f:
            json.dump({
                "image_path": abs_image_path,
                "bboxes": bboxes_out
            }, f, ensure_ascii=False, indent=2)
        print(f"[キャッシュ保存] {img_cache_path} bboxes: {bboxes_out}")
        return True
    except Exception as e:
        print(f"[キャッシュ保存失敗] {img_cache_path}: {e}")
        return False

def load_image_cache(image_path, cache_dir=None):
    img_cache_path = get_image_cache_path(image_path, cache_dir)
    if not os.path.exists(img_cache_path):
        print(f"[キャッシュ未発見] {img_cache_path}")
        return None, []
    try:
        with open(img_cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("image_path"), data.get("bboxes", [])
    except Exception as e:
        print(f"[キャッシュ読込失敗] {img_cache_path}: {e}")
        return None, []
