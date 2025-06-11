import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QTextEdit, QStatusBar, QMenuBar, QFileDialog, QAction, QComboBox
)
from PyQt6.QtCore import Qt

class SimpleSummaryWidget(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("シンプルフォトカテゴライザー")
        self.resize(900, 600)
        self._setup_menu()
        self._setup_ui()

    def _setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("ファイル")
        open_action = QAction("画像フォルダを開く", self)
        open_action.triggered.connect(self.open_folder)
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        file_menu.addAction("終了", lambda: QApplication.instance().quit())
        help_menu = menubar.addMenu("ヘルプ")
        help_menu.addAction("バージョン情報", lambda: self.statusBar().showMessage("v0.1"))

    def _setup_ui(self):
        central = QWidget(self)
        layout = QVBoxLayout(central)
        # プロジェクト選択（ダミー）
        proj_hbox = QHBoxLayout()
        proj_hbox.addWidget(QLabel("プロジェクト:"))
        self.project_combo = QComboBox()
        self.project_combo.addItem("デフォルトプロジェクト")
        proj_hbox.addWidget(self.project_combo)
        layout.addLayout(proj_hbox)
        # メイン
        main_hbox = QHBoxLayout()
        self.image_list = QListWidget()
        self.image_list.currentTextChanged.connect(self.on_image_selected)
        main_hbox.addWidget(self.image_list, 2)
        self.remarks_text = QTextEdit()
        self.remarks_text.setReadOnly(True)
        main_hbox.addWidget(self.remarks_text, 3)
        layout.addLayout(main_hbox, 1)
        # ステータスバー
        self.status = QStatusBar(self)
        self.setStatusBar(self.status)
        self.setCentralWidget(central)

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "画像フォルダを選択")
        if folder:
            self.load_images(folder)
            self.status.showMessage(f"画像フォルダ読込: {folder}")

    def load_images(self, folder):
        self.image_list.clear()
        exts = (".jpg", ".jpeg", ".png", ".bmp")
        files = [f for f in os.listdir(folder) if f.lower().endswith(exts)]
        for f in sorted(files):
            self.image_list.addItem(os.path.join(folder, f))
        self.remarks_text.clear()

    def on_image_selected(self, img_path):
        # remarksはダミー
        if img_path:
            self.remarks_text.setPlainText(f"選択画像: {os.path.basename(img_path)}\nremarks: ...")
        else:
            self.remarks_text.clear()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = SimpleSummaryWidget()
    w.show()
    sys.exit(app.exec())
