import sys
import os
import json
from src.scan_for_images_dataset import save_dataset_json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
import pytest
from summary_generator import get_all_image_data

THERMO_TEST_JSON = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src/scan_for_images_dataset_thermo_test.json"))
IMAGE_LIST_JSON = r"C:/Users/yuuji/Sanyuu2Kouku/cursor_tools/PhotoCategorizer/data/image_list20250531.json"
CACHE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src/image_preview_cache"))

def setup_module(module):
    # 既にテスト用JSONが存在すれば再生成をスキップ
    if not os.path.exists(THERMO_TEST_JSON):
        save_dataset_json(cache_dir=CACHE_DIR, out_path=THERMO_TEST_JSON, debug=False, collect_mode='list', image_list_json_path=IMAGE_LIST_JSON)

def test_thermo_mapping_realdata():
    import os
    base_dir = os.path.dirname(__file__)
    json_path = THERMO_TEST_JSON
    folder_path = "image_preview_cache"
    data = get_all_image_data(json_path, folder_path, folder_path)
    print("[test] thermo_remarks_map:")
    for k, v in data['thermo_remarks_map'].items():
        print(f"  {k}: {v}")
    print("[test] per_image_roles:")
    for k, v in data['per_image_roles'].items():
        print(f"  {k}: {v}")
    print("[test] match_results:")
    for k, v in data['match_results'].items():
        print(f"  {k}: {v}")
    print("[test] folder_to_images:")
    for k, v in data['folder_to_images'].items():
        print(f"  {k}: {v}")
    print("[test] folder_names:")
    print(data['folder_names'])

def test_list_all_roles():
    import os
    base_dir = os.path.dirname(__file__)
    json_path = THERMO_TEST_JSON
    folder_path = "image_preview_cache"
    data = get_all_image_data(json_path, folder_path, folder_path)
    image_roles = data['per_image_roles']
    all_roles = set()
    for roles in image_roles.values():
        all_roles.update(roles)
    print("全ロール名一覧:", all_roles)

def test_list_all_labels_and_roles():
    import json
    import os
    base_dir = os.path.dirname(__file__)
    json_path = THERMO_TEST_JSON
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    for entry in data:
        img_path = entry.get('image_path')
        bboxes = entry.get('bboxes', [])
        for bbox in bboxes:
            label = bbox.get('label')
            role = bbox.get('role')
            print(f"{img_path} | label: {label} | role: {role}")

def test_thermo_remarks_map_expectation():
    import os
    base_dir = os.path.dirname(__file__)
    json_path = THERMO_TEST_JSON
    folder_path = "image_preview_cache"
    data = get_all_image_data(json_path, folder_path, folder_path)
    image_roles = data['per_image_roles']
    thermo_remarks_map = data['thermo_remarks_map']
    # 温度計関連画像（roleにthermometerを含むもの）を抽出
    expected_thermo_imgs = [p for p, roles in image_roles.items() if any(r and "thermometer" in r for r in roles)]
    # thermo_remarks_mapのキー（絶対パス正規化）
    norm = lambda p: os.path.normcase(os.path.abspath(p))
    mapped_keys = set(thermo_remarks_map.keys())
    expected_keys = set(norm(p) for p in expected_thermo_imgs)
    # 1. すべての温度計画像がthermo_remarks_mapに含まれる
    assert expected_keys <= mapped_keys, f"温度計画像の一部がthermo_remarks_mapに含まれていません: {expected_keys - mapped_keys}"
    # 2. remarksがNoneでないものが一定数以上ある
    non_none = [v for v in thermo_remarks_map.values() if v]
    assert len(non_none) >= 1, "remarksがNoneでない温度計画像が1件もありません"
    # 3. remarks内容が温度測定系であること
    for v in non_none:
        assert "温度" in v or "測定" in v, f"remarks内容が温度測定系でない: {v}"

def test_cycle_matching_realdata():
    import os
    base_dir = os.path.dirname(__file__)
    json_path = THERMO_TEST_JSON
    folder_path = "image_preview_cache"
    data = get_all_image_data(json_path, folder_path, folder_path)
    match_results = data['match_results']
    thermo_remarks_map = data['thermo_remarks_map']

    # remarksが温度管理系（例: remarksに「温度」や「測定」含む）画像を抽出
    quality_imgs = [p for p, v in thermo_remarks_map.items() if v and ("温度" in v or "測定" in v)]
    sample_imgs = quality_imgs[:12]

    # まとめてテスト
    assert len(sample_imgs) == 12, f"品質管理写真が12枚未満: {len(sample_imgs)}"
    for p in sample_imgs:
        assert thermo_remarks_map[p] is not None, f"{p} のremarksがNone"

    # 1枚ずつ詳細検証
    for p in sample_imgs:
        remarks = thermo_remarks_map[p]
        print(f"[cycle-matching] {p}: remarks={remarks}, match={match_results.get(p)}")
        assert "温度" in remarks or "測定" in remarks, f"{p} のremarks内容が不正: {remarks}" 