import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / 'model_training_cache.db'
JSON_PATH = Path(__file__).parent / 'image_preview_cache_master.json'

# --- preset_roles.jsonのデフォルトパス ---
_PRESET_ROLES_PATH = Path(__file__).parent / 'preset_roles.json'

def _ensure_column_exists(cursor, table_name: str, column_name: str, column_def: str):
    """指定テーブルに列が無ければ追加するユーティリティ"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    cols = [row[1] for row in cursor.fetchall()]
    if column_name not in cols:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")

def register_classes_from_preset(db_path=None, preset_path: Path | None = None):
    """preset_roles.json から classes テーブルへ一括登録する"""
    if db_path is None:
        db_path = DB_PATH
    if preset_path is None:
        preset_path = _PRESET_ROLES_PATH
    if not Path(preset_path).exists():
        print(f"[WARN] preset_roles.json が見つかりません: {preset_path}")
        return
    # ロール一覧を読み込み
    try:
        with open(preset_path, encoding='utf-8') as f:
            roles = json.load(f)
    except Exception as e:
        print(f"[WARN] preset_roles.json 読み込み失敗: {e}")
        return
    class_names = [entry.get('label') for entry in roles if entry.get('label')]
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # classes テーブルが無い場合は作成
    c.execute('CREATE TABLE IF NOT EXISTS classes (id INTEGER PRIMARY KEY, name TEXT UNIQUE)')
    for idx, name in enumerate(class_names):
        try:
            c.execute('INSERT OR IGNORE INTO classes (id, name) VALUES (?, ?)', (idx, name))
        except sqlite3.IntegrityError:
            pass  # UNIQUE 制約で既に登録済みの場合
    conn.commit()
    conn.close()

def create_table(db_path=None):
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS image_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            image_path TEXT,
            bboxes TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            image_path TEXT UNIQUE,
            taken_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS bboxes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id INTEGER,
            cid INTEGER,
            cname TEXT,
            class_master_id INTEGER,
            conf REAL,
            x1 REAL,
            y1 REAL,
            x2 REAL,
            y2 REAL,
            role TEXT,
            FOREIGN KEY(image_id) REFERENCES images(id),
            FOREIGN KEY(class_master_id) REFERENCES classes(id)
        )
    ''')
    c.execute('''CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE
        )''')
    # 既存 bboxes テーブルに列が無ければ追加
    _ensure_column_exists(c, 'bboxes', 'class_master_id', 'INTEGER')
    conn.commit()
    conn.close()

def clear_tables(db_path=None):
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('DELETE FROM image_cache')
    c.execute('DELETE FROM bboxes')
    c.execute('DELETE FROM images')
    # classes テーブルもクリアしておく
    try:
        c.execute('DELETE FROM classes')
    except sqlite3.OperationalError:
        pass  # classes テーブルがまだ無い場合
    conn.commit()
    conn.close()

def insert_image_cache_record(filename: str, image_path: str, bboxes, db_path=None):
    if not isinstance(bboxes, str):
        bboxes = json.dumps(bboxes, ensure_ascii=False)
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO image_cache (filename, image_path, bboxes) VALUES (?, ?, ?)''',
              (filename, image_path, bboxes))
    conn.commit()
    conn.close()

def insert_from_json():
    # classes テーブルを初期登録
    register_classes_from_preset()
    log_path = Path(__file__).parent.parent.parent / 'logs' / '00_db_register.log'
    with open(JSON_PATH, encoding='utf-8') as f:
        data = json.load(f)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # 追加: 既存データを全削除
    c.execute('DELETE FROM image_cache')
    c.execute('DELETE FROM bboxes')
    c.execute('DELETE FROM images')
    total = 0
    success = 0
    fail = 0
    with open(log_path, 'w', encoding='utf-8') as logf:
        for entry in data:
            total += 1
            # bboxesの内容をprint/log
            logf.write(f"[DEBUG] filename={entry.get('filename')} bboxes={json.dumps(entry.get('bboxes'), ensure_ascii=False)}\n")
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
                    logf.write(f"[FAIL] {entry.get('filename')} invalid bbox: {invalid_bboxes}\n")
                    continue
                # imagesテーブルinsert
                c.execute('''INSERT OR IGNORE INTO images (filename, image_path) VALUES (?, ?)''',
                          (entry.get('filename'), entry.get('image_path')))
                c.execute('SELECT id FROM images WHERE image_path=?', (entry.get('image_path'),))
                image_id_row = c.fetchone()
                image_id = image_id_row[0] if image_id_row else None
                # bboxesテーブルinsert
                for bbox in bboxes:
                    # --- class_master_id を決定 ---
                    class_name = bbox.get('role') or bbox.get('cname') or bbox.get('label')
                    class_master_id = None
                    if class_name:
                        c.execute('SELECT id FROM classes WHERE name=?', (class_name,))
                        row = c.fetchone()
                        if row:
                            class_master_id = row[0]
                        else:
                            # 未登録クラスは末尾に追加
                            c.execute('SELECT MAX(id) FROM classes')
                            max_id = c.fetchone()[0]
                            new_id = (max_id + 1) if max_id is not None else 0
                            c.execute('INSERT OR IGNORE INTO classes (id, name) VALUES (?, ?)', (new_id, class_name))
                            class_master_id = new_id
                    c.execute('''INSERT INTO bboxes (image_id, cid, cname, class_master_id, conf, x1, y1, x2, y2, role) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                              (image_id, bbox.get('cid'), bbox.get('cname'), class_master_id, bbox.get('conf'),
                               bbox.get('xyxy', [None]*4)[0], bbox.get('xyxy', [None]*4)[1],
                               bbox.get('xyxy', [None]*4)[2], bbox.get('xyxy', [None]*4)[3],
                               bbox.get('role')))
                success += 1
            except Exception as e:
                fail += 1
                logf.write(f"[FAIL] {entry.get('filename')} error: {e}\n")
    conn.commit()
    conn.close()
    print(f"DB登録: 成功={success}件, 失敗={fail}件, 合計={total}件 (詳細はdb_register.log参照)")

def insert_from_yolo_dir(yolo_dir, db_path=None):
    """
    YOLOデータセットディレクトリ（images, labels）からimages/bboxesテーブルへ登録する
    yolo_dir: YOLOデータセットのルートディレクトリ
    db_path: DBファイルパス
    """
    from pathlib import Path
    import os
    if db_path is None:
        db_path = DB_PATH
    # classes テーブルを先に準備
    register_classes_from_preset(db_path=db_path)
    yolo_dir = Path(yolo_dir)
    # train/val両対応: train優先、なければ直下
    images_dir = yolo_dir / 'images' / 'train'
    labels_dir = yolo_dir / 'labels' / 'train'
    if not images_dir.exists() or not labels_dir.exists():
        images_dir = yolo_dir / 'images'
        labels_dir = yolo_dir / 'labels'
    if not images_dir.exists() or not labels_dir.exists():
        raise FileNotFoundError(f"images_dir or labels_dir not found: {images_dir}, {labels_dir}")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    total = 0
    success = 0
    fail = 0
    empty_label = 0
    parse_error = 0
    for img_file in images_dir.glob('*'):
        if img_file.is_file() and img_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
            label_path = labels_dir / (img_file.stem + '.txt')
            if not label_path.exists():
                print(f"[SKIP] ラベルファイルが存在しない: {label_path}")
                fail += 1
                continue
            with open(label_path, 'r', encoding='utf-8') as f:
                lines = [line for line in f if line.strip()]
            if not lines:
                print(f"[SKIP] ラベルファイルが空: {label_path}")
                empty_label += 1
                continue
            valid_bbox_lines = []
            for line in lines:
                parts = line.strip().split()
                if len(parts) == 5:
                    valid_bbox_lines.append(parts)
                else:
                    parse_error += 1
                    print(f"[SKIP] bbox parse error: {label_path} 行: '{line.strip()}'")
            if not valid_bbox_lines:
                print(f"[SKIP] 有効なbboxが1件も無い: {label_path}")
                fail += 1
                continue
            c.execute('INSERT OR IGNORE INTO images (filename, image_path) VALUES (?, ?)', (img_file.name, str(img_file.resolve())))
            c.execute('SELECT id FROM images WHERE image_path=?', (str(img_file.resolve()),))
            image_id_row = c.fetchone()
            image_id = image_id_row[0] if image_id_row else None
            for parts in valid_bbox_lines:
                cid, x, y, w, h = map(float, parts)
                img_w, img_h = 1280, 960
                try:
                    import cv2
                    img = cv2.imread(str(img_file))
                    if img is not None:
                        img_h, img_w = img.shape[:2]
                except Exception:
                    pass
                cx, cy = x * img_w, y * img_h
                bw, bh = w * img_w, h * img_h
                x1 = cx - bw / 2
                y1 = cy - bh / 2
                x2 = cx + bw / 2
                y2 = cy + bh / 2
                class_master_id = int(cid)
                # id からクラス名を取得（無ければ空文字）
                c.execute('SELECT name FROM classes WHERE id=?', (class_master_id,))
                row_name = c.fetchone()
                class_name = row_name[0] if row_name else ''
                role_val = class_name if class_name else None
                cname_val = class_name
                c.execute('''INSERT INTO bboxes (image_id, cid, cname, class_master_id, conf, x1, y1, x2, y2, role) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                          (image_id, int(cid), cname_val, class_master_id, 1.0, x1, y1, x2, y2, role_val))
            print(f"[OK] 登録: {img_file.name} (bbox数={len(valid_bbox_lines)})")
            total += 1
            success += 1
    conn.commit()
    conn.close()
    print(f"YOLOディレクトリ→DB登録: 成功={success}件, 空ラベル画像={empty_label}件, bboxパースエラー={parse_error}件, 有効bboxなし={fail}件, 合計画像={total+empty_label+fail}")

if __name__ == '__main__':
    create_table()
    clear_tables()
    insert_from_json()