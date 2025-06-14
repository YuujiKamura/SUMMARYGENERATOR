import os
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

        def _ensure_class(name: str) -> int:
            if name not in class_name_to_id:
                class_name_to_id[name] = len(class_names)
                class_names.append(name)
            return class_name_to_id[name]

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
            # role > cname の優先順でクラス名を決定
            if role and str(role).strip():
                class_name = role.strip()
            elif class_name_cname and str(class_name_cname).strip():
                class_name = str(class_name_cname).strip()
            else:
                class_name = "unknown"
            norm_p = self._normalize_path(image_path)
            images_set.add(norm_p)
            abs_p = str(Path(image_path).absolute())
            if norm_p not in annotations:
                annotations[norm_p] = {"abs_path": abs_p, "anns": []}
            # bboxをYOLO形式に変換
            img_w, img_h = 1280, 960
            if os.path.exists(image_path):
                try:
                    img = safe_imread_with_temp(image_path)
                    if img is not None:
                        img_h, img_w = img.shape[:2]
                except Exception:
                    pass
            xyxy = [x_min, y_min, x_max, y_max]
            box = self._xyxy_to_xywh_norm(xyxy, img_w, img_h)
            # 登録 & class_id 取得
            class_id = _ensure_class(class_name)
            annotations[norm_p]["anns"].append({
                "class_id": class_id,
                "box": box,
                "role": role,
                "label": label
            })
        # 最終クラスリストを保存（"unknown" が未登録なら追加）
        _ensure_class("unknown")

        self.classes = class_names
        self.images = sorted(images_set)
        self.annotations = annotations
        conn.close()
        logger.debug("[DEBUG] _load_image_lists後のannotations内容:")
        for k, v in self.annotations.items():
            logger.debug(f"  {k}: anns={len(v.get('anns', []))} abs_path={v.get('abs_path')}")

    def export(self, mode='all', existing_dataset_dir: Optional[str] = None, force_flush: bool = False):
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
        if self.classes:
            with open(self.output_dir / "classes.txt", "w", encoding="utf-8") as f:
                for c in self.classes:
                    f.write(f"{c}\n")
        img_list = list(self.images)
        if mode == 'add' and existing_names:
            img_list = [p for p in img_list if Path(self.annotations[p]["abs_path"]).name not in existing_names]
        self._rng.shuffle(img_list)
        # --- train/val分割ロジック修正 ---
        labeled_imgs = [p for p in self.images if self.annotations.get(p, {}).get('anns', [])]
        logger.debug(f"labeled_imgs: {[(p, len(self.annotations.get(p, {}).get('anns', []))) for p in labeled_imgs]}")
        unlabeled_imgs = [p for p in self.images if not self.annotations.get(p, {}).get('anns', [])]
        self._rng.shuffle(labeled_imgs)
        self._rng.shuffle(unlabeled_imgs)
        n_labeled = len(labeled_imgs)
        n_unlabeled = len(unlabeled_imgs)
        n_total = n_labeled + n_unlabeled
        n_val_labeled = int(n_labeled * self.val_ratio)
        # valに必ず1枚以上ラベル付き画像が入るようにする
        if n_val_labeled == 0 and n_labeled > 0:
            n_val_labeled = 1
        n_train_labeled = n_labeled - n_val_labeled
        train_imgs = labeled_imgs[:n_train_labeled]
        val_imgs = labeled_imgs[n_train_labeled:]
        # 残りのunlabeled画像をtrain/valに均等に割り当て
        n_val_unlabeled = int(n_unlabeled * self.val_ratio)
        n_train_unlabeled = n_unlabeled - n_val_unlabeled
        train_imgs += unlabeled_imgs[:n_train_unlabeled]
        val_imgs += unlabeled_imgs[n_train_unlabeled:]
        # valにラベル付き画像が1枚も無い場合は、trainから1枚移動
        if n_labeled > 0 and not any(self.annotations.get(p, {}).get('anns', []) for p in val_imgs):
            for i, p in enumerate(train_imgs):
                if self.annotations.get(p, {}).get('anns', []):
                    val_imgs.append(p)
                    del train_imgs[i]
                    break
        # --- ここで分割後のラベル付き画像数をprint ---
        # train_imgs/val_imgsのanns内容をデバッグログにダンプ
        if self.debug:
            anns_debug_log = path_manager.project_root / "logs" / "03_label_export_anns_debug.log"
            with open(anns_debug_log, 'w', encoding='utf-8') as f_debug:
                f_debug.write("[train_imgs anns debug]\n")
                for p in train_imgs:
                    anns = self.annotations.get(p, {}).get('anns', [])
                    f_debug.write(f"{p}: anns={repr(anns)}\n")
                f_debug.write("[val_imgs anns debug]\n")
                for p in val_imgs:
                    anns = self.annotations.get(p, {}).get('anns', [])
                    f_debug.write(f"{p}: anns={repr(anns)}\n")
        label_ok_train = sum(1 for p in train_imgs if self.annotations.get(p, {}).get('anns', []))
        label_ok_val = sum(1 for p in val_imgs if self.annotations.get(p, {}).get('anns', []))
        logger.info(f"train_imgs件数: {len(train_imgs)}, うちラベル付き: {label_ok_train}")
        logger.info(f"val_imgs件数: {len(val_imgs)}, うちラベル付き: {label_ok_val}")
        logger.debug(f"train_imgsサンプル: {train_imgs[:5]}")
        logger.debug(f"val_imgsサンプル: {val_imgs[:5]}")
        logger.info(f"[YOLO_EXPORT] 入力画像数: {n_total} (train: {len(train_imgs)}, val: {len(val_imgs)})")
        logger.info(f"[YOLO_EXPORT] ラベル有り画像数: train={label_ok_train}, val={label_ok_val}")
        # --- ここでラベルが空なら即中断 ---
        # バリデーション（出力前にDBのbbox値を正規化）
        from src.data.validate_db_bboxes import validate_bboxes_in_db
        validate_bboxes_in_db(self._db_path)
        if label_ok_train == 0 or label_ok_val == 0:
            if self.debug:
                debug_fallback_log = path_manager.project_root / "logs" / "03_label_export_fallback_debug.log"
                with open(debug_fallback_log, "w", encoding="utf-8") as f:
                    f.write(f"全self.images: {self.images}\n")
                    for k, v in self.annotations.items():
                        f.write(f"{k}: anns={len(v.get('anns', []))} abs_path={v.get('abs_path')}\n")
                    f.write(f"train_imgs: {train_imgs}\n")
                    f.write(f"val_imgs: {val_imgs}\n")
                    for p in train_imgs + val_imgs:
                        anns = self.annotations.get(p, {}).get('anns', [])
                        f.write(f"{p}: anns={len(anns)}\n")
            logger.error(f"trainまたはvalのラベル付き画像が0件です。詳細は logs/03_label_export_fallback_debug.log を参照してください。")
            raise RuntimeError("train/valにラベル付き画像がありません。データセット生成を中止します。")
        rejected = []
        out_img_count = 0
        success_list = []
        fail_list = []
        for norm_name in train_imgs:
            reason = self._export_one_with_reason(norm_name, train_img_dir, train_lbl_dir)
            if reason is None:
                out_img_count += 1
                success_list.append((norm_name, "OK"))
            else:
                rejected.append((norm_name, reason))
                fail_list.append((norm_name, reason))
        for norm_name in val_imgs:
            reason = self._export_one_with_reason(norm_name, val_img_dir, val_lbl_dir)
            if reason is None:
                out_img_count += 1
                success_list.append((norm_name, "OK"))
            else:
                rejected.append((norm_name, reason))
                fail_list.append((norm_name, reason))
        logger.info(f"[YOLO_EXPORT] 実際に出力した画像数: {out_img_count}")
        logger.info(f"[YOLO_EXPORT] ラベリング成功画像数: {len(success_list)}")
        logger.info(f"[YOLO_EXPORT] ラベリング失敗（除外）画像数: {len(fail_list)}")
        if rejected:
            logger.warning(f"[YOLO_EXPORT] 除外された画像一覧（理由付き）:")
            for p, reason in rejected:
                logger.warning(f"  {p}: {reason}")
        orig_class_set = set()
        orig_bbox_count = 0
        orig_roles = set()
        orig_labels = set()
        orig_class_names = set()
        for v in self.annotations.values():
            anns = v.get('anns', [])
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
            with open(lf, encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split()
                    if parts and len(parts) >= 5:
                        out_class_set.add(int(parts[0]))
                        out_bbox_count += 1
                        lines.append(line.strip())
            out_label_file_contents[os.path.basename(lf)] = lines
        out_class_names = set(self.classes[i] if i < len(self.classes) else str(i) for i in out_class_set)
        class_name_to_id_before = {}
        for v in self.annotations.values():
            anns = v.get('anns', [])
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