import os
import json
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QColor
from src.utils.image_cache_utils import load_image_cache
from src.utils.path_manager import path_manager

class ImagePreviewDataLoadThread(QThread):
    finished = pyqtSignal(object, object, list, list)
    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path
    def run(self):
        print(f"[DEBUG IPDLT] Loading image from: {self.image_path}")
        pixmap = QPixmap()
        if os.path.exists(self.image_path):
            print(f"[DEBUG IPDLT] 画像ファイルは存在しています: {self.image_path}")
            load_methods = [
                lambda: QPixmap(self.image_path),
                lambda: QPixmap(str(Path(self.image_path))),
                lambda: QPixmap(os.fsdecode(self.image_path)),
                lambda: QPixmap(os.path.abspath(self.image_path)),
                lambda: QPixmap(os.path.relpath(self.image_path))
            ]
            for i, load_method in enumerate(load_methods):
                try:
                    temp_pixmap = load_method()
                    if not temp_pixmap.isNull():
                        pixmap = temp_pixmap
                        print(f"[DEBUG IPDLT] 方法{i+1}で成功: サイズ {pixmap.width()}x{pixmap.height()}")
                        break
                    else:
                        print(f"[DEBUG IPDLT] 方法{i+1}は失敗 (Null pixmap)")
                except Exception as e:
                    print(f"[DEBUG IPDLT] 方法{i+1}でエラー: {e}")
        if pixmap.isNull():
            print(f"[DEBUG IPDLT] 全ての読み込み方法を試しましたが、画像を読み込めませんでした: {self.image_path}")
            error_pixmap = QPixmap(400, 300)
            error_pixmap.fill(QColor(240, 240, 240))
            painter = QPainter(error_pixmap)
            painter.setPen(QColor(255, 0, 0))
            painter.drawText(error_pixmap.rect(), 0x84, "画像読み込みエラー")
            painter.end()
            pixmap = error_pixmap
        else:
            print(f"[DEBUG IPDLT] 画像読み込み成功: {self.image_path}, サイズ: {pixmap.width()}x{pixmap.height()}")
        _, bboxes = load_image_cache(self.image_path)
        preset_path = str(path_manager.preset_roles)
        try:
            with open(preset_path, 'r', encoding='utf-8') as f:
                roles = json.load(f)
        except Exception as e:
            print(f"[WARNING] ロール定義読み込みエラー: {e}")
            roles = []
        self.finished.emit(pixmap, bboxes, roles, [])
