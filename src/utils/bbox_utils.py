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

# --- テスト関数 ---
def test_is_point_in_bbox():
    print("[基本パターン]")
    test_cases = [
        (5, 5, [0, 0, 10, 10], True),
        (0, 0, [0, 0, 10, 10], True),
        (10, 10, [0, 0, 10, 10], True),
        (11, 5, [0, 0, 10, 10], False),
        (5, -1, [0, 0, 10, 10], False),
        (0, 5, [0, 0, 0, 10], True),
        (5, 0, [0, 0, 10, 0], True),
        (0, 0, [0, 0, 0, 0], True),
        (5, 5, [10, 10, 0, 0], True),
        (5, 5, [-10, -10, 10, 10], True),
        (20, 20, [0, 0, 10, 10], False),
    ]
    for i, (x, y, bbox, expected) in enumerate(test_cases):
        result = is_point_in_bbox(x, y, bbox)
        print(f"Test {i}: point=({x},{y}), bbox={bbox} => {result} (expected {expected}) {'OK' if result==expected else 'NG'}")

    print("\n[複数ボックス・重なりパターン]")
    bboxes = [[0,0,10,10], [5,5,15,15], [20,20,30,30]]
    points = [(7,7), (12,12), (25,25), (0,0), (16,16)]
    expected = [[True, True, False], [False, True, False], [False, False, True], [True, False, False], [False, False, False]]
    for i, pt in enumerate(points):
        res = [is_point_in_bbox(pt[0], pt[1], bb) for bb in bboxes]
        print(f"Point {pt} in bboxes: {res} (expected {expected[i]}) {'OK' if res==expected[i] else 'NG'}")

    print("\n[スケール変換パターン]")
    orig_size = (100, 100)
    disp_size = (50, 50)  # 0.5倍に縮小
    bbox = [20, 20, 80, 80]
    # 表示画像上の座標(25,25)はオリジナル(50,50)に相当
    result = is_point_in_bbox_scaled(25, 25, bbox, orig_size, disp_size)
    print(f"Scaled: point=(25,25) in bbox={bbox} orig={orig_size} disp={disp_size} => {result} (expected True) {'OK' if result==True else 'NG'}")
    # 端
    result = is_point_in_bbox_scaled(40, 40, bbox, orig_size, disp_size)
    print(f"Scaled: point=(40,40) in bbox={bbox} orig={orig_size} disp={disp_size} => {result} (expected True) {'OK' if result==True else 'NG'}")
    # 外
    result = is_point_in_bbox_scaled(49, 49, bbox, orig_size, disp_size)
    print(f"Scaled: point=(49,49) in bbox={bbox} orig={orig_size} disp={disp_size} => {result} (expected False) {'OK' if result==False else 'NG'}")
    # 縮小率が異なる場合
    disp_size2 = (200, 100)  # x2, y1
    result = is_point_in_bbox_scaled(160, 50, bbox, orig_size, disp_size2)
    print(f"Scaled: point=(160,50) in bbox={bbox} orig={orig_size} disp={disp_size2} => {result} (expected True) {'OK' if result==True else 'NG'}")

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

if __name__ == "__main__":
    print("--- is_point_in_bbox ユニットテスト ---")
    test_is_point_in_bbox() 