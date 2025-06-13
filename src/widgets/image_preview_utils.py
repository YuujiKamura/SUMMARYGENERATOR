import os
import json
from src.utils.image_cache_utils import get_image_cache_path
from src.utils.path_manager import path_manager

def save_image_cache_with_location(image_path, bboxes, location, cache_dir=None):
    """
    bboxesとlocationを同時にキャッシュJSONへ保存
    """
    abs_image_path = os.path.abspath(image_path)
    img_cache_path = get_image_cache_path(abs_image_path, cache_dir)
    bboxes_out = [b.to_dict() if hasattr(b, 'to_dict') else b for b in bboxes]
    data = {
        "image_path": abs_image_path,
        "bboxes": bboxes_out,
        "location": location
    }
    try:
        with open(img_cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[キャッシュ保存失敗] {img_cache_path}: {e}")
        return False
