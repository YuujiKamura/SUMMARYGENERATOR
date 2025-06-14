import sys
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP, getcontext
import albumentations as A
import cv2
import numpy as np
import string
import random
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.utils.bbox_convert import xywh_norm_to_xyxy_abs, xyxy_abs_to_xywh_norm
from src.utils.bbox_normalizer import is_bbox_valid_yolo, convert_bbox_to_yolo
from src.data.json_to_db import insert_image_cache_record
from src.data.db_to_yolo_dataset import fetch_all_records
# --- 追加: bbox/transform, io/image_ioからimport ---
from src.bbox.transform import horizontal_flip_bbox, norm01, is_bbox_valid, clip_bbox_with_imgsize, clip01, clip_bbox01
from src.io.image_io import safe_imread_with_temp

getcontext().prec = 10  # 精度を十分に確保

# --- 旧augment_dataset, augment_dataset_from_db, mainを全て削除 ---
# 新しいrunner.pyを使う形に置換
if __name__ == '__main__':
    from src.augment.runner import main as augment_main
    import sys
    dataset_dir = sys.argv[1] if len(sys.argv) > 1 else None
    augment_main(dataset_dir)