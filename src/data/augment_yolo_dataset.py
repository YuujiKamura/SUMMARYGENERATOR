import albumentations as A
import cv2
from pathlib import Path
import shutil
import os
from .json_to_db import insert_image_cache_record
import json

def horizontal_flip_bbox(bbox):
    # bbox: [class_id, x_center, y_center, width, height] (YOLO normalized)
    class_id, x, y, w, h = bbox
    x_flipped = 1.0 - x
    return [class_id, x_flipped, y, w, h]

def augment_dataset(dataset_dir: Path):
    images_dir = dataset_dir / 'images' / 'train'
    labels_dir = dataset_dir / 'labels' / 'train'
    for img_path in images_dir.glob('*.jpg'):
        label_path = labels_dir / (img_path.stem + '.txt')
        if not label_path.exists():
            continue
        # 画像読み込み
        image = cv2.imread(str(img_path))
        h, w = image.shape[:2]
        # ラベル読み込み
        with open(label_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        bboxes = []
        for line in lines:
            parts = line.strip().split()
            if len(parts) != 5:
                continue
            class_id, x, y, bw, bh = map(float, parts)
            bboxes.append([int(class_id), x, y, bw, bh])
        # 画像左右反転
        aug_image = cv2.flip(image, 1)
        # bboxも左右反転
        aug_bboxes = [horizontal_flip_bbox(b) for b in bboxes]
        # 保存
        aug_img_name = f'aug_{img_path.name}'
        aug_label_name = f'aug_{img_path.stem}.txt'
        aug_img_path = images_dir / aug_img_name
        aug_label_path = labels_dir / aug_label_name
        cv2.imwrite(str(aug_img_path), aug_image)
        with open(aug_label_path, 'w', encoding='utf-8') as f:
            for b in aug_bboxes:
                f.write(f"{b[0]} {b[1]:.6f} {b[2]:.6f} {b[3]:.6f} {b[4]:.6f}\n")
        # DBにも登録
        # YOLO bboxをDB用に変換（cid, cname, conf, xyxy, role）形式は元データに合わせる
        # ここではcidのみ、他は空やNoneで仮登録
        db_bboxes = []
        for b in aug_bboxes:
            db_bboxes.append({
                "cid": int(b[0]),
                "cname": "",  # 必要ならクラス名リスト参照
                "conf": 1.0,
                "xyxy": [],  # 必要なら変換
                "role": None
            })
        insert_image_cache_record(
            filename=aug_img_name,
            image_path=str(aug_img_path.resolve()),
            bboxes=db_bboxes
        )

def main():
    dataset_dir = Path(__file__).parent.parent / 'datasets' / 'yolo_dataset_all_3_20250610_142237'
    augment_dataset(dataset_dir)

if __name__ == '__main__':
    main() 