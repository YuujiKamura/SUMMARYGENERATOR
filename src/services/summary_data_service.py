"""
SummaryDataService: サマリー生成用のデータサービス
"""
from src.utils.image_list_utils import filter_and_sort_entries
from src.utils.summary_generator import match_image_to_records
from src.utils.records_loader import load_records_from_json
from pathlib import Path
from src.utils.chain_record_utils import ChainRecord
from src.utils.image_entry import ImageEntry, ImageEntryList
from typing import Optional, Callable, List, Dict, Any
import logging
from collections import defaultdict

def is_thermometer_entry(entry):
    # rolesまたはbboxesに温度計ロールが含まれているか判定
    roles = getattr(entry, 'roles', []) if hasattr(entry, 'roles') else []
    if not roles and hasattr(entry, 'cache_json') and entry.cache_json:
        if 'roles' in entry.cache_json:
            roles = entry.cache_json['roles']
        elif 'bboxes' in entry.cache_json:
            roles = [b.get('role') for b in entry.cache_json['bboxes'] if b.get('role')]
    return any(r and ("温度計" in r or "thermometer" in r) for r in roles)

class SummaryDataService:
    """
    サマリー生成用のデータサービス。画像リスト・マッチング・カテゴリ抽出等を担当。
    """
    def __init__(self, dictionary_manager: Optional[Any] = None, cache_dir: Optional[str] = None, records_path: Optional[str] = None, settings_manager: Optional[Any] = None, role_mapping: Optional[dict] = None):
        self.dictionary_manager = dictionary_manager
        self.settings_manager = settings_manager
        self.cache_dir = cache_dir
        self.records_path = records_path
        self.role_mapping = role_mapping
        self.all_entries: List[ImageEntry] = []
        self.remarks_to_chain_record: Dict[str, ChainRecord] = {}
        self.image_roles: Dict[str, Dict[str, str]] = {}
        self.load_initial_data()

    def load_initial_data(self):
        if self.dictionary_manager:
            all_records = self.dictionary_manager.records
            if all_records:
                self.remarks_to_chain_record = {
                    record.remarks: record
                    for record in all_records if hasattr(record, 'remarks') and record.remarks
                }

    def set_all_entries(self, entries: List[ImageEntry]):
        print(f"[DEBUG][set_all_entries] 呼び出し: entriesの長さ={len(entries)} id_list={[id(e) for e in entries]}")
        self.all_entries = entries
        for entry in entries:
            # テスト用debug_log書き込みを削除
            print(f"[DEBUG][set_all_entries] entry: image_path={getattr(entry, 'image_path', None)}, id={id(entry)}, debug_log={entry.debug_log}")
            print(f"[DEBUG][SummaryDataService] image_path={getattr(entry, 'image_path', None)}, id={id(entry)}, chain_records={[{'remarks': getattr(r, 'remarks', None), 'photo_category': getattr(r, 'photo_category', None)} for r in getattr(entry, 'chain_records', [])]}")
        # --- 温度計ロール画像群の抽出 ---
        thermometer_entries = [e for e in entries if is_thermometer_entry(e)]
        # ファイル名昇順（古い順）でソート
        thermometer_entries.sort(key=lambda e: e.image_path or "")
        print(f"[DEBUG][set_all_entries] thermometer_entries(sorted): {[getattr(e, 'image_path', None) for e in thermometer_entries]}")
        if thermometer_entries:
            print(f"[DEBUG][SummaryDataService] 温度計ロール画像群: {len(thermometer_entries)}件 サイクルマッチング開始")
            from src.utils.thermometer_utils import process_thermometer_records
            # 各ImageEntryの通常候補を再取得
            candidates_list = [self.get_remarks_for_entry(e) for e in thermometer_entries]
            print(f"[DEBUG][set_all_entries] candidates_list lens: {[len(c) for c in candidates_list]}")
            print(f"[DEBUG][set_all_entries] candidates_list remarks: {[[getattr(r, 'remarks', None) for r in c] for c in candidates_list]}")
            print(f"[DEBUG][set_all_entries] debug_entries lens: {len(thermometer_entries)}")
            print(f"[DEBUG][set_all_entries] debug_entries image_paths: {[getattr(e, 'image_path', None) for e in thermometer_entries]}")
            # 一括でサイクルマッチング
            cycled_records = process_thermometer_records(candidates_list, debug_entries=thermometer_entries)
            print(f"[DEBUG][set_all_entries] cycled_records: {[getattr(r, 'remarks', None) if r else None for r in cycled_records]}")
            # サイクルマッチング結果を各ImageEntryに反映
            group_debug_log = []
            for idx, (e, rec) in enumerate(zip(thermometer_entries, cycled_records)):
                if rec is not None:
                    e.chain_records = [rec]
                    log_msg = f"[サイクルマッチング] idx={idx} remarks={getattr(rec, 'remarks', None)} photo_category={getattr(rec, 'photo_category', None)} → アサイン"
                    e.debug_log.append(log_msg)
                    group_debug_log.append(f"{e.image_path}: {log_msg}")
                else:
                    log_msg = f"[サイクルマッチング] idx={idx} → アサインなし"
                    e.debug_log.append(log_msg)
                    group_debug_log.append(f"{e.image_path}: {log_msg}")
            print("[DEBUG][SummaryDataService] 温度計サイクルマッチング詳細:")
            for line in group_debug_log:
                print("  ", line)
            # if hasattr(self, 'thermometer_group') and self.thermometer_group:
            #     self.thermometer_group.debug_log.extend(group_debug_log)
            print(f"[DEBUG][SummaryDataService] サイクルマッチング結果反映完了")
        # --- ここで全ImageEntryのdebug_logをprint ---
        print("[DEBUG][set_all_entries] return直前: entriesのdebug_log一覧")
        for entry in entries:
            print(f"  image_path={getattr(entry, 'image_path', None)}, id={id(entry)}, debug_log={getattr(entry, 'debug_log', None)}")
        return

    def update_image_roles(self, image_path: str, roles: Dict[str, str]):
        self.image_roles[image_path] = roles

    def get_roles_for_image(self, image_path: str) -> Dict[str, str]:
        return self.image_roles.get(image_path, {})

    def get_categories(self, entries, match_results):
        """
        画像リスト・マッチ結果からカテゴリ一覧を返す
        """
        records = getattr(self.dictionary_manager, 'records', []) if self.dictionary_manager and hasattr(self.dictionary_manager, 'records') else []
        remarks_to_category = {
            getattr(r, 'remarks', None): getattr(r, 'photo_category', '')
            for r in records if getattr(r, 'remarks', None)
        }
        sorted_entries, debug_lines = filter_and_sort_entries(
            entries, match_results, remarks_to_category, None, True
        )

        # remarks_to_category からカテゴリ一覧を抽出
        all_categories = set(remarks_to_category.values())
        # 固定カテゴリの例（必要に応じて調整）
        fixed_categories = [cat for cat in all_categories if cat in ("未分類", "その他", "不明")]  # 例
        categories = [cat for cat in all_categories if cat not in fixed_categories]
        # 必ずタプルで返す
        return fixed_categories, categories

    def get_sorted_entries(self, entries, match_results, selected_cat, ascending):
        """
        カテゴリ・ソート順で画像リストを並べ替え
        """
        records = getattr(self.dictionary_manager, 'records', []) if self.dictionary_manager and hasattr(self.dictionary_manager, 'records') else []
        remarks_to_category = {
            getattr(r, 'remarks', None): getattr(r, 'photo_category', '')
            for r in records if getattr(r, 'remarks', None)
        }
        sorted_entries, debug_lines = filter_and_sort_entries(
            entries, match_results, remarks_to_category, selected_cat, ascending
        )
        return sorted_entries, debug_lines

    def get_match_results(self, entries, role_mapping, remarks_to_chain_record, debug_callback=None):
        """
        画像リストからマッチング結果を取得（role_mapping, remarks_to_chain_recordはDIで明示的に渡す）
        """
        image_json_dict = {}
        for e in entries:
            roles = getattr(e, 'roles', None)
            if not roles or not isinstance(roles, list):
                roles = []
                if hasattr(e, 'cache_json') and e.cache_json and 'bboxes' in e.cache_json:
                    for b in e.cache_json['bboxes']:
                        if 'role' in b and b['role']:
                            roles.append(b['role'])
            if debug_callback:
                debug_callback(getattr(e, 'image_path', None), f"[get_match_results] roles: {roles}")
            
            # match_image_to_recordsが期待する形式でimg_jsonを構築
            img_json = {
                'image_path': e.path,
                'roles': roles
            }
            # cache_jsonから追加情報を取得（あれば）
            if hasattr(e, 'cache_json') and e.cache_json:
                img_json.update({
                    'img_w': e.cache_json.get('img_w'),
                    'img_h': e.cache_json.get('img_h'),
                    'bboxes': e.cache_json.get('bboxes', [])
                })
            
            image_json_dict[e.path] = img_json
        # --- ロールマッピングのロード詳細をデバッグコールバックに流す ---
        mapping_debug_lines = []
        if role_mapping:
            mapping_debug_lines.append(f"[ロールマッピング] 正常ロード: 件数={len(role_mapping)} keys={list(role_mapping.keys())[:5]}{' ...' if len(role_mapping)>5 else ''}")
        else:
            mapping_debug_lines.append(f"[ロールマッピング] ロード失敗 or 空")
        if debug_callback:
            for line in mapping_debug_lines:
                debug_callback('role_mapping', line)
        # match_results = match_image_to_remarks(
        #     image_roles, role_mapping, self.cache_dir, records_path=self.records_path, debug_callback=debug_callback
        # )        from summarygenerator.utils.summary_generator import match_image_to_records
        from src.utils.chain_record_utils import find_chain_records_by_roles
        records = getattr(self.dictionary_manager, 'records', [])
        match_results = match_image_to_records(image_json_dict, records)
        return match_results

    def get_remarks_for_entry(self, entry: 'ImageEntry', debug_callback: Optional[Callable[[str, str], None]] = None) -> List[ChainRecord]:
        def _debug(msg):
            if debug_callback and entry and hasattr(entry, 'image_path') and entry.image_path:
                debug_callback(entry.image_path, msg)
        if not entry or not hasattr(entry, 'image_path') or not entry.image_path:
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
            _debug(f"[get_remarks_for_entry] No roles determined for {entry.image_path}. Cannot match ChainRecords.")
            return []
        records = getattr(self.dictionary_manager, 'records', []) if self.dictionary_manager else []
        from src.utils.chain_record_utils import find_chain_records_by_roles
        matched_records = find_chain_records_by_roles(current_image_roles, records)
        _debug(f"[get_remarks_for_entry] Matched ChainRecords: {[r.remarks for r in matched_records]}")
        return matched_records

    def get_photo_category_from_remarks(self, remarks: str) -> str:
        rec = self.remarks_to_chain_record.get(remarks)
        return rec.photo_category if rec and hasattr(rec, 'photo_category') and rec.photo_category is not None else ''

    def get_chain_records_for_image(self, img_path: str) -> list:
        roles = []
        if hasattr(self, 'image_roles') and img_path in self.image_roles:
            val = self.image_roles[img_path]
            if isinstance(val, dict):
                roles = list(val.values())
            elif isinstance(val, list):
                roles = val
        records = getattr(self.dictionary_manager, 'records', []) if self.dictionary_manager else []
        from src.utils.chain_record_utils import find_chain_records_by_roles
        return find_chain_records_by_roles(roles, records)

    def get_image_entry_for_image(self, img_path: str) -> Optional[ImageEntry]:
        """
        画像パスからImageEntryを返す。all_entriesに存在しなければNone。
        """
        for entry in self.all_entries:
            if hasattr(entry, 'image_path') and entry.image_path == img_path:
                return entry
        return None