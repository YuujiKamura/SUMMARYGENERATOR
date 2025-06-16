#!/usr/bin/env python3
"""
キャプションボードが検出された画像を上から順番に確認するスクリプト
"""

import json
import os

def list_caption_board_images():
    # マスターファイルを読み込み
    master_path = "../data/image_preview_cache_master.json"
    with open(master_path, "r", encoding="utf-8") as f:
        master_data = json.load(f)
    
    print("=== キャプションボード検出画像一覧 ===")
    print(f"総画像数: {len(master_data)}件")
    
    caption_board_images = []
    
    for i, item in enumerate(master_data):
        image_path = item.get("image_path", "")
        filename = item.get("filename", "")
          # キャプションボードのbboxがあるかチェック
        caption_boards = []
        for bbox in item.get("bboxes", []):
            cname = bbox.get("cname", "")
            role = bbox.get("role", "") or ""
            if cname == "caption_board" or "caption_board" in role:
                caption_boards.append(bbox)
        
        if caption_boards:
            caption_board_images.append({
                "index": i,
                "filename": filename,
                "image_path": image_path,
                "caption_boards": caption_boards
            })
    
    print(f"キャプションボード検出画像: {len(caption_board_images)}件\n")
    
    for i, item in enumerate(caption_board_images):
        image_name = os.path.basename(item["image_path"]) if item["image_path"] else "N/A"
        print(f"{i+1:2d}. {image_name}")
        print(f"    ファイル名: {item['filename']}")
        
        for j, cb in enumerate(item["caption_boards"]):
            cname = cb.get("cname", "N/A")
            role = cb.get("role", "N/A")
            conf = cb.get("conf", 0)
            xyxy = cb.get("xyxy", [])
            
            if len(xyxy) >= 4:
                w = int(xyxy[2] - xyxy[0])
                h = int(xyxy[3] - xyxy[1])
                area = w * h
                print(f"    CB{j+1}: {cname} (role: {role})")
                print(f"         信頼度: {conf:.3f}, サイズ: {w}×{h} ({area:,} px²)")
            else:
                print(f"    CB{j+1}: {cname} (role: {role}), 信頼度: {conf:.3f}")
        print()
    
    return caption_board_images

if __name__ == "__main__":
    images = list_caption_board_images()
    
    print("\n=== 確認したい画像番号を入力してください ===")
    print("例: 1, 2, 3 など")
    print("範囲指定: 1-5")
    print("終了: q")
    
    while True:
        try:
            user_input = input("\n番号を入力 > ").strip()
            if user_input.lower() == 'q':
                break
                
            if '-' in user_input:
                # 範囲指定
                start, end = map(int, user_input.split('-'))
                for idx in range(start-1, min(end, len(images))):
                    if 0 <= idx < len(images):
                        image_name = os.path.basename(images[idx]["image_path"])
                        print(f"\n--- {idx+1}. {image_name} ---")
                        os.system(f'python test_single_image.py --filename {image_name.replace(".JPG", "")}')
                        input("次に進むにはEnterを押してください...")
            else:
                # 単一指定
                idx = int(user_input) - 1
                if 0 <= idx < len(images):
                    image_name = os.path.basename(images[idx]["image_path"])
                    print(f"\n--- {idx+1}. {image_name} ---")
                    os.system(f'python test_single_image.py --filename {image_name.replace(".JPG", "")}')
                else:
                    print("無効な番号です")
                    
        except ValueError:
            print("数値を入力してください")
        except KeyboardInterrupt:
            break
    
    print("終了しました。")
