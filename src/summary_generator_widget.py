import os
import sys
import json
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
from src.utils.project_menu_actions import add_project_menu_actions
from src.utils.context_menu_utils import handle_image_list_context_menu
from src.dictionary_manager import DictionaryManager
from src.utils.chain_record_utils import find_chain_records_by_roles
from src.utils.image_selection_debug import generate_image_selection_debug
from src.utils.summary_generator import load_role_mapping
from src.utils.record_matching_utils import match_roles_records_one_stop
from dataclasses import dataclass, field
from typing import List, Optional
from src.utils.image_entry import ImageEntry
from src.utils.image_data_manager import ImageDataManager
from src.db_manager import RoleMappingManager

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

class SummaryGeneratorViewModel(QObject):
    image_list_changed = pyqtSignal(list)
    remarks_changed = pyqtSignal(list)  # ChainRecordのリストをemitする
    status_changed = pyqtSignal(str)

    def __init__(self, data_service=None):
        super().__init__()
        self.data_service = data_service
        self.images = []
        self.remarks = []  # ChainRecordのリストで統一
        self.status = ""

    def load_images(self, folder):
        # data_serviceから画像リスト取得
        if self.data_service:
            images = self.data_service.get_image_list(folder)
            self.images = images
        else:
            self.images = []
        self.image_list_changed.emit(self.images)

    def select_image(self, img_path):
        # data_serviceからImageEntryを取得し、chain_recordsをremarksにセット
        if self.data_service:
            entry = self.data_service.get_image_entry_for_image(img_path)
            if entry and hasattr(entry, 'chain_records'):
                self.remarks = entry.chain_records
            else:
                self.remarks = []
        else:
            self.remarks = []
        self.remarks_changed.emit(self.remarks)

    def set_status(self, msg):
        self.status = msg
        self.status_changed.emit(msg)

