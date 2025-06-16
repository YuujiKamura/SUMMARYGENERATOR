import os
import json

def load_image_cache_master(project_root):
    """
    画像リストマスターJSONを読み込む
    """
    master_path = os.path.join(project_root, 'data', 'image_preview_cache_master.json')
    with open(master_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def find_caption_board_images(image_data, limit=5, skip=3):
    """
    キャプションボード関連の画像を指定件数取得
    """
    caption_board_images = []
    for item in image_data:
        for bbox in item.get('bboxes', []):
            cname = bbox.get('cname', '') or ''
            role = bbox.get('role', '') or ''
            if ('caption_board' in cname or 'caption_board' in role):
                caption_board_images.append({
                    'filename': item['filename'],
                    'image_path': item['image_path'],
                    'bbox': bbox
                })
                break  # 同じ画像の重複を避ける
        if len(caption_board_images) >= skip + limit:
            break
    # skip件をスキップして、次のlimit件を返す
    return caption_board_images[skip:skip + limit]
