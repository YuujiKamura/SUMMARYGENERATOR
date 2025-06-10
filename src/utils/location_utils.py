# --- Copied from src/utils/location_utils.py ---
import json
import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QDialogButtonBox
from .path_manager import path_manager

LOCATION_HISTORY_PATH = str(path_manager.src_dir / "location_history.json")

def load_location_history():
    try:
        with open(LOCATION_HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_location_history(history):
    try:
        with open(LOCATION_HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

class LocationInputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("測点名入力")
        vbox = QVBoxLayout(self)
        vbox.addWidget(QLabel("測点（location）を入力または選択してください："))
        self.combo = QComboBox(self)
        self.combo.setEditable(True)
        history = load_location_history()
        self.combo.addItems(history)
        vbox.addWidget(self.combo)
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        vbox.addWidget(btn_box)
    def get_text(self):
        return self.combo.currentText().strip()
