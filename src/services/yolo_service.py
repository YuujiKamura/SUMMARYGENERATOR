from PyQt6.QtCore import QThread, pyqtSignal
from src.yolo_predict_core import YOLOPredictor

class YoloWorker(QThread):
    finished = pyqtSignal(list, object)  # (bboxes, error)

    def __init__(self, img_path: str, model_path: str,
                 merge_roles: bool, old_bboxes, roles):
        super().__init__()
        self.img_path = img_path
        self.model_path = model_path
        self.merge_roles = merge_roles
        self.old_bboxes = old_bboxes
        self.roles = roles

    def run(self):
        try:
            preds = YOLOPredictor(self.model_path).predict(
                self.img_path,
                merge_roles=self.merge_roles,
                old_bboxes=self.old_bboxes,
                roles=self.roles,
            )
            self.finished.emit(preds, None)
        except Exception as e:
            self.finished.emit([], e)
