# テスト構成

このディレクトリには、PhotoCategorizerアプリケーションのテストが含まれています。

## テストの分類

テストは以下のカテゴリに分類されています：

### マーカーによる分類

- `@pytest.mark.unit`: モック中心の高速なユニットテスト
- `@pytest.mark.smoke`: 実際のモデルを使用する統合テスト
- `@pytest.mark.schema`: JSONデータ構造を検証するスキーマテスト

## ディレクトリ構造

- `tests/`: テストのルートディレクトリ
  - `test_roi_initialization.py`: ROI（Region of Interest）初期化テスト
  - `integration/`: 統合テスト
    - `test_init_model.py`: モデル初期化テスト
    - `test_infer_on_sample.py`: サンプル画像を使用した推論テスト

## テストの実行方法

### すべてのテストを実行

```bash
python -m pytest
```

### 特定のマーカーのテストのみ実行

```bash
# ユニットテストのみ実行（高速）
python -m pytest -m unit

# 統合テストのみ実行（重い処理を含む）
python -m pytest -m smoke

# スキーマテストのみ実行
python -m pytest -m schema
```

### 特定のディレクトリのテストのみ実行

```bash
# 統合テストのみ実行
python -m pytest tests/integration/
```

### 詳細表示でテストを実行

```bash
python -m pytest -v
```

## CI環境での実行

CI環境では、通常以下のコマンドを使用します：

```bash
# 通常のCI実行（モデルダウンロードなし）
python -m pytest -m "unit or schema"

# 週次スモークテスト（実モデルを使用）
python -m pytest -m smoke
```

# テスト実行ガイド

## ヘッドレステスト実行について

このプロジェクトでは、PyQt6を使用したGUIアプリケーションのテストを実行します。
テスト実行環境によって結果が異なる場合があるため、以下の点に注意してください。

### テストマネージャGUIでの実行

テストマネージャGUI（IDE統合テスト実行環境）で実行する場合：

1. 必ず最新の環境設定ファイルを使用する
2. 特に問題が発生した場合は、以下の設定を確認：
   - 環境変数: `QT_QPA_PLATFORM=offscreen` が設定されているか
   - 警告抑制が有効になっているか
   - QApplicationインスタンスが適切に管理されているか

### コマンドラインでの実行

コマンドラインから実行する場合は、以下のコマンドを使用：

```bash
# 全テスト実行
python -m pytest

# 特定のテストのみ実行
python -m pytest tests/test_annotation_tool.py::TestEditableBoundingBox::test_initial_state
```

## トラブルシューティング

テスト実行時に問題が発生した場合は、以下を確認してください：

1. **環境設定の問題**: tests/conftest.py のQApplicationの初期化が正しく行われているか
2. **警告によるエラー**: pytest.iniの警告フィルター設定が適切か
3. **リソース解放の問題**: テスト終了時にリソースが適切に解放されているか

## 注意事項

- テスト実行後は必ずリソースが解放されていることを確認してください
- 長時間テストを実行する場合はメモリリークに注意してください

# ルール

- ルートにあるsend_prompt.pyスクリプトを使うことで、AI間で通信ができる。
- 必要に応じてこのスクリプトを利用すること。
- 他のAIやプロセスとの連携が必要な場合は、send_prompt.pyの活用を検討すること。