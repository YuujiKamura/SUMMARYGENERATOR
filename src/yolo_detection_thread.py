from PyQt6.QtCore import QThread, pyqtSignal
from src.yolo_predict_core import YOLOPredictor

class YoloDetectionThread(QThread):
    finished = pyqtSignal(list, object)  # bboxes, error(None or Exception)
    def __init__(self, image_path, std_model_path, caption_model_path, merge_roles, old_bboxes, roles):
        super().__init__()
        self.image_path = image_path
        self.std_model_path = std_model_path
        self.caption_model_path = caption_model_path
        self.merge_roles = merge_roles
        self.old_bboxes = old_bboxes
        self.roles = roles

    def run(self):
        try:
            predictor = YOLOPredictor(self.std_model_path, self.caption_model_path)
            bboxes = predictor.predict(
                self.image_path,
                merge_roles=self.merge_roles,
                old_bboxes=self.old_bboxes,
                roles=self.roles
            )
            self.finished.emit(bboxes, None)
        except Exception as e:
            self.finished.emit([], e)
