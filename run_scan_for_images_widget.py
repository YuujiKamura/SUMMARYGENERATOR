# --- Copied from project root run_scan_for_images_widget.py ---
import sys
import os
# src配下に移動した場合のパス調整
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, 'src'))
sys.path.insert(0, project_root)

from PyQt6.QtWidgets import QApplication
from summarygenerator.widgets.scan_for_images_widget import ScanForImagesWidget
from PyQt6.QtCore import Qt, QTimer

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = ScanForImagesWidget()
    w.show()
    def set_half_maximize():
        screen = w.window().windowHandle().screen()
        if screen:
            avail_geom = screen.availableGeometry()
            half_width = avail_geom.width() // 2
            height = avail_geom.height()
            x = avail_geom.x() + half_width
            y = avail_geom.y()
            w.setGeometry(x, y, half_width, height)
    QTimer.singleShot(100, set_half_maximize)
    sys.exit(app.exec())
