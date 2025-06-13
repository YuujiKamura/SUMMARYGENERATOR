import pandas as pd
import os

# 入力ファイルと出力ファイルのパス
input_path = os.path.join(os.path.dirname(__file__), 'preset_roles_and_role_mapping.xlsx')
output_path = os.path.join(os.path.dirname(__file__), 'preset_roles_and_role_mapping_split.xlsx')

# role_mappingシートを読み込み
role_mapping = pd.read_excel(input_path, sheet_name='role_mapping')

# roles列をカンマで分割し、最大数を取得
split_roles = role_mapping['roles'].str.split(',')
max_roles = split_roles.map(len).max()

# 新しいカラム名を作成
role_columns = [f'role{i+1}' for i in range(max_roles)]

# rolesを分割して新しいDataFrameに展開
roles_expanded = split_roles.apply(lambda x: pd.Series(x, index=role_columns))

# 元のDataFrameと結合
result = pd.concat([role_mapping.drop('roles', axis=1), roles_expanded], axis=1)

# Excelに出力
with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
    result.to_excel(writer, sheet_name='role_mapping_split', index=False)

print(f'分割済みExcelを出力しました: {output_path}')
