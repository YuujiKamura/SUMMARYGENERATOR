import pandas as pd
import sys
import os

class XlsxTool:
    def __init__(self, xlsx_path):
        self.xlsx_path = xlsx_path
        self.xls = pd.ExcelFile(xlsx_path)

    def list_sheets(self):
        print('--- シート一覧 ---')
        for name in self.xls.sheet_names:
            print(name)

    def show_head(self, sheet_name, n=10):
        df = pd.read_excel(self.xlsx_path, sheet_name=sheet_name)
        max_rows = 100
        if n is None or n <= 0:
            n = 10
        if n > max_rows:
            print(f'警告: 最大{max_rows}行までしか表示しません。')
            n = max_rows
        print(f'--- {sheet_name} の先頭{n}行 ---')
        print(df.head(n))

    def show_all_sheets_preview(self, max_rows=30, max_cols=5):
        print('--- 全シート プレビュー ---')
        for name in self.xls.sheet_names:
            print(f'--- {name} ---')
            df = pd.read_excel(self.xlsx_path, sheet_name=name)
            if df.shape[1] > max_cols:
                df = df.iloc[:, :max_cols]
            if df.shape[0] > max_rows:
                print(df.head(max_rows))
                print(f'... (以下省略: 全{df.shape[0]}行, {df.shape[1]}列中{df.shape[1]}列のみ表示) ...')
            else:
                print(df)
            print('')

    def split_roles_column(self, sheet_name='role_mapping', output_path=None):
        df = pd.read_excel(self.xlsx_path, sheet_name=sheet_name)
        split_roles = df['roles'].str.split(',')
        max_roles = split_roles.map(len).max()
        role_columns = [f'role{i+1}' for i in range(max_roles)]
        roles_expanded = split_roles.apply(lambda x: pd.Series(x, index=role_columns))
        result = pd.concat([df.drop('roles', axis=1), roles_expanded], axis=1)
        if not output_path:
            output_path = self.xlsx_path.replace('.xlsx', '_split.xlsx')
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            result.to_excel(writer, sheet_name=sheet_name+'_split', index=False)
        print(f'分割済みExcelを出力しました: {output_path}')

    def auto_process(self):
        print('--- [auto] 全シートプレビュー ---')
        self.show_all_sheets_preview(max_rows=10, max_cols=5)
        for name in self.xls.sheet_names:
            df = pd.read_excel(self.xlsx_path, sheet_name=name)
            if 'roles' in df.columns and df['roles'].str.contains(',').any():
                print(f'--- [auto] {name} シートのroles列を分割します ---')
                output_path = self.xlsx_path.replace('.xlsx', f'_{name}_split.xlsx')
                def safe_split(x):
                    if isinstance(x, str):
                        return x.split(',')
                    return [None] * max_roles
                split_roles = df['roles'].apply(safe_split)
                max_roles = split_roles.map(len).max()
                role_columns = [f'role{i+1}' for i in range(max_roles)]
                roles_expanded = split_roles.apply(lambda x: pd.Series(x + [None]*(max_roles-len(x)), index=role_columns))
                result = pd.concat([df.drop('roles', axis=1), roles_expanded], axis=1)
                with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                    sheet_name_str = str(name)
                    result.to_excel(writer, sheet_name=sheet_name_str+'_split', index=False)
                print(f'    → 分割済みExcelを出力: {output_path}')
            else:
                print(f'--- [auto] {name} シートは特別な処理なし ---')
        print('--- [auto] 完了 ---')

    def autosize_columns(self, writer, sheet_names):
        from openpyxl.utils import get_column_letter
        for sheet_name in sheet_names:
            ws = writer.book[sheet_name]
            for col in ws.columns:
                max_length = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    try:
                        if cell.value:
                            max_length = max(max_length, len(str(cell.value)))
                    except Exception:
                        pass
                ws.column_dimensions[col_letter].width = max_length + 2

    def split_by_category(self, sheet_name=None, output_path=None):
        if sheet_name is None:
            sheet_name = self.xls.sheet_names[0]
        df = pd.read_excel(self.xlsx_path, sheet_name=sheet_name)
        if 'category' not in df.columns:
            print(f'エラー: シート「{sheet_name}」に category 列がありません')
            return
        categories = df['category'].dropna().unique()
        if not output_path:
            output_path = self.xlsx_path.replace('.xlsx', '_by_category.xlsx')
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            sheet_names = []
            for cat in categories:
                cat_df = df[df['category'] == cat]
                safe_cat = str(cat).replace('/', '_').replace('\\', '_')[:31]
                cat_df.to_excel(writer, sheet_name=safe_cat, index=False)
                sheet_names.append(safe_cat)
            writer.book.save(output_path)  # 明示的に保存
            self.autosize_columns(writer, sheet_names)
        print(f'カテゴリーごとに分割したExcelを出力しました: {output_path}')

def main():
    if len(sys.argv) < 3:
        print('Usage: python xlsx_interactive_tool.py <xlsx_path> <command> [options]')
        print('Commands:')
        print('  list_sheets')
        print('  show_head <sheet_name> [n]')
        print('  show_all_sheets_preview [max_rows] [max_cols]')
        print('  split_roles [sheet_name] [output_path]')
        print('  auto')
        print('  split_by_category [sheet_name] [output_path]')
        sys.exit(1)
    xlsx_path = sys.argv[1]
    command = sys.argv[2]
    tool = XlsxTool(xlsx_path)
    if command == 'list_sheets':
        tool.list_sheets()
    elif command == 'show_head':
        if len(sys.argv) < 4:
            print('Usage: show_head <sheet_name> [n]')
            sys.exit(1)
        sheet_name = sys.argv[3]
        try:
            n = int(sys.argv[4]) if len(sys.argv) > 4 else 10
        except Exception:
            n = 10
        tool.show_head(sheet_name, n)
    elif command == 'show_all_sheets_preview':
        try:
            max_rows = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        except Exception:
            max_rows = 30
        try:
            max_cols = int(sys.argv[4]) if len(sys.argv) > 4 else 5
        except Exception:
            max_cols = 5
        tool.show_all_sheets_preview(max_rows, max_cols)
    elif command == 'split_roles':
        sheet_name = sys.argv[3] if len(sys.argv) > 3 else 'role_mapping'
        output_path = sys.argv[4] if len(sys.argv) > 4 else None
        tool.split_roles_column(sheet_name, output_path)
    elif command == 'auto':
        tool.auto_process()
    elif command == 'split_by_category':
        sheet_name = sys.argv[3] if len(sys.argv) > 3 else None
        output_path = sys.argv[4] if len(sys.argv) > 4 else None
        tool.split_by_category(sheet_name, output_path)
    else:
        print('Unknown command')

if __name__ == '__main__':
    main()
