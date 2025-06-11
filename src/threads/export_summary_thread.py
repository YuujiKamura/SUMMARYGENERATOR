from PyQt6.QtCore import QThread, pyqtSignal
import json
from src.excel_photobook_exporter import export_excel_photobook
import os
import threading

class ExportSummaryThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, role_mapping_path, image_roles_path, mapping, records, out_path, match_results, cache_dir, parent=None):
        super().__init__(parent)
        self.role_mapping_path = role_mapping_path
        self.image_roles_path = os.path.abspath(image_roles_path)
        self.mapping = mapping
        self.records = records
        self.out_path = out_path
        self.match_results = match_results
        self.cache_dir = os.path.abspath(cache_dir)

    def run(self):
        def target():
            try:
                self.progress.emit('画像ロール情報読込中...')
                with open(self.image_roles_path, encoding='utf-8') as f:
                    image_roles = json.load(f)
                mapping = self.mapping
                records = self.records
                parent_folder_name = getattr(self, 'parent_folder_name', None)
                export_excel_photobook(self.match_results, image_roles, records, self.out_path, parent_folder_name, self.cache_dir, self.role_mapping_path)
                self.finished.emit(f'Excelサマリーを出力しました: {self.out_path}')
            except Exception as e:
                self.error.emit(f'Excel出力中にエラー: {e}')
        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout=60)
        if thread.is_alive():
            self.error.emit('Excel出力がタイムアウトしました（60秒）') 