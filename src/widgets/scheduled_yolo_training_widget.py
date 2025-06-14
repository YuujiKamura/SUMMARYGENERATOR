from __future__ import annotations

# coding: utf-8
"""
YOLO定時学習スケジューラウィジェット

任意のJSONラベルファイルを指定し、`run_create_yolo_dataset_from_json.py` を
指定時刻に自動実行する簡易スケジューラ。GUI から開始/停止を操作でき、
毎日同じ時刻に繰り返し実行するオプションも備える。

依存:
    PyQt6
"""

import sys
import shlex
import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QTimer, QDateTime, QProcess, pyqtSlot
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QHBoxLayout,
    QPushButton,
    QDateTimeEdit,
    QLineEdit,
    QFileDialog,
    QTextEdit,
    QLabel,
    QMessageBox,
    QCheckBox,
    QMainWindow,
)


class ScheduledYoloTrainingWidget(QMainWindow):
    """`run_create_yolo_dataset_from_json.py` を定時実行するウィジェット"""

    def __init__(self, parent: Optional[QMainWindow] = None) -> None:  # noqa: D401,E501
        super().__init__(parent)
        self.setWindowTitle("YOLO定時学習スケジューラ")

        self._scheduled_datetime: Optional[datetime.datetime] = None
        self._daily_repeat: bool = False
        self._process: Optional[QProcess] = None

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        self._setup_ui(parent_widget=central_widget)
        # 1 秒周期で現在時刻を確認
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timer_tick)
        self._timer.start(1000)

    # ---------------------------------------------------------------------
    # UI
    # ---------------------------------------------------------------------
    def _setup_ui(self, parent_widget: QWidget) -> None:
        layout = QVBoxLayout(parent_widget)

        form = QFormLayout()

        # 実行日時
        self.datetime_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.datetime_edit.setDisplayFormat("yyyy/MM/dd HH:mm:ss")
        self.datetime_edit.setCalendarPopup(True)
        form.addRow("実行日時", self.datetime_edit)

        # JSON ファイル選択
        json_hbox = QHBoxLayout()
        self.json_path_edit = QLineEdit()
        self.json_path_edit.setPlaceholderText("入力 JSON を選択…")
        browse_btn = QPushButton("参照…")
        browse_btn.clicked.connect(self._select_json)
        json_hbox.addWidget(self.json_path_edit, 1)
        json_hbox.addWidget(browse_btn)
        form.addRow("入力 JSON", json_hbox)

        # 追加 CLI 引数
        self.cli_args_edit = QLineEdit("--mode all --augment-num 5 --epochs 100")
        self.cli_args_edit.setPlaceholderText("例: --mode all --augment-num 5 --epochs 100 など")
        form.addRow("追加 CLI 引数", self.cli_args_edit)

        # CLI ヒント
        form.addRow("ヒント", QLabel("--mode all/augment, --augment-num, --epochs, --retrain-loops 等"))

        # 毎日実行
        self.repeat_chk = QCheckBox("毎日同じ時刻に繰り返し実行")
        form.addRow("", self.repeat_chk)

        layout.addLayout(form)

        # ボタン
        btn_hbox = QHBoxLayout()
        self.start_btn = QPushButton("スケジュール開始")
        self.run_now_btn = QPushButton("今すぐ実行！")
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setEnabled(False)
        self.start_btn.clicked.connect(self._start_schedule)
        self.stop_btn.clicked.connect(self._stop_schedule)
        self.run_now_btn.clicked.connect(self._run_now)
        btn_hbox.addWidget(self.start_btn)
        btn_hbox.addWidget(self.run_now_btn)
        btn_hbox.addWidget(self.stop_btn)
        layout.addLayout(btn_hbox)

        # ログ
        self.log_text: QTextEdit = QTextEdit()
        layout.addWidget(QLabel("ログ"))
        layout.addWidget(self.log_text)

        # デフォルトのJSONパス設定
        try:
            from src.utils.path_manager import path_manager
            default_json = path_manager.image_preview_cache_master
            self.json_path_edit.setText(str(default_json))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # スケジューラ制御
    # ------------------------------------------------------------------
    @pyqtSlot()
    def _start_schedule(self) -> None:
        json_path = self.json_path_edit.text().strip()
        if not json_path:
            QMessageBox.warning(self, "入力エラー", "入力 JSON を指定してください")
            return
        if not Path(json_path).exists():
            QMessageBox.warning(self, "入力エラー", "指定された JSON ファイルが存在しません")
            return

        self._scheduled_datetime = self.datetime_edit.dateTime().toPyDateTime()
        self._daily_repeat = self.repeat_chk.isChecked()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._log(f"スケジューラ開始: {self._scheduled_datetime}  (repeat={self._daily_repeat})")

    @pyqtSlot()
    def _stop_schedule(self) -> None:
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._scheduled_datetime = None
        self._log("スケジューラ停止")

    @pyqtSlot()
    def _run_now(self) -> None:
        """即時実行ボタンのハンドラ"""
        json_path = self.json_path_edit.text().strip()
        if not json_path or not Path(json_path).exists():
            QMessageBox.warning(self, "入力エラー", "有効な入力 JSON パスを指定してください")
            return
        self._launch_training_process()

    # ------------------------------------------------------------------
    # タイマ
    # ------------------------------------------------------------------
    def _on_timer_tick(self) -> None:
        if not self._scheduled_datetime:
            return

        now = datetime.datetime.now()
        if now >= self._scheduled_datetime:
            self._log("スケジュール時刻に達したため学習スクリプトを起動します…")
            self._launch_training_process()

            if self._daily_repeat:
                self._scheduled_datetime += datetime.timedelta(days=1)
                self._log(f"次回スケジュール: {self._scheduled_datetime}")
            else:
                # 1 回きりの場合は解除
                self._scheduled_datetime = None
                self.stop_btn.setEnabled(False)
                self.start_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # プロセス起動
    # ------------------------------------------------------------------
    def _launch_training_process(self) -> None:
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            self._log("前回のプロセスがまだ終了していないためスキップします")
            return

        script_path = Path(__file__).resolve().parents[2] / "run_create_yolo_dataset_from_json.py"
        if not script_path.exists():
            self._log(f"学習スクリプトが見つかりません: {script_path}")
            return

        args = [str(script_path), "--input-json", self.json_path_edit.text().strip()]
        extra = self.cli_args_edit.text().strip()
        if extra:
            args.extend(shlex.split(extra))

        self._process = QProcess(self)
        self._process.setProgram(sys.executable)
        self._process.setArguments(args)
        # カレントをプロジェクトルートに
        self._process.setWorkingDirectory(str(script_path.parent))
        self._process.readyReadStandardOutput.connect(lambda: self._read_process_output(False))
        self._process.readyReadStandardError.connect(lambda: self._read_process_output(True))
        self._process.finished.connect(self._on_process_finished)

        self._log("==== プロセス開始 ====")
        self._log("CMD: " + " ".join([sys.executable, *args]))
        self._process.start()

    def _read_process_output(self, is_stderr: bool = False) -> None:
        if not self._process:
            return
        data = self._process.readAllStandardError() if is_stderr else self._process.readAllStandardOutput()
        try:
            text = bytes(data).decode("utf-8", errors="replace")
        except Exception:  # pragma: no cover
            text = str(data)
        self._log(text.rstrip())

    def _on_process_finished(self, exit_code: int, _exit_status: QProcess.ExitStatus) -> None:
        self._log(f"==== プロセス終了 (exit_code={exit_code}) ====")

    # ------------------------------------------------------------------
    # ユーティリティ
    # ------------------------------------------------------------------
    def _log(self, message: str) -> None:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    # ------------------------------------------------------------------
    # ファイル選択
    # ------------------------------------------------------------------
    def _select_json(self) -> None:
        start_dir = Path(self.json_path_edit.text().strip()).resolve().parent if self.json_path_edit.text() else Path.cwd()
        file_path, _ = QFileDialog.getOpenFileName(self, "入力 JSON を選択", str(start_dir), "JSON (*.json)")
        if file_path:
            self.json_path_edit.setText(file_path) 