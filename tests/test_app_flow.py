import pytest
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QSignalSpy
from PyQt6.QtWidgets import QWidget
from scripts.test_manager.main_window import MainWindow
import logging

logger = logging.getLogger(__name__)

@pytest.mark.e2e
@pytest.mark.gui
@pytest.mark.slow
@pytest.mark.smoke
def test_run_all_tests(qt_app, qtbot):
    logger.info("--- test_run_all_tests START ---")
    """全テスト実行のエンドツーエンドテスト"""
    # 1) テストマネージャーアプリの起動
    logger.info("1) Creating MainWindow instance...")
    window = MainWindow()
    logger.info("Adding widget to qtbot...")
    qtbot.addWidget(window)
    logger.info("Showing window...")
    window.show()
    logger.info("Waiting for window to be exposed...")
    qtbot.waitExposed(window)
    logger.info("Window exposed.")

    # 2) 全テスト実行ボタンのクリック
    logger.info("2) Finding run_all_btn...")
    run_all_btn = window.run_all_btn
    assert run_all_btn, "全テスト実行ボタンが見つかりません"
    logger.info("Clicking run_all_btn...")
    QTest.mouseClick(run_all_btn, Qt.MouseButton.LeftButton)
    logger.info("Button clicked.")

    # 3) テスト完了シグナルの待機
    logger.info("3) Creating QSignalSpy for all_tests_finished...")
    spy = QSignalSpy(window.manager.all_tests_finished)
    logger.info("Waiting for signal (timeout=30s)...")
    # イベントループを少し処理する時間を与える
    qtbot.wait(100) 
    assert spy.wait(30000), "テスト実行がタイムアウトしました（30秒）"
    logger.info("Signal received or timed out.")

    # 4) 結果の検証
    logger.info("4) Verifying results...")
    status_bar = window.statusBar()
    assert "完了" in status_bar.currentMessage()
    assert window.manager.results is not None
    assert len(window.manager.results) > 0
    logger.info("Results verified.")
    logger.info("--- test_run_all_tests END ---")

@pytest.mark.e2e
@pytest.mark.gui
@pytest.mark.slow
@pytest.mark.ocr
@pytest.mark.photo
def test_photo_categorization(qt_app, qtbot):
    logger.info("--- test_photo_categorization START ---")
    """写真分類のエンドツーエンドテスト"""
    # 1) テストマネージャーアプリの起動
    logger.info("1) Creating MainWindow instance...")
    window = MainWindow()
    logger.info("Adding widget to qtbot...")
    qtbot.addWidget(window)
    logger.info("Showing window...")
    window.show()
    logger.info("Waiting for window to be exposed...")
    qtbot.waitExposed(window)
    logger.info("Window exposed.")

    # 2) OCRフェーズのテストを選択
    logger.info("2) Finding phase_ocr_radio...")
    phase_ocr_radio = window.phase_ocr_radio
    assert phase_ocr_radio, "OCRフェーズラジオボタンが見つかりません"
    logger.info("Checking phase_ocr_radio...")
    phase_ocr_radio.setChecked(True)
    qtbot.wait(100) # フィルター適用待ち

    # 3) 選択されたテストを実行
    logger.info("3) Finding run_selected_btn...")
    run_selected_btn = window.run_selected_btn
    assert run_selected_btn, "選択テスト実行ボタンが見つかりません"
    logger.info("Clicking run_selected_btn...")
    QTest.mouseClick(run_selected_btn, Qt.MouseButton.LeftButton)
    logger.info("Button clicked.")

    # 4) テスト完了シグナルの待機
    logger.info("4) Creating QSignalSpy for all_tests_finished...")
    spy = QSignalSpy(window.manager.all_tests_finished)
    logger.info("Waiting for signal (timeout=60s)...")
    # イベントループを少し処理する時間を与える
    qtbot.wait(100) 
    assert spy.wait(60000), "テスト実行がタイムアウトしました（60秒）"
    logger.info("Signal received or timed out.")

    # 5) 結果の検証
    logger.info("5) Verifying results...")
    status_bar = window.statusBar()
    assert "完了" in status_bar.currentMessage()
    assert window.manager.results is not None
    assert len(window.manager.results) > 0
    logger.info("Results verified.")
    logger.info("--- test_photo_categorization END ---") 