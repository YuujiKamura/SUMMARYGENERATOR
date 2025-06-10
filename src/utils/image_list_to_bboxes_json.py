import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

def image_list_to_bboxes_json(
    image_list_json: str,
    cache_dir: str,
    output_json: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    画像パスリストとキャッシュディレクトリからbboxes付きリストを再構成する。
    Args:
        image_list_json: 画像パスだけのJSON
        cache_dir: 個別画像JSON(bboxes付き)が格納されたディレクトリ
        output_json: 出力先パス（指定時のみ保存）
    Returns:
        bboxes付きリスト
    """
    with open(image_list_json, encoding="utf-8") as f:
        image_list = json.load(f)
    # キャッシュ全読み込み
    cache_map = {}
    for fname in os.listdir(cache_dir):
        if not fname.endswith('.json'):
            continue
        fpath = os.path.join(cache_dir, fname)
        try:
            with open(fpath, encoding='utf-8') as cf:
                data = json.load(cf)
            img_path = data.get('image_path')
            if img_path:
                cache_map[os.path.abspath(img_path)] = data
        except Exception:
            continue
    # 再構成
    result = []
    for img_path in image_list:
        abs_path = os.path.abspath(img_path)
        cache = cache_map.get(abs_path)
        bboxes = cache.get('bboxes', []) if cache else []
        result.append({"image_path": img_path, "bboxes": bboxes})
    if output_json:
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    return result

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="画像パスリスト→bboxes付きリスト再構成")
    parser.add_argument("--image_list_json", required=True, help="画像パスリストJSON")
    parser.add_argument("--cache_dir", required=True, help="個別画像JSONディレクトリ")
    parser.add_argument("--output_json", required=True, help="出力先bboxes付きJSON")
    args = parser.parse_args()
    image_list_to_bboxes_json(args.image_list_json, args.cache_dir, args.output_json)
    print(f"再構成完了: {args.output_json}") 