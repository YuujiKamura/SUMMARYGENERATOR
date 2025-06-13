import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from PyQt6.QtWidgets import QApplication
from src.widgets.detect_result_widget import DetectResultWidget
from src.utils.path_manager import path_manager
import json

class CustomDetectResultWidget(DetectResultWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._save_all_func = None
    def set_save_all_func(self, func):
        self._save_all_func = func
    def closeEvent(self, event):
        if self._save_all_func:
            self._save_all_func()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    image_paths = []
    bbox_dict = {}
    # 単体起動時のみ復元
    if len(sys.argv) == 1:
        detect_result_json = os.path.join(os.path.dirname(__file__), 'src', 'data', 'last_detect_results.json')
        if os.path.exists(detect_result_json):
            try:
                with open(detect_result_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                image_paths = data.get('image_paths', [])
                bbox_dict = data.get('bbox_dict', {})
                print(f"[検出結果復元] {detect_result_json} 画像: {len(image_paths)}件 bbox_dict: {len(bbox_dict)}件")
            except Exception as e:
                print(f"[検出結果復元エラー] {e}")
    widget = CustomDetectResultWidget()
    widget.set_images(image_paths, bbox_dict=bbox_dict)
    # 単体起動時のみ保存
    if len(sys.argv) == 1:
        def save_all():
            paths = widget.image_widget.image_paths if hasattr(widget.image_widget, 'image_paths') else widget.image_paths
            bboxes = widget.bbox_dict if hasattr(widget, 'bbox_dict') else {}
            from pathlib import Path
            detect_result_json = os.path.join(os.path.dirname(__file__), 'src', 'data', 'last_detect_results.json')
            Path(os.path.dirname(detect_result_json)).mkdir(parents=True, exist_ok=True)
            try:
                with open(detect_result_json, "w", encoding="utf-8") as f:
                    json.dump({'image_paths': paths, 'bbox_dict': bboxes}, f, ensure_ascii=False, indent=2)
                print(f"[検出結果保存] {detect_result_json} 画像: {len(paths)}件 bbox_dict: {len(bboxes)}件")
            except Exception as e:
                print(f"[検出結果保存エラー] {e}")
            widget.save_window_settings()
        widget.set_save_all_func(save_all)
        app.aboutToQuit.connect(save_all)
    widget.show()
    sys.exit(app.exec())
