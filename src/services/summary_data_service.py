"""
SummaryDataService: サマリー生成用のデータサービス
"""
from src.utils.chain_record_utils import ChainRecord, find_chain_records_by_roles
from src.utils.image_entry import ImageEntry
from typing import Optional, Callable, List, Dict, Any
import logging
from src.db_manager import (
    ChainRecordManager, RoleMappingManager
)
import json
from src.services.db_resource_service import DBResourceService
from src.services.image_matching_service import ImageMatchingService
from src.services.category_role_service import CategoryRoleService
from src.dictionary_manager import DictionaryManager

def is_thermometer_entry(entry):
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
    ファサードとして各専用サービスに処理を委譲する。
    """
    def __init__(self, db_path=None, dictionary_manager: Optional[Any] = None, cache_dir: Optional[str] = None, records_path: Optional[str] = None, settings_manager: Optional[Any] = None, role_mapping: Optional[dict] = None):
        self.db_path = db_path
        self.db_resource_service = DBResourceService()
        self.image_matching_service = ImageMatchingService()
        self.category_role_service = CategoryRoleService()
        self.dictionary_manager = dictionary_manager or DictionaryManager(db_path)
        self.settings_manager = settings_manager
        self.cache_dir = cache_dir
        self.records_path = records_path
        self.role_mapping = role_mapping
        self.all_entries: List[ImageEntry] = []
        self.remarks_to_chain_record: Dict[str, ChainRecord] = {}
        self.image_roles: Dict[str, Dict[str, str]] = {}
        self.load_initial_data()
        self.full_initialize()

    def load_initial_data(self):
        all_records = [ChainRecord.from_dict(r) for r in ChainRecordManager.get_all_chain_records()]
        self.all_records = all_records
        self.role_mappings = {
            row['role_name']: json.loads(row['mapping_json']) if row['mapping_json'] else {}
            for row in RoleMappingManager.get_all_role_mappings()
        }
        if all_records:
            self.remarks_to_chain_record = {
                record.remarks: record
                for record in all_records if hasattr(record, 'remarks') and record.remarks
            }

    def set_all_entries(self, entries: List[ImageEntry]):
        logging.info(
            "[DEBUG][set_all_entries] 呼び出し: entriesの長さ=%d id_list=%s",
            len(entries), [id(e) for e in entries]
        )
        self.all_entries = entries
        for entry in entries:
            # logging.info(
            #     "[DEBUG][set_all_entries] entry: image_path=%s, id=%d, debug_log=%s",
            #     getattr(entry, 'image_path', None), id(entry), entry.debug_log
            # )
            # logging.info(
            #     "[DEBUG][SummaryDataService] image_path=%s, id=%d, chain_records=%s",
            #     getattr(entry, 'image_path', None), id(entry),
            #     [
            #         {'remarks': getattr(r, 'remarks', None),
            #          'photo_category': getattr(r, 'photo_category', None)}
            #         for r in getattr(entry, 'chain_records', [])
            #     ]
            # )
            pass
        thermometer_entries = [e for e in entries if is_thermometer_entry(e)]
        thermometer_entries.sort(key=lambda e: e.image_path or "")
        logging.info(
            "[DEBUG][set_all_entries] thermometer_entries(sorted): %s",
            [getattr(e, 'image_path', None) for e in thermometer_entries]
        )
        if thermometer_entries:
            logging.info(
                "[DEBUG][SummaryDataService] 温度計ロール画像群: %d件 サイクルマッチング開始",
                len(thermometer_entries)
            )
            candidates_list = [self.get_remarks_for_entry(e) for e in thermometer_entries]
            logging.info(
                "[DEBUG][set_all_entries] candidates_list lens: %s",
                [len(c) for c in candidates_list]
            )
            logging.info(
                "[DEBUG][set_all_entries] candidates_list remarks: %s",
                [[getattr(r, 'remarks', None) for r in c] for c in candidates_list]
            )
            logging.info(
                "[DEBUG][set_all_entries] debug_entries lens: %d",
                len(thermometer_entries)
            )
            logging.info(
                "[DEBUG][set_all_entries] debug_entries image_paths: %s",
                [getattr(e, 'image_path', None) for e in thermometer_entries]
            )
            cycled_records = self.image_matching_service.process_thermometer_records(
                candidates_list, debug_entries=thermometer_entries)
            logging.info(
                "[DEBUG][set_all_entries] cycled_records: %s",
                [getattr(r, 'remarks', None) if r else None for r in cycled_records]
            )
            group_debug_log = []
            for idx, (e, rec) in enumerate(zip(thermometer_entries, cycled_records)):
                if rec is not None:
                    e.chain_records = [rec]
                    log_msg = (
                        f"[サイクルマッチング] idx={idx} remarks={getattr(rec, 'remarks', None)} "
                        f"photo_category={getattr(rec, 'photo_category', None)} → アサイン"
                    )
                    e.debug_log.append(log_msg)
                    group_debug_log.append(f"{e.image_path}: {log_msg}")
                else:
                    log_msg = f"[サイクルマッチング] idx={idx} → アサインなし"
                    e.debug_log.append(log_msg)
                    group_debug_log.append(f"{e.image_path}: {log_msg}")
            logging.info("[DEBUG][SummaryDataService] 温度計サイクルマッチング詳細:")
            # for line in group_debug_log:
            #     logging.info("  %s", line)
            logging.info("[DEBUG][SummaryDataService] サイクルマッチング結果反映完了")
        logging.info("[DEBUG][set_all_entries] return直前: entriesのdebug_log一覧")
        for entry in entries:
            # logging.info(
            #     "  image_path=%s, id=%d, debug_log=%s",
            #     getattr(entry, 'image_path', None), id(entry), getattr(entry, 'debug_log', None)
            # )
            pass
        return

    def update_image_roles(self, image_path: str, roles: Dict[str, str]):
        self.image_roles[image_path] = roles

    def get_roles_for_image(self, image_path: str) -> Dict[str, str]:
        return self.image_roles.get(image_path, {})

    def get_categories(self, entries, match_results):
        return self.category_role_service.get_categories(self.all_records)

    def get_sorted_entries(self, entries, match_results, selected_cat, ascending):
        return self.category_role_service.get_sorted_entries(
            entries, match_results, selected_cat, ascending, self.all_records)

    def get_remarks_for_entry(self, entry: 'ImageEntry',
                              debug_callback: Optional[Callable[[str, str], None]] = None) -> List[ChainRecord]:
        return self.category_role_service.get_remarks_for_entry(
            entry, self.all_records, debug_callback)

    def get_photo_category_from_remarks(self, remarks: str) -> str:
        rec = self.remarks_to_chain_record.get(remarks)
        return rec.photo_category if rec and rec.photo_category is not None else ''

    def get_chain_records_for_image(self, img_path: str) -> list:
        roles = []
        if hasattr(self, 'image_roles') and img_path in self.image_roles:
            r = self.image_roles[img_path]
            if isinstance(r, dict):
                roles = list(r.values())
            else:
                roles = r
        records = getattr(self.dictionary_manager, 'records', [])
        return find_chain_records_by_roles(roles, records)

    def get_image_entry_for_image(self, img_path: str) -> Optional[ImageEntry]:
        for entry in self.all_entries:
            if hasattr(entry, 'image_path') and entry.image_path == img_path:
                return entry
        return None

    def import_chain_records_from_json(self, json_path=None):
        return self.db_resource_service.import_chain_records_from_json(json_path)

    def import_role_mappings_from_json(self, json_path=None):
        return self.db_resource_service.import_role_mappings_from_json(json_path)

    def import_image_entries_from_json(self, json_path=None):
        return self.db_resource_service.import_image_entries_from_json(json_path)

    def reset_all_resources(self):
        return self.db_resource_service.reset_all_resources()

    def get_match_results(self, entries, role_mapping, remarks_to_chain_record, debug_callback=None):
        return self.image_matching_service.match_image_to_records(
            entries, role_mapping, remarks_to_chain_record, debug_callback)

    def full_initialize(self):
        self.reset_all_resources()
        image_dicts = self.db_resource_service.get_all_images()
        entries = [ImageEntry(image_path=d['image_path']) for d in image_dicts if d.get('image_path')]
        self.set_all_entries(entries)
        self.get_match_results(entries, self.role_mappings, self.remarks_to_chain_record)
        logging.info("[SummaryDataService] full_initialize完了（DB・データ・マッチング・ログ全出力）")