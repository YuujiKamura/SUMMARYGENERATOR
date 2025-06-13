# src/utils/models.py
# YOLOアノテーション等のデータ構造クラス定義（importエラー回避用ダミーも含む）
from src.utils.bbox_utils import BoundingBox

class Annotation:
    pass

class ClassDefinition:
    pass

class AnnotationDataset:
    pass

# IMAGE_EXTENSIONS も必要ならここで定義
IMAGE_EXTENSIONS = [
    '.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp'
]