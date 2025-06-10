import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / 'image_preview_cache.db'
JSON_PATH = Path(__file__).parent / 'image_preview_cache_master.json'

def create_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS image_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            image_path TEXT,
            bboxes TEXT
        )
    ''')
    conn.commit()
    conn.close()

def insert_image_cache_record(filename: str, image_path: str, bboxes):
    if not isinstance(bboxes, str):
        bboxes = json.dumps(bboxes, ensure_ascii=False)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO image_cache (filename, image_path, bboxes) VALUES (?, ?, ?)''',
              (filename, image_path, bboxes))
    conn.commit()
    conn.close()

def insert_from_json():
    with open(JSON_PATH, encoding='utf-8') as f:
        data = json.load(f)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for entry in data:
        c.execute('''INSERT INTO image_cache (filename, image_path, bboxes) VALUES (?, ?, ?)''',
                  (entry['filename'], entry['image_path'], json.dumps(entry['bboxes'], ensure_ascii=False)))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_table()
    insert_from_json() 