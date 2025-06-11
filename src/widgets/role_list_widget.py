import os
import json
from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QVBoxLayout, QPushButton, QWidget
from PyQt6.QtCore import Qt

class RoleListWidget(QWidget):
    def __init__(self, preset_file=None, parent=None, save_dir="seeds"):
        super().__init__(parent)
        if preset_file is None:
            preset_file = os.path.join(os.path.dirname(__file__), '../preset_roles.json')
        self.preset_file = os.path.abspath(preset_file)
        self.save_dir = save_dir
        layout = QVBoxLayout(self)
        self.reload_btn = QPushButton("リロード")
        self.reload_btn.clicked.connect(self.reload_roles)
        layout.addWidget(self.reload_btn)
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list_widget.setMinimumWidth(220)
        layout.addWidget(self.list_widget, 1)
        self.roles = []
        self.reload_roles()
        # 親ウィンドウのステータスバーにスクリプト名を表示
        mainwin = self.window()
        if hasattr(mainwin, 'set_current_widget_name'):
            mainwin.set_current_widget_name("role_list_widget.py")

    def reload_roles(self):
        self.list_widget.clear()
        try:
            with open(self.preset_file, 'r', encoding='utf-8') as f:
                self.roles = json.load(f)
            for role in self.roles:
                item = QListWidgetItem(role['display'])
                item.setData(Qt.ItemDataRole.UserRole, role['label'])
                self.list_widget.addItem(item)
        except Exception as e:
            self.list_widget.addItem(f"ロール読込エラー: {e}")
        self.update_entry_counts()

    def update_entry_counts(self):
        for i, role in enumerate(self.roles):
            label = role['label']
            display = role['display']
            json_path = os.path.join(self.save_dir, f"{label}.json")
            count = 0
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    count = len(data.get('images', []))
                except Exception:
                    count = 0
            text = f"{display} ({count}件)"
            item = self.list_widget.item(i)
            if item:
                item.setText(text)

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    import traceback

    try:
        app = QApplication(sys.argv)
        global widget
        widget = RoleListWidget()
        widget.show()
        sys.exit(app.exec())
    except Exception as e:
        print("例外発生:", e)
        traceback.print_exc()
        input("何かキーを押してください") 