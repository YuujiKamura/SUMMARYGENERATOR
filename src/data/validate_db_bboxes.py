import sqlite3
import json
from pathlib import Path

def safe_float(v):
    try:
        return float(v)
    except Exception:
        return 0.0

def clip01(x):
    try:
        return max(0.0, min(1.0, float(x)))
    except Exception:
        return 0.0

def validate_bboxes_in_db(db_path: Path, auto_fix: bool = True):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT filename, bboxes FROM image_cache")
    for filename, bboxes_json in c.fetchall():
        try:
            bboxes = json.loads(bboxes_json)
        except Exception as e:
            print(f"[バリデーション] {filename}: JSON decode error: {e}")
            continue
        fixed = False
        for i, bbox in enumerate(bboxes):
            if isinstance(bbox, dict):
                vals = bbox.get('xyxy') or bbox.get('bbox') or []
                if not vals:
                    vals = [bbox.get(k) for k in ['x', 'y', 'w', 'h'] if k in bbox]
                # クリップ処理
                if vals:
                    new_vals = [clip01(v) for v in vals]
                    if new_vals != vals:
                        fixed = True
                        # dictの該当キーに上書き
                        if bbox.get('xyxy') is not None:
                            bbox['xyxy'] = new_vals
                        elif bbox.get('bbox') is not None:
                            bbox['bbox'] = new_vals
                        else:
                            for k, v in zip(['x', 'y', 'w', 'h'], new_vals):
                                if k in bbox:
                                    bbox[k] = v
            else:
                # list形式 [class, x, y, w, h]
                if len(bbox) >= 5:
                    new_vals = [clip01(v) for v in bbox[1:5]]
                    if new_vals != bbox[1:5]:
                        fixed = True
                        bbox[1:5] = new_vals
        if fixed:
            print(f"[バリデーション] {filename}: bbox値を0.0～1.0に正規化しました")
            c.execute("UPDATE image_cache SET bboxes=? WHERE filename=?", (json.dumps(bboxes, ensure_ascii=False), filename))
    conn.commit()
    # 件数カウント
    c.execute("SELECT COUNT(*) FROM image_cache")
    count = c.fetchone()[0]
    conn.close()
    print(f"DB内bbox値のバリデーション・正規化が完了しました（画像件数: {count}）")
