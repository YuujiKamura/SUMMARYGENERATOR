import os
from pathlib import Path
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox,
    QListWidget, QListWidgetItem, QFileDialog, QMessageBox, QTextEdit
)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt
from ultralytics import YOLO
from src.utils.path_manager import path_manager
from src.utils.model_selector import get_available_models

class ModelTestWidget(QDialog):
    """YOLOモデルで画像群を一括推論し、サムネイル＋ラベル結果を一覧表示するウィジェット"""
    def __init__(self, parent: Optional[QDialog] = None):
        super().__init__(parent)
        self.setWindowTitle("YOLOモデル推論テスト")
        self.resize(1000, 700)
        self._setup_ui()
        from ultralytics import YOLO
        self._YOLO = YOLO

    def _setup_ui(self) -> None:
        vbox = QVBoxLayout(self)
        # モデル選択
        hbox_model = QHBoxLayout()
        hbox_model.addWidget(QLabel("モデル:"))
        self.model_combo = QComboBox()
        self.refresh_model_combo()
        hbox_model.addWidget(self.model_combo)
        self.reload_model_btn = QPushButton("モデルリスト再読込")
        hbox_model.addWidget(self.reload_model_btn)
        vbox.addLayout(hbox_model)
        # クラス一覧表示欄
        self.class_names_edit = QTextEdit()
        self.class_names_edit.setReadOnly(True)
        self.class_names_edit.setPlaceholderText("モデル内クラス一覧")
        vbox.addWidget(self.class_names_edit)
        # 画像フォルダ選択
        hbox_img = QHBoxLayout()
        hbox_img.addWidget(QLabel("画像フォルダ:"))
        self.img_dir_edit = QLineEdit()
        hbox_img.addWidget(self.img_dir_edit)
        self.img_dir_btn = QPushButton("参照")
        hbox_img.addWidget(self.img_dir_btn)
        vbox.addLayout(hbox_img)
        # 推論実行ボタン
        self.run_btn = QPushButton("推論実行")
        vbox.addWidget(self.run_btn)
        # サムネイル＋ラベル結果リスト
        self.result_list = QListWidget()
        vbox.addWidget(self.result_list)
        # シグナル
        self.img_dir_btn.clicked.connect(self.select_img_dir)
        self.run_btn.clicked.connect(self.run_inference)
        self.result_list.itemDoubleClicked.connect(self.show_image_preview)
        self.reload_model_btn.clicked.connect(self.refresh_model_combo)
        self.model_combo.currentIndexChanged.connect(self.update_class_names)

    def refresh_model_combo(self) -> None:
        self.model_combo.clear()
        for name, path in get_available_models():
            self.model_combo.addItem(name, path)

    def select_img_dir(self) -> None:
        dir_path = QFileDialog.getExistingDirectory(self, "画像フォルダを選択")
        if dir_path:
            self.img_dir_edit.setText(dir_path)

    def run_inference(self) -> None:
        img_dir = self.img_dir_edit.text()
        model_idx = self.model_combo.currentIndex()
        model_path = self.model_combo.itemData(model_idx) if model_idx >= 0 else None
        if not img_dir or not os.path.exists(img_dir):
            QMessageBox.warning(self, "エラー", "画像フォルダが存在しません")
            return
        if not model_path or not os.path.exists(model_path):
            QMessageBox.warning(self, "エラー", "モデルファイルが存在しません")
            return
        model = self._YOLO(model_path)
        # 画像ファイルを再帰的に収集
        exts = [".jpg", ".jpeg", ".png", ".bmp"]
        img_files = [
            str(p) for p in Path(img_dir).rglob("*") if p.suffix.lower() in exts
        ]
        if not img_files:
            QMessageBox.warning(self, "エラー", "画像ファイルが見つかりません")
            return
        self.result_list.clear()
        # 一括推論
        for img_path in img_files:
            try:
                results = model(img_path)
                boxes = results[0].boxes
                names = results[0].names if hasattr(results[0], 'names') else []
                if boxes and len(boxes) > 0:
                    label = ", ".join([
                        names[int(cls)] if names and int(cls) < len(names) else str(cls)
                        for cls in boxes.cls
                    ])
                    status = "OK"
                else:
                    label = "(検出なし)"
                    status = "NG"
                # サムネイル生成
                pixmap = QPixmap(img_path).scaled(
                    96, 96, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                item = QListWidgetItem(
                    QIcon(pixmap), f"{os.path.basename(img_path)} | {status} | {label}"
                )
                item.setData(Qt.ItemDataRole.UserRole, img_path)
                self.result_list.addItem(item)
            except (OSError, ValueError) as e:
                item = QListWidgetItem(
                    f"{os.path.basename(img_path)} | [ERROR] {e}"
                )
                item.setData(Qt.ItemDataRole.UserRole, img_path)
                self.result_list.addItem(item)

    def show_image_preview(self, item: QListWidgetItem) -> None:
        img_path = item.data(Qt.ItemDataRole.UserRole)
        if not img_path or not os.path.exists(img_path):
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(os.path.basename(img_path))
        vbox = QVBoxLayout(dlg)
        pixmap = QPixmap(img_path).scaled(
            512, 512, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        vbox.addWidget(QLabel(os.path.basename(img_path)))
        lbl = QLabel()
        lbl.setPixmap(pixmap)
        vbox.addWidget(lbl)
        btn = QPushButton("閉じる", dlg)
        btn.clicked.connect(dlg.accept)
        vbox.addWidget(btn)
        dlg.setLayout(vbox)
        dlg.exec()

    def update_class_names(self):
        model_idx = self.model_combo.currentIndex()
        model_path = self.model_combo.itemData(model_idx) if model_idx >= 0 else None
        if not model_path or not os.path.exists(model_path):
            self.class_names_edit.setPlainText("")
            return
        try:
            model = self._YOLO(model_path)
            names = getattr(model, "names", None)
            if isinstance(names, dict):
                class_list = [f"{k}: {v}" for k, v in names.items()]
            elif isinstance(names, list):
                class_list = [f"{i}: {v}" for i, v in enumerate(names)]
            else:
                class_list = [str(names)] if names else []
            self.class_names_edit.setPlainText("\n".join(class_list))
        except Exception as e:
            self.class_names_edit.setPlainText(f"[ERROR] {e}")

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    dlg = ModelTestWidget()
    dlg.show()
    sys.exit(app.exec()) 