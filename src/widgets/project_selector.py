from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QLabel, QInputDialog, QMessageBox, QWidget
from PyQt6.QtCore import pyqtSignal
import os
import glob
import json
from .project_manager_dialog import ProjectManagerDialog

class ProjectSelector(QWidget):
    project_selected = pyqtSignal()
    def __init__(self, path_manager, config_path, default_project_path=None, parent=None):
        super().__init__(parent)
        self.path_manager = path_manager
        self.config_path = config_path
        self.default_project_path = default_project_path
        self.selected_project = None
        self.selected_json_path = None
        self.selected_folder_path = None
        self.hbox = QHBoxLayout(self)
        self.project_select_btn = QPushButton("プロジェクト選択")
        self.project_label = QLabel("")
        self.hbox.addWidget(self.project_select_btn)
        self.hbox.addWidget(self.project_label)
        self.project_select_btn.clicked.connect(self.select_project_dialog)
        # デフォルト選択
        if default_project_path and os.path.exists(default_project_path):
            self.select_project(default_project_path, silent=True)

    def select_project_dialog(self):
        # ProjectManagerDialogを開いて選択
        managed_base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "managed_files"))
        dlg = ProjectManagerDialog(managed_base, self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            json_path = getattr(dlg, 'selected_project_json_path', None)
            if json_path and os.path.exists(json_path):
                self.select_project(json_path)

    def select_project(self, default_path=None, silent=False):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "managed_files"))
        json_files = glob.glob(os.path.join(base_dir, "**", "*.json"), recursive=True)
        candidates = []
        default_idx = 0
        for i, f in enumerate(json_files):
            try:
                with open(f, encoding="utf-8") as jf:
                    d = json.load(jf)
                if "image_list_json" in d and "image_dir" in d:
                    candidates.append((d.get("project_name") or os.path.basename(f), f, d))
                    if default_path and os.path.abspath(f) == os.path.abspath(default_path):
                        default_idx = len(candidates) - 1
            except Exception:
                continue
        if not candidates:
            QMessageBox.warning(self, "プロジェクト選択", "プロジェクトJSONが見つかりません")
            return
        items = [f"{c[0]}\n({os.path.relpath(c[1], base_dir)})" for c in candidates]
        idx = default_idx
        ok = True
        if not default_path:
            idx, ok = QInputDialog.getItem(self, "プロジェクト選択", "プロジェクトを選択:", items, 0, False)
            if not ok or not idx:
                return
            sel = items.index(idx)
        else:
            sel = default_idx
        proj = candidates[sel][2]
        proj_dir = os.path.dirname(candidates[sel][1])
        image_list_json = proj["image_list_json"]
        image_dir = proj["image_dir"]
        if not os.path.isabs(image_list_json):
            json_path = os.path.abspath(os.path.join(proj_dir, image_list_json))
        else:
            json_path = image_list_json
        if not os.path.isabs(image_dir):
            folder_path = os.path.abspath(os.path.join(proj_dir, image_dir))
        else:
            folder_path = image_dir
        self.selected_project = candidates[sel][0]
        self.selected_json_path = json_path
        self.selected_folder_path = folder_path
        self.project_label.setText(f"選択中: {self.selected_project}")
        # 設定ファイルに保存
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump({"last_json_path": os.path.abspath(json_path)}, f)
        except Exception:
            pass
        # プロジェクトチェーンをpath_managerに追加
        try:
            if hasattr(self.path_manager, 'project_chain'):
                if os.path.abspath(candidates[sel][1]) not in self.path_manager.project_chain:
                    self.path_manager.project_chain.append(os.path.abspath(candidates[sel][1]))
            else:
                self.path_manager.project_chain = [os.path.abspath(candidates[sel][1])]
            self.path_manager.current_project_path = os.path.abspath(candidates[sel][1])
        except Exception as e:
            print(f"[WARN] path_managerへのプロジェクトチェーン追加失敗: {e}")
        if not silent:
            self.project_selected.emit()
