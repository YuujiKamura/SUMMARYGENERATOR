"""
DBResourceService: DB初期化・リセット・データ投入・DBからの取得を担当
"""

from src.db_manager import (
    ChainRecordManager, RoleMappingManager, ImageManager, BBoxManager,
    import_image_preview_cache_json, reset_all_tables, init_db
)
from src.utils.records_loader import load_records_from_json
from src.utils.path_manager import PathManager
import json


class DBResourceService:
    def __init__(self):
        init_db()

    def reset_all_tables(self):
        reset_all_tables()

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
            if role_name.startswith('_'):
                continue
            RoleMappingManager.add_or_update_role_mapping(role_name, json.dumps(mapping, ensure_ascii=False))

    def import_image_entries_from_json(self, json_path=None):
        if json_path is None:
            pm = PathManager()
            json_path = pm.image_preview_cache_master
        import_image_preview_cache_json(json_path=json_path)

    def reset_all_resources(self):
        self.reset_all_tables()
        self.import_chain_records_from_json()
        self.import_role_mappings_from_json()
        self.import_image_entries_from_json()

    def get_all_chain_records(self):
        return ChainRecordManager.get_all_chain_records()

    def get_all_role_mappings(self):
        return RoleMappingManager.get_all_role_mappings()

    def get_all_images(self):
        return ImageManager.get_all_images()
