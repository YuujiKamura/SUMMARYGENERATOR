def format_date(date_str: str) -> str:
    """
    日付文字列をフォーマット（例: "5/30" → "5月30日"）
    """
    if not date_str:
        return ""
    if '/' in date_str:
        parts = date_str.split('/')
        if len(parts) == 2:
            month, day = parts
            return f"{month}月{day}日"
    return date_str
