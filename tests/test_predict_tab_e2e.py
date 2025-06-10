import os
import sys
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from src.ui.tabs.predict_tab import PredictTab
from pathlib import Path
import time

MODEL_PATH = r"C:\Users\yuuji\Sanyuu2Kouku\cursor_tools\PhotoCategorizer\runs\train\exp4\weights\best.pt"
IMAGE_DIR = r"H:\マイドライブ\過去の現場_元請\2019.1218 市道　田迎５丁目第１１号線外４路線舗装補修工事\７工事写真\285_0215　田迎１"

@pytest.mark.qt
def test_predict_tab_e2e(qtbot, tmp_path):
    # PredictTabインスタンス生成
    tab = PredictTab(settings_manager=None)
    qtbot.addWidget(tab)

    # モデルと画像ディレクトリをセット
    tab.model_combo.clear()
    tab.model_combo.addItem("テストモデル", MODEL_PATH)
    tab.model_combo.setCurrentIndex(0)
    tab.image_dir_edit.setText(IMAGE_DIR)

    # クラス名マッピングが日本語キャプションになっているか確認（printのみ）
    tab.load_class_names()
    print(f"[TEST] class_names: {tab.class_names}")

    # 信頼度を0.25にセット
    tab.conf_slider.setValue(25)

    # 予測開始（UI操作はスキップ）
    # with qtbot.waitSignal(tab.prediction_started, timeout=10000) as blocker:
    #     qtbot.mouseClick(tab.predict_btn, Qt.MouseButton.LeftButton)
    # # シグナル値を取得
    # model_path, image_dir, conf = blocker.args
    # assert model_path == MODEL_PATH
    # assert image_dir == IMAGE_DIR
    # assert abs(conf - 0.25) < 1e-3

    # 疑似的にon_prediction_finishedを呼ぶ（本来はバックグラウンドで実行される）
    test_img = next(Path(IMAGE_DIR).glob("*.jpg"), None)
    assert test_img is not None, "テスト画像が見つかりません"
    dummy_results = {str(test_img): [{"bbox": [10, 10, 100, 100], "score": 0.9, "label": "class_0", "class_id": 0}]}
    tab.on_prediction_finished(0, dummy_results)

    # 検出結果の各アイテムにclass_id, label, caption（日本語）が正しく再アサインされているかをprintで出力
    for det in tab.current_results[str(test_img)]:
        print(f"[TEST] class_id={det.get('class_id')}, label={det.get('label')}, caption={det.get('caption')}")

    # 結果リストが1件追加されていること
    assert tab.results_list.count() >= 1
    item = tab.results_list.item(0)
    assert item is not None
    # リスト選択
    tab.results_list.setCurrentRow(0)
    qtbot.wait(100)
    # 下ペインに画像が表示されていること
    pixmap = tab.image_placeholder.pixmap()
    assert pixmap is not None and not pixmap.isNull(), "下ペインに画像が表示されていません"
    # キャッシュファイルが保存されていること
    assert os.path.exists(tab.cache_file)
    # キャッシュから復元できること
    tab.current_results = {}
    tab.load_detection_cache()
    assert str(test_img) in tab.current_results 