# --- Copied from src/image_cache_utils.py ---
import os
import json
import hashlib
from pathlib import Path
from src.utils.path_manager import path_manager

def get_image_cache_path(image_path, cache_dir=None):
    if cache_dir is None:
        cache_dir = str(path_manager.image_cache_dir)
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

def load_image_cache(image_path, cache_dir=None, return_full: bool = False):
    """画像パスからキャッシュJSONを読み込む。

    Parameters
    ----------
    image_path : str
        画像ファイルのパス。
    cache_dir : str | None, default None
        キャッシュディレクトリ。None の場合は `path_manager.image_cache_dir` が使用される。
    return_full : bool, default False
        True の場合は読み込んだ JSON 全体 (dict) を返す。
        False の場合は旧互換のタプル ``(image_path, bboxes)`` を返す。
    """
    img_cache_path = get_image_cache_path(image_path, cache_dir)
    if not os.path.exists(img_cache_path):
        print(f"[キャッシュ未発見] {img_cache_path}")
        return None if return_full else (None, [])

    try:
        with open(img_cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if return_full:
            return data
        # 旧互換: image_path と bboxes のタプルを返す
        return data.get("image_path"), data.get("bboxes", [])

    except Exception as e:
        print(f"[キャッシュ読込失敗] {img_cache_path}: {e}")
        return None if return_full else (None, [])
