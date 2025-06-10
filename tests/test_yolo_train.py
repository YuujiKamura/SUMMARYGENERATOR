import os
import sys
import pytest
from pathlib import Path
from unittest import mock

@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.yolo
@pytest.mark.training
# ultralytics と torch のモック
@pytest.fixture(autouse=True)
def mock_ultralytics(monkeypatch):
    mock_yolo = mock.MagicMock()
    mock_yolo_instance = mock.MagicMock()
    mock_yolo.return_value = mock_yolo_instance
    
    # トレーニング結果のモック
    mock_results = mock.MagicMock()
    mock_results.results_dict = {
        "metrics/precision(B)": 0.85,
        "metrics/recall(B)": 0.80,
        "metrics/mAP50(B)": 0.82,
        "metrics/mAP50-95(B)": 0.75
    }
    # dict.getも0.85を返すように
    mock_results.results_dict.get = lambda key, default=0: 0.85 if key == "metrics/precision(B)" else default
    mock_yolo_instance.train.return_value = mock_results
    
    # torch のモックを詳細に設定
    mock_torch = mock.MagicMock()
    mock_torch.__version__ = "2.0.0"  # PyTorchバージョンを設定
    mock_torch.nn = mock.MagicMock()
    mock_torch.nn.modules = mock.MagicMock()
    mock_torch.nn.modules.container = mock.MagicMock()
    mock_torch.nn.modules.container.Sequential = mock.MagicMock()
    
    # ultralytics のモックを詳細に設定
    mock_ultralytics = mock.MagicMock()
    mock_ultralytics.nn = mock.MagicMock()
    mock_ultralytics.nn.tasks = mock.MagicMock()
    mock_ultralytics.nn.tasks.DetectionModel = mock.MagicMock()
    mock_ultralytics.nn.modules = mock.MagicMock()
    mock_ultralytics.nn.modules.Conv = mock.MagicMock()
    
    monkeypatch.setitem(sys.modules, 'ultralytics', mock_ultralytics)
    monkeypatch.setitem(sys.modules, 'ultralytics.nn', mock_ultralytics.nn)
    monkeypatch.setitem(sys.modules, 'ultralytics.nn.tasks', mock_ultralytics.nn.tasks)
    monkeypatch.setitem(sys.modules, 'ultralytics.nn.modules', mock_ultralytics.nn.modules)
    monkeypatch.setitem(sys.modules, 'torch', mock_torch)
    monkeypatch.setitem(sys.modules, 'torch.nn', mock_torch.nn)
    monkeypatch.setitem(sys.modules, 'torch.nn.modules', mock_torch.nn.modules)
    monkeypatch.setitem(sys.modules, 'torch.nn.modules.container', mock_torch.nn.modules.container)
    monkeypatch.setitem(sys.modules, 'torch.serialization', mock.MagicMock())
    
    return mock_yolo, mock_yolo_instance

@pytest.fixture
def dataset_path():
    """実際のデータセットパスを返す"""
    # プロジェクトのルートディレクトリを取得
    root_dir = Path(__file__).parent.parent
    dataset_yaml = root_dir / "dataset" / "dataset.yaml"
    return dataset_yaml

