import os
import sys
import json
import logging

# --- ロギング初期化 ---
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, 'summary_generator_app.log')
logging.basicConfig(
    level=logging.WARNING,  # INFO→WARNINGに変更
    format='[%(asctime)s][%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(log_path, encoding='utf-8'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# 直接実行時にもsrc配下importが通るようにパスを調整
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

"""
PhotoCategorizer サマリー生成メインウィジェット
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QStatusBar, QMenuBar, QMenu, QMainWindow, QComboBox, QToolButton, QFileDialog, QSplitter, QTextEdit
)
from PyQt6.QtWidgets import QDialog
from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtGui import QAction
from src.utils.path_manager import PathManager
from src.widgets.record_panel import RecordPanel
from src.widgets.image_list_panel import ImageListPanel
from src.services.summary_data_service import SummaryDataService
from src.utils.context_menu_utils import handle_image_list_context_menu
from src.dictionary_manager import DictionaryManager
from src.utils.chain_record_utils import find_chain_records_by_roles
from src.utils.image_selection_debug import generate_image_selection_debug
from src.utils.role_mapping_utils import load_role_mapping
from src.utils.record_matching_utils import match_roles_records_one_stop
from dataclasses import dataclass, field
from typing import List, Optional
from src.utils.image_entry import ImageEntry
from src.utils.image_data_manager import ImageDataManager
from src.db_manager import DB_PATH
from src.components.summary_generator_ui import SummaryGeneratorUI
from src.components.summary_generator_viewmodel import SummaryGeneratorViewModel
from src.services.summary_export_service import export_summary as export_summary_service
from src.components.edit_menu import create_edit_menu

# --- path_managerの初期化 ---
path_manager = PathManager()

# --- 集約ファイルの絶対パスをpath_managerで一元管理 ---
DATASET_JSON_PATH = str(path_manager.scan_for_images_dataset)
FOLDER_SUMMARY_PATH = str(path_manager.src_dir / "folder_summary.json")
ROLE_MAPPING_PATH = str(path_manager.role_mapping)
CACHE_DIR = str(path_manager.src_dir / "image_preview_cache")
CONFIG_PATH = str(path_manager.summary_generator_widget)
IMAGE_CACHE_DIR_CONFIG = str(path_manager.image_cache_dir_config)
IMAGE_ROLES_PATH = str(path_manager.scan_for_images_dataset)
RECORDS_PATH = str(path_manager.default_records)
LOCATION_HISTORY_PATH = str(path_manager.src_dir / "location_history.json")

class SummaryGeneratorWidget(QMainWindow):
    """
    サマリー生成メインウィジェット
    """
    test_finished = pyqtSignal()
    def __init__(self, parent=None, test_mode=False):
        super().__init__(parent)
        logger.info('SummaryGeneratorWidget: 初期化開始')
        # --- サービスクラスでDB・リソース初期化（必ず一度だけ呼ぶ）---
        self.data_service = SummaryDataService(db_path=DB_PATH)
        logger.info('SummaryDataServiceインスタンス生成: db_path=%s', DB_PATH)
        # 必要なマネージャやデータはサービスから取得
        self.dictionary_manager = self.data_service.dictionary_manager or DictionaryManager(DB_PATH)
        logger.info('DictionaryManagerインスタンス生成')
        db_role_mappings = self.data_service.role_mappings
        logger.debug('DBからrole_mappings取得: 件数=%d', len(db_role_mappings) if db_role_mappings else 0)
        # db_role_mappingsの中身がdictでなければjson.loadsで辞書化
        role_mappings_dicts = []
        for row in db_role_mappings:
            if isinstance(row, str):
                try:
                    row = json.loads(row)
                except Exception as e:
                    logger.warning('role_mappingsのjson.loads失敗: %s', e)
                    continue
            role_mappings_dicts.append(row)
        self.role_mapping = {row['role_name']: json.loads(row['mapping_json']) if row['mapping_json'] else {} for row in role_mappings_dicts}
        logger.info('role_mappingロード: keys=%s', list(self.role_mapping.keys()) if self.role_mapping else 'EMPTY')
        self.data_service = SummaryDataService(self.dictionary_manager, CACHE_DIR, RECORDS_PATH, role_mapping=self.role_mapping)
        logger.info('SummaryDataService再生成（role_mapping反映）')
        # 画像リストもDBから取得
        self.image_data_manager = ImageDataManager.from_db()
        logger.info('ImageDataManager.from_db()呼び出し')
        self.vm = SummaryGeneratorViewModel(self.data_service)
        self.test_mode = test_mode
        self.setup_ui()
        self.vm.image_list_changed.connect(self.image_list_panel.update_image_list)
        self.vm.remarks_changed.connect(lambda remarks: self.record_panel.update_records(remarks, None))
        self.vm.status_changed.connect(self.set_status_bar_message)
        # ここを修正: image_selected, image_double_clicked をWidget本体のハンドラに接続
        self.image_list_panel.image_selected.connect(self.on_image_selected)
        self.image_list_panel.image_double_clicked.connect(self.on_image_double_clicked)
        self._first_show = True
        logger.info('SummaryGeneratorWidget: 初期化完了')

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, '_first_show', True):
            self._first_show = False
            logger.info('showEvent: 初回表示で画像リスト自動ロード')
            self.load_image_list_from_path_manager()

    def setup_ui(self):
        # UI構築は分離クラスに委譲
        self.ui = SummaryGeneratorUI(self, path_manager, self.set_status_bar_message)
        # 主要UI部品をselfに再エクスポート（既存コード互換のため）
        self.menubar = self.ui.menubar
        self.image_list_panel = self.ui.image_list_panel
        self.record_panel = self.ui.record_panel
        self.category_combo = self.ui.category_combo
        self.order_button = self.ui.order_button
        self.status_bar = self.ui.status_bar
        self.json_path_edit = self.ui.json_path_edit
        self.folder_path_edit = self.ui.folder_path_edit
        # ファイル・編集・ヘルプメニューはUIクラスで一元管理
        # self.menubar.addMenu(edit_menu) などの重複追加は行わない
        # 追加のアクションやメニュー生成はここで行わない

    def on_json_path_changed(self, path):
        path_manager.current_image_list_json = path
        logging.info(f'[LOG] 画像リストパス変更: {path}')
        self.load_image_list_from_path_manager()

    def load_image_list_from_path_manager(self):
        # DBから画像リストを取得
        self.image_data_manager = ImageDataManager.from_db()
        self.update_image_list()

    def on_category_changed(self, idx):
        self.update_image_list()

    def on_order_button_clicked(self):
        # ボタンのラベルをトグル
        if self.order_button.isChecked():
            self.order_button.setText("古い写真が上")
        else:
            self.order_button.setText("新しい写真が上")
        self.update_image_list()

    def update_image_list(self):
        logging.info('[LOG] update_image_list: 開始')
        if hasattr(self, "image_data_manager"):
            entries = self.image_data_manager.entries
            self.data_service.set_all_entries(entries)
            for entry in entries:
                if hasattr(entry, 'chain_records'):
                    # logging.info(f"[DEBUG][Widget] image_path={getattr(entry, 'image_path', None)}, chain_records={[{'remarks': getattr(r, 'remarks', None), 'photo_category': getattr(r, 'photo_category', None)} for r in getattr(entry, 'chain_records', [])]}")
                    pass
            self.entries = entries
            # logging.info("[DEBUG][update_image_list] self.entries:")
            for e in self.entries:
                # logging.info(f"  id={id(e)} image_path={getattr(e, 'image_path', None)}")
                pass
            records = getattr(self.data_service.dictionary_manager, 'records', []) if self.data_service.dictionary_manager else []
            entry_to_category = {}
            for entry in entries:
                cat = None
                if hasattr(entry, 'chain_records') and entry.chain_records:
                    cat = getattr(entry.chain_records[0], 'photo_category', None)
                entry_to_category[entry.image_path] = cat
            all_categories = set(entry_to_category.values()) - {None}
            categories = sorted(all_categories)
            current_cat = self.category_combo.currentText() if hasattr(self, 'category_combo') else "(全て)"
            self.category_combo.blockSignals(True)
            self.category_combo.clear()
            self.category_combo.addItem("(全て)")
            for cat in categories:
                self.category_combo.addItem(cat)
            idx = self.category_combo.findText(current_cat)
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)
            self.category_combo.blockSignals(False)
            selected_cat = self.category_combo.currentText() if hasattr(self, 'category_combo') else "(全て)"
            ascending = self.order_button.isChecked() if hasattr(self, 'order_button') else True
            filtered_entries = []
            for entry in entries:
                cat = entry_to_category.get(entry.image_path)
                if selected_cat == "(全て)" or cat == selected_cat:
                    filtered_entries.append(entry)
            if selected_cat == "(全て)":
                filtered_entries.sort(key=lambda e: os.path.basename(getattr(e, 'image_path', '')), reverse=not ascending)
            else:
                def sort_key(e):
                    cat = entry_to_category.get(e.image_path)
                    basename = os.path.basename(getattr(e, 'image_path', ''))
                    return (cat or '', basename)
                filtered_entries.sort(key=sort_key, reverse=not ascending)
            self.vm.image_list_changed.emit(filtered_entries)
            # logging.info("[DEBUG][update_image_list] filtered_entries:")
            for e in filtered_entries:
                # logging.info(f"  id={id(e)} image_path={getattr(e, 'image_path', None)}")
                pass
            all_debugs = []
            for entry in self.entries:
                all_debugs.append(f"{getattr(entry, 'image_path', None)}:\n" + "\n".join(entry.debug_log or ["(empty)"]))
            if hasattr(self, 'record_panel'):
                self.record_panel.set_debug_text("\n\n".join(all_debugs))
        logging.info('[LOG] update_image_list: 終了')

    def get_remarks_and_debug(self, entry):
        """
        entryからマッチしたChainRecordリスト, location, debug_textを返す
        """
        if not entry:
            debug_lines = ["[WARN] entryがNoneまたは無効"]
            return [], "測点: 未設定", "\n".join(debug_lines)
        debug_lines = []
        # --- ChainRecordリストをImageEntryから取得 ---
        if hasattr(entry, 'chain_records'):
            matched_records = entry.chain_records
        else:
            matched_records = []
        # --- location_text決定 ---
        location_text = "測点: 未設定"
        ocr_sokuten = None
        if hasattr(entry, 'ocr_data') and entry.ocr_data and 'parsed_data' in entry.ocr_data and 'sokuten' in entry.ocr_data['parsed_data']:
            ocr_sokuten = entry.ocr_data['parsed_data']['sokuten']
        if ocr_sokuten:
            location_text = f"測点: {ocr_sokuten} (OCR)"
        elif hasattr(entry, 'location') and entry.location:
            location_text = f"測点: {entry.location}"
        # --- デバッグテキスト生成 ---
        from src.utils.image_selection_debug import generate_image_selection_debug
        debug_text = generate_image_selection_debug(entry, self.data_service, matched_records, debug_lines, role_mapping=self.role_mapping)
        return matched_records, location_text, debug_text

    def on_image_selected(self, entry):
        if not entry:
            self.vm.remarks_changed.emit([])
            if hasattr(self, 'record_panel'):
                self.record_panel.set_location("測点: 未設定")
                self.record_panel.set_debug_text("")
            return
        matched_records = entry.chain_records if hasattr(entry, 'chain_records') else []
        self.vm.remarks_changed.emit(matched_records)
        if hasattr(self, 'record_panel'):
            location = f"測点: {entry.location}" if hasattr(entry, 'location') and entry.location else "測点: 未設定"
            debug_texts = []
            if hasattr(entry, 'debug_text') and entry.debug_text:
                debug_texts.append(str(entry.debug_text))
            logging.info(f"[DEBUG][on_image_selected] entry.id = {id(entry)} entry.debug_log = {getattr(entry, 'debug_log', None)}")
            if hasattr(entry, 'debug_log') and entry.debug_log:
                debug_texts.append("\n".join([str(x) for x in entry.debug_log]))
            debug_text = "\n".join(debug_texts) if debug_texts else "デバッグ情報なし"
            logging.info(f"[DEBUG][on_image_selected] set_debug_textに渡す内容 = {debug_text}")
            self.record_panel.set_location(location)
            self.record_panel.set_debug_text(debug_text)
        logging.info(f"[LOG] record_panelへ反映: matched_records = [")
        for rec in matched_records:
            logging.info(f"  ChainRecord(remarks={getattr(rec, 'remarks', None)}, photo_category={getattr(rec, 'photo_category', None)}, work_category={getattr(rec, 'work_category', None)}, type={getattr(rec, 'type', None)}, subtype={getattr(rec, 'subtype', None)})")
        logging.info("]")
        logging.info(f"[DEBUG][record_panel] entry.id={id(entry)} chain_records={getattr(entry, 'chain_records', None)}")

    def on_image_double_clicked(self, entry):
        # ダブルクリックで画像プレビューを開く
        if not entry or not hasattr(entry, 'path'):
            return
        try:
            from src.widgets import image_preview_dialog
            import importlib
            importlib.reload(image_preview_dialog)
            dlg = image_preview_dialog.ImagePreviewDialog(entry.image_path, self)
            dlg.exec()
        except Exception as e:
            import traceback
            print(f"[ERROR] 画像プレビュー表示エラー: {e}")
            traceback.print_exc()

    def set_status_bar_message(self, message):
        if hasattr(self, "status_bar"):
            self.status_bar.showMessage(str(message))

    def export_summary(self):
        # UIクラスのexport_summaryを呼び出さず、ここでエクスポート処理を実行
        # 例: ファイルダイアログで保存先を選択し、エクスポートサービスを呼ぶ
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        out_path, _ = QFileDialog.getSaveFileName(self, "サマリーExcel出力先", "summary.xlsx", "Excel Files (*.xlsx)")
        if not out_path:
            return
        try:
            self.export_summary_to_path(out_path)
            QMessageBox.information(self, "完了", f"サマリーを出力しました: {out_path}")
        except Exception as e:
            import traceback
            QMessageBox.critical(self, "エラー", f"サマリー出力に失敗: {e}\n{traceback.format_exc()}")

    def export_summary_to_path(self, out_path):
        if not hasattr(self, "image_data_manager"):
            return
        entries = self.image_data_manager.entries
        match_results = self.data_service.get_match_results(
            entries,
            self.role_mapping,
            self.data_service.remarks_to_chain_record
        )
        selected_cat = self.category_combo.currentText() if hasattr(self, 'category_combo') else "(全て)"
        ascending = self.order_button.isChecked() if hasattr(self, 'order_button') else True
        export_summary_service(
            entries,
            match_results,
            selected_cat,
            ascending,
            self.data_service,
            self.role_mapping,
            out_path=out_path,
            parent=None,
            cache_dir=CACHE_DIR
        )
        if getattr(self, 'test_mode', False):
            self.test_finished.emit()

    def export_summary_to_path_db(self, out_path):
        """
        DBから画像リスト・ロール情報を取得しExcel出力する（E2Eテスト用）
        """
        # DBから最新の画像リストを取得
        self.image_data_manager = ImageDataManager.from_db()
        entries = self.image_data_manager.entries
        # DBからロールマッピングも取得済み（self.role_mapping）
        match_results = self.data_service.get_match_results(
            entries,
            self.role_mapping,
            self.data_service.remarks_to_chain_record
        )
        selected_cat = self.category_combo.currentText() if hasattr(self, 'category_combo') else "(全て)"
        ascending = self.order_button.isChecked() if hasattr(self, 'order_button') else True
        export_summary_service(
            entries,
            match_results,
            selected_cat,
            ascending,
            self.data_service,
            self.role_mapping,
            out_path=out_path,
            parent=None,
            cache_dir=CACHE_DIR
        )
        if getattr(self, 'test_mode', False):
            self.test_finished.emit()

    def export_excel_from_db(self):
        # UIクラスのexport_excel_from_dbを呼び出すだけに委譲
        if hasattr(self.ui, 'export_excel_from_db'):
            self.ui.export_excel_from_db()
        else:
            pass

    def open_image_list_json(self):
        # UIクラスのopen_image_list_jsonを呼び出すだけに委譲
        if hasattr(self.ui, 'open_image_list_json'):
            self.ui.open_image_list_json()
        else:
            pass

    def create_yolo_dataset(self):
        # UIクラスのcreate_yolo_datasetを呼び出すだけに委譲
        if hasattr(self.ui, 'create_yolo_dataset'):
            self.ui.create_yolo_dataset()
        else:
            pass

    def closeEvent(self, event):
        """
        アプリ終了時の処理: ログ出力のみ
        """
        logger.info('アプリ終了')
        super().closeEvent(event)

    def open_role_mapping_dialog(self):
        from src.widgets.dictionary_mapping_widget import DictionaryMappingWidget
        from PyQt6.QtWidgets import QDialog, QVBoxLayout
        dlg = QDialog(self)
        dlg.setWindowTitle("ロールマッピング編集")
        layout = QVBoxLayout(dlg)
        mapping_widget = DictionaryMappingWidget(dlg)
        layout.addWidget(mapping_widget)
        dlg.setLayout(layout)
        dlg.resize(800, 600)
        dlg.exec()

if __name__ == "__main__":
    # ログ設定: 画像ごとの詳細ログはファイルに出力
    logging.basicConfig(
        filename="./logs/summary_image_debug.log",
        filemode="w",
        format="%(asctime)s %(levelname)s %(message)s",
        level=logging.INFO
    )
    app = QApplication(sys.argv)
    w = SummaryGeneratorWidget()
    w.show()
    print("[INFO] 画像ごとの詳細ログは ./logs/summary_image_debug.log に出力されます")
    # テストモード時のみ10秒後に自動終了
    if "--test-mode" in sys.argv:
        QTimer.singleShot(10000, app.quit)
    sys.exit(app.exec())