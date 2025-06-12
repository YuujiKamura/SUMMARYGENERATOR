import os
import json
from typing import Dict, List, Any


def load_role_mapping(path: str) -> Dict[str, Any]:
    """Load role mapping JSON."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_records(records_path: str) -> List[Dict[str, Any]]:
    """Load record definitions from default_records.json."""
    with open(records_path, encoding="utf-8") as f:
        records_json = json.load(f)
    records = []
    base_dir = os.path.dirname(records_path)
    for rec_path in records_json.get("records", []):
        full_path = os.path.join(base_dir, rec_path)
        with open(full_path, encoding="utf-8") as rf:
            records.append(json.load(rf))
    return records


def collect_image_roles(cache_dir: str) -> Dict[str, List[str]]:
    """Collect roles from image preview cache directory."""
    image_roles: Dict[str, List[str]] = {}
    for fname in os.listdir(cache_dir):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(cache_dir, fname)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        img_path = data.get("image_path")
        if not img_path:
            continue
        bboxes = data.get("bboxes", [])
        roles = [b.get("role") for b in bboxes if b.get("role")]
        image_roles[img_path] = roles
    return image_roles


def match_images_with_records(
    image_roles: Dict[str, List[str]],
    role_mapping: Dict[str, Any],
    records: List[Dict[str, Any]],
) -> Dict[str, List[str]]:
    """Match images with record remarks based on roles."""
    results: Dict[str, List[str]] = {}
    for img_path, roles in image_roles.items():
        matched: List[str] = []
        for rec in records:
            remarks = rec.get("remarks")
            mapping_entry = role_mapping.get(remarks, {})
            required_roles = mapping_entry.get("roles", [])
            match_type = mapping_entry.get("match", "all")
            if not required_roles:
                continue
            if match_type == "all":
                if all(r in roles for r in required_roles):
                    matched.append(remarks)
            else:
                if any(r in roles for r in required_roles):
                    matched.append(remarks)
        results[img_path] = matched
    return results


def match_from_paths(
    cache_dir: str,
    mapping_path: str,
    records_path: str,
) -> Dict[str, List[str]]:
    """High level API to load data and perform matching."""
    role_mapping = load_role_mapping(mapping_path)
    records = load_records(records_path)
    image_roles = collect_image_roles(cache_dir)
    return match_images_with_records(image_roles, role_mapping, records)
