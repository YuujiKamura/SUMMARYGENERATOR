import os
import json
import shutil
import tempfile
from pathlib import Path
import pytest
from src.scan_for_images_dataset import save_dataset_json

def make_test_cache(cache_dir, image_dir, role_name="notice_sign_board"):
    # テスト画像を1枚作成
    img_path = os.path.join(image_dir, "test_img.jpg")
    with open(img_path, "wb") as f:
        f.write(b"\x00")  # ダミー画像
    # SHA1を計算
    import hashlib
    sha1 = hashlib.sha1(img_path.encode("utf-8")).hexdigest()
    # キャッシュJSONを作成
    cache_json = {
        "image_path": img_path,
        "bboxes": [
            {
                "role": role_name,
                "bbox": [10, 20, 30, 40]
            }
        ]
    }
    os.makedirs(cache_dir, exist_ok=True)
    with open(os.path.join(cache_dir, f"{sha1}.json"), "w", encoding="utf-8") as f:
        json.dump(cache_json, f, ensure_ascii=False, indent=2)
    return img_path


def test_save_dataset_json_includes_notice_sign_board():
    with tempfile.TemporaryDirectory() as tmpdir:
        image_dir = os.path.join(tmpdir, "images")
        cache_dir = os.path.join(tmpdir, "image_preview_cache")
        os.makedirs(image_dir, exist_ok=True)
        # notice_sign_boardを含むキャッシュを作成
        img_path = make_test_cache(cache_dir, image_dir, role_name="notice_sign_board")
        out_path = os.path.join(tmpdir, "scan_for_images_dataset.json")
        ok = save_dataset_json(cache_dir=cache_dir, out_path=out_path, debug=True, collect_mode='all')
        assert ok, "save_dataset_json failed"
        with open(out_path, encoding="utf-8") as f:
            data = json.load(f)
        # notice_sign_boardが含まれているか
        found = False
        for entry in data:
            for bbox in entry.get("bboxes", []):
                if bbox.get("role") == "notice_sign_board":
                    found = True
        assert found, "notice_sign_boardがscan_for_images_dataset.jsonに含まれていない"

def test_roles_exist_in_scan_for_images_dataset():
    """
    scan_for_images_dataset.jsonの中身をパースし、実際に含まれているrole一覧を動的に取得し、
    1つでもroleが含まれていればOKとする汎用テスト。
    """
    from src.utils.path_manager import path_manager
    import os
    import json
    json_path = str(path_manager.scan_for_images_dataset)
    assert os.path.exists(json_path), f"{json_path} が存在しません"
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    roles = set()
    for entry in data:
        for bbox in entry.get("bboxes", []):
            role = bbox.get("role")
            if role:
                roles.add(role)
    assert roles, "scan_for_images_dataset.json に1つもroleが含まれていません"
    print("含まれているrole一覧:", roles) 