import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))
import sqlite3
import json
from datetime import datetime
from utils.path_manager import path_manager

DB_PATH = (path_manager.project_root / "yolo_data.db").absolute()
JSON_PATH = path_manager.project_root / "data" / "image_preview_cache_master.json"

def init_db():
    print(f"[DEBUG] DB_PATH: {DB_PATH} exists={DB_PATH.exists()}")
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        image_path TEXT UNIQUE,
        taken_at TEXT  -- 撮影日（NULL可）
    )
    """)
    c.execute("PRAGMA table_info(images)")
    columns = [row[1] for row in c.fetchall()]
    print(f"[DEBUG] imagesテーブルカラム: {columns}")
    c.execute("""
    CREATE TABLE IF NOT EXISTS bboxes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        image_id INTEGER,
        cid INTEGER,
        cname TEXT,
        conf REAL,
        x1 REAL,
        y1 REAL,
        x2 REAL,
        y2 REAL,
        role TEXT,
        FOREIGN KEY(image_id) REFERENCES images(id)
    )
    """)
    c.execute('''
        CREATE TABLE IF NOT EXISTS datasets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            path TEXT NOT NULL,
            created_at TEXT NOT NULL,
            type TEXT,
            description TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS chain_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            remarks TEXT,
            photo_category TEXT,
            extra_json TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS image_chain_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id INTEGER,
            chain_record_id INTEGER,
            assigned_at TEXT,
            FOREIGN KEY(image_id) REFERENCES images(id),
            FOREIGN KEY(chain_record_id) REFERENCES chain_records(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            description TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS image_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id INTEGER,
            role_id INTEGER,
            FOREIGN KEY(image_id) REFERENCES images(id),
            FOREIGN KEY(role_id) REFERENCES roles(id)
        )
    ''')
    conn.commit()
    conn.close()

def migrate_add_taken_at(conn):
    c = conn.cursor()
    c.execute("PRAGMA table_info(images)")
    columns = [row[1] for row in c.fetchall()]
    if 'taken_at' not in columns:
        print('[INFO] imagesテーブルにtaken_atカラムを追加します')
        c.execute("ALTER TABLE images ADD COLUMN taken_at TEXT")
        conn.commit()
    else:
        print('[INFO] imagesテーブルには既にtaken_atカラムがあります')

    # 既存テーブルにUNIQUE制約がなければ追加
    c.execute("PRAGMA index_list(images)")
    indexes = [row[1] for row in c.fetchall()]
    if 'idx_images_image_path' not in indexes:
        try:
            c.execute("CREATE UNIQUE INDEX idx_images_image_path ON images(image_path)")
        except sqlite3.OperationalError:
            pass

def import_json(conn, json_path):
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    c = conn.cursor()
    for entry in data:
        filename = entry.get("filename")
        image_path = entry.get("image_path")
        c.execute("INSERT INTO images (filename, image_path) VALUES (?, ?)", (filename, image_path))
        image_id = c.lastrowid
        for bbox in entry.get("bboxes", []):
            cid = bbox.get("cid")
            cname = bbox.get("cname")
            conf = bbox.get("conf")
            xyxy = bbox.get("xyxy")
            role = bbox.get("role")
            if xyxy and len(xyxy) == 4:
                x1, y1, x2, y2 = xyxy
                c.execute("""
                    INSERT INTO bboxes (image_id, cid, cname, conf, x1, y1, x2, y2, role)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (image_id, cid, cname, conf, x1, y1, x2, y2, role))
    conn.commit()

def main():
    conn = sqlite3.connect(DB_PATH)
    init_db()
    migrate_add_taken_at(conn)
    import_json(conn, JSON_PATH)
    print(f"DB初期化・インポート完了: {DB_PATH}")
    conn.close()

if __name__ == "__main__":
    main()