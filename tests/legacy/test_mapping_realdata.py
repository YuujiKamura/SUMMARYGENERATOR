import os
import pytest
from src.record_matching_utils import match_image_to_remarks
from src.summary_generator import load_role_mapping
import json

@pytest.mark.parametrize("cache_dir, mapping_path, records_path", [
    (
        os.path.abspath("src/image_preview_cache"),
        os.path.abspath("role_mapping.json"),
        os.path.abspath("data/dictionaries/default_records.json"),
    )
])
def test_realdata_mapping(cache_dir, mapping_path, records_path):
    # マッピング・辞書ロード
    mapping = load_role_mapping(mapping_path)
    with open(records_path, encoding="utf-8") as f:
        records_json = json.load(f)
    # recordsはdefault_records.jsonの"records"リストをさらに読む
    records = []
    for rec_path in records_json["records"]:
        rec_abspath = os.path.join(os.path.dirname(records_path), rec_path)
        with open(rec_abspath, encoding="utf-8") as rf:
            records.append(json.load(rf))
    # 画像ロール情報をキャッシュから構築
    image_roles = {}
    for fname in os.listdir(cache_dir):
        if fname.endswith(".json"):
            with open(os.path.join(cache_dir, fname), encoding="utf-8") as f:
                data = json.load(f)
            img_path = data.get("image_path")
            bboxes = data.get("bboxes", [])
            roles = [b.get("role") for b in bboxes if b.get("role")]
            if img_path:
                image_roles[img_path] = roles
    # マッピング実行
    results = match_image_to_remarks(
        image_roles, mapping, cache_dir, records_path=records_path
    )
    # 期待値例: 画像ごとにremarksが1つ以上割り当てられている
    for img_path, remarks in results.items():
        print(f"{img_path}: {remarks}")
        assert isinstance(remarks, list)
        assert all(isinstance(r, str) for r in remarks)
        # ここに「この画像にはこのremarksが付くべき」などの個別assertを追加可能