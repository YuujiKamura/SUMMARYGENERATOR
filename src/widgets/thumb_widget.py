from PyQt6.QtCore import QThread, pyqtSignal
import hashlib
from PyQt6.QtGui import QPixmap, QImage
from src.utils.path_manager import path_manager
import os

class ThumbWorker(QThread):
    thumb_ready = pyqtSignal(int, str, str, list, list)
    def __init__(self, images, parent=None):
        super().__init__(parent)
        self.images = images
    def run(self):
        thumb_size = (180, 180)
        cache_dir = path_manager.src_dir / "image_preview_cache"
        os.makedirs(cache_dir, exist_ok=True)
        for idx, img in enumerate(self.images):
            img_path = img.get('image_path') if isinstance(img, dict) else img
            temp_img_path = None
            bbox_objs = img.get('bboxes', []) if isinstance(img, dict) else []
            roles = [bbox.get('role') for bbox in bbox_objs if bbox.get('role')]
            # キャッシュファイル名生成
            if img_path:
                h = hashlib.sha1(img_path.encode('utf-8')).hexdigest()
                cache_name = f"thumb_{h}_{thumb_size[0]}x{thumb_size[1]}.png"
                cache_path = os.path.join(cache_dir, cache_name)
            else:
                cache_path = None
            # キャッシュがあればそれを使う
            if cache_path and os.path.exists(cache_path):
                pixmap = QPixmap(cache_path)
            else:
                pixmap = QPixmap(img_path) if img_path and os.path.exists(img_path) else QPixmap()
                if not pixmap.isNull() and bbox_objs:
                    from PyQt6.QtGui import QPainter, QPen
                    from PyQt6.QtCore import Qt
                    painter = QPainter(pixmap)
                    pen = QPen(Qt.GlobalColor.red)
                    pen.setWidth(3)
                    painter.setPen(pen)
                    for bbox in bbox_objs:
                        if all(k in bbox for k in ("x", "y", "w", "h")):
                            x, y, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]
                            painter.drawRect(int(x), int(y), int(w), int(h))
                        elif all(k in bbox for k in ("xmin", "ymin", "xmax", "ymax")):
                            x, y, w, h = bbox["xmin"], bbox["ymin"], bbox["xmax"]-bbox["xmin"], bbox["ymax"]-bbox["ymin"]
                            painter.drawRect(int(x), int(y), int(w), int(h))
                    painter.end()
                # サムネイルリサイズ
                if not pixmap.isNull():
                    thumb_pixmap = pixmap.scaled(*thumb_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    thumb_pixmap.save(cache_path, "PNG")
                    pixmap = thumb_pixmap
            # emit
            self.thumb_ready.emit(idx, img_path, temp_img_path, bbox_objs, roles)
        # 最後にスレッド終了通知
        if hasattr(self, 'finished'):
            self.finished() 