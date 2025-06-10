import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from ocr_value_extractor import extract_texts_with_boxes_from_documentai_result, load_ocr_cache, get_image_size_local
from data_collector import DataCollector
from google.cloud.documentai_v1.types import Document

if __name__ == '__main__':
    print("start data collector test")
    # テスト用OCRキャッシュJSONのパスは適宜指定
    test_jsons = [
        os.path.join(os.path.dirname(__file__), '../src/image_preview_cache/5aa53bb683ea38479f2bfa366eda2d20cce7292b.json'),
        os.path.join(os.path.dirname(__file__), '../src/image_preview_cache/17bbf90db20bf0b54e881740f891615907df65be.json'),
        os.path.join(os.path.dirname(__file__), '../src/image_preview_cache/7443f2223fce815325803f63da592061b5cca24f.json'),
    ]
    # 温度管理用キーワード定義ファイル
    keywords_path = os.path.join(os.path.dirname(__file__), 'collect_keywords_tempmanage.json')
    with open(keywords_path, encoding='utf-8') as f:
        collect_dict = json.load(f)
    collector = DataCollector(collect_dict)
    for test_json in test_jsons:
        print(f"--- test: {os.path.basename(test_json)} ---")
        with open(test_json, encoding='utf-8') as f:
            data = json.load(f)
        image_path = data.get('image_path')
        if not image_path:
            print(f"[SKIP] image_pathなし: {test_json}")
            continue
        try:
            img_w, img_h, local_path = get_image_size_local(image_path)
        except Exception as e:
            print(f"[WARN] 画像サイズ取得失敗: {image_path}: {e}")
            continue
        cache = load_ocr_cache(local_path)
        if cache is not None:
            document = Document.from_json(json.dumps(cache['document']))
            texts_with_boxes = extract_texts_with_boxes_from_documentai_result(document, img_w, img_h)
            result = collector.collect_pairs(texts_with_boxes)
            print("[COLLECTED PAIRS]", result)
        else:
            print(f"[SKIP] OCRキャッシュなし: {local_path}") 