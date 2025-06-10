import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / 'model_training_cache.db'
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
    c.execute('''INSERT OR REPLACE INTO image_cache (filename, image_path, bboxes) VALUES (?, ?, ?)''',
              (filename, image_path, bboxes))
    conn.commit()
    conn.close()

def insert_from_json():
    log_path = Path(__file__).parent.parent.parent / 'logs' / '00_db_register.log'
    with open(JSON_PATH, encoding='utf-8') as f:
        data = json.load(f)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    total = 0
    success = 0
    fail = 0
    with open(log_path, 'w', encoding='utf-8') as logf:  # ← 'a'から'w'に変更
        for entry in data:
            total += 1
            # ここでbboxesの内容をprint/log
            logf.write(f"[DEBUG] filename={entry.get('filename')} bboxes={json.dumps(entry.get('bboxes'), ensure_ascii=False)}\n")
            # print(f"[DEBUG] filename={entry.get('filename')} bboxes={json.dumps(entry.get('bboxes'), ensure_ascii=False)}")
            try:
                # bboxの不正チェック（幅0/高さ0のbboxが含まれていないか）
                bboxes = entry.get('bboxes', [])
                invalid_bboxes = []
                for bbox in bboxes:
                    xyxy = bbox.get('xyxy', [])
                    if len(xyxy) == 4:
                        x1, y1, x2, y2 = xyxy
                        w = abs(x2 - x1)
                        h = abs(y2 - y1)
                        if w == 0 or h == 0:
                            invalid_bboxes.append(bbox)
                if invalid_bboxes:
                    fail += 1
                    logf.write(f"[FAIL] filename={entry.get('filename')} image_path={entry.get('image_path')}\n")
                    logf.write(f"  不正bbox数: {len(invalid_bboxes)}\n")
                    for ib in invalid_bboxes:
                        logf.write(f"    invalid_bbox: {json.dumps(ib, ensure_ascii=False)}\n")
                    logf.write(f"  全bbox: {json.dumps(bboxes, ensure_ascii=False)}\n")
                    logf.write(f"  ----\n")
                    continue  # 不正bboxが1つでもあれば登録スキップ
                # 登録処理
                c.execute('''INSERT OR REPLACE INTO image_cache (filename, image_path, bboxes) VALUES (?, ?, ?)''',
                          (entry['filename'], entry['image_path'], json.dumps(entry['bboxes'], ensure_ascii=False)))
                success += 1
                logf.write(f"[OK] filename={entry.get('filename')} 登録成功\n")
            except Exception as e:
                fail += 1
                logf.write(f"[ERROR] filename={entry.get('filename')} error={e}\n")
                logf.write(f"  entry: {json.dumps(entry, ensure_ascii=False)}\n")
                logf.write(f"  ----\n")
    conn.commit()
    conn.close()
    print(f"DB登録: 成功={success}件, 失敗={fail}件, 合計={total}件 (詳細はdb_register.log参照)")

if __name__ == '__main__':
    create_table()
    insert_from_json()