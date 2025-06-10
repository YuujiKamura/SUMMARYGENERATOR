from PyQt6.QtWidgets import QWidget, QLabel, QMenu, QListWidget, QWidgetAction, QTreeWidget, QTreeWidgetItem
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QMouseEvent, QWheelEvent
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QRectF
from utils.bbox_utils import BoundingBox
from utils.image_cache_utils import save_image_cache
from typing import List

# --- Copied from src/image_display_widget.py ---
# widgets/配下に移動したため、importは from summarygenerator.widgets. で参照

class ImageDisplayWidget(QWidget):
    # シグナル定義
    mousePressed = pyqtSignal(QMouseEvent)
    mouseReleased = pyqtSignal(QMouseEvent)
    mouseMoved = pyqtSignal(QMouseEvent)
    wheelMoved = pyqtSignal(QWheelEvent)

    def __init__(self, parent=None):
        super().__init__(parent)
        # 画像表示用ラベル
        self.imageLabel = QLabel(self)
        # 画像キャッシュ
        self.imageCache = {}
        # バウンディングボックス
        self.boundingBoxes = []
        # 初期設定
        self.initUI()

    def initUI(self):
        # レイアウト設定
        self.setGeometry(100, 100, 800, 600)
        # 画像ラベル設定
        self.imageLabel.setGeometry(QRectF(0, 0, self.width(), self.height()))
        # シグナルとスロットの接続
        self.imageLabel.mousePressEvent = self.onMousePress
        self.imageLabel.mouseReleaseEvent = self.onMouseRelease
        self.imageLabel.mouseMoveEvent = self.onMouseMove
        self.imageLabel.wheelEvent = self.onWheel

    def onMousePress(self, event: QMouseEvent):
        # マウス押下時の処理
        self.mousePressed.emit(event)

    def onMouseRelease(self, event: QMouseEvent):
        # マウス離上時の処理
        self.mouseReleased.emit(event)

    def onMouseMove(self, event: QMouseEvent):
        # マウス移動時の処理
        self.mouseMoved.emit(event)

    def onWheel(self, event: QWheelEvent):
        # ホイール操作時の処理
        self.wheelMoved.emit(event)

    def loadImage(self, filePath: str):
        # 画像読み込み
        if filePath in self.imageCache:
            pixmap = self.imageCache[filePath]
        else:
            pixmap = QPixmap(filePath)
            if not pixmap.isNull():
                self.imageCache[filePath] = pixmap
        self.imageLabel.setPixmap(pixmap)

    def clearImage(self):
        # 画像クリア
        self.imageLabel.clear()
        self.imageCache.clear()

    def addBoundingBox(self, bbox: BoundingBox):
        # バウンディングボックス追加
        self.boundingBoxes.append(bbox)
        self.update()

    def clearBoundingBoxes(self):
        # バウンディングボックスクリア
        self.boundingBoxes.clear()
        self.update()

    def paintEvent(self, event):
        # 描画イベント
        painter = QPainter(self.imageLabel.pixmap())
        pen = QPen(QColor(255, 0, 0))
        pen.setWidth(2)
        painter.setPen(pen)
        for bbox in self.boundingBoxes:
            painter.drawRect(bbox.x, bbox.y, bbox.width, bbox.height)
        super().paintEvent(event)

    def resizeEvent(self, event):
        # リサイズイベント
        self.imageLabel.setGeometry(QRectF(0, 0, self.width(), self.height()))
        super().resizeEvent(event)
