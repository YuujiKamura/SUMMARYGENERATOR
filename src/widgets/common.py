# YOLOウィジェット共通部品（PhotoCategorizerからコピー）
from pathlib import Path
from PyQt6.QtWidgets import QComboBox, QProgressBar, QTextEdit

def create_model_combo(parent=None):
    """YOLOモデル選択用コンボボックスを生成し、モデルリストをセットする"""
    combo = QComboBox(parent)
    model_files = [
        "yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt", "yolo11n.pt"
    ]
    for model_file in model_files:
        model_paths = [
            Path.cwd() / model_file,
            Path.cwd() / "yolo" / model_file,
            Path.cwd() / "models" / model_file,
            Path.home() / ".yolo" / "models" / model_file
        ]
        for model_path in model_paths:
            if model_path.exists():
                combo.addItem(model_file, str(model_path))
                break
        else:
            combo.addItem(f"{model_file} (見つかりません)", model_file)
    return combo

def create_progress_bar(parent=None):
    """進捗バーを生成"""
    bar = QProgressBar(parent)
    bar.setRange(0, 0)
    bar.setVisible(False)
    return bar

def create_log_text(parent=None):
    """ログ表示用テキストエリアを生成"""
    log = QTextEdit(parent)
    log.setReadOnly(True)
    log.setMinimumHeight(80)
    return log
