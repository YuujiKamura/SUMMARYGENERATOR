#!/usr/bin/env python3
"""
データ拡張（データオーグメンテーション）モジュール
トレーニングデータセットのサイズを仮想的に増やし、モデルの汎化性能を向上させるために使用します
"""
import shutil
# import glob  # 未使用
# import random  # 未使用
from pathlib import Path

import cv2
# import numpy as np  # 未使用
import albumentations as A
# from tqdm import tqdm  # 未使用
from PyQt6.QtCore import QThread, pyqtSignal
import yaml

def make_augmenter():
    """Albumentationsを使った拡張パイプライン定義"""
    return A.Compose([
        A.HorizontalFlip(p=0.5),
        A.Rotate(limit=15, p=0.5),
        A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.5),
        A.HueSaturationValue(hue_shift_limit=20, sat_shift_limit=30, val_shift_limit=20, p=0.5),
        A.Blur(blur_limit=3, p=0.2),
    ], bbox_params=A.BboxParams(format='yolo', label_fields=['category_ids'], check_each_transform=True))

def is_valid_yolo_bbox(x, y, w, h):
    # すべて0.0～1.0の範囲
    if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 and 0.0 < w <= 1.0 and 0.0 < h <= 1.0):
        return False
    # bbox全体が画像内に収まる
    if x - w/2 < 0.0 or x + w/2 > 1.0 or y - h/2 < 0.0 or y + h/2 > 1.0:
        return False
    return True

def augment_dataset(
    src_img_dir: str,
    src_label_dir: str,
    dst_dir: str,
    n_augment: int = 3,
    progress_callback=None
):
    """
    データセットに対して拡張処理を適用し、新しいデータセットを生成します
    
    Args:
        src_img_dir: 元画像フォルダ
        src_label_dir: YOLOラベル (.txt) フォルダ
        dst_dir: 増幅後の出力フォルダ（images と labels サブフォルダが作られます）
        n_augment: 画像あたり何バリエーション作るか
        progress_callback: 進捗状況を受け取るコールバック関数（オプション）
    
    Returns:
        dict: 処理結果の情報（元画像数、生成画像数など）
    """
    log_file = open('augment_warnings.log', 'w', encoding='utf-8')
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

    # 出力ディレクトリをクリーン or 作成
    if dst_images.exists():
        log(f"出力画像ディレクトリを削除: {dst_images}")
        shutil.rmtree(dst_images)
    if dst_labels.exists():
        log(f"出力ラベルディレクトリを削除: {dst_labels}")
        shutil.rmtree(dst_labels)
    dst_images.mkdir(parents=True, exist_ok=True)
    dst_labels.mkdir(parents=True, exist_ok=True)

    augmenter = make_augmenter()

    # 入力画像の列挙
    img_extensions = ["*.jpg", "*.jpeg", "*.png", "*.bmp"]
    img_files = []
    for ext in img_extensions:
        img_files.extend(list(src_img_dir.glob(ext)))
    total_files = len(img_files)
    log(f"元の画像ファイル: {total_files}件")
    log(f"各画像に対して{n_augment}種類の拡張処理を適用します")
    log(f"出力先: {dst_dir}")
    log("-" * 40)

    # 元ファイルをまずコピー
    log("元画像をコピー中...")
    for i, img_path in enumerate(img_files):
        label_path = src_label_dir / (img_path.stem + ".txt")
        shutil.copy(img_path, dst_images / img_path.name)
        if label_path.exists():
            shutil.copy(label_path, dst_labels / label_path.name)
        if i % 10 == 0:
            log(f"コピー進捗: {i+1}/{total_files}")

    # 拡張処理
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
        try:
            with open(label_path, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        cls_id = int(parts[0])
                        x_center, y_center, w, h = map(float, parts[1:5])
                        bboxes.append([x_center, y_center, w, h])
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
                    if not is_valid_yolo_bbox(x, y, w, h):
                        log(f"警告: bbox無効: {out_name} class_id={cid} box={box}")
                        continue
                    label_lines.append(f"{cid} {x:.6f} {y:.6f} {w:.6f} {h:.6f}")
                if label_lines:
                    with open(dst_labels / (img_path.stem + f"_aug{aug_idx}.txt"), "w", encoding="utf-8") as f:
                        f.write("\n".join(label_lines))
                    aug_count += 1
            except Exception as e:
                log(f"警告: 拡張処理エラー: {img_path.name} - {str(e)}")
        if i % 5 == 0:
            log(f"拡張進捗: {i+1}/{total_files}")

    # 元のdataset.yamlからクラス名を取得
    orig_yaml = None
    orig_names = None
    # src_label_dirの親ディレクトリを基準にdataset.yamlを探す
    src_base = Path(src_label_dir).parent.parent if (Path(src_label_dir).name == 'train') else Path(src_label_dir).parent
    for candidate in [src_base / 'dataset.yaml', src_base.parent / 'dataset.yaml']:
        if candidate.exists():
            orig_yaml = candidate
            break
    if orig_yaml:
        with open(orig_yaml, 'r', encoding='utf-8') as f:
            ydata = yaml.safe_load(f)
        orig_names = ydata.get('names')

    # dataset.yaml ファイルの作成
    yaml_content = f"""
# YOLOv8データセット設定
path: {dst_dir.absolute()}
train: images
val: images

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
        for label_file in dst_labels.glob("*.txt"):
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
    log("-" * 40)
    log("処理完了:")
    log(f"- 元画像数: {total_files}")
    log(f"- 拡張画像数: {aug_count}")
    log(f"- 合計画像数: {total_files + aug_count}")
    log(f"- 出力ディレクトリ: {dst_dir}")
    log(f"- データセット設定: {dst_dir / 'dataset.yaml'}")
    result = {
        "original_images": total_files,
        "augmented_images": aug_count,
        "total_images": total_files + aug_count,
        "output_dir": str(dst_dir),
        "yaml_file": str(dst_dir / "dataset.yaml")
    }
    log_file.close()
    return result


class DataAugmentThread(QThread):
    """バックグラウンドでデータ拡張を実行するためのスレッド"""
    output_received = pyqtSignal(str)
    process_finished = pyqtSignal(int, dict)  # 終了コード, 処理結果情報
    
    def __init__(self, src_img_dir, src_label_dir, dst_dir, n_augment=3):
        super().__init__()
        self.src_img_dir = src_img_dir
        self.src_label_dir = src_label_dir
        self.dst_dir = dst_dir
        self.n_augment = n_augment
    
    def progress_callback(self, message):
        """進捗メッセージをGUIに送信"""
        self.output_received.emit(message)
    
    def run(self):
        try:
            self.output_received.emit("データ拡張処理を開始します:")
            self.output_received.emit(f"- 元画像ディレクトリ: {self.src_img_dir}")
            self.output_received.emit(f"- 元ラベルディレクトリ: {self.src_label_dir}")
            self.output_received.emit(f"- 出力ディレクトリ: {self.dst_dir}")
            self.output_received.emit(f"- 拡張バリエーション数: {self.n_augment}")
            self.output_received.emit("")
            
            result = augment_dataset(
                src_img_dir=self.src_img_dir,
                src_label_dir=self.src_label_dir,
                dst_dir=self.dst_dir,
                n_augment=self.n_augment,
                progress_callback=self.progress_callback
            )
            
            self.output_received.emit("データ拡張処理が完了しました")
            self.process_finished.emit(0, result)
        except Exception as e:
            self.output_received.emit(f"[エラー] データ拡張中に例外が発生しました: {e}")
            self.process_finished.emit(1, {}) 