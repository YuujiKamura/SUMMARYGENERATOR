class ZoomableMixin:
    ZOOM_LEVELS = (0.5, 1.0, 1.5)

    def _init_zoom(self, widget):
        self._view = widget
        self._zoom_idx = 0
        self._zoom_scale = self.ZOOM_LEVELS[0]
        self._offset_x = 0
        self._offset_y = 0
        self._orig_size = (0, 0)

    def wheelEvent(self, event):
        angle = event.angleDelta().y()
        prev_idx = self._zoom_idx
        prev_scale = self._zoom_scale
        if angle > 0 and self._zoom_idx < len(self.ZOOM_LEVELS) - 1:
            self._zoom_idx += 1
        elif angle < 0 and self._zoom_idx > 0:
            self._zoom_idx -= 1
        if self._zoom_idx != prev_idx:
            self._zoom_scale = self.ZOOM_LEVELS[self._zoom_idx]
            mouse_pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
            label_size = self._view.size()
            base_w, base_h = label_size.width(), label_size.height()
            scaled_w_prev = int(self._orig_size[0] * prev_scale)
            scaled_h_prev = int(self._orig_size[1] * prev_scale)
            x0_prev = (base_w - scaled_w_prev) // 2 + self._offset_x
            y0_prev = (base_h - scaled_h_prev) // 2 + self._offset_y
            rel_x = mouse_pos.x() - x0_prev
            rel_y = mouse_pos.y() - y0_prev
            if 0 <= rel_x < scaled_w_prev and 0 <= rel_y < scaled_h_prev:
                scaled_w_new = int(self._orig_size[0] * self._zoom_scale)
                scaled_h_new = int(self._orig_size[1] * self._zoom_scale)
                ratio_x = rel_x / scaled_w_prev
                ratio_y = rel_y / scaled_h_prev
                rel_x_new = int(ratio_x * scaled_w_new)
                rel_y_new = int(ratio_y * scaled_h_new)
                x0_new = mouse_pos.x() - rel_x_new
                y0_new = mouse_pos.y() - rel_y_new
                self._offset_x = x0_new - (base_w - scaled_w_new) // 2
                self._offset_y = y0_new - (base_h - scaled_h_new) // 2
            else:
                self._offset_x = 0
                self._offset_y = 0
            self._apply_zoom()

    def _apply_zoom(self):
        self._view.update()
