import sys
import pytest
from PyQt6.QtWidgets import QApplication
from src.summary_generator_widget import SummaryGeneratorWidget
import threading

@pytest.fixture(scope="module")
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app

def find_menu_action(window, menu_name, action_name):
    menubar = window.menuBar()
    for menu_action in menubar.actions():
        if menu_action.text() == menu_name:
            menu = menu_action.menu()
            for action in menu.actions():
                if action.text() == action_name:
                    return action
    return None

def run_with_timeout(timeout_sec, func, *args, **kwargs):
    result = {}
    exc = {}
    def target():
        try:
            result['value'] = func(*args, **kwargs)
        except Exception as e:
            exc['error'] = e
    t = threading.Thread(target=target)
    t.start()
    t.join(timeout_sec)
    if t.is_alive():
        raise TimeoutError(f"Test timed out after {timeout_sec} seconds!")
    if 'error' in exc:
        raise exc['error']
    return result.get('value')

@pytest.mark.timeout(10)
def test_file_menu_actions_signal_connections(app, qtbot):
    def inner():
        window = SummaryGeneratorWidget()
        window.show()
        qtbot.addWidget(window)

        # ファイルメニューのアクションを取得
        open_json_action = find_menu_action(window, "ファイル", "画像リストJSONを開く")
        export_excel_action = find_menu_action(window, "ファイル", "DB画像リストからExcelエクスポート")
        yolo_action = find_menu_action(window, "ファイル", "YOLO学習一括実行")

        assert open_json_action is not None, "画像リストJSONを開くアクションが見つからない"
        assert export_excel_action is not None, "DB画像リストからExcelエクスポートアクションが見つからない"
        assert yolo_action is not None, "YOLO学習一括実行アクションが見つからない"

        # 各アクションのtriggeredシグナルが何らかのスロットに接続されているか確認
        assert open_json_action.receivers(open_json_action.triggered) > 0, "画像リストJSONを開くのtriggeredシグナルが未接続"
        assert export_excel_action.receivers(export_excel_action.triggered) > 0, "DB画像リストからExcelエクスポートのtriggeredシグナルが未接続"
        assert yolo_action.receivers(yolo_action.triggered) > 0, "YOLO学習一括実行のtriggeredシグナルが未接続"

        # 実際にtriggerしてみて例外が出ないか（UI側でprint/log出力されればOK）
        open_json_action.trigger()
        export_excel_action.trigger()
        yolo_action.trigger()

        window.close()
    run_with_timeout(10, inner)
