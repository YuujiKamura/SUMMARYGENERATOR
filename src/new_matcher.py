import json
import os
from typing import List, Dict, Any


def load_image_jsons(directory: str) -> List[Dict[str, Any]]:
    """Load all image preview cache JSONs."""
    images = []
    for fname in os.listdir(directory):
        if not fname.endswith('.json'):
            continue
        path = os.path.join(directory, fname)
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        images.append(data)
    return images


def load_role_mapping(path: str) -> Dict[str, Dict[str, Any]]:
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def load_records(default_records_path: str) -> List[Dict[str, Any]]:
    with open(default_records_path, encoding='utf-8') as f:
        info = json.load(f)
    records = []
    base_dir = os.path.dirname(default_records_path)
    for rec_file in info.get('records', []):
        rec_path = os.path.join(base_dir, rec_file)
        with open(rec_path, encoding='utf-8') as rf:
            records.append(json.load(rf))
    return records


def match_images_with_records(images: List[Dict[str, Any]],
                              role_mapping: Dict[str, Dict[str, Any]],
                              records: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = {}
    for img in images:
        roles = []
        for b in img.get('bboxes', []) or []:
            r = b.get('role')
            if r:
                roles.append(r)
        unique_roles = set(roles)
        matched = []
        for rec in records:
            remarks = rec.get('remarks')
            mapping_entry = role_mapping.get(remarks)
            if not mapping_entry:
                continue
            mapping_roles = mapping_entry.get('roles', [])
            if not mapping_roles:
                continue
            match_type = mapping_entry.get('match', 'all')
            if match_type == 'all':
                if all(r in unique_roles for r in mapping_roles):
                    matched.append(remarks)
            else:
                if any(r in unique_roles for r in mapping_roles):
                    matched.append(remarks)
        result[img.get('image_path', '')] = matched
    return result


# -----------------------------------------------------------------------------
# Adapter: remarks → ChainRecord objects
# -----------------------------------------------------------------------------

def match_images_with_chain_records(
    images: List[Dict[str, Any]],
    role_mapping: Dict[str, Dict[str, Any]],
    records: List[Any],
) -> Dict[str, List[Any]]:
    """match_images_with_records の結果を ChainRecord オブジェクトに置き換えて返す

    Args:
        images: image dict list (same as match_images_with_records)
        role_mapping: remarks ➜ {roles, match}
        records: ChainRecord または dict のリスト

    Returns:
        {image_path: [ChainRecord, ...]}
    """
    # まず remarks list を取得
    img_to_remarks = match_images_with_records(images, role_mapping, [r.to_dict() if hasattr(r, 'to_dict') else r for r in records])

    # remarks → record lookup
    lookup = {}
    for r in records:
        rem = None
        if isinstance(r, dict):
            rem = r.get('remarks')
        else:
            rem = getattr(r, 'remarks', None)
        if rem is not None:
            lookup[rem] = r

    img_to_records: Dict[str, List[Any]] = {}
    for img_path, remarks_list in img_to_remarks.items():
        img_to_records[img_path] = [lookup[rem] for rem in remarks_list if rem in lookup]
    return img_to_records
