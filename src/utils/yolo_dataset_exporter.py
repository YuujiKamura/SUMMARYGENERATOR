import os
# flake8: noqa
import json
import shutil
import random
import cv2
import hashlib
import logging
import sqlite3
from pathlib import Path
from typing import Optional, List
from src.utils.path_manager import path_manager
from src.data.db_to_yolo_dataset import safe_imread_with_temp

logger = logging.getLogger(__name__)

def get_db_path():
    """DBファイルの絶対パスをpath_manager経由で取得"""
    return Path(path_manager.yolo_db)

class YoloDatasetExporter:
    """
    YOLOデータセットエクスポート用クラス。
    画像・アノテーション情報は全てDB（yolo_data.db）から取得する。
    JSONファイル等には依存しない。
    """
    def __init__(self, output_dir: Optional[str] = None, val_ratio: float = 0.2, seed: Optional[int] = None, db_path: Optional[str] = None, debug: bool = False):
        self.val_ratio = val_ratio
        self.output_dir = Path(output_dir) if output_dir else Path("yolo_dataset")
        self.images = []  # 正規化ファイル名で保持
        self.annotations = {}  # {正規化ファイル名: {"abs_path": 絶対パス, "anns": アノテーションリスト}}
        self.classes = []
        self._rng = random.Random(seed)
        self._db_path = Path(db_path) if db_path else get_db_path()
        self.debug = debug
        self._load_image_lists()

        if self.debug:
            debug_init_log = path_manager.project_root / "logs" / "03_exporter_init_debug.log"
            with open(debug_init_log, 'w', encoding='utf-8') as f:
                f.write(f"images: {self.images}\n")
                for k, v in self.annotations.items():
                    f.write(f"{k}: {len(v.get('anns', []))}\n")
            logger.debug(f"__init__でself.images, self.annotations内容を {debug_init_log} にダンプ")
        # DBファイルの絶対パスを必ずログ出力
        logger.info(f"[YOLO_EXPORT] 使用DBファイル: {self._db_path.resolve()}")

    def _normalize_path(self, p):
        # ファイル名全体を小文字化＋md5(abs_path)[:6]で衝突回避
        p = str(p)
        base = os.path.basename(p).lower()
        h = hashlib.md5(p.encode('utf-8')).hexdigest()[:6]
        return f"{h}_{base}"

    def _xyxy_to_xywh_norm(self, xyxy, img_w, img_h):
        x_min, y_min, x_max, y_max = map(float, xyxy)
        x = ((x_min + x_max) / 2) / img_w
        y = ((y_min + y_max) / 2) / img_h
        w = (x_max - x_min) / img_w
        h = (y_max - y_min) / img_h
        return [x, y, w, h]

    def _load_image_lists(self):
        # DBから画像・アノテーション・クラス情報を取得
        db_path = self._db_path
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        # 1) preset_roles.json からロール名を読み込んでクラス順序を固定
        from pathlib import Path as _P
        import json as _json
        preset_path = _P(__file__).parent.parent / 'data' / 'preset_roles.json'
        class_names: list[str] = []
        if preset_path.exists():
            try:
                with open(preset_path, encoding='utf-8') as _f:
                    _preset = _json.load(_f)
                # display や category は無視し、label を使用
                class_names = [p['label'] for p in _preset if p.get('label')]
            except Exception:
                class_names = []
        class_name_to_id: dict[str, int] = {n: i for i, n in enumerate(class_names)}

        # 画像・アノテーション取得（bboxesとimagesをJOINしてimage_pathを取得）
        cur.execute("""
            SELECT images.image_path, bboxes.cname, bboxes.x1, bboxes.y1, bboxes.x2, bboxes.y2, bboxes.role, NULL
            FROM bboxes
            JOIN images ON bboxes.image_id = images.id
        """)
        images_set = set()
        annotations = {}
        for row in cur.fetchall():
            image_path, class_name_cname, x_min, y_min, x_max, y_max, role, label = row
            
            determined_class_name = None
            # role > cname の優先順でクラス名を決定
            current_role = str(role).strip() if role else ""
            current_cname = str(class_name_cname).strip() if class_name_cname else ""

            if current_role and current_role in class_name_to_id:
                determined_class_name = current_role
            elif current_cname and current_cname in class_name_to_id:
                determined_class_name = current_cname
            
            if determined_class_name is None:
                logger.warning(
                    f"画像 {image_path} のアノテーションで、preset_roles.json に一致するクラスが見つかりませんでした。"
                    f"role='{current_role}', cname='{current_cname}'。このアノテーションはスキップされます。"
                )
                continue # このアノテーションを処理しない
            
            class_id = class_name_to_id[determined_class_name]

            norm_p = self._normalize_path(image_path)
            images_set.add(norm_p)
            abs_p = str(Path(image_path).absolute())
            if norm_p not in annotations:
                annotations[norm_p] = {"abs_path": abs_p, "anns": []}
            
            img_w, img_h = 1280, 960 # デフォルト値
            if os.path.exists(image_path):
                try:
                    img = safe_imread_with_temp(image_path)
                    if img is not None:
                        img_h, img_w = img.shape[:2]
                except Exception:
                    pass # 画像読み込み失敗時はデフォルトサイズを使用
            
            xyxy = [x_min, y_min, x_max, y_max]
            box = self._xyxy_to_xywh_norm(xyxy, img_w, img_h)
            
            annotations[norm_p]["anns"].append({
                "class_id": class_id,
                "box": box,
                "role": determined_class_name, # 元のrole/cnameではなく、決定されたクラス名
                "label": label # labelは現状使われていないようだが保持
            })
        
        self.classes = class_names # preset_roles.json から読み込んだものをそのまま使用
        self.images = sorted(images_set)
        self.annotations = annotations
        conn.close()
        logger.debug("[DEBUG] _load_image_lists後のannotations内容:")
        for k, v in self.annotations.items():
            logger.debug(f"  {k}: anns={len(v.get('anns', []))} abs_path={v.get('abs_path')}")

    def export(self, mode='all', existing_dataset_dir: Optional[str] = None, force_flush: bool = False) -> str: # 戻り値を str (YAMLファイルのパス) に変更
        if force_flush and self.output_dir.exists():
            logger.info(f"[YOLO_EXPORT] 出力先をクリーン: {self.output_dir}")
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
        
        dataset_yaml_content = {
            'path': str(self.output_dir.resolve()), # データセットのルートディレクトリ
            'train': str((self.output_dir / 'images' / 'train').resolve()),
            'val': str((self.output_dir / 'images' / 'val').resolve()),
            'nc': len(self.classes),
            'names': self.classes
        }
        yaml_path = self.output_dir / "data.yaml"
        with open(yaml_path, "w", encoding="utf-8") as f:
            import yaml # PyYAMLが必要
            yaml.dump(dataset_yaml_content, f, default_flow_style=False, sort_keys=False)
        logger.info(f"[YOLO_EXPORT] data.yaml を生成: {yaml_path}")

        if self.classes:
            with open(self.output_dir / "classes.txt", "w", encoding="utf-8") as f:
                for c in self.classes:
                    f.write(f"{c}\n")
        
        img_list = list(self.images)
        if mode == 'add' and existing_names:
            img_list = [p for p in img_list if Path(self.annotations[p]["abs_path"]).name not in existing_names]
        self._rng.shuffle(img_list)
        
        labeled_imgs = [p for p in self.images if self.annotations.get(p, {}).get('anns', [])]
        logger.debug(f"labeled_imgs: {[(p, len(self.annotations.get(p, {}).get('anns', []))) for p in labeled_imgs]}")
        unlabeled_imgs = [p for p in self.images if not self.annotations.get(p, {}).get('anns', [])]
        self._rng.shuffle(labeled_imgs)
        self._rng.shuffle(unlabeled_imgs)
        n_labeled = len(labeled_imgs)
        n_unlabeled = len(unlabeled_imgs)
        n_val_labeled = int(n_labeled * self.val_ratio)
        if n_val_labeled == 0 and n_labeled > 0:
            n_val_labeled = 1
        n_train_labeled = n_labeled - n_val_labeled
        train_imgs = labeled_imgs[:n_train_labeled]
        val_imgs = labeled_imgs[n_train_labeled:]
        n_val_unlabeled = int(n_unlabeled * self.val_ratio)
        n_train_unlabeled = n_unlabeled - n_val_unlabeled
        train_imgs += unlabeled_imgs[:n_train_unlabeled]
        val_imgs += unlabeled_imgs[n_train_unlabeled:]
        if n_labeled > 0 and not any(self.annotations.get(p, {}).get('anns', []) for p in val_imgs):
            if train_imgs: # train_imgsが空でないことを確認
                for i, p in enumerate(train_imgs):
                    if self.annotations.get(p, {}).get('anns', []):
                        val_imgs.append(p)
                        del train_imgs[i]
                        break
            elif labeled_imgs: # train_imgsが空でも、元のlabeled_imgsに要素があればそこから移動
                # このケースは通常発生しづらいが、念のため
                moved = False
                for i, p_orig in enumerate(labeled_imgs):
                    if p_orig not in val_imgs: # まだvalに入っていないラベル付き画像を探す
                        val_imgs.append(p_orig)
                        moved = True
                        # train_imgs から削除する処理は不要（既に空か、またはこの画像を含まないため）
                        break
                if not moved and val_imgs: # それでも移動できず、val_imgsに何かあれば、それをそのまま使う
                    pass # val_imgs は既にラベル付き画像を含む可能性がある

        # ... (既存の画像コピー処理など) ...
        # 画像とラベルファイルの書き出し
        for split, img_paths in [("train", train_imgs), ("val", val_imgs)]:
            img_dir_split = self.output_dir / "images" / split
            lbl_dir_split = self.output_dir / "labels" / split
            for norm_p in img_paths:
                if norm_p not in self.annotations:
                    logger.warning(f"アノテーション情報が見つからないためスキップ: {norm_p}")
                    continue
                
                abs_img_path = self.annotations[norm_p]["abs_path"]
                if not Path(abs_img_path).exists():
                    logger.warning(f"元画像ファイルが見つからないためスキップ: {abs_img_path} (norm: {norm_p})")
                    continue

                # 画像ファイル名に拡張子を保持しつつ、正規化名を使う
                original_suffix = Path(abs_img_path).suffix
                # norm_p には既に拡張子が含まれている想定だが、念のため
                base_norm_p, _ = os.path.splitext(norm_p)
                dst_img_name = f"{base_norm_p}{original_suffix}"
                dst_img_path = img_dir_split / dst_img_name
                dst_lbl_path = lbl_dir_split / f"{base_norm_p}.txt"

                try:
                    shutil.copy2(abs_img_path, dst_img_path)
                except Exception as e:
                    logger.error(f"画像コピー失敗: {abs_img_path} -> {dst_img_path}, エラー: {e}")
                    continue

                with open(dst_lbl_path, "w", encoding="utf-8") as f_label:
                    if self.annotations[norm_p].get("anns"):
                        for ann in self.annotations[norm_p]["anns"]:
                            class_id = ann["class_id"]
                            box = ann["box"]
                            f_label.write(f"{class_id} {' '.join(map(str, box))}\n")
        
        logger.info(f"[YOLO_EXPORT] データセットのエクスポート完了: {self.output_dir}")
        return str(yaml_path.resolve()) # 生成したYAMLファイルの絶対パスを返す

    def _export_one_with_reason(self, norm_name, img_dir, lbl_dir):
        def _clip01(x):
            return max(0.0, min(1.0, x))
        if not norm_name or not str(norm_name):
            return "画像パスがNoneまたは空"
        log_path = path_manager.project_root / "logs" / "02_yolo_label_export.log"
        try:
            ann = self.annotations.get(norm_name)
            if not ann:
                return f"annotationsが存在しません: {norm_name}"
            img_path = Path(ann["abs_path"])
            if not img_path.exists():
                return f"画像が存在しません: {img_path}"
            dst_name = img_path.name
            stem, ext = os.path.splitext(dst_name)
            dst_name = stem + ext.lower()
            dst_img_path = img_dir / dst_name
            shutil.copy2(str(img_path), str(dst_img_path))
            anns = ann.get('anns', [])
            # --- annsの中身をデバッグログにダンプ ---
            if self.debug:
                anns_debug_log = path_manager.project_root / "logs" / "03_label_export_anns_debug.log"
                with open(anns_debug_log, 'a', encoding='utf-8') as f_debug:
                    f_debug.write(f"[anns debug] {img_path.name}: anns={repr(anns)}\n")
            label_path = lbl_dir / (stem + '.txt')
            label_lines = []
            if anns:
                with open(label_path, 'w', encoding='utf-8') as f:
                    for ann_item in anns:
                        class_id = ann_item.get('class_id', 0)
                        box = ann_item.get('box')
                        if not box or len(box) != 4:
                            continue
                        x, y, w, h = [_clip01(float(v)) for v in box]
                        line = f"{class_id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}"
                        f.write(line + "\n")
                        label_lines.append(line)
            else:
                open(label_path, 'w').close()
            if self.debug:
                with open(log_path, 'a', encoding='utf-8') as logf:
                    logf.write(f"[02_LABEL_EXPORT] {img_path.name}\n")
                    if label_lines:
                        for line in label_lines:
                            logf.write(f"[02_LABEL_EXPORT]   {line}\n")
                    else:
                        logf.write("[02_LABEL_EXPORT]   (empty)\n")
        except Exception as e:
            logger.exception(f"export failed: {norm_name}")
            return str(e)
        return None