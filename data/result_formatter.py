# result_formatter.py
"""
マッチ結果の出力整形を担当
"""
def format_match_result(record, found, match_val):
    if match_val.isdigit():
        reason = f"found={len(found)}/{match_val}"
    elif match_val == 'any':
        reason = f"found={len(found)}>0"
    elif match_val == 'all':
        reason = f"found={len(found)}/all"
    else:
        reason = "found=?"
    return f"{reason} {record['key']}"
