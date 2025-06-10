import subprocess
import sys
from pathlib import Path

def test_yolo_model_validation():
    """
    YOLOv8学習済みモデルの自動バリデーションテスト。
    学習済みモデル(best.pt)が存在する場合、valセットでmAP等の指標を出力し、
    mAPが一定以上であることを確認する（閾値は適宜調整）。
    """
    # 最新のデータセットディレクトリを自動検出
    datasets_base = Path(__file__).parent.parent / 'src' / 'datasets'
    candidates = sorted(datasets_base.glob('yolo_dataset_all_*'), reverse=True)
    assert candidates, 'yolo_dataset_all_* ディレクトリが見つかりません'
    dataset_dir = candidates[0]
    model_path = dataset_dir / 'train_run' / 'exp' / 'weights' / 'best.pt'
    yaml_path = dataset_dir / 'dataset.yaml'
    assert model_path.exists(), f"モデルが見つかりません: {model_path}"
    assert yaml_path.exists(), f"dataset.yamlが見つかりません: {yaml_path}"

    # ultralytics CLIでvalを実行
    cmd = [
        sys.executable, '-m', 'ultralytics', 'val',
        'model=' + str(model_path),
        'data=' + str(yaml_path),
        'save_json=False',
        'plots=False',
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    # mAP値の自動判定（例: mAP50 > 0.5 なら合格）
    import re
    m = re.search(r"mAP50-95:\s*([0-9.]+)", result.stdout)
    if m:
        map_val = float(m.group(1))
        assert map_val > 0.1, f"mAP50-95が低すぎます: {map_val}"
    else:
        raise AssertionError('mAP値が出力から取得できませんでした')
