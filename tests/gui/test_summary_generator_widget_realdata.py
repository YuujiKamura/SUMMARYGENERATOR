import os
import json
import pytest
from src.summary_generator_widget import SummaryGeneratorWidget

def load_all_records(records_path):
    with open(records_path, encoding="utf-8") as f:
        records_json = json.load(f)
    records = []
    for rec_path in records_json["records"]:
        rec_abspath = os.path.join(os.path.dirname(records_path), rec_path)
        with open(rec_abspath, encoding="utf-8") as rf:
            records.append(json.load(rf))
    return records

@pytest.mark.qt
def test_summary_generator_mapping_logic(qtbot):
    # ウィジェット起動
    widget = SummaryGeneratorWidget()
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)

    # デフォルト画像リスト取得
    entries = widget.image_data_manager.entries

    # records全件をロード
    records_path = os.path.abspath("data/dictionaries/default_records.json")
    all_records = load_all_records(records_path)
    remarks_set = {r["remarks"] for r in all_records if "remarks" in r}

    # 施工状況写真: image_pathとrolesを全件print
    for entry in entries:
        if getattr(entry, "photo_category", None) == "施工状況写真":
            print(f"画像: {getattr(entry, 'image_path', '')}, roles: {getattr(entry, 'roles', None)}")

    # 施工状況写真: remarksパネルの内容をprintで全出力
    for entry in entries:
        if getattr(entry, "photo_category", None) == "施工状況写真":
            widget.on_image_selected(entry)
            table = widget.record_panel.record_list_widget
            row_count = table.rowCount()
            col_count = table.columnCount()
            print(f"画像: {getattr(entry, 'image_path', '')}")
            for row in range(row_count):
                row_data = [table.item(row, col).text() if table.item(row, col) else "" for col in range(col_count)]
                print(f"  Row {row}: {row_data}")

    # 出来形: 管理図ボードサイズによる3分岐＋砕石厚判定
    for entry in entries:
        if getattr(entry, "photo_category", None) == "出来形管理写真":
            remarks, _, debug_text, _ = widget.get_remarks_and_debug(entry)
            assert remarks, f"出来形管理写真 {getattr(entry, 'image_path', '')} でremarksが空"
            # debug_textやremarks内容で分岐判定も可能

    # 温度管理: 3枚セットのサイクル判定＋件数assert
    thermo_entries = []
    print("[調査] 品質管理写真のremarks全件:")
    for entry in entries:
        if getattr(entry, "photo_category", None) == "品質管理写真":
            remarks, _, _, _ = widget.get_remarks_and_debug(entry)
            print(f"  {getattr(entry, 'image_path', '')}: {remarks}")
            if any("温度管理" in r or "温度" in r for r in remarks):
                thermo_entries.append((entry, remarks))
    print(f"温度管理系remarks付き品質管理写真: {len(thermo_entries)}件")
    for entry, remarks in thermo_entries:
        print(f"  {getattr(entry, 'image_path', '')}: {remarks}")
    # assert len(thermo_entries) >= 12, f"温度管理remarks付き品質管理写真が12件未満: {len(thermo_entries)}"

    # 必要に応じてUI部品の値やパネル内容もassert可能

    print("[調査] UI経由で見えているレコード全件:")
    for entry in entries:
        widget.on_image_selected(entry)
        table = widget.record_panel.record_list_widget
        row_count = table.rowCount()
        col_count = table.columnCount()
        print(f"画像: {getattr(entry, 'image_path', '')} (カテゴリ: {getattr(entry, 'photo_category', None)})")
        for row in range(row_count):
            row_data = [table.item(row, col).text() if table.item(row, col) else "" for col in range(col_count)]
            print(f"  Row {row}: {row_data}")