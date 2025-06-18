import os
import json
from datetime import datetime
from caption_board_ocr_utils import format_date
import logging

# 簡潔なスキップ理由変換
def _short_reason(reason: str) -> str:
    if not reason:
        return "OCRスキップ"
    if "縦長" in reason:
        return "縦長ボックス"
    if "小サイズ" in reason:
        return "ボード極小"
    return "OCRスキップ"


def print_extracted_results_summary(extracted_results):
    # --- 統計 ------------------------------------------------------
    locations = sum(1 for r in extracted_results if _get_final_location(r))
    kw_cnt = sum(1 for r in extracted_results if r.get('keyword_found'))
    pair_cnt = sum(1 for r in extracted_results if r.get('pairs_found'))
    summary_msg = (
        f"総画像数: {len(extracted_results)}件 | 測点取得: {locations}件 | KWあり: {kw_cnt}件 | PAIR: {pair_cnt}件"
    )
    logging.info(f"=== {summary_msg}")
    # --- 全画像の結果一覧 ------------------------------------------
    logging.info("[全画像 最終結果]:")
    for i, result in enumerate(extracted_results, 1):
        filename = _get_original_filename(result)
        time_str = _format_capture_time(result.get('capture_time'))
        # SurveyPointのget_display_valueを使う
        sp = None
        if hasattr(result, 'get_display_value'):
            sp = result
        elif hasattr(result, 'survey_point') and hasattr(result['survey_point'], 'get_display_value'):
            sp = result['survey_point']
        if sp:
            display_value = sp.get_display_value()
        else:
            # fallback: 旧ロジック
            meta = result.get('meta', {})
            matched_location_pair = meta.get('matched_location_pair')
            matched_date_pair = meta.get('matched_date_pair')
            matched_count_pair = meta.get('matched_count_pair')
            if matched_location_pair:
                display_value = matched_location_pair.get('value', '')
            elif matched_date_pair and matched_count_pair:
                date_val = matched_date_pair.get('value', '')
                count_val = matched_count_pair.get('value', '')
                display_value = f"{date_val} {count_val}"
            else:
                display_value = (
                    _get_final_location(result) or
                    _get_date_count_info(result) or
                    _get_status_info(result) or
                    "情報なし"
                )

        meta = result.get('meta', {})
        decision_source = meta.get('decision_source')
        matched_location_pair = meta.get('matched_location_pair')
        matched_date_pair = meta.get('matched_date_pair')
        matched_count_pair = meta.get('matched_count_pair')
        matched_info_lines = []  # NEW: collect additional lines for detailed info
        def _pair_to_line(pair, label):
            if not pair:
                return ""
            kw = pair.get('keyword', '')
            val = pair.get('value', '')
            # value_text は詳細として扱うが長いので省略
            return f"{label}: kw={kw}, val={val}"
        # --- build detailed lines ------------------------------
        if matched_location_pair:
            matched_info_lines.append(_pair_to_line(matched_location_pair, "場所"))
        if matched_date_pair:
            matched_info_lines.append(_pair_to_line(matched_date_pair, "日付"))
        if matched_count_pair:
            matched_info_lines.append(_pair_to_line(matched_count_pair, "台数"))

        # KW/PAIR status flags
        status_flags = []
        if result.get('keyword_found'):
            status_flags.append('KW')
        if result.get('pairs_found'):
            status_flags.append('PAIR')
        # 補完フラグ
        if result.get('inferred_location') or decision_source == 'inferred':
            status_flags.append('補完')
        status_str = f" [{' / '.join(status_flags)}]" if status_flags else ""

        line_msg = f"{i:2d}. {filename} ({time_str}): {display_value}{status_str}"
        logging.info(f"  {line_msg}")

        # 追加行を出力（存在する場合）
        for detail in matched_info_lines:
            logging.info(f"      - {detail}")

        # decision_source があり、かつペア詳細が無い場合だけ情報源を出力
        if decision_source and not matched_info_lines:
            src_msg = f"      - source: {decision_source}"
            logging.info(src_msg)

    # --- 1行サマリー ---------------------------------------------
    total = len(extracted_results)
    loc_ok = sum(1 for r in extracted_results if _get_final_location(r))
    inferred = sum(1 for r in extracted_results if r.get('inferred_location'))
    logging.info(
        f"=== [SUMMARY] 総画像={total} | 測点取得={loc_ok} (補完={inferred}) | KW={kw_cnt} | PAIR={pair_cnt}"
    )
    logging.info("=" * 70)

def _get_date_count_info(result):
    """日付・台数情報を整形して返す"""
    date_val = result.get('date_value')
    count_val = result.get('count_value')
    if date_val and count_val:
        formatted_date = format_date(date_val)
        return f"{formatted_date} {count_val}"
    return None

