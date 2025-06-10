import sqlite3

db_path = 'src/data/model_training_cache.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()
with open('logs/preview_image_cache_db.txt', 'w', encoding='utf-8') as f:
    for row in c.execute('SELECT * FROM image_cache'):
        f.write(str(row) + '\n')
conn.close()
print('DB内容をlogs/preview_image_cache_db.txtに出力しました')
