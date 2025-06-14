from PyQt6.QtWidgets import QMenu, QWidgetAction, QMessageBox
from PyQt6.QtGui import QCursor
from src.components.role_tree_selector import RoleTreeSelector

__all__ = ["handle_box_right_clicked"]

def handle_box_right_clicked(dialog, indices):
    """
    ImagePreviewDialogのon_box_right_clickedのロジックを外部化
    dialog: ImagePreviewDialogインスタンス
    indices: 選択インデックスリスト
    """
    if not indices:
        return
    menu = QMenu(dialog)
    role_selector = RoleTreeSelector(dialog.roles)
    action = QWidgetAction(menu)
    action.setDefaultWidget(role_selector)
    menu.addAction(action)
    menu.addSeparator()
    delete_action = menu.addAction("選択ボックスを削除")
    dupdel_action = menu.addAction("重複ボックス検出削除")
    edit_action = menu.addAction("ロール編集...")
    incorrect_action = menu.addAction("不正解としてマーク（ImageEntry保存）")

    def on_role_selected(role_label):
        for idx in indices:
            dialog.bboxes[idx].role = role_label
        dialog.update_image_with_bboxes()
        dialog.save_bboxes_to_image_cache()
        menu.close()
    role_selector.role_selected.connect(on_role_selected)

    selected_action = menu.exec(dialog.mapToGlobal(dialog.image_widget.mapFromGlobal(QCursor.pos())))
    if selected_action == delete_action:
        for idx in sorted(indices, reverse=True):
            if 0 <= idx < len(dialog.bboxes):
                del dialog.bboxes[idx]
        dialog.selected_indices = []
        dialog.update_image_with_bboxes()
        dialog.save_bboxes_to_image_cache()
    elif selected_action == dupdel_action:
        def is_same_box(b1, b2):
            if b1.cid != b2.cid or b1.cname != b2.cname or b1.role != b2.role:
                return False
            return all(abs(a-b) < 1.0 for a, b in zip(b1.xyxy, b2.xyxy))
        unique = []
        for b in dialog.bboxes:
            if not any(is_same_box(b, u) for u in unique):
                unique.append(b)
        if len(unique) < len(dialog.bboxes):
            dialog.bboxes = unique
            dialog.selected_indices = []
            dialog.update_image_with_bboxes()
            dialog.save_bboxes_to_image_cache()
    elif selected_action == edit_action:
        dialog.open_role_editor()
    elif selected_action == incorrect_action:
        # ImageEntryとして保存
        from src.utils.image_entry import ImageEntry
        import json, os
        # 元アノテーションJSONのパス
        json_path = getattr(dialog, 'json_path', None)
        if json_path and os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                entry_dict = json.load(f)
            # ImageEntryとしてバリデート（必要ならfrom_dict等）
            # ここではdictのまま保存
            output_path = os.path.join(os.path.dirname(__file__), '../data/retrain/incorrect_entries.json')
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            try:
                if os.path.exists(output_path):
                    with open(output_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                else:
                    data = []
            except Exception:
                data = []
            data.append(entry_dict)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            QMessageBox.information(dialog, "保存完了", f"不正解エントリーを保存しました\n{output_path}")
        else:
            QMessageBox.warning(dialog, "エラー", "元アノテーションJSONが見つかりません")
