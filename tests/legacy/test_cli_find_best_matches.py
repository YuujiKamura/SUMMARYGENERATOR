import sys
import os
import json
from PhotoCategorizer.app.controllers.dictionary_manager import DictionaryManager, DictRecord

# OCRキャッシュファイルのパス
OCR_CACHE_PATH = os.path.join(os.path.dirname(__file__), '../data/ocr_results_cache.json')

# テスト用ユーザー辞書レコード
TEST_RECORDS = [
    DictRecord(category="舗装補修工", type="アスファルト舗装補修工", subtype="舗装版切断", remarks="As舗装版切断状況", station="", control=""),
    DictRecord(category="舗装補修工", type="アスファルト舗装補修工", subtype="舗装版破砕", remarks="剥取状況", station="", control=""),
    DictRecord(category="舗装補修工", type="アスファルト舗装補修工", subtype="舗装版破砕", remarks="積込状況", station="", control=""),
    DictRecord(category="舗装補修工", type="アスファルト舗装補修工", subtype="舗装版破砕", remarks="既設舗装厚さ", station="", control="t=50mm"),
    DictRecord(category="舗装補修工", type="アスファルト舗装補修工", subtype="上層路盤工", remarks="補足材搬入 RM-40", station="", control=""),
    DictRecord(category="舗装補修工", type="アスファルト舗装補修工", subtype="上層路盤工", remarks="不陸整正状況", station="", control=""),
    DictRecord(category="舗装補修工", type="アスファルト舗装補修工", subtype="上層路盤工", remarks="転圧状況", station="", control=""),
    DictRecord(category="舗装補修工", type="アスファルト舗装補修工", subtype="上層路盤工", remarks="路盤完了", station="", control=""),
    DictRecord(category="舗装補修工", type="アスファルト舗装補修工", subtype="上層路盤工", remarks="不陸整正出来形・全景", station="", control=""),
    DictRecord(category="舗装補修工", type="アスファルト舗装補修工", subtype="上層路盤工", remarks="不陸整正出来形・管理値", station="", control=""),
    DictRecord(category="舗装補修工", type="アスファルト舗装補修工", subtype="上層路盤工", remarks="不陸整正出来形・接写", station="", control="H1=50"),
    DictRecord(category="舗装補修工", type="アスファルト舗装補修工", subtype="上層路盤工", remarks="不陸整正出来形・接写", station="", control="H2=50"),
    DictRecord(category="舗装補修工", type="アスファルト舗装補修工", subtype="上層路盤工", remarks="不陸整正出来形・接写", station="", control="H3=50"),
    DictRecord(category="舗装補修工", type="アスファルト舗装補修工", subtype="上層路盤工", remarks="砕石厚測定", station="", control="t=30mm"),
    DictRecord(category="舗装補修工", type="アスファルト舗装補修工", subtype="表層工", remarks="プライムコート乳剤散布状況", station="", control=""),
    DictRecord(category="舗装補修工", type="アスファルト舗装補修工", subtype="表層工", remarks="プライムコート養生砂清掃状況", station="", control=""),
    DictRecord(category="舗装補修工", type="アスファルト舗装補修工", subtype="表層工", remarks="端部乳剤塗布状況", station="", control=""),
    DictRecord(category="舗装補修工", type="アスファルト舗装補修工", subtype="表層工", remarks="舗設状況", station="", control=""),
    DictRecord(category="舗装補修工", type="アスファルト舗装補修工", subtype="表層工", remarks="初期転圧状況", station="", control=""),
    DictRecord(category="舗装補修工", type="アスファルト舗装補修工", subtype="表層工", remarks="2次転圧状況", station="", control=""),
    DictRecord(category="舗装補修工", type="アスファルト舗装補修工", subtype="表層工", remarks="As混合物温度管理到着温度測定", station="", control="161℃"),
    DictRecord(category="舗装補修工", type="アスファルト舗装補修工", subtype="表層工", remarks="As混合物温度管理敷均し温度測定", station="", control="155℃"),
    DictRecord(category="舗装補修工", type="アスファルト舗装補修工", subtype="表層工", remarks="As混合物温度管理初期締固前温度", station="", control="148℃"),
    DictRecord(category="舗装補修工", type="アスファルト舗装補修工", subtype="表層工", remarks="As混合物温度管理開放温度測定", station="", control="38℃"),
]

def main():
    with open(OCR_CACHE_PATH, encoding='utf-8') as f:
        ocr_cache = json.load(f)
    dm = DictionaryManager()
    dm.records = TEST_RECORDS
    for img_key, ocr_text in ocr_cache.items():
        print(f"=== {img_key} ===")
        results = dm.find_best_matches(ocr_text, top_n=3, threshold=70)
        print(f"--- OCRテキスト ---\n{ocr_text}\n-------------------")
        print("--- 類似度上位3件 ---")
        for i, r in enumerate(results, 1):
            rec = r['record']
            print(f"{i}. スコア: {r['score']} フィールド: {r['matched_field']} 候補: {getattr(rec, r['matched_field'])} (OCR行: '{r['ocr_line']}')")
        if not results:
            print("該当候補なし")
        print()

if __name__ == '__main__':
    main() 