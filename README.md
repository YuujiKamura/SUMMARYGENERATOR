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
- `ocr-ruby/` : Ruby版OCRシステム - DocumentAI APIによる測点情報抽出と補完
  - `lib/` : OCR処理ライブラリ（DocumentAIクライアント、Survey Point補完など）
  - `bin/` : 実行スクリプト群（メインプロセッサー、接続テスト、設定確認など）
  - `config/` : DocumentAI設定ファイル
  - `test_images/` : テスト用画像
- `ocr_tools/` : Python版OCRツール（既存）

## 主要スクリプト・機能

- `run_summary_generator_widget.py` : サマリー生成ウィジェットの起動
- `run_image_preview_dialog.py` : 画像プレビュー用ダイアログの起動
- `run_yolo_widgets.py` : YOLOデータセット管理ウィジェットの起動
- `send_prompt.py` : 他AIやプロセスとのプロンプト送受信

## 各種run_*.pyスクリプトの用途

- `run_create_yolo_dataset_from_json.py` : DB登録→YOLOデータセット生成→オーグメント→YOLOv8学習までを一括自動実行するバッチスクリプト（ワンストップ処理）
- `run_export_yolo_from_db.py` : DBに登録された画像・アノテーションからYOLOデータセット（images/labels）をエクスポートする専用スクリプト
- `run_init_yolo_db.py` : YOLO用DB（image_preview_cache.db等）の初期化・セットアップ用スクリプト
- `run_yolo_workflow_cli.py` : コマンドラインからYOLOワークフロー（推論・学習等）を実行するCLIツールのエントリポイント
- `run_yolo_widgets.py` : PyQtウィジェット（GUI）でYOLO推論・学習・データセット変換などを操作できるGUIアプリの起動スクリプト

### 使い分けの目安
- **全部自動でやりたい** → `run_create_yolo_dataset_from_json.py`
- **DB→YOLOデータセットだけ** → `run_export_yolo_from_db.py`
- **DB初期化** → `run_init_yolo_db.py`
- **CLIでYOLOワークフロー** → `run_yolo_workflow_cli.py`
- **GUIでYOLO操作** → `run_yolo_widgets.py`

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
   - **テスト実行時はタイムアウト10秒（例: `pytest --timeout=10`）の指定を推奨します。**

## AI間通信・プロセス連携について

- ルートにある `send_prompt.py` スクリプトを使うことで、AI間でプロンプト（指示・メッセージ）を送受信できます。
- 他のAIやプロセスとの連携が必要な場合は、このスクリプトの活用を検討してください。
- 使い方例や詳細は `send_prompt.py` のソースコードやコメントを参照してください。
- 【前提】Windows環境で、HD解像度の全画面を左右ハーフ分割し、左側にVSCode（Copilot）、右側にCursorを配置した画面構成を想定しています。
- PyAutoGUIを利用しています。プロンプト表示位置の上に他のGUIウィンドウが被っている場合、正常に動作しません。
- Copilotは、Cursorに「次に何をすれば良いか指示をお願いします」とsend_prompt.py経由で問い合わせてください。

## YOLO自動学習・再学習バッチ運用について

- `run_create_yolo_dataset_from_json.py` は、DB登録→YOLOデータセット生成→オーグメント→学習→推論→インコレクト抽出→再学習までを一括自動化できます。
- コマンドライン引数で
    - `--retrain-mode` : 再学習タイミング（`ask`=都度確認, `immediate`=すぐ, `night`=夜間バッチ推奨）
    - `--retrain-loops` : 再学習ループ回数
    - `--epoch-multiplier` : 再学習ごとのエポック数倍率
  などを指定可能。
- 初回学習後に自動で推論・インコレクト抽出を行い、失敗画像枚数を通知。再学習の実行・エポック数増加も対話式または自動で選択できます。
- 夜間バッチ運用やImageListJobManagerとの連携で、完全自動化も可能です。

### 例: 夜間バッチで自動学習
```pwsh
python run_create_yolo_dataset_from_json.py --retrain-mode night --retrain-loops 1 --epoch-multiplier 2
```

### 例: 対話式で即時再学習
```pwsh
python run_create_yolo_dataset_from_json.py --retrain-mode ask
```

- 詳細はスクリプト先頭のコメントやヘルプ（`-h`）を参照してください。

## 注意
- テストやAI間通信のルールは `tests/README.md` に記載
- 本READMEはプロジェクト全体の構成・概要ガイドです
- **コード変更後は必ずflake8やpylint等で静的解析を実施し、エラーや警告がないことを確認してください。**

---

ご不明点や詳細な使い方は各サブディレクトリのREADMEやソースコード内コメントも参照してください。