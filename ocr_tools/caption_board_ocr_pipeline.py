import os
import json
from ocr_value_extractor import process_image_json, extract_texts_with_boxes_from_documentai_result, get_image_size_local, load_ocr_cache, save_ocr_cache
from ocr_aa_layout import print_ocr_aa_layout
from caption_board_value_extractor import extract_caption_board_values
from google.cloud.documentai_v1.types import Document
from google.protobuf.json_format import MessageToDict

def process_caption_board_image(img_info, engine, ocr_tools_dir, src_dir):
    """
    1画像分のOCR・値抽出・AAレイアウト・判定を行い、結果dictを返す
    img_info: {'filename', 'image_path', 'bbox'}
    engine: DocumentAIエンジン
    ocr_tools_dir, src_dir: パス解決用
    """
    bbox = img_info['bbox']
    role = bbox.get('role', '') or 'None'
    cname = bbox.get('cname', '')
    size = f"{bbox.get('width', '?')}x{bbox.get('height', '?')}"
    print(f"ロール: {role}")
    print(f"クラス: {cname}")
    print(f"画像サイズ: {size}")

    cache_dir = os.path.join(src_dir, 'image_preview_cache')
    json_file_path = os.path.join(cache_dir, img_info['filename'])
    preset_roles_path = os.path.join(ocr_tools_dir, 'preset_roles.json')

    if not os.path.exists(json_file_path):
        print(f"[SKIP] キャッシュファイルが見つかりません: {json_file_path}")
        return None

    with open(json_file_path, encoding='utf-8') as f:
        data = json.load(f)
    image_path = data.get('image_path', '')
    if not image_path or not os.path.exists(image_path):
        print("画像ファイルが見つかりません")
        return None

    img_w = bbox.get('width', 1280)
    img_h = bbox.get('height', 960)

    # OCRキャッシュ確認
    ocr_cache = load_ocr_cache(image_path)
    if ocr_cache is not None:
        print("[CACHE] OCRキャッシュヒット")
        document = Document.from_json(json.dumps(ocr_cache['document']))
    else:
        print("[OCR] 新規OCR実行")
        result = engine.client.process_document(request={
            "name": engine.processor_name,
            "raw_document": {"content": open(image_path, "rb").read(), "mime_type": "image/jpeg"}
        })
        document = result.document
        save_ocr_cache(image_path, {"document": MessageToDict(document._pb)})

    # テキストボックス抽出
    texts_with_boxes = extract_texts_with_boxes_from_documentai_result(document, img_w, img_h)
    print(f"抽出されたテキストボックス数: {len(texts_with_boxes)}")

    # ペアマッチング実行
    extracted = extract_caption_board_values(
        texts_with_boxes,
        keyword_list=["場所", "日付", "台数"],
        max_y_diff=50,
        min_x_diff=5,
    )
    pairs = extracted["pairs"]
    location_value = extracted["location_value"]
    date_value = extracted["date_value"]
    count_value = extracted["count_value"]

    print(f"検出されたペア数: {len(pairs)}")
    # AAレイアウト表示
    if pairs:
        highlight_boxes = []
        for pair in pairs:
            highlight_boxes.append(pair['keyword_box'])
            highlight_boxes.append(pair['value_box'])
        print("\n[AAレイアウト - ペアマッチング結果]")
        print_ocr_aa_layout(texts_with_boxes, img_w, img_h, highlight_boxes=highlight_boxes)
    else:
        print("\n[AAレイアウト - 全テキスト]")
        print_ocr_aa_layout(texts_with_boxes, img_w, img_h)

    # 結果dict
    return {
        'filename': img_info['filename'],
        'image_path': img_info['image_path'],
        'location_value': location_value,
        'date_value': date_value,
        'count_value': count_value,
        'all_pairs': pairs
    }
