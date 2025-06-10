import sqlite3
from pathlib import Path
import json

DB_PATH = Path(__file__).parent / 'image_preview_cache.db'

def fetch_all_records():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT filename, image_path, bboxes FROM image_cache')
    rows = c.fetchall()
    conn.close()
    return rows

def main():
    records = fetch_all_records()
    for filename, image_path, bboxes in records:
        print(f'filename: {filename}')
        print(f'image_path: {image_path}')
        print(f'bboxes: {bboxes}')
        print('---')

if __name__ == '__main__':
    main() 