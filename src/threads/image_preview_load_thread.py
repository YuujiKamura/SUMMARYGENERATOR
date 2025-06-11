from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QPixmap

class ImagePreviewLoadThread(QThread):
    finished = pyqtSignal(object)
    def __init__(self, img_path, parent=None):
        super().__init__(parent)
        self.img_path = img_path
    def run(self):
        pixmap = QPixmap(self.img_path)
        self.finished.emit(pixmap) 