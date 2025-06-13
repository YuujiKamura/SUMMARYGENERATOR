import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QListWidget, QListWidgetItem, QMessageBox, QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from .role_selector import select_role_menu
from .role_editor_dialog import RoleEditorDialog
import threading
from src.utils.records_loader import load_records_from_json
from src.utils.path_manager import path_manager
from src.utils.datadeploy_test import run_datadeploy_test
from src.utils.chain_record_utils import ChainRecord, load_chain_records
from src.utils.role_mapping_utils import RoleMappingManager
from src.db_manager import ChainRecordManager, RoleMappingManager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RECORDS_PATH = str(path_manager.default_records)
ROLES_PATH = str(path_manager.data_dir / 'preset_roles.json')
MAPPING_PATH = os.path.abspath(os.path.join(BASE_DIR, '../role_mapping.json'))

DATASET_JSON_PATH = str(path_manager.scan_for_images_dataset)

class DictionaryMappingWidget(QWidget):
    mapping_updated = pyqtSignal()  # シグナル追加
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("辞書エントリー⇔ロール割当ウィジェット")
        self.resize(600, 440)
        layout = QVBoxLayout(self)

        # --- データ読込 ---
        self.chain_records = self.load_chain_records()
        self.roles = self.load_roles()
        self.mapping = self.load_mapping()
        self.max_roles = 10

        # --- エントリー選択 ---
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("辞書エントリー:"))
        self.entry_combo = QComboBox()
        self.entry_combo.setMinimumWidth(400)
        for rec in self.chain_records:
            disp = f"{rec.work_category or ''}, {rec.type or ''}, {rec.subtype or ''}, {rec.remarks or ''}"
            self.entry_combo.addItem(disp, rec)
        self.entry_combo.currentIndexChanged.connect(self.on_entry_changed)
        hbox.addWidget(self.entry_combo, 1)
        layout.addLayout(hbox)

        # --- 割当ロールリスト ---
        self.role_list = QListWidget()
        self.role_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.role_list)
        self.role_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.role_list.customContextMenuRequested.connect(self.on_role_list_context_menu)

        # --- 一致条件 ---
        match_hbox = QHBoxLayout()
        match_hbox.addWidget(QLabel("一致条件:"))
        self.match_combo = QComboBox()
        self.match_combo.addItem("全てのロールが見つかったら一致", "all")
        self.match_combo.addItem("どれか1つでも見つかったら一致", "any")
        self.match_combo.currentIndexChanged.connect(self.on_match_changed)
        match_hbox.addWidget(self.match_combo)
        match_hbox.addStretch(1)
        layout.addLayout(match_hbox)

        # --- ロール操作ボタン ---
        btn_hbox = QHBoxLayout()
        self.add_btn = QPushButton("+ロール追加")
        self.add_btn.clicked.connect(self.on_add_role)
        btn_hbox.addWidget(self.add_btn)
        self.up_btn = QPushButton("↑")
        self.up_btn.clicked.connect(self.on_move_up)
        btn_hbox.addWidget(self.up_btn)
        self.down_btn = QPushButton("↓")
        self.down_btn.clicked.connect(self.on_move_down)
        btn_hbox.addWidget(self.down_btn)
        self.del_btn = QPushButton("×")
        self.del_btn.clicked.connect(self.on_delete_role)
        btn_hbox.addWidget(self.del_btn)
        btn_hbox.addStretch(1)
        layout.addLayout(btn_hbox)

        # --- 保存・リセット ---
        save_hbox = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.on_save)
        save_hbox.addWidget(self.save_btn)
        self.reset_btn = QPushButton("リセット")
        self.reset_btn.clicked.connect(self.on_reset)
        save_hbox.addWidget(self.reset_btn)
        save_hbox.addStretch(1)
        layout.addLayout(save_hbox)

        self.on_entry_changed(0)

    def load_chain_records(self):
        return [ChainRecord.from_dict(r) for r in ChainRecordManager.get_all_chain_records()]

    def load_roles(self):
        with open(ROLES_PATH, encoding='utf-8') as f:
            return json.load(f)

    def load_mapping(self):
        rows = RoleMappingManager.get_all_role_mappings()
        mapping = {}
        for row in rows:
            mapping[row['role_name']] = json.loads(row['mapping_json']) if row['mapping_json'] else {}
        return mapping

    def save_mapping(self, mapping):
        for remarks, v in mapping.items():
            RoleMappingManager.add_or_update_role_mapping(remarks, json.dumps(v, ensure_ascii=False))

    def get_current_remarks(self):
        rec: ChainRecord = self.entry_combo.currentData()
        return rec.remarks if rec else ''

    def update_mapping_from_list(self):
        """現在のリスト内容と一致条件をself.mappingに即時反映し、バックグラウンド保存"""
        remarks = self.get_current_remarks()
        roles = [self.role_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.role_list.count())]
        match = self.match_combo.currentData()
        if roles:
            self.mapping[remarks] = {"roles": roles, "match": match}
        elif remarks in self.mapping:
            del self.mapping[remarks]
        self.save_mapping(self.mapping)

    def on_entry_changed(self, idx):
        self.role_list.clear()
        remarks = self.get_current_remarks()
        entry = self.mapping.get(remarks, {})
        roles = entry.get("roles") if isinstance(entry, dict) else entry
        if roles is None:
            roles = []
        for role_label in roles:
            role = next((r for r in self.roles if r['label'] == role_label), None)
            disp = role['display'] if role else role_label
            item = QListWidgetItem(disp)
            item.setData(Qt.ItemDataRole.UserRole, role_label)
            self.role_list.addItem(item)
        # 一致条件の復元
        match = entry.get("match") if isinstance(entry, dict) else "all"
        idx = self.match_combo.findData(match)
        if idx >= 0:
            self.match_combo.setCurrentIndex(idx)
        else:
            self.match_combo.setCurrentIndex(0)
        if self.role_list.count() > 0:
            self.role_list.setCurrentRow(0)
        self.update_btn_state()

    def on_match_changed(self, idx):
        self.update_mapping_from_list()

    def handle_role_selected(self, label):
        if self.role_list.count() >= self.max_roles:
            QMessageBox.warning(self, "上限", f"最大{self.max_roles}個までです")
            return
        for i in range(self.role_list.count()):
            if self.role_list.item(i).data(Qt.ItemDataRole.UserRole) == label:
                QMessageBox.warning(self, "重複", "すでに追加済みです")
                return
        role = next((r for r in self.roles if r['label'] == label), None)
        disp = role['display'] if role else label
        item = QListWidgetItem(disp)
        item.setData(Qt.ItemDataRole.UserRole, label)
        self.role_list.addItem(item)
        self.update_btn_state()
        self.update_mapping_from_list()

    def handle_edit_roles(self):
        dlg = RoleEditorDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.roles = self.load_roles()
            self.on_entry_changed(self.entry_combo.currentIndex())

    def on_add_role(self):
        select_role_menu(
            self,
            self.roles,
            self.handle_role_selected,
            self.handle_edit_roles,
            pos=self.add_btn.mapToGlobal(self.add_btn.rect().bottomLeft())
        )

    def on_role_list_context_menu(self, pos):
        select_role_menu(
            self.role_list,
            self.roles,
            self.handle_role_selected,
            self.handle_edit_roles,
            pos=self.role_list.viewport().mapToGlobal(pos)
        )

    def on_move_up(self):
        row = self.role_list.currentRow()
        if row > 0:
            item = self.role_list.takeItem(row)
            self.role_list.insertItem(row-1, item)
            self.role_list.setCurrentRow(row-1)
        self.update_btn_state()
        self.update_mapping_from_list()

    def on_move_down(self):
        row = self.role_list.currentRow()
        if 0 <= row < self.role_list.count()-1:
            item = self.role_list.takeItem(row)
            self.role_list.insertItem(row+1, item)
            self.role_list.setCurrentRow(row+1)
        self.update_btn_state()
        self.update_mapping_from_list()

    def on_delete_role(self):
        row = self.role_list.currentRow()
        if row >= 0:
            self.role_list.takeItem(row)
        self.update_btn_state()
        self.update_mapping_from_list()

    def on_save(self):
        self.update_mapping_from_list()
        QMessageBox.information(self, "保存", "ロール割当を保存しました")
        self.mapping_updated.emit()  # シグナル発行

    def on_reset(self):
        self.mapping = {}
        self.on_entry_changed(self.entry_combo.currentIndex())
        self.save_mapping()
        QMessageBox.information(self, "リセット", "ロール割当をリセットしました")
        self.mapping_updated.emit()  # シグナル発行

    def update_btn_state(self):
        cnt = self.role_list.count()
        self.add_btn.setEnabled(cnt < self.max_roles)
        sel = self.role_list.currentRow()
        self.up_btn.setEnabled(sel > 0)
        self.down_btn.setEnabled(0 <= sel < cnt-1)
        self.del_btn.setEnabled(sel >= 0)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-datadeploy", action="store_true")
    args = parser.parse_args()
    if args.test_datadeploy:
        from os.path import dirname, abspath, join
        BASE_DIR = dirname(abspath(__file__))
        DATASET_JSON_PATH = join(BASE_DIR, "scan_for_images_dataset.json")
        CACHE_DIR = join(BASE_DIR, "image_preview_cache")
        run_datadeploy_test(DATASET_JSON_PATH, CACHE_DIR, use_thermo_special=True)

    from PyQt6.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    w = DictionaryMappingWidget()
    w.show()
    sys.exit(app.exec())