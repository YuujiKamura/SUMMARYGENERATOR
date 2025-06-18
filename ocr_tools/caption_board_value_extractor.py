from typing import List, Dict, Any

from ocr_tools.ocr_value_pair_detector import (
    detect_value_pairs_from_boxes_enhanced,
)

from ocr_tools.ocr_keyword_config import PRIMARY_KEYWORDS, KEYWORDS


def extract_caption_board_values(
    texts_with_boxes: List[Dict[str, Any]],
    keyword_list: List[str] | None = None,
    value_pattern: str = r"([0-9]+\.?[0-9]*)\s*°?C?",
    max_y_diff: int = 50,
    min_x_diff: int = 5,
) -> Dict[str, Any]:
    """キャプションボード上の主要要素（場所・日付・台数）の値を抽出する共通ユーティリティ関数。

    Args:
        texts_with_boxes: DocumentAIなどから抽出した `{"text", "x", "y"}` リスト。
        keyword_list: 抽出対象キーワード。デフォルトは PRIMARY_KEYWORDS。
        value_pattern: 数値系値に対する正規表現パターン。
        max_y_diff: キーワードと値ボックスの y 方向許容差。
        min_x_diff: キーワードと値ボックスの x 方向最小差。

    Returns:
        dict: 以下のキーを持つ辞書を返す。
            - pairs:   detect_value_pairs_from_boxes_enhanced の生結果
            - location_value: str | None
            - date_value: str | None
            - count_value: str | None
    """
    if keyword_list is None:
        keyword_list = PRIMARY_KEYWORDS

    # value_pattern は将来拡張用に受け取るが現在は PairDetector 側で使用しない
    pairs = detect_value_pairs_from_boxes_enhanced(
        texts_with_boxes,
        keyword_list=keyword_list,
        max_y_diff=max_y_diff,
        min_x_diff=min_x_diff,
    )

    def _get_value(keyword: str):  # pylint: disable=missing-docstring
        return next((p["value"] for p in pairs if p["keyword"] == keyword), None)

    def _get_value_text(keyword: str):  # raw text including spaces
        return next((p["value_text"].strip() for p in pairs if p["keyword"] == keyword), None)

    location_val = _get_value("場所")
    if location_val is None:
        # 測点は value に格納された連結済み文字列を取得
        location_val = _get_value("測点")

    return {
        "pairs": pairs,
        "location_value": location_val,
        "date_value": _get_value("日付"),
        "count_value": _get_value("台数"),
    } 