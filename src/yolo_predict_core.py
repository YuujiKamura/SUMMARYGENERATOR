import os
from pathlib import Path
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
        # ModelManager でモデル情報を取得するだけに変更
        if self.yolo_std is None:
            self.yolo_std = self.model_manager
        if self.yolo_caption is None:
            self.yolo_caption = self.model_manager

    def predict(self, image_path, merge_roles=True, old_bboxes=None, roles=None):
        self.load_models()
        # ModelManager には predict は無いので、ここは仮実装
        # preds_std, preds_caption = [], []
        # ここで本来はYOLO推論を呼ぶが、ダミーで空リスト返す
        preds_std = []
        preds_caption = []
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
        # BoundingBox生成も空リスト
        new_bboxes = []
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
