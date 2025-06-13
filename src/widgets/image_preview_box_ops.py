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
