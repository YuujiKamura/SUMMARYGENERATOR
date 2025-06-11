import json

def generate_matching_debug_log(matched_records, entry, indent_level=0):
    """
    マッチング結果の詳細デバッグログを生成する（record, 各種ラベル, location等）
    indent_level: recordごとのインデントレベル
    Returns:
        debug_lines: strリスト
    """
    debug_lines = []
    indent = '  ' * indent_level
    if matched_records:
        for rec in matched_records:
            remarks = getattr(rec, 'remarks', None) if hasattr(rec, 'remarks') else rec.get('remarks', None)
            # ChainRecord型ならto_dictで辞書化
            if hasattr(rec, 'to_dict'):
                rec_dict = rec.to_dict()
            elif isinstance(rec, dict):
                rec_dict = rec
            else:
                rec_dict = str(rec)
            debug_lines.append(f"{indent}└ remarks: {remarks}")
            debug_lines.append(f"{indent}    [record] {json.dumps(rec_dict, ensure_ascii=False, default=str)}")
            work_category = rec_dict.get('work_category', rec_dict.get('category', '')) if isinstance(rec_dict, dict) else ''
            typ = rec_dict.get('type', '') if isinstance(rec_dict, dict) else ''
            subtyp = rec_dict.get('subtype', '') if isinstance(rec_dict, dict) else ''
            photo_cat = rec_dict.get('photo_category', '') if isinstance(rec_dict, dict) else ''
            location = getattr(entry, 'location', '')
            debug_line = f"{indent}    photo_category: {photo_cat} / work_category: {work_category} / type: {typ} / subtype: {subtyp} / remarks: {remarks} / location: {location}"
            debug_lines.append(debug_line)
    else:
        # --- NO MATCH時の出力を簡潔かつ有益に ---
        location = getattr(entry, 'location', '')
        roles = getattr(entry, 'roles', None)
        debug_lines.append(f"[NO MATCH] roles: {roles}  (location: {location})")
    return debug_lines