from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QMouseEvent
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal

class AnnotationViewWidget(QWidget):
    bbox_committed = pyqtSignal()  # ボックス確定時に通知
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self._orig_size = (0, 0)
        self.bboxes = []  # [{id, class_id, box, ...}]
        self.selected_idx = None
        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)
        self._drawing = False
        self._draw_start = None
        self._draw_rect = None
        self._current_class_id = 0
        self._current_class_label = None
        self._current_class_index = None

    def set_image(self, image_path):
        self._pixmap = QPixmap(image_path)
        self._orig_size = (self._pixmap.width(), self._pixmap.height())
        self.update()

    def set_bboxes(self, bboxes):
        self.bboxes = bboxes
        self.update()

    def set_current_class_id(self, class_id, class_label=None, class_index=None):
        self._current_class_id = class_id
        self._current_class_label = class_label
        self._current_class_index = class_index

    def paintEvent(self, event):
        painter = QPainter(self)
        if self._pixmap:
            painter.drawPixmap(0, 0, self._pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio))
            scale_x = self.width() / self._orig_size[0] if self._orig_size[0] else 1
            scale_y = self.height() / self._orig_size[1] if self._orig_size[1] else 1
        painter.end()
