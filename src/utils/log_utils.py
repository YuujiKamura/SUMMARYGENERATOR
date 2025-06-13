import os
import json
import datetime
import hashlib

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATHS = {
    'step': os.path.join(LOG_DIR, 'step.log'),
    'image_matching': os.path.join(LOG_DIR, 'image_matching.log'),
    'thermo': os.path.join(LOG_DIR, 'thermo.log'),
    'debug': os.path.join(LOG_DIR, 'debug.log'),
    'image_json_dict': os.path.join(LOG_DIR, 'image_json_dict.log'),
    'chain_records_match': os.path.join(LOG_DIR, 'chain_records_match.log'),
    'S3_match_results': os.path.join(LOG_DIR, 'S3_match_results.log'),
}
_last_log_hash = {}
def step_log(label, data):
    path = LOG_PATHS[label]
    h = hashlib.md5(json.dumps(data, ensure_ascii=False, sort_keys=True, default=str).encode('utf-8')).hexdigest()
    if _last_log_hash.get(label) == h:
        return
    _last_log_hash[label] = h
    with open(path, 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.datetime.now().isoformat()}] {label}\n")
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        f.write('\n')
