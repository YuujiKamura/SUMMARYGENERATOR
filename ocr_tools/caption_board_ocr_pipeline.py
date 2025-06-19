import os
import json
from datetime import datetime
from ocr_tools.ocr_value_extractor import (
    extract_texts_with_boxes_from_documentai_result,
    extract_measurement_points_from_boxes,
    load_ocr_cache,
    save_ocr_cache,
    copy_to_local,
    get_cache_path,
)
from ocr_tools.caption_board_value_extractor import extract_caption_board_values
from ocr_tools.caption_board_ocr_filter import should_skip_ocr_by_size_and_aspect
from google.cloud.documentai_v1.types import Document
from google.protobuf.json_format import MessageToDict
from src.utils.image_cache_utils import get_image_cache_path, load_image_cache
import logging
import re

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s', encoding='utf-8')

TIME_WINDOW_SEC = 300  # 5分以内を隣接とみなす

# ---------------------------------------------------------------------------
# Helper: "No. 26" → "No.26" など、No. の後ろの空白を除去
# 全角スペースやタブも対象
# ---------------------------------------------------------------------------

_NO_PATTERN = re.compile(r"(No\.?)[\s\u3000]+(\d+)", flags=re.IGNORECASE)

def _normalize_no(text: str | None) -> str | None:
    if not text:
        return text
    return _NO_PATTERN.sub(r"\1\2", text)

def compute_bbox_metrics(bbox):
    """bbox: [x1, y1, x2, y2] or dict から width, height, area を返す（Noneは0扱い）"""
    if isinstance(bbox, dict):
        xyxy = bbox.get('xyxy') or [bbox.get('x1'), bbox.get('y1'), bbox.get('x2'), bbox.get('y2')]
    else:
        xyxy = bbox
    if xyxy and len(xyxy) == 4:
        x1, y1, x2, y2 = [(v if v is not None else 0) for v in xyxy]
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        area = width * height
        return {'width': width, 'height': height, 'area': area}
    return {'width': 0, 'height': 0, 'area': 0}

