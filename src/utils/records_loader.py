import json
import os

def load_records_from_json(json_path):
    """
    辞書JSONファイル（参照型・従来型どちらも対応）から全レコードをリストで返す
    """
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    records = data.get("records", [])
    # 参照型（パスリスト）なら各ファイルを読み込む
    if records and isinstance(records[0], str):
        base_dir = os.path.dirname(json_path)
        loaded = []
        for rec_path in records:
            if os.path.isabs(rec_path):
                rec_abspath = rec_path
            else:
                rec_abspath = os.path.normpath(os.path.join(base_dir, rec_path.lstrip('./\\')))
            with open(rec_abspath, encoding="utf-8") as rf:
                rec_data = json.load(rf)
                if not isinstance(rec_data, dict):
                    print(f"[WARN] {rec_abspath} の内容がdictではありません: {type(rec_data)}")
                    continue
                loaded.append(rec_data)
        result = loaded
    # 従来型（リスト of dict）
    else:
        result = records
    print("DEBUG: load_records_from_json return type:", type(result), "first item type:", type(result[0]) if result else None)
    return result


def save_records_to_json(json_path, records, as_reference=False):
    """
    辞書JSONファイル（参照型・従来型どちらも対応）として保存
    as_reference=Trueなら個別ファイル分割＋パスリスト保存、Falseなら従来型
    """
    if as_reference:
        # 個別ファイルに分割保存
        base_dir = os.path.join(os.path.dirname(json_path), "records")
        os.makedirs(base_dir, exist_ok=True)
        path_list = []
        for i, rec in enumerate(records, 1):
            fname = f"rec_{i:04d}.json"
            rec_path = os.path.join(base_dir, fname)
            with open(rec_path, "w", encoding="utf-8") as f:
                json.dump(rec, f, ensure_ascii=False, indent=2)
            path_list.append(f"records/{fname}")
        # 上位JSONをパスリストで保存
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["records"] = path_list
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    else:
        # 従来型
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["records"] = records
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2) 