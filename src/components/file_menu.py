from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QAction
import logging
import subprocess
import sys
import os

logger = logging.getLogger(__name__)

def create_file_menu(parent, on_open_json, on_export_excel_from_db):
    """
    ファイルメニュー(QMenu)を生成し、各アクションにコールバックを接続して返す。
    Args:
        parent: QMenuBarやQMainWindowなどの親ウィジェット
        on_open_json: JSONファイルを開くアクションのコールバック
        on_export_excel_from_db: DB画像リストからExcelエクスポートするアクションのコールバック
    Returns:
        QMenu: ファイルメニュー
    """
    logger.debug('ファイルメニュー生成開始')
    file_menu = QMenu('ファイル', parent)

    open_json_action = QAction('画像リストJSONを開く', parent)
    open_json_action.triggered.connect(on_open_json)
    file_menu.addAction(open_json_action)

    export_excel_db_action = QAction('DB画像リストからExcelエクスポート', parent)
    export_excel_db_action.triggered.connect(on_export_excel_from_db)
    file_menu.addAction(export_excel_db_action)

    # YOLO学習一括実行
    def run_yolo_workflow():
        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'run_create_yolo_dataset_from_json.py')
        script_path = os.path.abspath(script_path)
        logger.info(f'YOLO学習一括実行: {script_path}')
        try:
            subprocess.Popen([sys.executable, script_path], shell=False)
        except Exception as e:
            logger.error(f'YOLO学習一括実行の起動に失敗: {e}')
    yolo_action = QAction('YOLO学習一括実行', parent)
    yolo_action.triggered.connect(run_yolo_workflow)
    file_menu.addAction(yolo_action)

    logger.debug('ファイルメニュー生成完了')
    return file_menu
