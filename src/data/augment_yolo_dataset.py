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

getcontext().prec = 10  # 精度を十分に確保

def horizontal_flip_bbox(bbox):
    # bbox: [class_id, x_center, y_center, width, height] (YOLO normalized)
    class_id, x, y, w, h = bbox
    x_flipped = 1.0 - x
    return [class_id, x_flipped, y, w, h]

def norm01(x):
    return float(max(Decimal('0.0'), min(Decimal(str(x)), Decimal('1.0'))))

def is_bbox_valid(b):
    # 旧: YOLO正規化bboxが完全に0.0～1.0範囲内か
    return is_bbox_valid_yolo(*b)

def clip_bbox_with_imgsize(b, img_w, img_h):
    # b: [class_id, x, y, w, h] (YOLO形式, 0.0-1.0)
    class_id, x, y, w, h = b
    # Decimalで計算
    x = Decimal(str(x))
    y = Decimal(str(y))
    w = Decimal(str(w))
    h = Decimal(str(h))
    img_w_d = Decimal(str(img_w))
    img_h_d = Decimal(str(img_h))
    # 1. YOLO正規化→絶対座標
    x1, y1, x2, y2 = xywh_norm_to_xyxy_abs(float(x), float(y), float(w), float(h), int(img_w), int(img_h))
    x1 = Decimal(str(x1)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    y1 = Decimal(str(y1)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    x2 = Decimal(str(x2)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    y2 = Decimal(str(y2)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    # 2. 画像サイズでclip
    x1 = max(Decimal('0.0'), min(x1, img_w_d))
    y1 = max(Decimal('0.0'), min(y1, img_h_d))
    x2 = max(Decimal('0.0'), min(x2, img_w_d))
    y2 = max(Decimal('0.0'), min(y2, img_h_d))
    # 3. 幅・高さが0以下なら除外
    if x2 <= x1 or y2 <= y1:
        return None
    # 4. 再度YOLO正規化
    x_c, y_c, w_c, h_c = xyxy_abs_to_xywh_norm(float(x1), float(y1), float(x2), float(y2), int(img_w), int(img_h))
    x_c = Decimal(str(x_c)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    y_c = Decimal(str(y_c)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    w_c = Decimal(str(w_c)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    h_c = Decimal(str(h_c)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    # 5. 0.0-1.0にclip
    x_c = max(Decimal('0.0'), min(x_c, Decimal('1.0')))
    y_c = max(Decimal('0.0'), min(y_c, Decimal('1.0')))
    w_c = max(Decimal('0.0'), min(w_c, Decimal('1.0')))
    h_c = max(Decimal('0.0'), min(h_c, Decimal('1.0')))
    if w_c <= 0 or h_c <= 0:
        return None
    return [class_id, float(x_c), float(y_c), float(w_c), float(h_c)]

def clip01(x):
    return max(0.0, min(1.0, float(x)))

def safe_imread_with_temp(src_path):
    """
    日本語・全角記号を含むパスの場合、C:\\temp_yolo_imagesに一時コピーし、
    半角英数字ファイル名でcv2.imreadする。
    """
    import cv2
    import shutil
    import re
    src_path = str(src_path)
    if re.search(r'[^\x00-\x7F]', src_path):
        temp_dir = Path('C:/temp_yolo_images')
        temp_dir.mkdir(parents=True, exist_ok=True)
        ext = Path(src_path).suffix
        randname = ''.join(random.choices(string.ascii_letters + string.digits, k=16)) + ext
        temp_path = temp_dir / randname
        try:
            shutil.copy2(src_path, temp_path)
            img = cv2.imread(str(temp_path))
            temp_path.unlink(missing_ok=True)
            return img
        except Exception as e:
            print(f'[警告] テンポラリコピー失敗: {src_path} → {temp_path} ({e})')
            return None
    else:
        return cv2.imread(src_path)

def augment_dataset(dataset_dir: Path, augment_num: int = 5):
    images_dir = dataset_dir / 'images' / 'train'
    labels_dir = dataset_dir / 'labels' / 'train'
    for img_path in images_dir.glob('*.jpg'):
        # aug_で始まる画像はスキップ（多重拡張防止）
        if img_path.name.startswith('aug'):
            continue
        label_path = labels_dir / (img_path.stem + '.txt')
        if not label_path.exists():
            continue
        # 画像読み込み
        image = safe_imread_with_temp(img_path)
        if image is None:
            print(f'[警告] 画像読み込み失敗: {img_path}')
            continue
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
        # --- 追加: 元データbboxが範囲外ならスキップ ---
        invalid_bboxes = [b for b in bboxes if not is_bbox_valid([b[1], b[2], b[3], b[4]])]
        print(f"[DEBUG] {img_path.name} チェック中 bbox: {bboxes} → 異常: {invalid_bboxes}")
        if invalid_bboxes:
            print(f"[警告] {img_path.name} のbboxに0.0～1.0範囲外の値が含まれるため、オーグメント処理をスキップします。対象bbox: {invalid_bboxes}")
            continue
        for i in range(augment_num):
            if i == 0:
                # 1回目は左右反転のみ
                aug_image = cv2.flip(image, 1)
                aug_bboxes = [horizontal_flip_bbox(b) for b in bboxes]
                aug_type = 'flip'
            else:
                # 2回目以降は色変換・ノイズ系を多めに適用
                # 色変換・ノイズ系を3回、その他（例: 追加のflipや他の拡張）は1回程度
                if i <= 3:
                    aug = A.Compose([
                        A.RandomBrightnessContrast(p=0.8),
                        A.HueSaturationValue(p=0.8),
                        A.GaussNoise(p=0.8),
                    ], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels']))
                else:
                    aug = A.Compose([
                        A.HorizontalFlip(p=0.5),
                        A.RandomBrightnessContrast(p=0.5),
                        A.HueSaturationValue(p=0.5),
                        A.GaussNoise(p=0.3),
                    ], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels']))
                yolo_bboxes = [[clip01(b[1]), clip01(b[2]), clip01(b[3]), clip01(b[4])] for b in bboxes]
                class_labels = [b[0] for b in bboxes]
                valid_bboxes = [bb for bb in yolo_bboxes if is_bbox_valid(bb)]
                valid_labels = [cl for bb, cl in zip(yolo_bboxes, class_labels) if is_bbox_valid(bb)]
                valid_bboxes = [[max(0.0, min(1.0, v)) for v in bb] for bb in valid_bboxes]
                if not valid_bboxes or all(not all(0.0 <= float(x) <= 1.0 for x in bb) for bb in valid_bboxes):
                    continue
                augmented = aug(image=image, bboxes=valid_bboxes, class_labels=valid_labels)
                aug_image = augmented['image']
                aug_bboxes = [[cl] + list(bb) for cl, bb in zip(augmented['class_labels'], augmented['bboxes'])]
                for b in aug_bboxes:
                    b[1:5] = np.clip(b[1:5], 0.0, 1.0)
                aug_bboxes = [b for b in aug_bboxes if all(0.0 <= float(x) <= 1.0 for x in b[1:5])]
                for b in aug_bboxes:
                    for j in range(1, 5):
                        b[j] = max(0.0, min(1.0, float(b[j])))
                aug_type = 'color_noise'
            # bbox値をclip_bbox_with_imgsizeで補正
            aug_bboxes = [clip_bbox_with_imgsize(b, w, h) for b in aug_bboxes]
            aug_bboxes = [b for b in aug_bboxes if b is not None]
            if not aug_bboxes:
                continue
            aug_img_name = f'aug{i+1}_{img_path.name}'
            aug_label_name = f'aug{i+1}_{img_path.stem}.txt'
            aug_img_path = images_dir / aug_img_name
            aug_label_path = labels_dir / aug_label_name
            cv2.imwrite(str(aug_img_path), aug_image)
            with open(aug_label_path, 'w', encoding='utf-8') as f:
                for b in aug_bboxes:
                    f.write(f"{b[0]} {b[1]:.6f} {b[2]:.6f} {b[3]:.6f} {b[4]:.6f}\n")
            # --- 追加: 生成ログ出力（上書き対応） ---
            logs_dir = Path(__file__).parent.parent.parent / 'logs'
            logs_dir.mkdir(exist_ok=True)
            gen_log_path = logs_dir / '03_augment_generated.log'
            if i == 0 and not gen_log_path.exists():
                log_mode = 'w'
            else:
                log_mode = 'a'
            with open(gen_log_path, log_mode, encoding='utf-8') as logf:
                logf.write(f'[AUGMENT] type: {aug_type}, file: {aug_img_name}, bbox_count: {len(aug_bboxes)}\n')
            # DBにも登録
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

def augment_dataset_from_db(augment_num: int = 5):
    import json
    records = fetch_all_records()
    for filename, image_path, bboxes in records:
        img_path = Path(image_path)
        if not img_path.exists():
            print(f'[警告] 画像ファイルが存在しません: {img_path}')
            continue
        image = safe_imread_with_temp(img_path)
        if image is None:
            print(f'[警告] 画像読み込み失敗: {img_path}')
            continue
        h, w = image.shape[:2]
        try:
            bbox_list = json.loads(bboxes) if isinstance(bboxes, str) else bboxes
        except Exception as e:
            print(f'[警告] bboxパース失敗: {bboxes} ({e})')
            continue
        # YOLO形式に変換（[class_id, x, y, w, h]）
        bboxes_yolo = []
        for bbox in bbox_list:
            try:
                class_id, x_c, y_c, bw, bh = convert_bbox_to_yolo(bbox, w, h)
                bboxes_yolo.append([class_id, x_c, y_c, bw, bh])
            except Exception as e:
                continue
        # --- ここでw>0, h>0なbboxだけにフィルタ ---
        bboxes_yolo = [b for b in bboxes_yolo if is_bbox_valid_yolo(*b[1:5])]
        if not bboxes_yolo:
            log_path = Path(__file__).parent.parent.parent / 'logs' / '03_augment_invalid_bboxes.log'
            log_mode = 'w' if not log_path.exists() else 'a'
            with open(log_path, log_mode, encoding='utf-8') as logf:
                logf.write(f'[filename: {filename}] 無効bboxでスキップ\n')
                logf.write(f'  image_path: {img_path}\n')
                logf.write(f'  image size: w={w}, h={h}\n')
                logf.write(f'  元bboxリスト: {bbox_list}\n')
                logf.write(f'  YOLO変換後: {bboxes_yolo}\n')
                logf.write(f'  ---\n')
            continue
        # --- 以降は従来のaugment処理と同じ ---
        # bboxの範囲外チェック
        invalid_bboxes = [b for b in bboxes_yolo if not is_bbox_valid([b[1], b[2], b[3], b[4]])]
        if invalid_bboxes:
            print(f"[警告] {img_path.name} のbboxに0.0～1.0範囲外の値が含まれるため、オーグメント処理をスキップします。対象bbox: {invalid_bboxes}")
            continue
        for i in range(augment_num):
            if i == 0:
                aug_image = cv2.flip(image, 1)
                aug_bboxes = [horizontal_flip_bbox(b) for b in bboxes_yolo]
                aug_type = 'flip'
            else:
                aug = A.Compose([
                    A.HorizontalFlip(p=0.5),
                    A.RandomBrightnessContrast(p=0.5),
                    A.HueSaturationValue(p=0.5),
                    A.GaussNoise(p=0.3),
                ], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels']))
                yolo_bboxes = [[clip01(b[1]), clip01(b[2]), clip01(b[3]), clip01(b[4])] for b in bboxes_yolo]
                class_labels = [b[0] for b in bboxes_yolo]
                valid_bboxes = [bb for bb in yolo_bboxes if is_bbox_valid(bb)]
                valid_labels = [cl for bb, cl in zip(yolo_bboxes, class_labels) if is_bbox_valid(bb)]
                valid_bboxes = [[max(0.0, min(1.0, v)) for v in bb] for bb in valid_bboxes]
                if not valid_bboxes or all(not all(0.0 <= float(x) <= 1.0 for x in bb) for bb in valid_bboxes):
                    continue
                augmented = aug(image=image, bboxes=valid_bboxes, class_labels=valid_labels)
                aug_image = augmented['image']
                aug_bboxes = [[cl] + list(bb) for cl, bb in zip(augmented['class_labels'], augmented['bboxes'])]
                for b in aug_bboxes:
                    b[1:5] = np.clip(b[1:5], 0.0, 1.0)
                aug_bboxes = [b for b in aug_bboxes if all(0.0 <= float(x) <= 1.0 for x in b[1:5])]
                for b in aug_bboxes:
                    for j in range(1, 5):
                        b[j] = max(0.0, min(1.0, float(b[j])))
                aug_type = 'color_noise'
            aug_bboxes = [clip_bbox_with_imgsize(b, w, h) for b in aug_bboxes]
            aug_bboxes = [b for b in aug_bboxes if b is not None]
            if not aug_bboxes:
                continue
            aug_img_name = f'aug{i+1}_{img_path.name}'
            aug_img_path = img_path.parent / aug_img_name
            cv2.imwrite(str(aug_img_path), aug_image)
            # DBにも登録
            db_bboxes = []
            for b in aug_bboxes:
                db_bboxes.append({
                    "cid": int(b[0]),
                    "cname": "",
                    "conf": 1.0,
                    "xyxy": [],
                    "role": None
                })
            insert_image_cache_record(
                filename=aug_img_name,
                image_path=str(aug_img_path.resolve()),
                bboxes=db_bboxes
            )

def main(dataset_dir=None, augment_num=5):
    augment_dataset_from_db(augment_num=augment_num)

if __name__ == '__main__':
    main()