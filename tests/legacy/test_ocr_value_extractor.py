import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from ocr_value_extractor import process_image_json, init_documentai_engine, PRESET_ROLES_PATH, CACHE_DIR

if __name__ == '__main__':
    print("start test")
    # 添付のテストファイルのみでテスト
    test_json = os.path.join(CACHE_DIR, 'c4d7269c03ff71c024e178e7819581dbae1fef3a.json')
    engine = init_documentai_engine()
    process_image_json(test_json, PRESET_ROLES_PATH, engine)

    # 添付のテストファイルでテスト
    test_jsons = [
        os.path.join(CACHE_DIR, '../../src/image_preview_cache/5aa53bb683ea38479f2bfa366eda2d20cce7292b.json'),
        os.path.join(CACHE_DIR, '../../src/image_preview_cache/17bbf90db20bf0b54e881740f891615907df65be.json'),
        os.path.join(CACHE_DIR, '../../src/image_preview_cache/7443f2223fce815325803f63da592061b5cca24f.json'),
    ]
    engine = init_documentai_engine()
    for test_json in test_jsons:
        print(f"--- test: {os.path.basename(test_json)} ---")
        process_image_json(test_json, PRESET_ROLES_PATH, engine) 