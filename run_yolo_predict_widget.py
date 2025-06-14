"""Run YOLO Predict Widget standalone script

This startup script adjusts the import path to the project-root ``src`` directory
before importing application modules.  Because of this dynamic path
manipulation, the import ordering violates *Flake8* rule *E402* (module-level
import not at top of file).  We intentionally ignore that rule for this file.
"""

# flake8: noqa: E402
# mypy: ignore-errors

import sys
from pathlib import Path

# summarygenerator ディレクトリをプロジェクトルートとみなす
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from PyQt6.QtWidgets import QApplication
from src.widgets.yolo_predict_widget import YoloPredictWidget

if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = YoloPredictWidget()
    widget.show()
    sys.exit(app.exec())
