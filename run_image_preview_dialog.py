# --- Copied from project root run_image_preview_dialog.py ---
import sys
import os
from PyQt6.QtWidgets import QApplication
# src配下に移動した場合のパス調整
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, 'src'))
sys.path.insert(0, project_root)
from widgets.image_preview_dialog import ImagePreviewDialog
import json


def load_last_image_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.abspath(os.path.join(base_dir, "image_preview_dialog_last.json"))
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
    config_path = os.path.abspath(os.path.join(base_dir, "image_preview_dialog_last.json"))
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"last_image_path": path}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        img_path = load_last_image_path()
        if not img_path:
            print("使い方: python run_image_preview_dialog.py <画像ファイルパス>")
            sys.exit(1)
        print(f"[INFO] 最後に開いた画像を復元して起動: {img_path}")
    else:
        img_path = sys.argv[1]
    app = QApplication(sys.argv)
    dlg = ImagePreviewDialog(img_path)
    save_last_image_path(img_path)
    dlg.exec()
