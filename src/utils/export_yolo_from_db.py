import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))
import sqlite3
import os
import random
import shutil
from datetime import datetime
from utils.bbox_convert import xyxy_abs_to_xywh_norm
from utils.path_manager import path_manager

DB_PATH = (path_manager.project_root / "src" / "yolo_data.db").absolute()
OUTPUT_DIR = (
    Path(__file__).parent.parent / "src" / "datasets" /
    f"yolo_dataset_exported_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)
VAL_RATIO = 0.2

# 1. DBから全画像・bbox情報を取得
conn = sqlite3.connect(str(DB_PATH))
c = conn.cursor()

# クラス名一覧（roleのdistinct）
c.execute("SELECT DISTINCT role FROM bboxes WHERE role IS NOT NULL")
classes = sorted([row[0] for row in c.fetchall() if row[0]])
class_name_to_id = {name: i for i, name in enumerate(classes)}

# 画像リスト
c.execute("SELECT id, image_path FROM images")
images = c.fetchall()  # [(id, image_path), ...]

# 2. train/val分割
random.shuffle(images)
split_idx = int(len(images) * (1 - VAL_RATIO))
train_imgs = images[:split_idx]
val_imgs = images[split_idx:]

# 3. 出力ディレクトリ作成
for sub in ["images/train", "images/val", "labels/train", "labels/val"]:
    (OUTPUT_DIR / sub).mkdir(parents=True, exist_ok=True)

# 4. クラスリスト出力
with open(OUTPUT_DIR / "classes.txt", "w", encoding="utf-8") as f:
    for c in classes:
        f.write(f"{c}\n")

# 5. 画像・ラベル出力
for subset, img_list in zip(["train", "val"], [train_imgs, val_imgs]):
    for img_id, img_path in img_list:
        img_path = Path(img_path)
        if not img_path.exists():
            # ファイル名一致で親ディレクトリから探す
            parent_dir = img_path.parent
            fname = img_path.name
            if parent_dir.exists():
                for entry in os.listdir(parent_dir):
                    if entry.lower() == fname.lower():
                        img_path = parent_dir / entry
                        break
        if not img_path.exists():
            print(
                f"[YOLO_EXPORT][除外] ファイルが存在しません: {img_path}"
            )
            continue
        # 画像コピー
        shutil.copy2(
            img_path, OUTPUT_DIR / f"images/{subset}" / img_path.name
        )
        # bbox取得
        c.execute(
            "SELECT cid, cname, conf, x1, y1, x2, y2, role "
            "FROM bboxes WHERE image_id=?",
            (img_id,)
        )
        bboxes = c.fetchall()
        label_path = OUTPUT_DIR / f"labels/{subset}" / (img_path.stem + ".txt")
        with open(label_path, "w", encoding="utf-8") as f:
            for cid, cname, conf, x1, y1, x2, y2, role in bboxes:
                class_name = role or cname
                if class_name not in class_name_to_id:
                    continue
                class_id = class_name_to_id[class_name]
                try:
                    from PIL import Image
                    with Image.open(img_path) as im:
                        img_w, img_h = im.size
                except Exception:
                    continue
                x, y, w, h = xyxy_abs_to_xywh_norm(
                    x1, y1, x2, y2, img_w, img_h
                )
                if w <= 0 or h <= 0:
                    continue
                if not (
                    0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 and 0.0 < w <= 1.0
                    and 0.0 < h <= 1.0
                ):
                    continue
                f.write(
                    f"{class_id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n"
                )

# 6. dataset.yaml出力
yaml_path = OUTPUT_DIR / "dataset.yaml"
with open(yaml_path, "w", encoding="utf-8") as f:
    f.write(f"path: {OUTPUT_DIR.absolute()}\n")
    f.write("train: images/train\n")
    f.write("val: images/val\n")
    f.write(f"names: {classes}\n")

# 7. datasetsテーブルに登録
created_at = datetime.now().isoformat(timespec='seconds')
description = f"YOLOエクスポート: images={len(images)}, classes={len(classes)}"
c.execute(
    "INSERT INTO datasets (name, path, created_at, type, description) VALUES (?, ?, ?, ?, ?)",
    (OUTPUT_DIR.name, str(OUTPUT_DIR), created_at, "yolo", description)
)
conn.commit()

print(
    f"YOLOデータセットエクスポート完了: {OUTPUT_DIR} "
    f"(DBにも記録済み)"
)
conn.close() 