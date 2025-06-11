from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QListWidget, QListWidgetItem

class DictionaryMappingTableWidget(QWidget):
    def __init__(self, records, role_names, mapping=None, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.table = QTableWidget(len(records), 6)
        self.table.setHorizontalHeaderLabels([
            "写真区分", "工種", "種別", "細別", "備考（remarks）", "ロール割当（複数可）"
        ])
        self.records = records
        self.role_names = role_names
        self.mapping = mapping or {}
        for i, record in enumerate(records):
            self.table.setItem(i, 0, QTableWidgetItem(record.get('photo_category', '')))
            self.table.setItem(i, 1, QTableWidgetItem(record.get('work_category', '') or record.get('category', '')))
            self.table.setItem(i, 2, QTableWidgetItem(record.get('type', '')))
            self.table.setItem(i, 3, QTableWidgetItem(record.get('subtype', '')))
            self.table.setItem(i, 4, QTableWidgetItem(record.get('remarks', '')))
            list_widget = QListWidget()
            list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
            for role in role_names:
                item = QListWidgetItem(role)
                list_widget.addItem(item)
            # 既存マッピングがあれば選択
            key = record.get('remarks', '')
            assigned = self.mapping.get(key, [])
            if isinstance(assigned, str):
                assigned = [assigned]
            for j in range(list_widget.count()):
                if list_widget.item(j).text() in assigned:
                    list_widget.item(j).setSelected(True)
            self.table.setCellWidget(i, 5, list_widget)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

    def get_mapping(self):
        mapping = {}
        for i, record in enumerate(self.records):
            key = record.get('remarks', '')
            list_widget = self.table.cellWidget(i, 5)
            selected_roles = [list_widget.item(j).text() for j in range(list_widget.count()) if list_widget.item(j).isSelected()]
            if selected_roles:
                mapping[key] = selected_roles
        return mapping