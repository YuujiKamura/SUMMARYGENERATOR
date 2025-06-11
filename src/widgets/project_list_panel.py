from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QLabel, QTextEdit, QHBoxLayout
import os
import json

class ProjectListPanel(QWidget):
    def __init__(self, managed_base_dir, parent=None):
        super().__init__(parent)
        self.managed_base_dir = managed_base_dir
        layout = QHBoxLayout(self)
        # 左: プロジェクトリスト
        vbox_left = QVBoxLayout()
        self.list_widget = QListWidget(self)
        vbox_left.addWidget(self.list_widget)
        layout.addLayout(vbox_left, 1)
        # 右: 詳細表示
        vbox_right = QVBoxLayout()
        self.detail_label = QLabel("プロジェクト詳細")
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        vbox_right.addWidget(self.detail_label)
        vbox_right.addWidget(self.detail_text)
        layout.addLayout(vbox_right, 2)
        self.setLayout(layout)
        self.refresh_list()
        self.list_widget.currentRowChanged.connect(self.show_detail)

    def refresh_list(self):
        self.project_info = []  # (表示名, json_path, data)
        # managed_files直下
        for d in os.listdir(self.managed_base_dir):
            full_path = os.path.join(self.managed_base_dir, d)
            if d.endswith('.json'):
                try:
                    with open(full_path, encoding='utf-8') as f:
                        data = json.load(f)
                    name = data.get('project_name', d)
                    image_dir = data.get('image_dir', '')
                    desc = data.get('description', '')
                    display = f"{name}（{image_dir}）"
                    self.project_info.append((display, full_path, data))
                except Exception:
                    continue
        # current/配下のjsonも追加
        current_dir = os.path.join(self.managed_base_dir, "current")
        if os.path.isdir(current_dir):
            for d in os.listdir(current_dir):
                if d.endswith('.json'):
                    full_path = os.path.join(current_dir, d)
                    try:
                        with open(full_path, encoding='utf-8') as f:
                            data = json.load(f)
                        name = data.get('project_name', d)
                        image_dir = data.get('image_dir', '')
                        desc = data.get('description', '')
                        display = f"{name}（{image_dir}）"
                        self.project_info.append((display, full_path, data))
                    except Exception:
                        continue
        self.list_widget.clear()
        self.list_widget.addItems([x[0] for x in self.project_info])
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
            self.list_widget.setFocus()

    def show_detail(self, row):
        if row < 0 or row >= len(self.project_info):
            self.detail_text.clear()
            return
        display, json_path, data = self.project_info[row]
        lines = [
            f"パス: {json_path}",
            f"project_name: {data.get('project_name', '')}",
            f"image_dir: {data.get('image_dir', '')}",
            f"image_list_json: {data.get('image_list_json', '')}",
            f"type: {data.get('type', '')}",
            f"created_at: {data.get('created_at', '')}",
            f"description: {data.get('description', '')}",
        ]
        self.detail_text.setPlainText('\n'.join(lines))

    def get_selected_projects(self):
        rows = [i.row() for i in self.list_widget.selectedIndexes()]
        return [self.project_info[r][1] for r in rows if 0 <= r < len(self.project_info)]
