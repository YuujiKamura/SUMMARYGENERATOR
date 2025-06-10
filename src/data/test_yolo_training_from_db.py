import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import sqlite3
import math
from pathlib import Path as _Path
import time
import argparse
from src.data.generate_yolo_dataset_from_db import export_yolo_dataset_from_db

def get_total_records(db_path: _Path) -> int:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM image_cache")
    total = c.fetchone()[0]
    conn.close()
    return total

def run_yolo_train(dataset_dir: _Path, group_id: int) -> bool:
    # dataset.yamlの自動生成（最小構成）
    yaml_path = dataset_dir / 'dataset.yaml'
    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write(f"""
train: {dataset_dir / 'images' / 'train'}
val: {dataset_dir / 'images' / 'train'}
nc: 80
names: [class0,class1,class2,class3,class4,class5,class6,class7,class8,class9,class10,class11,class12,class13,class14,class15,class16,class17,class18,class19,class20,class21,class22,class23,class24,class25,class26,class27,class28,class29,class30,class31,class32,class33,class34,class35,class36,class37,class38,class39,class40,class41,class42,class43,class44,class45,class46,class47,class48,class49,class50,class51,class52,class53,class54,class55,class56,class57,class58,class59,class60,class61,class62,class63,class64,class65,class66,class67,class68,class69,class70,class71,class72,class73,class74,class75,class76,class77,class78,class79]
""")
    # YOLOv8学習（ultralytics Python API）
    try:
        from ultralytics import YOLO
        model = YOLO('yolov8n.pt')
        model.train(
            data=str(yaml_path),
            epochs=1,
            project=str(dataset_dir),
            name=f'exp_group_{group_id}',
            exist_ok=True,
            verbose=True
        )
        return True
    except Exception as e:
        print(f"[ERROR] Group {group_id} 学習中に例外: {e}")
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=int, default=None, help='開始グループ番号（0始まり）')
    parser.add_argument('--end', type=int, default=None, help='終了グループ番号（0始まり, この番号は含まない）')
    args = parser.parse_args()

    db_path = Path(__file__).parent.parent / 'data' / 'model_training_cache.db'
    total = get_total_records(db_path)
    group_size = 5
    num_groups = math.ceil(total / group_size)
    failed_groups = []

    start = args.start if args.start is not None else 0
    end = args.end if args.end is not None else num_groups
    print(f'グループ範囲: {start+1}～{end}（全{num_groups}グループ中）')

    for group_id in range(start, end):
        offset = group_id * group_size
        out_dir = Path(__file__).parent.parent / 'datasets' / f'debug_yolo_from_db_group_{group_id+1}'
        print(f"\n=== Group {group_id+1}/{num_groups} (offset={offset}) ===")
        export_yolo_dataset_from_db(db_path, out_dir, offset=offset, limit=group_size)
        time.sleep(1)  # I/O待ち
        success = run_yolo_train(out_dir, group_id+1)
        if not success:
            failed_groups.append(group_id+1)
    print("\n=== テスト完了 ===")
    if failed_groups:
        print(f"失敗したグループ: {failed_groups}")
    else:
        print("全グループで学習成功")

if __name__ == '__main__':
    main()