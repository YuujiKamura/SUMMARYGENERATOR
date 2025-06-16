import sys
import os

# summarygeneratorプロジェクト用のパス設定
current_dir = os.path.dirname(os.path.abspath(__file__))
ocr_tools_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(ocr_tools_dir)
src_dir = os.path.join(project_root, 'src')

# パスを追加
sys.path.insert(0, ocr_tools_dir)
sys.path.insert(0, src_dir)

# デバッグ: パス確認
print(f"[DEBUG] current_dir: {current_dir}")
print(f"[DEBUG] ocr_tools_dir: {ocr_tools_dir}")
print(f"[DEBUG] project_root: {project_root}")
print(f"[DEBUG] src_dir: {src_dir}")

from ocr_value_extractor import process_image_json, init_documentai_engine, PRESET_ROLES_PATH, CACHE_DIR

if __name__ == '__main__':
    print("start test")
    print(f"[INFO] OCRツール統合テスト開始")
    print(f"[INFO] キャッシュディレクトリ: {CACHE_DIR}")
    
    # パスマネージャを使用してリソースパス解決済みの正しいキャッシュディレクトリを使用
    test_json = os.path.join(CACHE_DIR, 'c4d7269c03ff71c024e178e7819581dbae1fef3a.json')
    print(f"Testing with: {test_json}")
    print(f"File exists: {os.path.exists(test_json)}")
    
    engine = init_documentai_engine()
    process_image_json(test_json, PRESET_ROLES_PATH, engine)

    # 他のテストファイルも正しいパスで指定
    test_jsons = [
        os.path.join(CACHE_DIR, '5aa53bb683ea38479f2bfa366eda2d20cce7292b.json'),
        os.path.join(CACHE_DIR, '17bbf90db20bf0b54e881740f891615907df65be.json'),
        os.path.join(CACHE_DIR, '7443f2223fce815325803f63da592061b5cca24f.json'),
    ]
    engine = init_documentai_engine()
    for test_json in test_jsons:
        if os.path.exists(test_json):
            print(f"--- test: {os.path.basename(test_json)} ---")
            process_image_json(test_json, PRESET_ROLES_PATH, engine)
        else:
            print(f"[SKIP] File not found: {test_json}")
            
    print(f"[INFO] OCRツール統合テスト完了")