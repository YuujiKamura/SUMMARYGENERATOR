"""
DetectResultWidget: 検出結果画像リストとプレビュー
"""
import os
import json
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QMessageBox, QMenu
from PyQt6.QtCore import Qt
from src.widgets.scan_for_images_widget import ScanForImagesWidget
from src.widgets.detect_result_utils import convert_role_json_to_annotation_dataset
from src.widgets.detect_result_dialogs import show_reassign_dialog, export_yolo_from_roles, validate_image_paths, show_bbox_completion_dialog
from src.widgets.detect_result_assign import assign_selected_images, _save_and_update, save_to_json, find_images_without_bboxes
from src.utils.models import Annotation, ClassDefinition, AnnotationDataset, BoundingBox
from src.widgets.image_preview_dialog import ImagePreviewDialog
from src.utils.path_manager import path_manager
from src.utils.chain_record_utils import ChainRecord
from src.widgets.incorrect_marker_widget import IncorrectMarkerWidget

class DetectResultWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle("DetectResultWidget - detect_result_widget.py")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("検出画像一覧"))
        self.image_widget = ScanForImagesWidget()
        layout.addWidget(self.image_widget, 1)
        self.image_paths = []
        self.bbox_dict = {}
        # --- ダブルクリックでプレビューを開く ---
        if hasattr(self.image_widget, 'fast_thumb_list'):
            self.image_widget.fast_thumb_list.doubleClicked.connect(self.on_image_double_clicked)
        # --- 検出結果テキスト表示欄を追加 ---
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        layout.addWidget(QLabel("検出結果テキスト"))
        layout.addWidget(self.result_text)
        self.setLayout(layout)
        self.assignment = {}
        self.test_mode = False
        self.save_dir = "seeds"
        logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../logs")
        logs_dir = os.path.abspath(logs_dir)
        os.makedirs(logs_dir, exist_ok=True)
        self._settings_path = os.path.join(logs_dir, "detect_result_widget_settings.json")
        self.restore_window_settings()
        if not hasattr(self, '_restored_size') or not self._restored_size:
            self.resize(1200, 800)
        self.incorrect_entries = []
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        IncorrectMarkerWidget(self)  # 不正解マーカー機能

    # --- 画像リスト・検出結果表示以外のロジックを削除 ---
    def set_images(self, image_paths, bbox_dict=None):
        print("[set_images] image_paths:", image_paths)
        self.image_paths = image_paths
        self.bbox_dict = bbox_dict or {}
        self.image_widget.set_images(image_paths, self.bbox_dict)  # bbox_dictも渡す
        if image_paths:
            self.show_detection_text(image_paths[0])
        if hasattr(self.image_widget, 'fast_thumb_list'):
            sel_model = self.image_widget.fast_thumb_list.selectionModel()
            if sel_model:
                sel_model.selectionChanged.connect(self.on_image_selection_changed)

    def on_image_selection_changed(self):
        selected = self.image_widget.get_selected_image_paths()
        if selected:
            self.show_detection_text(selected[0])

    def show_detection_text(self, img_path):
        dets = self.bbox_dict.get(img_path, [])
        if not dets:
            self.result_text.setText("検出結果なし")
            return
        lines = []
        for det in dets:
            bbox = det.get('bbox', [])
            cname = det.get('class_name', '')
            conf = det.get('confidence', 0)
            lines.append(f"{cname} conf={conf:.2f} bbox={bbox}")
        self.result_text.setText("\n".join(lines))

    def restore_window_settings(self):
        try:
            if os.path.exists(self._settings_path):
                with open(self._settings_path, "r", encoding="utf-8") as f:
                    s = json.load(f)
                if "size" in s:
                    self.resize(*s["size"])
                    self._restored_size = True
                if "pos" in s:
                    self.move(*s["pos"])
        except Exception:
            pass

    def save_window_settings(self):
        s = {
            "size": [self.width(), self.height()],
            "pos": [self.x(), self.y()]
        }
        with open(self._settings_path, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)

    def save_image_list(self):
        # 画像リストの保存
        try:
            paths = self.image_widget.image_paths if hasattr(self.image_widget, 'image_paths') else self.image_paths
            image_list_json = str(path_manager.last_images)
            Path(image_list_json).parent.mkdir(parents=True, exist_ok=True)
            with open(image_list_json, "w", encoding="utf-8") as f:
                json.dump(paths, f, ensure_ascii=False, indent=2)
            print(f"[画像リスト保存] {image_list_json} ({len(paths)}件)")
            path_manager.current_image_list_json = image_list_json
        except Exception as e:
            print(f"[画像リスト保存エラー] {e}")

    def closeEvent(self, event):
        self.save_image_list()
        self.save_window_settings()
        super().closeEvent(event)

    # --- 不要なメソッド・内部ロジックをすべて削除 ---
    def on_image_double_clicked(self, index):
        """
        サムネイル画像のダブルクリック時にImagePreviewDialogを開く
        """
        img_path = index.data(Qt.ItemDataRole.UserRole)
        if not img_path or not os.path.exists(img_path):
            QMessageBox.warning(self, "エラー", f"画像が存在しません: {img_path}")
            return
        dlg = ImagePreviewDialog(img_path, self)
        dlg.exec()

    def show_context_menu(self, pos):
        menu = QMenu(self)
        mark_action = menu.addAction("不正解としてマーク")
        action = menu.exec(self.mapToGlobal(pos))
        if action == mark_action:
            current_image = self.image_widget.current_image
            if current_image and current_image in self.bbox_dict:
                record = ChainRecord(
                    image_path=current_image,
                    bbox=self.bbox_dict[current_image],
                    remarks="incorrect_detection"
                )
                self.incorrect_entries.append(record)
                self.save_incorrect_entries()

    def save_incorrect_entries(self):
        if not self.incorrect_entries:
            return
        output_path = os.path.join(path_manager.get_retrain_data_dir(), "incorrect_entries.json")
        Path(os.path.dirname(output_path)).mkdir(parents=True, exist_ok=True)
        data = [record.to_dict() for record in self.incorrect_entries]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)