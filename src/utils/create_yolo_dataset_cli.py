import argparse
import sqlite3
import os
import random
import shutil
from pathlib import Path
from datetime import datetime
from utils.bbox_convert import xyxy_abs_to_xywh_norm
import subprocess
import sys
import json
import glob
sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))
from utils.path_manager import path_manager

def import_json_if_needed(conn, json_path):
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM images")
    count = c.fetchone()[0]
    if count > 0:
        print("[INFO] imagesテーブルに既にデータが存在するためインポートをスキップ")
        return
    print(f"[INFO] JSON({json_path})からDBへインポート開始...")
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    for entry in data:
        filename = entry.get("filename")
        image_path = entry.get("image_path")
        taken_at = entry.get("taken_at")
        c.execute("INSERT INTO images (filename, image_path, taken_at) VALUES (?, ?, ?)", (filename, image_path, taken_at))
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
    print("[INFO] JSON→DBインポート完了")

def update_taken_at_from_json_dir(conn, json_dir):
    c = conn.cursor()
    json_files = glob.glob(str(Path(json_dir) / '*.json'))
    updated = 0
    for jf in json_files:
        try:
            with open(jf, encoding='utf-8') as f:
                data = json.load(f)
            image_path = data.get('image_path')
            taken_at = data.get('taken_at')
            if image_path and taken_at:
                c.execute("UPDATE images SET taken_at=? WHERE image_path=?", (taken_at, image_path))
                if c.rowcount > 0:
                    updated += 1
        except Exception as e:
            print(f"[WARN] {jf} 読み込み失敗: {e}")
    conn.commit()
    print(f"[INFO] taken_at一括更新: {updated}件")

DB_PATH = (path_manager.project_root / "yolo_data.db").absolute()


def get_new_dataset_dir(conn, base_name):
    """
    datasetsテーブルから同名データセットの個数をカウントし、
    yolo_dataset_{base_name}_{N}_{YYYYMMDD_HHMMSS} 形式で新規ディレクトリ名を生成
    """
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM datasets WHERE name LIKE ?", (f"yolo_dataset_{base_name}%",))
    count = c.fetchone()[0]
    nowstr = datetime.now().strftime('%Y%m%d_%H%M%S')
    name = f"yolo_dataset_{base_name}_{count+1}_{nowstr}"
    output_dir = Path(__file__).resolve().parent.parent / "datasets" / name
    return name, output_dir


