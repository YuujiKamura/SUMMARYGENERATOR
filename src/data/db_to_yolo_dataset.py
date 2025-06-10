import sqlite3
from pathlib import Path
import json
import shutil
import os
import string
import random
from src.utils.bbox_normalizer import convert_bbox_to_yolo

DB_PATH = Path(__file__).parent / 'model_training_cache.db'

def fetch_all_records():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT filename, image_path, bboxes FROM image_cache')
    rows = c.fetchall()
    conn.close()
    return rows

def safe_imread_with_temp(src_path):
    """
    日本語・全角記号を含むパスの場合、C:\\temp_yolo_imagesに一時コピーし、
    半角英数字ファイル名でcv2.imreadする。
    """
    import cv2
    import shutil
    import re
    src_path = str(src_path)
    # 全角文字や日本語が含まれるか判定
    if re.search(r'[^\x00-\x7F]', src_path):
        temp_dir = Path('C:/temp_yolo_images')
        temp_dir.mkdir(parents=True, exist_ok=True)
        # ランダムな半角英数字ファイル名を生成
        ext = Path(src_path).suffix
        randname = ''.join(random.choices(string.ascii_letters + string.digits, k=16)) + ext
        temp_path = temp_dir / randname
        try:
            shutil.copy2(src_path, temp_path)
            img = cv2.imread(str(temp_path))
            temp_path.unlink(missing_ok=True)
            return img
        except Exception as e:
            print(f'[警告] テンポラリコピー失敗: {src_path} → {temp_path} ({e})')
            return None
    else:
        return cv2.imread(src_path)

