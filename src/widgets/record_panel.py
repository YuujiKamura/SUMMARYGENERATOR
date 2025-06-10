from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QSplitter
from PyQt6.QtCore import Qt
from .record_table_widget import RecordTableWidget

class RecordPanel(QWidget):
    """
    右側: 測点ラベル＋記録テーブル＋デバッグ欄
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # 測点ラベル（固定位置）
        self.location_label = QLabel("測点：未設定")
        self.location_label.setStyleSheet("font-weight: bold; color: #1a237e; padding: 2px 0;")
        layout.addWidget(self.location_label)
        
        # 記録エントリラベル（固定位置）
        layout.addWidget(QLabel("マッチした記録エントリー（record）"))
        
        # 縦方向のスプリッターを作成
        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Vertical)
        
        # スプリッターのスタイル設定
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #e0e0e0;
                border: none;
                height: 2px;
            }
            QSplitter::handle:hover {
                background-color: #4a90e2;
            }
            QSplitter::handle:pressed {
                background-color: #357abd;
            }
        """)
        splitter.setHandleWidth(3)
        
        # 上側：記録テーブル
        self.record_list_widget = RecordTableWidget()
        splitter.addWidget(self.record_list_widget)
        
        # 下側：デバッグテキスト
        self.debug_text = QTextEdit()
        self.debug_text.setReadOnly(True)
        splitter.addWidget(self.debug_text)
        
        # スプリッターの配分を設定（上：下 = 2：1）
        splitter.setSizes([400, 200])
        splitter.setCollapsible(0, False)  # 記録テーブルが完全に閉じられないようにする
        splitter.setCollapsible(1, False)  # デバッグパネルが完全に閉じられないようにする
        
        # レイアウトにスプリッターを追加
        layout.addWidget(splitter, 1)

    def set_location(self, text):
        self.location_label.setText(text)

    def set_debug_text(self, text):
        self.debug_text.setPlainText(text)

    def update_records(self, matched_records, remarks_to_record=None):
        # 上位3件まで表示
        top_records = matched_records[:3] if matched_records else []
        self.record_list_widget.update_records(top_records)

    def setRowCount(self, n):
        self.record_list_widget.setRowCount(n)
