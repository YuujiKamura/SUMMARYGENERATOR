import os
from src.new_matcher import load_image_jsons, load_role_mapping, load_records, match_images_with_records

CACHE_DIR = os.path.abspath('src/image_preview_cache')
ROLE_MAPPING_PATH = os.path.abspath('src/data/role_mapping.json')
RECORDS_PATH = os.path.abspath('src/data/dictionaries/default_records.json')


def test_match_images_with_records_realdata():
    images = load_image_jsons(CACHE_DIR)
    mapping = load_role_mapping(ROLE_MAPPING_PATH)
    records = load_records(RECORDS_PATH)
    results = match_images_with_records(images, mapping, records)
    assert isinstance(results, dict)
    # at least one image should have matches
    matched_counts = sum(1 for v in results.values() if v)
    assert matched_counts > 0
