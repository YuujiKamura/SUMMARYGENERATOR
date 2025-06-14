import sys
import os
import json
from pathlib import Path
from PyQt6.QtWidgets import QDialog, QApplication, QMessageBox, QVBoxLayout
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap
from src.utils.bbox_utils import BoundingBox
from src.services.yolo_service import YoloWorker
from src.services.cache_service import CacheService
from src.services.pixmap_loader import PixmapLoaderService
from src.ui.components.zoomable_mixin import ZoomableMixin
from src.ui.components.image_preview_ui_builder import build_image_preview_ui
from src.widgets.image_preview_data_load_thread import ImagePreviewDataLoadThread
from src.widgets.image_preview_json_utils import restore_bboxes_from_cache, save_bboxes_to_image_cache, show_current_json
from src.widgets.image_preview_box_ops import handle_box_right_clicked
from src.widgets.image_preview_role_utils import load_roles as ext_load_roles, load_last_image_path as ext_load_last_image_path, save_last_image_path as ext_save_last_image_path
from src.widgets.image_preview_event_handlers import mouse_press_event, close_event, accept as ext_accept, reject as ext_reject, done as ext_done
from src.utils.location_utils import LocationInputDialog, load_location_history, save_location_history
from src.utils.path_manager import path_manager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = str(path_manager.image_cache_dir)
CONFIG_PATH = os.path.abspath(os.path.join(BASE_DIR, "image_preview_dialog_last.json"))

DATASET_JSON_PATH = str(path_manager.scan_for_images_dataset)

