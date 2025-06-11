from pathlib import Path
import shutil
import json
from src.data.db_to_yolo_dataset import safe_imread_with_temp, convert_bbox_to_yolo

class ImageRecord:
    def __init__(self, filename, image_path, bboxes, images_dir, labels_dir, debug_log_path):
        self.filename = filename
        self.image_path = image_path
        self.bboxes = bboxes
        self.images_dir = images_dir
        self.labels_dir = labels_dir
        self.debug_log_path = debug_log_path
        self.dst_img = images_dir / Path(image_path).name
        self.img_w = None
        self.img_h = None
        self.status = ''
        self.error = ''
        self.bbox_results = []

    def process(self):
        src_img = Path(self.image_path)
        if src_img.exists():
            shutil.copy2(src_img, self.dst_img)
            img = safe_imread_with_temp(self.dst_img)
            if img is None:
                self.status = 'skip'
                self.error = f'画像読み込み失敗: {self.dst_img}'
                return
            self.img_h, self.img_w = img.shape[:2]
            if not self.img_w or not self.img_h or self.img_w <= 1 or self.img_h <= 1:
                print(f'[警告] 画像サイズ取得失敗: {self.dst_img} → CALS標準サイズ(1280,960)で正規化')
                self.img_w, self.img_h = 1280, 960
            if self.img_w <= 1 or self.img_h <= 1:
                with open(self.debug_log_path, 'w', encoding='utf-8') as debugf:
                    debugf.write(f"[ERROR] 画像サイズ異常: filename={self.filename} img_w={self.img_w} img_h={self.img_h} path={self.dst_img}\n")
                print(f"[ERROR] 画像サイズ異常: filename={self.filename} img_w={self.img_w} img_h={self.img_h} path={self.dst_img}")
            try:
                bbox_list = json.loads(self.bboxes)
                with open(self.debug_log_path, 'w', encoding='utf-8') as debugf:
                    debugf.write(f"[DEBUG] filename={self.filename} bbox_list={json.dumps(bbox_list, ensure_ascii=False)}\n")
                print(f"[DEBUG] filename={self.filename} bbox_list={json.dumps(bbox_list, ensure_ascii=False)}")
            except Exception as e:
                self.status = 'skip'
                self.error = f'bboxesパース失敗: {self.bboxes} ({e})'
                return
            label_path = self.labels_dir / (src_img.stem + '.txt')
            with open(label_path, 'w', encoding='utf-8') as f:
                for bbox in bbox_list:
                    with open(self.debug_log_path, 'w', encoding='utf-8') as debugf:
                        debugf.write(f"[DEBUG] filename={self.filename} bbox={json.dumps(bbox, ensure_ascii=False)}\n")
                    print(f"[DEBUG] filename={self.filename} bbox={json.dumps(bbox, ensure_ascii=False)}")
                    bbox_info = {'src': bbox, 'result': None, 'status': '', 'error': ''}
                    try:
                        if not (isinstance(bbox, dict) or (isinstance(bbox, (list, tuple)) and len(bbox) >= 5)):
                            bbox_info['status'] = 'skip'
                            bbox_info['error'] = 'bbox形式不正'
                            self.bbox_results.append(bbox_info)
                            continue
                        class_id, x, y, w, h = convert_bbox_to_yolo(bbox, self.img_w, self.img_h)
                        if w <= 0 or h <= 0:
                            bbox_info['status'] = 'skip'
                            bbox_info['error'] = f'幅または高さが0以下: w={w}, h={h}'
                            bbox_info['result'] = [class_id, x, y, w, h]
                            self.bbox_results.append(bbox_info)
                            continue
                        f.write(f'{class_id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n')
                        bbox_info['status'] = 'ok'
                        bbox_info['result'] = [class_id, x, y, w, h]
                        self.bbox_results.append(bbox_info)
                    except Exception as e:
                        bbox_info['status'] = 'error'
                        bbox_info['error'] = str(e)
                        self.bbox_results.append(bbox_info)
            self.status = 'ok'
        else:
            self.status = 'skip'
            self.error = f'画像ファイルが存在しません: {src_img}'
            print(f'画像ファイルが存在しません: {src_img}')
