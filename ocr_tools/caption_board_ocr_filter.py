from typing import Optional, Dict, Any

def should_skip_ocr_by_size_and_aspect(
    width: Optional[int], height: Optional[int], area: Optional[int],
    min_area: int = 100_000
) -> Dict[str, Any]:
    """
    OCRをスキップすべきかどうかを判定する純粋関数。
    - 横幅 < 縦幅 ならスキップ（ボードは横長前提）
    - 面積が min_area 未満ならスキップ
    戻り値: {skip: bool, reason: str}
    """
    if width is None or height is None or area is None:
        return {"skip": True, "reason": "サイズ情報不足"}
    if width < height:
        return {"skip": True, "reason": "縦長ボード(横幅<縦幅)"}
    if area < min_area:
        return {"skip": True, "reason": f"小サイズ({area} < {min_area})"}
    return {"skip": False, "reason": ""}
