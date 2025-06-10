import sys
import os
import json
import logging
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.utils.chain_record_utils import ChainRecord
from src.record_matching_utils import match_roles_records_one_stop
from src.utils.path_manager import path_manager
from src.dictionary_manager import DictionaryManager

logging.basicConfig(level=logging.INFO)

# 画像リスト（パスマネージャー経由で取得）
image_list_path = path_manager.current_image_list_json
with open(image_list_path, encoding="utf-8") as f:
    image_list = json.load(f)

# ロールマッピングを外部JSONからDIできるように変更
parser = argparse.ArgumentParser()
parser.add_argument('--role_mapping', type=str, default=None, help='role_mapping.jsonのパス')
args = parser.parse_args()

if args.role_mapping:
    with open(args.role_mapping, encoding="utf-8") as f:
        role_mapping = json.load(f)
else:
    with open(str(path_manager.role_mapping), encoding="utf-8") as f:
        role_mapping = json.load(f)

# デフォルトレコードJSONから全件ロード
with open("data/dictionaries/default_records.json", encoding="utf-8") as f:
    default_records_json = json.load(f)

records = []
for rec_path in default_records_json["records"]:
    rec_full_path = os.path.join("data/dictionaries", rec_path)
    with open(rec_full_path, encoding="utf-8") as f:
        rec_dict = json.load(f)
        records.append(ChainRecord.from_dict(rec_dict))

# 仮の画像→ロール割当（ここではダミー: 画像名から推測するロールを割り当てる例）
def guess_roles_from_filename(filename):
    # 本来はYOLO等の推論結果やキャッシュから取得する
    # ここではファイル名に応じて適当なロールを割り当てる
    if "8603" in filename or "8602" in filename:
        return ["role_worker_pavementcutting"]
    if "8601" in filename or "8600" in filename:
        return ["role_driver_backhoe_break"]
    if "8599" in filename or "8598" in filename:
        return ["role_driver_backhoe_pavement_load"]
    if "8597" in filename or "8596" in filename:
        return ["role_measurer_staff_asphalt_break_thickness"]
    if "8595" in filename or "8594" in filename:
        return ["role_worker_unload_soil"]
    if "8593" in filename or "8592" in filename:
        return ["role_driver_backhoe_level"]
    if "8591" in filename or "8590" in filename:
        return ["roller_conbined_2.5t"]
    if "8589" in filename or "8588" in filename:
        return ["role_measurer_staff_setdown"]
    if "8587" in filename or "8586" in filename:
        return ["role_measurer_staff_soil_thickness"]
    if "8585" in filename or "8584" in filename:
        return ["role_worker_emulsion_spray"]
    if "8583" in filename or "8582" in filename:
        return ["role_worker_emulsion_edge"]
    if "8581" in filename or "8580" in filename:
        return ["role_worker_surface_level"]
    if "8579" in filename or "8578" in filename:
        return ["role_driver_combined_roller"]
    if "8577" in filename or "8576" in filename:
        return ["roller_tyres_3t"]
    if "8575" in filename or "8574" in filename:
        return ["thermometer"]
    if "8573" in filename or "8572" in filename:
        return ["role_worker_sand_curing"]
    if "8571" in filename or "8570" in filename:
        return ["role_worker_meeting"]
    if "8569" in filename or "8568" in filename:
        return ["role_guardman"]
    if "8567" in filename or "8566" in filename:
        return ["role_worker_safety_training"]
    return []

def match_roles_records_normal_test(roles, role_mapping, records):
    """
    通常マッチング（record_index指定のみ）を直接テストする関数。
    """
    indices = set()
    for role in roles:
        mapping = role_mapping.get(role, {})
        idx = mapping.get("record_index")
        if idx is not None and 0 <= idx < len(records):
            indices.add(idx)
    return [records[i] for i in sorted(indices)]

def match_roles_records_normal_debug(roles, role_mapping, records):
    matched_remarks = set()
    for remarks, mapping in role_mapping.items():
        mapping_roles = mapping.get("roles", [])
        if any(role in mapping_roles for role in roles):
            matched_remarks.add(remarks)
    matched_records = [rec for rec in records if getattr(rec, "remarks", None) in matched_remarks]
    return matched_remarks, matched_records

print("画像ファイル名,割当ロール,matched_remarks,マッチしたレコード(フォトカテゴリー/タイプ/サブタイプ/ワークカテゴリー/リマーク)")
for img_path in image_list:
    roles = guess_roles_from_filename(img_path)
    matched_remarks, matched = match_roles_records_normal_debug(roles, role_mapping, records)
    matched_str = "; ".join(
        f"{getattr(r, 'photo_category', '')}/"
        f"{getattr(r, 'type', '')}/"
        f"{getattr(r, 'subtype', '')}/"
        f"{getattr(r, 'work_category', '')}/"
        f"{getattr(r, 'remarks', '')}"
        for r in matched
    )
    print(f"{os.path.basename(img_path)},{roles},{list(matched_remarks)},{matched_str}")
