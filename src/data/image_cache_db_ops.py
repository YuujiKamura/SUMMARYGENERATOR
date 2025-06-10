import sys
import json
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
from image_cache_db import ImageCacheDB

DB_PATH = Path(__file__).parent / 'model_training_cache.db'
JSON_PATH = Path(__file__).parent / 'image_preview_cache_master.json'

def init_db_from_json(json_path=JSON_PATH, db_path=DB_PATH):
    db = ImageCacheDB(db_path)
    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)
    for row in data:
        db.insert_image(row['filename'], row['image_path'], row['bboxes'])
    db.close()
    print('全データをDBに登録しました')

def add_augment_image(filename, image_path, bboxes):
    db = ImageCacheDB()
    db.insert_image(filename, image_path, bboxes)
    db.close()
    print(f'オーグメント画像 {filename} をDBに追加しました')

def remove_image(filename):
    db = ImageCacheDB()
    db.delete_image(filename)
    db.close()
    print(f'画像 {filename} をDBから削除しました')

def list_images():
    db = ImageCacheDB()
    for rec in db.fetch_all():
        print(rec['filename'], rec['image_path'])
    db.close()

if __name__ == '__main__':
    # 例: 初期化
    init_db_from_json()
    # 例: 一覧
    list_images()
    # 例: 追加
    # add_augment_image('aug1_xxx.jpg', '/path/to/aug1_xxx.jpg', [])
    # 例: 削除
    # remove_image('aug1_xxx.jpg')
