# --- Copied from src/components/role_tree_selector.py ---
from PyQt6.QtWidgets import QWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout
from PyQt6.QtCore import pyqtSignal, Qt
from utils.roles_utils import group_roles_by_category

class RoleTreeSelector(QWidget):
    role_selected = pyqtSignal(str)  # 選択されたロールのlabelを返す
    def __init__(self, roles, parent=None):
        super().__init__(parent)
        vbox = QVBoxLayout(self)
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        vbox.addWidget(self.tree_widget)
        self.setMinimumWidth(200)
        self.setMaximumHeight(250)
        self.set_roles(roles)
        self.tree_widget.itemClicked.connect(self._on_item_clicked)
        self.tree_widget.viewport().installEventFilter(self)
    def set_roles(self, roles):
        self.tree_widget.clear()
        cats = group_roles_by_category(roles)
        for cat, roles in sorted(cats.items()):
            cat_item = QTreeWidgetItem([cat])
            self.tree_widget.addTopLevelItem(cat_item)
            for r in roles:
                role_item = QTreeWidgetItem([r['display']])
                role_item.setData(0, Qt.ItemDataRole.UserRole, r['label'])
                cat_item.addChild(role_item)
            cat_item.setExpanded(False)
    def _on_item_clicked(self, item, col):
        if item.parent():  # ロール（子）
            role_label = item.data(0, Qt.ItemDataRole.UserRole)
            self.role_selected.emit(role_label)
    def eventFilter(self, obj, event):
        if obj is self.tree_widget.viewport() and event.type() == event.Type.MouseButtonPress:
            pos = event.pos()
            item = self.tree_widget.itemAt(pos)
            if item and not item.parent():
                # カテゴリー（親）をクリックした場合、展開/フォールドをトグル
                item.setExpanded(not item.isExpanded())
        return super().eventFilter(obj, event)
