import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.simple_matcher import match_from_paths  # noqa: E402


def test_simple_matcher_real_data():
    cache_dir = os.path.abspath('src/image_preview_cache')
    mapping_path = os.path.abspath('src/data/role_mapping.json')
    records_path = os.path.abspath(
        'src/data/dictionaries/default_records.json'
    )

    results = match_from_paths(cache_dir, mapping_path, records_path)
    assert isinstance(results, dict)
    assert results

    any_matched = False
    for img_path, remarks in results.items():
        assert isinstance(img_path, str)
        assert isinstance(remarks, list)
        if remarks:
            any_matched = True
        for r in remarks:
            assert isinstance(r, str)
    assert any_matched
