import os
import json
import pytest
from src.utils.path_manager import path_manager

def test_parse_roles_labels_from_json():
    # 実データのscan_for_images_dataset.jsonを使う
    json_path = str(path_manager.scan_for_images_dataset)
    assert os.path.exists(json_path), f"not found: {json_path}"
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    roles = set()
    labels = set()
    if isinstance(data, list):
        images = data
    elif isinstance(data, dict):
        images = data.get('images', [])
    else:
        images = []
    print(f"[TEST] images count: {len(images)}")
    for img in images[:5]:
        print(f"[TEST] img keys: {list(img.keys())}")
        bboxes = img.get('bboxes', [])
        print(f"[TEST] bboxes count: {len(bboxes)}")
        for bbox in bboxes[:5]:
            print(f"[TEST] bbox: {bbox}")
            if 'role' in bbox and bbox['role']:
                roles.add(bbox['role'])
            if 'label' in bbox and bbox['label']:
                labels.add(bbox['label'])
    role_count = 0
    label_count = 0
    role_samples = []
    label_samples = []
    for img in images:
        bboxes = img.get('bboxes', [])
        for bbox in bboxes:
            if 'role' in bbox and bbox['role']:
                roles.add(bbox['role'])
                role_count += 1
                if len(role_samples) < 10:
                    role_samples.append(bbox['role'])
            if 'label' in bbox and bbox['label']:
                labels.add(bbox['label'])
                label_count += 1
                if len(label_samples) < 10:
                    label_samples.append(bbox['label'])
    print(f"[TEST] total bbox count: {sum(len(img.get('bboxes', [])) for img in images)}")
    print(f"[TEST] role count: {role_count}, label count: {label_count}")
    print(f"[TEST] unique roles: {sorted(roles)}")
    print(f"[TEST] unique labels: {sorted(labels)}")
    print(f"[TEST] role samples: {role_samples}")
    print(f"[TEST] label samples: {label_samples}")
    assert len(images) > 0, "imagesが空" 