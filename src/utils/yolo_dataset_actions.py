import os
from typing import Optional, Dict, Any
from pathlib import Path
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QWidget
from summarygenerator.utils.yolo_dataset_exporter import YoloDatasetExporter
from rich.console import Console
from rich.traceback import install as rich_install

# アプリ独自の例外セット
class AppError(Exception):
    """アプリ全体の基底例外"""
class DataValidationError(AppError):
    """データ検証エラー"""
class YoloDatasetError(AppError):
    """YOLOデータセット作成エラー"""

# エラー出力一元管理クラス
class ErrorReporter:
    IS_CLI = False
    _console = Console()
    @staticmethod
    def set_cli_mode(is_cli: bool):
        ErrorReporter.IS_CLI = is_cli
        if is_cli:
            rich_install(show_locals=True)
    @staticmethod
    def report(e: Exception, context: Optional[str] = None, parent_widget: Optional[QWidget] = None, extra: Optional[str] = None):
        msg = f"[ERROR]{'['+context+']' if context else ''} {e}"
        if extra:
            msg += f"\n{extra}"
        # CLI: richでカラー出力
        if ErrorReporter.IS_CLI or parent_widget is None:
            ErrorReporter._console.print(f"[CLI] エラー: [bold red]{msg}[/bold red]")
            ErrorReporter._console.print_exception()
        # GUI: QMessageBox
        else:
            QMessageBox.critical(parent_widget, "エラー", msg)

class YoloDatasetActionHandler:
    def __init__(self, parent_widget: QWidget):
        self.parent_widget = parent_widget
    def create_yolo_dataset_from_current_json(self, current_json_path: str, status_callback: Optional[callable] = None) -> Optional[Dict[str, Any]]:
        if not current_json_path or not os.path.exists(current_json_path):
            abs_json = os.path.abspath(current_json_path) if current_json_path else '(None)'
            e = DataValidationError(f"有効な画像リストJSONが設定されていません。 入力: {abs_json}")
            ErrorReporter.report(e, context="YOLO DataSet作成", parent_widget=self.parent_widget)
            raise e
        if self.parent_widget is None:
            output_dir = input("[CLI] YOLO DataSet出力先ディレクトリを入力してください: ").strip()
            if not output_dir:
                ErrorReporter.report(DataValidationError("キャンセルされました。"), context="YOLO DataSet作成", parent_widget=None)
                return None
        else:
            output_dir = QFileDialog.getExistingDirectory(self.parent_widget, "YOLO DataSet出力先ディレクトリを選択")
            if not output_dir:
                return None
        abs_json = os.path.abspath(current_json_path)
        abs_out = os.path.abspath(output_dir)
        ErrorReporter.report(AppError(f"入力JSON: {abs_json}"), context="YOLO DataSet作成", parent_widget=self.parent_widget)
        ErrorReporter.report(AppError(f"出力先: {abs_out}"), context="YOLO DataSet作成", parent_widget=self.parent_widget)
        return self._execute_yolo_dataset_creation(current_json_path, output_dir, status_callback)
    def create_yolo_dataset_from_pathmanager(self, path_manager, status_callback: Optional[callable] = None) -> Optional[Dict[str, Any]]:
        current_json = getattr(path_manager, 'current_image_list_json', None)
        return self.create_yolo_dataset_from_current_json(current_json, status_callback)
    def _execute_yolo_dataset_creation(self, json_path: str, output_dir: str, status_callback: Optional[callable] = None) -> Dict[str, Any]:
        abs_json = os.path.abspath(json_path)
        abs_out = os.path.abspath(output_dir)
        try:
            if status_callback:
                status_callback(f"YOLO DataSet作成中... (入力: {abs_json}, 出力: {abs_out})")
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
            ErrorReporter.report(AppError(msg), context="YOLO DataSet作成", parent_widget=self.parent_widget)
            return result
        except Exception as e:
            error_msg = f"YOLO DataSet作成エラー: {str(e)} (入力: {abs_json}, 出力: {abs_out})"
            wrapped = YoloDatasetError(error_msg)
            ErrorReporter.report(wrapped, context="YOLO DataSet作成", parent_widget=self.parent_widget)
            raise wrapped

def create_yolo_dataset_action(parent_widget: QWidget, current_json_path: str, status_callback: Optional[callable] = None) -> Optional[Dict[str, Any]]:
    handler = YoloDatasetActionHandler(parent_widget)
    return handler.create_yolo_dataset_from_current_json(current_json_path, status_callback)

def create_yolo_dataset_from_pathmanager_action(parent_widget: QWidget, path_manager, status_callback: Optional[callable] = None) -> Optional[Dict[str, Any]]:
    handler = YoloDatasetActionHandler(parent_widget)
    return handler.create_yolo_dataset_from_pathmanager(path_manager, status_callback) 