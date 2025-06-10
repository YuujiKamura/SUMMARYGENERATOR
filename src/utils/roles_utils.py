import json

def load_roles(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def group_roles_by_category(roles):
    cats = {}
    for r in roles:
        cat = r.get('category', '未分類') or '未分類'
        cats.setdefault(cat, []).append(r)
    return cats
