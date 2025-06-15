from typing import Any, Iterable, Optional, List, Tuple, Dict

try:
    from .records import Record
except ImportError:
    from records import Record

def get_match_val(record: Any) -> str:
    if isinstance(record, dict):
        return str(record.get('match', 'any')).strip().lower()
    if hasattr(record, 'match'):
        return str(getattr(record, 'match', 'any')).strip().lower()
    return 'any'

def get_criteria(record: Any) -> List[str]:
    """
    criteria フィールドが無い場合でも安全に動作するように改良。
    優先順位は以下の通り。

    1. record['criteria'] または record.criteria が存在すればそれを使用
    2. record['roles'] / record.roles が存在すればそれを使用
    3. ChainRecord 互換オブジェクトの場合は work_category / type / subtype / extra の文字列を候補に使用

    どのケースでも、返り値は小文字化された文字列リストとなる。
    """

    # --- dict 型 ---
    if isinstance(record, dict):
        if 'criteria' in record and record['criteria']:
            criteria = record['criteria']
        elif 'roles' in record and record['roles']:
            criteria = record['roles']
        else:
            # work_category/type/subtype などを補助的に利用
            candidates = []
            for key in ('work_category', 'type', 'subtype'):
                if key in record and record[key]:
                    candidates.append(str(record[key]))
            # extra(dict) 内の文字列値も追加
            extra = record.get('extra') or {}
            if isinstance(extra, dict):
                for v in extra.values():
                    if isinstance(v, str):
                        candidates.append(v)
                    elif isinstance(v, list):
                        candidates.extend([str(x) for x in v])
            criteria = candidates
    else:
        # --- オブジェクト型 ---
        if hasattr(record, 'criteria') and getattr(record, 'criteria'):
            criteria = getattr(record, 'criteria')
        elif hasattr(record, 'roles') and getattr(record, 'roles'):
            criteria = getattr(record, 'roles')
        else:
            # ChainRecord を想定
            candidates = []
            for attr in ('work_category', 'type', 'subtype'):
                if hasattr(record, attr):
                    val = getattr(record, attr)
                    if val:
                        candidates.append(str(val))
            # extra(dict) の文字列値
            if hasattr(record, 'extra'):
                extra = getattr(record, 'extra') or {}
                if isinstance(extra, dict):
                    for v in extra.values():
                        if isinstance(v, str):
                            candidates.append(v)
                        elif isinstance(v, list):
                            candidates.extend([str(x) for x in v])
            criteria = candidates

    # いずれの方法でも criteria が文字列 or リストになるよう保証
    if isinstance(criteria, str):
        return [criteria.strip().lower()]
    elif isinstance(criteria, (list, tuple, set)):
        return [str(c).strip().lower() for c in criteria if c]
    else:
        # 不明な型は空リスト
        return []

def match_record_to_roles(record: Any, roles: Iterable[str]) -> Tuple[bool, List[str]]:
    criteria = get_criteria(record)
    roles_norm = {r.strip().lower() for r in roles if r}
    if not criteria:
        return False, []
    found = list({c for c in criteria if c in roles_norm})
    match_val = get_match_val(record)
    if match_val.isdigit():
        result = len(found) >= int(match_val)
    elif match_val == 'any':
        result = len(found) > 0
    elif match_val == 'all':
        result = all(c in roles_norm for c in criteria)
    else:
        result = False
    return result, found

def collect_match_candidates(records: List[Any], roles: Iterable[str]) -> List[Tuple[Any, List[str], str]]:
    candidates: List[Tuple[Any, List[str], str]] = []
    for rec in records:
        ok, found = match_record_to_roles(rec, roles)
        if ok:
            match_val = get_match_val(rec)
            candidates.append((rec, found, match_val))
    return candidates

def select_best_match(candidates: List[Tuple[Any, List[str], str]]) -> Optional[Tuple[Any, List[str], str]]:
    # found数最大、同数なら最初
    return max(candidates, key=lambda x: len(x[1]), default=None)

