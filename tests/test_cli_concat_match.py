import sys
import os
import json
from rapidfuzz import fuzz
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/utils')))
from path_manager import path_manager

def normalize(text):
    table = str.maketrans({'舖':'舗','鋪':'舗','劑':'剤','裝':'装','，':',','、':' ','・':' ','　':' '})
    return text.translate(table).strip()

def main():
    ocr_text = '''工事名 東區市道(5区)舖裝補修工事\n業種 鋪裝工 测点 湖東\n步道部\n表層工\n乳劑、養生砂'''
    # default_records.jsonをロード
    records_index_path = path_manager.default_records
    with open(records_index_path, encoding='utf-8') as f:
        records_index = json.load(f)
    # 各レコードファイルをロード
    records = []
    records_dir = os.path.join(os.path.dirname(records_index_path), 'records')
    for rec_file in records_index['records']:
        rec_path = os.path.join(records_dir, os.path.basename(rec_file))
        with open(rec_path, encoding='utf-8') as rf:
            records.append(json.load(rf))
    ocr_norm = normalize(ocr_text.replace('\n',' '))
    results = []
    for r in records:
        remarks_norm = normalize(r.get('remarks', ''))
        subtype_norm = normalize(r.get('subtype', ''))
        score_remarks = fuzz.token_set_ratio(ocr_norm, remarks_norm)
        score_subtype = fuzz.token_set_ratio(ocr_norm, subtype_norm)
        score = score_remarks * 0.7 + score_subtype * 0.3
        results.append((score, r.get('subtype',''), r.get('remarks',''), r))
    results.sort(key=lambda x: x[0], reverse=True)
    print('--- OCRテキスト ---')
    print(ocr_text)
    print('-------------------')
    print('--- remarks優先+subtype加味の合成スコア 上位10件 ---')
    for i, (score, subtype, remarks, rec_obj) in enumerate(results[:10]):
        print(f'{i+1}. スコア: {score:.2f} サブタイプ: {subtype} リマーク: {remarks}')
        if remarks == '端部乳剤塗布状況':
            print('   ※このレコードが「端部乳剤塗布状況」です')
    for score, subtype, remarks, rec_obj in results:
        if remarks == '端部乳剤塗布状況':
            print(f'【端部乳剤塗布状況のスコア】 {score:.2f} サブタイプ: {subtype} リマーク: {remarks}')
            break

if __name__ == '__main__':
    main()