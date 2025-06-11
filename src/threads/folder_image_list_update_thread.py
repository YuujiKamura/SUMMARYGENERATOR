from PyQt6.QtCore import QThread, pyqtSignal

class FolderImageListUpdateThread(QThread):
    finished = pyqtSignal(list)
    def __init__(self, img_paths, parent=None):
        super().__init__(parent)
        self.img_paths = img_paths
    def run(self):
        # 必要ならここでサムネイル生成など重い処理を実行
        self.finished.emit(self.img_paths) 