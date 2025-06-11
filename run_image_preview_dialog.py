# --- Copied from project root run_image_preview_dialog.py ---
import sys
import os
from PyQt6.QtWidgets import QApplication
# src配下に移動した場合のパス調整
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.abspath(os.path.join(current_dir, 'src'))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
from src.widgets.image_preview_dialog import ImagePreviewDialog
from src.utils.path_manager import path_manager
import json


def load_last_image_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    config_path = os.path.join(logs_dir, "image_preview_dialog_last.json")
    if not os.path.exists(config_path):
        return None
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("last_image_path")
    except Exception:
        return None

def save_last_image_path(path):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    config_path = os.path.join(logs_dir, "image_preview_dialog_last.json")
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"last_image_path": path}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        img_path = load_last_image_path()
        if not img_path:
            # image_preview_cache_master.jsonのトップエントリーを使う
            try:
                dataset_path = str(path_manager.image_preview_cache_master)
                with open(dataset_path, 'r', encoding='utf-8') as f:
                    dataset = json.load(f)
                if isinstance(dataset, list) and len(dataset) > 0 and 'image_path' in dataset[0]:
                    img_path = dataset[0]['image_path']
                    print(f"[INFO] image_preview_cache_master.jsonのトップ画像を使用: {img_path}")
                else:
                    print("使い方: python run_image_preview_dialog.py <画像ファイルパス>")
                    sys.exit(1)
            except Exception as e:
                print(f"使い方: python run_image_preview_dialog.py <画像ファイルパス> (エラー: {e})")
                sys.exit(1)
        print(f"[INFO] 最後に開いた画像を復元して起動: {img_path}")
    else:
        img_path = sys.argv[1]
    app = QApplication(sys.argv)
    dlg = ImagePreviewDialog(img_path)
    save_last_image_path(img_path)
    dlg.exec()
