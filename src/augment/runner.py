import albumentations as A
from src.augment.sources import folder_source
from src.augment.core import run as core_run
from src.augment.save_and_log import save_and_log
from pathlib import Path
import traceback
import json
import shutil
from src.bbox.types import BBoxYOLO

color_pipe = A.Compose([
    A.RandomBrightnessContrast(p=0.8),
    A.HueSaturationValue(p=0.8),
    A.GaussNoise(p=0.8),
], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels']))
mixed_pipe = A.Compose([
    A.HorizontalFlip(p=0.5),
    A.RandomBrightnessContrast(p=0.5),
    A.HueSaturationValue(p=0.5),
    A.GaussNoise(p=0.3),
], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels']))

PIPES = {'color': color_pipe, 'mixed': mixed_pipe}

class AugmentRunner:
    def __init__(self, dataset_dir, db_path, n=5, output_dir=None):
        self.dataset_dir = Path(dataset_dir)
        self.db_path = Path(db_path)
        self.n = n
        self.output_dir = Path(output_dir) if output_dir else self.dataset_dir.parent / 'yolo_augmented'
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self, show_progress=False, return_summary=False):
        # --- 生画像・ラベルをDBに登録（ファイルコピーせずDB経由に統一） ---
        from src.data.json_to_db import insert_image_cache_record
        for split in ['train', 'val']:
            images_dir = self.dataset_dir / 'images' / split
            labels_dir = self.dataset_dir / 'labels' / split
            for img_file in images_dir.glob('*'):
                if img_file.is_file() and img_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                    label_path = labels_dir / (img_file.stem + '.txt')
                    bboxes = []
                    if label_path.exists():
                        with open(label_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                parts = line.strip().split()
                                if len(parts) == 5:
                                    cid_f, x_f, y_f, bw_f, bh_f = map(float, parts)
                                    bboxes.append(BBoxYOLO(int(cid_f), x_f, y_f, bw_f, bh_f))
                    # BBoxYOLOオブジェクトが含まれる場合はdictへ変換してJSONシリアライズできるようにする
                    serializable_bboxes = [b.__dict__ if hasattr(b, '__dict__') else b for b in bboxes]
                    insert_image_cache_record(img_file.name, str(img_file.resolve()), serializable_bboxes, db_path=str(self.db_path))
        # --- まず元画像・元ラベルをoutput_dir配下にコピー（train/valごと） ---
        for split in ['train', 'val']:
            src_img_dir = self.dataset_dir / 'images' / split
            src_label_dir = self.dataset_dir / 'labels' / split
            dst_img_dir = self.output_dir / 'images' / split
            dst_label_dir = self.output_dir / 'labels' / split
            dst_img_dir.mkdir(parents=True, exist_ok=True)
            dst_label_dir.mkdir(parents=True, exist_ok=True)
            for img_file in src_img_dir.glob('*'):
                if img_file.is_file() and img_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                    shutil.copy2(img_file, dst_img_dir / img_file.name)
                    label_path = src_label_dir / (img_file.stem + '.txt')
                    if label_path.exists():
                        shutil.copy2(label_path, dst_label_dir / label_path.name)
        total = 0
        tried = 0  # 試行回数
        saved = 0  # 実際に保存できた拡張画像数
        fail = 0
        failed_files = []
        fail_reasons = {}
        fail_examples = []
        all_img_paths = list((self.dataset_dir / 'images' / 'train').glob('*.jpg'))
        total_imgs = len(all_img_paths)
        def save_and_log_with_outdir(img_path, aug_img, aug_boxes, tag, split='train'):
            try:
                dst_img_dir = self.output_dir / 'images' / split
                dst_label_dir = self.output_dir / 'labels' / split
                dst_img_dir.mkdir(parents=True, exist_ok=True)
                dst_label_dir.mkdir(parents=True, exist_ok=True)
                base = Path(img_path).stem
                out_img_name = f"{base}_aug{tag}.jpg"
                out_label_name = f"{base}_aug{tag}.txt"
                import cv2
                cv2.imwrite(str(dst_img_dir / out_img_name), aug_img)
                with open(dst_label_dir / out_label_name, 'w', encoding='utf-8') as f:
                    for b in aug_boxes:
                        if isinstance(b, dict):
                            cid = b.get('cid', 0)
                            x = b.get('x', 0)
                            y = b.get('y', 0)
                            w = b.get('w', 0)
                            h = b.get('h', 0)
                        elif isinstance(b, BBoxYOLO):
                            cid, x, y, w, h = b.cid, b.x, b.y, b.w, b.h
                        else:
                            cid, x, y, w, h = b
                        f.write(f"{cid} {x} {y} {w} {h}\n")
                return True, None
            except Exception as e:
                return False, e
        # train/val両方を拡張
        for split in ['train', 'val']:
            images_dir = self.dataset_dir / 'images' / split
            labels_dir = self.dataset_dir / 'labels' / split
            for img_path in images_dir.glob('*.jpg'):
                label_path = labels_dir / (img_path.stem + '.txt')
                if not label_path.exists():
                    continue
                import cv2
                img = cv2.imread(str(img_path))
                if img is None:
                    continue
                h, w = img.shape[:2]
                bboxes = []
                with open(label_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) != 5:
                            continue
                        cid_f, x_f, y_f, bw_f, bh_f = map(float, parts)
                        bboxes.append(BBoxYOLO(int(cid_f), x_f, y_f, bw_f, bh_f))
                if not bboxes:
                    continue
                for i in range(self.n):
                    total += 1
                    tried += 1
                    try:
                        from src.augment.core import apply_pipeline
                        aug_img, aug_boxes, tag = apply_pipeline(img, bboxes, i, PIPES, w, h)
                        if not aug_boxes:
                            fail += 1
                            reason = 'no_aug_boxes'
                            fail_reasons[reason] = fail_reasons.get(reason, 0) + 1
                            if len(fail_examples) < 5:
                                fail_examples.append({'img': str(img_path), 'bboxes': bboxes, 'reason': reason})
                            continue
                        ok, err = save_and_log_with_outdir(img_path, aug_img, aug_boxes, tag, split=split)
                        if ok:
                            saved += 1
                        else:
                            fail += 1
                            reason = str(type(err).__name__)
                            fail_reasons[reason] = fail_reasons.get(reason, 0) + 1
                            if len(fail_examples) < 5:
                                fail_examples.append({'img': str(img_path), 'bboxes': bboxes, 'reason': reason, 'error': str(err), 'trace': traceback.format_exc()})
                            failed_files.append(str(img_path))
                    except Exception as e:
                        fail += 1
                        reason = str(type(e).__name__)
                        fail_reasons[reason] = fail_reasons.get(reason, 0) + 1
                        if len(fail_examples) < 5:
                            fail_examples.append({'img': str(img_path), 'bboxes': bboxes, 'reason': reason, 'error': str(e), 'trace': traceback.format_exc()})
                        failed_files.append(str(img_path))
                    if show_progress:
                        pass  # 進捗個別ログを完全に抑制
        summary = {
            'total': total,
            'tried': tried,
            'saved': saved,
            'fail': fail,
            'failed_files': failed_files,
            'fail_reasons': fail_reasons,
            # 'fail_examples': fail_examples,  # サマリー返却時は詳細を除外
            'output_dir': str(self.output_dir)
        }
        if fail > 0:
            print('[AUG][FAIL SUMMARY]')
            print('失敗理由ごとの件数:', fail_reasons)
            # 失敗例詳細の個別出力を抑制（サマリーのみ）
        if return_summary:
            return summary

def main(dataset_dir, n=5, output_dir=None, show_progress=False, return_summary=False, db_path=None):
    runner = AugmentRunner(dataset_dir, db_path=db_path, n=n, output_dir=output_dir)
    return runner.run(show_progress=show_progress, return_summary=return_summary)

if __name__ == '__main__':
    import sys
    main(sys.argv[1])
