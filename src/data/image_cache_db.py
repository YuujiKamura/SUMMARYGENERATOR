import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / 'model_training_cache.db'

class ImageCacheDB:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self._init_table()

    def _init_table(self):
        c = self.conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS image_cache (
                filename TEXT PRIMARY KEY,
                image_path TEXT,
                bboxes TEXT
            )
        ''')
        self.conn.commit()

    def insert_image(self, filename, image_path, bboxes):
        c = self.conn.cursor()
        c.execute('REPLACE INTO image_cache (filename, image_path, bboxes) VALUES (?, ?, ?)',
                  (filename, image_path, json.dumps(bboxes, ensure_ascii=False)))
        self.conn.commit()

    def delete_image(self, filename):
        c = self.conn.cursor()
        c.execute('DELETE FROM image_cache WHERE filename=?', (filename,))
        self.conn.commit()

    def fetch_image(self, filename):
        c = self.conn.cursor()
        c.execute('SELECT filename, image_path, bboxes FROM image_cache WHERE filename=?', (filename,))
        row = c.fetchone()
        if row:
            return {'filename': row[0], 'image_path': row[1], 'bboxes': json.loads(row[2])}
        return None

    def fetch_all(self):
        c = self.conn.cursor()
        c.execute('SELECT filename, image_path, bboxes FROM image_cache')
        rows = c.fetchall()
        return [
            {'filename': r[0], 'image_path': r[1], 'bboxes': json.loads(r[2])}
            for r in rows
        ]

    def close(self):
        self.conn.close()

if __name__ == '__main__':
    db = ImageCacheDB()
    # 例: 全件表示
    for rec in db.fetch_all():
        print(rec)
    db.close()
