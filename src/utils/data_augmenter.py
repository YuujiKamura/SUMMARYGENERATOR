# --- データ拡張メイン関数 ---
import os
import shutil
import random
from typing import Optional, Callable, Dict, Any
from pathlib import Path
from PIL import Image, ImageEnhance, ImageOps
import numpy as np
import cv2
import albumentations as A
import yaml
import datetime

def augment_image(image_path: str, out_dir: str, idx: int = 0) -> str:
    """
    画像をランダムに拡張して保存する（回転・明度・反転など）
    """
    img = Image.open(image_path)
    # ランダム回転
    angle = random.choice([0, 90, 180, 270])
    img = img.rotate(angle)
    # 明度調整
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(random.uniform(0.7, 1.3))
    # ランダム左右反転
    if random.random() > 0.5:
        img = ImageOps.mirror(img)
    # 保存
    out_name = f"{Path(image_path).stem}_aug{idx}{Path(image_path).suffix}"
    out_path = os.path.join(out_dir, out_name)
    img.save(out_path)
    return out_path

def augment_label(label_path: str, out_path: str, angle: int, img_w: int, img_h: int, flip: bool = False):
    """
    YOLOラベルを回転・反転に合わせて変換して保存
    """
    # ... existing code ...

def make_augmenter():
    return A.Compose([
        A.HorizontalFlip(p=0.5),
        A.Rotate(limit=15, p=0.5),
        A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.5),
        A.HueSaturationValue(hue_shift_limit=20, sat_shift_limit=30, val_shift_limit=20, p=0.5),
        A.Blur(blur_limit=3, p=0.2),
    ], bbox_params=A.BboxParams(format='yolo', label_fields=['category_ids'], check_each_transform=True, min_visibility=0.0))

def is_valid_yolo_bbox(x, y, w, h):
    if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 and 0.0 < w <= 1.0 and 0.0 < h <= 1.0):
        return False
    if x - w/2 < 0.0 or x + w/2 > 1.0 or y - h/2 < 0.0 or y + h/2 > 1.0:
        return False
    return True

def get_default_aug_output_dir():
    now_str = datetime.datetime.now().strftime("%Y%m%d")
    return Path("datasets") / f"yolo_dataset_aug_{now_str}"

def split_train_val(files, val_ratio=0.2, seed=42):
    random.seed(seed)
    files = list(files)
    random.shuffle(files)
    n_val = int(len(files) * val_ratio)
    val_files = set(files[:n_val])
    train_files = set(files[n_val:])
    return train_files, val_files

