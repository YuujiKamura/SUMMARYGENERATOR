import os
import shutil
import json
from pathlib import Path
from src.utils.models import Annotation, ClassDefinition, AnnotationDataset, BoundingBox

def convert_role_json_to_annotation_dataset(json_paths, copy_network_drive=True, skip_missing_files=True, use_temp_dir=True):
    # クラス名・IDの一意リスト作成
    class_name_to_id = {}
    class_defs = []
    annotations = {}
    path_mapping = {}
    total_images = 0
    total_annotations = 0
    failures = 0
    temp_files = []
    import tempfile
    temp_dir = os.path.join(tempfile.gettempdir(), "photocategorizer_temp")
    os.makedirs(temp_dir, exist_ok=True)
    def is_network_drive_path(path):
        return (
            path.startswith(("H:", "H:/", "H:\\")) or
            "マイドライブ" in path or
            "Googleドライブ" in path or
            "\\nas" in path or
            "\\server" in path
        )
    def copy_to_local(img_path):
        try:
            if not os.path.exists(img_path):
                print(f"画像が存在しません: {img_path}")
                return None
            import hashlib
            file_hash = hashlib.md5(img_path.encode()).hexdigest()[:8]
            basename = os.path.basename(img_path)
            temp_path = os.path.join(temp_dir, f"{file_hash}_{basename}")
            if os.path.exists(temp_path):
                return temp_path
            shutil.copy2(img_path, temp_path)
            temp_files.append(temp_path)
            print(f"ネットワークドライブからコピー: {img_path} -> {temp_path}")
            return temp_path
        except Exception as e:
            print(f"ファイルコピーエラー: {img_path} - {e}")
            return None
    def normalize_path(img_path):
        try:
            if img_path in path_mapping:
                return path_mapping[img_path]
            if copy_network_drive and is_network_drive_path(img_path):
                local_path = copy_to_local(img_path)
                if local_path:
                    path_mapping[img_path] = local_path
                    return local_path
                elif skip_missing_files:
                    path_mapping[img_path] = None
                    return None
            if use_temp_dir and not is_network_drive_path(img_path) and os.path.exists(img_path):
                local_path = copy_to_local(img_path)
                if local_path:
                    path_mapping[img_path] = local_path
                    return local_path
            if skip_missing_files and not os.path.exists(img_path):
                alt_path = img_path.replace('\\', '/')
                if not os.path.exists(alt_path):
                    path_mapping[img_path] = None
                    return None
                img_path = alt_path
            try:
                norm_path = img_path.replace('\\', '/')
                if not os.path.exists(norm_path) and os.path.exists(img_path):
                    norm_path = img_path
                p = Path(norm_path).resolve()
                abs_path = str(p)
                if os.path.exists(abs_path):
                    if use_temp_dir:
                        local_path = copy_to_local(abs_path)
                        if local_path:
                            path_mapping[img_path] = local_path
                            return local_path
                    path_mapping[img_path] = abs_path
                    return abs_path
                if os.path.exists(img_path):
                    if use_temp_dir:
                        local_path = copy_to_local(img_path)
                        if local_path:
                            path_mapping[img_path] = local_path
                            return local_path
                    path_mapping[img_path] = img_path
                    return img_path
                path_mapping[img_path] = norm_path
                return norm_path
            except Exception as e:
                print(f"パス正規化エラー: {img_path} - {e}")
                path_mapping[img_path] = img_path
                return img_path
        except Exception as e:
            print(f"パス処理例外: {img_path} - {e}")
            return img_path
    for json_path in json_paths:
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            label = data.get('label', Path(json_path).stem)
            if label not in class_name_to_id:
                cid = len(class_name_to_id)
                class_name_to_id[label] = cid
                class_defs.append(ClassDefinition(id=cid, name=label, color="#FF0000"))
            cid = class_name_to_id[label]
            for img in data.get('images', []):
                total_images += 1
                try:
                    if isinstance(img, str):
                        img_path = img
                        bboxes = []
                    else:
                        img_path = img['path']
                        bboxes = img.get('bboxes', [])
                    norm_img_path = normalize_path(img_path)
                    if norm_img_path is None:
                        print(f"無効なパスをスキップ: {img_path}")
                        failures += 1
                        continue
                    if not bboxes:
                        print(f"バウンディングボックスなし: {norm_img_path}")
                        failures += 1
                        continue
                    anns = []
                    for i, bbox in enumerate(bboxes):
                        try:
                            box = BoundingBox(
                                x1=float(bbox['bbox'][0]), y1=float(bbox['bbox'][1]),
                                x2=float(bbox['bbox'][2]), y2=float(bbox['bbox'][3])
                            )
                            anns.append(Annotation(id=i, class_id=cid, box=box))
                            total_annotations += 1
                        except (KeyError, IndexError, ValueError, TypeError) as e:
                            print(f"バウンディングボックス形式エラー: {e}")
                            failures += 1
                            continue
                    if not anns:
                        print(f"有効なアノテーションがなし: {norm_img_path}")
                        failures += 1
                        continue
                    if not os.path.exists(norm_img_path) and not os.path.exists(img_path):
                        if skip_missing_files:
                            print(f"画像ファイルが存在しない: {norm_img_path}")
                            failures += 1
                            continue
                    if norm_img_path not in annotations and img_path not in annotations:
                        annotations[norm_img_path] = anns
                    else:
                        existing_key = norm_img_path if norm_img_path in annotations else img_path
                        offset = len(annotations[existing_key])
                        for i, ann in enumerate(anns):
                            annotations[existing_key].append(
                                Annotation(id=offset+i, class_id=ann.class_id, box=ann.box)
                            )
                except Exception as e:
                    print(f"画像エントリ処理エラー: {img} - {e}")
                    failures += 1
                    continue
        except Exception as e:
            print(f"JSONファイル処理エラー: {json_path} - {e}")
            failures += 1
    print(f"変換統計: 総画像数={total_images}, 成功={len(annotations)}, 失敗={failures}, アノテーション={total_annotations}")
    return AnnotationDataset(classes=class_defs, annotations=annotations)
