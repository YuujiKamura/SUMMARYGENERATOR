# --- Copied from src/utils/datadeploy_test.py ---
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from summarygenerator.utils.data_manager import DataManager
from summarygenerator.utils.summary_generator import collect_image_data_from_cache
import subprocess

def run_datadeploy_test(dataset_json_path, cache_dir, use_thermo_special=True):
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
        image_data = collect_image_data_from_cache(cache_dir)
        print("個別JSON集約: 画像数=", len(image_data['image_roles']))
        print("個別JSON集約: フォルダ数=", len(image_data['folder_names']))
        return True
    except Exception as e:
        print("配備テストNG:", e)
        return False

def run_all_datadeploy_tests():
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
