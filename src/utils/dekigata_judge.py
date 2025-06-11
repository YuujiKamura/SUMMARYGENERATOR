"""
出来形（caption_board_dekigata）判定ロジック専用モジュール
"""
import logging
from src.utils.caption_board_utils import judge_caption_board_closeup

def _is_true(val):
    return val is True or val == "True" or val == 1

def _is_false(val):
    return val is False or val == "False" or val == 0

def has_caption_board(img_json):
    """
    img_json内にcaption_boardロールが存在するか判定
    """
    # caption_board, caption_board_dekigata どちらも許容
    roles = img_json.get('roles', [])
    if any(r in ('caption_board', 'caption_board_dekigata') for r in roles):
        return True
    for b in img_json.get('bboxes', []):
        if b.get('role') in ('caption_board', 'caption_board_dekigata'):
            return True
    return False

def detect_caption_board_type(img_json):
    """
    caption_boardの種別を判定し、"closeup"/"overview"/"kanrichi"/None のいずれかを返す。
    img_json: 1画像分のキャッシュJSON/dict
    戻り値: str or None
    """
    bboxes = img_json.get('bboxes')
    img_w = img_json.get('img_w')
    img_h = img_json.get('img_h')
    try:
        is_closeup_val, ratio = judge_caption_board_closeup(bboxes or [], img_w, img_h)
        if is_closeup_val is True:
            return "closeup"
        elif is_closeup_val is False:
            return "overview"
        elif is_closeup_val is None and ratio is not None:
            return "kanrichi"
    except Exception as e:
        logging.warning(f"judge_caption_board_closeup error: {e}")
    return None

# 出来形種別→remarks対応を一元管理
type_to_remarks = {
    "closeup": "出来形接写",
    "overview": "出来形全景",
    "kanrichi": "出来形管理値",
}

def get_dekigata_remarks_by_type(closeup_type, mapping):
    """
    closeup_typeに応じて該当remarksリストを返す
    remarks名に部分一致（例: "接写"・"全景"・"管理値"）や末尾キーワード一致も許容
    """
    remarks_name = type_to_remarks.get(closeup_type)
    print(f"[DEBUG] get_dekigata_remarks_by_type: remarks_name={remarks_name}, mapping_keys={list(mapping.keys())}")
    if remarks_name is None:
        return []
    # 完全一致
    exact = [r for r in mapping if r == remarks_name]
    if exact:
        return exact
    # remarks_name全体で部分一致
    partial = [r for r in mapping if remarks_name in r]
    if partial:
        return partial
    # 末尾キーワード（例: "接写"・"全景"・"管理値"）で部分一致
    for kw in ["接写", "全景", "管理値"]:
        if remarks_name.endswith(kw):
            tail = kw
            tail_match = [r for r in mapping if r.endswith(tail)]
            if tail_match:
                return tail_match
    return []

def classify_dekigata_caption_board(img_json, mapping):
    print(f"[DEBUG] classify_dekigata_caption_board: roles={img_json.get('roles')}, bboxes={img_json.get('bboxes')}")
    has_cb = has_caption_board(img_json)
    print(f"[DEBUG] has_caption_board: {has_cb}")
    if not has_cb:
        return []
    closeup_type = detect_caption_board_type(img_json)
    print(f"[DEBUG] detect_caption_board_type: {closeup_type}")
    remarks = get_dekigata_remarks_by_type(closeup_type, mapping)
    print(f"[DEBUG] get_dekigata_remarks_by_type: {remarks}")
    return remarks

def judge_dekigata_records(record):
    """
    record: ChainRecord/dict（roles, bboxes, img_w, img_h, remarks, photo_category などを含む）
    戻り値: [record] or []
    """
    bboxes = record.get('bboxes') if isinstance(record, dict) else getattr(record, 'bboxes', None)
    if not bboxes or not any(b.get('role') == 'caption_board' for b in bboxes):
        return []
    closeup_type = detect_caption_board_type(record)
    remarks = record.get('remarks') if isinstance(record, dict) else getattr(record, 'remarks', None)
    remarks_kw = type_to_remarks.get(closeup_type)
    if remarks_kw and remarks and remarks_kw.replace("出来形", "") in remarks:
        return [record]
    return []
