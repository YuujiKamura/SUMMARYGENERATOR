# バウンディングボックスクリック判定ユーティリティ

def is_point_in_bbox(x, y, bbox):
    """
    座標(x, y)がbboxのxyxy矩形内に入っているか判定
    bbox: [x1, y1, x2, y2] または (x1, y1, x2, y2)
    """
    if not bbox or len(bbox) != 4:
        return False
    x1, y1, x2, y2 = bbox
    # x1, y1, x2, y2が昇順でない場合も考慮
    left, right = sorted([x1, x2])
    top, bottom = sorted([y1, y2])
    return left <= x <= right and top <= y <= bottom

# 画像が縮小・拡大されている場合のスケール変換付き判定
def is_point_in_bbox_scaled(x, y, bbox, orig_size, disp_size):
    """
    画像がorig_size→disp_sizeにリサイズされている場合のクリック判定
    x, y: 表示画像上の座標
    bbox: オリジナル画像上のxyxy
    orig_size: (w, h) オリジナル画像サイズ
    disp_size: (w, h) 表示画像サイズ
    """
    if not bbox or len(bbox) != 4:
        return False
    scale_x = disp_size[0] / orig_size[0]
    scale_y = disp_size[1] / orig_size[1]
    # クリック座標をオリジナル画像座標に逆変換
    orig_x = x / scale_x
    orig_y = y / scale_y
    return is_point_in_bbox(orig_x, orig_y, bbox)

class BoundingBox:
    def __init__(self, cid, cname, conf, xyxy, role=None):
        self.cid = cid
        self.cname = cname
        self.conf = conf
        self.xyxy = xyxy  # [x1, y1, x2, y2] (元画像座標)
        self.role = role

    def get_scaled_xyxy(self, orig_size, disp_size):
        """
        オリジナル画像座標xyxyを表示画像サイズにスケーリングして返す
        """
        scale_x = disp_size[0] / orig_size[0]
        scale_y = disp_size[1] / orig_size[1]
        x1, y1, x2, y2 = self.xyxy
        return [x1 * scale_x, y1 * scale_y, x2 * scale_x, y2 * scale_y]

    def contains_point(self, x, y, orig_size, disp_size):
        """
        表示画像上の座標(x, y)がこのバウンディングボックス内か判定
        """
        scale_x = disp_size[0] / orig_size[0]
        scale_y = disp_size[1] / orig_size[1]
        orig_x = x / scale_x
        orig_y = y / scale_y
        x1, y1, x2, y2 = self.xyxy
        left, right = sorted([x1, x2])
        top, bottom = sorted([y1, y2])
        return left <= orig_x <= right and top <= orig_y <= bottom

    def to_dict(self):
        return {
            "cid": self.cid,
            "cname": self.cname,
            "conf": self.conf,
            "xyxy": self.xyxy,
            "role": self.role
        }

    @staticmethod
    def from_dict(d):
        return BoundingBox(
            cid=d.get("cid"),
            cname=d.get("cname"),
            conf=d.get("conf"),
            xyxy=d.get("xyxy"),
            role=d.get("role")
        )
