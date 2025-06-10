# YOLOデータセット変換・生成用エクスポータ（src/yolo_dataset_exporter.pyのコピー）
# 必ずこのクラスを使ってデータセット変換・生成を行うこと

import os
import json
import shutil
import random
from pathlib import Path
from typing import Optional, List
from src.utils.path_manager import PathManager
from src.utils.bbox_convert import xyxy_abs_to_xywh_norm

class YoloDatasetExporter:
    def __init__(self, image_list_json_paths: List[str], output_dir: Optional[str] = None, val_ratio: float = 0.2):
        self.image_list_json_paths = image_list_json_paths
        self.val_ratio = val_ratio
        self.pm = PathManager()
        self.output_dir = Path(output_dir) if output_dir else self.pm.project_root / "datasets" / "yolo_dataset_exported"
        self.images = []
        self.annotations = {}
        self.classes = []
        self._load_image_lists()

    def _load_image_lists(self):
        images_set = set()
        annotations = {}
        class_names = set()
        for json_path in self.image_list_json_paths:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                img_path = item.get("image_path")
                bboxes = item.get("bboxes", [])
                if img_path:
                    images_set.add(img_path)
                    anns = []
                    for bbox in bboxes:
                        class_name = bbox.get("role")
                        box = bbox.get("bbox") or bbox.get("xyxy")
                        if not class_name or not box or len(box) != 4:
                            continue
                        class_names.add(class_name)
                        anns.append({"class_name": class_name, "box": box})
                    if anns:
                        annotations[img_path] = anns
        self.images = sorted(images_set)
        self.classes = sorted(class_names)
        self.class_name_to_id = {name: i for i, name in enumerate(self.classes)}
        self.annotations = annotations

    def export(self, force_flush: bool = False):
        if force_flush and self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        train_img_dir = self.output_dir / "images" / "train"
        val_img_dir = self.output_dir / "images" / "val"
        train_lbl_dir = self.output_dir / "labels" / "train"
        val_lbl_dir = self.output_dir / "labels" / "val"
        for d in [train_img_dir, val_img_dir, train_lbl_dir, val_lbl_dir]:
            d.mkdir(parents=True, exist_ok=True)
        with open(self.output_dir / "classes.txt", "w", encoding="utf-8") as f:
            for c in self.classes:
                f.write(f"{c}\n")
        img_list = list(self.images)
        random.shuffle(img_list)
        split_idx = int(len(img_list) * (1 - self.val_ratio))
        train_imgs = img_list[:split_idx]
        val_imgs = img_list[split_idx:]
        for img_path in train_imgs:
            self._export_one(img_path, train_img_dir, train_lbl_dir)
        for img_path in val_imgs:
            self._export_one(img_path, val_img_dir, val_lbl_dir)
        yaml_path = self.output_dir / "dataset.yaml"
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(f"path: {self.output_dir.absolute()}\n")
            f.write("train: images/train\n")
            f.write("val: images/val\n")
            f.write(f"names: {self.classes}\n")
        return {"output_dir": str(self.output_dir)}

    def _export_one(self, img_path, img_dir, lbl_dir):
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
            print(f"[YOLO_EXPORT][除外] ファイルが存在しません: {img_path}")
            return
        anns = self.annotations.get(str(img_path), [])
        if not anns:
            print(f"[YOLO_EXPORT][除外] ラベルが無い: {img_path}")
            return
        shutil.copy2(img_path, img_dir / img_path.name)
        label_path = lbl_dir / (img_path.stem + ".txt")
        with open(label_path, "w", encoding="utf-8") as f:
            for ann in anns:
                class_id = self.class_name_to_id.get(ann["class_name"], -1)
                box = ann["box"]
                try:
                    from PIL import Image
                    with Image.open(img_path) as im:
                        img_w, img_h = im.size
                except Exception:
                    continue
                x1, y1, x2, y2 = box
                x, y, w, h = xyxy_abs_to_xywh_norm(x1, y1, x2, y2, img_w, img_h)
                if w <= 0 or h <= 0:
                    continue
                if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 and 0.0 < w <= 1.0 and 0.0 < h <= 1.0):
                    continue
                f.write(f"{class_id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")

# 必要に応じて、src/yolo_dataset_exporter.pyの全実装をここにコピーしてください。
# 以降は summarygenerator/ 配下のこのYoloDatasetExporterを使って統一してください。
