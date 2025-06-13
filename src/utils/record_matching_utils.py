# --- Copied from src/record_matching_utils.py ---
import os
import logging
from .dekigata_judge import judge_dekigata_records
from .image_entry import ImageEntry
from .thermometer_utils import process_thermometer_records
from .role_mapping_utils import normalize_role_name

def is_thermometer_image(roles):
    return any(r and ("温度計" in r or "thermometer" in r) for r in roles)

def is_thermometer_or_caption_board_image(roles):
    return any(r and ("温度計" in r or "thermometer" in r or "caption_board" in r) for r in roles)

def match_priority_roles(roles, mapping):
    PRIORITY_ROLES = [
        "role_measurer_thermometer",
        "caption_board_thermometer",
    ]
    found_priority_roles = set(PRIORITY_ROLES) & set(roles)
    if found_priority_roles:
        matched_remarks = []
        for remarks, entry in mapping.items():
            entry_roles = entry.get("roles", [])
            if set(entry_roles) & found_priority_roles:
                matched_remarks.append(remarks)
        logging.debug(f"[match_priority_roles] 優先ロール一致: {found_priority_roles} → {matched_remarks}")
        return matched_remarks
    return []

def match_dekigata_roles(roles, mapping, is_closeup=None):
    is_dekigata = any("caption_board_dekigata" in r for r in roles)
    if is_dekigata:
        matched_remarks = judge_dekigata_records(roles, mapping, is_closeup)
        logging.debug(f"[match_dekigata_roles] 出来形判定: {matched_remarks}")
        return matched_remarks
    return []

def match_normal_roles_records(record, mapping, records):
    if hasattr(record, 'roles'):
        roles = record.roles
    elif isinstance(record, dict) and 'roles' in record:
        roles = record['roles']
    else:
        roles = []
    if roles is None:
        roles = []
    # ここでrolesを正規化
    norm_roles = set([normalize_role_name(r) for r in roles if r])
    matched = []
    for r in records:
        remarks = getattr(r, 'remarks', None) if hasattr(r, 'remarks') else r.get('remarks', None)
        if not remarks:
            continue
        norm_remarks = normalize_role_name(str(remarks))
        entry = mapping.get(norm_remarks, {})
        entry_roles = entry.get("roles", [])
        match_type = entry.get("match", "all")
        if not entry_roles:
            continue
        norm_entry_roles = set([normalize_role_name(er) for er in entry_roles if er])
        if match_type == "all":
            if norm_entry_roles and norm_entry_roles.issubset(norm_roles):
                matched.append(r)
        else:
            if norm_entry_roles & norm_roles:
                matched.append(r)
    return matched

def match_roles_records_one_stop(img_json, role_mapping, records, image_path=None, json_path=None):
    """
    img_json, role_mapping, recordsを受け取り、ImageEntryを返すワンストップAPI
    """
    img_roles = set(img_json.get('roles', []) or [])
    bboxes = img_json.get('bboxes', []) or []
    bbox_roles = set([b.get('role') for b in bboxes if b.get('role')])
    all_roles = img_roles | bbox_roles
    # soil_thickness特別判定
    if any('soil_thickness' in r for r in all_roles):
        saishaku_records = [r for r in records if (getattr(r, 'remarks', None) == '礫石厚測定') or (isinstance(r, dict) and r.get('remarks') == '礫石厚測定')]
        entry = ImageEntry(
            image_path=image_path or img_json.get('image_path', ''),
            json_path=json_path or img_json.get('json_path', ''),
            chain_records=saishaku_records,
            location=img_json.get('location', None),
            debug_text=img_json.get('debug_text', None)
        )
        entry.debug_log.append('[match_roles_records_one_stop] soil_thickness特別処理: 礫石厚測定レコードのみ返却')
        return entry
    # 通常マッチング
    matched_records = match_normal_roles_records(img_json, role_mapping, records)
    if matched_records is None:
        matched_records = []
    entry = ImageEntry(
        image_path=image_path or img_json.get('image_path', ''),
        json_path=json_path or img_json.get('json_path', ''),
        chain_records=matched_records,
        location=img_json.get('location', None),
        debug_text=img_json.get('debug_text', None),
        roles=list(all_roles)
    )
    entry.debug_log.append("[match_roles_records_one_stop] roles={} → matched_remarks={}".format(list(all_roles), [getattr(r, 'remarks', None) for r in matched_records]))
    return entry
