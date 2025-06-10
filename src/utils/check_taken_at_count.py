import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))
from utils.path_manager import path_manager
import sqlite3

DB_PATH = path_manager.project_root / "src" / "yolo_data.db"

def main():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    date = '2025-05-30'
    c.execute("SELECT COUNT(*), MIN(image_path) FROM images WHERE taken_at=?", (date,))
    count, sample = c.fetchone()
    print(f"taken_at={date} の画像件数: {count}")
    if sample:
        print(f"サンプル画像パス: {sample}")
    else:
        print("該当画像なし")
    conn.close()

if __name__ == "__main__":
    main() 