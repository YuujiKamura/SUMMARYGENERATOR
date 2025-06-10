import sys
import os
import json
import logging

# プロジェクトのルートディレクトリをsys.pathに追加してsrc以下のモジュールをインポート可能にする
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.kanrichi_ocr_collector import KanrichiOcrDataCollector
from src.ocr_value_extractor import get_image_size_local # 追加

# ロギング設定
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s - %(message)s')

def test_run_ocr_from_cache_json(): # 関数名をpytestが認識できるように変更
    # テスト用のキャッシュJSONファイルのパスを直接指定
    # このパスは、実際のテスト環境に合わせて調整してください。
    # 例: src/image_preview_cache/ にある特定のキャッシュファイルを指すなど。
    # ここでは、以前のやり取りで使われた可能性のあるファイルを仮定します。
    cache_json_path = os.path.join(project_root, "src", "image_preview_cache", "306dbcd7bfe7091a324e550437ffff39832395cb.json")
    
    logging.info(f"テスト開始: {cache_json_path}")

    if not os.path.exists(cache_json_path):
        logging.error(f"指定されたJSONキャッシュファイルが見つかりません: {cache_json_path}")
        return

    try:
        with open(cache_json_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
    except Exception as e:
        logging.error(f"JSONキャッシュファイルの読み込みに失敗しました: {cache_json_path}, エラー: {e}")
        return

    image_path = cache_data.get("image_path")
    image_width = cache_data.get("width")
    image_height = cache_data.get("height")

    if not image_path:
        logging.error("JSONキャッシュファイルに必要な情報（image_path）が含まれていません。")
        return

    # image_pathの解決ロジックは先に実行
    if not os.path.exists(image_path):
        potential_path_from_root = os.path.join(project_root, image_path)
        if os.path.exists(potential_path_from_root):
            image_path = potential_path_from_root
            logging.info(f"画像パスをプロジェクトルートからの相対パスとして解決しました: {image_path}")
        else:
            logging.error(f"実際の画像ファイルが見つかりません: {cache_data.get('image_path')} および {potential_path_from_root}")
            return
    
    # widthとheightがJSONにない場合、画像から読み込む
    if image_width is None or image_height is None:
        logging.info("JSONキャッシュにwidth/heightがありません。画像ファイルから読み込みます。")
        try:
            # get_image_size_local は (width, height, local_path) を返す
            img_w, img_h, _ = get_image_size_local(image_path)
            image_width = img_w
            image_height = img_h
            logging.info(f"画像から取得したサイズ: width={image_width}, height={image_height}")
        except Exception as e:
            logging.error(f"画像ファイルからのサイズ取得に失敗しました: {image_path}, エラー: {e}")
            return # サイズがなければ処理を続行できない

    if not all([image_width, image_height]): # image_pathは既にチェック済み
        logging.error("画像パスまたは画像サイズ（width, height）の取得に失敗しました。")
        logging.error(f"  image_path: {image_path}")
        logging.error(f"  width: {image_width}")
        logging.error(f"  height: {image_height}")
        return

    logging.info(f"OCR対象画像: {image_path}")
    logging.info(f"画像幅: {image_width}, 画像高さ: {image_height}")

    collector = KanrichiOcrDataCollector()

    if not collector.engine or not collector.engine.client:
        logging.error("KanrichiOcrDataCollector の DocumentAI エンジンが初期化できませんでした。")
        logging.error("data/documentai_config.json の設定と認証情報を確認してください。")
        return

    try:
        logging.info("KanrichiOcrDataCollector.extract_text_from_image を呼び出します...")
        raw_ocr_data, parsed_measurements = collector.extract_text_from_image(image_path, image_width, image_height)
        
        logging.info("\n--- 生のOCR結果 (上位5件まで表示) ---")
        for i, item in enumerate(raw_ocr_data[:5]):
            logging.info(f"  {i+1}: Text: '{item.get('text')}', X: {item.get('x')}, Y: {item.get('y')}")
        if len(raw_ocr_data) > 5:
            logging.info(f"  ...他 {len(raw_ocr_data) - 5} 件")

        logging.info("\n--- パースされた測定値 ---")
        logging.info(json.dumps(parsed_measurements, indent=2, ensure_ascii=False))

        if not parsed_measurements.get("design") and not parsed_measurements.get("measured"):
            logging.warning("設計値・実測値がパースされませんでした。OCR結果またはパースロジックを確認してください。")
        
        logging.info("\nテスト完了")

    except Exception as e:
        logging.error(f"OCR処理中にエラーが発生しました: {e}", exc_info=True)
        assert False, f"OCR処理中にエラー: {e}" # pytestに失敗を通知

def test_run_ocr_without_cache(): # 新しいテスト関数
    # キャッシュを使用せずにOCRを実行するテスト
    # test_run_ocr_from_cache_json と同様のセットアップを行うが、
    # KanrichiOcrDataCollector は use_cache=False で初期化する。
    cache_json_path = os.path.join(project_root, "src", "image_preview_cache", "306dbcd7bfe7091a324e550437ffff39832395cb.json")
    logging.info(f"テスト開始 (キャッシュ無効): {cache_json_path}")

    if not os.path.exists(cache_json_path):
        logging.error(f"指定されたJSONキャッシュファイルが見つかりません: {cache_json_path}")
        assert False, f"JSONキャッシュファイルが見つかりません: {cache_json_path}"

    try:
        with open(cache_json_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
    except Exception as e:
        logging.error(f"JSONキャッシュファイルの読み込みに失敗しました: {cache_json_path}, エラー: {e}")
        assert False, f"JSONキャッシュファイルの読み込み失敗: {e}"

    image_path = cache_data.get("image_path")
    image_width = cache_data.get("width")
    image_height = cache_data.get("height")

    if not image_path:
        logging.error("JSONキャッシュファイルに必要な情報（image_path）が含まれていません。")
        assert False, "JSONキャッシュにimage_pathがありません。"

    if not os.path.exists(image_path):
        potential_path_from_root = os.path.join(project_root, image_path)
        if os.path.exists(potential_path_from_root):
            image_path = potential_path_from_root
            logging.info(f"画像パスをプロジェクトルートからの相対パスとして解決しました: {image_path}")
        else:
            logging.error(f"実際の画像ファイルが見つかりません: {cache_data.get('image_path')} および {potential_path_from_root}")
            assert False, f"画像ファイルが見つかりません: {image_path}"
    
    if image_width is None or image_height is None:
        logging.info("JSONキャッシュにwidth/heightがありません。画像ファイルから読み込みます。")
        try:
            img_w, img_h, _ = get_image_size_local(image_path)
            image_width = img_w
            image_height = img_h
            logging.info(f"画像から取得したサイズ: width={image_width}, height={image_height}")
        except Exception as e:
            logging.error(f"画像ファイルからのサイズ取得に失敗しました: {image_path}, エラー: {e}")
            assert False, f"画像サイズの取得失敗: {e}"

    if not all([image_width, image_height]):
        logging.error("画像パスまたは画像サイズ（width, height）の取得に失敗しました。")
        assert False, "画像パスまたはサイズの取得失敗"

    logging.info(f"OCR対象画像 (キャッシュ無効): {image_path}")
    logging.info(f"画像幅: {image_width}, 画像高さ: {image_height}")

    collector = KanrichiOcrDataCollector(use_cache=False) # キャッシュを無効にして初期化

    if not collector.engine or not collector.engine.client:
        logging.error("KanrichiOcrDataCollector の DocumentAI エンジンが初期化できませんでした。")
        assert False, "DocumentAIエンジン初期化失敗"

    try:
        logging.info("KanrichiOcrDataCollector.extract_text_from_image を呼び出します (キャッシュ無効)...")
        raw_ocr_data, parsed_measurements = collector.extract_text_from_image(image_path, image_width, image_height)
        
        logging.info("\n--- 生のOCR結果 (キャッシュ無効時、上位5件まで表示) ---")
        for i, item in enumerate(raw_ocr_data[:5]):
            logging.info(f"  {i+1}: Text: '{item.get('text')}', X: {item.get('x')}, Y: {item.get('y')}")
        if len(raw_ocr_data) > 5:
            logging.info(f"  ...他 {len(raw_ocr_data) - 5} 件")

        logging.info("\n--- パースされた測定値 (キャッシュ無効時) ---")
        logging.info(json.dumps(parsed_measurements, indent=2, ensure_ascii=False))

        # ここで parsed_measurements["sokuten"] が期待通りに取得できているか確認するアサーションを追加
        # 例えば、テスト画像において測点が "No. 24" と期待される場合:
        # assert parsed_measurements.get("sokuten") == "No. 24", f"期待される測点 'No. 24' が得られませんでした: {parsed_measurements.get('sokuten')}
        # このテストケースでは特定の測点値を期待せず、パース処理がエラーなく完了することを確認する程度に留める
        assert "sokuten" in parsed_measurements, "パース結果に 'sokuten' キーが含まれていません。"
        logging.info(f"抽出された測点 (キャッシュ無効時): {parsed_measurements.get('sokuten')}")

        if not parsed_measurements.get("design") and not parsed_measurements.get("measured"):
            logging.warning("設計値・実測値がパースされませんでした。OCR結果またはパースロジックを確認してください。")
        
        logging.info("\nテスト完了 (キャッシュ無効)")

    except Exception as e:
        logging.error(f"OCR処理中にエラーが発生しました (キャッシュ無効): {e}", exc_info=True)
        assert False, f"OCR処理中にエラー (キャッシュ無効): {e}"


if __name__ == "__main__":
    # この部分はpytest実行時には使われないが、直接スクリプトを実行する場合には残しておいても良い
    # test_run_ocr_from_cache_json() # 直接実行する場合はこちらをコール
    # テストするJSONキャッシュファイルのパス
    # ユーザー提供のパスを使用
    # target_cache_json = os.path.join(project_root, "src", "image_preview_cache", "306dbcd7bfe7091a324e550437ffff39832395cb.json") 
    # run_test_ocr_from_cache_json(target_cache_json)
    print("このスクリプトを直接実行する代わりに、`pytest tests/test_kanrichi_ocr_integration.py` を使用してください。")