def match_images_and_records_normal(records, image_roles, formatter=None):
    """
    画像ごとにfound数最大のものだけを返す
    戻り値: [(img_path, record, found, match_val, formatted)]
    """
    results = []
    for img_path, roles in image_roles.items():
        candidates = collect_match_candidates(records, roles)
        best = select_best_match(candidates)
        if best:
            record, found, match_val = best
            formatted = formatter(record, found, match_val) if formatter else str((record, found, match_val))
            results.append((img_path, record, found, match_val, formatted))
    return results

def extract_temp_records(q_list):
    """
    q_listから温度管理レコード(remarks, number, record)のリストを返す。number昇順、なければremarks昇順。
    remarksに「温度測定」または「温度」が含まれていれば抽出。
    """
    temp_records = []
    for _, record, _, _, _ in q_list:
        remarks = record.get_remarks()
        number = record.get_number()
        if remarks and ('温度測定' in remarks or '温度' in remarks):
            temp_records.append((number, remarks, record))
    temp_records.sort(key=lambda x: (x[0] if x[0] is not None else '', x[1]))
    return temp_records

def extract_temp_records_from_all(records):
    """
    全レコードから温度管理レコード(remarks, number, record)のリストを返す。number昇順、なければremarks昇順。
    remarksに「温度測定」または「温度」が含まれていれば抽出。
    """
    temp_records = []
    for record in records:
        if hasattr(record, 'get_remarks'):
            remarks = record.get_remarks()
            number = record.get_number()
        elif isinstance(record, dict):
            remarks = record.get('remarks', record['key'][4] if 'key' in record else '')
            number = record.get('number', record['key'][3] if 'key' in record else None)
        else:
            remarks = getattr(record, 'remarks', '')
            number = getattr(record, 'number', None)
        if remarks and ('温度測定' in remarks or '温度' in remarks):
            temp_records.append((number, remarks, record))
    temp_records.sort(key=lambda x: (x[0] if x[0] is not None else '', x[1]))
    return temp_records