def main():
    print(f"[DEBUG] DB_PATH: {DB_PATH}")
    if not DB_PATH.exists():
        print(f"[ERROR] DBファイルが存在しません: {DB_PATH}")
        sys.exit(1)
    parser = argparse.ArgumentParser(description="YOLOデータセット拡張CLI(SQL管理)")
    parser.add_argument('--role', type=str, default=None, help='抽出するrole名（カンマ区切り可）')
    parser.add_argument('--desc', type=str, default='', help='データセット説明')
    parser.add_argument('--output', type=str, default=None, help='出力先ディレクトリ（省略時は自動）')
    parser.add_argument('--val_ratio', type=float, default=0.2, help='val比率')
    parser.add_argument('--model', type=str, default=None, help='YOLOモデルパス（省略時はsrc/yolo/yolov8n.pt）')
    parser.add_argument('--json', type=str, default=None, help='image_preview_cache_master.jsonのパス')
    parser.add_argument('--date_from', type=str, default=None, help='撮影日(YYYY-MM-DD)以降')
    parser.add_argument('--date_to', type=str, default=None, help='撮影日(YYYY-MM-DD)以前')
    parser.add_argument('--update_taken_at', type=str, default=None, help='個別画像JSONディレクトリからtaken_atを一括更新')
    args = parser.parse_args()

    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # JSON→DB登録（必要時のみ）
    if args.json:
        import_json_if_needed(conn, args.json)

    # roleフィルタ
    roles = [r.strip() for r in args.role.split(',')] if args.role else None
    # 日付フィルタ
    date_cond = []
    date_params = []
    if args.date_from:
        date_cond.append("taken_at >= ?")
        date_params.append(args.date_from)
    if args.date_to:
        date_cond.append("taken_at <= ?")
        date_params.append(args.date_to)
    # 画像抽出クエリ
    if roles:
        q = 'SELECT DISTINCT image_id FROM bboxes WHERE ' + ' OR '.join(['role=?']*len(roles))
        c.execute(q, roles)
        image_ids = [row[0] for row in c.fetchall()]
        if not image_ids:
            print(f"[ERROR] 指定roleの画像が見つかりません: {roles}")
            return
        img_q = f"SELECT id, image_path FROM images WHERE id IN ({','.join(['?']*len(image_ids))})"
        if date_cond:
            img_q += ' AND ' + ' AND '.join(date_cond)
            c.execute(img_q, image_ids + date_params)
        else:
            c.execute(img_q, image_ids)
        images = c.fetchall()
    else:
        img_q = "SELECT id, image_path FROM images"
        if date_cond:
            img_q += ' WHERE ' + ' AND '.join(date_cond)
            c.execute(img_q, date_params)
        else:
            c.execute(img_q)
        images = c.fetchall()

    # 出力先ディレクトリ名はSQL管理
    base_name = '_'.join(roles) if roles else 'all'
    if args.output:
        output_dir = Path(args.output)
        name = output_dir.name
    else:
        name, output_dir = get_new_dataset_dir(conn, base_name)
    output_dir.mkdir(parents=True, exist_ok=True)

    # クラス名一覧
    c.execute("SELECT DISTINCT role FROM bboxes WHERE role IS NOT NULL")
    classes = sorted([row[0] for row in c.fetchall() if row[0]])
    class_name_to_id = {name: i for i, name in enumerate(classes)}

    # train/val分割
    random.shuffle(images)
    split_idx = int(len(images) * (1 - args.val_ratio))
    train_imgs = images[:split_idx]
    val_imgs = images[split_idx:]

    for sub in ["images/train", "images/val", "labels/train", "labels/val"]:
        (output_dir / sub).mkdir(parents=True, exist_ok=True)

    with open(output_dir / "classes.txt", "w", encoding="utf-8") as f:
        for c_ in classes:
            f.write(f"{c_}\n")

    for subset, img_list in zip(["train", "val"], [train_imgs, val_imgs]):
        for img_id, img_path in img_list:
            img_path = Path(img_path)
            if not img_path.exists():
                parent_dir = img_path.parent
                fname = img_path.name
                if parent_dir.exists():
                    for entry in os.listdir(parent_dir):
                        if entry.lower() == fname.lower():
                            img_path = parent_dir / entry
                            break
            if not img_path.exists():
                print(f"[YOLO_EXPORT][除外] ファイルが存在しません: {img_path}")
                continue
            shutil.copy2(
                img_path, output_dir / f"images/{subset}" / img_path.name
            )
            if roles:
                q = 'SELECT cid, cname, conf, x1, y1, x2, y2, role FROM bboxes WHERE image_id=? AND (' + ' OR '.join(['role=?']*len(roles)) + ')'
                c.execute(q, (img_id, *roles))
            else:
                c.execute("SELECT cid, cname, conf, x1, y1, x2, y2, role FROM bboxes WHERE image_id=?", (img_id,))
            bboxes = c.fetchall()
            label_path = output_dir / f"labels/{subset}" / (img_path.stem + ".txt")
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

    yaml_path = output_dir / "dataset.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(f"path: {output_dir.absolute()}\n")
        f.write("train: images/train\n")
        f.write("val: images/val\n")
        f.write(f"names: {classes}\n")

    created_at = datetime.now().isoformat(timespec='seconds')
    description = args.desc or f"YOLO拡張: role={roles if roles else 'all'} images={len(images)}"
    c.execute(
        "INSERT INTO datasets (name, path, created_at, type, description) VALUES (?, ?, ?, ?, ?)",
        (name, str(output_dir), created_at, "yolo", description)
    )
    conn.commit()
    print(f"[OK] YOLOデータセット作成・DB記録完了: {output_dir}")

    # YOLO学習自動実行
    model_path = args.model or (Path(__file__).resolve().parent.parent / "yolo" / "yolov8n.pt")
    dataset_yaml = output_dir / "dataset.yaml"
    train_cmd = [
        "yolo", "train",
        f"data={dataset_yaml}",
        f"model={model_path}",
        "epochs=10",
        "imgsz=640",
        f"project={output_dir}",
        "name=train_run"
    ]
    print(f"[INFO] YOLO学習コマンド: {' '.join(str(x) for x in train_cmd)}")
    try:
        subprocess.run(train_cmd, check=True)
    except Exception as e:
        print(f"[ERROR] YOLO学習実行時にエラー: {e}")

    # 更新のみで終了したい場合はreturn
    if not (args.json or args.role or args.date_from or args.date_to):
        conn.close()
        return

    # 更新処理
    if args.update_taken_at:
        update_taken_at_from_json_dir(conn, args.update_taken_at)

    conn.close()

if __name__ == "__main__":
    main() 