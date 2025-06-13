import os
import json
import threading

def assign_selected_images(self):
    selected_paths = self.image_widget.get_selected_image_paths()
    if not selected_paths:
        return
    role_label = "default"
    for path in selected_paths:
        self.assignment[path] = role_label
    if self.test_mode:
        self.save_to_json(role_label, selected_paths)
    else:
        threading.Thread(target=self._save_and_update, args=(role_label, selected_paths), daemon=True).start()

def _save_and_update(self, role_label, img_paths):
    self.save_to_json(role_label, img_paths)

def save_to_json(self, role_label, img_paths):
    os.makedirs(self.save_dir, exist_ok=True)
    json_path = os.path.join(self.save_dir, f"{role_label}.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            images = {img['path']: img for img in data.get("images", [])}
        except Exception:
            images = {}
    else:
        images = {}
    bbox_dict = getattr(self.image_widget, 'bbox_dict', {})
    for path in img_paths:
        bboxes = []
        if bbox_dict and path in bbox_dict:
            for cid, cname, conf, xyxy in bbox_dict[path]:
                if xyxy:
                    bboxes.append({
                        "class_id": cid,
                        "bbox": list(map(float, xyxy)),
                        "confidence": float(conf)
                    })
        images[path] = {"path": path, "bboxes": bboxes}
    out = {"label": role_label, "images": list(images.values())}
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

def find_images_without_bboxes(self):
    result = {}
    for fname in os.listdir(self.save_dir):
        if not fname.endswith('.json'):
            continue
        path = os.path.join(self.save_dir, fname)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            label = data.get('label', fname.replace('.json', ''))
            images = data.get('images', [])
            no_bbox = []
            for entry in images:
                if isinstance(entry, str):
                    no_bbox.append(entry)
                elif isinstance(entry, dict):
                    bboxes = entry.get('bboxes', None)
                    if not bboxes:
                        no_bbox.append(entry.get('path'))
            if no_bbox:
                result[label] = no_bbox
        except Exception as e:
            print(f"Error reading {path}: {e}")
    return result
