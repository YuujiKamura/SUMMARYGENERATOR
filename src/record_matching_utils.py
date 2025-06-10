# remarks（辞書）マッピング関連ユーティリティ

import os
import logging
from src.dekigata_judge import judge_dekigata_records
from src.image_entry import ImageEntry
from src.thermometer_utils import process_thermometer_records


def is_thermometer_image(roles):
    """画像が温度計ロールを含むか判定。"""
    return any(r and ("温度計" in r or "thermometer" in r) for r in roles)


def is_thermometer_or_caption_board_image(roles):
    """画像が温度計またはキャプションボードロールを含むか判定。"""
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
    """
    通常ロールマッチング: record(roles)とmapping, recordsからマッチしたレコードリストを返す
    record: ChainRecord/dict（roles属性/キー必須）
    mapping: remarks→dict（roles, match, ...）
    records: ChainRecord/dictリスト
    戻り値: [ChainRecord/dict, ...]
    """
    if hasattr(record, 'roles'):
        roles = record.roles
    elif isinstance(record, dict) and 'roles' in record:
        roles = record['roles']
    else:
        roles = []
    if roles is None:
        roles = []
    matched = []
    for r in records:
        entry = mapping.get(getattr(r, 'remarks', None) if hasattr(r, 'remarks') else r.get('remarks', None), {})
        entry_roles = entry.get("roles", [])
        match_type = entry.get("match", "all")
        if not entry_roles:
            continue
        if match_type == "all":
            # entry_rolesの全てがrolesに含まれる場合のみ
            if all(role in roles for role in entry_roles) and len(entry_roles) > 0:
                matched.append(r)
        else:
            # entry_rolesのいずれかがrolesに含まれる場合
            if any(role in roles for role in entry_roles):
                matched.append(r)
    return matched


# --- 旧stringベースAPIは廃止 ---
# match_roles_to_remarks, match_image_to_remarks, get_matched_remarks, match_normal_roles, match_priority_roles, match_dekigata_roles
# はすべてrecord/dictベースAPIに統一

# record/dictベースAPIのみ残す

# match_record_roles_to_remarks → match_roles_records にリネーム

def ensure_img_size(img_json):
    """
    img_jsonにimg_w/img_hがなければimage_pathから自動取得して補完
    """
    # --- ここでlistが来た場合はdictのlistなら先頭要素、空listや不正ならdict({})を返す ---
    if isinstance(img_json, list):
        if len(img_json) > 0 and isinstance(img_json[0], dict):
            img_json = img_json[0]
        else:
            # 空リストや不正な場合は空dictで返す（エラーで止めない）
            img_json = {}
    if img_json.get("img_w") is None or img_json.get("img_h") is None:
        img_path = img_json.get("image_path")
        if img_path and os.path.exists(img_path):
            try:
                from PIL import Image
                with Image.open(img_path) as im:
                    img_json["img_w"], img_json["img_h"] = im.width, im.height
            except Exception as e:
                print(
                    "[WARN] 画像サイズ取得失敗: {} {}".format(
                        img_path, e
                    )
                )
    return img_json


