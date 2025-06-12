import json
import os


def load_image_list(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_image_roles(cache_dir):
    roles_data = {}
    for fname in os.listdir(cache_dir):
        if fname.endswith('.json'):
            file_path = os.path.join(cache_dir, fname)
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            img_path = data.get('image_path')
            bboxes = data.get('bboxes', []) or []
            roles = [b.get('role') for b in bboxes if b.get('role')]
            if img_path:
                roles_data[img_path] = roles
    return roles_data


def load_role_mapping(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_records(default_records_path):
    with open(default_records_path, encoding="utf-8") as f:
        meta = json.load(f)
    records = []
    base = os.path.dirname(default_records_path)
    for rec_file in meta.get('records', []):
        rec_path = os.path.join(base, rec_file)
        with open(rec_path, encoding="utf-8") as rf:
            rec = json.load(rf)
        records.append(rec)
    return records


def match_image_to_remarks(image_roles, role_mapping, records):
    results = {}
    for img_path, roles in image_roles.items():
        matched = []
        role_set = set(roles)
        for rec in records:
            remarks = rec.get('remarks')
            mapping_entry = role_mapping.get(remarks, {})
            mapping_roles = mapping_entry.get('roles', [])
            match_type = mapping_entry.get('match', 'all')
            if not mapping_roles:
                continue
            if match_type == 'all':
                if all(r in role_set for r in mapping_roles):
                    matched.append(remarks)
            else:
                if any(r in role_set for r in mapping_roles):
                    matched.append(remarks)
        results[img_path] = matched
    return results
