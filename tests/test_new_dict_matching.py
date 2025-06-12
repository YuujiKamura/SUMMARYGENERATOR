import os
from src.new_record_matching import (
    load_image_list,
    load_image_roles,
    load_role_mapping,
    load_records,
    match_image_to_remarks,
)


def test_dictionary_matching_with_real_data():
    image_list_path = os.path.abspath("src/data/image_list20250531.json")
    cache_dir = os.path.abspath("src/image_preview_cache")
    role_mapping_path = os.path.abspath("src/data/role_mapping.json")
    records_path = os.path.abspath("src/data/dictionaries/default_records.json")

    image_list = load_image_list(image_list_path)
    image_roles_all = load_image_roles(cache_dir)
    role_mapping = load_role_mapping(role_mapping_path)
    records = load_records(records_path)

    image_roles = {p: roles for p, roles in image_roles_all.items() if p in image_list}
    assert image_roles, "no matching image roles found"

    results = match_image_to_remarks(image_roles, role_mapping, records)
    assert isinstance(results, dict)
    assert results, "no results"

    # at least one image should have matched remarks
    assert any(len(v) > 0 for v in results.values())

    all_remarks = {rec["remarks"] for rec in records}
    for remarks in results.values():
        for r in remarks:
            assert r in all_remarks
