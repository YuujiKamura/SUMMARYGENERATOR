import os
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QPushButton
from src.image_preview_dialog import ImagePreviewDialog
import json

@pytest.fixture
def dialog(qtbot):
    # 最後に開いた画像パスをconfigから取得
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    config_path = os.path.abspath(os.path.join(base_dir, "src", "image_preview_dialog_last.json"))
    assert os.path.exists(config_path), f"image_preview_dialog_last.jsonが存在しません: {config_path}"
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    img_path = data.get("last_image_path")
    assert img_path and os.path.exists(img_path), f"画像ファイルが存在しません: {img_path}"
    dlg = ImagePreviewDialog(img_path)
    qtbot.addWidget(dlg)
    dlg.show()
    qtbot.waitExposed(dlg)
    return dlg

def test_yolo_inference_button_works(qtbot, dialog):
    # YOLO推論ボタンを押す
    btn = dialog.detect_btn
    assert isinstance(btn, QPushButton)
    qtbot.mouseClick(btn, Qt.MouseButton.LeftButton)
    # 推論スレッドが完了するまで待つ（最大60秒）
    qtbot.waitUntil(lambda: not dialog._data_load_thread.isRunning(), timeout=60000)
    # bboxが1つ以上生成されるまでさらに待つ（最大5秒）
    qtbot.waitUntil(lambda: len(dialog.bboxes) > 0, timeout=5000)
    # ステータスバーにエラーが出ていないか確認
    status = dialog.status_label.text()
    assert "エラー" not in status, f"YOLO推論でエラー: {status}"
    # bboxが1つ以上生成されていることを確認
    assert len(dialog.bboxes) > 0, "YOLO推論でバウンディングボックスが生成されていません" 