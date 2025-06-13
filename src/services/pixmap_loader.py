from pathlib import Path
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

class PixmapLoaderService:
    def load(self, img_path: str, fallback_size=(400, 300)) -> tuple[QPixmap, tuple[int,int]]:
        if img_path and Path(img_path).exists():
            pix = QPixmap(img_path)
            if not pix.isNull():
                return pix, (pix.width(), pix.height())
        pix = QPixmap(*fallback_size)
        pix.fill(Qt.GlobalColor.lightGray)
        return pix, fallback_size
