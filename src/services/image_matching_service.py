from src.utils.chain_record_utils import ChainRecord
from src.utils.thermometer_utils import process_thermometer_records
import hashlib, json, datetime, os
from src.utils.log_utils import LOG_PATHS, step_log

def match_image_to_records(image_json_dict, records, mapping=None):
    """
    画像パス→キャッシュJSON（img_json）→ChainRecordリストのdictを返す
    image_json_dict: {image_path: img_json, ...}
    mapping: role_mapping（Noneの場合は空dictで渡す）
    """
    from src.utils.record_matching_utils import match_roles_records_one_stop
    result = {}
    if mapping is None:
        mapping = {}
    for img_path, img_json in image_json_dict.items():
        matched = match_roles_records_one_stop(img_json, mapping, records)
        result[img_path] = matched
    return result

"""
ImageMatchingService: 画像エントリのマッチング、温度計サイクルマッチングを担当
"""
class ImageMatchingService:
    def __init__(self):
        pass

    def match_image_to_records(self, entries, role_mapping, remarks_to_chain_record, debug_callback=None):
        image_json_dict = {}
        for e in entries:
            path = getattr(e, 'path', None) or getattr(e, 'image_path', None)
            roles = getattr(e, 'roles', None)
            if not roles or not isinstance(roles, list):
                roles = []
                if hasattr(e, 'cache_json') and e.cache_json and 'bboxes' in e.cache_json:
                    for b in e.cache_json['bboxes']:
                        if 'role' in b and b['role']:
                            roles.append(b['role'])
            if debug_callback:
                debug_callback(path, f"[get_match_results] roles: {roles}")
            img_json = {
                'image_path': path,
                'roles': roles
            }
            if hasattr(e, 'cache_json') and e.cache_json:
                img_json.update({
                    'img_w': e.cache_json.get('img_w'),
                    'img_h': e.cache_json.get('img_h'),
                    'bboxes': e.cache_json.get('bboxes', [])
                })
            image_json_dict[path] = img_json
        step_log('image_json_dict', image_json_dict)
        # DBからChainRecordを取得
        # records = [ChainRecord.from_dict(r) for r in remarks_to_chain_record.values()]
        records = list(remarks_to_chain_record.values())
        step_log('chain_records_match', [r.__dict__ for r in records])
        match_results = match_image_to_records(image_json_dict, records, role_mapping)
        step_log('S3_match_results', match_results)
        return match_results

    def process_thermometer_records(self, candidates_list, debug_entries=None):
        return process_thermometer_records(candidates_list, debug_entries=debug_entries)
