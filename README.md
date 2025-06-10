# PhotoCategorizer SummaryGenerator

このリポジトリは、PhotoCategorizerアプリケーションのサマリー生成やYOLOデータセット拡張など、画像処理・アノテーション支援のための各種ツール・ウィジェットをまとめたものです。

## ディレクトリ構成

- `src/` : サマリー生成・画像プレビュー・YOLOデータセット管理など、主要なアプリケーションロジック
  - `components/`, `services/`, `widgets/`, `utils/` など機能別サブディレクトリ
  - `yolo/` : YOLOデータセット関連処理
  - `summarygenerator/` : サマリー生成ウィジェット本体
- `tests/` : テストコード・テスト用データ・テスト実行ガイド（詳細は `tests/README.md` 参照）
- `send_prompt.py` : AI間通信・プロセス連携用スクリプト
- `run_*.py` : 各種ウィジェットやツールの単体起動用スクリプト
- `yolo_data.db` : YOLOデータセット管理用DB（サンプル）

## 主要スクリプト・機能

- `run_summary_generator_widget.py` : サマリー生成ウィジェットの起動
- `run_image_preview_dialog.py` : 画像プレビュー用ダイアログの起動
- `run_yolo_widgets.py` : YOLOデータセット管理ウィジェットの起動
- `send_prompt.py` : 他AIやプロセスとのプロンプト送受信

## 開発・実行の基本

1. 必要なPythonパッケージをインストール
   ```bash
   pip install -r requirements.txt
   ```
2. 各種スクリプトを直接実行してGUIや機能を確認可能
   ```bash
   python run_summary_generator_widget.py
   ```
3. テストの実行や詳細なテスト運用ルールは `tests/README.md` を参照

## AI間通信・プロセス連携について

- ルートにある `send_prompt.py` スクリプトを使うことで、AI間でプロンプト（指示・メッセージ）を送受信できます。
- 他のAIやプロセスとの連携が必要な場合は、このスクリプトの活用を検討してください。
- 使い方例や詳細は `send_prompt.py` のソースコードやコメントを参照してください。
- 【前提】Windows環境で、HD解像度の全画面を左右ハーフ分割し、左側にVSCode（Copilot）、右側にCursorを配置した画面構成を想定しています。
- PyAutoGUIを利用しています。プロンプト表示位置の上に他のGUIウィンドウが被っている場合、正常に動作しません。
- Copilotは、Cursorに「次に何をすれば良いか指示をお願いします」とsend_prompt.py経由で問い合わせてください。

## 注意
- テストやAI間通信のルールは `tests/README.md` に記載
- 本READMEはプロジェクト全体の構成・概要ガイドです

---

ご不明点や詳細な使い方は各サブディレクトリのREADMEやソースコード内コメントも参照してください。