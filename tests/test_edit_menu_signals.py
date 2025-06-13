import sys
import pytest
from PyQt6.QtWidgets import QApplication, QDialog
from src.summary_generator_widget import SummaryGeneratorWidget

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

def test_edit_role_mapping_action_opens_dialog(app, qtbot):
    window = SummaryGeneratorWidget(test_mode=True)
    window.show()
    qtbot.addWidget(window)

    # 編集メニューのアクションを取得
    edit_action = find_menu_action(window, "編集", "ロールマッピング編集")
    assert edit_action is not None, "ロールマッピング編集 QActionが見つかりません"

    dialogs_before = [w for w in QApplication.topLevelWidgets() if isinstance(w, QDialog)]
    # QActionを発火
    edit_action.trigger()
    qtbot.wait(500)
    dialogs_after = [w for w in QApplication.topLevelWidgets() if isinstance(w, QDialog)]
    new_dialogs = [d for d in dialogs_after if d not in dialogs_before]
    # タイトルがロールマッピング編集のQDialogが開いているか
    found = False
    for dlg in new_dialogs:
        if dlg.windowTitle() == 'ロールマッピング編集' and dlg.isVisible():
            found = True
            dlg.close()  # テスト後に閉じる
            break
    assert found, "ロールマッピング編集ダイアログが開きませんでした"
    window.close()
