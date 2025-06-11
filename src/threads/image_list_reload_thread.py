from PyQt6.QtCore import QThread, pyqtSignal
from src.summary_generator import get_all_image_data

class ImageListReloadThread(QThread):
    finished = pyqtSignal(dict, dict, dict, list, list, dict)
    error = pyqtSignal(str)
    def __init__(self, json_path, folder_path, parent=None):
        super().__init__(parent)
        self.json_path = json_path
        self.folder_path = folder_path
    def run(self):
        try:
            # get_all_image_dataで全データを取得
            data = get_all_image_data(self.json_path, self.folder_path)
            self.finished.emit(
                data['image_roles'],
                data['match_results'],
                data['folder_to_images'],
                data['folder_names'],
                data['records'],
                data['thermo_remarks_map']
            )
        except Exception as e:
            self.error.emit(str(e)) 