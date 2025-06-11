import os
from typing import Optional, Dict, Any
from pathlib import Path
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QWidget
from summarygenerator.utils.yolo_dataset_exporter import YoloDatasetExporter

class YoloDatasetActionHandler:
    def __init__(self, parent_widget: QWidget):
        self.parent_widget = parent_widget
    def create_yolo_dataset_from_current_json(self, current_json_path: str, status_callback: Optional[callable] = None) -> Optional[Dict[str, Any]]:
        if not current_json_path or not os.path.exists(current_json_path):
            QMessageBox.warning(self.parent_widget, "エラー", "有効な画像リストJSONが設定されていません。")
            return None
        output_dir = QFileDialog.getExistingDirectory(self.parent_widget, "YOLO DataSet出力先ディレクトリを選択")
        if not output_dir:
            return None
        return self._execute_yolo_dataset_creation(current_json_path, output_dir, status_callback)
    def create_yolo_dataset_from_pathmanager(self, path_manager, status_callback: Optional[callable] = None) -> Optional[Dict[str, Any]]:
        current_json = getattr(path_manager, 'current_image_list_json', None)
        return self.create_yolo_dataset_from_current_json(current_json, status_callback)
    def _execute_yolo_dataset_creation(self, json_path: str, output_dir: str, status_callback: Optional[callable] = None) -> Dict[str, Any]:
        try:
            if status_callback:
                status_callback("YOLO DataSet作成中...")
            exporter = YoloDatasetExporter(
                image_list_json_paths=[json_path],
                output_dir=output_dir,
                val_ratio=0.2
            )
            result = exporter.export(mode='all', force_flush=True)
            msg = f"YOLO DataSet作成完了: {result['output_dir']}"
            if 'class_count_after' in result:
                msg += f" (クラス数: {result['class_count_after']}"
            if 'bbox_count_after' in result:
                msg += f", BBox数: {result['bbox_count_after']}"
            if 'class_count_after' in result or 'bbox_count_after' in result:
                msg += ")"
            if status_callback:
                status_callback(msg)
            QMessageBox.information(self.parent_widget, "YOLO DataSet作成完了", f"YOLO DataSetの作成が正常に完了しました。\n\n出力先: {result['output_dir']}\ndataset.yamlファイルが作成されました。")
            return result
        except Exception as e:
            import traceback
            error_msg = f"YOLO DataSet作成エラー: {str(e)}"
            print(f"[ERROR] {error_msg}")
            traceback.print_exc()
            if status_callback:
                status_callback(f"エラー: {error_msg}")
            QMessageBox.critical(self.parent_widget, "エラー", f"YOLO DataSet作成中にエラーが発生しました:\n\n{str(e)}")
            raise

def create_yolo_dataset_action(parent_widget: QWidget, current_json_path: str, status_callback: Optional[callable] = None) -> Optional[Dict[str, Any]]:
    handler = YoloDatasetActionHandler(parent_widget)
    return handler.create_yolo_dataset_from_current_json(current_json_path, status_callback)

def create_yolo_dataset_from_pathmanager_action(parent_widget: QWidget, path_manager, status_callback: Optional[callable] = None) -> Optional[Dict[str, Any]]:
    handler = YoloDatasetActionHandler(parent_widget)
    return handler.create_yolo_dataset_from_pathmanager(path_manager, status_callback) 