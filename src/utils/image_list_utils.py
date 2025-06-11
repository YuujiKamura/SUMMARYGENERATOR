import os

def normalize_category(cat):
    if not cat:
        return '未分類'
    cat = str(cat).strip()
    for std in ["施工状況写真", "出来形管理写真", "品質管理写真", "安全管理写真", "その他"]:
        if cat.startswith(std):
            return std
    return cat


def collect_categories(entries, match_results, remarks_to_category, fixed_categories):
    categories = set(fixed_categories)
    for e in entries:
        img_path = e.path
        matched_remarks = match_results.get(img_path, []) if match_results else []
        cat = None
        for remarks in matched_remarks:
            cat = normalize_category(remarks_to_category.get(remarks, ''))
            if cat and cat != '未分類':
                break
        if not cat or cat == '未分類':
            raw_cat = e.cache_json.get('photo_category') if e.cache_json else ''
            cat = normalize_category(raw_cat)
        if not cat:
            cat = '未分類'
        categories.add(cat)
    return categories


def filter_and_sort_entries(entries, match_results, remarks_to_category, selected_cat, order_ascending):
    filtered_entries = []
    debug_lines = []
    for e in entries:
        img_path = e.path
        matched_remarks = match_results.get(img_path, []) if match_results else []
        cat = None
        for remarks in matched_remarks:
            cat = normalize_category(remarks_to_category.get(remarks, ''))
            if cat and cat != '未分類':
                break
        if not cat or cat == '未分類':
            raw_cat = e.cache_json.get('photo_category') if e.cache_json else ''
            cat = normalize_category(raw_cat)
        if not cat:
            cat = '未分類'
        debug_lines.append(f"[filter] path={e.path} matched_remarks={matched_remarks} → cat='{cat}'")
        if selected_cat == "(全て)" or cat == selected_cat:
            filtered_entries.append(e)
            debug_lines.append(f"[filter]  → 選択cat='{selected_cat}'に含める")
        else:
            debug_lines.append(f"[filter]  → 選択cat='{selected_cat}'で除外")
    sorted_entries = sorted(filtered_entries, key=lambda e: os.path.getmtime(e.path) if os.path.exists(e.path) else 0, reverse=not order_ascending)
    return sorted_entries, debug_lines
