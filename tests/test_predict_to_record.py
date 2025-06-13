# test_predict_to_record.py
# OCRテキスト→辞書レコード推論の最小テスト
import sys
import os
import json
from rapidfuzz import fuzz
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/utils')))
from path_manager import path_manager

def normalize(text):
    table = str.maketrans({'舖':'舗','鋪':'舗','劑':'剤','裝':'装','，':',','、':' ','・':' ','　':' '})
    return text.translate(table).strip()

def predict_to_record(ocr_text):
    records_index_path = path_manager.default_records
    with open(records_index_path, encoding='utf-8') as f:
        records_index = json.load(f)
    records = []
    records_dir = os.path.join(os.path.dirname(records_index_path), 'records')
    for rec_file in records_index['records']:
        rec_path = os.path.join(records_dir, os.path.basename(rec_file))
        with open(rec_path, encoding='utf-8') as rf:
            records.append(json.load(rf))
    ocr_norm = normalize(ocr_text.replace('\n',' '))
    best_score = -1
    best_record = None
    for r in records:
        remarks_norm = normalize(r.get('remarks', ''))
        subtype_norm = normalize(r.get('subtype', ''))
        score_remarks = fuzz.token_set_ratio(ocr_norm, remarks_norm)
        score_subtype = fuzz.token_set_ratio(ocr_norm, subtype_norm)
        score = score_remarks * 0.7 + score_subtype * 0.3
        if score > best_score:
            best_score = score
            best_record = r
    return best_score, best_record

def test_predict_to_record():
    ocr_text = '工事名 東區市道(5区)舖裝補修工事\n業種 鋪裝工 测点 湖東\n步道部\n表層工\n乳劑、養生砂'
    score, record = predict_to_record(ocr_text)
    print('推論スコア:', score)
    print('推論レコード:', record)
    assert record is not None, '推論レコードがNoneです'
    assert score > 0, 'スコアが0以下です'

if __name__ == '__main__':
    test_predict_to_record()
