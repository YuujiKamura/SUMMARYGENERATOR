# DetectResultWidget: YOLO推論結果をサムネイル＋bbox＋ラベルで表示するウィジェット
# PhotoCategorizer/src/widgets/detect_result_widget.py からコピー
# 必要に応じて依存パス等は後で修正

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt
from .scan_for_images_widget import ScanForImagesWidget

class DetectResultWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("推論結果一覧")
        layout = QHBoxLayout(self)
        vbox = QVBoxLayout()
        vbox.addWidget(QLabel("検出画像一覧"))
        self.image_widget = ScanForImagesWidget()
        vbox.addWidget(self.image_widget, 1)
        layout.addLayout(vbox, 1)
        self.setLayout(layout)
        self.image_paths = []
        self.bbox_dict = {}

    def set_images(self, image_paths, bbox_dict=None):
        self.image_paths = image_paths
        self.bbox_dict = bbox_dict or {}
        self.image_widget.set_images(image_paths, self.bbox_dict)
