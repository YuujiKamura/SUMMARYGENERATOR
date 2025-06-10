# --- Copied from src/caption_board_utils.py ---
import os
import shutil
import tempfile
from PIL import Image

def judge_caption_board_closeup(bboxes, img_w, img_h, threshold_closeup=0.3, threshold_kanrichi=0.8, image_path=None):
    for b in bboxes:
        role = b.get("role")
        if role and ("温度計" in role or "thermometer" in role):
            print("[判定ログ] 温度計/thermometerロール検出: 判定スキップ")
            return None, None
    if (not img_w or not img_h) and image_path:
        try:
            tmp_path = None
            if not os.path.exists(image_path):
                print(f"[判定ログ] 画像パスが存在しません: {image_path}")
                return None, None
            if not os.path.isfile(image_path):
                print(f"[判定ログ] 画像パスがファイルでありません: {image_path}")
                return None, None
            tmp_dir = tempfile.gettempdir()
            tmp_path = os.path.join(tmp_dir, os.path.basename(image_path))
            if image_path != tmp_path:
                shutil.copy2(image_path, tmp_path)
                open_path = tmp_path
            else:
                open_path = image_path
            with Image.open(open_path) as img:
                img_w, img_h = img.width, img.height
            if tmp_path and os.path.exists(tmp_path) and tmp_path != image_path:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            print(f"[判定ログ] 画像サイズ取得: width={img_w}, height={img_h}")
        except Exception as e:
            print(f"[画像サイズ取得失敗] {image_path}: {e}")
            return None, None
    if not img_w or not img_h:
        print(f"[判定ログ] 画像サイズ未取得: img_w={img_w}, img_h={img_h}")
        return None, None
    print("[判定ログ] bboxes全文:")
    import json
    print(json.dumps(bboxes, ensure_ascii=False, indent=2))
    caption_bboxes = []
    for b in bboxes:
        if (b.get("role") == "caption_board" or b.get("cname") == "caption_board"):
            box = b.get("bbox") or b.get("xyxy")
            if box:
                caption_bboxes.append(box)
    print(f"[判定ログ] caption_board候補数: {len(caption_bboxes)}")
    if not img_w or not img_h or not caption_bboxes:
        print(f"[判定ログ] 判定不能: img_w={img_w}, img_h={img_h}, caption_bboxes={caption_bboxes}")
        return None, None
    bbox = max(caption_bboxes, key=lambda box: abs((box[2]-box[0])*(box[3]-box[1])))
    x1, y1, x2, y2 = bbox
    bbox_area = abs((x2-x1)*(y2-y1))
    img_area = img_w * img_h
    ratio = bbox_area / img_area if img_area > 0 else 0
    print(f"[判定ログ] 最大caption_board bbox: {bbox}")
    print(f"[判定ログ] bbox_area={bbox_area}, img_area={img_area}, ratio={ratio:.4f}")
    print(f"[判定ログ] threshold_closeup={threshold_closeup}, threshold_kanrichi={threshold_kanrichi}")
    if ratio >= threshold_kanrichi:
        print(f"[判定ログ] 判定結果: 管理値 (ratio={ratio:.4f} >= {threshold_kanrichi})")
        return None, ratio
    if ratio >= threshold_closeup:
        print(f"[判定ログ] 判定結果: 接写 (ratio={ratio:.4f} >= {threshold_closeup})")
        return True, ratio
    print(f"[判定ログ] 判定結果: 全景 (ratio={ratio:.4f} < {threshold_closeup})")
    return False, ratio
