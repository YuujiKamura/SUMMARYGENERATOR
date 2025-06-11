from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QLineEdit, QFileDialog
import os
import json

class ImageListControlPanel(QWidget):
    def __init__(self, config_path, image_cache_dir_config, default_json_path, default_folder_path, parent=None):
        super().__init__(parent)
        self.config_path = config_path
        self.image_cache_dir_config = image_cache_dir_config
        self.hbox = QHBoxLayout(self)
        # 画像リストJSON
        self.hbox.addWidget(QLabel("画像リストJSON:"))
        self.json_path_edit = QLineEdit(default_json_path)
        self.hbox.addWidget(self.json_path_edit)
        self.json_browse_btn = QPushButton("参照")
        self.hbox.addWidget(self.json_browse_btn)
        # 画像リスト再読込ボタン
        self.reload_btn = QPushButton("画像リスト再読込")
        self.hbox.addWidget(self.reload_btn)
        # 画像フォルダ
        self.hbox.addWidget(QLabel("画像フォルダ:"))
        self.folder_path_edit = QLineEdit(default_folder_path)
        self.hbox.addWidget(self.folder_path_edit)
        self.folder_browse_btn = QPushButton("参照")
        self.hbox.addWidget(self.folder_browse_btn)
        self.folder_open_btn = QPushButton("フォルダを開く")
        self.hbox.addWidget(self.folder_open_btn)
        # ボタンの挙動
        self.json_browse_btn.clicked.connect(self.browse_json)
        self.folder_browse_btn.clicked.connect(self.browse_folder)
        self.folder_open_btn.clicked.connect(self.open_folder)
    def browse_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "画像リストJSONを選択", self.json_path_edit.text(), "JSON Files (*.json)")
        if path:
            self.json_path_edit.setText(path)
            try:
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump({"last_json_path": os.path.abspath(path)}, f)
            except Exception:
                pass
    def browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "画像フォルダを選択", self.folder_path_edit.text())
        if path:
            self.folder_path_edit.setText(path)
            try:
                with open(self.image_cache_dir_config, "w", encoding="utf-8") as f:
                    json.dump({"image_cache_dir": path}, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
    def open_folder(self):
        folder = self.folder_path_edit.text()
        if folder and os.path.exists(folder):
            import subprocess
            import sys
            if sys.platform.startswith('win'):
                os.startfile(folder)
            elif sys.platform.startswith('darwin'):
                subprocess.Popen(['open', folder])
            else:
                subprocess.Popen(['xdg-open', folder])
