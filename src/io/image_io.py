"""
画像I/O（日本語パス対応imread等）
"""
import cv2
import shutil
import string
import random
import re
from pathlib import Path

def safe_imread_with_temp(src_path):
    src_path = str(src_path)
    if re.search(r'[^\x00-\x7F]', src_path):
        temp_dir = Path('C:/temp_yolo_images')
        temp_dir.mkdir(parents=True, exist_ok=True)
        ext = Path(src_path).suffix
        randname = ''.join(random.choices(string.ascii_letters + string.digits, k=16)) + ext
        temp_path = temp_dir / randname
        try:
            shutil.copy2(src_path, temp_path)
            img = cv2.imread(str(temp_path))
            temp_path.unlink(missing_ok=True)
            return img
        except Exception as e:
            print(f'[警告] テンポラリコピー失敗: {src_path} → {temp_path} ({e})')
            return None
    else:
        return cv2.imread(src_path)
