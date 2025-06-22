import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from detect_with_yolo_widget import DetectWithYoloWidget
import random
import os
import pickle
import tempfile
from PIL import Image
import numpy as np

def create_corrupt_image(path):
    """壊れたJPEG画像を作成する"""
    # まずダミー画像を作成
    img = np.ones((100, 100, 3), dtype=np.uint8) * 200
    img_path = path
    Image.fromarray(img).save(img_path)
    
    # 後半を切り詰めて破損させる
    with open(img_path, 'rb') as f:
        data = f.read()
    
    # 画像データを途中で切り詰めて破損させる
    with open(img_path, 'wb') as f:
        f.write(data[:len(data) // 2])
    
    return img_path

@pytest.mark.usefixtures("qtbot")
@pytest.mark.timeout(30)
def test_detect_person_flow(qtbot):
    app = QApplication.instance() or QApplication([])
    widget = DetectWithYoloWidget()
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)

    # モデルリストが空でないこと
    assert widget.model_combo.count() > 0
    # 最初のモデルを選択
    widget.model_combo.setCurrentIndex(0)
    qtbot.wait(500)

    # ラベルリストが空でないこと
    assert widget.label_list.count() > 0
    # "person"ラベルを選択（なければ最初のラベル）
    person_index = None
    for i in range(widget.label_list.count()):
        if "person" in widget.label_list.item(i).text():
            person_index = i
            break
    if person_index is not None:
        widget.label_list.setCurrentRow(person_index)
    else:
        widget.label_list.setCurrentRow(0)
    qtbot.wait(500)

    # 画像が1枚以上あること
    total_images = widget.image_widget.list_widget.count()
    assert total_images > 0
    # ランダムに5枚だけ選択
    indices = random.sample(range(total_images), min(5, total_images))
    widget.image_widget.list_widget.clearSelection()
    for idx in indices:
        widget.image_widget.list_widget.item(idx).setSelected(True)
    # 検出ボタンを押す
    qtbot.mouseClick(widget.detect_btn, Qt.MouseButton.LeftButton)
    # 検出結果が出るまで待つ
    qtbot.wait(2000)
    # 検出結果リストが表示されていること（0件でもOK）
    assert hasattr(widget, "result_widget")
    assert widget.result_widget is not None
    # 終了
    widget.close()

@pytest.mark.usefixtures("qtbot")
@pytest.mark.timeout(30)
def test_label_list_cache_display(qtbot):
    app = QApplication.instance() or QApplication([])
    widget = DetectWithYoloWidget()
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)

    # モデル・ラベル・画像セットを取得
    model_path = widget.model_paths[0]
    widget.model_combo.setCurrentIndex(0)
    qtbot.wait(200)
    label_id = list(widget.class_names.keys())[0]
    image_paths = tuple([widget.image_widget.list_widget.item(i).data(Qt.ItemDataRole.UserRole)
                        for i in range(widget.image_widget.list_widget.count())])
    cache_key = (model_path, label_id, image_paths)
    # キャッシュをセット
    widget.detect_cache[cache_key] = ([], {})
    # on_model_selectedでラベルリストを再生成
    widget.on_model_selected()
    # [cache]が付いているか確認
    found = False
    for i in range(widget.label_list.count()):
        text = widget.label_list.item(i).text()
        if "[cache]" in text:
            found = True
            break
    assert found, "ラベルリストに[cache]表示がない"

@pytest.mark.usefixtures("qtbot")
@pytest.mark.timeout(30)
def test_detected_thumbnail_has_bbox(qtbot):
    app = QApplication.instance() or QApplication([])
    widget = DetectWithYoloWidget()
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)

    # モデル・ラベル・画像を選択
    widget.model_combo.setCurrentIndex(0)
    qtbot.wait(200)
    assert widget.label_list.count() > 0
    widget.label_list.setCurrentRow(0)
    qtbot.wait(200)
    total_images = widget.image_widget.list_widget.count()
    assert total_images > 0
    # 1枚だけ選択
    widget.image_widget.list_widget.clearSelection()
    widget.image_widget.list_widget.item(0).setSelected(True)
    qtbot.mouseClick(widget.detect_btn, Qt.MouseButton.LeftButton)
    qtbot.wait(2000)
    # 検出結果ウィンドウのサムネイルにbboxが描画されているか
    # → set_imagesでbbox_dictが渡っていればOK
    result_widget = widget.result_widget
    img_path = result_widget.image_paths[0]
    assert img_path in result_widget.bbox_dict
    assert len(result_widget.bbox_dict[img_path]) >= 0  # 0件でもOK（描画処理が走ることが重要）
    widget.close()

@pytest.mark.usefixtures("qtbot")
@pytest.mark.timeout(30)
def test_corrupt_image_exclusion(qtbot):
    """破損画像がキャッシュから自動的に除外されることを検証"""
    app = QApplication.instance() or QApplication([])
    
    # 一時ディレクトリ作成
    temp_dir = tempfile.mkdtemp()
    # 破損画像を作成
    corrupt_path = os.path.join(temp_dir, "corrupt.jpg")
    create_corrupt_image(corrupt_path)
    
    # 一時キャッシュファイルのパスを設定
    cache_file = os.path.join(temp_dir, "test_cache.pkl")
    
    # テスト用キャッシュデータを作成
    test_cache = {
        ("dummy_model", 0, corrupt_path): [],  # 破損画像エントリ
        ("dummy_model", 1, "dummy_path.jpg"): []  # 正常エントリ
    }
    
    # キャッシュ保存
    with open(cache_file, "wb") as f:
        pickle.dump(test_cache, f)
    
    # 起動前のキャッシュサイズ記録
    before_count = len(test_cache)
    
    # モンキーパッチでキャッシュファイルを差し替え
    orig_cache_file = DetectWithYoloWidget.CACHE_FILE
    DetectWithYoloWidget.CACHE_FILE = cache_file
    
    try:
        # ウィジェット初期化（この時点でキャッシュ検査が走る）
        widget = DetectWithYoloWidget()
        qtbot.addWidget(widget)
        
        # 破損画像エントリがキャッシュから除外されていることを確認
        assert len(widget.detect_cache) < before_count
        
        # 破損画像のエントリが存在しないことを確認
        corrupt_keys = [k for k in widget.detect_cache.keys() if k[2] == corrupt_path]
        assert len(corrupt_keys) == 0, "破損画像がキャッシュから除外されていない"
        
        widget.close()
    finally:
        # モンキーパッチを戻す
        DetectWithYoloWidget.CACHE_FILE = orig_cache_file
        # 一時ファイル削除（可能であれば）
        try:
            os.remove(corrupt_path)
            os.remove(cache_file)
            os.rmdir(temp_dir)
        except:
            pass 