# OCR Tools

このディレクトリはOCR関連の機能を統合して管理するためのモジュールです。

## ディレクトリ構造

```
ocr_tools/
├── README.md                    # このファイル
├── __init__.py                  # モジュール初期化
├── documentai_engine.py         # DocumentAI エンジン
├── ocr_config_loader.py         # 設定ファイル読み込み
├── ocr_value_extractor.py       # OCR値抽出メイン機能
├── ocr_value_pair_detector.py   # OCR値ペア検出
├── ocr_aa_layout.py            # AA レイアウト表示
├── preset_roles.json           # プリセットロール定義
├── credential/                  # 認証情報
│   └── visionapi-437405-0cd91b6d2db4.json
├── ocr_cache/                   # OCRキャッシュ
│   ├── *.json                   # キャッシュファイル
└── tests/                       # テストファイル
    └── test_ocr_value_extractor.py
```

## 使用方法

### 基本的な使用

```python
from ocr_tools.ocr_value_extractor import process_image_json, init_documentai_engine

# DocumentAI エンジンの初期化
engine = init_documentai_engine()

# 画像JSONファイルの処理
process_image_json('path/to/image.json', 'preset_roles.json', engine)
```

### テストの実行

```bash
# ocr_toolsディレクトリから実行
cd ocr_tools
python tests/test_ocr_value_extractor.py
```

## 機能

- **OCR値抽出**: DocumentAI を使用した高精度OCR
- **キャッシュ機能**: 処理済みOCR結果の自動キャッシュ
- **パス管理**: PathManagerによる統一されたリソースパス解決
- **テスト統合**: 自己完結型のテストスイート

## 依存関係

- Google Cloud DocumentAI
- PIL (Python Imaging Library)
- PathManager (プロジェクト内のユーティリティ)

## 設定

認証情報は `credential/` ディレクトリに配置し、キャッシュは `ocr_cache/` に自動保存されます。