class ImagePreviewDialog(QDialog, ZoomableMixin):
    """
    ImagePreviewDialog: 画像プレビューとYOLO検出・編集ダイアログ
    """
    # --- ズーム・リサイズ設定 ---
    ZOOM_LEVELS = [0.5, 1.0, 1.5]  # 小・中・大
    RESIZE_DEBOUNCE_MS = 50  # リサイズ反応速度（ミリ秒）
    # -------------------------
    image_json_saved = pyqtSignal(str)  # 追加: 画像パスを渡す
    reload_requested = pyqtSignal(str)  # リロード要求シグナル

    def __init__(self, img_path, parent=None, pixmap=None, json_path=None):
        super().__init__(parent)
        self.cache = CacheService()
        self.pixsvc = PixmapLoaderService()
        self._init_state(img_path, pixmap, json_path)
        self._build_widgets()  # UI部品をここで生やす
        self._connect_signals()
        self._start_async_loading()
        self._init_zoom(self.image_widget)

    def _init_state(self, img_path, pixmap, json_path):
        self.img_path = img_path
        self._input_pixmap = pixmap
        self.json_path = json_path
        self.setWindowTitle(Path(img_path).name)
        self.selected_model_path = None
        self.yolo = None
        self.bboxes = []
        self.selected_indices = []
        self.roles = []
        self._zoom_idx = 0
        self._zoom_scale = self.ZOOM_LEVELS[self._zoom_idx]
        self._zoom_timer = QTimer(self)
        self._zoom_timer.setSingleShot(True)
        self._offset_x = 0
        self._offset_y = 0
        self._status_anim_timer = QTimer(self)
        self._status_anim_phase = 0
        self._suppress_resize_event = False
        self._orig_size = (0, 0)

    def _build_widgets(self):
        build_image_preview_ui(self)

    def _connect_signals(self):
        self.model_selector.model_changed.connect(self._on_model_changed)
        self._zoom_timer.timeout.connect(self.update_image_with_bboxes)
        self._status_anim_timer.timeout.connect(self._update_status_anim)
        self.image_widget.role_edit_requested.connect(self.open_role_editor)
        self.image_widget.box_right_clicked.connect(self.on_box_right_clicked)  # 右クリックメニュー用

    def _start_async_loading(self):
        # バックグラウンドで画像・bbox・rolesロード
        self._data_load_thread = ImagePreviewDataLoadThread(self.img_path)
        self._data_load_thread.finished.connect(self._on_data_loaded)
        self._data_load_thread.start()

    def _on_model_changed(self, path):
        self.selected_model_path = path
        self.yolo = None
        if hasattr(self, 'status_label'):
            self.status_label.setText(f"モデル切替: {Path(self.selected_model_path).name}")

    def _on_data_loaded(self, pixmap, bboxes, roles, _):
        # ピクスマップ生成・エラーハンドリングをPixmapLoaderServiceに委譲
        self._pixmap, self._orig_size = self.pixsvc.load(self.img_path)
        # バウンディングボックスとロールの設定
        self.bboxes = [BoundingBox.from_dict(b) for b in bboxes] if bboxes else []
        self.roles = roles
        # ImageDisplayWidgetに画像とデータを設定
        self.image_widget.set_bboxes(self.bboxes)
        self.image_widget.set_roles(self.roles)
        self.image_widget.set_selected_indices(self.selected_indices)
        self.image_widget._pixmap = self._pixmap  # pylint: disable=protected-access
        self.image_widget._orig_size = self._orig_size  # pylint: disable=protected-access
        self.image_widget.update()
        # ズーム倍率を考慮した表示サイズ
        scaled_w = int(self._orig_size[0] * self._zoom_scale)
        scaled_h = int(self._orig_size[1] * self._zoom_scale)
        screen = QApplication.primaryScreen()
        if screen is not None:
            screen_size = screen.size()
            max_w = int(screen_size.width() * 0.8)
            max_h = int(screen_size.height() * 0.8)
        else:
            max_w = 1536
            max_h = 864
        disp_w = min(scaled_w, max_w)
        disp_h = min(scaled_h, max_h)
        self.image_widget.setFixedSize(disp_w, disp_h)
        vbox = self.layout() if isinstance(self.layout(), QVBoxLayout) else None
        if vbox is not None:
            vbox.setContentsMargins(4, 4, 4, 4)
            vbox.setSpacing(4)
        self.resize(disp_w + 16, disp_h + 80)
        self._update_location_label()

    def _load_location_from_cache(self):
        return self.cache.load_location_from_cache(self.img_path)

    def _update_location_label(self):
        location = self._load_location_from_cache()
        if location:
            self.location_label.setText(f"測点：{location}")
        else:
            self.location_label.setText("測点：未設定")

    def load_roles(self):
        return ext_load_roles(self)

    def set_image(self, image_path):
        self._pixmap = QPixmap(image_path)  # 原寸
        self._orig_size = (self._pixmap.width(), self._pixmap.height())
        self.update_image_with_bboxes()

    def restore_bboxes_from_cache(self):
        restore_bboxes_from_cache(self)

    def save_bboxes_to_image_cache(self):
        return save_bboxes_to_image_cache(self)

    def update_image_with_bboxes(self):
        # self.labelの代わりにwidgetへ反映
        if hasattr(self, '_pixmap'):
            self.image_widget.set_bboxes(self.bboxes)
            self.image_widget.set_roles(self.roles)
            self.image_widget.set_selected_indices(self.selected_indices)
        # ウィンドウサイズは変更しない

    def run_yolo_detection(self) -> None:
        self.detect_btn.setEnabled(False)
        self.status_label.setText("YOLO検出中")
        self._status_anim_phase = 0
        self._status_anim_timer.start(300)
        model_path = self.selected_model_path or ""
        self._yolo_worker = YoloWorker(
            self.img_path,
            model_path,
            self.merge_checkbox.isChecked(),
            self.bboxes,
            self.roles
        )
        self._yolo_worker.finished.connect(self._on_yolo_detection_finished_thread)
        self._yolo_worker.start()

    def _on_yolo_detection_finished_thread(self, bboxes, error):
        self.detect_btn.setEnabled(True)
        self._status_anim_timer.stop()
        if error is not None:
            self.status_label.setText("YOLO検出失敗")
            QMessageBox.warning(self, "YOLOエラー", f"YOLO推論に失敗しました: {error}")
            return
        self.bboxes = bboxes
        self.selected_indices = []
        self.update_image_with_bboxes()
        self.save_bboxes_to_image_cache()
        self.status_label.setText("YOLO検出完了")

    def _update_status_anim(self):
        dots = "." * (self._status_anim_phase % 4)
        self.status_label.setText(f"YOLO検出中{dots}")
        self._status_anim_phase += 1

    def on_yolo_detection_finished(self, bboxes, error):
        self.detect_btn.setEnabled(True)
        self._status_anim_timer.stop()
        if error is not None:
            self.status_label.setText("YOLO検出失敗")
            QMessageBox.warning(self, "YOLOエラー", f"YOLO推論に失敗しました: {error}")
            return
        self.bboxes = bboxes
        self.selected_indices = []
        self.update_image_with_bboxes()
        self.save_bboxes_to_image_cache()
        self.status_label.setText("YOLO検出完了")

    def load_last_image_path(self):
        return ext_load_last_image_path(CONFIG_PATH)

    def save_last_image_path(self, path):
        ext_save_last_image_path(CONFIG_PATH, path)

    def save_and_emit(self):
        self.bboxes = self.image_widget.bboxes.copy()
        saved = self.save_bboxes_to_image_cache()
        if not saved:
            return
        self.save_last_image_path(self.img_path)
        self.image_json_saved.emit(self.img_path)  # emitはここだけ
        self.status_label.setText(f"[LOG] 保存・emit完了: {self.img_path}")

    # --- イベントハンドラは外部ラッパーで統一 ---
    def wheelEvent(self, event):
        ZoomableMixin.wheelEvent(self, event)
    def mousePressEvent(self, event):
        mouse_press_event(self, event)
    def closeEvent(self, event):
        close_event(self, event)
    def accept(self):
        ext_accept(self)
    def reject(self):
        ext_reject(self)
    def done(self, r):
        ext_done(self, r)
    # --- ここまで ---

    def open_role_editor(self):
        import importlib
        if 'src.role_editor_dialog' in sys.modules:
            importlib.reload(sys.modules['src.role_editor_dialog'])
        else:
            from src.widgets.role_editor_dialog import RoleEditorDialog
        RoleEditorDialog = sys.modules['src.role_editor_dialog'].RoleEditorDialog
        dlg_local = RoleEditorDialog(self)
        if dlg_local.exec() == QDialog.DialogCode.Accepted:
            self.roles = self.load_roles()
            self.image_widget.set_roles(self.roles)
            self.update_image_with_bboxes()

    def open_single_label_maker(self):
        from src.widgets.single_label_maker_dialog import SingleLabelMakerDialog
        preset_path = str(path_manager.preset_roles)
        try:
            with open(preset_path, 'r', encoding='utf-8') as f:
                class_list = json.load(f)
        except Exception as exc:
            QMessageBox.warning(self, "エラー", f"クラスリストの読込に失敗しました: {exc}")
            return
        dlg_local = SingleLabelMakerDialog(self.img_path, class_list, self, bboxes=self.bboxes)
        dlg_local.image_json_saved.connect(lambda _: self.image_json_saved.emit(self.img_path))
        if dlg_local.exec() == QDialog.DialogCode.Accepted:
            # キャッシュからbboxesを再読込し、再描画
            self.restore_bboxes_from_cache()
            self.update_image_with_bboxes()

    def on_box_right_clicked(self, indices):
        handle_box_right_clicked(self, indices)

    def show_current_json(self):
        show_current_json(self)

    def assign_location(self):
        dlg_local = LocationInputDialog(self)
        if dlg_local.exec() == QDialog.DialogCode.Accepted:
            text = dlg_local.get_text()
            if text:
                history = load_location_history()
                if text in history:
                    history.remove(text)
                history.insert(0, text)
                history = history[:20]
                save_location_history(history)
                self.cache.save_location(self.img_path, text)
                self.status_label.setText(f"測点（location）を割り当てました: {text}")
                self._update_location_label()

def load_last_image_path():
    return ext_load_last_image_path(CONFIG_PATH)

def save_last_image_path(path):
    ext_save_last_image_path(CONFIG_PATH, path)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-datadeploy", action="store_true")
    args = parser.parse_args()
    if args.test_datadeploy:
        from src.utils.datadeploy_test import run_datadeploy_test
        from os.path import dirname, abspath, join
        BASE_DIR = dirname(abspath(__file__))
        DATASET_JSON_PATH = join(BASE_DIR, "scan_for_images_dataset.json")
        CACHE_DIR = join(BASE_DIR, "image_preview_cache")
        run_datadeploy_test(DATASET_JSON_PATH, CACHE_DIR, use_thermo_special=True)

    app = QApplication(sys.argv)
    image_path = sys.argv[1] if len(sys.argv) > 1 else load_last_image_path() or "test.jpg"
    dlg_main = ImagePreviewDialog(image_path)
    save_last_image_path(image_path)
    dlg_main.exec()