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
        
        # デバッグテキストパネルは不要になったため削除
        # splitter には RecordTableWidget のみ配置
        splitter.setSizes([600])
        splitter.setCollapsible(0, False)
        
        # レイアウトにスプリッターを追加
        layout.addWidget(splitter, 1)

    def set_location(self, text):
        self.location_label.setText(text)

    # デバッグテキスト機能は削除
    def set_debug_text(self, text):
        pass

    def update_records(self, matched_records, remarks_to_record=None):
        # 全件表示に修正
        self.record_list_widget.update_records(matched_records if matched_records else [])

    def setRowCount(self, n):
        self.record_list_widget.setRowCount(n)