class YoloDatasetBuilder:
    def __init__(self, out_dir=None):
        import cv2
        if out_dir is None:
            out_dir = Path(__file__).parent.parent / 'datasets' / 'yolo_dataset_from_db'
        self.out_dir = Path(out_dir)
        self.images_dir = self.out_dir / 'images' / 'train'
        self.labels_dir = self.out_dir / 'labels' / 'train'
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.labels_dir.mkdir(parents=True, exist_ok=True)
        self.records = fetch_all_records()
        self.dump_records = []
        self.debug_log_path = Path(__file__).parent / 'db_to_yolo_dataset_debug.log'
        # 1. 画像ごとのbbox情報を一時保存
        self.image_bboxes = []  # [{filename, image_path, bboxes: [dict]}]
        self.class_names_set = set()
        self.class_name_to_id = dict()
        self.id_to_class_name = dict()
        self.class_names = []

    def process(self):
        # 1. 全画像・全bboxからクラス名を抽出
        for filename, image_path, bboxes in self.records:
            try:
                bbox_list = json.loads(bboxes)
            except Exception:
                bbox_list = []
            img_info = {'filename': filename, 'image_path': image_path, 'bboxes': bbox_list}
            self.image_bboxes.append(img_info)
            for bbox in bbox_list:
                if isinstance(bbox, dict):
                    cname = bbox.get('role') or bbox.get('label')
                    if cname:
                        self.class_names_set.add(cname)
        # 2. クラス名→ID割当
        self.class_names = sorted(self.class_names_set)
        self.class_name_to_id = {name: i for i, name in enumerate(self.class_names)}
        self.id_to_class_name = {i: name for i, name in enumerate(self.class_names)}
        # 3. YOLOデータセット書き出し
        for img_info in self.image_bboxes:
            self.process_image(img_info)
        self.write_yaml()
        self.write_dump()

    def process_image(self, img_info):
        filename = img_info['filename']
        image_path = img_info['image_path']
        bbox_list = img_info['bboxes']
        src_img = Path(image_path)
        dst_img = self.images_dir / src_img.name
        img_result = {
            'filename': filename,
            'image_path': str(image_path),
            'dst_img': str(dst_img),
            'bboxes': [],
            'status': '',
            'error': '',
            'img_w': None,
            'img_h': None,
        }
        if src_img.exists():
            shutil.copy2(src_img, dst_img)
            img = safe_imread_with_temp(dst_img)
            if img is None:
                img_result['status'] = 'skip'
                img_result['error'] = f'画像読み込み失敗: {dst_img}'
                self.dump_records.append(img_result)
                print(f'画像読み込み失敗: {dst_img}')
                return
            img_h, img_w = img.shape[:2]
            if not img_w or not img_h or img_w <= 1 or img_h <= 1:
                print(f'[警告] 画像サイズ取得失敗: {dst_img} → CALS標準サイズ(1280,960)で正規化')
                img_w, img_h = 1280, 960
            img_result['img_w'] = img_w
            img_result['img_h'] = img_h
            if img_w <= 1 or img_h <= 1:
                with open(self.debug_log_path, 'a', encoding='utf-8') as debugf:
                    debugf.write(f"[ERROR] 画像サイズ異常: filename={filename} img_w={img_w} img_h={img_h} path={dst_img}\n")
                print(f"[ERROR] 画像サイズ異常: filename={filename} img_w={img_w} img_h={img_h} path={dst_img}")
            label_path = self.labels_dir / (src_img.stem + '.txt')
            with open(label_path, 'w', encoding='utf-8') as f:
                for bbox in bbox_list:
                    bbox_info = {'src': bbox, 'result': None, 'status': '', 'error': ''}
                    try:
                        if not (isinstance(bbox, dict) or (isinstance(bbox, (list, tuple)) and len(bbox) >= 5)):
                            bbox_info['status'] = 'skip'
                            bbox_info['error'] = 'bbox形式不正'
                            img_result['bboxes'].append(bbox_info)
                            continue
                        # --- クラス名抽出 ---
                        class_name = None
                        if isinstance(bbox, dict):
                            class_name = bbox.get('role') or bbox.get('label')
                        if not class_name:
                            class_name = self.class_names[0] if self.class_names else 'class0'
                        class_id = self.class_name_to_id.get(class_name, 0)
                        # --- bbox変換 ---
                        class_id_yolo, x, y, w, h = convert_bbox_to_yolo(bbox, img_w, img_h)
                        if w <= 0 or h <= 0:
                            bbox_info['status'] = 'skip'
                            bbox_info['error'] = f'幅または高さが0以下: w={w}, h={h}'
                            bbox_info['result'] = [class_id, x, y, w, h]
                            img_result['bboxes'].append(bbox_info)
                            continue
                        f.write(f'{class_id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n')
                        bbox_info['status'] = 'ok'
                        bbox_info['result'] = [class_id, x, y, w, h]
                        img_result['bboxes'].append(bbox_info)
                    except Exception as e:
                        bbox_info['status'] = 'error'
                        bbox_info['error'] = str(e)
                        img_result['bboxes'].append(bbox_info)
            img_result['status'] = 'ok'
        else:
            img_result['status'] = 'skip'
            img_result['error'] = f'画像ファイルが存在しません: {src_img}'
        self.dump_records.append(img_result)

    def write_yaml(self):
        nc = len(self.class_names) if self.class_names else 1
        names = self.class_names if self.class_names else ['class0']
        abs_images_dir = str((self.out_dir / 'images' / 'train').resolve())
        yaml_path = self.out_dir / 'dataset.yaml'
        yaml_content = f'''train: {abs_images_dir}\nval: {abs_images_dir}\nnc: {nc}\nnames: {names}\n'''
        with open(yaml_path, 'w', encoding='utf-8') as f:
            f.write(yaml_content)

    def write_dump(self):
        logs_dir = Path(__file__).parent.parent.parent / 'logs'
        logs_dir.mkdir(exist_ok=True)
        dump_path = logs_dir / '02_yolo_dataset_dump.json'
        with open(dump_path, 'w', encoding='utf-8') as f:
            json.dump(self.dump_records, f, ensure_ascii=False, indent=2)

def main(out_dir=None):
    builder = YoloDatasetBuilder(out_dir)
    builder.process()

if __name__ == '__main__':
    main()