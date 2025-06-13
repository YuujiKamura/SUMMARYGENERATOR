import sys
import os
import pickle
import json
from pathlib import Path
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QComboBox, QApplication, QMessageBox, QMenu, QListWidget, QWidgetAction, QCheckBox, QHBoxLayout, QTextEdit, QStatusBar
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QCursor
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from src.utils.bbox_utils import is_point_in_bbox_scaled, BoundingBox
import hashlib
from src.widgets.role_editor_dialog import RoleEditorDialog
import importlib
from src.utils.image_cache_utils import save_image_cache, load_image_cache, get_image_cache_path
from src.widgets.image_display_widget import ImageDisplayWidget
from src.utils.location_utils import LocationInputDialog, load_location_history, save_location_history
from src.widgets.single_label_maker_dialog import SingleLabelMakerDialog
from src.utils.last_opened_path import save_last_path, load_last_path
from src.components.role_tree_selector import RoleTreeSelector
from src.components.json_bbox_viewer_dialog import JsonBboxViewerDialog
from src.utils.path_manager import path_manager
from src.utils.model_manager import ModelManager
from src.widgets.model_selector_widget import ModelSelectorWidget

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = str(path_manager.image_cache_dir)
CONFIG_PATH = os.path.abspath(os.path.join(BASE_DIR, "image_preview_dialog_last.json"))

DATASET_JSON_PATH = str(path_manager.scan_for_images_dataset)

class ImagePreviewDataLoadThread(QThread):
    finished = pyqtSignal(object, object, list, list)
    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path
    def run(self):
        print(f"[DEBUG IPDLT] Loading image from: {self.image_path}")
        
        # 画像読み込み処理の改善版
        pixmap = QPixmap()  # 初期化
        
        # パラメータ（引数）として渡されたパスで試行
        if os.path.exists(self.image_path):
            print(f"[DEBUG IPDLT] 画像ファイルは存在しています: {self.image_path}")
            
            # 複数の方法を順番に試す
            load_methods = [
                # 方法1: 直接パスを使用
                lambda: QPixmap(self.image_path),
                # 方法2: pathlibを使用
                lambda: QPixmap(str(Path(self.image_path))),
                # 方法3: os.fsdecodeを使用
                lambda: QPixmap(os.fsdecode(self.image_path)),
                # 方法4: フルパスに変換
                lambda: QPixmap(os.path.abspath(self.image_path)),
                # 方法5: 相対パスに変換
                lambda: QPixmap(os.path.relpath(self.image_path))
            ]
            
            for i, load_method in enumerate(load_methods):
                try:
                    temp_pixmap = load_method()
                    if not temp_pixmap.isNull():
                        pixmap = temp_pixmap
                        print(f"[DEBUG IPDLT] 方法{i+1}で成功: サイズ {pixmap.width()}x{pixmap.height()}")
                        break
                    else:
                        print(f"[DEBUG IPDLT] 方法{i+1}は失敗 (Null pixmap)")
                except Exception as e:
                    print(f"[DEBUG IPDLT] 方法{i+1}でエラー: {e}")

        if pixmap.isNull():
            print(f"[DEBUG IPDLT] 全ての読み込み方法を試しましたが、画像を読み込めませんでした: {self.image_path}")
            # フォールバック：エラーメッセージ画像を作成
            error_pixmap = QPixmap(400, 300)
            error_pixmap.fill(QColor(240, 240, 240))
            painter = QPainter(error_pixmap)
            painter.setPen(QColor(255, 0, 0))
            painter.drawText(error_pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "画像読み込みエラー")
            painter.end()
            pixmap = error_pixmap
        else:
            print(f"[DEBUG IPDLT] 画像読み込み成功: {self.image_path}, サイズ: {pixmap.width()}x{pixmap.height()}")
        
        # 付加情報の読み込み
        _, bboxes = load_image_cache(self.image_path)
        preset_path = str(path_manager.preset_roles)
        try:
            with open(preset_path, 'r', encoding='utf-8') as f:
                roles = json.load(f)
        except Exception as e:
            print(f"[WARNING] ロール定義読み込みエラー: {e}")
            roles = []
            
        # 読み込んだデータをシグナル送信
        self.finished.emit(pixmap, bboxes, roles, [])

