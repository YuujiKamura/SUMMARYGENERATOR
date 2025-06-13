# --- Copied from src/scan_for_images_widget.py ---
# widgets/配下に移動したため、importは from summarygenerator.widgets. で参照

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QProgressBar, QListWidget, QListView, QAbstractItemView, QMenu, QApplication, QStyledItemDelegate, QStyle, QToolButton, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QAbstractListModel, QModelIndex, QRect
from PyQt6.QtGui import QPixmap, QPen, QColor, QPainter
import os
import json
from pathlib import Path
from src.utils.image_utils import IMAGE_EXTENSIONS, filter_corrupt_images
from src.utils.image_cache_utils import save_image_cache, load_image_cache
from src.utils.scan_for_images_dataset import save_dataset_json
from src.utils.path_manager import path_manager

# --- FastThumbnailListModel, FastThumbnailDelegate, FastThumbnailListWidget ---
class FastThumbnailListModel(QAbstractListModel):
    def __init__(self, image_paths: list[str], thumb_size: int, bbox_dict=None, parent=None):
        super().__init__(parent)
        self.image_paths = image_paths
        self.thumb_size = thumb_size
        self._thumb_cache = {}
        self.bbox_dict = bbox_dict or {}
    def rowCount(self, parent=QModelIndex()):
        return len(self.image_paths)
    def data(self, index, role):
        if not index.isValid():
            return None
        img_path = self.image_paths[index.row()]
        if role == Qt.ItemDataRole.UserRole:
            return img_path
        if role == Qt.ItemDataRole.DecorationRole:
            if img_path in self._thumb_cache:
                return self._thumb_cache[img_path]
            pixmap = QPixmap(img_path)
            if not pixmap.isNull():
                thumb = pixmap.scaled(self.thumb_size, self.thumb_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                # --- bbox描画 ---
                dets = self.bbox_dict.get(img_path, [])
                if dets:
                    painter = QPainter(thumb)
                    pen = QPen(QColor(255, 0, 0), 3)
                    painter.setPen(pen)
                    for det in dets:
                        bbox = det.get('bbox', [])
                        if len(bbox) == 4:
                            x1, y1, x2, y2 = bbox
                            # スケール変換
                            w0, h0 = pixmap.width(), pixmap.height()
                            ws, hs = thumb.width(), thumb.height()
                            scale_x = ws / w0 if w0 else 1.0
                            scale_y = hs / h0 if h0 else 1.0
                            sx1, sy1 = int(x1 * scale_x), int(y1 * scale_y)
                            sx2, sy2 = int(x2 * scale_x), int(y2 * scale_y)
                            painter.drawRect(sx1, sy1, sx2 - sx1, sy2 - sy1)
                    painter.end()
                self._thumb_cache[img_path] = thumb
                return thumb
            return None
        return None
    def clear_cache(self):
        self._thumb_cache.clear()

class FastThumbnailDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
    def paint(self, painter, option, index):
        if painter is None:
            return
        pixmap = index.data(Qt.ItemDataRole.DecorationRole)
        rect = option.rect
        if pixmap:
            thumb_size = pixmap.size()
            x = rect.left() + (rect.width() - thumb_size.width()) // 2
            y = rect.top()
            if hasattr(painter, 'drawPixmap'):
                painter.drawPixmap(x, y, pixmap)
        if option.state & QStyle.StateFlag.State_Selected:
            pen = QPen(QColor(0, 120, 255), 3)
            if hasattr(painter, 'setPen'):
                painter.setPen(pen)
            if hasattr(painter, 'drawRect'):
                painter.drawRect(rect.adjusted(2, 2, -2, -2))
    def sizeHint(self, option, index):
        view = self.parent()
        thumb_size = getattr(view, 'thumb_size', 160)
        return QSize(thumb_size + 16, thumb_size + 36)

class FastThumbnailListWidget(QListView):
    def __init__(self, parent=None, thumb_size: int = 160):
        super().__init__(parent)
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setIconSize(QSize(thumb_size, thumb_size))
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setItemDelegate(FastThumbnailDelegate(self))
        self.thumb_size = thumb_size
        self.model_ref = None
        self.setSpacing(8)
    def set_images(self, image_paths: list[str], bbox_dict=None):
        model = FastThumbnailListModel(image_paths, self.thumb_size, bbox_dict)
        self.setModel(model)
        self.model_ref = model
    def clear_cache(self):
        if self.model_ref:
            self.model_ref.clear_cache()
    def clear(self):
        self.setModel(None)
        self.model_ref = None
    def set_thumb_size(self, size: int):
        self.thumb_size = size
        if self.model_ref:
            image_paths = self.model_ref.image_paths
            self.set_images(image_paths)

# --- ScanForImagesWidget本体 ---
class ScanForImagesWidget(QWidget):
    images_scanned = pyqtSignal(list)
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.fast_thumb_list = FastThumbnailListWidget(thumb_size=160)
        layout.addWidget(self.fast_thumb_list, 1)
        self.setLayout(layout)
        self.image_paths = []
        self.bbox_dict = {}
    def set_images(self, image_paths, bbox_dict=None):
        self.image_paths = image_paths
        self.bbox_dict = bbox_dict or {}
        self.fast_thumb_list.set_images(image_paths, self.bbox_dict)
    def get_selected_image_paths(self):
        selected_indexes = self.fast_thumb_list.selectedIndexes()
        paths = []
        for idx in selected_indexes:
            path = idx.data(Qt.ItemDataRole.UserRole)
            if path:
                paths.append(path)
        return paths
