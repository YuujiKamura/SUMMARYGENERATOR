import os
import json
import hashlib
from summarygenerator.utils.path_manager import path_manager

OUT_PATH = str(path_manager.scan_for_images_dataset)

def get_sha1(path):
    return hashlib.sha1(path.encode("utf-8")).hexdigest()

def save_dataset_json(cache_dir=None, out_path=None, debug=False, collect_mode=None, image_list_json_path=None):
    """
    image_preview_cache/配下の全jsonを集約、または指定リストのみ集約し、scan_for_images_dataset.jsonに保存
    collect_mode: 'all'（全件） or 'list'（指定リストのみ）
    image_list_json_path: 'list'モード時に使う画像リストJSONパス
    """
    if collect_mode not in ('all', 'list'):
        raise ValueError("collect_modeは'all'または'list'で明示指定してください")
    if cache_dir is None:
        cache_dir = os.path.join(os.path.dirname(__file__), "image_preview_cache")
    if out_path is None:
        out_path = OUT_PATH
    if not os.path.exists(cache_dir):
        print(f"[保存エラー] キャッシュディレクトリが見つかりません: {cache_dir}")
        return False
    dataset = []
    if collect_mode == 'all':
        for fname in os.listdir(cache_dir):
            if not fname.endswith('.json'):
                continue
            fpath = os.path.join(cache_dir, fname)
            try:
                with open(fpath, encoding='utf-8') as f:
                    data = json.load(f)
                image_path = data.get('image_path')
                bboxes = data.get('bboxes', [])
                # テスト用ファイル除外
                if image_path and ("--test-" in image_path or "/test_" in image_path or "\\test_" in image_path or image_path.endswith("test.png")):
                    continue
                if debug:
                    print(f"[DEBUG] {fname} bboxes:", bboxes)
                entry = {
                    'image_path': image_path,
                    'bboxes': bboxes
                }
                if image_path:
                    dataset.append(entry)
            except (json.JSONDecodeError, OSError) as e:
                print(f"[dataset集約エラー] {fpath}: {e}")
    elif collect_mode == 'list':
        # listモードの実装（必要に応じて追加）
        pass
    # 保存
    try:
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump({'dataset': dataset}, f, ensure_ascii=False, indent=2)
        print(f"[INFO] データセットを保存: {out_path}")
        return True
    except Exception as e:
        print(f"[保存エラー] {out_path}: {e}")
        return False
