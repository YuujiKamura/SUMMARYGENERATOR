import os
import json
import hashlib
import pytest
from PyQt6.QtWidgets import QApplication
from src.single_label_maker_dialog import SingleLabelMakerDialog
from src.utils.bbox_utils import BoundingBox

@pytest.mark.usefixtures("qtbot")
def test_label_add_delete_saves_json(qtbot):
    # 1. 実データから画像パス・クラスリスト取得
    base_dir = os.path.dirname(os.path.dirname(__file__))
    preset_path = os.path.join(base_dir, "src", "preset_roles.json")
    cache_dir = os.path.join(base_dir, "src", "image_preview_cache")
    with open(preset_path, encoding="utf-8") as f:
        class_list = json.load(f)
    # 適当な画像キャッシュファイルを1つ選ぶ
    img_path = None
    for fname in os.listdir(cache_dir):
        if fname.endswith(".json"):
            with open(os.path.join(cache_dir, fname), encoding="utf-8") as f:
                data = json.load(f)
            img_path = data.get("image_path")
            if img_path:
                break
    if not img_path:
        pytest.skip("No image cache found")
    # 2. ダイアログ起動
    dlg = SingleLabelMakerDialog(img_path, class_list)
    qtbot.addWidget(dlg)
    dlg.show()
    qtbot.waitExposed(dlg)
    # 3. bbox追加
    orig_count = len(dlg.anno_view.bboxes)
    new_box = BoundingBox(0, "test", 1.0, [10, 10, 50, 50], "test_role")
    dlg.anno_view.bboxes.append(new_box)
    dlg.save_current_bboxes()
    # 4. JSONファイルを即時チェック
    h = hashlib.sha1(img_path.encode("utf-8")).hexdigest()
    json_path = os.path.join(cache_dir, f"{h}.json")
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert any(b.get("xyxy") == [10, 10, 50, 50] for b in data.get("bboxes", []))
    # 5. bbox削除
    dlg.anno_view.bboxes = [b for b in dlg.anno_view.bboxes if not (hasattr(b, 'xyxy') and b.xyxy == [10, 10, 50, 50])]
    dlg.save_current_bboxes()
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert not any(b.get("xyxy") == [10, 10, 50, 50] for b in data.get("bboxes", [])) 