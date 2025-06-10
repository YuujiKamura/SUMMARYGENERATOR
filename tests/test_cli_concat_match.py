import json
from rapidfuzz import fuzz
import os

def normalize(text):
    # 旧字体→新字体、全角→半角、カンマや記号もスペースに
    table = str.maketrans({'舖':'舗','鋪':'舗','劑':'剤','裝':'装','，':',','、':' ','・':' ','　':' '})
    return text.translate(table).strip()

def main():
    # OCRテキスト
    ocr_text = '''工事名 東區市道(5区)舖裝補修工事\n業種 鋪裝工 测点 湖東\n步道部\n表層工\n乳劑、養生砂'''
    # 全レコードを読み込み
    records_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/dictionaries/default_records.json'))
    with open(records_path, encoding='utf-8') as f:
        records = json.load(f)
    ocr_norm = normalize(ocr_text.replace('\n',' '))
    results = []
    for r in records:
        remarks_norm = normalize(r['remarks'])
        subtype_norm = normalize(r['subtype'])
        score_remarks = fuzz.token_set_ratio(ocr_norm, remarks_norm)
        score_subtype = fuzz.token_set_ratio(ocr_norm, subtype_norm)
        score = score_remarks * 0.7 + score_subtype * 0.3  # remarks優先
        results.append((score, r['subtype'], r['remarks'], r))
    results.sort(key=lambda x: x[0], reverse=True)
    print('--- OCRテキスト ---')
    print(ocr_text)
    print('-------------------')
    print('--- remarks優先+subtype加味の合成スコア 上位10件 ---')
    for i, (score, subtype, remarks, rec_obj) in enumerate(results[:10]):
        print(f'{i+1}. スコア: {score:.2f} サブタイプ: {subtype} リマーク: {remarks}')
        if remarks == '端部乳剤塗布状況':
            print('   ※このレコードが「端部乳剤塗布状況」です')
    # 端部乳剤塗布状況のスコアも個別表示
    for score, subtype, remarks, rec_obj in results:
        if remarks == '端部乳剤塗布状況':
            print(f'【端部乳剤塗布状況のスコア】 {score:.2f} サブタイプ: {subtype} リマーク: {remarks}')
            break

if __name__ == '__main__':
    main() 