class ImagePreviewDialog(QDialog):
    # --- ズーム・リサイズ設定 ---
    ZOOM_LEVELS = [0.5, 1.0, 1.5]  # 小・中・大
    RESIZE_DEBOUNCE_MS = 50  # リサイズ反応速度（ミリ秒）
    # -------------------------
    image_json_saved = pyqtSignal(str)  # 追加: 画像パスを渡す
    reload_requested = pyqtSignal(str)  # リロード要求シグナル

    def __init__(self, img_path, parent=None, pixmap=None, json_path=None):
        super().__init__(parent)
        print(f"[DEBUG IPD] 初期化開始 - 画像パス: {img_path}")
        self.img_path = img_path
        self._input_pixmap = pixmap  # 外部から渡されたピクスマップ
        self.json_path = json_path
        self.setWindowTitle(Path(img_path).name)
        vbox = QVBoxLayout(self)
        # --- モデル選択ウィジェット ---
        self.model_selector = ModelSelectorWidget(self)
        vbox.addWidget(self.model_selector)
        self.selected_model_path = self.model_selector.get_selected_model_path()
        self.model_selector.model_changed.connect(self._on_model_changed)
        # --- 画像表示ウィジェット ---
        self.image_widget = ImageDisplayWidget(self)
        self.image_widget.draw_global_selection_frame = False  # プレビューでは青枠を消す
        vbox.addWidget(self.image_widget)
        # --- 下部にボタン群 ---
        bottom_vbox = QVBoxLayout()
        btn_hbox = QHBoxLayout()
        btn = QPushButton("JSON保存して閉じる")
        btn.clicked.connect(self.accept)
        btn_hbox.addWidget(btn)
        self.detect_btn = QPushButton("YOLO物体検出")
        self.detect_btn.clicked.connect(self.run_yolo_detection)
        btn_hbox.addWidget(self.detect_btn)
        self.single_label_btn = QPushButton("シングルラベル追加")
        self.single_label_btn.clicked.connect(self.open_single_label_maker)
        btn_hbox.addWidget(self.single_label_btn)
        self.show_json_btn = QPushButton("JSON確認")
        self.show_json_btn.clicked.connect(self.show_current_json)
        btn_hbox.addWidget(self.show_json_btn)
        self.assign_location_btn = QPushButton("測点割当")
        self.assign_location_btn.clicked.connect(self.assign_location)
        btn_hbox.addWidget(self.assign_location_btn)
        bottom_vbox.addLayout(btn_hbox)
        self.merge_checkbox = QCheckBox("ロール割当をマージ")
        self.merge_checkbox.setChecked(True)
        bottom_vbox.addWidget(self.merge_checkbox)
        vbox.addLayout(bottom_vbox)
        # --- ステータスバー（測点表示＋メッセージ） ---
        self.status_bar = QStatusBar(self)
        self.location_label = QLabel()
        self.location_label.setStyleSheet("font-weight: bold; color: #1a237e; padding: 2px 0;")
        self.status_bar.addWidget(self.location_label, 1)
        self.status_label = QLabel("")
        self.status_bar.addPermanentWidget(self.status_label, 1)
        vbox.addWidget(self.status_bar)
        self.setMinimumSize(400, 300)
        self.yolo = None
        self.bboxes = []
        self.selected_indices = []  # 複数選択対応
        self.roles = []
        self._zoom_idx = 0  # デフォルトは小（0.5）
        self._zoom_scale = self.ZOOM_LEVELS[self._zoom_idx]
        self._zoom_timer = QTimer(self)
        self._zoom_timer.setSingleShot(True)
        self._zoom_timer.timeout.connect(self.update_image_with_bboxes)
        self._suppress_resize_event = False  # resizeEvent抑制用フラグ
        self._offset_x = 0
        self._offset_y = 0
        # ステータスアニメーション用
        self._status_anim_timer = QTimer(self)
        self._status_anim_timer.timeout.connect(self._update_status_anim)
        self._status_anim_phase = 0
        # バックグラウンドで画像・bbox・rolesロード
        self._data_load_thread = ImagePreviewDataLoadThread(img_path)
        self._data_load_thread.finished.connect(self._on_data_loaded)
        self._data_load_thread.start()
        self.image_widget.role_edit_requested.connect(self.open_role_editor)
        self.image_widget.box_right_clicked.connect(self.on_box_right_clicked)

        # レイアウトが未設定の場合は明示的に設定
        if self.layout() is None:
            self.setLayout(vbox)
        # setContentsMargins/setSpacingはQVBoxLayoutインスタンスでのみ呼ぶ
        vbox.setContentsMargins(4, 4, 4, 4)
        vbox.setSpacing(4)

    def _on_model_changed(self, path):
        self.selected_model_path = path
        self.yolo = None
        if hasattr(self, 'status_label'):
            self.status_label.setText(f"モデル切替: {Path(self.selected_model_path).name}")

    def _on_data_loaded(self, pixmap, bboxes, roles, _):
        print(f"[DEBUG IPD] _on_data_loaded called. スレッドからのpixmapは無効: {pixmap is None or pixmap.isNull()}")
        
        # 外部から渡されたピクスマップを優先使用
        if self._input_pixmap and not self._input_pixmap.isNull():
            self._pixmap = self._input_pixmap
            print(f"[DEBUG IPD] 引数で渡されたピクスマップを使用: {self._pixmap.width()}x{self._pixmap.height()}")
        else:
            # スレッドからのピクスマップを使用
            self._pixmap = pixmap
            if self._pixmap and not self._pixmap.isNull():
                print(f"[DEBUG IPD] スレッドからのピクスマップを使用: {self._pixmap.width()}x{self._pixmap.height()}")
            else:
                print("[DEBUG IPD] 有効なピクスマップがありません。ダミー画像を作成します。")
                # ダミー画像の作成
                self._pixmap = QPixmap(400, 300)
                self._pixmap.fill(QColor(220, 220, 220))
                painter = QPainter(self._pixmap)
                painter.setPen(QColor(255, 0, 0))
                painter.drawText(self._pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "画像読み込みエラー")
                painter.end()
                
        # 画像サイズを記録
        self._orig_size = (self._pixmap.width(), self._pixmap.height())
        
        # バウンディングボックスとロールの設定
        self.bboxes = [BoundingBox.from_dict(b) for b in bboxes] if bboxes else []
        self.roles = roles
        
        # ImageDisplayWidgetに画像とデータを設定
        self.image_widget.set_bboxes(self.bboxes)
        self.image_widget.set_roles(self.roles)
        self.image_widget.set_selected_indices(self.selected_indices)
        
        # ピクスマップを直接設定（パス名からの読み込みは使わない）
        self.image_widget._pixmap = self._pixmap
        self.image_widget._orig_size = self._orig_size
        self.image_widget.update()
        # ズーム倍率を考慮した表示サイズ
        scaled_w = int(self._orig_size[0] * self._zoom_scale)
        scaled_h = int(self._orig_size[1] * self._zoom_scale)
        # 画面サイズ取得
        screen = QApplication.primaryScreen()
        if screen is not None:
            screen_size = screen.size()
            max_w = int(screen_size.width() * 0.8)
            max_h = int(screen_size.height() * 0.8)
        else:
            # デフォルト値（FHD相当）
            max_w = 1536
            max_h = 864
        # 最大値で制限
        disp_w = min(scaled_w, max_w)
        disp_h = min(scaled_h, max_h)
        # ラベル・ウィンドウサイズを調整
        self.image_widget.setFixedSize(disp_w, disp_h)
        # setContentsMargins/setSpacingはQVBoxLayoutインスタンスでのみ呼ぶ
        vbox = self.layout() if isinstance(self.layout(), QVBoxLayout) else None
        if vbox is not None:
            vbox.setContentsMargins(4, 4, 4, 4)
            vbox.setSpacing(4)
        self.resize(disp_w + 16, disp_h + 80)
        self._update_location_label()

    def _load_location_from_cache(self):
        json_path = get_image_cache_path(self.img_path)
        location = None
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                location = data.get("location")
            except Exception:
                location = None
        return location

    def _update_location_label(self):
        location = self._load_location_from_cache()
        if location:
            self.location_label.setText(f"測点：{location}")
        else:
            self.location_label.setText("測点：未設定")

    def load_roles(self):
        preset_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'preset_roles.json'))
        try:
            with open(preset_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"ロール読込失敗: {e}")
            return []

    def set_image(self, image_path):
        self._pixmap = QPixmap(image_path)  # 原寸
        self._orig_size = (self._pixmap.width(), self._pixmap.height())
        self.update_image_with_bboxes()

    def restore_bboxes_from_cache(self):
        # 共通関数でキャッシュ読込
        _, bboxes = load_image_cache(self.img_path)
        if bboxes:
            self.bboxes = [BoundingBox.from_dict(b) for b in bboxes]
            print(f"[共通キャッシュ復元] {self.img_path} bboxes: {self.bboxes}")
        else:
            self.bboxes = []
            print(f"[共通キャッシュ復元] {self.img_path} bboxes: EMPTY")

    def save_bboxes_to_image_cache(self):
        # 保存前に確認ダイアログを表示
        ret = QMessageBox.question(self, "キャッシュ上書き確認", "この検出結果でキャッシュ（image_preview_cache）を上書きしますか？",
                                   QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        if ret != QMessageBox.StandardButton.Ok:
            self.status_label.setText("[LOG] 保存をキャンセルしました")
            return False
        ok = save_image_cache(self.img_path, self.bboxes)
        if ok:
            print(f"[共通キャッシュ保存] {self.img_path} bboxes: {self.bboxes}")
        return ok

    def update_image_with_bboxes(self):
        # self.labelの代わりにwidgetへ反映
        if hasattr(self, '_pixmap'):
            self.image_widget.set_bboxes(self.bboxes)
            self.image_widget.set_roles(self.roles)
            self.image_widget.set_selected_indices(self.selected_indices)
        # ウィンドウサイズは変更しない

    def run_yolo_detection(self):
        from src.yolo_predict_core import YOLOPredictor
        predictor = YOLOPredictor(std_model_path=self.selected_model_path)
        merge_roles = self.merge_checkbox.isChecked()
        preds = predictor.predict(self.img_path, merge_roles=merge_roles, old_bboxes=self.bboxes, roles=self.roles)
        self.bboxes = preds
        self.image_widget.set_bboxes(self.bboxes)
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
        return load_last_path(CONFIG_PATH, "last_image_path")

    def save_last_image_path(self, path):
        save_last_path(CONFIG_PATH, "last_image_path", path)

    def save_and_emit(self):
        self.bboxes = self.image_widget.bboxes.copy()
        saved = self.save_bboxes_to_image_cache()
        if not saved:
            return
        self.save_last_image_path(self.img_path)
        self.image_json_saved.emit(self.img_path)  # emitはここだけ
        self.status_label.setText(f"[LOG] 保存・emit完了: {self.img_path}")

    def accept(self):
        super().accept()

    def reject(self):
        super().reject()

    def done(self, r):
        super().done(r)

    def closeEvent(self, event):
        # バツボタンで閉じた時は何も処理しない
        super().closeEvent(event)

    def wheelEvent(self, event):
        angle = event.angleDelta().y()
        prev_idx = self._zoom_idx
        prev_scale = self._zoom_scale
        if angle > 0 and self._zoom_idx < len(self.ZOOM_LEVELS) - 1:
            self._zoom_idx += 1
        elif angle < 0 and self._zoom_idx > 0:
            self._zoom_idx -= 1
        if self._zoom_idx != prev_idx:
            self._zoom_scale = self.ZOOM_LEVELS[self._zoom_idx]
            # --- マウス座標を中心にズーム ---
            mouse_pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
            label_size = self.image_widget.size()
            # 画像の左上座標（現在のオフセット込み）
            base_w, base_h = label_size.width(), label_size.height()
            scaled_w_prev = int(self._orig_size[0] * prev_scale)
            scaled_h_prev = int(self._orig_size[1] * prev_scale)
            x0_prev = (base_w - scaled_w_prev) // 2 + self._offset_x
            y0_prev = (base_h - scaled_h_prev) // 2 + self._offset_y
            # マウス座標が画像内のどこか
            rel_x = mouse_pos.x() - x0_prev
            rel_y = mouse_pos.y() - y0_prev
            if 0 <= rel_x < scaled_w_prev and 0 <= rel_y < scaled_h_prev:
                # 画像内なら、その点がズーム後も同じ位置に来るようにオフセット調整
                scaled_w_new = int(self._orig_size[0] * self._zoom_scale)
                scaled_h_new = int(self._orig_size[1] * self._zoom_scale)
                ratio_x = rel_x / scaled_w_prev
                ratio_y = rel_y / scaled_h_prev
                rel_x_new = int(ratio_x * scaled_w_new)
                rel_y_new = int(ratio_y * scaled_h_new)
                x0_new = mouse_pos.x() - rel_x_new
                y0_new = mouse_pos.y() - rel_y_new
                self._offset_x = x0_new - (base_w - scaled_w_new) // 2
                self._offset_y = y0_new - (base_h - scaled_h_new) // 2
            else:
                # 画像外なら中央ズーム
                self._offset_x = 0
                self._offset_y = 0
            self.update_image_with_bboxes()

    def open_role_editor(self):
        import importlib
        import sys
        if 'src.role_editor_dialog' in sys.modules:
            importlib.reload(sys.modules['src.role_editor_dialog'])
        else:
            from src.widgets.role_editor_dialog import RoleEditorDialog
        RoleEditorDialog = sys.modules['src.role_editor_dialog'].RoleEditorDialog
        dlg = RoleEditorDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.roles = self.load_roles()
            self.image_widget.set_roles(self.roles)
            self.update_image_with_bboxes()

    def open_single_label_maker(self):
        # 直接importして参照する形に修正
        from src.widgets.single_label_maker_dialog import SingleLabelMakerDialog
        preset_path = str(path_manager.preset_roles)
        try:
            with open(preset_path, 'r', encoding='utf-8') as f:
                class_list = json.load(f)
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"クラスリストの読込に失敗しました: {e}")
            return
        dlg = SingleLabelMakerDialog(self.img_path, class_list, self, bboxes=self.bboxes)
        dlg.image_json_saved.connect(lambda _: self.image_json_saved.emit(self.img_path))
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # キャッシュからbboxesを再読込し、再描画
            self.restore_bboxes_from_cache()
            self.update_image_with_bboxes()

    def on_box_right_clicked(self, indices):
        if not indices:
            return
        menu = QMenu(self)
        role_selector = RoleTreeSelector(self.roles)
        action = QWidgetAction(menu)
        action.setDefaultWidget(role_selector)
        menu.addAction(action)
        menu.addSeparator()
        delete_action = menu.addAction("選択ボックスを削除")
        dupdel_action = menu.addAction("重複ボックス検出削除")
        edit_action = menu.addAction("ロール編集...")

        def on_role_selected(role_label):
            for idx in indices:
                self.bboxes[idx].role = role_label
            self.update_image_with_bboxes()
            self.save_bboxes_to_image_cache()
            menu.close()
        role_selector.role_selected.connect(on_role_selected)

        selected_action = menu.exec(self.mapToGlobal(self.image_widget.mapFromGlobal(QCursor.pos())))
        if selected_action == delete_action:
            # インデックス降順で削除（indexズレ防止）
            for idx in sorted(indices, reverse=True):
                if 0 <= idx < len(self.bboxes):
                    del self.bboxes[idx]
            self.selected_indices = []
            self.update_image_with_bboxes()
            self.save_bboxes_to_image_cache()
        elif selected_action == dupdel_action:
            # 重複ボックス検出削除
            def is_same_box(b1, b2):
                if b1.cid != b2.cid or b1.cname != b2.cname or b1.role != b2.role:
                    return False
                return all(abs(a-b) < 1.0 for a, b in zip(b1.xyxy, b2.xyxy))
            unique = []
            for b in self.bboxes:
                if not any(is_same_box(b, u) for u in unique):
                    unique.append(b)
            if len(unique) < len(self.bboxes):
                self.bboxes = unique
                self.selected_indices = []
                self.update_image_with_bboxes()
                self.save_bboxes_to_image_cache()
        elif selected_action == edit_action:
            self.open_role_editor()

    def mousePressEvent(self, event):
        # 右クリック独自処理は不要、親クラスへ
        super().mousePressEvent(event)

    def show_current_json(self):
        # 最新のキャッシュJSONを必ず再読込して表示
        from src.utils.image_cache_utils import get_image_cache_path
        cache_path = get_image_cache_path(self.img_path)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        else:
            data = {}
        # bboxesもUIから最新取得
        self.bboxes = self.image_widget.bboxes.copy()
        # locationもキャッシュから取得
        dlg = JsonBboxViewerDialog(self.img_path, cache_path, self)
        dlg.image_json_saved.connect(lambda _: self.image_json_saved.emit(self.img_path))
        dlg.exec()

    def assign_location(self):
        dlg = LocationInputDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            text = dlg.get_text()
            if text:
                # 履歴に追加（重複なし、先頭）
                history = load_location_history()
                if text in history:
                    history.remove(text)
                history.insert(0, text)
                history = history[:20]  # 最大20件
                save_location_history(history)
                # bboxesも含めてlocationを同時保存
                from src.utils.image_cache_utils import get_image_cache_path
                json_path = get_image_cache_path(self.img_path)
                # 既存キャッシュを読み込み
                if os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                    except Exception:
                        data = {}
                else:
                    data = {}
                bboxes = data.get("bboxes", [])
                ok = save_image_cache_with_location(self.img_path, bboxes, text, os.path.dirname(json_path))
                self.status_label.setText(f"測点（location）を割り当てました: {text}")
                self._update_location_label()
                # emitはここで行わない

def save_image_cache_with_location(image_path, bboxes, location, cache_dir=None):
    """
    bboxesとlocationを同時にキャッシュJSONへ保存
    """
    from src.utils.image_cache_utils import get_image_cache_path
    abs_image_path = os.path.abspath(image_path)
    img_cache_path = get_image_cache_path(abs_image_path, cache_dir)
    bboxes_out = [b.to_dict() if hasattr(b, 'to_dict') else b for b in bboxes]
    data = {
        "image_path": abs_image_path,
        "bboxes": bboxes_out,
        "location": location
    }
    try:
        with open(img_cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[キャッシュ保存失敗] {img_cache_path}: {e}")
        return False

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

    # 最後に開いた画像パスの保存・復元
    def load_last_image_path():
        return load_last_path(CONFIG_PATH, "last_image_path")

    def save_last_image_path(path):
        save_last_path(CONFIG_PATH, "last_image_path", path)

    app = QApplication(sys.argv)
    image_path = sys.argv[1] if len(sys.argv) > 1 else load_last_image_path() or "test.jpg"
    dlg = ImagePreviewDialog(image_path)
    save_last_image_path(image_path)
    dlg.exec()