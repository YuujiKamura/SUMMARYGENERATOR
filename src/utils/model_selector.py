from src.utils.path_manager import path_manager
from pathlib import Path

def get_available_models():
    """
    標準モデル・学習済みモデル（models_dir配下）を全てリストアップし、
    (表示名, パス)のリストで返す。パス重複は除外。
    """
    seen = set()
    models = []
    # 標準モデル
    model_files = [
        "yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt", "yolo11n.pt"
    ]
    for model_file in model_files:
        for model_path in [
            path_manager.yolo_model_dir / model_file,
            path_manager.models_dir / model_file
        ]:
            if model_path.exists() and str(model_path) not in seen:
                models.append((model_file, str(model_path)))
                seen.add(str(model_path))
                break
    # 学習済みモデル（models_dir配下の*.pt）
    if path_manager.models_dir.exists():
        for pt in path_manager.models_dir.glob("*.pt"):
            if str(pt) not in seen:
                models.append((pt.name, str(pt)))
                seen.add(str(pt))
    return models 