import os
import glob
import json
from src.scan_for_images_dataset import save_dataset_json

def regen_scan_for_images_dataset(project_dir, debug=False):
    """
    指定プロジェクトディレクトリ内のimage_preview_cacheからscan_for_images_dataset.jsonを再生成し、
    事前サマリー・再生成結果・サマリー情報を返す。
    Returns:
        dict: {
            'cache_dir': str,
            'cache_jsons': list,
            'image_paths': list,
            'exist_count': int,
            'none_count': int,
            'pred_output': int,
            'out_path': str,
            'regen_ok': bool,
            'num_images': int,
            'num_bboxes': int,
            'summary_msg': str,
        }
    """
    cache_dir = os.path.join(project_dir, "image_preview_cache")
    image_dir = os.path.join(project_dir, "images")
    out_path = os.path.join(project_dir, "scan_for_images_dataset.json")
    cache_jsons = list(glob.glob(f"{cache_dir}/*.json")) if os.path.exists(cache_dir) else []
    image_paths = []
    exist_count = 0
    none_count = 0
    for json_path in cache_jsons:
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            img_path = data.get('image_path')
            if img_path:
                image_paths.append(img_path)
                if os.path.exists(img_path):
                    exist_count += 1
            else:
                none_count += 1
        except Exception:
            none_count += 1
    pred_output = len(image_paths)
    # 再生成
    regen_ok = save_dataset_json(cache_dir=cache_dir, out_path=out_path, debug=debug, collect_mode='all')
    # サマリー
    num_images = 0
    num_bboxes = 0
    summary_msg = ""
    if regen_ok:
        try:
            with open(out_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            num_images = len(data)
            num_bboxes = sum(len(entry.get('bboxes', [])) for entry in data)
            summary_msg = f"\n画像数: {num_images}\n全bbox数: {num_bboxes}"
        except Exception as e:
            summary_msg = f"\n[サマリー取得失敗] {e}"
    return {
        'cache_dir': cache_dir,
        'cache_jsons': cache_jsons,
        'image_paths': image_paths,
        'exist_count': exist_count,
        'none_count': none_count,
        'pred_output': pred_output,
        'out_path': out_path,
        'regen_ok': regen_ok,
        'num_images': num_images,
        'num_bboxes': num_bboxes,
        'summary_msg': summary_msg,
    } 