import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from path_manager import path_manager

def main(image_list_json, output_path=None):
    # 画像リストJSONを読み込む
    with open(image_list_json, encoding='utf-8') as f:
        image_list = json.load(f)
    if not isinstance(image_list, list):
        raise ValueError('画像リストJSONはリスト形式である必要があります')
    # キャッシュ全走査でimage_path逆引き辞書を作る
    cache_dir = path_manager.image_cache_dir
    cache_map = {}
    for json_file in Path(cache_dir).glob('*.json'):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            img_path = data.get('image_path')
            if img_path:
                cache_map[img_path] = (json_file, data)
        except Exception as e:
            print(f"[ERROR] {json_file}: {e}")
    # 画像リストJSONの各パスに対してキャッシュを逆引き
    master_list = []
    for img_path in image_list:
        if img_path in cache_map:
            json_file, data = cache_map[img_path]
            entry = {
                'filename': Path(json_file).name,
                'image_path': data.get('image_path'),
                'bboxes': data.get('bboxes'),
                # 必要なら他のメタ情報も追加可能
            }
            master_list.append(entry)
        else:
            print(f"[WARN] 個別画像JSONが見つかりません: {img_path}")
    # 出力先
    if output_path is None:
        output_path = Path(image_list_json).parent / 'image_preview_cache_master.json'
    else:
        output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(master_list, f, ensure_ascii=False, indent=2)
    print(f"マスタJSONを出力: {output_path} ({len(master_list)}件)")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="画像リストJSONから個別画像JSONを集約しマスタJSONを生成（キャッシュ全走査逆引き版）")
    parser.add_argument('--image_list_json', required=True, help='画像リストJSONファイル')
    parser.add_argument('--output', default=None, help='出力先マスタJSONファイル')
    args = parser.parse_args()
    main(args.image_list_json, args.output) 