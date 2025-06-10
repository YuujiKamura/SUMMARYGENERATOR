import json
import os
from typing import List, Optional

def convert_image_list_json_to_yolo_ann_json(
    input_json_path: str,
    output_json_path: Optional[str] = None
) -> List[dict]:
    """
    画像パスだけのJSON（{"images": [...]} またはリスト）やbboxes付きJSONを
    YOLO用アノテーション付きJSON（bboxes維持 or 空）リストに変換する。
    output_json_pathを指定すれば書き出しも行う。
    戻り値: 変換後のリスト
    """
    with open(input_json_path, encoding="utf-8") as f:
        data = json.load(f)
    result = []
    if isinstance(data, dict) and "images" in data:
        images = data["images"]
        for img in images:
            if isinstance(img, dict):
                path = img.get("path") or img.get("image_path")
            else:
                path = img
            if not path:
                continue
            result.append({"image_path": path, "bboxes": []})
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                path = item.get("image_path") or item.get("path")
                bboxes = item.get("bboxes")
                if path:
                    result.append({"image_path": path, "bboxes": bboxes if bboxes is not None else []})
            else:
                result.append({"image_path": item, "bboxes": []})
    else:
        raise ValueError(f"画像リストJSONの形式が不正です: {input_json_path}")
    if output_json_path:
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    return result

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="画像リストJSON→YOLOアノテーションJSON変換")
    parser.add_argument("--in_json", required=True, help="画像リストJSONファイル")
    parser.add_argument("--out_json", required=True, help="出力先YOLOアノテーションJSONファイル")
    args = parser.parse_args()
    convert_image_list_json_to_yolo_ann_json(args.in_json, args.out_json)
    print(f"変換完了: {args.out_json}") 