def process_caption_board_image(img_info, engine, ocr_tools_dir, src_dir):
    """
    1画像分のOCR・値抽出・AAレイアウト・判定を行い、結果dictを返す
    img_info: {'filename', 'image_path', 'bbox'}
    engine: DocumentAIエンジン
    ocr_tools_dir, src_dir: パス解決用    """
    bbox = img_info['bbox']
    logging.info(f"[DEBUG] img_info['bbox']: {bbox}")
    # 参考情報（ログ用途）：ロール・クラス名・サイズ
    role = bbox.get('role', '') or 'None'
    cname = bbox.get('cname', '')
    size = f"{bbox.get('width', '?')}x{bbox.get('height', '?')}"
    # いまのところ変数未使用だがロギングに使う可能性があるため抑制コメントを付与
    _ = (role, cname, size)
    # logging.info(f"ロール: {role}")
    # logging.info(f"クラス: {cname}")
    # logging.info(f"画像サイズ: {size}")

    # SHAハッシュベースのキャッシュファイルパスを取得
    image_path = img_info['image_path']
    cache_dir = os.path.join(src_dir, 'image_preview_cache')
    json_file_path = get_image_cache_path(image_path, cache_dir)
    # preset_roles_path = os.path.join(ocr_tools_dir, 'preset_roles.json')  # 未使用だが将来用途で残す可能性あり
    
    # --- ネットワーク/リムーバブルドライブ対策：ローカルコピーを取得 ---
    local_image_path = copy_to_local(image_path)
    if local_image_path is None or not os.path.exists(local_image_path):
        logging.warning(f"[SKIP] 画像のローカルコピー取得に失敗: {image_path}")
        return None
    
    if not os.path.exists(json_file_path):
        logging.warning(f"[SKIP] キャッシュファイルが見つかりません: {json_file_path}")
        return None
    cache_data = load_image_cache(image_path, cache_dir, return_full=True)
    # cache_dataがtupleの場合（(meta, bboxes)など）とdictの場合で分岐
    if isinstance(cache_data, tuple):
        cache_meta = cache_data[0] if len(cache_data) > 0 else None
        cache_bboxes = cache_data[1] if len(cache_data) > 1 else None
        if not cache_bboxes:
            logging.warning(f"[SKIP] キャッシュデータ(bboxes)が無効です: {json_file_path} 内容: {str(cache_data)[:200]}")
            return None
        logging.info(f"[CACHE] キャッシュ読込成功(tuple): {json_file_path}")
        image_path = cache_meta.get('image_path', image_path) if isinstance(cache_meta, dict) else image_path
    elif isinstance(cache_data, dict):
        if not cache_data.get('bboxes'):
            logging.warning(f"[SKIP] キャッシュデータが無効です: {json_file_path} 内容: {str(cache_data)[:200]}")
            return None
        logging.info(f"[CACHE] キャッシュ読込成功(dict): {json_file_path}")
        image_path = cache_data.get('image_path', image_path)
    else:
        logging.warning(f"[SKIP] キャッシュデータの型が不明: {json_file_path} 内容: {str(cache_data)[:200]}")
        return None
    if not image_path or not os.path.exists(image_path):
        logging.error("画像ファイルが見つかりません")
        return None

    metrics = compute_bbox_metrics(bbox)
    img_w = metrics['width'] or 1280
    img_h = metrics['height'] or 960
    area = metrics['area']

    # --- ペアマッチングの距離しきい値をボード高さに応じてスケール調整 ---
    baseline_height = 400  # 経験的基準（従来サイズ）
    scale = (img_h / baseline_height) if baseline_height > 0 else 1.0
    # 最小0.8倍、最大3倍程度に制限して極端な値を抑制
    scale = max(0.8, min(scale, 3.5))
    dyn_max_y = int(30 * scale)
    dyn_min_x = int(5 * scale)

    # --- OCRスキップ判定前にサイズ情報をログ出力 ---
    logging.info(f"[ボードサイズ] {os.path.basename(image_path)} width={img_w}, height={img_h}, area={area}")

    # RIMG8573.JPG の場合はピクセル値→mm換算で特別ログ出力
    if os.path.basename(image_path).upper() == "RIMG8573.JPG":
        # 仮に1ピクセル=0.1017mm換算（例）
        px_to_mm = 0.1017
        width_mm = img_w * px_to_mm
        height_mm = img_h * px_to_mm
        area_mm2 = width_mm * height_mm
        logging.info(f"[ボードサイズ] RIMG8573.JPG width={width_mm:.2f}mm, height={height_mm:.2f}mm, area={area_mm2:.2f}mm^2")

    # --- OCRスキップ判定 ---
    skip_info = should_skip_ocr_by_size_and_aspect(img_w, img_h, area)
    if skip_info["skip"]:
        reason = skip_info["reason"]
        # logging.info(f"[SKIP_OCR] {reason} → OCRを実行しません")
        return {
            'filename': img_info['filename'],
            'image_path': img_info['image_path'],
            'location_value': None,
            'date_value': None,
            'count_value': None,
            'all_pairs': [],
            'bbox': img_info['bbox'],
            'ocr_skipped': True,
            'ocr_skip_reason': reason,
        }

    # OCRキャッシュ確認
    ocr_cache_path = get_cache_path(local_image_path, ocr=True)
    ocr_cache = load_ocr_cache(local_image_path)

    if ocr_cache is not None:
        # INFOレベルでキャッシュヒットをログ
        logging.info(f"[CACHE] OCRキャッシュ読込成功: {ocr_cache_path}")
        document = Document.from_json(json.dumps(ocr_cache['document']))
    else:
        logging.info(f"[CACHE] OCRキャッシュなし (miss): {ocr_cache_path} → 新規OCR実行")
        # logging.info("[OCR] 新規OCR実行")
        with open(local_image_path, "rb") as _f:
            img_bytes = _f.read()
        result = engine.client.process_document(request={
            "name": engine.processor_name,
            "raw_document": {"content": img_bytes, "mime_type": "image/jpeg"}
        })
        document = result.document
        save_ocr_cache(
            local_image_path,
            {"document": MessageToDict(document._pb)},
            img_info['image_path'],
        )
    # テキストボックス抽出
    texts_with_boxes = extract_texts_with_boxes_from_documentai_result(document, img_w, img_h)
    logging.debug(f"[BOXES] {texts_with_boxes}")
    # 近接結合は行わず、そのまま使用
    measurement_points = extract_measurement_points_from_boxes(texts_with_boxes, y_margin=25)
    # logging.debug(f"抽出されたテキストボックス数: {len(texts_with_boxes)}")
    
    # ペアマッチング実行
    extracted = extract_caption_board_values(
        texts_with_boxes,
        keyword_list=None,
        max_y_diff=dyn_max_y,
        min_x_diff=dyn_min_x,
    )
    pairs = extracted["pairs"]
    logging.debug(f"[PAIRS] {pairs}")
    
    # 測点値が抽出できた場合はlocation_value候補として優先
    location_value = None
    if measurement_points:
        # 最初のマッチを優先（複数ある場合は要検討）
        location_value = measurement_points[0]['matched_text']
    else:
        location_value = extracted["location_value"]
    date_value = extracted["date_value"]
    count_value = extracted["count_value"]

    # --- No.XX 形式のスペース除去 ---------------------------------------
    location_value = _normalize_no(location_value)

    # どのペアで決まったかを記録
    matched_location_pair = next((p for p in pairs if p["keyword"] == "場所" and str(p["value"]) == str(location_value)), None)
    matched_date_pair = next((p for p in pairs if p["keyword"] == "日付" and str(p["value"]) == str(date_value)), None)
    matched_count_pair = next((p for p in pairs if p["keyword"] == "台数" and str(p["value"]) == str(count_value)), None)

    # 検出結果の要約
    results_summary = []
    if location_value:
        results_summary.append(f"場所:{location_value}")
    if date_value:
        results_summary.append(f"日付:{date_value}")
    if count_value:
        results_summary.append(f"台数:{count_value}")

    # 判定根拠をmetaから抽出
    meta_info = {
        'matched_location_pair': matched_location_pair,
        'matched_date_pair': matched_date_pair,
        'matched_count_pair': matched_count_pair,
    }
    summary = ", ".join(results_summary) if results_summary else "検出なし"

    # ファイルの更新時刻を取得（撮影時刻の代替）
    try:
        mtime = os.path.getmtime(image_path)
        time_str = datetime.fromtimestamp(mtime).strftime("%m/%d %H:%M")
    except:
        time_str = "??/?? ??:??"
    full_image_path = image_path  # フルパスを使用

    logging.info(f"OCR結果 | {full_image_path} ({time_str}) | {summary} | 判定根拠: {meta_info}")

    # --- キーワード検出フラグ ---
    LOG_KEYWORDS = ["場所", "測点", "日付", "台数"]
    keyword_found = any(
        any(kw in (b.get("text", "")) for kw in LOG_KEYWORDS)
        for b in texts_with_boxes
    )

    # 結果dict
    return {
        'filename': img_info['filename'],
        'image_path': img_info['image_path'],
        'location_value': location_value,
        'date_value': date_value,
        'count_value': count_value,
        'all_pairs': pairs,
        'bbox': img_info['bbox'],
        'meta': meta_info,
        'keyword_found': keyword_found,
        'pairs_found': bool(pairs)
    }