def make_temp_assign_order(n, temp_records):
    """
    割り当て数nと温度管理レコードリストから、割り当てるremarks順リストを返す。
    """
    open_temp = [r for r in temp_records if '開放温度' in r[1]]
    main_temp = [r for r in temp_records if '開放温度' not in r[1]]
    assign_order = []
    if not main_temp and not open_temp:
        assign_order = [''] * n  # フォールバック: 空文字
    elif n > 3 and main_temp:
        main_n = n - 3
        for i in range(main_n):
            temp_idx = (i // 3) % len(main_temp)
            assign_order.append(main_temp[temp_idx])
        assign_order += [open_temp[0] if open_temp else main_temp[0]] * 3 if (open_temp or main_temp) else [None] * 3
    else:
        if open_temp or main_temp:
            assign_order = [open_temp[0] if open_temp else main_temp[0]] * n
        else:
            assign_order = [None] * n
    return assign_order

def find_record_by_remarks(q_list, target_remarks):
    """
    q_listからremarksが一致するレコードタプル(img_path, record, found, match_val, formatted)を返す。
    """
    for t in q_list:
        record = t[1]
        remarks = record.get_remarks()
        if remarks == target_remarks:
            return t
    return None

def assign_qc_temperature_records(q_list, all_records=None):
    """
    品質管理写真のリストに対し、3枚ごとに温度管理レコード（remarksやナンバー順）で割り当てる。
    all_recordsが与えられた場合はそこから温度管理レコードを抽出して使う。
    純粋関数（新リストを返す）。
    """
    if all_records is not None:
        temp_records = extract_temp_records_from_all(all_records)
    else:
        temp_records = extract_temp_records(q_list)
    assign_order = make_temp_assign_order(len(q_list), temp_records)
    new_q_list = []
    for i, (img_path, record, found, match_val, formatted) in enumerate(q_list):
        target_remarks = assign_order[i]
        rec = next((r[2] for r in temp_records if r[1] == target_remarks), record)
        new_q_list.append((img_path, rec, found, match_val, formatted))
    return new_q_list

def collect_temp_management_candidates(records: List[Any], image_roles: Dict[str, List[str]], img_paths: Optional[List[str]] = None) -> List[Any]:
    temp_records = []
    paths = img_paths if img_paths is not None else list(image_roles.keys())
    for img_path in paths:
        roles = image_roles[img_path]
        candidates = collect_match_candidates(records, roles)
        temp_candidates = [rec for rec, _, _ in candidates if any(k in rec.get_remarks() for k in ('温度管理', '温度測定', '温度'))]
        temp_records.extend(temp_candidates)
    # 重複除去
    seen = set()
    unique_temp_records = []
    for rec in temp_records:
        key = (rec.get_number(), rec.get_remarks())
        if key not in seen:
            seen.add(key)
            unique_temp_records.append(rec)
    return unique_temp_records

def assign_qc_temperature_records_with_candidates(q_list, records, image_roles, formatter=None):
    """
    品質管理写真の温度管理レコード割り当て。
    - 到着温度3枚→敷均し温度3枚→初期締固前温度3枚→末尾3枚は必ず開放温度
    この仕様を厳格に守る。
    """
    img_paths = list(dict.fromkeys(img_path for img_path, *_ in q_list))
    n = len(img_paths)
    # 温度管理レコードをremarksで分類
    temp_records = [r[2] for r in extract_temp_records_from_all(records)]
    def find_by_kw(key):
        for r in temp_records:
            if hasattr(r, 'get_remarks'):
                remarks = r.get_remarks()
            elif isinstance(r, dict):
                remarks = r.get('remarks', r['key'][4] if 'key' in r else '')
            else:
                remarks = getattr(r, 'remarks', '')
            if key in remarks:
                return r
        return None
    rec_arrival = find_by_kw('到着温度')
    rec_spread = find_by_kw('敷均し温度')
    rec_precomp = find_by_kw('初期締固前温度')
    rec_open = find_by_kw('開放温度')
    # 割当順を厳格に作成
    assign_order = []
    main_n = max(0, n - 3)
    for i in range(main_n):
        if (i // 3) % 3 == 0:
            assign_order.append(rec_arrival)
        elif (i // 3) % 3 == 1:
            assign_order.append(rec_spread)
        else:
            assign_order.append(rec_precomp)
    # 末尾3枚は必ず開放温度
    for i in range(3):
        assign_order.append(rec_open)
    # 割当
    new_q_list = []
    for i, img_path in enumerate(img_paths):
        rec = assign_order[i] if i < len(assign_order) else None
        roles = image_roles[img_path]
        if rec is not None:
            result, found = match_record_to_roles(rec, roles)
            match_val = str(getattr(rec, 'match', 'any')).strip().lower()
            formatted = formatter(rec, found, match_val) if formatter else str((rec, found, match_val))
        else:
            result, found, match_val = False, [], 'none'
            formatted = 'NO RECORD'
        new_q_list.append((img_path, rec, found, match_val, formatted))
    return new_q_list

def group_results_by_photo_category(results):
    """
    マッチ結果リストをphoto_categoryごとにグルーピングして辞書で返す。
    {photo_category: [ (img_path, record, found, match_val, formatted), ... ] }
    """
    by_category = {}
    for img_path, record, found, match_val, formatted in results:
        if hasattr(record, 'get_category'):
            photo_category = record.get_category()
        elif isinstance(record, dict):
            photo_category = record.get('photo_category', '') or (record.get('key', [''])[0] if 'key' in record else '')
        else:
            photo_category = getattr(record, 'photo_category', '') or ''
        if photo_category not in by_category:
            by_category[photo_category] = []
        by_category[photo_category].append((img_path, record, found, match_val, formatted))
    return by_category

def match_images_and_records(records, image_roles, formatter=None):
    """
    マッチングフレームワーク関数。デフォルトはノーマルマッチングを呼び、photo_categoryごとにグルーピングして返す。
    品質管理写真だけは候補再抽出＆温度管理レコード割り当て直し。
    戻り値: {photo_category: [ (img_path, record, found, match_val, formatted), ... ] }
    """
    all_results = match_images_and_records_normal(records, image_roles, formatter=formatter)
    grouped = group_results_by_photo_category(all_results)
    if '品質管理写真' in grouped:
        grouped['品質管理写真'] = assign_qc_temperature_records_with_candidates(
            grouped['品質管理写真'], records, image_roles, formatter=formatter)
    return grouped
