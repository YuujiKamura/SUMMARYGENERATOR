# --- Copied from src/utils/image_utils.py ---
from PIL import Image
from PyQt6.QtGui import QImage, QPixmap
import pickle
import os
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"}

def filter_corrupt_images(image_paths):
    valid, corrupt = [], []
    for img in image_paths:
        pil_ok = True
        qt_ok = True
        try:
            with Image.open(img) as im:
                im.verify()
        except Exception:
            pil_ok = False
        qimg = QImage(img)
        if qimg.isNull():
            qt_ok = False
        if pil_ok and qt_ok:
            valid.append(img)
        else:
            corrupt.append(img)
    return valid, corrupt

def find_warn_images(image_paths):
    warn = []
    for img in image_paths:
        try:
            qpixmap = QPixmap(img)
            if qpixmap.isNull() or qpixmap.width() == 0 or qpixmap.height() == 0:
                warn.append(img)
                print(f"警告画像検出(QPixmap): {img}")
                continue
        except Exception:
            warn.append(img)
    return warn
