from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem
from src.utils.chain_record_utils import ChainRecord  # 遅延インポートで循環回避

class RecordTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels([
            "写真区分", "工種", "種別", "細別", "備考（record）"
        ])
        self.resizeColumnsToContents()
        self.setColumnWidth(4, 300)

    def update_records(self, records_list):
        """ChainRecord のみを表示対象とするシンプル実装"""
        self.setRowCount(0)

        for record in records_list:
            if not isinstance(record, ChainRecord):
                # 想定外の型はスキップ
                continue

            row = self.rowCount()
            self.insertRow(row)

            self.setItem(row, 0, QTableWidgetItem(record.photo_category or ""))
            self.setItem(row, 1, QTableWidgetItem(record.work_category or ""))
            self.setItem(row, 2, QTableWidgetItem(record.type or ""))
            self.setItem(row, 3, QTableWidgetItem(record.subtype or ""))
            self.setItem(row, 4, QTableWidgetItem(record.remarks or ""))

        self.resizeColumnsToContents()
        self.setColumnWidth(4, 300)
