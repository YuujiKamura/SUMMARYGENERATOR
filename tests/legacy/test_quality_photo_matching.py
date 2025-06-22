import os
import json
import pytest
from src.summary_generator import collect_image_data_from_cache, load_role_mapping
from src.utils.records_loader import load_records_from_json
from src.record_matching_utils import match_roles_records, is_thermometer_image
from src.utils.path_manager import path_manager
from src.thermometer_utils import assign_thermometer_remarks, THERMO_REMARKS

# テスト用画像リストJSON
IMAGE_LIST_PATH = os.path.join('data', 'image_list20250531.json')
CACHE_DIR = 'src/image_preview_cache'

@pytest.mark.parametrize('image_list_path', [IMAGE_LIST_PATH])
def test_quality_photo_extraction(image_list_path):
    # 画像リスト読み込み
    with open(image_list_path, encoding='utf-8') as f:
        image_list = json.load(f)
    # roles情報取得
    image_data = collect_image_data_from_cache(CACHE_DIR)
    per_image_roles = image_data['per_image_roles']
    # ロールマッピング・レコードリスト取得
    mapping = load_role_mapping()
    records = load_records_from_json(path_manager.default_records)
    # 品質管理写真カテゴリの抽出
    quality_photos = []
    for img_path in image_list:
        abs_img_path = os.path.abspath(img_path)
        roles = per_image_roles.get(abs_img_path, [])
        if not roles:
            continue  # roles情報がなければスキップ
        # 仮のimg_jsonを構築
        img_json = {'roles': roles, 'image_path': abs_img_path}
        matched = match_roles_records(img_json, mapping, records)
        # 品質管理写真カテゴリが含まれるか
        for rec in matched:
            photo_category = getattr(rec, 'photo_category', None) or rec.get('photo_category')
            if photo_category == '品質管理写真':
                quality_photos.append(abs_img_path)
                break
    # 結果検証（最低1件は品質管理写真が抽出されることを期待）
    assert len(quality_photos) > 0, '品質管理写真が1件も抽出されませんでした'
    print(f"品質管理写真に分類された画像数: {len(quality_photos)}")

@pytest.mark.parametrize('image_list_path', [IMAGE_LIST_PATH])
def test_thermometer_image_remark_assignment(image_list_path):
    # 画像リスト読み込み
    with open(image_list_path, encoding='utf-8') as f:
        image_list = json.load(f)
    # roles情報取得
    image_data = collect_image_data_from_cache(CACHE_DIR)
    per_image_roles = image_data['per_image_roles']
    # レコードリスト取得
    records = load_records_from_json(path_manager.default_records)
    # 品質管理写真カテゴリのremarksのみ抽出
    quality_remarks = [getattr(r, 'remarks', None) if hasattr(r, 'remarks') else r.get('remarks', None) for r in records if (getattr(r, 'photo_category', None) or r.get('photo_category', None)) == '品質管理写真']
    # THERMO_REMARKS順で並べ替え
    ordered_remarks = [r for r in THERMO_REMARKS if r in quality_remarks]
    # 温度計画像だけ抽出
    thermometer_images = []
    for img_path in image_list:
        abs_img_path = os.path.abspath(img_path)
        roles = per_image_roles.get(abs_img_path, [])
        if not roles:
            continue
        if is_thermometer_image(roles):
            thermometer_images.append(abs_img_path)
    # 温度管理用remarks割り当て
    assigned = assign_thermometer_remarks(thermometer_images, remarks_list=ordered_remarks)
    # 割り当て結果の検証
    assert len(assigned) == len(thermometer_images), '温度計画像へのremarks割り当て数が一致しません'
    # remarks内容が温度測定系であることを検証
    for img_path, remark in assigned.items():
        assert remark is not None, f'{img_path} にremarksが割り当てられていません'
        assert '温度' in remark or '測定' in remark, f'{img_path} のremarksが温度測定系でない: {remark}'
    print(f"温度計画像数: {len(thermometer_images)} / 割り当て成功: {len(assigned)}")

@pytest.mark.parametrize('image_list_path', [IMAGE_LIST_PATH])
def test_thermometer_remark_cycle(image_list_path):
    # 画像リスト読み込み
    with open(image_list_path, encoding='utf-8') as f:
        image_list = json.load(f)
    # roles情報取得
    image_data = collect_image_data_from_cache(CACHE_DIR)
    per_image_roles = image_data['per_image_roles']
    # レコードリスト取得
    records = load_records_from_json(path_manager.default_records)
    # 品質管理写真カテゴリのremarksのみ抽出
    quality_remarks = [getattr(r, 'remarks', None) if hasattr(r, 'remarks') else r.get('remarks', None) for r in records if (getattr(r, 'photo_category', None) or r.get('photo_category', None)) == '品質管理写真']
    # THERMO_REMARKS順で並べ替え
    ordered_remarks = [r for r in THERMO_REMARKS if r in quality_remarks]
    # remarksが4種未満ならスキップ
    if len(ordered_remarks) < 4:
        pytest.skip('温度管理remarksが4種未満のためサイクル検証不可')
    # 温度計画像だけ抽出
    thermometer_images = []
    for img_path in image_list:
        abs_img_path = os.path.abspath(img_path)
        roles = per_image_roles.get(abs_img_path, [])
        if not roles:
            continue
        if is_thermometer_image(roles):
            thermometer_images.append(abs_img_path)
    # 時系列順（ファイル名昇順）でソート
    thermometer_images_sorted = sorted(thermometer_images, key=lambda x: os.path.basename(x))
    # remarksサイクル割り当て
    assigned = assign_thermometer_remarks(thermometer_images_sorted, remarks_list=ordered_remarks)
    # サイクル割り当てが仕様通りか（末尾3枚は開放温度）を検証
    group_size = 3
    n = len(thermometer_images_sorted)
    for i in range(n):
        if n - i <= 3:
            expected = THERMO_REMARKS[-1]  # 開放温度
        else:
            expected = THERMO_REMARKS[(i // group_size) % (len(THERMO_REMARKS)-1)]
        actual = assigned[thermometer_images_sorted[i]]
        assert actual == expected, f'{i+1}枚目: 割り当てremarksがサイクル通りでない: {actual} != {expected}'
    print(f"サイクル割り当て検証OK: {n}枚/グループ{group_size}ごとに切替（末尾3枚は開放温度、時系列順）") 