# data_loader.py
"""
CSV・JSONの読み込みとデータ整形を担当
"""
import csv
import json
from collections import OrderedDict

def load_records(csv_path):
    records = []
    with open(csv_path, encoding='utf-8') as f:
        lines = f.readlines()
    header_idx = None
    for i, line in enumerate(lines):
        if 'photo_category' in line.strip().lower():
            header_idx = i
            break
    if header_idx is None:
        raise ValueError('ヘッダー行が見つかりません')
    fieldnames = [h.strip() for h in lines[header_idx].strip().split(',')]
    if fieldnames and fieldnames[0].startswith('\ufeff'):
        fieldnames[0] = fieldnames[0].lstrip('\ufeff')
    reader = csv.DictReader(lines[header_idx+1:], fieldnames=fieldnames)
    for row in reader:
        if not any(row.values()):
            continue
        criteria = []
        for c in ['machine', 'driver/worker', 'board', 'mesurer', 'object', 'surface']:
            val = row[c]
            if val:
                for part in val.replace('\r', '').replace('\n', '\n').split('\n'):
                    for sub in part.split(','):
                        s = sub.strip()
                        if s:
                            criteria.append(s)
        record = {
            'key': tuple(row[k] for k in ['photo_category', 'work category', 'type', 'subtype', 'remarks']),
            'match': row['match'],
            'criteria': criteria
        }
        records.append(record)
    return records

def load_image_roles(json_path):
    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)
    image_roles = {}
    for entry in data:
        roles = [bbox.get('role') for bbox in entry.get('bboxes', []) if bbox.get('role')]
        image_roles[entry['image_path']] = roles
    # 画像名でソートしてOrderedDictで返す
    sorted_items = sorted(image_roles.items(), key=lambda x: x[0])
    return OrderedDict(sorted_items)
