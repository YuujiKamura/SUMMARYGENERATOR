from .path_manager import path_manager
import os
import shutil
from pathlib import Path

def save_current_managed_files(base_dir=None):
    """
    現在アサインされている管理ファイルを managed_files/current に集約保存する
    :param base_dir: 基準ディレクトリ（Noneならこのファイルの親の親）
    """
    if base_dir is None:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    managed_dir = os.path.join(base_dir, "managed_files", "current")
    os.makedirs(managed_dir, exist_ok=True)
    path_manager.copy_all_managed_files(managed_dir, overwrite=True)
    return managed_dir 

def switch_managed_file_set(set_dir):
    """
    指定ディレクトリ内の管理ファイルセットを、path_managerの各所定位置に上書きコピーする
    :param set_dir: 管理ファイルセットのディレクトリ
    """
    set_dir = Path(set_dir)
    # path_managerが管理しているファイル名とパスのマッピングを作る
    managed_targets = {p.name: p for p in path_manager.list_all_json()}
    # セットディレクトリ内のファイルを上書きコピー
    for file in set_dir.glob("*.json"):
        if file.name in managed_targets:
            shutil.copy2(file, managed_targets[file.name])
    # image_preview_cache ディレクトリ
    cache_src = set_dir / "image_preview_cache"
    cache_dst = path_manager.src_dir / "image_preview_cache"
    if cache_src.exists() and cache_src.is_dir():
        if cache_dst.exists():
            shutil.rmtree(cache_dst)
        shutil.copytree(cache_src, cache_dst)
    # data/dictionaries ディレクトリ
    dict_src = set_dir / "dictionaries"
    dict_dst = path_manager.project_root / "data" / "dictionaries"
    if dict_src.exists() and dict_src.is_dir():
        if dict_dst.exists():
            shutil.rmtree(dict_dst)
        shutil.copytree(dict_src, dict_dst)
    # 必要に応じて他の管理ディレクトリも追加
    return str(set_dir) 