def match_roles_records(img_json: dict, mapping: dict, records: list, is_closeup=None) -> list:
    """
    img_json（1画像分のキャッシュJSON/dict）とmapping, recordsリストを受けて、roles→remarksマッチング（出来形・温度管理含む）を行い、
    マッチしたremarksに該当するレコード（ChainRecord/dict）リストを返す。
    img_json: 1画像分のキャッシュJSON（rolesキー必須、かつ'image_path'キー必須）
    mapping: remarks→dict（roles, match, ...）
    records: ChainRecordまたはdictのリスト（remarksフィールド必須）
    is_closeup: 出来形判定用（必要なら）
    戻り値: [ChainRecord/dict, ...]
    ※ img_jsonには必ず'image_path'（画像ID）を含めること。
    """
    img_json = ensure_img_size(img_json)
    print("[DEBUG] image_path={}, img_w={}, img_h={}, roles={}".format(img_json.get('image_path'), img_json.get('img_w'), img_json.get('img_h'), img_json.get('roles')))
    roles = img_json.get('roles', [])
    # --- 温度管理写真のサイクルマッチング分岐を追加 ---
    if is_thermometer_image(roles):
        print('[DEBUG][match_roles_records] 温度管理写真検出: サイクルマッチングを適用')
        # 通常候補を取得
        candidates = match_normal_roles_records(img_json, mapping, records)
        # debug_log記録用ImageEntryを生成（呼び出し元でImageEntry化されるのでここはdictでOK）
        # process_thermometer_recordsはChainRecord/dictリストを返す
        selected = process_thermometer_records([candidates])
        # debug_logへの記録はprocess_thermometer_records側で行う
        return selected
    matched = match_normal_roles_records(img_json, mapping, records)
    logging.info(
        "[通常マッチ] roles={} → photo_category={}".format(
            getattr(img_json, 'roles', img_json.get('roles', [])),
            [getattr(r, 'photo_category', None) if hasattr(r, 'photo_category') else r.get('photo_category', None) for r in matched]
        )
    )
    def get_photo_category(r):
        return getattr(r, 'photo_category', None) if hasattr(r, 'photo_category') else r.get('photo_category', None)
    # --- 品質管理写真の特殊処理 ---
    if any(get_photo_category(r) == '品質管理写真' for r in matched):
        print('[DEBUG][match_roles_records] 品質管理写真が含まれているためspecial_hinshitsu_handlingを適用')
        return special_hinshitsu_handling(img_json, mapping, records)
    # "出来形管理" or "出来形管理写真" どちらも許容
    has_dekigata = any(get_photo_category(r) in ("出来形管理", "出来形管理写真") for r in matched)
    if matched:
        if has_dekigata:
            from src.dekigata_judge import classify_dekigata_caption_board
            # --- 追加: 出来形分岐時の詳細出力 ---
            print(
                "[DEBUG] 出来形分岐: matched件数={}, matched_remarks={}".format(
                    len(matched),
                    [getattr(r, 'remarks', None) for r in matched]
                )
            )
            print(
                "[DEBUG] 管理図ボードサイズ: img_w={}, img_h={}".format(
                    img_json.get('img_w'),
                    img_json.get('img_h')
                )
            )
            dekigata_remarks = classify_dekigata_caption_board(img_json, mapping)
            print(
                "[DEBUG] classify_dekigata_caption_board → {}".format(
                    dekigata_remarks
                )
            )
            print(
                "[DEBUG] records内remarks → {}".format(
                    [getattr(r, 'remarks', None) for r in records]
                )
            )
            # remarksが複数でも全て採用
            if dekigata_remarks:
                filtered = [r for r in records if (getattr(r, 'remarks', None) or r.get('remarks')) in dekigata_remarks]
                print(f"[DEBUG] filtered: {[getattr(r, 'remarks', None) for r in filtered]}")
                if filtered:
                    print(
                        "[DEBUG] 最終選択: remarks={}, photo_category={}".format(
                            [getattr(f, 'remarks', None) for f in filtered],
                            [getattr(f, 'photo_category', None) for f in filtered]
                        )
                    )
                    return filtered
                else:
                    print(f"[DEBUG] dekigata_remarksに該当するレコードが見つかりませんでした")
            else:
                print(f"[DEBUG] classify_dekigata_caption_boardが空を返しました")
            return []
        return matched
    print(f"[DEBUG] matchedが空です")
    return []


def match_priority_roles_records(record, mapping, records):
    """
    優先ロールマッチング: record(roles)とmapping, recordsからマッチしたレコードリストを返す
    record: ChainRecord/dict（roles属性/キー必須）
    mapping: remarks→dict（roles, match, ...）
    records: ChainRecord/dictリスト
    戻り値: [ChainRecord/dict, ...]
    """
    PRIORITY_ROLES = [
        "role_measurer_thermometer",
        "caption_board_thermometer",
    ]
    if hasattr(record, 'roles'):
        roles = record.roles
    elif isinstance(record, dict) and 'roles' in record:
        roles = record['roles']
    else:
        roles = []
    found_priority_roles = set(PRIORITY_ROLES) & set(roles)
    if found_priority_roles:
        matched = []
        for r in records:
            entry = mapping.get(getattr(r, 'remarks', None) if hasattr(r, 'remarks') else r.get('remarks', None), {})
            entry_roles = entry.get("roles", [])
            if set(entry_roles) & found_priority_roles:
                matched.append(r)
        return matched
    return []


