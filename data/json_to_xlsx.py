import json
import os
import pandas as pd
from pathlib import Path
import sys

# 使い方: python json_to_xlsx.py input.json output.xlsx

def json_to_xlsx(json_files, xlsx_path):
    # json_files: {シート名: jsonファイルパス}
    with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
        for sheet_name, json_path in json_files.items():
            with open(json_path, encoding='utf-8') as f:
                data = json.load(f)
            # dictなら1行、listなら複数行
            if isinstance(data, dict):
                df = pd.DataFrame([data])
            else:
                df = pd.DataFrame(data)
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    print(f'Excelファイルを作成しました: {xlsx_path}')

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='複数のjsonファイルをExcelの各シートに変換')
    parser.add_argument('--output', type=str, required=True, help='出力するxlsxファイルのパス')
    parser.add_argument('--sheet', action='append', nargs=2, metavar=('SHEET_NAME', 'JSON_PATH'), required=True,
                        help='シート名とjsonファイルパスのペア。例: --sheet preset_roles preset_roles.json')
    args = parser.parse_args()

    json_files = {sheet: path for sheet, path in args.sheet}
    json_to_xlsx(json_files, args.output)

    # 以下、default_records.jsonの処理
    base_dir = os.path.dirname(__file__)
    default_records_path = os.path.join(base_dir, 'default_records.json')
    with open(default_records_path, encoding='utf-8') as f:
        default_records = json.load(f)

    # records配下の全レコードをパース
    records_dir = os.path.join(base_dir, 'records')
    records_data = []
    for rec_path in default_records['records']:
        abs_path = os.path.join(base_dir, rec_path)
        with open(abs_path, encoding='utf-8') as f:
            rec = json.load(f)
        rec['record_file'] = rec_path  # どのファイルかも記録
        records_data.append(rec)
    df_records = pd.DataFrame(records_data)

    # photo_categoriesもシート化
    df_categories = pd.DataFrame({'photo_category': default_records['photo_categories']})

    # Excel出力
    out_path = os.path.join(base_dir, 'default_records_all.xlsx')
    with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
        df_records.to_excel(writer, sheet_name='records', index=False)
        df_categories.to_excel(writer, sheet_name='photo_categories', index=False)
    print(f'Excelファイルを作成しました: {out_path}')
