from __future__ import annotations

"""画像リスト JSON 選択ダイアログの共通アクション。Widget と UI の衝突を避けるため分離。"""

import logging
from typing import Optional
from PyQt6.QtWidgets import QFileDialog, QWidget, QLineEdit
from src.utils.path_manager import path_manager

__all__ = ["open_image_list_json_dialog"]


def open_image_list_json_dialog(
    parent: QWidget,
    json_path_edit: Optional[QLineEdit] = None,
) -> Optional[str]:
    """ファイルダイアログを開いて画像リスト JSON を選択する。

    Parameters
    ----------
    parent : QWidget
        ダイアログの親ウィジェット。
    json_path_edit : QLineEdit | None
        選択結果を表示するテキストボックス。指定されていれば自動で反映。

    Returns
    -------
    str | None
        選択されたファイルパス。キャンセル時は ``None``。
    """

    initial_path = path_manager.current_image_list_json
    file_path, _ = QFileDialog.getOpenFileName(
        parent,
        "画像リストJSONを選択",
        initial_path,
        "JSON Files (*.json)"
    )
    if not file_path:
        return None

    # パスを保存し UI に反映
    path_manager.current_image_list_json = file_path
    if json_path_edit is not None:
        json_path_edit.setText(file_path)

    logging.info("[LOG] 画像リストJSONを開く: %s", file_path)
    return file_path 