def _get_status_info(result):
    """スキップ理由などのステータス情報を返す"""
    if result.get('ocr_skipped'):
        return _short_reason(result.get('ocr_skip_reason', ''))
    return None

def save_success_results(extracted_results, project_root, log_prefix="caption_board_ocr_success"):
    """
    成功した抽出結果のみをlogsディレクトリに保存
    """
    success_results = [r for r in extracted_results if r.get('location_value') or (r.get('date_value') and r.get('count_value'))]
    if success_results:
        log_dir = os.path.join(project_root, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        out_path = os.path.join(log_dir, f'{log_prefix}_{ts}.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(success_results, f, ensure_ascii=False, indent=2, default=str)
        logging.info(f"[INFO] 検出OK {len(success_results)} 件を {out_path} に保存しました")
    else:
        logging.info("[INFO] 成功検出はありませんでした (ファイル保存スキップ)")

def print_final_stats(results):
    """最終件数サマリ: 抽出 / 推定 / 未取得 を集計して表示"""
    total = len(results)
    explicit_loc = inferred_loc = date_only = 0
    for r in results:
        if r.get('location_value'):
            explicit_loc += 1
        elif r.get('inferred_location'):
            inferred_loc += 1
        elif r.get('date_value') and r.get('count_value'):
            date_only += 1

    missing = total - explicit_loc - inferred_loc - date_only
    logging.info(f"総処理ファイル数: {total}")
    logging.info(f"測点名称検出数 (OCR成功): {explicit_loc}")
    logging.info(f"測点名称補完数     : {inferred_loc}")
    logging.info(f"未取得            : {missing}")
    logging.info(f"日付・台数検出数  : {date_only}")

def list_caption_board_images(image_data, caption_board_images):
    """
    キャプションボード画像の一覧をターミナルに表示
    """
    logging.info(f"=== キャプションボード画像一覧 ({len(caption_board_images)}件) ===")
    for i, img_info in enumerate(caption_board_images):
        bbox = img_info['bbox']
        role = bbox.get('role', '') or 'None'
        cname = bbox.get('cname', '')
        size = f"{bbox.get('width', '?')}x{bbox.get('height', '?')}"
        logging.info(f"{i:2d}. {os.path.basename(img_info['filename'])}")
        logging.info(f"    パス: {img_info['image_path']}")
        logging.info(f"    ロール: {role}")
        logging.info(f"    クラス: {cname}")
        logging.info(f"    サイズ: {size}")
        logging.info("")

def _get_original_filename(result):
    """結果辞書から元の画像ファイル名を取得"""
    image_path = result.get('image_path', '')
    if image_path:
        # パスから実際のファイル名を抽出
        return os.path.basename(image_path)
    else:
        # フォールバック: result['filename']を使用
        filename = result.get('filename', 'unknown')
        # ハッシュ化されたファイル名の場合は、より読みやすい形式に変換
        if len(filename) > 40 and filename.endswith('.json'):
            return f"画像#{filename[:8]}..."
        return filename

def _format_capture_time(capture_time):
    """撮影時刻をフォーマットして表示用文字列に変換"""
    if capture_time is None:
        return "撮影時刻不明"
    try:
        if isinstance(capture_time, datetime):
            dt = capture_time
        elif isinstance(capture_time, (int, float)):
            dt = datetime.fromtimestamp(capture_time)
        else:
            return "撮影時刻不明"
        return dt.strftime("%m/%d %H:%M")
    except Exception as e:
        logging.debug(f"[DEBUG] 撮影時刻フォーマットエラー: {e}")
        return "撮影時刻不明"

def _is_incomplete_location(location_value):
    """測点名が不完全かどうかを判定"""
    if not location_value or location_value.strip() == "":
        return False
    
    location_value = location_value.strip()
    
    # 「No.」や「No」だけの場合
    if location_value.lower() in ['no.', 'no', 'na', 'n/a']:
        return True
    
    # 数字だけの場合
    if location_value.isdigit():
        return True
    
    # 短すぎる場合（2文字以下）
    if len(location_value) <= 2:
        return True
    
    # 一般的な不完全なパターン
    incomplete_patterns = ['小山', '大山', '山', '川', '橋', '駅', '町']
    if location_value in incomplete_patterns:
        return True
    
    return False



def _get_final_location(result):
    """最終的な場所情報を取得（補完後の結果を優先）"""
    inferred_location = result.get('inferred_location')
    location_value = result.get('location_value')
    
    # 補完結果があればそれを使用、なければ元の検出結果
    return inferred_location or location_value

def get_final_location_list(extracted_results):
    """
    抽出結果のリストから、最終的な測点名のリストを生成して返す。
    測点名が存在しない結果は無視される。
    """
    final_locations = []
    for result in extracted_results:
        final_location = _get_final_location(result)
        if final_location:
            final_locations.append(final_location)
    return final_locations