def match_roles_records_one_stop(img_json, role_mapping, records, image_path=None, json_path=None):
    print(f"[DEBUG][match_roles_records_one_stop] image_path={image_path}")
    print(f"[DEBUG][match_roles_records_one_stop] roles={img_json.get('roles')}")
    print(f"[DEBUG][match_roles_records_one_stop] role_mapping={role_mapping}")
    print(f"[DEBUG][match_roles_records_one_stop] records={records}")
    img_roles = set(img_json.get('roles', []) or [])
    bboxes = img_json.get('bboxes', []) or []
    bbox_roles = set([b.get('role') for b in bboxes if b.get('role')])
    all_roles = img_roles | bbox_roles
    # 'soil_thickness'を含むロールが1つでもあれば特別判定
    if any('soil_thickness' in r for r in all_roles):
        print('[DEBUG][match_roles_records_one_stop] soil_thicknessロール検出: 特別処理で砕石厚測定レコードのみ返す')
        saishaku_records = [r for r in records if (getattr(r, 'remarks', None) == '砕石厚測定') or (isinstance(r, dict) and r.get('remarks') == '砕石厚測定')]
        entry = ImageEntry(
            image_path=image_path or img_json.get('image_path', ''),
            json_path=json_path or img_json.get('json_path', ''),
            chain_records=saishaku_records,
            location=img_json.get('location', None),
            debug_text=img_json.get('debug_text', None)
        )
        entry.debug_log.append('[match_roles_records_one_stop] soil_thickness特別処理: 砕石厚測定レコードのみ返却')
        return entry
    # 通常マッチングのみ
    matched_records = _original_match_roles_records_one_stop(img_json, role_mapping, records)
    if matched_records is None:
        matched_records = []
    entry = ImageEntry(
        image_path=image_path or img_json.get('image_path', ''),
        json_path=json_path or img_json.get('json_path', ''),
        chain_records=matched_records,
        location=img_json.get('location', None),
        debug_text=img_json.get('debug_text', None)
    )
    # マッチング経緯をdebug_logに記録
    entry.debug_log.append("[match_roles_records_one_stop] roles={} → matched_remarks={}".format(list(all_roles), [getattr(r, 'remarks', None) for r in matched_records]))
    return entry


def _original_match_roles_records_one_stop(img_json, role_mapping, records):
    print(
        "[DEBUG][_original_match_roles_records_one_stop] img_json={}"
        .format(img_json)
    )
    print(f"[DEBUG][_original_match_roles_records_one_stop] role_mapping={role_mapping}")
    print(f"[DEBUG][_original_match_roles_records_one_stop] records={records}")
    # 本来のマッチングロジックを呼び出す
    return match_roles_records(img_json, role_mapping, records)


def special_hinshitsu_handling(record, mapping, records):
    """
    品質管理特別処理: 温度管理用サイクルマッチングロジックでレコード単位で割り当て
    """
    # 通常マッチ候補
    candidates = match_normal_roles_records(record, mapping, records)
    # サイクルマッチング（温度管理と同じロジック）
    # 1画像分のレコードリストをリスト化して渡す
    # recordがImageEntryならリストで渡す
    debug_entries = [record] if hasattr(record, 'debug_log') else None
    selected = process_thermometer_records([candidates], debug_entries=debug_entries)
    # process_thermometer_recordsはリストで返すので、1件目のみ返す
    # --- debug_logに詳細を記録 ---
    if hasattr(record, 'debug_log'):
        record.debug_log.append(f"[品質管理特殊処理] 通常候補: {[getattr(r, 'remarks', None) for r in candidates]}")
        if selected and selected[0] is not None:
            rec = selected[0]
            record.debug_log.append(f"[品質管理特殊処理] サイクルマッチングでアサイン: remarks={getattr(rec, 'remarks', None)} photo_category={getattr(rec, 'photo_category', None)}")
        else:
            record.debug_log.append("[品質管理特殊処理] サイクルマッチングでアサインなし")
    return [selected[0]] if selected and selected[0] is not None else []