def augment_dataset(
    src_img_dir: str,
    src_label_dir: str,
    dst_dir: str,
    n_augment: int = 3,
    progress_callback=None
):
    log_file = open('augment_warnings.log', 'a', encoding='utf-8')
    def log(msg):
        print(f"[AUGMENT] {msg}")
        if progress_callback:
            progress_callback(msg)
        log_file.write(f"[AUGMENT] {msg}\n")
    src_img_dir = Path(src_img_dir)
    src_label_dir = Path(src_label_dir)
    dst_dir = Path(dst_dir)
    dst_images = dst_dir / "images"
    dst_labels = dst_dir / "labels"
    if dst_images.exists():
        log(f"出力画像ディレクトリを削除: {dst_images}")
        shutil.rmtree(dst_images)
    if dst_labels.exists():
        log(f"出力ラベルディレクトリを削除: {dst_labels}")
        shutil.rmtree(dst_labels)
    dst_images.mkdir(parents=True, exist_ok=True)
    dst_labels.mkdir(parents=True, exist_ok=True)
    augmenter = make_augmenter()
    img_extensions = ["*.jpg", "*.jpeg", "*.png", "*.bmp"]
    img_files = []
    for ext in img_extensions:
        img_files.extend(list(src_img_dir.glob(ext)))
    total_files = len(img_files)
    log(f"元の画像ファイル: {total_files}件")
    log(f"各画像に対して{n_augment}種類の拡張処理を適用します")
    log(f"出力先: {dst_dir}")
    log("-" * 40)
    log("元画像をコピー中...")
    for i, img_path in enumerate(img_files):
        label_path = src_label_dir / (img_path.stem + ".txt")
        shutil.copy(img_path, dst_images / img_path.name)
        if label_path.exists():
            shutil.copy(label_path, dst_labels / label_path.name)
        if i % 10 == 0:
            log(f"コピー進捗: {i+1}/{total_files}")
    aug_count = 0
    log("画像拡張処理中...")
    for i, img_path in enumerate(img_files):
        label_path = src_label_dir / (img_path.stem + ".txt")
        if not label_path.exists():
            continue
        image = cv2.imread(str(img_path))
        if image is None:
            log(f"警告: 画像が読み込めません: {img_path}")
            continue
        bboxes = []
        class_ids = []
        label_lines_raw = []
        try:
            with open(label_path, "r", encoding="utf-8") as f:
                for line in f:
                    label_lines_raw.append(line.rstrip())
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        cls_id = int(parts[0])
                        x_center, y_center, w, h = map(float, parts[1:5])
                        # --- クリップ前処理 ---
                        x1 = max(0.0, x_center - w/2)
                        y1 = max(0.0, y_center - h/2)
                        x2 = min(1.0, x_center + w/2)
                        y2 = min(1.0, y_center + h/2)
                        new_w = x2 - x1
                        new_h = y2 - y1
                        if new_w <= 0 or new_h <= 0:
                            continue  # 完全に画像外
                        new_x = (x1 + x2) / 2
                        new_y = (y1 + y2) / 2
                        bboxes.append([new_x, new_y, new_w, new_h])
                        class_ids.append(cls_id)
        except Exception as e:
            log(f"警告: ラベルファイル読み込みエラー: {label_path} - {str(e)}")
            continue
        for aug_idx in range(n_augment):
            try:
                aug = augmenter(image=image, bboxes=bboxes, category_ids=class_ids)
                aug_img = aug["image"]
                aug_boxes = aug["bboxes"]
                aug_classes = aug["category_ids"]
                if len(aug_boxes) == 0:
                    continue
                out_name = f"{img_path.stem}_aug{aug_idx}.jpg"
                cv2.imwrite(str(dst_images / out_name), aug_img)
                label_lines = []
                for cid, box in zip(aug_classes, aug_boxes):
                    # 0.0～1.0にクリップ
                    box = [max(0.0, min(1.0, v)) for v in box]
                    x, y, w, h = box
                    # bboxの端が完全に画像外なら除外
                    if x + w/2 <= 0.0 or x - w/2 >= 1.0 or y + h/2 <= 0.0 or y - h/2 >= 1.0:
                        log(f"警告: bbox完全に画像外: {out_name} class_id={cid} box={box}")
                        continue
                    # クリップ後のbboxが有効範囲か再チェック
                    if not is_valid_yolo_bbox(x, y, w, h):
                        log(f"警告: bboxクリップ後も無効: {out_name} class_id={cid} box={box}")
                        continue
                    label_lines.append(f"{cid} {x:.6f} {y:.6f} {w:.6f} {h:.6f}")
                if label_lines:
                    with open(dst_labels / (img_path.stem + f"_aug{aug_idx}.txt"), "w", encoding="utf-8") as f:
                        f.write("\n".join(label_lines))
                    aug_count += 1
            except Exception as e:
                log(f"警告: 拡張処理エラー: {img_path.name} - {str(e)}\n  元ラベル: {label_path}")
        if i % 5 == 0:
            log(f"拡張進捗: {i+1}/{total_files}")
    # train/val分割
    val_ratio = 0.2  # デフォルト値。元データセットのval比率を取得する場合はyamlから取得可
    orig_yaml = None
    orig_names = None
    src_base = Path(src_label_dir).parent.parent if (Path(src_label_dir).name == 'train') else Path(src_label_dir).parent
    for candidate in [src_base / 'dataset.yaml', src_base.parent / 'dataset.yaml']:
        if candidate.exists():
            orig_yaml = candidate
            break
    if orig_yaml:
        with open(orig_yaml, 'r', encoding='utf-8') as f:
            ydata = yaml.safe_load(f)
        orig_names = ydata.get('names')
        if 'val' in ydata and 'train' in ydata:
            # val/train比率を推定
            train_count = len(list((src_base / ydata['train']).glob('*.jpg')))
            val_count = len(list((src_base / ydata['val']).glob('*.jpg')))
            if train_count + val_count > 0:
                val_ratio = val_count / (train_count + val_count)
    # 画像ファイルをtrain/valに分割
    train_imgs, val_imgs = split_train_val([f for f in dst_images.glob('*.jpg')], val_ratio=val_ratio)
    # train/valサブディレクトリ作成
    for sub in ['train', 'val']:
        (dst_images / sub).mkdir(exist_ok=True)
        (dst_labels / sub).mkdir(exist_ok=True)
    # 画像・ラベルを移動
    for img_path in dst_images.glob('*.jpg'):
        stem = img_path.stem
        label_path = dst_labels / f"{stem}.txt"
        if img_path in train_imgs:
            shutil.move(str(img_path), str(dst_images / 'train' / img_path.name))
            if label_path.exists():
                shutil.move(str(label_path), str(dst_labels / 'train' / label_path.name))
        else:
            shutil.move(str(img_path), str(dst_images / 'val' / img_path.name))
            if label_path.exists():
                shutil.move(str(label_path), str(dst_labels / 'val' / label_path.name))
    # dataset.yaml ファイルの作成
    yaml_content = f"""
# YOLOv8データセット設定
path: .
train: images/train
val: images/val

# クラス情報
names:
"""
    if orig_names:
        if isinstance(orig_names, dict):
            for k, v in orig_names.items():
                yaml_content += f"  {k}: {v}\n"
        elif isinstance(orig_names, list):
            for i, v in enumerate(orig_names):
                yaml_content += f"  {i}: {v}\n"
    else:
        class_ids = set()
        for label_file in (dst_labels / 'train').glob("*.txt"):
            try:
                with open(label_file, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split()
                        if parts:
                            class_ids.add(int(parts[0]))
            except Exception:
                pass
        for class_id in sorted(class_ids):
            yaml_content += f"  {class_id}: class_{class_id}\n"
    with open(dst_dir / "dataset.yaml", "w", encoding="utf-8") as f:
        f.write(yaml_content)
    log_file.close()
    return {
        "original_images": total_files,
        "augmented_images": aug_count,
        "total_images": total_files + aug_count,
        "yaml_file": str(dst_dir / "dataset.yaml")
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="YOLOデータセット用データ拡張ツール")
    parser.add_argument("--src_img_dir", required=True, help="元画像ディレクトリ")
    parser.add_argument("--src_label_dir", required=True, help="元ラベルディレクトリ")
    parser.add_argument("--dst_dir", default=None, help="出力先ディレクトリ（省略時はdatasets/日付/）")
    parser.add_argument("--n_augment", type=int, default=3, help="画像ごとの拡張バリエーション数")
    args = parser.parse_args()
    dst_dir = Path(args.dst_dir) if args.dst_dir else get_default_aug_output_dir()
    result = augment_dataset(
        src_img_dir=args.src_img_dir,
        src_label_dir=args.src_label_dir,
        dst_dir=dst_dir,
        n_augment=args.n_augment
    )
    print("拡張完了:", result) 