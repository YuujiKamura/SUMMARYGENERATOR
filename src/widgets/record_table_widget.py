from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem

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
        self.setRowCount(0)
        for record in records_list:
            # recordがChainRecordなら属性参照、dictならdict参照
            if hasattr(record, 'remarks') and hasattr(record, 'photo_category'):
                rec = record
            elif isinstance(record, dict):
                rec = record
            else:
                rec = None
            row = self.rowCount()
            self.insertRow(row)
            if rec is not None:
                # ChainRecord型なら属性参照、dict型ならdict参照
                def get_val(obj, attr, default=''):
                    if hasattr(obj, attr):
                        return getattr(obj, attr)
                    elif isinstance(obj, dict):
                        return obj.get(attr, default)
                    return default
                self.setItem(row, 0, QTableWidgetItem(get_val(rec, 'photo_category')))
                self.setItem(row, 1, QTableWidgetItem(get_val(rec, 'work_category', get_val(rec, 'category'))))
                self.setItem(row, 2, QTableWidgetItem(get_val(rec, 'type')))
                self.setItem(row, 3, QTableWidgetItem(get_val(rec, 'subtype')))
                self.setItem(row, 4, QTableWidgetItem(get_val(rec, 'remarks', str(record))))
            else:
                # recがNone（不明な型）は空欄
                self.setItem(row, 0, QTableWidgetItem(''))
                self.setItem(row, 1, QTableWidgetItem(''))
                self.setItem(row, 2, QTableWidgetItem(''))
                self.setItem(row, 3, QTableWidgetItem(''))
                self.setItem(row, 4, QTableWidgetItem(str(record)))
        self.resizeColumnsToContents()
        self.setColumnWidth(4, 300)
