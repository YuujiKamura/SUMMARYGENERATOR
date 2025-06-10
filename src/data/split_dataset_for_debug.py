import os
from pathlib import Path
import shutil

def split_dataset_for_debug(dataset_dir: Path, group_size: int = 5):
    images_dir = dataset_dir / 'images' / 'train'
    labels_dir = dataset_dir / 'labels' / 'train'
    image_files = sorted([f for f in images_dir.glob('*.jpg')])
    label_files = sorted([f for f in labels_dir.glob('*.txt')])
    # 画像とラベルのペアのみ対象
    pairs = [(img, labels_dir / (img.stem + '.txt')) for img in image_files if (labels_dir / (img.stem + '.txt')).exists()]
    total = len(pairs)
    print(f"総ペア数: {total}")
    for i in range(0, total, group_size):
        group = pairs[i:i+group_size]
        group_id = i // group_size + 1
        out_dir = dataset_dir / f'debug_split_{group_id}'
        out_img_dir = out_dir / 'images' / 'train'
        out_lbl_dir = out_dir / 'labels' / 'train'
        out_img_dir.mkdir(parents=True, exist_ok=True)
        out_lbl_dir.mkdir(parents=True, exist_ok=True)
        for img, lbl in group:
            shutil.copy(img, out_img_dir / img.name)
            shutil.copy(lbl, out_lbl_dir / lbl.name)
        print(f"debug_split_{group_id}: {len(group)}件コピー完了")

if __name__ == '__main__':
    base_dir = Path(__file__).parent.parent / 'datasets' / 'yolo_dataset_all_3_20250610_142237'
    split_dataset_for_debug(base_dir, group_size=5) 