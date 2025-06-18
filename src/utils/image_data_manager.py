import os
import json
from src.utils.image_cache_utils import get_image_cache_path
from src.utils.image_entry import ImageEntry
from src.utils.record_matching_utils import match_roles_records_one_stop
from src.services.summary_data_service import SummaryDataService
from src.dictionary_manager import DictionaryManager
from src.utils.role_mapping_utils import load_role_mapping
from src.db_manager import ImageManager, BBoxManager, ChainRecordManager, DBConnection
from src.utils.chain_record_utils import ChainRecord
from ocr_tools.survey_point import SurveyPoint as _SP

class ImageDataManager:
    def __init__(self, image_list_json_path=None, cache_dir=None):
        self.entries = []
        self.load()

    def load(self):
        """
        DBから画像リスト・BBoxを取得し、ImageEntryリストを生成する。ログも出力。
        """
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, 'A_dictionary_load.log')
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
            records_master = dictionary_manager.records
            for img in images:
                image_id = img["id"]
                img_path = img["image_path"]
                bboxes = BBoxManager.get_bboxes_for_image(image_id)
                # --- SurveyPoint 取得 ---
                survey_point_dict = None
                with DBConnection() as _conn:
                    sp_row = _conn.execute("SELECT * FROM survey_points WHERE image_id=?", (image_id,)).fetchone()
                    if sp_row:
                        survey_point_dict = dict(sp_row)
                        # JSON列を展開
                        import json as _json
                        if 'values_json' in survey_point_dict and survey_point_dict['values_json']:
                            try:
                                survey_point_dict['values'] = _json.loads(survey_point_dict['values_json'])
                            except Exception:
                                survey_point_dict['values'] = {}
                        if 'inferred_json' in survey_point_dict and survey_point_dict['inferred_json']:
                            try:
                                survey_point_dict['inferred_values'] = _json.loads(survey_point_dict['inferred_json'])
                            except Exception:
                                survey_point_dict['inferred_values'] = {}
                cache_json = {
                    "image_path": img_path,
                    "bboxes": bboxes
                }
                # roles 抽出（bboxes から）
                roles: list[str] = []
                for b in bboxes:
                    role = b.get("role")
                    if role:
                        roles.append(role)
                # chain_records は DB に登録済みのもののみ取得、ここでは新規マッチングしない
                chain_record_dicts = ChainRecordManager.get_chain_records_for_image(image_id)
                chain_records = [ChainRecord.from_dict(r) for r in chain_record_dicts]
                entry = ImageEntry(
                    image_path=img_path,
                    json_path=None,
                    chain_records=chain_records,
                    location=None,
                    debug_text=None,
                    cache_json=cache_json,
                    roles=roles
                )
                if survey_point_dict:
                    entry.survey_point = _SP.from_raw(survey_point_dict) if hasattr(_SP, 'from_raw') else _SP(**survey_point_dict)
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
        dictionary_manager = DictionaryManager(None)
        records_master = dictionary_manager.records
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
            # roles 抽出（bboxes から）
            roles: list[str] = []
            for b in bboxes:
                role = b.get("role")
                if role:
                    roles.append(role)
            # chain_records は DB 登録済みのみ。ここでは新規マッチングしない
            entry = ImageEntry(
                image_path=img_path,
                json_path=None,
                chain_records=chain_records,
                location=None,
                debug_text=None,
                cache_json=cache_json,
                roles=roles
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