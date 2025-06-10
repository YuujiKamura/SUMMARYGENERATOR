from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QListView, QAbstractItemView
from PyQt6.QtCore import QSize, pyqtSignal, Qt
from PyQt6.QtGui import QPixmap, QIcon
import os
from src.image_cache_utils import get_image_cache_path

CACHE_DIR = os.path.join(os.path.dirname(__file__), "../image_preview_cache")

class ImageListWidget(QListWidget):
    image_selected = pyqtSignal(object)
    image_double_clicked = pyqtSignal(object)
    context_menu_requested = pyqtSignal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListView.ViewMode.ListMode)
        self.setIconSize(QSize(128, 128))
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEnabled(True)
        self.currentItemChanged.connect(self._on_item_changed)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)
        self._img_entries = []

    def update_image_list(self, img_entries):
        self.clear()
        self._img_entries = img_entries
        for entry in img_entries:
            if hasattr(entry, 'is_label') and getattr(entry, 'is_label', False):
                # 区切りラベル用アイテム
                item = QListWidgetItem(entry.label)
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable & ~Qt.ItemFlag.ItemIsEnabled)
                self.addItem(item)
                continue
            icon = QIcon()
            if os.path.exists(entry.image_path):
                pixmap = QPixmap(entry.image_path)
                if not pixmap.isNull():
                    icon = QIcon(pixmap.scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            text = os.path.basename(entry.image_path)
            # 測点名（location）があれば2段表示
            location = getattr(entry, 'location', None)
            if location and location != '未設定':
                text = f"{text}\n測点: {location}"
            item = QListWidgetItem(icon, text)
            item.setData(Qt.ItemDataRole.UserRole, entry)
            self.addItem(item)

    def _on_item_changed(self, current, previous):
        if current:
            entry = current.data(Qt.ItemDataRole.UserRole)
            self.image_selected.emit(entry)

    def _on_item_double_clicked(self, item):
        entry = item.data(Qt.ItemDataRole.UserRole)
        self.image_double_clicked.emit(entry)

    def _on_context_menu(self, pos):
        items = self.selectedItems()
        if not items:
            item = self.itemAt(pos)
            if item:
                items = [item]
            else:
                items = []
        self.context_menu_requested.emit(items, pos)

    def refresh_current_items(self):
        """
        現在の画像リストを再描画（キャッシュJSONの変更を即時反映）
        """
        self.update_image_list(self._img_entries)