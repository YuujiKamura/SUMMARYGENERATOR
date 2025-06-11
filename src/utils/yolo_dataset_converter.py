import os
import json
import shutil
import random
from pathlib import Path
from typing import List, Optional, Dict, Any
from PIL import Image
import yaml
import datetime
from path_manager import PathManager

def get_default_output_dir():
    now_str = datetime.datetime.now().strftime("%Y%m%d")
    return Path("datasets") / f"yolo_dataset_{now_str}"

class YoloDatasetConverter:
    def __init__(self, role_mapping_path: str, preset_roles_path: str):
        self.role_mapping_path = role_mapping_path
        self.preset_roles_path = preset_roles_path
        self.label_to_display = self._load_label_to_display()

    def _load_label_to_display(self):
        label_to_display = {}
        with open(self.preset_roles_path, encoding="utf-8") as f:
            preset_roles = json.load(f)
        for entry in preset_roles:
            label = entry.get("label")
            display = entry.get("display")
            if label and display:
                label_to_display[label] = display
        return label_to_display

    def load_class_names_filtered(self, used_class_names: set) -> List[str]:
        with open(self.role_mapping_path, encoding="utf-8") as f:
            role_mapping = json.load(f)
        class_names = set()
        for v in role_mapping.values():
            for r in v.get("roles", []):
                class_names.add(r)
        with open(self.preset_roles_path, encoding="utf-8") as f:
            preset_roles = json.load(f)
        for entry in preset_roles:
            class_names.add(entry.get("label"))
        # 画像で実際に使われているクラスのみ返す
        return sorted([c for c in class_names if c and c in used_class_names])

    @staticmethod
    def xyxy_abs_to_xywh_norm(x1, y1, x2, y2, img_w, img_h):
        bw = x2 - x1
        bh = y2 - y1
        cx = x1 + bw / 2
        cy = y1 + bh / 2
        x = cx / img_w
        y = cy / img_h
        w = bw / img_w
        h = bh / img_h
        return x, y, w, h

    def convert(self, in_json: str, out_dir: Path, val_ratio: float = 0.2, force_flush: bool = True, classify_mode: bool = False) -> Dict[str, Any]:
        if force_flush and out_dir.exists():
            shutil.rmtree(out_dir)
        (out_dir / "images/train").mkdir(parents=True, exist_ok=True)
        (out_dir / "images/val").mkdir(parents=True, exist_ok=True)
        (out_dir / "labels/train").mkdir(parents=True, exist_ok=True)
        (out_dir / "labels/val").mkdir(parents=True, exist_ok=True)
        with open(in_json, encoding="utf-8") as f:
            data = json.load(f)
        used_class_names = set()
        entries = []
        if isinstance(data, dict) and "images" in data:
            entries = [{"image_path": p, "bboxes": []} for p in data["images"]]
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    path = item.get("image_path") or item.get("path")
                    bboxes = item.get("bboxes")
                    entries.append({"image_path": path, "bboxes": bboxes if bboxes is not None else []})
                    for bbox in (bboxes or []):
                        class_name = bbox.get("role") or bbox.get("label") or bbox.get("cname")
                        if class_name:
                            used_class_names.add(class_name)
                else:
                    entries.append({"image_path": item, "bboxes": []})
        else:
            raise ValueError(f"画像リストJSONの形式が不正です: {in_json}")
        random.shuffle(entries)
        split_idx = int(len(entries) * (1 - val_ratio))
        train_entries = entries[:split_idx]
        val_entries = entries[split_idx:]
        class_names = self.load_class_names_filtered(used_class_names)
        class_name_to_id = {name: i for i, name in enumerate(class_names)}
        def process_entries(sub_entries, img_dir, lbl_dir):
            for entry in sub_entries:
                img_path = entry["image_path"]
                bboxes = entry.get("bboxes", [])
                if not img_path or not os.path.exists(img_path):
                    continue
                with Image.open(img_path) as im:
                    img_w, img_h = im.size
                label_path = Path(lbl_dir) / (Path(img_path).stem + ".txt")
                with open(label_path, "w", encoding="utf-8") as f:
                    for bbox in bboxes:
                        class_name = bbox.get("role") or bbox.get("label") or bbox.get("cname")
                        if not class_name or class_name not in class_name_to_id:
                            continue
                        class_id = class_name_to_id[class_name]
                        box = bbox.get("bbox") or bbox.get("xyxy")
                        if not box or len(box) != 4:
                            continue
                        x1, y1, x2, y2 = box
                        x, y, w, h = self.xyxy_abs_to_xywh_norm(x1, y1, x2, y2, img_w, img_h)
                        if w <= 0 or h <= 0 or not all(0 <= v <= 1 for v in [x, y, w, h]):
                            continue
                        f.write(f"{class_id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")
                # 分類タスク用ディレクトリ構造生成
                if classify_mode:
                    # bboxesが空でもclass_nameをentry/itemから取得
                    class_name = None
                    if bboxes and (bboxes[0].get("role") or bboxes[0].get("label") or bboxes[0].get("cname")):
                        class_name = bboxes[0].get("role") or bboxes[0].get("label") or bboxes[0].get("cname")
                    else:
                        class_name = entry.get("class_name") or entry.get("label") or entry.get("role")
                    if class_name and class_name in class_name_to_id:
                        class_dir = Path(img_dir) / class_name
                        class_dir.mkdir(exist_ok=True)
                        shutil.copy2(img_path, class_dir / Path(img_path).name)
                else:
                    shutil.copy2(img_path, Path(img_dir) / Path(img_path).name)
        process_entries(train_entries, out_dir / "images/train", out_dir / "labels/train")
        process_entries(val_entries, out_dir / "images/val", out_dir / "labels/val")
        with open(out_dir / "classes.txt", "w", encoding="utf-8") as f:
            for c in class_names:
                f.write(f"{c}\n")
        pm = PathManager()
        out_dir_abs = pm.normalize(out_dir)
        names_display = [self.label_to_display.get(c, c) for c in class_names]
        yaml_content = {
            "path": str(out_dir_abs),
            "train": "images/train",
            "val": "images/val",
            "names": names_display
        }
        with open(out_dir / "dataset.yaml", "w", encoding="utf-8") as f:
            yaml.dump(yaml_content, f, allow_unicode=True)
        return {
            "output_dir": str(out_dir),
            "class_names": class_names,
            "train_count": len(train_entries),
            "val_count": len(val_entries)
        }