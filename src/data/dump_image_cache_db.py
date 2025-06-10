import sqlite3
import json
from pathlib import Path

db_path = Path(__file__).parent / 'model_training_cache.db'
out_path = Path(__file__).parent / 'dump_image_cache_db.json'

conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute('SELECT filename, image_path, bboxes FROM image_cache')
rows = c.fetchall()
conn.close()

result = []
for filename, image_path, bboxes in rows:
    try:
        bboxes_json = json.loads(bboxes)
    except Exception:
        bboxes_json = bboxes
    result.append({
        'filename': filename,
        'image_path': image_path,
        'bboxes': bboxes_json
    })

with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"Dumped {len(result)} records to {out_path}")
