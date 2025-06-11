import sqlite3
import os

db_path = 'src/data/model_training_cache.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()
tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
os.makedirs('logs', exist_ok=True)
with open('logs/preview_image_cache_db_tables.txt', 'w', encoding='utf-8') as f:
    for t in tables:
        f.write(str(t) + '\n')
conn.close()
print('テーブル一覧をlogs/preview_image_cache_db_tables.txtに出力しました') 