import os
from pathlib import Path
from .yolo_classifier import YOLOClassifier
from .utils.bbox_utils import BoundingBox
from .utils.model_manager import ModelManager

class YOLOPredictor:
    def __init__(self, std_model_path=None, caption_model_path=None, conf_threshold=0.25):
        self.conf_threshold = conf_threshold
        self.model_manager = ModelManager()
        # モデルパスが指定されていなければ、model_managerから取得
        if std_model_path is None:
            default = self.model_manager.get_default_model()
            self.std_model_path = default[0] if default else None
        else:
            self.std_model_path = std_model_path
        if caption_model_path is None:
            # キャプション用モデルも同様に取得（ここでは同じものを使う例）
            self.caption_model_path = self.std_model_path
        else:
            self.caption_model_path = caption_model_path
        self.yolo_std = None
        self.yolo_caption = None

    def load_models(self):
        if self.yolo_std is None:
            self.yolo_std = YOLOClassifier(model_path=self.std_model_path, conf_threshold=self.conf_threshold)
        if self.yolo_caption is None:
            self.yolo_caption = YOLOClassifier(model_path=self.caption_model_path, conf_threshold=self.conf_threshold)

    def predict(self, image_path, merge_roles=True, old_bboxes=None, roles=None):
        """
        画像に対してYOLO推論を行い、バウンディングボックスを返す。
        merge_roles: 既存bbox(role付き)をマージするか
        old_bboxes: 既存bboxリスト（BoundingBox型）
        roles: ロールリスト（未使用だが将来拡張用）
        """
        self.load_models()
        preds_std = self.yolo_std.predict(image_path)
        preds_caption = self.yolo_caption.predict(image_path)
        # キャプションボード検出モデルのクラス名を上書き
        preds_caption = [(cid, "caption_board", conf, xyxy) for cid, cname, conf, xyxy in preds_caption]
        # 検出結果をマージ（重複除去:座標・クラス名一致）
        def bbox_key(pred):
            cid, cname, conf, xyxy = pred
            return (tuple(xyxy) if xyxy else None, cname)
        seen = set()
        merged_preds = []
        for pred in preds_std + preds_caption:
            key = bbox_key(pred)
            if key not in seen:
                seen.add(key)
                merged_preds.append(pred)
        new_bboxes = [BoundingBox(cid, cname, conf, xyxy, None) for cid, cname, conf, xyxy in merged_preds]
        if merge_roles and old_bboxes:
            role_bboxes = [b for b in old_bboxes if getattr(b, 'role', None)]
            def is_duplicate(new_bbox):
                for rb in role_bboxes:
                    if rb.xyxy == new_bbox.xyxy and rb.cname == new_bbox.cname:
                        return True
                return False
            merged = role_bboxes + [b for b in new_bboxes if not is_duplicate(b)]
            bboxes = merged
        else:
            bboxes = new_bboxes
        return bboxes
