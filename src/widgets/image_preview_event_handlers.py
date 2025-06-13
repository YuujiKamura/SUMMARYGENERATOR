from PyQt6.QtWidgets import QDialog

def wheel_event(dialog, event):
    angle = event.angleDelta().y()
    prev_idx = dialog._zoom_idx
    prev_scale = dialog._zoom_scale
    if angle > 0 and dialog._zoom_idx < len(dialog.ZOOM_LEVELS) - 1:
        dialog._zoom_idx += 1
    elif angle < 0 and dialog._zoom_idx > 0:
        dialog._zoom_idx -= 1
    if dialog._zoom_idx != prev_idx:
        dialog._zoom_scale = dialog.ZOOM_LEVELS[dialog._zoom_idx]
        mouse_pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
        label_size = dialog.image_widget.size()
        base_w, base_h = label_size.width(), label_size.height()
        scaled_w_prev = int(dialog._orig_size[0] * prev_scale)
        scaled_h_prev = int(dialog._orig_size[1] * prev_scale)
        x0_prev = (base_w - scaled_w_prev) // 2 + dialog._offset_x
        y0_prev = (base_h - scaled_h_prev) // 2 + dialog._offset_y
        rel_x = mouse_pos.x() - x0_prev
        rel_y = mouse_pos.y() - y0_prev
        if 0 <= rel_x < scaled_w_prev and 0 <= rel_y < scaled_h_prev:
            scaled_w_new = int(dialog._orig_size[0] * dialog._zoom_scale)
            scaled_h_new = int(dialog._orig_size[1] * dialog._zoom_scale)
            ratio_x = rel_x / scaled_w_prev
            ratio_y = rel_y / scaled_h_prev
            rel_x_new = int(ratio_x * scaled_w_new)
            rel_y_new = int(ratio_y * scaled_h_new)
            x0_new = mouse_pos.x() - rel_x_new
            y0_new = mouse_pos.y() - rel_y_new
            dialog._offset_x = x0_new - (base_w - scaled_w_new) // 2
            dialog._offset_y = y0_new - (base_h - scaled_h_new) // 2
        else:
            dialog._offset_x = 0
            dialog._offset_y = 0
        dialog.update_image_with_bboxes()

def mouse_press_event(dialog, event):
    QDialog.mousePressEvent(dialog, event)

def close_event(dialog, event):
    QDialog.closeEvent(dialog, event)

def accept(dialog):
    QDialog.accept(dialog)

def reject(dialog):
    QDialog.reject(dialog)

def done(dialog, r):
    QDialog.done(dialog, r)
