import sys
from pathlib import Path

# --- sys.path 調整: src ディレクトリを最優先にする ------------------------
current_dir = Path(__file__).resolve().parent
src_dir = current_dir / "src"
widgets_dir = src_dir / "widgets"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
if str(widgets_dir) not in sys.path:
    sys.path.insert(0, str(widgets_dir))

from PyQt6.QtWidgets import QApplication
from scheduled_yolo_training_widget import ScheduledYoloTrainingWidget  # type: ignore


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = ScheduledYoloTrainingWidget()
    w.show()
    sys.exit(app.exec()) 