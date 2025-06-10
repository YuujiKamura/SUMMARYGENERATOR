#!/usr/bin/env python3
"""
YOLOトレーニング＆予測マネージャーのヘッドレステスト

このスクリプトはGUIを起動せずに、アプリケーションの主要機能をテストします。
- アセットのチェックと初期配置
- データセットの検証
- 設定の保存と読み込み
"""
import os
import sys
import logging
from pathlib import Path
import pytest

# 親ディレクトリをパスに追加して、srcモジュールをインポートできるようにする
sys.path.insert(0, str(Path(__file__).parent.parent))

# モジュールのインポート
from src.utils.asset_checker import AssetChecker
from src.utils.dataset_validator import DatasetValidationThread
from src.utils.settings_manager import SettingsManager
from src.utils.process_thread import ProcessThread

@pytest.mark.unit
@pytest.mark.integration
class DummySignal:
    def __init__(self):
        self.callbacks = []
    
    def connect(self, callback):
        self.callbacks.append(callback)
    
    def emit(self, *args):
        for callback in self.callbacks:
            callback(*args)

@pytest.mark.unit
@pytest.mark.integration
class ThreadMock:
    def __init__(self):
        self.output_received = DummySignal()
        self.process_finished = DummySignal()
        self.validation_finished = DummySignal()
    
    def start(self):
        pass  # 実際には開始しない

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@pytest.mark.unit
@pytest.mark.integration
def test_asset_checker():
    """アセットチェッカーのテスト"""
    logger.info("=== アセットチェッカーのテスト ===")
    checker = AssetChecker(verbose=True)
    result = checker.check_all_assets()
    
    # テスト結果を確認
    if not (result["missing_dirs"] or result["missing_models"]):
        logger.info("✓ アセットチェックに合格しました")
    else:
        logger.warning("! アセットチェックは完了しましたが、追加されたアセットがあります")
    
    return result

@pytest.mark.unit
@pytest.mark.integration
def test_dataset_validator():
    """データセット検証機能のテスト"""
    logger.info("\n=== データセット検証機能のテスト ===")
    
    # datasets.yamlが確実に存在することを確認
    yaml_path = Path.cwd() / "dataset" / "dataset.yaml"
    if not yaml_path.exists():
        logger.error(f"テスト失敗: dataset.yaml が見つかりません: {yaml_path}")
        return False
    
    # 出力を受け取るコールバック
    outputs = []
    def capture_output(text):
        outputs.append(text)
        logger.info(f"  検証出力: {text}")
    
    # 検証結果を受け取るコールバック
    validation_result = [None, None]
    def capture_result(success, errors):
        validation_result[0] = success
        validation_result[1] = errors
        logger.info(f"  検証結果: 成功={success}, エラー={errors}")
    
    # データセット検証を実行
    thread_mock = ThreadMock()
    validator = DatasetValidationThread(str(yaml_path))
    validator.output_received = thread_mock.output_received
    validator.validation_finished = thread_mock.validation_finished
    
    # シグナルに接続
    validator.output_received.connect(capture_output)
    validator.validation_finished.connect(capture_result)
    
    # 検証を実行（ヘッドレスモードなので直接run()を呼び出す）
    validator.run()
    
    # 結果のチェック
    if validation_result[0] is not None:
        if validation_result[0]:
            logger.info("✓ データセット検証に合格しました")
        else:
            logger.warning(f"! データセット検証でエラーが検出されました: {validation_result[1]}")
        return validation_result[0]
    else:
        logger.error("テスト失敗: 検証結果が返されませんでした")
        return False

@pytest.mark.unit
@pytest.mark.integration
def test_settings_manager():
    """設定マネージャーのテスト"""
    logger.info("\n=== 設定マネージャーのテスト ===")
    
    # テスト用の設定ファイル名
    test_settings_file = "test_settings.json"
    
    # テスト用のダミーUIコンポーネント
    class DummyComponent:
        def __init__(self, value):
            self._value = value
        
        def currentText(self):
            return self._value
        
        def value(self):
            return self._value
        
        def text(self):
            return self._value
        
        def setValue(self, value):
            self._value = value
        
        def setText(self, value):
            self._value = value
        
        def findText(self, text):
            return 0 if text == self._value else -1
        
        def setCurrentIndex(self, index):
            pass
    
    # テスト用のコンポーネント辞書
    test_components = {
        "model": DummyComponent("yolov8n.pt"),
        "epochs": DummyComponent(20),
        "name": DummyComponent("test_model"),
        "image_dir": DummyComponent("test/images")
    }
    
    # 設定マネージャーのインスタンス化
    settings_manager = SettingsManager(test_settings_file)
    
    # 設定の保存
    logger.info("設定を保存しています...")
    save_result = settings_manager.save_settings(test_components, logger.info)
    
    # 値の変更（読み込みテスト用）
    for component in test_components.values():
        if hasattr(component, "setValue"):
            component.setValue("changed")
        elif hasattr(component, "setText"):
            component.setText("changed")
    
    # 設定の読み込み
    logger.info("設定を読み込んでいます...")
    load_result = settings_manager.load_settings(test_components, logger.info)
    
    # テスト後のクリーンアップ
    try:
        os.remove(test_settings_file)
        logger.info(f"テスト設定ファイルを削除しました: {test_settings_file}")
    except:
        pass
    
    # テスト結果の確認
    if save_result and load_result:
        logger.info("✓ 設定マネージャーのテストに合格しました")
        return True
    else:
        logger.error("テスト失敗: 設定の保存または読み込みに失敗しました")
        return False

@pytest.mark.unit
@pytest.mark.integration
def run_all_tests():
    """すべてのテストを実行"""
    logger.info("YOLOトレーニング＆予測マネージャーのヘッドレステストを開始します")
    
    # アセットチェックのテスト
    asset_result = test_asset_checker()
    
    # データセット検証のテスト
    dataset_result = test_dataset_validator()
    
    # 設定マネージャーのテスト
    settings_result = test_settings_manager()
    
    # 総合結果の表示
    logger.info("\n=== テスト結果サマリー ===")
    logger.info(f"アセットチェック: {'✓' if not (asset_result['missing_dirs'] or asset_result['missing_models']) else '!'}")
    logger.info(f"データセット検証: {'✓' if dataset_result else '✗'}")
    logger.info(f"設定マネージャー: {'✓' if settings_result else '✗'}")
    
    # すべてのテストが成功したか
    all_success = (
        True and  # アセットチェックは警告があっても成功とみなす
        dataset_result and 
        settings_result
    )
    
    logger.info(f"\n{'すべてのテストが成功しました！' if all_success else 'テストに失敗があります。詳細ログを確認してください。'}")
    return all_success

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 