import sqlite3
import json
from pathlib import Path
import shutil
import os
from typing import List

def export_yolo_dataset_from_db(db_path: Path, out_dir: Path, offset: int = 0, limit: int = 5):
    images_dir = out_dir / 'images' / 'train'
    labels_dir = out_dir / 'labels' / 'train'
    # 既存の出力先をクリア
    if out_dir.exists():
        shutil.rmtree(out_dir)
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT filename, image_path, bboxes FROM image_cache LIMIT ? OFFSET ?", (limit, offset))
    rows = c.fetchall()
    for filename, image_path, bboxes_json in rows:
        # 画像コピー
        src_img = Path(image_path)
        if not src_img.exists():
            print(f"[警告] 画像が存在しません: {src_img}")
            continue
        dst_img = images_dir / src_img.name
        shutil.copy(src_img, dst_img)
        # bboxラベル書き出し
        try:
            bboxes = json.loads(bboxes_json)
        except Exception as e:
            print(f"[警告] bboxデコード失敗: {filename}: {e}")
            continue
        label_path = labels_dir / (src_img.stem + '.txt')
        with open(label_path, 'w', encoding='utf-8') as f:
            for bbox in bboxes:
                # YOLO形式 [class, x, y, w, h] or dict
                if isinstance(bbox, dict):
                    # xyxy→xywh正規化変換が必要な場合はここで
                    vals = bbox.get('bbox') or bbox.get('xywh') or bbox.get('xyxy')
                    if vals and len(vals) == 4:
                        # ここではxywh正規化済み前提
                        class_id = bbox.get('cid', 0)
                        x, y, w, h = [float(v) for v in vals]
                        # 0.0〜1.0でクリッピング
                        x = max(0.0, min(1.0, x))
                        y = max(0.0, min(1.0, y))
                        w = max(0.0, min(1.0, w))
                        h = max(0.0, min(1.0, h))
                        f.write(f"{class_id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")
                elif isinstance(bbox, list) and len(bbox) >= 5:
                    class_id = int(bbox[0])
                    x = max(0.0, min(1.0, float(bbox[1])))
                    y = max(0.0, min(1.0, float(bbox[2])))
                    w = max(0.0, min(1.0, float(bbox[3])))
                    h = max(0.0, min(1.0, float(bbox[4])))
                    f.write(f"{class_id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")
    conn.close()
    print(f"{len(rows)}件分のYOLOデータセットを書き出しました: {out_dir}")

if __name__ == '__main__':
    db_path = Path(__file__).parent.parent / 'data' / 'model_training_cache.db'
    out_dir = Path(__file__).parent.parent / 'datasets' / 'debug_yolo_from_db'
    export_yolo_dataset_from_db(db_path, out_dir, offset=0, limit=5)