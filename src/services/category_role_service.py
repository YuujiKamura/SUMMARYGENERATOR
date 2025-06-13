"""
CategoryRoleService: カテゴリ・ロール関連の抽出・管理を担当
"""

from src.utils.chain_record_utils import find_chain_records_by_roles
from src.utils.image_list_utils import filter_and_sort_entries


class CategoryRoleService:
    def __init__(self):
        pass

    def get_categories(self, records):
        remarks_to_category = {
            getattr(r, 'remarks', None): getattr(r, 'photo_category', '')
            for r in records if getattr(r, 'remarks', None)
        }
        all_categories = set(remarks_to_category.values())
        fixed_categories = [cat for cat in all_categories if cat in ("未分類", "その他", "不明")]
        categories = [cat for cat in all_categories if cat not in fixed_categories]
        return fixed_categories, categories

    def get_sorted_entries(self, entries, match_results, selected_cat, ascending, records):
        remarks_to_category = {
            getattr(r, 'remarks', None): getattr(r, 'photo_category', '')
            for r in records if getattr(r, 'remarks', None)
        }
        sorted_entries, debug_lines = filter_and_sort_entries(
            entries, match_results, remarks_to_category, selected_cat, ascending
        )
        return sorted_entries, debug_lines

    def get_remarks_for_entry(self, entry, records, debug_callback=None):
        def _debug(msg):
            path = getattr(entry, 'path', None) or getattr(entry, 'image_path', None)
            if debug_callback and entry and path:
                debug_callback(path, msg)
        path = getattr(entry, 'path', None) or getattr(entry, 'image_path', None)
        if not entry or not path:
            if debug_callback:
                debug_callback("unknown_entry", "[get_remarks_for_entry] Invalid entry provided.")
            return []
        current_image_roles = entry.roles if hasattr(entry, 'roles') and entry.roles else []
        if (not current_image_roles or current_image_roles == {}) and hasattr(entry, 'cache_json') and entry.cache_json and 'bboxes' in entry.cache_json:
            current_image_roles = [b.get('role') for b in entry.cache_json['bboxes'] if b.get('role')]
            _debug(f"[get_remarks_for_entry] fallback roles from bboxes: {current_image_roles}")
        if not isinstance(current_image_roles, list):
            current_image_roles = []
        if not current_image_roles:
            _debug(f"[get_remarks_for_entry] No roles determined for {path}. Cannot match ChainRecords.")
            return []
        if isinstance(current_image_roles, dict):
            current_image_roles = list(current_image_roles.values())
        matched_records = find_chain_records_by_roles(current_image_roles, records)
        _debug(f"[get_remarks_for_entry] Matched ChainRecords: {[r.remarks for r in matched_records]}")
        return matched_records
