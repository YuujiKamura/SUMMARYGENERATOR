from src.bbox.transform import horizontal_flip_bbox, clip_bbox_with_imgsize, clip01, clip_bbox01
from src.bbox.types import BBoxYOLO
from src.utils.bbox_normalizer import is_bbox_valid_yolo
import numpy as np
import logging

def apply_pipeline(img, boxes, i, pipes, img_w, img_h):
    # 入力bboxを[0,1]クリッピング
    boxes_clipped = [BBoxYOLO(b.cid, *clip_bbox01([b.cid, b.x, b.y, b.w, b.h])[1:]) for b in boxes]
    if i == 0:
        aug_img = img[:, ::-1]  # 水平反転
        aug_boxes = [BBoxYOLO(b.cid, *[clip01(v) for v in horizontal_flip_bbox([b.cid, b.x, b.y, b.w, b.h])[1:]]) for b in boxes_clipped]
        tag = 'flip'
    else:
        aug = pipes['color'] if i <= 3 else pipes['mixed']
        try:
            res = aug(image=img, bboxes=[b.xywh for b in boxes_clipped], class_labels=[b.cid for b in boxes_clipped])
            aug_img = res['image']
            aug_boxes = []
            for cid, bb in zip(res['class_labels'], res['bboxes']):
                try:
                    # bbox値をclipし、画像サイズで補正
                    b_clipped = clip_bbox01([cid, *bb])
                    b_img_clipped = clip_bbox_with_imgsize(b_clipped, img_w, img_h)
                    if b_img_clipped is not None:
                        _, x, y, w, h = b_img_clipped
                        if is_bbox_valid_yolo(x, y, w, h):
                            aug_boxes.append(BBoxYOLO(*b_img_clipped))
                except Exception:
                    continue
            tag = 'color_noise'
        except Exception:
            # albumentations自体がValueError等をraiseした場合は空リスト返す
            return img, [], 'albumentations_error'
    return aug_img, aug_boxes, tag

def run(source_iter, pipelines, n=5, save_and_log=None):
    logger = logging.getLogger('augment')
    for img_path, img, bboxes in source_iter:
        h, w = img.shape[:2]
        for i in range(n):
            aug_img, aug_boxes, tag = apply_pipeline(img, bboxes, i, pipelines, w, h)
            if not aug_boxes:
                continue
            if save_and_log:
                save_and_log(img_path, aug_img, aug_boxes, tag)
            logger.info(f"AUGMENT: {img_path.name} [{tag}] bbox={len(aug_boxes)}")
