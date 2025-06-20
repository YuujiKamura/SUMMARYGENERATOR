import sqlite3
from pathlib import Path
from typing import List, Optional, Any, Dict
import json
from src.utils.role_mapping_utils import normalize_role_name

DB_PATH = Path(__file__).resolve().parent / "yolo_data.db"
JSON_PATH = Path(__file__).resolve().parent / "data" / "image_preview_cache_master.json"

def init_db(db_path: Path = DB_PATH):
    with sqlite3.connect(str(db_path)) as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            image_path TEXT UNIQUE,
            taken_at TEXT,
            location TEXT
        )
        """)
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
                location TEXT,
                controls TEXT,
                photo_category TEXT,
                work_category TEXT,
                type TEXT,
                subtype TEXT,
                remarks TEXT,
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
        c.execute('''
            CREATE TABLE IF NOT EXISTS role_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_name TEXT UNIQUE,
                mapping_json TEXT
            )
        ''')
        # SurveyPoint テーブル
        c.execute('''
            CREATE TABLE IF NOT EXISTS survey_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_id INTEGER UNIQUE,
                location TEXT,
                date_value TEXT,
                count_value TEXT,
                date_count TEXT,
                values_json TEXT,
                inferred_json TEXT,
                capture_time REAL,
                FOREIGN KEY(image_id) REFERENCES images(id)
            )
        ''')
        # UNIQUE制約インデックス
        c.execute("PRAGMA index_list(images)")
        indexes = [row[1] for row in c.fetchall()]
        if 'idx_images_image_path' not in indexes:
            try:
                c.execute("CREATE UNIQUE INDEX idx_images_image_path ON images(image_path)")
            except sqlite3.OperationalError:
                pass
        conn.commit()

class DBConnection:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
    def __enter__(self):
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        return self.conn
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()

class ImageManager:
    @staticmethod
    def get_all_images() -> List[Dict[str, Any]]:
        with DBConnection() as conn:
            cur = conn.execute("SELECT * FROM images")
            return [dict(row) for row in cur.fetchall()]
    @staticmethod
    def add_image(filename: str, image_path: str, taken_at: Optional[str]=None, location: Optional[str]=None) -> int:
        with DBConnection() as conn:
            cur = conn.execute(
                "INSERT INTO images (filename, image_path, taken_at, location) VALUES (?, ?, ?, ?)",
                (filename, image_path, taken_at, location)
            )
            conn.commit()
            return cur.lastrowid

class BBoxManager:
    @staticmethod
    def get_bboxes_for_image(image_id: int) -> List[Dict[str, Any]]:
        with DBConnection() as conn:
            cur = conn.execute("SELECT * FROM bboxes WHERE image_id=?", (image_id,))
            return [dict(row) for row in cur.fetchall()]
    @staticmethod
    def add_bbox(image_id: int, cid: int, cname: str, conf: float, x1: float, y1: float, x2: float, y2: float, role: Optional[str]=None) -> int:
        with DBConnection() as conn:
            cur = conn.execute(
                "INSERT INTO bboxes (image_id, cid, cname, conf, x1, y1, x2, y2, role) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (image_id, cid, cname, conf, x1, y1, x2, y2, role)
            )
            conn.commit()
            return cur.lastrowid

class RoleManager:
    @staticmethod
    def get_all_roles() -> List[Dict[str, Any]]:
        with DBConnection() as conn:
            cur = conn.execute("SELECT * FROM roles")
            return [dict(row) for row in cur.fetchall()]
    @staticmethod
    def add_role(name: str, description: Optional[str]=None) -> int:
        with DBConnection() as conn:
            cur = conn.execute(
                "INSERT INTO roles (name, description) VALUES (?, ?)",
                (name, description)
            )
            conn.commit()
            return cur.lastrowid
    @staticmethod
    def assign_role_to_image(image_id: int, role_id: int) -> int:
        with DBConnection() as conn:
            cur = conn.execute(
                "INSERT INTO image_roles (image_id, role_id) VALUES (?, ?)",
                (image_id, role_id)
            )
            conn.commit()
            return cur.lastrowid
    @staticmethod
    def get_roles_for_image(image_id: int) -> List[Dict[str, Any]]:
        with DBConnection() as conn:
            cur = conn.execute(
                "SELECT r.* FROM roles r JOIN image_roles ir ON r.id = ir.role_id WHERE ir.image_id = ?",
                (image_id,)
            )
            return [dict(row) for row in cur.fetchall()]

class ChainRecordManager:
    @staticmethod
    def get_all_chain_records(db_path=DB_PATH) -> List[Dict[str, Any]]:
        with DBConnection(db_path) as conn:
            cur = conn.execute("SELECT * FROM chain_records")
            return [dict(row) for row in cur.fetchall()]
    @staticmethod
    def add_chain_record(location: Optional[str]=None, controls: Optional[list]=None, photo_category: Optional[str]=None, extra_json: Optional[str]=None, db_path=DB_PATH, work_category: Optional[str]=None, type_: Optional[str]=None, subtype: Optional[str]=None, remarks: Optional[str]=None) -> int:
        # controlsはリスト→JSON文字列
        controls_json = json.dumps(controls, ensure_ascii=False) if controls is not None else None
        with DBConnection(db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO chain_records (location, controls, photo_category, work_category, type, subtype, remarks, extra_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (location, controls_json, photo_category, work_category, type_, subtype, remarks, extra_json)
            )
            conn.commit()
            return cur.lastrowid
    @staticmethod
    def assign_chain_record_to_image(image_id: int, chain_record_id: int) -> int:
        with DBConnection() as conn:
            cur = conn.execute(
                "INSERT INTO image_chain_assignments (image_id, chain_record_id, assigned_at) VALUES (?, ?, datetime('now'))",
                (image_id, chain_record_id)
            )
            conn.commit()
            return cur.lastrowid
    @staticmethod
    def get_chain_records_for_image(image_id: int) -> List[Dict[str, Any]]:
        with DBConnection() as conn:
            cur = conn.execute(
                "SELECT cr.* FROM chain_records cr JOIN image_chain_assignments ica ON cr.id = ica.chain_record_id WHERE ica.image_id = ?",
                (image_id,)
            )
            return [dict(row) for row in cur.fetchall()]

class RoleMappingManager:
    @staticmethod
    def get_all_role_mappings(db_path=DB_PATH) -> list:
        with DBConnection(db_path) as conn:
            cur = conn.execute("SELECT * FROM role_mappings")
            return [dict(row) for row in cur.fetchall()]

    @staticmethod
    def get_role_mapping(role_name: str, db_path=DB_PATH) -> dict:
        with DBConnection(db_path) as conn:
            cur = conn.execute("SELECT * FROM role_mappings WHERE role_name = ?", (role_name,))
            row = cur.fetchone()
            return dict(row) if row else None

    @staticmethod
    def add_or_update_role_mapping(role_name: str, mapping_json: str, db_path=DB_PATH) -> int:
        # ここでrole_nameを正規化
        role_name = normalize_role_name(role_name)
        with DBConnection(db_path) as conn:
            cur = conn.execute(
                "INSERT INTO role_mappings (role_name, mapping_json) VALUES (?, ?) ON CONFLICT(role_name) DO UPDATE SET mapping_json=excluded.mapping_json",
                (role_name, mapping_json)
            )
            conn.commit()
            cur = conn.execute("SELECT id FROM role_mappings WHERE role_name = ?", (role_name,))
            row = cur.fetchone()
            return row["id"] if row else -1

    @staticmethod
    def delete_role_mapping(role_name: str, db_path=DB_PATH) -> None:
        with DBConnection(db_path) as conn:
            conn.execute("DELETE FROM role_mappings WHERE role_name = ?", (role_name,))
            conn.commit()

def import_image_preview_cache_json(json_path: Path = JSON_PATH, db_path: Path = DB_PATH):
    init_db(db_path)  # 追加: 必ず初期化
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    with DBConnection(db_path) as conn:
        for entry in data:
            filename = entry.get("filename")
            image_path = entry.get("image_path")
            cur = conn.execute(
                "SELECT id FROM images WHERE image_path = ?",
                (image_path,)
            )
            row = cur.fetchone()
            if row is None:
                cur = conn.execute(
                    "INSERT INTO images (filename, image_path) VALUES (?, ?)",
                    (filename, image_path)
                )
                image_id = cur.lastrowid
            else:
                image_id = row["id"]
            for bbox in entry.get("bboxes", []):
                cid = bbox.get("cid")
                cname = bbox.get("cname")
                conf = bbox.get("conf")
                xyxy = bbox.get("xyxy")
                role = bbox.get("role")
                if xyxy and len(xyxy) == 4:
                    x1, y1, x2, y2 = xyxy
                    conn.execute(
                        "INSERT INTO bboxes (image_id, cid, cname, conf, x1, y1, x2, y2, role) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (image_id, cid, cname, conf, x1, y1, x2, y2, role)
                    )
        conn.commit()

def reset_all_tables(db_path=DB_PATH):
    with DBConnection(db_path) as conn:
        conn.execute('DELETE FROM chain_records')
        conn.execute('DELETE FROM images')
        conn.execute('DELETE FROM roles')
        conn.execute('DELETE FROM bboxes')
        conn.execute('DELETE FROM image_roles')
        conn.execute('DELETE FROM image_chain_assignments')
        conn.execute('DELETE FROM role_mappings')
        conn.commit()

class SurveyPointManager:
    @staticmethod
    def upsert_survey_point(image_id: int, sp_dict: dict, conn: sqlite3.Connection | None = None):
        """image_id をキーに survey_points を挿入 or 更新"""
        own_conn = False
        if conn is None:
            conn = DBConnection().__enter__()
            own_conn = True
        cur = conn.execute("SELECT id FROM survey_points WHERE image_id=?", (image_id,))
        row = cur.fetchone()
        location = sp_dict.get("location_value") or sp_dict.get("inferred_location")
        date_val = sp_dict.get("date_value")
        count_val = sp_dict.get("count_value")
        date_count = sp_dict.get("inferred_date_count") or sp_dict.get("date_count")
        values_json = json.dumps(sp_dict.get("values", {}), ensure_ascii=False)
        inferred_json = json.dumps(sp_dict.get("inferred_values", {}), ensure_ascii=False)
        capture_time = sp_dict.get("capture_time")
        if row:
            conn.execute(
                """UPDATE survey_points SET location=?, date_value=?, count_value=?, date_count=?, values_json=?, inferred_json=?, capture_time=? WHERE image_id=?""",
                (location, date_val, count_val, date_count, values_json, inferred_json, capture_time, image_id)
            )
        else:
            conn.execute(
                """INSERT INTO survey_points (image_id, location, date_value, count_value, date_count, values_json, inferred_json, capture_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (image_id, location, date_val, count_val, date_count, values_json, inferred_json, capture_time)
            )
        if own_conn:
            conn.commit()
            conn.close()

# --- Migration helpers -------------------------------------------------

def ensure_images_columns():
    """既存 images テーブルに location / taken_at カラムが無ければ追加する"""
    with DBConnection() as conn:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(images)").fetchall()]
        if 'taken_at' not in cols:
            conn.execute("ALTER TABLE images ADD COLUMN taken_at TEXT")
        if 'location' not in cols:
            conn.execute("ALTER TABLE images ADD COLUMN location TEXT")
        conn.commit()