import os
import json
import datetime
import hashlib

LOG_PATHS = {
    'S1_chain_records_and_role_mappings': os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs', 'S1_chain_records_and_role_mappings.log'),
    'S2_image_entries': os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs', 'S2_image_entries.log'),
    'S3_match_results': os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs', 'S3_match_results.log'),
    'image_json_dict': os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs', 'image_json_dict.log'),
    'chain_records_match': os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs', 'chain_records_match.log'),
}
_last_log_hash = {}
def step_log(label, data):
    path = LOG_PATHS[label]
    h = hashlib.md5(json.dumps(data, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()
    # S3_match_results は毎回上書き
    if label == 'S3_match_results':
        mode = 'w'
        _last_log_hash.pop(label, None)
    else:
        mode = 'a'
        if _last_log_hash.get(label) == h:
            return
    _last_log_hash[label] = h
    with open(path, mode, encoding='utf-8') as f:
        f.write(f"[{datetime.datetime.now().isoformat()}] {label}\n")
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')