@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.yolo
@pytest.mark.training
def test_dataset_exists_and_valid(dataset_path):
    """データセットが存在し、構造が正しいかテスト"""
    # デバッグ出力
    print(f"テスト対象のデータセットパス: {dataset_path}")
    print(f"ファイルの存在: {dataset_path.exists()}")
    
    # データセットYAMLファイルの存在確認
    assert dataset_path.exists(), f"データセットYAMLファイルが見つかりません: {dataset_path}"
    
    # YAMLを読み込んで検証
    import yaml
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    # YAMLの内容を表示
    print(f"読み込んだYAML内容: {data}")
    
    # 必須キーの存在確認
    assert 'path' in data, "dataset.yamlにpathキーがありません"
    assert 'train' in data, "dataset.yamlにtrainキーがありません"
    assert 'val' in data, "dataset.yamlにvalキーがありません"
    assert 'names' in data or 'nc' in data, "dataset.yamlにnames/ncキーがありません"
    
    # パスの解決
    if os.path.isabs(data['path']):
        data_path = Path(data['path'])
    else:
        data_path = dataset_path.parent / data['path']
    
    print(f"解決したデータパス: {data_path}")
    
    # トレーニング画像ディレクトリ
    train_image_path = os.path.join(data_path, data['train'])
    train_images = Path(train_image_path)
    print(f"トレーニング画像パス: {train_images}")
    print(f"トレーニング画像ディレクトリの存在: {train_images.exists()}")
    
    # 存在チェック
    assert train_images.exists(), f"トレーニング画像ディレクトリが存在しません: {train_images}"
    
    # ラベル推定
    train_labels_path = train_image_path.replace('images', 'labels')
    train_labels = Path(train_labels_path)
    print(f"トレーニングラベルパス: {train_labels}")
    print(f"トレーニングラベルディレクトリの存在: {train_labels.exists()}")
    
    assert train_labels.exists(), f"トレーニングラベルディレクトリが存在しません: {train_labels}"
    
    # ファイル数の確認
    image_patterns = ['*.jpg', '*.png', '*.JPG', '*.PNG', '*.jpeg', '*.JPEG']
    train_images_files = []
    for pattern in image_patterns:
        train_images_files.extend(list(train_images.glob(pattern)))
    train_images_count = len(train_images_files)
    
    train_labels_count = len(list(train_labels.glob('*.txt')))
    
    print(f"画像ファイル数: {train_images_count}")
    print(f"ラベルファイル数: {train_labels_count}")
    
    assert train_images_count > 0, "トレーニング画像が見つかりません"
    assert train_labels_count > 0, "トレーニングラベルが見つかりません"
    assert train_labels_count >= train_images_count * 0.5, f"ラベルファイル数が不足しています: {train_labels_count}/{train_images_count}"
    
    # 画像とラベルの対応確認（サンプル数枚）
    import random
    image_files = train_images_files
    if image_files:
        sample_files = random.sample(image_files, min(5, len(image_files)))
        
        for img_file in sample_files:
            print(f"サンプル画像ファイル: {img_file}")
            label_file = train_labels / f"{img_file.stem}.txt"
            print(f"  対応するラベルファイル: {label_file}")
            print(f"  ラベルファイルの存在: {label_file.exists()}")
            
            assert label_file.exists(), f"画像 {img_file.name} に対応するラベルファイルがありません"
            
            # ラベルファイルの形式チェック
            with open(label_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                print(f"  ラベル内容: {content[:50]}...")
                assert content, f"ラベルファイル {label_file.name} が空です"
                
                # 少なくとも1行の有効なYOLOフォーマットかチェック
                lines = content.split('\n')
                parts = lines[0].split()
                assert len(parts) >= 5, f"ラベルファイル {label_file.name} のフォーマットが不正です: {lines[0]}"
                
                # クラスIDが範囲内か
                class_id = int(parts[0])
                if 'names' in data and isinstance(data['names'], list):
                    assert 0 <= class_id < len(data['names']), f"クラスID {class_id} が範囲外です (0-{len(data['names'])-1})"
                elif 'nc' in data:
                    assert 0 <= class_id < data['nc'], f"クラスID {class_id} が範囲外です (0-{data['nc']-1})"

@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.yolo
@pytest.mark.training
def test_yolo_train_execution(mock_ultralytics, dataset_path):
    """YOLOトレーニングの実行をテスト"""
    mock_yolo, mock_yolo_instance = mock_ultralytics
    
    # トレーニングスレッドをインポート
    from src.utils.yolo_threads import YoloTrainThread
    
    # シグナル受信用のモック
    output_received = mock.MagicMock()
    process_finished = mock.MagicMock()
    
    # トレーニングスレッドを作成
    thread = YoloTrainThread(
        model_path="yolo/yolov8n.pt",
        dataset_yaml=str(dataset_path),
        epochs=1,
        exp_name="test_model",
        project="runs/test"
    )
    
    # シグナルに接続
    thread.output_received.connect(output_received)
    thread.process_finished.connect(process_finished)
    
    # トレーニング実行（スレッド起動ではなく直接実行）
    thread.run()
    
    # 出力シグナルが発行されたことを確認
    assert output_received.call_count >= 5  # 少なくとも5回の出力
    
    # 出力メッセージを確認
    output_messages = [args[0][0] for args in output_received.call_args_list]
    assert any("トレーニングを開始します" in msg for msg in output_messages)
    assert any("トレーニングが完了しました" in msg for msg in output_messages)
    
    # プロセス終了シグナルが成功コード（0）で呼ばれたことを確認
    process_finished.assert_called_once()
    args = process_finished.call_args[0]
    assert args[0] == 0  # 終了コード
    assert isinstance(args[1], dict)  # 結果辞書
    assert "best_model" in args[1]
    assert "last_model" in args[1]
    assert "results" in args[1]
    assert args[1]["results"]["best_fitness"] == 0.85

@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.yolo
@pytest.mark.training
def test_yolo_train_with_error(mock_ultralytics):
    """エラー発生時の動作確認"""
    mock_yolo, mock_yolo_instance = mock_ultralytics
    
    # トレーニングでエラーを発生させるように設定
    mock_yolo_instance.train.side_effect = Exception("データセットが見つかりません")
    
    from src.utils.yolo_threads import YoloTrainThread
    
    # シグナル受信用のモック
    output_received = mock.MagicMock()
    process_finished = mock.MagicMock()
    
    # トレーニングスレッドを作成（無効なパスを指定）
    thread = YoloTrainThread(
        model_path="yolo/yolov8n.pt",
        dataset_yaml="invalid/path.yaml",
        epochs=1,
        exp_name="test_error",
        project="runs/test"
    )
    
    # シグナルに接続
    thread.output_received.connect(output_received)
    thread.process_finished.connect(process_finished)
    
    # トレーニング実行
    thread.run()
    
    # 出力シグナルが発行されたことを確認
    assert output_received.call_count >= 5  # 少なくとも5回の出力
    
    # 出力メッセージを確認
    output_messages = [args[0][0] for args in output_received.call_args_list]
    assert any("トレーニングを開始します" in msg for msg in output_messages)
    assert any("エラーが発生しました" in msg for msg in output_messages)
    assert any("データセットが見つかりません" in msg for msg in output_messages)
    
    # プロセス終了シグナルがエラーコード（1）で呼ばれたことを確認
    process_finished.assert_called_once()
    args = process_finished.call_args[0]
    assert args[0] == 1  # エラーコード
    assert isinstance(args[1], dict)  # 結果辞書
    assert "error" in args[1]
    assert "データセットが見つかりません" in args[1]["error"] 