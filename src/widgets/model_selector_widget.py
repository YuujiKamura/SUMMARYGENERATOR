from PyQt6.QtWidgets import QWidget, QHBoxLayout, QComboBox, QLabel
from PyQt6.QtCore import pyqtSignal
from pathlib import Path
from src.utils.model_manager import ModelManager
import os

class ModelSelectorWidget(QWidget):
    model_changed = pyqtSignal(str)  # 選択モデルパスを通知

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        self.combo = QComboBox(self)
        self.model_manager = ModelManager()
        self.model_path_map = []  # (表示名, パス)
        for cat in self.model_manager.categories():
            for path, info in self.model_manager.entries(cat):
                display = self._make_display_name(cat, path, info)
                self.combo.addItem(display, path)
                self.model_path_map.append((display, path))
        self.combo.currentIndexChanged.connect(self._on_index_changed)
        layout.addWidget(QLabel("モデル選択: "))
        layout.addWidget(self.combo)
        layout.addStretch(1)
        self.setLayout(layout)

    def _make_display_name(self, cat, path, info):
        # dataset直下のディレクトリ名を取得
        p = Path(path)
        # 例: .../datasets/xxxx/weights/best.pt → xxxx
        dataset_dir = None
        for parent in p.parents:
            if parent.name == "datasets":
                idx = p.parents.index(parent)
                if idx > 0:
                    dataset_dir = p.parents[idx-1].name
                break
        # fallback: runs/train/xxxx/weights/best.pt → xxxx
        if not dataset_dir:
            for parent in p.parents:
                if parent.name == "train":
                    idx = p.parents.index(parent)
                    if idx > 0:
                        dataset_dir = p.parents[idx-1].name
                    break
        # fallback: さらに一つ上
        if not dataset_dir and len(p.parents) > 2:
            dataset_dir = p.parents[2].name

        if cat == "優先モデル":
            return f"[{cat}] {info.get('name', p.name)} ({dataset_dir or '?'})"
        elif cat == "トレーニング済みモデル":
            exp = info.get('experiment') or dataset_dir or p.parent.parent.name
            return f"[{cat}] {info.get('name', p.name)} ({exp})"
        else:
            return f"[{cat}] {info.get('name', p.name)}"

    def _on_index_changed(self, idx):
        if 0 <= idx < len(self.model_path_map):
            path = self.model_path_map[idx][1]
            self.model_changed.emit(path)

    def get_selected_model_path(self):
        idx = self.combo.currentIndex()
        if 0 <= idx < len(self.model_path_map):
            return self.model_path_map[idx][1]
        return None

    def set_selected_model_path(self, path):
        for i, (_, p) in enumerate(self.model_path_map):
            if p == path:
                self.combo.setCurrentIndex(i)
                break
