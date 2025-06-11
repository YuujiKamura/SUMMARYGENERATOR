from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLabel, QMessageBox, QTextEdit, QGraphicsView, QGraphicsPixmapItem, QMenu
from src.widgets.annotation_view_widget import AnnotationViewWidget
from src.utils.last_opened_path import save_last_path, load_last_path
from src.utils.image_cache_utils import save_image_cache, load_image_cache
from src.widgets.image_display_widget import EditableImageDisplayWidget
from src.widgets.role_editor_dialog import RoleEditorDialog
from src.utils.roles_utils import group_roles_by_category
import os
import json
from src.utils.bbox_utils import BoundingBox
from PyQt6.QtGui import QPixmap, QTransform, QCursor
from PyQt6.QtCore import QRectF, pyqtSignal
from src.components.json_bbox_viewer_dialog import JsonBboxViewerDialog

class SingleLabelMakerDialog(QDialog):
    image_json_saved = pyqtSignal(str)  # 画像パスを渡す
    def __init__(self, image_path=None, class_list=None, parent=None, bboxes=None):
        super().__init__(parent)
        self.setWindowTitle("単品アノテーション追加")
        vbox = QVBoxLayout(self)
        # 最後に開いた画像パスの保存ファイル
        self._config_path = os.path.join(os.path.dirname(__file__), "single_label_maker_last.json")
        # 画像パスが未指定なら前回のパスを復元
        if image_path is None:
            image_path = load_last_path(self._config_path, "last_image_path") or ""
        # クラスリストが未指定なら空リスト
        if class_list is None:
            class_list = []
        # 既存ボックス・rolesのロード
        if bboxes is not None:
            bboxes = [BoundingBox.from_dict(b) if isinstance(b, dict) else b for b in bboxes]
        else:
            _, bboxes = load_image_cache(image_path)
            bboxes = [BoundingBox.from_dict(b) for b in bboxes] if bboxes else []
        # 重複排除
        def is_same_box(b1, b2):
            if b1.cid != b2.cid or b1.cname != b2.cname or b1.role != b2.role:
                return False
            return all(abs(a-b) < 1.0 for a, b in zip(b1.xyxy, b2.xyxy))
        unique = []
        for b in bboxes:
            if not any(is_same_box(b, u) for u in unique):
                unique.append(b)
        bboxes = unique
        self.roles = class_list
        # クラス選択
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("クラス:"))
        self.class_combo = QComboBox()
        # カテゴリーごとにグループ化して追加
        cats = group_roles_by_category(class_list)
        for cat, roles in sorted(cats.items()):
            idx = self.class_combo.count()
            self.class_combo.addItem(f"--- {cat} ---")
            self.class_combo.model().item(idx).setEnabled(False)
            for r in roles:
                self.class_combo.addItem(r["display"], r["label"])
        hbox.addWidget(self.class_combo)
        # 前回選択インデックスを復元
        last_idx = load_last_path(self._config_path, "last_class_index")
        if last_idx is not None and isinstance(last_idx, int) and 0 <= last_idx < self.class_combo.count():
            self.class_combo.setCurrentIndex(last_idx)
        # ロール編集ボタン追加
        self.role_edit_btn = QPushButton("ロール編集")
        self.role_edit_btn.clicked.connect(self.open_role_editor)
        hbox.addWidget(self.role_edit_btn)
        vbox.addLayout(hbox)
        # 画像＋bbox編集（QWidgetベースに戻す）
        self.anno_view = EditableImageDisplayWidget(self)
        self.anno_view.set_image(image_path)
        self.anno_view.set_bboxes(bboxes)
        self.anno_view.set_roles(self.roles)
        self.anno_view.set_current_class_id(self.class_combo.currentData())
        vbox.addWidget(self.anno_view, 1)
        self.anno_view.bbox_committed.connect(self.save_current_bboxes)
        self.anno_view.box_right_clicked.connect(self.on_box_right_clicked)
        # 画像サイズにウィンドウをフィット（表示倍率を考慮）
        if self.anno_view._pixmap and self.anno_view._pixmap.width() > 0 and self.anno_view._pixmap.height() > 0:
            w, h = int(self.anno_view._pixmap.width()), int(self.anno_view._pixmap.height())
            screen = self.screen()
            if screen:
                screen_size = screen.size()
                max_w = int(screen_size.width() * 0.8)
                max_h = int(screen_size.height() * 0.8)
                scale = min(max_w / w, max_h / h, 1.0)
                disp_w = int(w * scale)
                disp_h = int(h * scale)
                self.anno_view._zoom_scale = scale
                self.anno_view.setFixedSize(disp_w, disp_h)
                self.layout().setContentsMargins(4, 4, 4, 4)
                self.layout().setSpacing(4)
                self.resize(disp_w + 16, disp_h + 80)
        # ボタン
        btn_hbox = QHBoxLayout()
        ok_btn = QPushButton("JSON保存して閉じる")
        cancel_btn = QPushButton("キャンセル")
        btn_hbox.addWidget(ok_btn)
        btn_hbox.addWidget(cancel_btn)
        vbox.addLayout(btn_hbox)
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        self.class_combo.currentIndexChanged.connect(self._on_class_changed)
        self._image_path = image_path
        # JSON確認ボタン追加
        self.show_json_btn = QPushButton("JSON確認")
        self.show_json_btn.clicked.connect(self.show_current_json)
        vbox.addWidget(self.show_json_btn)
        # ステータスバー追加
        self.status_bar = QLabel()
        hint = "画像上で: 左ダブルクリック=追加/確定, 右クリック=キャンセル, 左クリック=選択, 右クリック=削除"
        self.status_bar.setText(hint)
        vbox.addWidget(self.status_bar)
        # EditableImageDisplayWidgetのマウスイベント用シグナル接続
        self.anno_view.mouse_hint_changed.connect(self.status_bar.setText)
    def _on_class_changed(self, idx):
        self.anno_view.set_current_class_id(self.class_combo.currentData(), self.class_combo.currentText(), self.class_combo.currentIndex())
        self.anno_view.set_roles(self.roles)
        # 選択インデックスを保存
        save_last_path(self._config_path, "last_class_index", idx)
    def get_bboxes(self):
        # BoundingBoxリストをdictに変換して返す（従来互換）
        return [b.to_dict() if hasattr(b, 'to_dict') else b for b in self.anno_view.bboxes]
    def accept(self):
        # OK時に画像パスを保存
        save_last_path(self._config_path, "last_image_path", self._image_path)
        # 現在のボックスをキャッシュ保存（重複防止のためsave_current_bboxesのみ呼ぶ）
        self.save_current_bboxes()
        self.image_json_saved.emit(self._image_path)
        super().accept()
    def open_role_editor(self):
        dlg = RoleEditorDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # 編集後にクラスリストを再読込して反映
            preset_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'preset_roles.json'))
            try:
                with open(preset_path, 'r', encoding='utf-8') as f:
                    class_list = json.load(f)
            except Exception as e:
                QMessageBox.warning(self, "エラー", f"クラスリストの読込に失敗しました: {e}")
                return
            self.class_combo.clear()
            for c in class_list:
                self.class_combo.addItem(c["display"], c["label"])
            self.roles = class_list
            self.anno_view.set_roles(self.roles)
    def save_current_bboxes(self):
        # UI上のbboxリストをすべてdict化して保存
        bboxes = [b.to_dict() if hasattr(b, 'to_dict') else b for b in self.anno_view.bboxes]
        save_image_cache(self._image_path, bboxes)
    def show_current_json(self):
        # ここで最新のbboxesをキャッシュに保存
        self.save_current_bboxes()
        cache_path = os.path.join(os.path.dirname(__file__), "image_preview_cache")
        import hashlib
        h = hashlib.sha1(self._image_path.encode("utf-8")).hexdigest()
        json_path = os.path.join(cache_path, f"{h}.json")
        dlg = JsonBboxViewerDialog(self._image_path, json_path, self)
        dlg.exec()
    def on_box_right_clicked(self, indices):
        if not indices:
            return
        menu = QMenu(self)
        delete_action = menu.addAction("選択ボックスを削除")
        selected_action = menu.exec(self.anno_view.mapToGlobal(self.anno_view.mapFromGlobal(QCursor.pos())))
        if selected_action == delete_action:
            # インデックス降順で削除（indexズレ防止）
            for idx in sorted(indices, reverse=True):
                if 0 <= idx < len(self.anno_view.bboxes):
                    del self.anno_view.bboxes[idx]
            self.anno_view.selected_indices = []
            self.anno_view.update()
            self.save_current_bboxes()
            if hasattr(self.anno_view, 'bbox_committed'):
                self.anno_view.bbox_committed.emit()

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    from utils.last_opened_path import load_last_path, save_last_path

    CONFIG_PATH = os.path.join(os.path.dirname(__file__), "single_label_maker_last.json")
    def load_last_image_path():
        return load_last_path(CONFIG_PATH, "last_image_path")
    def save_last_image_path(path):
        save_last_path(CONFIG_PATH, "last_image_path", path)

    app = QApplication(sys.argv)
    image_path = sys.argv[1] if len(sys.argv) > 1 else load_last_image_path() or ""
    # rolesのロードも必要ならここで
    preset_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'preset_roles.json'))
    try:
        with open(preset_path, 'r', encoding='utf-8') as f:
            class_list = json.load(f)
    except Exception:
        class_list = []
    dlg = SingleLabelMakerDialog(image_path, class_list)
    if dlg.exec() == QDialog.DialogCode.Accepted:
        save_last_image_path(image_path)