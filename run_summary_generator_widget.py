import sys
import os
import traceback
import argparse
import subprocess
import threading
import time
import multiprocessing

def excepthook(type, value, tb):
    with open("summarygenerator_error.log", "w", encoding="utf-8") as f:
        traceback.print_exception(type, value, tb, file=f)
    sys.__excepthook__(type, value, tb)
sys.excepthook = excepthook

# src配下に移動した場合のパス調整
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, 'src'))
sys.path.insert(0, project_root)

# DBリセット
from src.db_manager import reset_all_tables, import_image_preview_cache_json
from src.utils.path_manager import PathManager
from src.services.summary_data_service import SummaryDataService
# DB・リソース初期化
SummaryDataService().reset_all_resources()
# パスマネージャー経由でJSONパス取得しDB登録
pm = PathManager()
import_image_preview_cache_json(json_path=pm.image_preview_cache_master)

print(f"[DEBUG] sys.path: {sys.path}")

parser = argparse.ArgumentParser()
parser.add_argument("--cli", action="store_true", help="CLIモードで起動")
parser.add_argument("--create-yolo-dataset", action="store_true", help="YOLOデータセット作成")
parser.add_argument("--json", type=str, help="画像リストJSONのパス")
parser.add_argument("--out", type=str, help="出力先ディレクトリ")
args, unknown = parser.parse_known_args()

def cli_main(json_path, out):
    from summarygenerator.utils.yolo_dataset_actions import YoloDatasetActionHandler, ErrorReporter
    handler = YoloDatasetActionHandler(None)
    try:
        handler._execute_yolo_dataset_creation(json_path, out, status_callback=None)
    except Exception:
        sys.exit(1)

if __name__ == "__main__":
    if args.cli and args.create_yolo_dataset:
        from summarygenerator.utils.path_manager import PathManager
        from summarygenerator.utils.yolo_dataset_actions import ErrorReporter
        ErrorReporter.set_cli_mode(True)
        path_manager = PathManager()
        json_path = args.json if args.json else path_manager.current_image_list_json
        if not json_path or not args.out:
            ErrorReporter.report(Exception("--json <画像リストJSON> と --out <出力先ディレクトリ> を指定してください。"), context="CLI引数")
            sys.exit(1)
        p = multiprocessing.Process(target=cli_main, args=(json_path, args.out))
        p.start()
        p.join(60)
        if p.is_alive():
            ErrorReporter.report(Exception("タイムアウト: CLI処理が60秒以内に完了しませんでした。"), context="CLIタイムアウト")
            p.terminate()
            p.join()
            sys.exit(1)
        sys.exit(p.exitcode)

from src.summary_generator_widget import SummaryGeneratorWidget
from PyQt6.QtWidgets import QApplication

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = SummaryGeneratorWidget()
    w.show()
    sys.exit(app.exec())
