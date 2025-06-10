import os
import json
from src.image_cache_utils import get_image_cache_path
from src.image_entry import ImageEntry
from src.record_matching_utils import match_roles_records_one_stop
from src.services.summary_data_service import SummaryDataService
from src.dictionary_manager import DictionaryManager
from src.summary_generator import load_role_mapping
from src.db_manager import ImageManager, BBoxManager

class ImageDataManager:
    def __init__(self, image_list_json_path, cache_dir):
        self.entries = []
        self.load(image_list_json_path, cache_dir)

    @classmethod
    def from_db(cls):
        """
        DBから画像リスト・BBoxを取得し、ImageEntryリストを生成する
        """
        entries = []
        images = ImageManager.get_all_images()
        role_mapping = load_role_mapping()
        dictionary_manager = DictionaryManager(None)
        records = dictionary_manager.records
        for img in images:
            image_id = img["id"]
            img_path = img["image_path"]
            bboxes = BBoxManager.get_bboxes_for_image(image_id)
            # ImageEntry.from_cache_jsonの引数に合わせてcache_jsonを生成
            cache_json = {
                "image_path": img_path,
                "bboxes": bboxes
            }
            entry = ImageEntry.from_cache_json(img_path, cache_json, role_mapping, records)
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

    def load(self, image_list_json_path, cache_dir):
        # 画像リストJSONをdict型リストに正規化
        with open(image_list_json_path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            img_dicts = [
                {"path": d["path"]} if isinstance(d, dict) and "path" in d else
                {"path": d["image_path"]} if isinstance(d, dict) and "image_path" in d else
                {"path": d} if isinstance(d, str) else None
                for d in data
                if (
                    (isinstance(d, dict) and ("path" in d or "image_path" in d))
                    or isinstance(d, str)
                )
            ]
            img_dicts = [d for d in img_dicts if d is not None]
        elif isinstance(data, dict) and "images" in data:
            img_dicts = [
                {"path": d["path"]} if isinstance(d, dict) and "path" in d else {"path": d}
                for d in data["images"]
                if (isinstance(d, dict) and "path" in d) or isinstance(d, str)
            ]
        else:
            img_dicts = []
        self.entries = []
        cache_data = self._load_all_cache_json(cache_dir)
        # --- 追加: マッチング用のrole_mapping/recordsをロード ---
        dictionary_manager = DictionaryManager(None)
        records = dictionary_manager.records
        role_mapping = load_role_mapping()
        for img in img_dicts:
            img_path = os.path.abspath(img["path"])
            cache_json = cache_data.get(img_path)
            entry = ImageEntry.from_cache_json(img_path, cache_json, role_mapping, records)
            if hasattr(entry, 'chain_records'):
                print(f"[DEBUG][ImageDataManager] image_path={getattr(entry, 'image_path', None)}, chain_records={[{'remarks': getattr(r, 'remarks', None), 'photo_category': getattr(r, 'photo_category', None)} for r in getattr(entry, 'chain_records', [])]}")
            self.entries.append(entry)