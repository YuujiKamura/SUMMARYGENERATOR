import os
import json
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QPushButton, QHBoxLayout, QListWidgetItem, QMenu, QWidgetAction
from PyQt6.QtCore import Qt

ROLES_PATH = os.path.join(os.path.dirname(__file__), 'preset_roles.json')

def select_role(parent=None, multi=False, preselect_labels=None):
    """
    ロール選択ダイアログを表示し、選択されたロールlabelリストを返す。
    multi=Trueで複数選択、Falseで単一選択。
    preselect_labels: 事前選択するlabelリスト（任意）
    キャンセル時はNoneを返す。
    """
    with open(ROLES_PATH, encoding='utf-8') as f:
        roles = json.load(f)
    dlg = QDialog(parent)
    dlg.setWindowTitle("ロールを選択")
    vbox = QVBoxLayout(dlg)
    listw = QListWidget()
    if multi:
        listw.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
    else:
        listw.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
    for role in roles:
        item = QListWidgetItem(role['display'])
        item.setData(Qt.ItemDataRole.UserRole, role['label'])
        listw.addItem(item)
    # 事前選択
    if preselect_labels:
        for i in range(listw.count()):
            if listw.item(i).data(Qt.ItemDataRole.UserRole) in preselect_labels:
                listw.item(i).setSelected(True)
    vbox.addWidget(listw)
    btn_hbox = QHBoxLayout()
    ok_btn = QPushButton("OK")
    cancel_btn = QPushButton("キャンセル")
    btn_hbox.addWidget(ok_btn)
    btn_hbox.addWidget(cancel_btn)
    vbox.addLayout(btn_hbox)
    ok_btn.clicked.connect(dlg.accept)
    cancel_btn.clicked.connect(dlg.reject)
    result = dlg.exec()
    if result == QDialog.DialogCode.Accepted:
        if multi:
            selected = [listw.item(i).data(Qt.ItemDataRole.UserRole) for i in range(listw.count()) if listw.item(i).isSelected()]
        else:
            sel = listw.currentItem()
            selected = [sel.data(Qt.ItemDataRole.UserRole)] if sel else []
        return selected
    return None

def select_role_menu(parent, roles, on_role_selected, on_edit_roles=None, pos=None):
    """
    右クリックメニュー用: rolesリストから選択肢をQMenu+QListWidgetで表示し、
    項目クリックでon_role_selected(label)を即時呼ぶ。ロール編集項目も追加。
    on_edit_roles: ロール編集が選択されたとき呼ばれるコールバック（省略可）
    pos: メニュー表示位置（QPoint, 省略時はparentのmapToGlobal(0,0)）
    """
    menu = QMenu(parent)
    list_widget = QListWidget()
    for role in roles:
        item = QListWidgetItem(role['display'])
        item.setData(Qt.ItemDataRole.UserRole, role['label'])
        list_widget.addItem(item)
    list_widget.setMinimumWidth(200)
    list_widget.setMaximumHeight(200)
    action = QWidgetAction(menu)
    action.setDefaultWidget(list_widget)
    menu.addAction(action)
    menu.addSeparator()
    edit_action = menu.addAction("ロール編集...")
    def on_item_clicked(item):
        label = item.data(Qt.ItemDataRole.UserRole)
        menu.close()
        if on_role_selected:
            on_role_selected(label)
    list_widget.itemClicked.connect(on_item_clicked)
    selected_action = menu.exec(pos or parent.mapToGlobal(parent.rect().center()))
    if selected_action == edit_action and on_edit_roles:
        on_edit_roles() 