class SummaryGeneratorWidget(QMainWindow):
    """
    サマリー生成メインウィジェット
    """
    test_finished = pyqtSignal()
    def __init__(self, parent=None, test_mode=False):
        super().__init__(parent)
        self.dictionary_manager = DictionaryManager(RECORDS_PATH)
        # --- DBからロールマッピングをロードし保持 ---
        db_role_mappings = RoleMappingManager.get_all_role_mappings()
        self.role_mapping = {row['role_name']: json.loads(row['mapping_json']) for row in db_role_mappings}
        print(f"[DEBUG] role_mapping loaded from DB at init: keys={list(self.role_mapping.keys()) if self.role_mapping else 'EMPTY'}")
        self.data_service = SummaryDataService(self.dictionary_manager, CACHE_DIR, RECORDS_PATH, role_mapping=self.role_mapping)
        # 画像リストもDBから取得
        self.image_data_manager = ImageDataManager.from_db()
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

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, '_first_show', True):
            self._first_show = False
            print('[LOG] showEvent: 初回表示で画像リスト自動ロード')
            self.load_image_list_from_path_manager()

    def setup_ui(self):
        self.setWindowTitle("Summary Generator Widget")
        self.resize(1000, 700)
        self.menubar = QMenuBar(self)
        file_menu = QMenu("ファイル", self)
        # 画像リストJSONを開くアクション追加
        act_open_json = QAction("画像リストJSONを開く", self)
        act_open_json.triggered.connect(self.open_image_list_json)
        file_menu.addAction(act_open_json)
        # Excel出力アクション追加
        act_export_excel = QAction("Excelフォトブック出力", self)
        act_export_excel.triggered.connect(self.export_summary)
        file_menu.addAction(act_export_excel)
        
        # YOLO Dataset作成アクション追加
        act_create_yolo_dataset = QAction("YOLO学習用DataSet作成", self)
        act_create_yolo_dataset.triggered.connect(self.create_yolo_dataset)
        file_menu.addAction(act_create_yolo_dataset)
        
        self.menubar.addMenu(file_menu)
        edit_menu = QMenu("編集", self)
        # ロールマッピング編集アクション追加
        act_edit_role_mapping = QAction("ロールマッピング編集", self)
        def open_role_mapping_dialog():
            from src.dictionary_mapping_widget import DictionaryMappingWidget
            from PyQt6.QtWidgets import QDialog
            dlg = QDialog(self)
            dlg.setWindowTitle("ロールマッピング編集")
            layout = QVBoxLayout(dlg)
            mapping_widget = DictionaryMappingWidget(dlg)
            layout.addWidget(mapping_widget)
            dlg.setLayout(layout)
            dlg.resize(800, 600)
            dlg.exec()
        act_edit_role_mapping.triggered.connect(open_role_mapping_dialog)
        edit_menu.addAction(act_edit_role_mapping)
        self.menubar.addMenu(edit_menu)
        help_menu = QMenu("ヘルプ", self)
        self.menubar.addMenu(help_menu)
        self.setMenuBar(self.menubar)
        add_project_menu_actions(self)
        central_widget = QWidget(self)
        # QSplitterを導入
        main_splitter = QSplitter()
        main_splitter.setOrientation(Qt.Orientation.Horizontal)
        
        # スプリッターハンドルを見やすくするスタイル設定
        main_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #e0e0e0;
                border: none;
                width: 2px;
            }
            QSplitter::handle:hover {
                background-color: #4a90e2;
            }
            QSplitter::handle:pressed {
                background-color: #357abd;
            }
        """)
        
        # ハンドル幅を設定
        main_splitter.setHandleWidth(3)
        vbox = QVBoxLayout(central_widget)
        vbox.addWidget(main_splitter, 1)
        self.json_path_edit = QLineEdit(path_manager.current_image_list_json)
        self.json_path_edit.textChanged.connect(self.on_json_path_changed)
        self.folder_path_edit = QLineEdit(str(path_manager.src_dir / "image_preview_cache"))
        left_vbox = QVBoxLayout()
        sort_hbox = QHBoxLayout()
        self.category_combo = QComboBox()
        self.category_combo.addItem("(全て)")
        sort_hbox.addWidget(QLabel("写真区分フィルタ:"))
        sort_hbox.addWidget(self.category_combo)
        self.order_button = QToolButton()
        self.order_button.setText("古い写真が上")
        self.order_button.setCheckable(True)
        self.order_button.setChecked(True)
        sort_hbox.addWidget(self.order_button)
        sort_hbox.addStretch()
        left_vbox.addLayout(sort_hbox)
        self.image_list_panel = ImageListPanel()
        # 右クリックメニューのハンドラを接続
        self.image_list_panel.set_context_menu_handler(
            lambda panel, items, pos: handle_image_list_context_menu(
                self, panel, items, pos, self.folder_path_edit, self.set_status_bar_message, None, getattr(self, 'image_data_manager', None)
            )
        )
        left_vbox.addWidget(self.image_list_panel, 1)
        left_widget = QWidget()
        left_widget.setLayout(left_vbox)
        
        # 右側パネルは単純にRecordPanelのみ
        self.record_panel = RecordPanel()
        
        # メインスプリッターに左右ウィジェットを追加
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(self.record_panel)
        
        # パネル配分を1:2に設定し、境界をドラッグ可能にする
        main_splitter.setSizes([333, 667])  # 左1: 右2の比率で設定
        main_splitter.setCollapsible(0, False)  # 左パネルが完全に閉じられないようにする
        main_splitter.setCollapsible(1, False)  # 右パネルが完全に閉じられないようにする
        
        self.status_bar = QStatusBar(self)
        vbox.addWidget(self.status_bar)
        self.setCentralWidget(central_widget)
        self.setMenuBar(self.menubar)
        # --- イベントハンドラ追加 ---
        self.category_combo.currentIndexChanged.connect(self.on_category_changed)
        self.order_button.clicked.connect(self.on_order_button_clicked)

    def on_json_path_changed(self, path):
        path_manager.current_image_list_json = path
        print(f'[LOG] 画像リストパス変更: {path}')
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
        print('[LOG] update_image_list: 開始')
        if hasattr(self, "image_data_manager"):
            entries = self.image_data_manager.entries
            # ここでset_all_entriesを呼ぶ
            self.data_service.set_all_entries(entries)
            for entry in entries:
                if hasattr(entry, 'chain_records'):
                    print(f"[DEBUG][Widget] image_path={getattr(entry, 'image_path', None)}, chain_records={[{'remarks': getattr(r, 'remarks', None), 'photo_category': getattr(r, 'photo_category', None)} for r in getattr(entry, 'chain_records', [])]}")
            self.entries = entries
            print("[DEBUG][update_image_list] self.entries:")
            for e in self.entries:
                print(f"  id={id(e)} image_path={getattr(e, 'image_path', None)}")
            # --- 1. チェーンレコード（分類辞書）を先にロード ---
            records = getattr(self.data_service.dictionary_manager, 'records', [])
            # --- 2. 画像ごとにphoto_categoryを決定 ---
            entry_to_category = {}
            for entry in entries:
                # chain_recordsの先頭からphoto_categoryを取得
                cat = None
                if hasattr(entry, 'chain_records') and entry.chain_records:
                    cat = getattr(entry.chain_records[0], 'photo_category', None)
                entry_to_category[entry.image_path] = cat
            # --- 3. カテゴリ一覧を生成 ---
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
            # --- 4. カテゴリでフィルタ・ソート ---
            filtered_entries = []
            for entry in entries:
                cat = entry_to_category.get(entry.image_path)
                if selected_cat == "(全て)" or cat == selected_cat:
                    filtered_entries.append(entry)
            if selected_cat == "(全て)":
                # 全件表示時はファイル名（basename）で時系列ソート
                filtered_entries.sort(key=lambda e: os.path.basename(getattr(e, 'image_path', '')), reverse=not ascending)
            else:
                # カテゴリ選択時はphoto_category＋basenameでソート
                def sort_key(e):
                    cat = entry_to_category.get(e.image_path)
                    basename = os.path.basename(getattr(e, 'image_path', ''))
                    return (cat or '', basename)
                filtered_entries.sort(key=sort_key, reverse=not ascending)
            self.vm.image_list_changed.emit(filtered_entries)
            print("[DEBUG][update_image_list] filtered_entries:")
            for e in filtered_entries:
                print(f"  id={id(e)} image_path={getattr(e, 'image_path', None)}")
            # --- 追加: 全ImageEntryのdebug_logをデバッグパネルに表示 ---
            all_debugs = []
            for entry in self.entries:
                all_debugs.append(f"{getattr(entry, 'image_path', None)}:\n" + "\n".join(entry.debug_log or ["(empty)"]))
            if hasattr(self, 'record_panel'):
                self.record_panel.set_debug_text("\n\n".join(all_debugs))
        print('[LOG] update_image_list: 終了')

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
        # 画像エントリ選択時の詳細取得・ChainRecordマッチング・パネル更新
        if not entry:
            self.vm.remarks_changed.emit([])
            if hasattr(self, 'record_panel'):
                self.record_panel.set_location("測点: 未設定")
                self.record_panel.set_debug_text("")
            return
        # entryはImageEntry想定
        matched_records = entry.chain_records if hasattr(entry, 'chain_records') else []
        self.vm.remarks_changed.emit(matched_records)
        if hasattr(self, 'record_panel'):
            location = f"測点: {entry.location}" if hasattr(entry, 'location') and entry.location else "測点: 未設定"
            debug_texts = []
            if hasattr(entry, 'debug_text') and entry.debug_text:
                debug_texts.append(str(entry.debug_text))
            # debug_logの内容とidをprintで確認
            print(f"[DEBUG][on_image_selected] entry.id = {id(entry)} entry.debug_log = {getattr(entry, 'debug_log', None)}")
            if hasattr(entry, 'debug_log') and entry.debug_log:
                debug_texts.append("\n".join([str(x) for x in entry.debug_log]))
            debug_text = "\n".join(debug_texts) if debug_texts else "デバッグ情報なし"
            print(f"[DEBUG][on_image_selected] set_debug_textに渡す内容 = {debug_text}")
            self.record_panel.set_location(location)
            self.record_panel.set_debug_text(debug_text)
        # レコード単位でのデバッグ出力
        print(f"[LOG] record_panelへ反映: matched_records = [")
        for rec in matched_records:
            print(f"  ChainRecord(remarks={getattr(rec, 'remarks', None)}, photo_category={getattr(rec, 'photo_category', None)}, work_category={getattr(rec, 'work_category', None)}, type={getattr(rec, 'type', None)}, subtype={getattr(rec, 'subtype', None)})")
        print("]")
        print(f"[DEBUG][record_panel] entry.id={id(entry)} chain_records={getattr(entry, 'chain_records', None)}")

    def on_image_double_clicked(self, entry):
        # ダブルクリックで画像プレビューを開く
        if not entry or not hasattr(entry, 'path'):
            return
        try:
            from src import image_preview_dialog
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
        sorted_entries, _ = self.data_service.get_sorted_entries(entries, match_results, selected_cat, ascending)
        # カテゴリでフィルタ
        filtered_match_results = {}
        for entry in sorted_entries:
            path = entry.image_path
            if path in match_results:
                filtered_match_results[path] = match_results[path]
        # ファイル保存ダイアログ
        out_path, _ = QFileDialog.getSaveFileName(self, "Excelフォトブックの保存先を指定", "photobook.xlsx", "Excel Files (*.xlsx)")
        if not out_path:
            return  # キャンセル時は何もしない
        from src.excel_photobook_exporter import export_excel_photobook
        export_excel_photobook(
            filtered_match_results,
            {},  # image_roles（必要なら用意）
            self.data_service.dictionary_manager.records,
            out_path,
            cache_dir=CACHE_DIR
        )

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
        sorted_entries, _ = self.data_service.get_sorted_entries(entries, match_results, selected_cat, ascending)
        filtered_match_results = {}
        for entry in sorted_entries:
            path = entry.image_path
            if path in match_results:
                filtered_match_results[path] = match_results[path]
        from src.excel_photobook_exporter import export_excel_photobook
        export_excel_photobook(
            filtered_match_results,
            {},  # image_roles（必要なら用意）
            self.data_service.dictionary_manager.records,
            out_path,
            cache_dir=CACHE_DIR
        )
        if getattr(self, 'test_mode', False):
            self.test_finished.emit()

    def open_image_list_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "画像リストJSONを開く", "", "JSON Files (*.json)")
        if not path:
            return
        path_manager.current_image_list_json = path
        self.json_path_edit.setText(path)
        self.load_image_list_from_path_manager()

    def create_yolo_dataset(self):
        """YOLO学習用DataSet作成 - 処理は別モジュールに委譲"""
        from src.utils.yolo_dataset_actions import create_yolo_dataset_from_pathmanager_action
        
        try:
            # 専用モジュールに処理を委譲（タイムアウト設定付き）
            result = create_yolo_dataset_from_pathmanager_action(
                parent_widget=self,
                path_manager=path_manager,
                status_callback=self.set_status_bar_message,
                timeout_seconds=600  # 10分でタイムアウト
            )
            
            if result:
                self.set_status_bar_message("YOLO DataSet作成が正常に完了しました")
            else:
                self.set_status_bar_message("YOLO DataSet作成がキャンセルされました")
                
        except Exception as e:
            error_msg = f"YOLO DataSet作成でエラーが発生しました: {str(e)}"
            self.set_status_bar_message(error_msg)
            print(f"[ERROR] {error_msg}")
            import traceback
            traceback.print_exc()

    def closeEvent(self, event):
        """
        アプリ終了時の処理: ログ出力のみ
        """
        import datetime
        # ログ出力
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, 'summary_generator_app.log')
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(f"[{datetime.datetime.now()}] アプリ終了\n")
        super().closeEvent(event) 