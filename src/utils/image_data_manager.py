import os
import json
from src.utils.image_cache_utils import get_image_cache_path
from src.utils.image_entry import ImageEntry
from src.utils.record_matching_utils import match_roles_records_one_stop
from src.services.summary_data_service import SummaryDataService
from src.dictionary_manager import DictionaryManager
from src.utils.summary_generator import load_role_mapping
from src.db_manager import ImageManager, BBoxManager, ChainRecordManager
from src.utils.chain_record_utils import ChainRecord

class ImageDataManager:
    def __init__(self, image_list_json_path=None, cache_dir=None):
        self.entries = []
        self.load()

    def load(self):
        """
        DBから画像リスト・BBoxを取得し、ImageEntryリストを生成する。ログも出力。
        """
        log_path = 'logs/A_dictionary_load.log'
        def log(msg, obj=None):
            with open(log_path, 'w', encoding='utf-8') as f:
                if obj is not None:
                    f.write(msg + ' ' + json.dumps(obj, ensure_ascii=False) + '\n')
                else:
                    f.write(msg + '\n')
        try:
            entries = []
            images = ImageManager.get_all_images()
            role_mapping = load_role_mapping()
            dictionary_manager = DictionaryManager(None)
            records = dictionary_manager.records
            for img in images:
                image_id = img["id"]
                img_path = img["image_path"]
                bboxes = BBoxManager.get_bboxes_for_image(image_id)
                cache_json = {
                    "image_path": img_path,
                    "bboxes": bboxes
                }
                entry = ImageEntry.from_cache_json(img_path, cache_json, role_mapping, records)
                entries.append(entry)
            self.entries = entries
            log('A_IMAGE_LOAD', {'count': len(images), 'image_paths': [img["image_path"] for img in images[:10]]})
        except Exception as e:
            log('A_IMAGE_LOAD_ERROR', {'error': str(e)})

    @classmethod
    def from_db(cls):
        """
        DBから画像リスト・BBox・ChainRecordを取得し、ImageEntryリストを生成する
        """
        entries = []
        images = ImageManager.get_all_images()
        role_mapping = load_role_mapping()
        for img in images:
            image_id = img["id"]
            img_path = img["image_path"]
            bboxes = BBoxManager.get_bboxes_for_image(image_id)
            # DBからchain_recordsを取得
            chain_record_dicts = ChainRecordManager.get_chain_records_for_image(image_id)
            chain_records = [ChainRecord.from_dict(r) for r in chain_record_dicts]
            cache_json = {
                "image_path": img_path,
                "bboxes": bboxes
            }
            entry = ImageEntry(
                image_path=img_path,
                json_path=None,
                chain_records=chain_records,
                location=None,
                debug_text=None,
                cache_json=cache_json,
                roles=None
            )
            entries.append(entry)
        inst = cls.__new__(cls)
        inst.entries = entries
        return inst

    def _load_all_cache_json(self, cache_dir):
        """キャッシュディレクトリ内の全jsonをロードし、img_path→data辞書を返す（ScanForImagesWidgetと同等）"""
        cache_data = {}
        if os.path.exists(cache_dir):
            for fname in os.listdir(cache_dir):
                if not fname.endswith('.json'):
                    continue
                fpath = os.path.join(cache_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if not isinstance(data, dict):
                        # dict型以外（list型など）はスキップ
                        continue
                    img_path = data.get("image_path")
                    if img_path:
                        cache_data[os.path.abspath(img_path)] = data
                except (OSError, json.JSONDecodeError):
                    continue
        return cache_data