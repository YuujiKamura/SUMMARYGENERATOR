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
            for idx, bbox in enumerate(self.bboxes):
                color = QColor(0, 200, 255) if idx == self.selected_idx else QColor(0, 200, 0)
                pen = QPen(color, 2)
                painter.setPen(pen)
                coords = bbox.get('box') or bbox.get('xyxy')
                if coords:
                    x1, y1, x2, y2 = coords
                    painter.drawRect(int(x1*scale_x), int(y1*scale_y), int((x2-x1)*scale_x), int((y2-y1)*scale_y))
            # 描画中の矩形
            if self._drawing and self._draw_rect:
                painter.setPen(QPen(QColor(255,0,0), 2, Qt.PenStyle.DashLine))
                painter.drawRect(self._draw_rect)
        else:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No Image")
        painter.end()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self._pixmap:
            self._drawing = True
            self._draw_start = event.position()
            self._draw_rect = QRectF(self._draw_start, self._draw_start)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drawing and self._draw_start:
            end = event.position()
            self._draw_rect = QRectF(self._draw_start, end).normalized()
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._drawing and self._draw_rect:
            # bbox追加
            scale_x = self._orig_size[0] / self.width() if self.width() else 1
            scale_y = self._orig_size[1] / self.height() if self.height() else 1
            rect = self._draw_rect
            x1 = rect.left() * scale_x
            y1 = rect.top() * scale_y
            x2 = rect.right() * scale_x
            y2 = rect.bottom() * scale_y
            if abs(x2-x1) > 5 and abs(y2-y1) > 5:
                # YOLO標準形式で保存
                cid = getattr(self, '_current_class_index', 0) or 0
                cname = getattr(self, '_current_class_label', None) or ''
                conf = 1.0
                role = getattr(self, '_current_class_id', None)
                self.bboxes.append({'cid': cid, 'cname': cname, 'conf': conf, 'xyxy': [x1, y1, x2, y2], 'role': role})
                self.bbox_committed.emit()  # 追加時に通知
            self._drawing = False
            self._draw_start = None
            self._draw_rect = None
            self.update()
        super().mouseReleaseEvent(event) 