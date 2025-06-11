"""
SummaryDataService: サマリー生成用のデータサービス
"""
from src.utils.image_list_utils import filter_and_sort_entries
from src.utils.summary_generator import match_image_to_records
from src.utils.records_loader import load_records_from_json
from pathlib import Path
from src.utils.chain_record_utils import ChainRecord, find_chain_records_by_roles
from src.utils.image_entry import ImageEntry, ImageEntryList
from typing import Optional, Callable, List, Dict, Any
import logging
from collections import defaultdict
from src.db_manager import (
    ChainRecordManager, RoleMappingManager, ImageManager, BBoxManager,
    import_image_preview_cache_json, reset_all_tables
)
from src.utils.path_manager import PathManager
import json
from src.utils.thermometer_utils import process_thermometer_records
import os
import datetime
import hashlib

LOG_PATHS = {
    'S1_chain_records_and_role_mappings': os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs', 'S1_chain_records_and_role_mappings.log'),
    'S2_image_entries': os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs', 'S2_image_entries.log'),
    'S3_match_results': os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs', 'S3_match_results.log'),
}
_last_log_hash = {}
def step_log(label, data):
    path = LOG_PATHS[label]
    h = hashlib.md5(json.dumps(data, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()
    if _last_log_hash.get(label) == h:
        return
    _last_log_hash[label] = h
    with open(path, 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.datetime.now().isoformat()}] {label}\n")
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')

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
        # DBからChainRecord/ロールマッピングをロード
        all_records = [ChainRecord.from_dict(r) for r in ChainRecordManager.get_all_chain_records()]
        self.all_records = all_records
        self.role_mappings = {row['role_name']: json.loads(row['mapping_json']) for row in RoleMappingManager.get_all_role_mappings()}
        # S1: チェーンレコードとロールマッピングまとめてダンプ
        step_log('S1_chain_records_and_role_mappings', {
            'chain_records': [r.__dict__ for r in all_records],
            'role_mappings': self.role_mappings
        })
        if all_records:
            self.remarks_to_chain_record = {
                record.remarks: record
                for record in all_records if hasattr(record, 'remarks') and record.remarks
            }

    def set_all_entries(self, entries: List[ImageEntry]):
        print(f"[DEBUG][set_all_entries] 呼び出し: entriesの長さ={len(entries)} id_list={[id(e) for e in entries]}")
        self.all_entries = entries
        # S2: 画像リストDB登録結果
        step_log('S2_image_entries', [e.__dict__ for e in entries])
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
            if hasattr(self, 'thermometer_group') and self.thermometer_group:
                self.thermometer_group.debug_log.extend(group_debug_log)
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
        remarks_to_category = {
            getattr(r, 'remarks', None): getattr(r, 'photo_category', '')
            for r in self.dictionary_manager.records if getattr(r, 'remarks', None)
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
        remarks_to_category = {
            getattr(r, 'remarks', None): getattr(r, 'photo_category', '')
            for r in self.dictionary_manager.records if getattr(r, 'remarks', None)
        }
        sorted_entries, debug_lines = filter_and_sort_entries(
            entries, match_results, remarks_to_category, selected_cat, ascending
        )
        return sorted_entries, debug_lines

    def get_match_results(self, entries, role_mapping, remarks_to_chain_record, debug_callback=None):
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
                debug_callback(getattr(e, 'path', None), f"[get_match_results] roles: {roles}")
            img_json = {
                'image_path': e.path,
                'roles': roles
            }
            if hasattr(e, 'cache_json') and e.cache_json:
                img_json.update({
                    'img_w': e.cache_json.get('img_w'),
                    'img_h': e.cache_json.get('img_h'),
                    'bboxes': e.cache_json.get('bboxes', [])
                })
            image_json_dict[e.path] = img_json
        step_log('image_json_dict', image_json_dict)
        # DBからChainRecordを取得
        records = [ChainRecord.from_dict(r) for r in ChainRecordManager.get_all_chain_records()]
        step_log('chain_records_match', [r.__dict__ for r in records])
        match_results = match_image_to_records(image_json_dict, records)
        # S3: マッチング結果
        step_log('S3_match_results', match_results)
        return match_results

    def get_remarks_for_entry(self, entry: 'ImageEntry', debug_callback: Optional[Callable[[str, str], None]] = None) -> List[ChainRecord]:
        def _debug(msg):
            if debug_callback and entry and hasattr(entry, 'path') and entry.path:
                debug_callback(entry.path, msg)
        if not entry or not hasattr(entry, 'path') or not entry.path:
            if debug_callback:
                debug_callback("unknown_entry", "[get_remarks_for_entry] Invalid entry provided.")
            return []
        # rolesが空ならbboxesから抽出
        current_image_roles = entry.roles if hasattr(entry, 'roles') and entry.roles else []
        if (not current_image_roles or current_image_roles == {}) and hasattr(entry, 'cache_json') and entry.cache_json and 'bboxes' in entry.cache_json:
            current_image_roles = [b.get('role') for b in entry.cache_json['bboxes'] if b.get('role')]
            _debug(f"[get_remarks_for_entry] fallback roles from bboxes: {current_image_roles}")
        if not isinstance(current_image_roles, list):
            current_image_roles = []
        if not current_image_roles:
            _debug(f"[get_remarks_for_entry] No roles determined for {entry.path}. Cannot match ChainRecords.")
            return []
        # ChainRecordリストをrolesで直接フィルタ
        records = getattr(self.dictionary_manager, 'records', [])
        matched_records = find_chain_records_by_roles(current_image_roles, records)
        _debug(f"[get_remarks_for_entry] Matched ChainRecords: {[r.remarks for r in matched_records]}")
        return matched_records

    def get_photo_category_from_remarks(self, remarks: str) -> str:
        rec = self.remarks_to_chain_record.get(remarks)
        return rec.photo_category if rec else ''

    def get_chain_records_for_image(self, img_path: str) -> list:
        # 画像パスからrolesを取得し、ChainRecordリストを返す
        # 画像パス→rolesリストの取得方法はimage_rolesまたはcache_json等に応じて調整
        roles = []
        # image_rolesがdict[str, list[str]]形式で保持されている前提
        if hasattr(self, 'image_roles') and img_path in self.image_roles:
            roles = self.image_roles[img_path]
        # records取得
        records = getattr(self.dictionary_manager, 'records', [])
        return find_chain_records_by_roles(roles, records)

    def get_image_entry_for_image(self, img_path: str) -> Optional[ImageEntry]:
        """
        画像パスからImageEntryを返す。all_entriesに存在しなければNone。
        """
        for entry in self.all_entries:
            if hasattr(entry, 'image_path') and entry.image_path == img_path:
                return entry
        return None

    def import_chain_records_from_json(self, json_path=None):
        if json_path is None:
            pm = PathManager()
            json_path = pm.default_records
        records = load_records_from_json(json_path)
        for rec in records:
            ChainRecordManager.add_chain_record(
                location=rec.get('location'),
                controls=rec.get('controls'),
                photo_category=rec.get('photo_category'),
                work_category=rec.get('work_category'),
                type_=rec.get('type'),
                subtype=rec.get('subtype'),
                remarks=rec.get('remarks'),
                extra_json=json.dumps(rec, ensure_ascii=False)
            )

    def import_role_mappings_from_json(self, json_path=None):
        if json_path is None:
            pm = PathManager()
            json_path = pm.role_mapping
        with open(json_path, encoding='utf-8') as f:
            mappings = json.load(f)
        for role_name, mapping in mappings.items():
            if role_name.startswith('_'):  # コメント等はスキップ
                continue
            RoleMappingManager.add_or_update_role_mapping(role_name, json.dumps(mapping, ensure_ascii=False))

    def import_image_entries_from_json(self, json_path=None):
        if json_path is None:
            pm = PathManager()
            json_path = pm.image_preview_cache_master
        import_image_preview_cache_json(json_path=json_path)

    def reset_all_resources(self):
        reset_all_tables()
        self.import_chain_records_from_json()
        self.import_role_mappings_from_json()
        self.import_image_entries_from_json()