import os
import sys
from pathlib import Path

# DBとJSONのパスをsrc/data配下に固定
DATA_DIR = Path(__file__).parent / 'src' / 'data'
DB_PATH = DATA_DIR / 'model_training_cache.db'
JSON_PATH = DATA_DIR / 'image_preview_cache_master.json'

# 1. DB作成
os.system(f'python src/data/create_test_db_from_json.py')

# 2. オーグメント処理（1件だけDBに入っている想定）
ret = os.system(f'python src/data/augment_yolo_dataset.py')
if ret != 0:
    print('オーグメント処理でエラーが発生しました')
else:
    print('オーグメント処理が正常に完了しました')
