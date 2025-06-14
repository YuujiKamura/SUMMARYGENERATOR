import cv2
from pathlib import Path
from src.bbox.types import BBoxYOLO
from src.data.json_to_db import insert_image_cache_record
import logging

def save_and_log(img_path, aug_img, aug_boxes, tag, out_dir=None, db_path=None):
    logger = logging.getLogger('augment')
    out_dir = Path(out_dir) if out_dir else img_path.parent
    aug_img_name = f'aug_{tag}_{img_path.name}'
    aug_img_path = out_dir / aug_img_name
    cv2.imwrite(str(aug_img_path), aug_img)
    # ラベル保存
    label_dir = out_dir.parent.parent / 'labels' / 'train'
    label_dir.mkdir(parents=True, exist_ok=True)  # ここで必ず作成
    label_path = label_dir / (aug_img_path.stem + '.txt')
    with open(label_path, 'w', encoding='utf-8') as f:
        for b in aug_boxes:
            f.write(f"{b.cid} {b.x:.6f} {b.y:.6f} {b.w:.6f} {b.h:.6f}\n")
    # DB登録
    db_bboxes = [{
        "cid": int(b.cid),
        "cname": "",
        "conf": 1.0,
        "xyxy": [],
        "role": None
    } for b in aug_boxes]
    insert_image_cache_record(
        filename=aug_img_name,
        image_path=str(aug_img_path.resolve()),
        bboxes=db_bboxes,
        db_path=db_path
    )
