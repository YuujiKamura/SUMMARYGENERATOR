#!/usr/bin/env python3
"""
基本的なGUI起動テスト
"""

"""テスト対象: src\yolo_train_predict_manager.py (エントリーポイント)"""
import sys
import os
from pathlib import Path

# モジュールのパスを追加
current_dir = Path(__file__).parent.parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# srcディレクトリを追加
src_dir = current_dir / 'src'
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

try:
    # 必要なライブラリをインポート
    import PyQt6
    from PyQt6.QtWidgets import QApplication
    print("PyQt6が正常にインポートされました。")
except ImportError as e:
    print(f"PyQt6のインポートに失敗しました: {e}")
    print("pip install PyQt6 を実行してインストールしてください。")
    sys.exit(1)

try:
    # YOLOスレッドモジュールをインポート（albumentationsの依存関係をチェック）
    # utils階層をインポートパスに追加
    sys.path.append(str(src_dir))
    
    # srcを省いてインポート
    from utils.yolo_threads import YoloTrainThread, YoloPredictThread
    print("YOLOスレッドモジュールが正常にインポートされました。")
except ImportError as e:
    print(f"YOLOスレッドモジュールのインポートに失敗しました: {e}")
    sys.exit(1)

try:
    # 拡張モジュールをインポート（albumentationsの依存関係をチェック）
    from utils.data_augmenter import DataAugmentThread
    print("データ拡張モジュールが正常にインポートされました。")
except ImportError as e:
    print(f"データ拡張モジュールのインポートに失敗しました: {e}")
    print("pip install albumentations tqdm を実行してインストールしてください。")
    sys.exit(1)

try:
    # メインGUIをインポート
    from yolo_train_predict_manager import YoloTrainPredictManager
    print("YOLOトレーニング＆予測マネージャーが正常にインポートされました。")
except ImportError as e:
    print(f"YOLOトレーニング＆予測マネージャーのインポートに失敗しました: {e}")
    sys.exit(1)

def main():
    """基本的なGUI起動テスト"""
    print("アプリケーション初期化を開始します...")
    
    # アプリケーションインスタンスを作成
    app = QApplication(sys.argv)
    
    print("GUIウィンドウを作成しています...")
    try:
        # メインウィンドウを作成
        window = YoloTrainPredictManager()
        
        # タブの数を確認
        print(f"タブ数: {window.tabs.count()}")
        for i in range(window.tabs.count()):
            print(f"タブ {i}: {window.tabs.tabText(i)}")
        
        # 主要ボタンの存在確認
        required_buttons = ["train_btn", "predict_btn", "auto_annotate_btn", "augment_btn"]
        for btn_name in required_buttons:
            if hasattr(window, btn_name):
                print(f"ボタン '{btn_name}' が正常に初期化されました。")
            else:
                print(f"警告: ボタン '{btn_name}' が見つかりません。")
        
        print("ウィンドウを表示します...")
        window.show()
        
        print("基本的な初期化は正常に完了しました。")
        print("このウィンドウを閉じると、テストは終了します。")
        
        # イベントループを開始
        return app.exec()
        
    except Exception as e:
        print(f"GUI初期化中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 