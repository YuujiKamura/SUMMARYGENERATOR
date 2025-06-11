import sys
import os
# プロジェクトルート（PhotoCategorizer）をsys.pathに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.data_manager import DataManager
from src.summary_generator import collect_image_data_from_cache
import subprocess

def run_datadeploy_test(dataset_json_path, cache_dir, use_thermo_special=True):
    """
    DIで渡されたパスでDataManager/collect_image_data_from_cacheを使い、
    データ流通の疎通テストを行う。printとexit codeで結果を返す。
    """
    print(f"[datadeploy_test] dataset_json_path={dataset_json_path}")
    print(f"[datadeploy_test] cache_dir={cache_dir}")
    try:
        dm = DataManager(
            json_path=dataset_json_path,
            folder_path=cache_dir,
            use_thermo_special=use_thermo_special
        )
        dm.reload()
        print("配備テストOK: 画像数=", len(dm.get_image_roles()))
        print("フォルダ数=", len(dm.get_folder_names()))
        print("レコード数=", len(dm.get_records()))
        # 追加: 個別JSON群から直接集約
        image_data = collect_image_data_from_cache(cache_dir)
        print("個別JSON集約: 画像数=", len(image_data['image_roles']))
        print("個別JSON集約: フォルダ数=", len(image_data['folder_names']))
        return True
    except Exception as e:
        print("配備テストNG:", e)
        return False

def run_all_datadeploy_tests():
    """
    src配下の主要な依存モジュールすべてに対して--test-datadeployを一括実行する
    """
    # プロジェクトルート（PhotoCategorizer）
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_root_parent = os.path.dirname(project_root)
    targets = [
        "summary_generator_widget.py",
        "data_manager.py",
        "summary_generator.py",
        "scan_for_images_widget.py",
        "dictionary_mapping_widget.py",
        "image_preview_dialog.py",
        "excel_photobook_exporter.py",
    ]
    all_ok = True
    for fname in targets:
        modname = f"src.{os.path.splitext(fname)[0]}"
        print(f"\n===== {fname} 配備テスト =====")
        result = subprocess.run([sys.executable, "-m", modname, "--test-datadeploy"], capture_output=True, encoding="utf-8", errors="replace", cwd=project_root_parent)
        print(result.stdout)
        if result.stderr:
            print("[stderr]", result.stderr)
        if result.returncode != 0:
            print(f"[NG] {fname} 配備テスト失敗")
            all_ok = False
        else:
            print(f"[OK] {fname} 配備テスト成功")
    if all_ok:
        print("\n=== 全モジュール配備テストOK ===")
        sys.exit(0)
    else:
        print("\n=== 一部モジュールで配備テストNG ===")
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="全モジュール一括配備テスト")
    args = parser.parse_args()
    if args.all:
        run_all_datadeploy_tests()
    else:
        # デフォルトは単体テスト（手動でパス指定）
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        DATASET_JSON_PATH = os.path.join(base_dir, "scan_for_images_dataset.json")
        CACHE_DIR = os.path.join(base_dir, "image_preview_cache")
        run_datadeploy_test(DATASET_JSON_PATH, CACHE_DIR, use_thermo_special=True) 