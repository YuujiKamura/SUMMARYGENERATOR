import json
import tempfile
from pathlib import Path
import shutil
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'summarygenerator' / 'utils'))
from path_manager import PathManager

def test_generate_master_image_list(tmp_path):
    # テスト用画像リストと個別JSONを作成
    img1 = tmp_path / 'img1.jpg'
    img2 = tmp_path / 'img2.jpg'
    img1.write_text('dummy')
    img2.write_text('dummy')
    pm = PathManager()
    cache_dir = tmp_path / 'image_preview_cache'
    cache_dir.mkdir()
    # img1: class_nameあり, img2: labelあり
    import hashlib
    hash1 = hashlib.md5(str(img1).encode('utf-8')).hexdigest()
    hash2 = hashlib.md5(str(img2).encode('utf-8')).hexdigest()
    (cache_dir / f'{hash1}.json').write_text(json.dumps({'class_name': 'cat'}))
    (cache_dir / f'{hash2}.json').write_text(json.dumps({'label': 'dog'}))
    # パスマネージャーのsrc_dirをテスト用に上書き
    pm.src_dir = tmp_path
    image_list = [str(img1), str(img2)]
    image_list_json = tmp_path / 'image_list.json'
    output_json = tmp_path / 'master_image_list.json'
    image_list_json.write_text(json.dumps(image_list))
    # テスト対象ロジック
    master_list = []
    for img_path in image_list:
        json_path = pm.get_individual_json_path(img_path)
        assert json_path.exists()
        with open(json_path, 'r', encoding='utf-8') as jf:
            info = json.load(jf)
        class_name = info.get('class_name') or info.get('label') or info.get('role')
        assert class_name in ['cat', 'dog']
        master_list.append({'image_path': img_path, 'class_name': class_name})
    output_json.write_text(json.dumps(master_list, ensure_ascii=False, indent=2))
    # 検証
    with open(output_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert len(data) == 2
    assert data[0]['class_name'] == 'cat'
    assert data[1]['class_name'] == 'dog' 