# YOLO推論・学習ウィジェット起動スクリプト
import sys
import os
from PyQt6.QtWidgets import QApplication

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from widgets.yolo_predict_widget import YoloPredictWidget
from widgets.yolo_train_widget import YoloTrainWidget
from src.widgets.yolo_dataset_convert_widget import YoloDatasetConvertWidget

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 起動したいウィジェットを選択
    # win = YoloPredictWidget()
    # win = YoloTrainWidget()
    win = YoloDatasetConvertWidget()
    win.show()
    sys.exit(app.exec())
