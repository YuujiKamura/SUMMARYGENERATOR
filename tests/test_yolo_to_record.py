import sys
import os
import json
from rapidfuzz import fuzz
import pytest

# プロジェクトルートをsys.pathに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.utils.path_manager import path_manager

def load_all_records():
    records_index_path = path_manager.default_records
    with open(records_index_path, encoding='utf-8') as f:
        records_index = json.load(f)
    records = []
    records_dir = os.path.join(os.path.dirname(records_index_path), 'records')
    for rec_file in records_index['records']:
        rec_path = os.path.join(records_dir, os.path.basename(rec_file))
        with open(rec_path, encoding='utf-8') as rf:
            records.append(json.load(rf))
    return records

def load_role_mapping():
    mapping_path = path_manager.role_mapping
    with open(mapping_path, encoding='utf-8') as f:
        return json.load(f)

def match_roles_to_record(roles, records, role_mapping):
    candidates = []
    for r in records:
        score = 0
        for role in roles:
            mapping = role_mapping.get(role)
            if not mapping:
                continue
            field = mapping.get("field")
            if not field or field not in r:
                continue
            rec_val = str(r.get(field, ''))
            role_val = role
            score += fuzz.token_set_ratio(role_val, rec_val)
        candidates.append((score, r))
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates

@pytest.mark.parametrize("roles,expected_remarks", [
    (["舗装版切断"], "As舗装版切断状況"),
    (["端部乳剤塗布"], "端部乳剤塗布状況"),
    (["表層工"], "プライムコート養生砂散布状況"),
])
def test_yolopredict_roles_to_record(roles, expected_remarks):
    records = load_all_records()
    role_mapping = load_role_mapping()
    results = match_roles_to_record(roles, records, role_mapping)
    top_remarks = results[0][1].get('remarks', '')
    print(f"ロール: {roles} → 最上位: {top_remarks}")
    assert expected_remarks in top_remarks or top_remarks in expected_remarks

@pytest.mark.parametrize("surface, persons, objects, expected_remarks", [
    ("舗装面", [{"name": "山田", "role": "切断作業"}], ["標尺"], "As舗装版切断状況"),
    ("路盤", [{"name": "佐藤", "role": "乳剤塗布"}], [], "端部乳剤塗布状況"),
    ("表層", [], ["養生砂"], "プライムコート養生砂散布状況"),
])
def test_photo_entities_to_record(surface, persons, objects, expected_remarks):
    """
    surface, persons, objects から record を検索・remarks をマッチングする現場イメージ重視のテスト雛形
    """
    records = load_all_records()
    # 仮: surface, persons, objects を remarks に連結して単純検索（本実装は要リファクタ）
    query = f"{surface} " + " ".join([p["role"] for p in persons]) + " " + " ".join(objects)
    best = None
    best_score = -1
    for r in records:
        rec_val = str(r.get('remarks', ''))
        score = fuzz.token_set_ratio(query, rec_val)
        if score > best_score:
            best_score = score
            best = r
    top_remarks = best.get('remarks', '') if best else ''
    print(f"surface: {surface}, persons: {persons}, objects: {objects} → 最上位: {top_remarks}")
    assert expected_remarks in top_remarks or top_remarks in expected_remarks

@pytest.mark.parametrize("surface, persons, objects, machines, expected_remarks", [
    # 個人＋道具＋姿勢
    ("舗装面", [{"name": "山田", "tool": "カッター", "posture": "切断"}], [], [], "As舗装版切断状況"),
    # 標尺の使われ方
    ("舗装面", [], ["標尺"], [], "舗装厚測定状況"),
    # 機械＋運転手
    ("舗装面", [], [], [{"type": "ローラー", "operator": "佐藤"}], "転圧作業状況"),
])
def test_photo_entities_to_record_rich(surface, persons, objects, machines, expected_remarks):
    """
    surface, persons(tool, posture), objects, machines(operator) から record を検索・remarks をマッチングするテスト（現場イメージ拡張版）
    """
    records = load_all_records()
    person_desc = " ".join([f"{p.get('tool','')} {p.get('posture','')}".strip() for p in persons])
    machine_desc = " ".join([f"{m.get('type','')} {m.get('operator','')}".strip() for m in machines])
    query = f"{surface} {person_desc} {' '.join(objects)} {machine_desc}"
    best = None
    best_score = -1
    for r in records:
        rec_val = str(r.get('remarks', ''))
        score = fuzz.token_set_ratio(query, rec_val)
        if score > best_score:
            best_score = score
            best = r
    top_remarks = best.get('remarks', '') if best else ''
    print(f"surface: {surface}, persons: {persons}, objects: {objects}, machines: {machines} → 最上位: {top_remarks}")
    assert expected_remarks in top_remarks or top_remarks in expected_remarks

@pytest.mark.parametrize("yoloclasses, expected_remarks", [
    (["舗装面", "切断作業", "標尺"], "As舗装版切断状況"),
    (["路盤", "乳剤塗布"], "端部乳剤塗布状況"),
    (["表層", "養生砂"], "プライムコート養生砂散布状況"),
])
def test_yoloclasses_to_record(yoloclasses, expected_remarks):
    records = load_all_records()
    query = " ".join(yoloclasses)
    best = None
    best_score = -1
    for r in records:
        rec_val = str(r.get('remarks', ''))
        score = fuzz.token_set_ratio(query, rec_val)
        if score > best_score:
            best_score = score
            best = r
    top_remarks = best.get('remarks', '') if best else ''
    print(f"yoloclasses: {yoloclasses} → 最上位: {top_remarks}")
    assert expected_remarks in top_remarks or top_remarks in expected_remarks

class YoloBox:
    """
    YOLO検出結果の矩形領域とその属性を表す。
    category: サブタイプ（例: 'surface', 'roleperson', 'object' など）
    class_name: 具体的な種別名（例: '舗装面', '切断作業', '標尺' など）
    bbox: (x1, y1, x2, y2)
    info: 追加情報（任意、辞書型。例: {'role': '切断作業', 'tool': 'カッター'}）
    """
    def __init__(self, category, class_name, bbox, info=None):
        self.category = category
        self.class_name = class_name
        self.bbox = bbox
        self.info = info or {}

    def __repr__(self):
        return f"<YoloBox {self.category} {self.class_name} {self.bbox} {self.info}>"
