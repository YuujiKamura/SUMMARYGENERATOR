import os
import sys
import json
import logging
from PyQt6.QtWidgets import QMenu, QApplication, QMessageBox, QDialog
from PyQt6.QtCore import Qt, QTimer
from .location_utils import LocationInputDialog, load_location_history, save_location_history
from src.utils.image_cache_utils import get_image_cache_path


def handle_image_list_context_menu(parent, image_list_panel, items, pos, folder_path_edit, set_status, on_image_json_saved, image_data_manager):
    menu = QMenu(parent)
    act_assign_location = menu.addAction("測点（location）を割り当て")
    act_copy_img = menu.addAction("画像パスをコピー")
    act_copy_json = menu.addAction("キャッシュJSONパスをコピー")
    act_open_folder = menu.addAction("画像フォルダを開く")
    act_open_preview = menu.addAction("イメージプレビューで開く")
    action = menu.exec(image_list_panel.mapToGlobal(pos))
    CACHE_DIR = folder_path_edit.text().strip() if folder_path_edit else None
    if action == act_copy_img:
        img_paths = []
        for i in items:
            item_data = i.data(Qt.ItemDataRole.UserRole)
            if isinstance(item_data, str):
                img_paths.append(item_data)
            elif hasattr(item_data, 'path'):
                img_paths.append(item_data.path)
        QApplication.clipboard().setText("\\n".join(img_paths))
    elif action == act_copy_json:
        json_paths = []
        for i in items:
            item_data = i.data(Qt.ItemDataRole.UserRole)
            img_path = None
            if isinstance(item_data, str):
                img_path = item_data
            elif hasattr(item_data, 'path'):
                img_path = item_data.path
            
            if img_path and CACHE_DIR: # CACHE_DIR もチェック
                json_paths.append(get_image_cache_path(img_path, CACHE_DIR))
            elif not CACHE_DIR:
                logging.warning("CACHE_DIR is not set. Cannot get JSON path.") # 警告ログ追加
        QApplication.clipboard().setText("\\\\n".join(json_paths))
    elif action == act_open_folder:
        item_data = items[0].data(Qt.ItemDataRole.UserRole)
        folder_path = None
        if isinstance(item_data, str):
            folder_path = item_data
        elif hasattr(item_data, 'path'):
            folder_path = item_data.path
        
        if folder_path:
            folder = os.path.dirname(folder_path)
            if sys.platform.startswith('win'):
                os.startfile(folder)
            elif sys.platform.startswith('darwin'):
                import subprocess
                subprocess.Popen(['open', folder])
            else:
                import subprocess
                subprocess.Popen(['xdg-open', folder])
    elif action == act_assign_location:
        dlg = LocationInputDialog(parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            text = dlg.get_text()
            if text:
                history = load_location_history()
                if text in history:
                    history.remove(text)
                history.insert(0, text)
                history = history[:20]
                save_location_history(history)
                logger = logging.getLogger('app_debug')
                list_widget = image_list_panel.image_list_widget
                selected_paths = set()
                for item in list_widget.selectedItems():
                    entry = item.data(Qt.ItemDataRole.UserRole)
                    if hasattr(entry, 'path'):
                        selected_paths.add(entry.path)
                scroll_pos = list_widget.verticalScrollBar().value() if list_widget.verticalScrollBar() else None
                logger.debug(f"[測点割当] 割当前: selected_paths={selected_paths} scroll_pos={scroll_pos}")
                img_paths = []
                for i in items:
                    img_path = i.data(Qt.ItemDataRole.UserRole)
                    if hasattr(img_path, 'path'):
                        img_path = img_path.path
                    img_paths.append(img_path)
                    logger.debug(f"[測点割当] img_path={img_path}")
                for img_path in img_paths:
                    json_path = get_image_cache_path(img_path, CACHE_DIR)
                    if os.path.exists(json_path):
                        try:
                            with open(json_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                        except Exception:
                            data = {}
                    else:
                        data = {}
                    data["location"] = text
                    try:
                        with open(json_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                    except Exception as e:
                        QMessageBox.warning(parent, "エラー", f"{json_path} の保存に失敗: {e}")
                    set_status(f"[測点割当] {img_path} にlocation={text}を保存・反映")
                    if on_image_json_saved is not None:
                        on_image_json_saved(img_path)
                set_status(f"{len(items)}件の画像に測点（location）を割り当てました")
                for entry in getattr(image_data_manager, 'entries', []):
                    if entry.path in img_paths:
                        if entry.cache_json is not None:
                            entry.cache_json["location"] = text
                for i in range(list_widget.count()):
                    entry = list_widget.item(i).data(Qt.ItemDataRole.UserRole)
                    if hasattr(entry, 'path') and entry.path in img_paths:
                        list_widget.item(i).setToolTip(f"{os.path.basename(entry.path)}\n測点: {entry.cache_json.get('location', '')}")
                def restore_selection():
                    for i in range(list_widget.count()):
                        entry = list_widget.item(i).data(Qt.ItemDataRole.UserRole)
                        if hasattr(entry, 'path') and entry.path in selected_paths:
                            list_widget.item(i).setSelected(True)
                    if scroll_pos is not None:
                        list_widget.verticalScrollBar().setValue(scroll_pos)
                    logger.debug(f"[測点割当] restore_selection完了: scroll_pos={scroll_pos}")
                QTimer.singleShot(0, restore_selection)
    elif action == act_open_preview:
        if items:
            item_data = items[0].data(Qt.ItemDataRole.UserRole)
            img_path_to_open = None
            if isinstance(item_data, str):
                img_path_to_open = item_data
            elif hasattr(item_data, 'path'):
                img_path_to_open = item_data.path

            if img_path_to_open:
                # SummaryGeneratorWidgetのインスタンスメソッドを呼び出す想定であれば、
                # parent が SummaryGeneratorWidget のインスタンスである必要がある。
                # ここでは、SummaryGeneratorWidget に on_image_item_double_clicked があると仮定。
                if hasattr(parent, 'on_image_double_clicked') and callable(getattr(parent, 'on_image_double_clicked')) :
                    # on_image_double_clicked が entry オブジェクトを期待する場合、
                    # img_path_to_open だけでは不十分かもしれない。
                    # ここでは、items[0].data(Qt.ItemDataRole.UserRole) が entry オブジェクトであることを期待してそのまま渡す。
                    # ただし、上記の img_path_to_open のロジックと矛盾が生じる可能性あり。
                    # 一旦、オリジナルのロジックに近い形で entry オブジェクト (item_data) を渡すようにする。
                    parent.on_image_double_clicked(item_data)
                else:
                    logging.warning("Parent does not have a callable on_image_double_clicked method.")
            else:
                logging.warning("Could not determine image path for preview.")
