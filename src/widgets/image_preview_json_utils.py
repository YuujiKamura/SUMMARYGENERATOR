import os
import json
from PyQt6.QtWidgets import QMessageBox
from src.utils.image_cache_utils import load_image_cache, save_image_cache, get_image_cache_path
from src.components.json_bbox_viewer_dialog import JsonBboxViewerDialog

__all__ = ["restore_bboxes_from_cache", "save_bboxes_to_image_cache", "show_current_json"]

def restore_bboxes_from_cache(dialog):
    _, bboxes = load_image_cache(dialog.img_path)
    if bboxes:
        dialog.bboxes = [dialog.BoundingBox.from_dict(b) for b in bboxes]
        print(f"[共通キャッシュ復元] {dialog.img_path} bboxes: {dialog.bboxes}")
    else:
        dialog.bboxes = []
        print(f"[共通キャッシュ復元] {dialog.img_path} bboxes: EMPTY")

def save_bboxes_to_image_cache(dialog):
    ret = QMessageBox.question(dialog, "キャッシュ上書き確認", "この検出結果でキャッシュ（image_preview_cache）を上書きしますか？",
                               QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
    if ret != QMessageBox.StandardButton.Ok:
        dialog.status_label.setText("[LOG] 保存をキャンセルしました")
        return False
    ok = save_image_cache(dialog.img_path, dialog.bboxes)
    if ok:
        print(f"[共通キャッシュ保存] {dialog.img_path} bboxes: {dialog.bboxes}")
    return ok

def show_current_json(dialog):
    cache_path = get_image_cache_path(dialog.img_path)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    else:
        data = {}
    dialog.bboxes = dialog.image_widget.bboxes.copy()
    dlg = JsonBboxViewerDialog(dialog.img_path, cache_path, dialog)
    dlg.image_json_saved.connect(lambda _: dialog.image_json_saved.emit(dialog.img_path))
    dlg.exec()
