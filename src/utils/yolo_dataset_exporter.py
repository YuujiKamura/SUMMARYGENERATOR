import os
import json
import shutil
import random
from pathlib import Path
from typing import Optional, List
from summarygenerator.utils.path_manager import path_manager

class YoloDatasetExporter:
    def __init__(self, image_list_json_paths: List[str], output_dir: Optional[str] = None, val_ratio: float = 0.2):
        self.image_list_json_paths = image_list_json_paths
        self.val_ratio = val_ratio
        self.output_dir = Path(output_dir) if output_dir else Path(os.path.dirname(image_list_json_paths[0])) / "yolo_dataset"
        self.images = []
        self.annotations = {}
        self.classes = []
        self._load_image_lists()

    def _load_image_lists(self):
        images_set = set()
        annotations = {}
        role_mapping_path = path_manager.role_mapping
        with open(role_mapping_path, encoding="utf-8") as f:
            role_mapping = json.load(f)
        all_class_names = []
        for v in role_mapping.values():
            roles = v.get("roles", [])
            for r in roles:
                if r not in all_class_names:
                    all_class_names.append(r)
        self.classes = all_class_names
        class_name_to_id = {name: i for i, name in enumerate(self.classes)}
        for json_path in self.image_list_json_paths:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and 'image_path' in data and 'bboxes' in data:
                data = [data]
            if isinstance(data, dict):
                imgs = data.get("images") or list(data.get("annotations", {}).keys())
                if isinstance(imgs, list):
                    for item in imgs:
                        if isinstance(item, dict):
                            p = item.get('path') or item.get('image_path')
                            if p:
                                images_set.add(p)
                        else:
                            images_set.add(item)
                else:
                    images_set.add(imgs)
                annotations.update(data.get("annotations", {}))
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and 'image_path' in item and 'bboxes' in item:
                        p = item['image_path']
                        if p:
                            images_set.add(p)
                        anns = []
                        for bbox in item['bboxes']:
                            role = bbox.get('role')
                            label = bbox.get('label')
                            class_name = role if role else label
                            box = bbox.get('bbox')
                            if box is None and 'xyxy' in bbox:
                                box = bbox['xyxy']
                            if not class_name or not box or len(box) != 4:
                                continue
                            if class_name not in class_name_to_id:
                                continue
                            class_id = class_name_to_id[class_name]
                            anns.append({"class_id": class_id, "box": box, "role": role, "label": label})
                        if anns:
                            annotations[p] = anns
                    elif isinstance(item, dict):
                        p = item.get('path') or item.get('image_path')
                        if p:
                            images_set.add(p)
                    else:
                        images_set.add(item)
            else:
                raise ValueError(f"画像リストJSONの形式が不明: {json_path}")
        self.images = sorted(images_set)
        self.annotations = annotations

    def export(self, mode='all', existing_dataset_dir: Optional[str] = None, force_flush: bool = False):
        if force_flush and self.output_dir.exists():
            print(f"[YOLO_EXPORT] 出力先をクリーン: {self.output_dir}")
            shutil.rmtree(self.output_dir)
        existing_names = set()
        if mode == 'add' and existing_dataset_dir:
            for subdir in ["images/train", "images/val"]:
                img_dir = Path(existing_dataset_dir) / subdir
                if img_dir.exists():
                    for img_file in img_dir.glob("*.*"):
                        existing_names.add(img_file.name)
        train_img_dir = self.output_dir / "images" / "train"
        val_img_dir = self.output_dir / "images" / "val"
        train_lbl_dir = self.output_dir / "labels" / "train"
        val_lbl_dir = self.output_dir / "labels" / "val"
        for d in [train_img_dir, val_img_dir, train_lbl_dir, val_lbl_dir]:
            d.mkdir(parents=True, exist_ok=True)
        if self.classes:
            with open(self.output_dir / "classes.txt", "w", encoding="utf-8") as f:
                for c in self.classes:
                    f.write(f"{c}\n")
        img_list = list(self.images)
        if mode == 'add' and existing_names:
            img_list = [p for p in img_list if Path(p).name not in existing_names]
        random.shuffle(img_list)
        split_idx = int(len(img_list) * (1 - self.val_ratio))
        train_imgs = img_list[:split_idx]
        val_imgs = img_list[split_idx:]
        print(f"[YOLO_EXPORT] 入力画像数: {len(img_list)} (train: {len(train_imgs)}, val: {len(val_imgs)})")
        label_ok_train = sum(1 for p in train_imgs if self.annotations.get(str(Path(p)), []))
        label_ok_val = sum(1 for p in val_imgs if self.annotations.get(str(Path(p)), []))
        print(f"[YOLO_EXPORT] ラベル有り画像数: train={label_ok_train}, val={label_ok_val}")
        rejected = []
        out_img_count = 0
        success_list = []
        fail_list = []
        for img_path in train_imgs:
            reason = self._export_one_with_reason(img_path, train_img_dir, train_lbl_dir)
            if reason is None:
                out_img_count += 1
                success_list.append((img_path, "OK"))
            else:
                rejected.append((img_path, reason))
                fail_list.append((img_path, reason))
        for img_path in val_imgs:
            reason = self._export_one_with_reason(img_path, val_img_dir, val_lbl_dir)
            if reason is None:
                out_img_count += 1
                success_list.append((img_path, "OK"))
            else:
                rejected.append((img_path, reason))
                fail_list.append((img_path, reason))
        print(f"[YOLO_EXPORT] 実際に出力した画像数: {out_img_count}")
        print("[YOLO_EXPORT] ラベリング成功画像一覧:")
        for p, status in success_list:
            print(f"  {p}: {status}")
        print("[YOLO_EXPORT] ラベリング失敗（除外）画像一覧:")
        for p, reason in fail_list:
            print(f"  {p}: {reason}")
        if rejected:
            print(f"[YOLO_EXPORT] 除外された画像一覧（理由付き）:")
            for p, reason in rejected:
                print(f"  {p}: {reason}")
        orig_class_set = set()
        orig_bbox_count = 0
        orig_roles = set()
        orig_labels = set()
        orig_class_names = set()
        for anns in self.annotations.values():
            for ann in anns:
                class_id = ann.get("class_id", 0)
                role = ann.get("role")
                label = ann.get("label")
                orig_class_set.add(class_id)
                if role:
                    orig_roles.add(role)
                    orig_class_names.add(role)
                elif label:
                    orig_labels.add(label)
                    orig_class_names.add(label)
                orig_bbox_count += 1
        out_label_files = list((self.output_dir / "labels" / "train").glob("*.txt")) + list((self.output_dir / "labels" / "val").glob("*.txt"))
        out_class_set = set()
        out_bbox_count = 0
        out_class_names = set()
        out_label_file_contents = {}
        for lf in out_label_files:
            lines = []
            with open(lf, encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    if parts and len(parts) >= 5:
                        out_class_set.add(int(parts[0]))
                        out_bbox_count += 1
                        lines.append(line.strip())
            out_label_file_contents[os.path.basename(lf)] = lines
        out_class_names = set(self.classes[i] if i < len(self.classes) else str(i) for i in out_class_set)
        class_name_to_id_before = {}
        for anns in self.annotations.values():
            for ann in anns:
                role = ann.get("role")
                label = ann.get("label")
                class_name = role if role else label
                class_id = ann.get("class_id", 0)
                if class_name is not None:
                    class_name_to_id_before[class_name] = class_id
        class_id_to_name_after = {i: self.classes[i] if i < len(self.classes) else str(i) for i in out_class_set}
        yaml_path = self.output_dir / "dataset.yaml"
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(f"path: {self.output_dir.absolute()}\n")
            f.write("train: images/train\n")
            f.write("val: images/val\n")
            if self.classes:
                f.write(f"names: {self.classes}\n")
        return {"output_dir": self.output_dir, "rejected": rejected,
                "class_count_before": len(orig_class_set), "class_count_after": len(out_class_set),
                "bbox_count_before": orig_bbox_count, "bbox_count_after": out_bbox_count,
                "roles_before": sorted(orig_roles), "labels_before": sorted(orig_labels),
                "class_names_before": sorted(orig_class_names), "class_names_after": sorted(out_class_names),
                "label_file_contents": out_label_file_contents,
                "class_name_to_id_before": class_name_to_id_before,
                "class_id_to_name_after": class_id_to_name_after}

    def _export_one_with_reason(self, img_path, img_dir, lbl_dir):
        def _clip01(x):
            return max(0.0, min(1.0, x))
        img_path = Path(img_path)
        if not img_path or not str(img_path):
            return "画像パスがNoneまたは空"
        import os
        print(f"[YOLO_EXPORT][画像存在チェック] repr: {repr(str(img_path))}")
        print(f"[YOLO_EXPORT][画像存在チェック] os.path.exists: {os.path.exists(str(img_path))}")
        print(f"[YOLO_EXPORT][画像存在チェック] Path.exists: {img_path.exists()}")
        parent_dir = os.path.dirname(str(img_path))
        print(f"[YOLO_EXPORT][画像存在チェック] 親ディレクトリ: {parent_dir}")
        try:
            entries = os.listdir(parent_dir)
            # ... rest of the method ...
        except Exception as e:
            return str(e)
        return None 