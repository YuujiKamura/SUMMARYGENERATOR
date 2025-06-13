import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from PyQt6.QtWidgets import QApplication
from src.widgets.yolo_predict_widget import YoloPredictWidget

if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = YoloPredictWidget()
    widget.show()
    sys.exit(app.exec())
