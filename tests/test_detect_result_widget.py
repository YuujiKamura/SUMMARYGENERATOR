import sys
import os
import json
import shutil
import pytest
from PyQt6.QtWidgets import QApplication
from src.widgets.detect_result_widget import DetectResultWidget

def setup_module(module):
    # seeds_testディレクトリをテスト前に削除
    if os.path.exists('seeds_test'):
        shutil.rmtree('seeds_test')

def teardown_module(module):
    # seeds_testディレクトリは残す
    pass

def get_real_image_paths(n=3):
    cache_path = os.path.join('data', 'detection_results_cache.json')
    with open(cache_path, 'r', encoding='utf-8') as f:
        d = json.load(f)
    # 空でない画像パスを優先
    paths = [k for k, v in d.items() if isinstance(v, list) and v]
    if len(paths) < n:
        paths = list(d.keys())[:n]
    return paths[:n]

def test_detect_result_widget_layout(qtbot):
    widget = DetectResultWidget()
    qtbot.addWidget(widget)
    widget.show()
    # ロールリストと画像ウィジェットが存在するか
    assert hasattr(widget, 'role_list')
    assert hasattr(widget, 'image_widget')
    # レイアウトが正しく設定されているか
    assert widget.layout() is not None
    # 子ウィジェットがDetectResultWidgetの子として存在するか
    assert widget.role_list in widget.findChildren(type(widget.role_list))
    assert widget.image_widget in widget.findChildren(type(widget.image_widget))

def test_assign_and_json_save(qtbot):
    widget = DetectResultWidget(test_mode=True, save_dir="seeds_test")
    qtbot.addWidget(widget)
    widget.show()
    # 実データキャッシュから画像パス取得
    real_images = get_real_image_paths(3)
    widget.set_images(real_images)
    # 画像を複数選択
    for i in range(len(real_images)):
        item = widget.image_widget.list_widget.item(i)
        item.setSelected(True)
    # ロールを1つ選択
    widget.role_list.setCurrentRow(0)
    role_label = widget.role_list.currentItem().data(256)  # UserRole
    # 割り当てボタン押下
    widget.assign_selected_images()
    # JSONファイルができているか
    json_path = os.path.join('seeds_test', f'{role_label}.json')
    assert os.path.exists(json_path)
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert data['label'] == role_label
    assert set(data['images']) == set(real_images) 