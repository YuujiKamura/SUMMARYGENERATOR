from PyQt6.QtWidgets import QMenuBar, QMenu, QVBoxLayout, QHBoxLayout, QSplitter, QWidget, QComboBox, QToolButton, QLabel, QLineEdit, QStatusBar
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt
from src.utils.context_menu_utils import handle_image_list_context_menu
from src.widgets.record_panel import RecordPanel
from src.widgets.image_list_panel import ImageListPanel
from src.components.edit_menu import create_edit_menu

class SummaryGeneratorUI:
    def __init__(self, parent, path_manager, set_status_bar_message):
        self.parent = parent
        self.path_manager = path_manager
        self.central_widget = QWidget(parent)
        self.menubar = QMenuBar(parent)
        file_menu = QMenu("ファイル", parent)
        # 画像リストJSONを開く
        act_open_json = QAction("画像リストJSONを開く", parent)
        act_open_json.triggered.connect(parent.open_image_list_json)
        file_menu.addAction(act_open_json)
        # DB画像リストからExcelエクスポート
        act_export_excel = QAction("DB画像リストからExcelエクスポート", parent)
        act_export_excel.triggered.connect(parent.export_summary)
        file_menu.addAction(act_export_excel)
        # YOLO学習一括実行
        act_yolo = QAction("YOLO学習一括実行", parent)
        def run_yolo_workflow():
            import subprocess, sys, os
            script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'run_create_yolo_dataset_from_json.py'))
            try:
                subprocess.Popen([sys.executable, script_path], shell=False)
            except Exception as e:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(parent, "エラー", f"YOLO学習一括実行の起動に失敗: {e}")
        act_yolo.triggered.connect(run_yolo_workflow)
        file_menu.addAction(act_yolo)
        self.menubar.addMenu(file_menu)
        # 編集メニューは部品モジュールから生成
        edit_menu = create_edit_menu(parent, getattr(parent, 'dictionary_manager', None))
        self.menubar.addMenu(edit_menu)
        help_menu = QMenu("ヘルプ", parent)
        self.menubar.addMenu(help_menu)
        main_splitter = QSplitter()
        main_splitter.setOrientation(Qt.Orientation.Horizontal)
        main_splitter.setStyleSheet("""
            QSplitter::handle { background-color: #e0e0e0; border: none; width: 2px; }
            QSplitter::handle:hover { background-color: #4a90e2; }
            QSplitter::handle:pressed { background-color: #357abd; }
        """)
        main_splitter.setHandleWidth(3)
        vbox = QVBoxLayout(self.central_widget)
        vbox.addWidget(main_splitter, 1)
        self.json_path_edit = QLineEdit(path_manager.current_image_list_json)
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
        self.image_list_panel.set_context_menu_handler(
            lambda panel, items, pos: handle_image_list_context_menu(
                parent, panel, items, pos, self.folder_path_edit, set_status_bar_message, None, getattr(parent, 'image_data_manager', None)
            )
        )
        left_vbox.addWidget(self.image_list_panel, 1)
        left_widget = QWidget()
        left_widget.setLayout(left_vbox)
        self.record_panel = RecordPanel()
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(self.record_panel)
        main_splitter.setSizes([333, 667])
        main_splitter.setCollapsible(0, False)
        main_splitter.setCollapsible(1, False)
        self.status_bar = QStatusBar(parent)
        vbox.addWidget(self.status_bar)
        self.central_widget.setLayout(vbox)
        self.parent.setCentralWidget(self.central_widget)
        self.parent.setMenuBar(self.menubar)
        self.category_combo.currentIndexChanged.connect(parent.on_category_changed)
        self.order_button.clicked.connect(parent.on_order_button_clicked)

    def export_summary(self):
        if hasattr(self.parent, 'export_summary'):
            self.parent.export_summary()

    def export_excel_from_db(self):
        if hasattr(self.parent, 'export_excel_from_db'):
            self.parent.export_excel_from_db()

    def open_image_list_json(self):
        if hasattr(self.parent, 'open_image_list_json'):
            self.parent.open_image_list_json()

    def create_yolo_dataset(self):
        if hasattr(self.parent, 'create_yolo_dataset'):
            self.parent.create_yolo_dataset()
