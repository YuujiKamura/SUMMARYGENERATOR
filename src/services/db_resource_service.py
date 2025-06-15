"""
DBResourceService: DB初期化・リセット・データ投入・DBからの取得を担当
"""

from src.db_manager import (
    ChainRecordManager, RoleMappingManager, ImageManager, BBoxManager,
    import_image_preview_cache_json, reset_all_tables, init_db
)
from src.utils.path_manager import PathManager
from src.utils.csv_records_loader import load_records_and_roles_csv


class DBResourceService:
    def __init__(self):
        # DB スキーマ初期化と同時に CSV / JSON からデータも一括投入しておく
        init_db()
        self.reset_all_resources()

    def reset_all_tables(self):
        reset_all_tables()

    def import_image_entries_from_json(self, json_path=None):
        if json_path is None:
            pm = PathManager()
            json_path = pm.image_preview_cache_master
        import_image_preview_cache_json(json_path=json_path)

    def import_records_and_mappings_from_csv(self, csv_path=None):
        pm = PathManager()
        if csv_path is None:
            csv_path = pm.records_and_roles_csv
        if not csv_path.exists():
            return
        records, mappings = load_records_and_roles_csv(csv_path)
        for rec in records:
            ChainRecordManager.add_chain_record(
                location=rec.location,
                controls=rec.controls,
                photo_category=rec.photo_category,
                work_category=rec.work_category,
                type_=rec.type,
                subtype=rec.subtype,
                remarks=rec.remarks,
                extra_json="{}"
            )
        import json as _json
        for remarks, mp in mappings.items():
            RoleMappingManager.add_or_update_role_mapping(remarks, _json.dumps(mp, ensure_ascii=False))

    def reset_all_resources(self):
        self.reset_all_tables()
        self.import_records_and_mappings_from_csv()
        self.import_image_entries_from_json()

    def get_all_chain_records(self):
        return ChainRecordManager.get_all_chain_records()

    def get_all_role_mappings(self):
        return RoleMappingManager.get_all_role_mappings()

    def get_all_images(self):
        return ImageManager.get_all_images()
