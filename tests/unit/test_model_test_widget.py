import os
import shutil
import tempfile
import pytest
from PyQt6.QtWidgets import QApplication
from src.widgets.model_test_widget import ModelTestWidget
from src.utils.path_manager import path_manager

def test_model_test_widget_custom_model(qtbot):
    # テスト用のダミーモデルファイルをmodels_dirに作成
    models_dir = path_manager.models_dir
    models_dir.mkdir(parents=True, exist_ok=True)
    dummy_model_path = models_dir / "dummy_test_model.pt"
    with open(dummy_model_path, "w") as f:
        f.write("dummy")
    dummy_img_path = models_dir / "dummy.jpg"
    with open(dummy_img_path, "wb") as f:
        f.write(b"\x00")
    # ウィジェット起動
    widget = ModelTestWidget()
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    # モデルリストにダミーモデルが出ているか
    found = False
    for i in range(widget.model_combo.count()):
        if widget.model_combo.itemData(i) == str(dummy_model_path):
            found = True
            widget.model_combo.setCurrentIndex(i)
            break
    assert found, "自前モデルがプルダウンに出ていない"
    # 推論実行時に正しいパスが使われるか
    called = {}
    def fake_yolo_init(path):
        called['path'] = path
        class Dummy:
            def __call__(self, img):
                class R: boxes = []; names = []
                return [R()]
        return Dummy()
    widget._YOLO = fake_yolo_init
    try:
        widget.img_dir_edit.setText(str(models_dir))  # 存在するディレクトリをセット
        widget.run_inference()
        assert called['path'] == str(dummy_model_path), f"YOLOに渡されたパスが違う: {called['path']}"
        print(f"[TEST] YOLOに渡されたパス: {called['path']}")
    finally:
        dummy_model_path.unlink()
        dummy_img_path.unlink() 