import sqlite3
import json
from pathlib import Path

# テスト用DBパス
DB_PATH = Path(__file__).parent / 'model_training_cache.db'
JSON_PATH = Path(__file__).parent / 'image_preview_cache_master.json'

def create_test_db_from_json():
    # DB作成
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DROP TABLE IF EXISTS image_cache')
    c.execute('''
        CREATE TABLE image_cache (
            filename TEXT PRIMARY KEY,
            image_path TEXT,
            bboxes TEXT
        )
    ''')
    # JSON読み込み
    with open(JSON_PATH, encoding='utf-8') as f:
        data = json.load(f)
    # 1件だけ挿入（最初の要素）
    if isinstance(data, list) and data:
        row = data[0]
        c.execute('INSERT INTO image_cache (filename, image_path, bboxes) VALUES (?, ?, ?)',
                  (row['filename'], row['image_path'], json.dumps(row['bboxes'], ensure_ascii=False)))
    conn.commit()
    conn.close()
    print('テスト用DBを作成しました')

if __name__ == '__main__':
    create_test_db_from_json()
