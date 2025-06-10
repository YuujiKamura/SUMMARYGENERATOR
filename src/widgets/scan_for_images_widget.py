# --- Copied from src/scan_for_images_widget.py ---
# widgets/配下に移動したため、importは from summarygenerator.widgets. で参照

from src.utils.image_utils import IMAGE_EXTENSIONS, filter_corrupt_images
from src.utils.image_cache_utils import save_image_cache, load_image_cache
from src.utils.scan_for_images_dataset import save_dataset_json
from src.utils.path_manager import path_manager
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal

class ScanForImagesWidget(QWidget):
    images_scanned = pyqtSignal(list)
    def __init__(self, parent=None):
        super().__init__(parent)
        # TODO: 必要なUIやロジックをPhotoCategorizer/src/scan_for_images_widget.pyから移植
        pass
    def set_images(self, image_paths, bbox_dict=None):
        # TODO: サムネイル＋bbox描画ロジックを実装
        pass
