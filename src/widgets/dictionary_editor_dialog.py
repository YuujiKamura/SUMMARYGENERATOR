#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ユーザー辞書のリスト（テーブル）編集ダイアログ（工種→種別→細別→備考）
"""

import sys
import os
import shutil
import datetime
import json
import glob
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QWidget, QMessageBox, QApplication, QSplitter, QFileDialog, QTableWidget, QTableWidgetItem, QComboBox, QMenu, QInputDialog
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem

# 依存: DictionaryManager
from ..dictionary_manager import DictionaryManager
from ..utils.records_loader import load_records_from_json, save_records_to_json

PHOTO_CATEGORY_DEFAULTS = [
    "着手前及び完成写真（既済部分写真等含む）",
    "施工状況写真",
    "安全管理写真",
    "使用材料写真",
    "品質管理写真",
    "出来形管理写真",
    "災害写真",
    "事故写真",
    "その他（公害、環境、補償等）"
]

LAST_PATH_FILE = os.path.join(os.path.dirname(__file__), '../../.userdict_lastpath.json')

def rotate_backups(base_path, max_backup=20):
    # 古いものから順にリネーム
    for i in range(max_backup, 0, -1):
        bak_path = f"{base_path}.{i}.bak"
        if os.path.exists(bak_path):
            if i == max_backup:
                os.remove(bak_path)
            else:
                os.rename(bak_path, f"{base_path}.{i+1}.bak")
    # 最新を .1.bak に
    if os.path.exists(base_path):
        shutil.copy2(base_path, f"{base_path}.1.bak")

class DictionaryListEditorDialog(QDialog):
    """
    工種→種別→細別→備考 のリスト（テーブル）編集ダイアログ
    ユーザー辞書ファイルの切り替え・保存時バックアップ機能付き
    """
    def __init__(self, dictionary_manager: DictionaryManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ユーザー辞書リストエディタ")
        self.resize(1200, 700)
        self.dictionary_manager = dictionary_manager
        # ここで前回ファイルを自動ロード
        self._auto_load_last_json()
        self.current_dict_path = self.dictionary_manager._get_records_file()
        self._setup_ui()
        print(f"[LOG] 起動直後 records: {repr(self.dictionary_manager.records)}")
        self._load_table_from_records()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        # --- ファイル選択UI ---
        file_hbox = QHBoxLayout()
        self.file_label = QLabel("ユーザー辞書ファイル:")
        file_hbox.addWidget(self.file_label)
        self.file_path_edit = QLineEdit(self.current_dict_path)
        self.file_path_edit.setReadOnly(True)
        file_hbox.addWidget(self.file_path_edit, 1)
        self.file_btn = QPushButton("ファイル選択")
        self.file_btn.clicked.connect(self._on_select_file)
        file_hbox.addWidget(self.file_btn)
        layout.addLayout(file_hbox)
        # --- メインUI ---
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["写真区分", "工種", "種別", "細別", "備考"])
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(self.table.EditTrigger.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_table_context_menu)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.viewport().installEventFilter(self)
        layout.addWidget(self.table)
        self.setLayout(layout)
        self.selected_rows_pool = set()

    def _load_table_from_records(self):
        self.table.setRowCount(0)
        # 写真区分リストの更新
        self.photo_categories = set(PHOTO_CATEGORY_DEFAULTS)
        records = []
        # 共通ローダーで全レコード取得
        try:
            records = load_records_from_json(self.current_dict_path)
        except Exception as e:
            print(f"[LOG] レコード読込エラー: {e}")
        for rec in records:
            # work_categoryがなければcategoryやkou_shuから補完
            if 'work_category' not in rec:
                if 'kou_shu' in rec:
                    rec['work_category'] = rec['kou_shu']
                elif 'category' in rec:
                    rec['work_category'] = rec['category']
            row = self.table.rowCount()
            self.table.insertRow(row)
            photo_cat = getattr(rec, 'photo_category', '') if hasattr(rec, 'photo_category') else rec.get('photo_category', '') if isinstance(rec, dict) else ''
            self.table.setItem(row, 0, QTableWidgetItem(photo_cat))
            self.table.setItem(row, 1, QTableWidgetItem(getattr(rec, 'work_category', '') if hasattr(rec, 'work_category') else rec.get('work_category', '') if isinstance(rec, dict) else ''))
            self.table.setItem(row, 2, QTableWidgetItem(getattr(rec, 'type', '') if hasattr(rec, 'type') else rec.get('type', '') if isinstance(rec, dict) else ''))
            self.table.setItem(row, 3, QTableWidgetItem(getattr(rec, 'subtype', '') if hasattr(rec, 'subtype') else rec.get('subtype', '') if isinstance(rec, dict) else ''))
            self.table.setItem(row, 4, QTableWidgetItem(getattr(rec, 'remarks', '') if hasattr(rec, 'remarks') else rec.get('remarks', '') if isinstance(rec, dict) else ''))
        self.table.resizeColumnsToContents()

    def _on_selection_changed(self):
        # 選択行をプール
        selected = self.table.selectionModel().selectedRows()
        self.selected_rows_pool = set(idx.row() for idx in selected)
        print(f"[LOG] selection changed, pool={self.selected_rows_pool}")

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if obj == self.table.viewport():
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                print("[LOG] フォーカス外れたのでpoolクリア")
                self.selected_rows_pool.clear()
        return super().eventFilter(obj, event)

    def _on_table_context_menu(self, pos):
        menu = QMenu(self)
        index = self.table.indexAt(pos)
        row, col = index.row(), index.column()
        action_map = {}
        if row >= 0 and col >= 0:
            # セル右クリック: 既存値リストを表示
            unique_values = set()
            for r in range(self.table.rowCount()):
                item = self.table.item(r, col)
                if item and item.text():
                    unique_values.add(item.text())
            if col == 0:
                unique_values.update(PHOTO_CATEGORY_DEFAULTS)
            value_list = sorted(unique_values, key=lambda x: (PHOTO_CATEGORY_DEFAULTS.index(x) if col == 0 and x in PHOTO_CATEGORY_DEFAULTS else 999, x))
            for val in value_list:
                act = menu.addAction(val)
                act.setData(val)
                act.setProperty("bulk_assign", True)
                action_map[act] = val
            menu.addSeparator()
        assign_col = None
        if self.selected_rows_pool and col >= 0:
            assign_col = menu.addAction(f"選択行のこの列（{self.table.horizontalHeaderItem(col).text()}）を一括アサイン")
            assign_col.setData("__BULK_ASSIGN__")
        add_row = menu.addAction("行追加")
        del_row = menu.addAction("行削除")
        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action:
            if action == add_row:
                self._on_add_row()
                self._auto_save_json()
            elif action == del_row:
                self._on_delete_row()
                self._auto_save_json()
            elif action.property("bulk_assign"):
                val = action.data()
                print(f"[LOG] 一括アサイン: col={col}, val={val}, pool={self.selected_rows_pool}")
                for r in self.selected_rows_pool:
                    print(f"[LOG] setItem row={r}, col={col}, val={val}")
                    self.table.setItem(r, col, QTableWidgetItem(val))
                self.table.viewport().update()
                self._auto_save_json()
            elif action.data() is not None:
                if col == 0 and self.selected_rows_pool:
                    for r in self.selected_rows_pool:
                        self.table.setItem(r, 0, QTableWidgetItem(action.data()))
                else:
                    self.table.setItem(row, col, QTableWidgetItem(action.data()))
                self._auto_save_json()

    def _on_cell_double_clicked(self, row, col):
        # 既存値リストを作成
        unique_values = set()
        for r in range(self.table.rowCount()):
            item = self.table.item(r, col)
            if item and item.text():
                unique_values.add(item.text())
        if col == 0:
            unique_values.update(PHOTO_CATEGORY_DEFAULTS)
        value_list = sorted(unique_values, key=lambda x: (PHOTO_CATEGORY_DEFAULTS.index(x) if col == 0 and x in PHOTO_CATEGORY_DEFAULTS else 999, x))
        value_list.append("その他（自由入力）")
        old = self.table.item(row, col).text() if self.table.item(row, col) else ""
        val, ok = QInputDialog.getItem(self, "セル編集", f"{self.table.horizontalHeaderItem(col).text()}を選択:", value_list, 0, False)
        if ok:
            if val == "その他（自由入力）":
                text, ok2 = QInputDialog.getText(self, "セル編集", f"新しい値を入力（{self.table.horizontalHeaderItem(col).text()}）:", text=old)
                if ok2:
                    self.table.setItem(row, col, QTableWidgetItem(text))
                    self._auto_save_json()
            else:
                self.table.setItem(row, col, QTableWidgetItem(val))
                self._auto_save_json()

    def _on_add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        for i in range(5):
            self.table.setItem(row, i, QTableWidgetItem(""))
        self.table.selectRow(row)

    def _on_delete_row(self):
        selected = self.table.selectionModel().selectedRows()
        for idx in sorted(selected, key=lambda x: -x.row()):
            self.table.removeRow(idx.row())

    def _on_select_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "ユーザー辞書JSONを選択", self.file_path_edit.text(), "JSON Files (*.json)")
        if not path:
            return
        self.file_path_edit.setText(path)
        self.dictionary_manager.records = []
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "records" in data:
                self.dictionary_manager.records = data["records"]
                self.dictionary_manager.photo_categories = data.get("photo_categories", PHOTO_CATEGORY_DEFAULTS)
            elif isinstance(data, list):
                self.dictionary_manager.records = data
                self.dictionary_manager.photo_categories = PHOTO_CATEGORY_DEFAULTS
            else:
                QMessageBox.warning(self, "形式エラー", "不明な形式のJSONです")
        except Exception as e:
            QMessageBox.warning(self, "読込エラー", f"ファイル読込に失敗: {e}")
        self._load_table_from_records()

    def _auto_save_json(self):
        path = self.file_path_edit.text()
        print(f"[LOG] 保存先パス: {path}")
        if not path:
            return
        rotate_backups(path, max_backup=20)
        records = []
        for row in range(self.table.rowCount()):
            rec = {
                "photo_category": self.table.item(row, 0).text() if self.table.item(row, 0) else "",
                "work_category": self.table.item(row, 1).text() if self.table.item(row, 1) else "",
                "type": self.table.item(row, 2).text() if self.table.item(row, 2) else "",
                "subtype": self.table.item(row, 3).text() if self.table.item(row, 3) else "",
                "remarks": self.table.item(row, 4).text() if self.table.item(row, 4) else "",
            }
            records.append(rec)
        # photo_categoriesは現状維持
        try:
            save_records_to_json(path, records, as_reference=True)
            # ラストパスJSONも保存
            with open(LAST_PATH_FILE, "w", encoding="utf-8") as f:
                json.dump({"last_path": path}, f)
            print(f"[LOG] ラストパスJSON保存: {LAST_PATH_FILE}")
            print(f"[LOG] 自動保存: {path}")
        except Exception as e:
            print(f"[LOG] 自動保存失敗: {e}")

    def _auto_load_last_json(self):
        print("[LOG] _auto_load_last_json呼び出し")
        print(f"[LOG] LAST_PATH_FILE: {LAST_PATH_FILE}")
        if not os.path.exists(LAST_PATH_FILE):
            print("[LOG] LAST_PATH_FILEが存在しません")
            return
        with open(LAST_PATH_FILE, encoding="utf-8") as f:
            raw = f.read()
            print(f"[LOG] .userdict_lastpath.json内容: {raw}")
            f.seek(0)
            d = json.load(f)
        last_path = d.get("last_path")
        print(f"[LOG] 自動復元: last_path={last_path}")
        if last_path and os.path.exists(last_path):
            with open(last_path, encoding="utf-8") as f2:
                raw = f2.read()
                print(f"[LOG] 起動時JSON内容: {raw}")
                f2.seek(0)
                data = json.loads(raw)
            if isinstance(data, dict) and "records" in data:
                self.dictionary_manager.records = data["records"]
                self.dictionary_manager.photo_categories = data.get("photo_categories", PHOTO_CATEGORY_DEFAULTS)
            elif isinstance(data, list):
                self.dictionary_manager.records = data
                self.dictionary_manager.photo_categories = PHOTO_CATEGORY_DEFAULTS
            print(f"[LOG] 自動復元: {last_path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dm = DictionaryManager()
    dlg = DictionaryListEditorDialog(dm)
    dlg.exec()