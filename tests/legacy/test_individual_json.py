from summarygenerator.utils.path_manager import path_manager
import json

# テスト用画像パス（image_list20250531.jsonの先頭画像を例示）
image_path = r'H:\マイドライブ\〇東区市道（2工区）舗装補修工事（水防等含）（単価契約）\６工事写真\0530小山工区\RIMG8603.JPG'
json_path = path_manager.get_individual_json_path(image_path)
print('JSON PATH:', json_path)

if json_path.exists():
    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)
        print('image_path:', data.get('image_path'))
        print('bboxes:', data.get('bboxes'))
else:
    print('個別JSONが存在しません:', json_path)
