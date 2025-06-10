from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton, QLineEdit, QMessageBox, QInputDialog, QMenu
from PyQt6.QtCore import Qt
import json
import os
from pathlib import Path

PRESET_ROLES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'preset_roles.json'))

class RoleEditorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ロール編集")
        self.setMinimumSize(500, 400)
        vbox = QVBoxLayout(self)
        # --- ツリーウィジェット ---
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["カテゴリー", "ロール名", "ラベル"])
        self.tree_widget.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        vbox.addWidget(self.tree_widget)
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.open_context_menu)
        # 列幅を1:1:1で均等に
        self.tree_widget.header().setSectionResizeMode(0, self.tree_widget.header().ResizeMode.Stretch)
        self.tree_widget.header().setSectionResizeMode(1, self.tree_widget.header().ResizeMode.Stretch)
        self.tree_widget.header().setSectionResizeMode(2, self.tree_widget.header().ResizeMode.Stretch)
        # --- ボタン群 ---
        btn_layout = QHBoxLayout()
        self.move_role_btn = QPushButton("選択ロールをカテゴリー変更")
        self.add_category_btn = QPushButton("カテゴリー追加")
        self.edit_category_btn = QPushButton("カテゴリー編集")
        self.del_category_btn = QPushButton("カテゴリー削除")
        self.add_role_btn = QPushButton("ロール追加")
        self.edit_role_btn = QPushButton("ロール編集")
        self.del_role_btn = QPushButton("ロール削除")
        btn_layout.addWidget(self.move_role_btn)
        btn_layout.addWidget(self.add_category_btn)
        btn_layout.addWidget(self.edit_category_btn)
        btn_layout.addWidget(self.del_category_btn)
        btn_layout.addWidget(self.add_role_btn)
        btn_layout.addWidget(self.edit_role_btn)
        btn_layout.addWidget(self.del_role_btn)
        vbox.addLayout(btn_layout)
        # OK/キャンセル
        ok_cancel = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.cancel_btn = QPushButton("キャンセル")
        ok_cancel.addWidget(self.ok_btn)
        ok_cancel.addWidget(self.cancel_btn)
        vbox.addLayout(ok_cancel)
        # --- データロード ---
        self.roles = self.load_roles()
        self.refresh_tree()
        # --- シグナル ---
        self.add_category_btn.clicked.connect(self.add_category)
        self.edit_category_btn.clicked.connect(self.edit_category)
        self.del_category_btn.clicked.connect(self.delete_category)
        self.add_role_btn.clicked.connect(self.add_role)
        self.edit_role_btn.clicked.connect(self.edit_role)
        self.del_role_btn.clicked.connect(self.delete_role)
        self.move_role_btn.clicked.connect(self.move_roles_to_category)
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
    def load_roles(self):
        if not os.path.exists(PRESET_ROLES_PATH):
            return []
        with open(PRESET_ROLES_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_roles(self):
        with open(PRESET_ROLES_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.roles, f, ensure_ascii=False, indent=4)

    def refresh_tree(self):
        # 一旦クリア
        self.tree_widget.clear()
        # カテゴリー毎にグループ化
        grouped_roles = {}
        for role in self.roles:
            cat = role.get('category', '未分類') or '未分類'
            if cat not in grouped_roles:
                grouped_roles[cat] = []
            grouped_roles[cat].append(role)
        # ツリーに反映
        for cat, roles in grouped_roles.items():
            cat_item = QTreeWidgetItem([cat])
            self.tree_widget.addTopLevelItem(cat_item)
            for role in roles:
                role_item = QTreeWidgetItem([cat, role['display'], role['label']])
                cat_item.addChild(role_item)
        # ルートのカテゴリーが無い場合は「未分類」カテゴリーを作成
        if '未分類' not in grouped_roles:
            self.tree_widget.addTopLevelItem(QTreeWidgetItem(['未分類']))

    def add_category(self):
        text, ok = QInputDialog.getText(self, "カテゴリー追加", "カテゴリー名:")
        if ok and text:
            # 既に存在するカテゴリー名かチェック
            for i in range(self.tree_widget.topLevelItemCount()):
                item = self.tree_widget.topLevelItem(i)
                if item.text(0) == text:
                    QMessageBox.warning(self, "エラー", "同名のカテゴリーが既に存在します")
                    return
            # 新規カテゴリーを追加
            self.roles.append({'category': text})
            self.refresh_tree()

    def edit_category(self):
        item = self.tree_widget.currentItem()
        if item and not item.parent():
            cat = item.text(0)
            text, ok = QInputDialog.getText(self, "カテゴリー編集", "カテゴリー名:", text=cat)
            if ok and text:
                # 既に存在するカテゴリー名かチェック
                for i in range(self.tree_widget.topLevelItemCount()):
                    other_item = self.tree_widget.topLevelItem(i)
                    if other_item != item and other_item.text(0) == text:
                        QMessageBox.warning(self, "エラー", "同名のカテゴリーが既に存在します")
                        return
                # カテゴリー名を変更
                for r in self.roles:
                    if (r.get('category', '未分類') or '未分類') == cat:
                        r['category'] = text
                item.setText(0, text)

    def delete_category(self):
        item = self.tree_widget.currentItem()
        if item and not item.parent():
            cat = item.text(0)
            for r in self.roles:
                if (r.get('category', '未分類') or '未分類') == cat:
                    r['category'] = ''
            self.refresh_tree()

    def add_role(self):
        item = self.tree_widget.currentItem()
        cat = '未分類'
        if item:
            if not item.parent():
                cat = item.text(0)
            elif item.parent():
                cat = item.parent().text(0)
        text = ""
        while True:
            text, ok = QInputDialog.getText(self, "ロール追加", "表示名:ラベル名（カンマまたはコロン区切り）", text=text)
            if not ok:
                break
            parts = self.split_role_input(text)
            if len(parts) == 2:
                display, label = parts[0], parts[1]
                self.roles.append({'display': display, 'label': label, 'category': cat})
                self.refresh_tree()
                # 追加したロールを選択状態にする
                self.select_role_in_tree(display, label, cat)
                break
            else:
                QMessageBox.warning(self, "入力エラー", "表示名,ラベル名 または 表示名:ラベル名 の形式で入力してください")

    def edit_role(self):
        item = self.tree_widget.currentItem()
        if item and item.parent():
            cat = item.parent().text(0)
            display = item.text(1)
            label = item.text(2)
            idx = next((i for i, r in enumerate(self.roles) if r['display'] == display and r['label'] == label and (r.get('category', '未分類') or '未分類') == cat), None)
            if idx is not None:
                text = f"{display},{label}"
                while True:
                    text, ok = QInputDialog.getText(self, "ロール編集", "表示名:ラベル名（カンマまたはコロン区切り）", text=text)
                    if not ok:
                        break
                    parts = self.split_role_input(text)
                    if len(parts) == 2:
                        display, label = parts[0], parts[1]
                        self.roles[idx]['display'] = display
                        self.roles[idx]['label'] = label
                        self.refresh_tree()
                        break
                    else:
                        QMessageBox.warning(self, "入力エラー", "表示名,ラベル名 または 表示名:ラベル名 の形式で入力してください")

    def delete_role(self):
        item = self.tree_widget.currentItem()
        if item and item.parent():
            cat = item.parent().text(0)
            display = item.text(1)
            label = item.text(2)
            self.roles = [r for r in self.roles if not (r['display'] == display and r['label'] == label and (r.get('category', '未分類') or '未分類') == cat)]
            self.refresh_tree()

    def move_roles_to_category(self):
        items = self.tree_widget.selectedItems()
        if not items:
            return
        cats = set()
        roles = []
        for item in items:
            if not item.parent():
                cats.add(item.text(0))
            elif item.parent():
                roles.append(item)
        if not roles:
            return
        # 既存カテゴリー一覧＋新規カテゴリー
        existing_cats = sorted(set(r.get('category', '未分類') or '未分類' for r in self.roles))
        cat_choices = [c for c in existing_cats if c != '未分類'] + ["新規カテゴリー"]
        cat, ok = QInputDialog.getItem(self, "カテゴリー変更", "移動先カテゴリーを選択:", cat_choices, 0, False)
        if not ok:
            return
        if cat == "新規カテゴリー":
            cat, ok = QInputDialog.getText(self, "新規カテゴリー", "新しいカテゴリー名を入力:")
            if not ok or not cat:
                return
        for item in roles:
            display = item.text(1)
            label = item.text(2)
            for r in self.roles:
                if r['display'] == display and r['label'] == label:
                    r['category'] = cat
        self.refresh_tree()

    def split_role_input(self, text):
        if ',' in text and ':' in text:
            idx_comma = text.find(',')
            idx_colon = text.find(':')
            if idx_comma < idx_colon:
                parts = text.split(',', 1)
            else:
                parts = text.split(':', 1)
        elif ',' in text:
            parts = text.split(',', 1)
        elif ':' in text:
            parts = text.split(':', 1)
        else:
            parts = [text]
        return [p.strip() for p in parts]

    def select_role_in_tree(self, display, label, cat):
        # ツリー内でdisplay, label, cat一致のロールを選択
        root_count = self.tree_widget.topLevelItemCount()
        for i in range(root_count):
            cat_item = self.tree_widget.topLevelItem(i)
            if cat_item.text(0) == cat:
                for j in range(cat_item.childCount()):
                    role_item = cat_item.child(j)
                    if role_item.text(1) == display and role_item.text(2) == label:
                        self.tree_widget.setCurrentItem(role_item)
                        return

    def open_context_menu(self, pos):
        item = self.tree_widget.itemAt(pos)
        menu = QMenu(self)
        if item:
            if not item.parent():  # カテゴリー
                menu.addAction("カテゴリー作成", self.add_category)
                menu.addAction("カテゴリー編集", self.edit_category)
                menu.addAction("カテゴリー削除", self.delete_category)
                menu.addSeparator()
                menu.addAction("ロール作成", self.add_role)
            else:  # ロール
                menu.addAction("ロール作成", self.add_role)
                menu.addAction("ロール編集", self.edit_role)
                menu.addAction("ロール削除", self.delete_role)
        else:
            menu.addAction("カテゴリー作成", self.add_category)
            menu.addAction("ロール作成", self.add_role)
        menu.exec(self.tree_widget.viewport().mapToGlobal(pos))

    def accept(self):
        self.save_roles()
        super().accept()
