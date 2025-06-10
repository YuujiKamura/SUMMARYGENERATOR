import sys
from PyQt6.QtWidgets import QApplication, QListWidget, QListWidgetItem, QMainWindow
from PyQt6.QtGui import QIcon, QPixmap
import os

class ThumbListWindow(QMainWindow):
    def __init__(self, image_paths):
        super().__init__()
        self.setWindowTitle('QListWidget Thumbnail Sample')
        self.resize(800, 600)
        self.list_widget = QListWidget(self)
        self.setCentralWidget(self.list_widget)
        for img_path in image_paths:
            if not os.path.exists(img_path):
                continue
            pixmap = QPixmap(img_path)
            if pixmap.isNull():
                continue
            icon = QIcon(pixmap)
            item = QListWidgetItem(icon, os.path.basename(img_path))
            self.list_widget.addItem(item)

if __name__ == '__main__':
    # テスト用画像パスを適宜指定
    image_paths = [
        r'H:/マイドライブ/過去の現場_元請/2023.03.23 東区市道（５工区）舗装補修工事（水防等含）（単価契約）/9 工事写真/７～９月/0726 湖東２丁目/温度管理/RIMG4768.JPG',
        r'H:/マイドライブ/過去の現場_元請/2023.03.23 東区市道（５工区）舗装補修工事（水防等含）（単価契約）/9 工事写真/７～９月/0726 湖東２丁目/出来形/RIMG4742.JPG',
    ]
    app = QApplication(sys.argv)
    win = ThumbListWindow(image_paths)
    win.show()
    sys.exit(app.exec()) 