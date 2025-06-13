import os
import json
import unicodedata
from PyQt6.QtCore import QObject, pyqtSignal
from src.utils.path_manager import PathManager

# ROLE_MAPPING_PATHをpath_managerから取得
path_manager = PathManager()
ROLE_MAPPING_PATH = str(path_manager.role_mapping)

class RoleMappingManager(QObject):
    role_mapping_changed = pyqtSignal(str)  # パス変更時に通知

    def __init__(self, default_path):
        super().__init__()
        self._path = default_path

    def get_path(self):
        return self._path

    def set_path(self, new_path):
        if self._path != new_path:
            self._path = new_path
            self.role_mapping_changed.emit(new_path)

    def exists(self):
        return os.path.exists(self._path)

    def load(self):
        with open(self._path, encoding="utf-8") as f:
            return json.load(f)

def load_role_mapping(path=ROLE_MAPPING_PATH):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    # 旧形式対応
    for k, v in list(data.items()):
        if isinstance(v, list):
            data[k] = {"roles": v, "match": "all"}
    return data

def load_image_roles_from_cache(cache_dir):
    """
    画像パス→[role, ...] のdictを返す
    """
    result = {}
    if not os.path.exists(cache_dir):
        return result
    for fname in os.listdir(cache_dir):
        if not fname.endswith('.json'):
            continue
        fpath = os.path.join(cache_dir, fname)
        try:
            with open(fpath, encoding='utf-8') as f:
                data = json.load(f)
            img_path = data.get('image_path')
            if not img_path:
                continue
            bboxes = data.get('bboxes', [])
            roles = [b.get('role') for b in bboxes if b.get('role')]
            if roles:
                result[img_path] = roles
        except Exception as e:
            print(f"[cache read error] {fpath}: {e}")
    return result

def normalize_role_name(role: str) -> str:
    """
    ロール名を正規化（全角→半角、小文字化、前後空白除去など）
    """
    if not isinstance(role, str):
        return ""
    role = unicodedata.normalize('NFKC', role)
    role = role.strip().lower()
    # ここにtypo補正や追加ルールを必要に応じて追加
    return role
