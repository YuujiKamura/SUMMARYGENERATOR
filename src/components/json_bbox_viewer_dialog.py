from QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QListWidgetItem, QTextEdit, QTabWidget, QMessageBox
from QtCore import pyqtSignal
import os
import json

class JsonBboxViewerDialog(QDialog):
    image_json_saved = pyqtSignal(str)  # 画像パスを渡す
    def __init__(self, image_path, cache_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("JSON内容確認・編集")
        self.image_path = image_path
        self.cache_path = cache_path
        vbox = QVBoxLayout(self)
        self.tabs = QTabWidget()
        # --- 生データタブ ---
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.tabs.addTab(self.text_edit, "生データ")
        # --- リスト削除タブ ---
        self.bbox_list = QListWidget()
        self.bbox_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.tabs.addTab(self.bbox_list, "エントリー削除")
        vbox.addWidget(self.tabs)
        # --- ボタン ---
        btn_hbox = QHBoxLayout()
        self.del_btn = QPushButton("選択行を削除")
        self.close_btn = QPushButton("閉じる")
        btn_hbox.addWidget(self.del_btn)
        btn_hbox.addWidget(self.close_btn)
        vbox.addLayout(btn_hbox)
        self.del_btn.clicked.connect(self.delete_selected)
        self.close_btn.clicked.connect(self.accept)
        self.reload()
        self.resize(700, 500)
        self._modified = False
    def reload(self):
        # 生データ
        try:
            with open(self.cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            text = json.dumps(data, ensure_ascii=False, indent=2)
        except Exception as e:
            text = f"ファイル読込エラー: {e}"
            data = {}
        self.text_edit.setText(text)
        # bboxリスト
        self.bbox_list.clear()
        bboxes = data.get("bboxes", []) if isinstance(data, dict) else []
        for i, b in enumerate(bboxes):
            item = QListWidgetItem(f"[{i}] {b.get('cname', '')} {b.get('role', '')} {b.get('xyxy', '')}")
            self.bbox_list.addItem(item)
    def delete_selected(self):
        selected = self.bbox_list.selectedIndexes()
        if not selected:
            QMessageBox.information(self, "削除", "削除する行を選択してください")
            return
        try:
            with open(self.cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            bboxes = data.get("bboxes", [])
            idxs = sorted([s.row() for s in selected], reverse=True)
            for idx in idxs:
                if 0 <= idx < len(bboxes):
                    del bboxes[idx]
            data["bboxes"] = bboxes
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._modified = True
            self.image_json_saved.emit(self.image_path)
        except Exception as e:
            QMessageBox.warning(self, "保存エラー", str(e))
            return
        self.reload()
    def accept(self):
        if self._modified:
            self.image_json_saved.emit(self.image_path)
        super().accept()
