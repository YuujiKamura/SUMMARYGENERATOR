#!/usr/bin/env python3
"""
YOLOウィジェット共通部品
"""
from pathlib import Path
from PyQt6.QtWidgets import QComboBox, QProgressBar, QTextEdit

def create_model_combo(parent=None):
    """src/yolo, src/datasets配下の.ptモデルを再帰的に探索し、コンボボックスにセット"""
    from pathlib import Path
    from PyQt6.QtWidgets import QComboBox
    import os
    combo = QComboBox(parent)
    base_dirs = [Path(os.path.dirname(__file__)).parent / "yolo", Path(os.path.dirname(__file__)).parent / "datasets"]
    seen = set()
    for base in base_dirs:
        if base.exists():
            for pt in base.rglob("*.pt"):
                if pt.name not in seen:
                    combo.addItem(pt.name, str(pt))
                    seen.add(pt.name)
    if combo.count() == 0:
        combo.addItem("(モデルが見つかりません)", "")
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