import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from PyQt6.QtWidgets import QApplication
from src.widgets.yolo_predict_widget import YoloPredictWidget

@pytest.fixture(scope="module")
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app

def test_widget_ui_components(app):
    widget = YoloPredictWidget()
    # UI部品が正しく生成されているか
    assert widget.model_combo is not None
    assert widget.model_refresh_btn is not None
    assert widget.image_dir_edit is not None
    assert widget.image_dir_btn is not None
    assert widget.conf_spin is not None
    assert widget.predict_btn is not None
    assert widget.progress_bar is not None
    assert widget.log_text is not None
    # モデルリストが1件以上ある（環境依存だが空でなければOK）
    assert widget.model_combo.count() > 0
    # 信頼度初期値
    assert 0.01 <= widget.conf_spin.value() <= 1.0
    widget.close()
