import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'summarygenerator' / 'utils'))
from path_manager import PathManager

def test_path_manager_image_cache(tmp_path):
    # テスト用キャッシュディレクトリとJSONを作成
    cache_dir = tmp_path / 'image_preview_cache'
    cache_dir.mkdir()
    img_path = tmp_path / 'img1.jpg'
    img_path.write_text('dummy')
    import hashlib
    hash_name = hashlib.md5(str(img_path).encode('utf-8')).hexdigest()
    json_path = cache_dir / f'{hash_name}.json'
    json_path.write_text(json.dumps({'class_name': 'cat'}))
    # パスマネージャーのsrc_dirをテスト用に上書き
    pm = PathManager()
    pm.src_dir = tmp_path
    # get_individual_json_pathで正しく参照できるか
    resolved_json = pm.get_individual_json_path(str(img_path))
    assert resolved_json.exists()
    with open(resolved_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert data['class_name'] == 'cat' 